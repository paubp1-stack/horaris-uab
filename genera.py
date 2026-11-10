"""Vigilant de PDF d'horaris (s'executa a GitHub Actions cada 30 minuts).

Per a cada titulació del catàleg (fonts.py):
  1. baixa el PDF; si l'empremta SHA-256 és la mateixa que l'última vegada, no fa res;
  2. si ha canviat, el llegeix i, per a cada grup, genera
       docs/cal/<universitat>/<titulació>/<grup>.ics   (subscripció)
       docs/cal/<universitat>/<titulació>/<grup>.json  (per a l'Apps Script)
  3. compara amb la versió anterior i envia un avís al tema de ntfy del grup.
També genera docs/cataleg.json, que fa servir la web.

Ús:  python genera.py            (normal)
     python genera.py --forca    (rellegeix encara que el PDF no hagi canviat)
     python genera.py --sense-avisos
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests

import avisos
import canvis
import fonts
import ics

DOCS = Path(__file__).parent / "docs"
ESTAT = DOCS / "estat.json"
WEB = os.environ.get("WEB_URL", "")  # p.ex. https://usuari.github.io/horaris-uab


def baixa(url):
    r = requests.get(url, timeout=60, headers={"User-Agent": "horaris-uab/1.0"})
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise ValueError(f"{url} no ha retornat un PDF")
    return r.content


def tema_ntfy(tit, grup):
    return f"{tit['ntfy']}-{grup}" if tit.get("ntfy") else None


def _escriu(cami, text):
    cami.parent.mkdir(parents=True, exist_ok=True)
    if not cami.exists() or cami.read_text(encoding="utf-8") != text:
        cami.write_text(text, encoding="utf-8", newline="")


def processa(id_font, tit, estat, forca, amb_avisos):
    e = estat.setdefault(id_font, {})
    try:
        pdf = baixa(tit["url"])
    except Exception as err:
        e["error"] = f"Error baixant el PDF: {err}"
        print(f"[{id_font}] {e['error']}")
        return
    sha = hashlib.sha256(pdf).hexdigest()
    if not forca and e.get("sha256") == sha:
        e.pop("error", None)
        return
    print(f"[{id_font}] PDF nou o canviat ({sha[:12]})")
    errors = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf)
        cami_pdf = f.name
    try:
        for grup in tit["grups"]:
            sessions, _ = tit["lector"].llegeix(cami_pdf, grup)
            base = DOCS / "cal" / id_font / grup
            fitxer_json = base.with_suffix(".json")
            abans = None
            if fitxer_json.exists():
                abans = json.loads(fitxer_json.read_text(encoding="utf-8"))["sessions"]
            # Protecció: si la universitat canvia el format del PDF i el lector
            # en treu molt menys que abans, no toquem el calendari de ningú.
            if abans and len(sessions) < 0.5 * len(abans):
                errors.append(f"grup {grup}: {len(sessions)} sessions (abans {len(abans)})")
                print(f"[{id_font}] ATENCIÓ {errors[-1]}. Format nou? No s'actualitza.")
                continue
            nom = tit["nom"]
            for s in sessions:
                s["id"] = ics.id_sessio(id_font, grup, s)
                s["titol"] = ics.titol(s)
                s["descripcio"] = ics.descripcio(s, nom, grup)
            _escriu(base.with_suffix(".ics"), ics.genera(id_font, nom, grup, sessions))
            _escriu(fitxer_json, json.dumps(
                {"titulacio": nom, "grup": grup, "sessions": sessions},
                ensure_ascii=False, indent=1))
            c = canvis.compara(abans or [], sessions)
            if abans and canvis.hi_ha_canvis(c):
                print(f"[{id_font}] grup {grup}:\n{canvis.resum(c, 50)}")
                if amb_avisos:
                    avisos.envia(tema_ntfy(tit, grup), f"Canvis d'horari · {nom} · Grup {grup}",
                                 canvis.resum(c), WEB or None)
    finally:
        os.unlink(cami_pdf)
    e["sha256"] = sha
    e["canviat"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
    if errors:
        e["error"] = "; ".join(errors)
    else:
        e.pop("error", None)


def cataleg():
    out = []
    for id_font, uni, tit in fonts.totes():
        out.append({"id": id_font, "universitat": uni["nom"], "titulacio": tit["nom"],
                    "grups": [{"grup": g, "ntfy": tema_ntfy(tit, g)} for g in tit["grups"]]})
    return out


def main():
    forca = "--forca" in sys.argv
    amb_avisos = "--sense-avisos" not in sys.argv
    estat = json.loads(ESTAT.read_text(encoding="utf-8")) if ESTAT.exists() else {}
    for id_font, _, tit in fonts.totes():
        processa(id_font, tit, estat, forca, amb_avisos)
    # Data de l'última comprovació (només el dia): fa un canvi al repositori
    # un cop al dia, perquè GitHub no aturi la tasca per inactivitat.
    estat["_comprovat"] = datetime.now(timezone.utc).date().isoformat()
    _escriu(ESTAT, json.dumps(estat, ensure_ascii=False, indent=1, sort_keys=True))
    _escriu(DOCS / "cataleg.json", json.dumps(cataleg(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
