"""Lector del PDF d'horaris de 1r de Medicina (UAB, Unitat Docent CMB).

El PDF és una graella: cada pàgina és una setmana, cada dia té columnes de
mitja hora (9:00-19:30) i cada fila és un subgrup (G1...G20). Cada classe és
un rectangle de color amb el text (assignatura i aula) escrit en vertical.

Retorna esdeveniments del grup demanat: només les sessions que fa TOT el grup
(teoria). Les sessions de subgrups (pràctiques, seminaris) es retornen a part.
"""
import re
from datetime import datetime, timedelta

import pdfplumber

MESOS = {"gener": 1, "febrer": 2, "març": 3, "abril": 4, "maig": 5, "juny": 6,
         "juliol": 7, "agost": 8, "setembre": 9, "octubre": 10,
         "novembre": 11, "desembre": 12}

# Files (subgrups) de cada grup de matrícula a la graella principal.
# Deduït de les línies gruixudes que separen els blocs de files.
# Assignatures A (18 subgrups): el 104 són les files G15-G18.
# Assignatures B (20 subgrups): el 104 són les files G16b-G20 (la G15b va amb
# el 103).
# NOMÉS VALIDAT PER AL GRUP 104.
GRUPS = {
    "103": [["G11", "G12", "G13", "G14"]],
    "104": [["G15", "G16", "G17", "G18"],
            ["G16b", "G17b", "G18b", "G19b", "G20"]],
}

ABREV = {
    "BE": "Bioestadística", "BC": "Biologia Cel·lular", "BF": "Biofísica",
    "BQ": "Bioquímica Estructural i Biologia Molecular",
    "ICS": "Introducció a les Ciències de la Salut",
    "PCA": "Pràctica Clínica Assistencial I",
    "AHI": "Anatomia Humana: Generalitats i Aparell Locomotor",
    "HIS": "Histologia", "H": "Histologia", "BQM": "Bioquímica Metabòlica",
    "FG": "Fisiologia General", "AIM": "Aprenentatge Integrat de Medicina I",
    "AIMI": "Aprenentatge Integrat de Medicina I",
    "AHII": "Anatomia Humana: Cardiovascular, Cap i Coll",
}
TIPUS = {"T": "Teoria", "PLAB": "Pràctiques de laboratori",
         "SEM": "Seminari", "PAUL": "Pràctiques d'aula"}


def _es_color(c):
    """Rectangles de classe: color (RGB) que no sigui gris ni blanc."""
    return isinstance(c, (tuple, list)) and len(c) == 3 and len(set(c)) > 1


def _dies(pg):
    """Capçaleres 'dilluns, 7 setembre de 2026' -> [(x_centre, date)] per x."""
    ws = [w for w in pg.extract_words() if w["top"] < 110]
    dies = []
    for i, w in enumerate(ws):
        if w["text"].lower() in MESOS and i >= 1 and i + 2 < len(ws) \
                and ws[i - 1]["text"].isdigit() and ws[i + 2]["text"].isdigit():
            d, a = int(ws[i - 1]["text"]), int(ws[i + 2]["text"])
            x = (ws[i - 1]["x0"] + ws[i + 2]["x1"]) / 2
            dies.append((x, datetime(a, MESOS[w["text"].lower()], d).date()))
    return sorted(dies)


def _hora(text):
    """Les hores estan escrites girades: '03:51' -> 15:30, '0.01' -> 10:00."""
    t = text[::-1].replace(":", ".")
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})", t)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2).ljust(2, "0"))
    return h * 60 + mi if 7 <= h <= 21 and mi in (0, 30) else None


def _columnes(pg):
    """Primera fila de capçalera d'hores -> [(x_centre, minuts)] per x."""
    cands = [(w, _hora(w["text"])) for w in pg.extract_words() if w["top"] < 140]
    cands = [(w, m) for w, m in cands if m is not None]
    if not cands:
        return []
    top = min(w["top"] for w, _ in cands)
    return sorted(((w["x0"] + w["x1"]) / 2, m) for w, m in cands if w["top"] - top < 3)


def _files(pg, x_primera_col):
    """Etiquetes de fila (G1, G15, G15b...) a l'esquerra de la graella.
    Retorna {'G15': (top, bottom)}."""
    lab = [c for c in pg.chars if x_primera_col - 16 < c["x0"] < x_primera_col - 1]
    per_y = {}
    for c in lab:
        per_y.setdefault(round(c["top"]), []).append(c)
    centres = []
    for y, cs in sorted(per_y.items()):
        t = "".join(c["text"] for c in sorted(cs, key=lambda c: c["x0"]))
        m = re.fullmatch(r"\s*G?\s?(\d{1,2}b?)\s*\S?", t)
        if m and int(re.sub(r"\D", "", m.group(1))) <= 30:
            centres.append(("G" + m.group(1), y + 2))
    files = {}
    for i, (nom, y) in enumerate(centres):
        alt = 16.4
        if i + 1 < len(centres) and 10 < centres[i + 1][1] - y < 20:
            alt = centres[i + 1][1] - y
        files.setdefault(nom, (y - alt / 2, y + alt / 2))
    return files


def _rotat(c):
    m = c.get("matrix") or (1, 0, 0, 1, 0, 0)
    return abs(m[1]) > 0.5


def _text(pg, x0, x1, top, bottom):
    cs = [c for c in pg.chars
          if x0 <= (c["x0"] + c["x1"]) / 2 <= x1 and top <= (c["top"] + c["bottom"]) / 2 <= bottom]
    # el PDF fa les negretes escrivint el mateix caràcter 3 cops desplaçat
    unics = []
    for c in cs:
        if not any(u["text"] == c["text"] and abs(u["x0"] - c["x0"]) < 0.8
                   and abs(u["top"] - c["top"]) < 0.8 for u in unics):
            unics.append(c)
    cs = unics
    rot = [c for c in cs if _rotat(c)]
    hor = [c for c in cs if not _rotat(c)]
    parts = []
    # text girat 90°: es llegeix de baix a dalt; cada línia és una "columna" x
    linies = {}
    for c in rot:
        linies.setdefault(round(c["x0"] / 2), []).append(c)
    for k in sorted(linies):
        parts.append("".join(c["text"] for c in sorted(linies[k], key=lambda c: -c["top"])))
    linies = {}
    for c in hor:
        linies.setdefault(round(c["top"] / 2), []).append(c)
    for k in sorted(linies):
        parts.append("".join(c["text"] for c in sorted(linies[k], key=lambda c: c["x0"])))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _blocs(pg):
    """Ajunta els rectangles de color contigus en blocs (una classe)."""
    rs = [r for r in pg.rects if r.get("fill") and _es_color(r.get("non_stroking_color"))]
    blocs = []
    for r in sorted(rs, key=lambda r: (r["x0"], r["top"])):
        col = tuple(round(v, 3) for v in r["non_stroking_color"])
        for b in blocs:
            if b["col"] == col and abs(b["x0"] - r["x0"]) < 1 and abs(b["x1"] - r["x1"]) < 1 \
                    and abs(b["bottom"] - r["top"]) < 1.5:
                b["bottom"] = max(b["bottom"], r["bottom"])
                break
        else:
            blocs.append({"col": col, "x0": r["x0"], "x1": r["x1"],
                          "top": r["top"], "bottom": r["bottom"]})
    return blocs


def _norm(t):
    t = t.casefold().replace("·", ".").replace("l.l", "ll")
    return re.sub(r"[^a-zàèéíïòóúüç ]", " ", t)


NOMS = sorted(set(ABREV.values()), key=len, reverse=True)


def _hores_text(text):
    """'15-19h', 'Horari: 9-14h', '12:00-16:00h' -> (inici, fi) en minuts."""
    m = re.search(r"\b(\d{1,2})(?:[:.](\d{2}))?\s?-\s?(\d{1,2})(?:[:.](\d{2}))?\s?h", text)
    if not m:
        return None
    a = int(m.group(1)) * 60 + int(m.group(2) or 0)
    b = int(m.group(3)) * 60 + int(m.group(4) or 0)
    return (a, b) if 7 * 60 <= a < b <= 22 * 60 else None


def _descriu(text):
    """'BF-T2 Aula M5-003' -> ('Biofísica', 'Teoria', 'M5-003')."""
    aules = [a.replace(" ", "") for a in re.findall(r"\bM\d[-/]\s?\d{2,3}", text)]
    nt = _norm(text)
    if re.search(r"examen|parcial", nt):
        nom = next((n for n in NOMS if _norm(n) in nt), None)
        if not nom:  # p.ex. 'ANATOMIA HUMANA -II: CARDIOVASCULAR...'
            nom = next((n for n in NOMS if all(w in nt for w in _norm(n).split() if len(w) > 3)), text)
        p = re.search(r"([123])\s?(?:r|n)\s+parcial", text.casefold())
        tipus = f"Examen {p.group(1)}{'n' if p.group(1) == '2' else 'r'} parcial" if p else "Examen"
        if "pr.ctic" in nt:
            tipus += " (pràctic)"
        elif "te.ric" in nt:
            tipus += " (teòric)"
        if "microscopis" in nt:
            tipus = "Examen de microscopis"
        return nom, tipus, ", ".join(dict.fromkeys(aules))
    nom = next((ABREV[t] for t in re.findall(r"\b([A-ZÀ-Ú]+)\b|([A-ZÀ-Ú]+)(?=-)", text) for t in t if t in ABREV), None)
    if nom is None:
        nom = next((ABREV[t] for t in re.findall(r"[A-ZÀ-Ú]+", text) if t in ABREV and len(t) > 1), text)
    t = re.search(r"-\s?(PLAB|SEM|PAUL|T)\d?\b", text)
    tipus = TIPUS.get(t.group(1), "") if t else ("SAT" if "SAT" in text else "")
    aula = aules[0] if aules else ""
    m = re.search(r"SAT\s?\d+", text)
    if not aula and m:
        aula = ""
        tipus = m.group(0).replace(" ", "")
    return nom, tipus, aula


# Subgrups de pràctiques: (grup de matrícula, fila de la graella)
SUBGRUPS = {"G11": ("103", "G11"), "G15": ("104", "G15"), "G16b": ("104", "G16b")}


def grups_disponibles():
    return ["104", "G11", "G15", "G16b"]


def nom_grup(grup):
    if grup in SUBGRUPS:
        return f"Subgrup {grup} (grup {SUBGRUPS[grup][0]})"
    return f"Grup {grup} (només sessions de tot el grup)"


def llegeix(cami_pdf, grup):
    """grup: '104' (sessions de tot el grup) o un subgrup ('G15'): sessions de
    tot el seu grup + les pràctiques i seminaris d'aquell subgrup."""
    if isinstance(cami_pdf, (list, tuple)):
        cami_pdf = cami_pdf[0]
    if grup in SUBGRUPS:
        pare, fila = SUBGRUPS[grup]
        tot, parcials = _llegeix(cami_pdf, pare)
        propis = [s for s in parcials if fila in s["subgrups"]]
        clau = lambda e: (e["dia"], e["inici"], e["text"])
        return sorted({clau(e): e for e in tot + propis}.values(), key=clau), []
    return _llegeix(cami_pdf, grup)


_CACHE = {}


def _llegeix(cami_pdf, grup):
    import os
    clau = (cami_pdf, os.path.getmtime(cami_pdf), grup)
    if clau not in _CACHE:
        _CACHE[clau] = _llegeix_pdf(cami_pdf, grup)
    tot, sub = _CACHE[clau]
    return [dict(s) for s in tot], [dict(s) for s in sub]


def _llegeix_pdf(cami_pdf, grup):
    """Retorna (sessions_de_tot_el_grup, sessions_de_subgrups)."""
    blocs_grup = GRUPS[grup]
    esdeveniments, subgrups = [], []
    with pdfplumber.open(cami_pdf) as pdf:
        for pg in pdf.pages:
            dies = _dies(pg)
            cols = _columnes(pg)
            if not dies or not cols:
                continue
            files = _files(pg, cols[0][0] - 3)
            # cada columna pertany al dia amb la capçalera més propera
            dia_de_col = [min(range(len(dies)), key=lambda k: abs(dies[k][0] - x))
                          for x, m in cols]
            for b in _blocs(pg):
                dins = [i for i, (x, m) in enumerate(cols) if b["x0"] - 1 <= x <= b["x1"] + 1]
                if not dins:
                    continue
                text = _text(pg, b["x0"], b["x1"], b["top"], b["bottom"])
                if not text:
                    continue
                for sub in blocs_grup:
                    rows = [f for f in sub if f in files]
                    cob = [f for f in rows
                           if b["top"] - 2 <= (files[f][0] + files[f][1]) / 2 <= b["bottom"] + 2]
                    if not cob:
                        continue
                    ini, fi = cols[dins[0]][1], cols[dins[-1]][1] + 30
                    explicit = _hores_text(text)
                    if explicit:
                        ini, fi = explicit
                    nom, tipus, aula = _descriu(text)
                    e = {
                        "dia": dies[dia_de_col[dins[0]]][1].isoformat(),
                        "inici": f"{ini // 60:02d}:{ini % 60:02d}",
                        "fi": f"{fi // 60:02d}:{fi % 60:02d}",
                        "text": text, "assignatura": nom, "tipus": tipus, "aula": aula,
                        "subgrups": cob,
                    }
                    (esdeveniments if len(cob) == len(rows) else subgrups).append(e)
    clau = lambda e: (e["dia"], e["inici"], e["text"])
    dedup = lambda l: sorted({clau(e): e for e in l}.values(), key=clau)
    return dedup(esdeveniments), dedup(subgrups)
