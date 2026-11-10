"""Lector dels PDF d'horaris del Grau en Veterinària (UAB).

Cada pàgina és una setmana: una taula amb les franges horàries a l'esquerra i
els dies a dalt. Els matins hi ha pràctiques (cada dia dividit en columnes,
una per pràctica, amb el codi, els grups i l'aula) i les tardes la teoria
("SANITAT (6) g1-A13": assignatura, número de sessió, grup de teoria, aula).

Grups de l'estudiant: grup de teoria (1 o 2) i subgrup de pràctiques
(p. ex. "3ab"). Una pràctica marcada "g 3" o "g 3a" també la fa el 3ab.
Identificador de grup: "T1-3ab".
"""
import re
from datetime import date

import pdfplumber

DIES = ("DILLUNS", "DIMARTS", "DIMECRES", "DIJOUS", "DIVENDRES")
MESOS = {"setembre": 9, "octubre": 10, "novembre": 11, "desembre": 12, "gener": 1,
         "febrer": 2, "març": 3, "marc": 3, "abril": 4, "maig": 5, "juny": 6, "juliol": 7}
CATEGORIES = {"PLAB": "Pràctiques de laboratori", "SEM": "Seminari",
              "PQV": "Pràctiques en quiròfan", "PAV": "Pràctiques amb animals vius",
              "PCAv": "Pràctica clínica assistencial", "PAUL": "Pràctiques d'aula",
              "PVG": "Pràctiques en granges", "SESP": "Seminari especialitzat"}
# Noms abreujats de la teoria -> nom complet (segons la llegenda dels PDF)
NOMS_TEORIA = {"sanitat": "Sanitat Animal I", "sanitat ii": "Sanitat Animal II",
               "pai": "Producció Animal Integrada I", "pai ii": "Producció Animal Integrada II",
               "farmaco": "Farmacologia", "farmacologia": "Farmacologia",
               "cirurgia/ anestes.": "Cirurgia i Anestesiologia",
               "med. i cirurgia a. abastament": "Medicina i Cirurgia d'Animals d'Abastament",
               "reproducció": "Reproducció Animal", "aqüicultura": "Aqüicultura i Ictiopatologia",
               "millora genètica": "Millora Genètica"}
RE_TEORIA = re.compile(r"\bg\s?([12])\s?[-–]\s?([A-Z][\w.]*)")
RE_GRUP = re.compile(r"\bg\s?(\d{1,2}[a-z]{0,2}(?:\s?,\s?\d{1,2}[a-z]{0,2})*)\b")
RE_CODI = re.compile(r"\b([A-Z]{1,4}\d{1,2})\b")
RE_AULA = re.compile(r"(V0-?\s?\d{3}[A-Z]?|Inf\.\s?\d|SD|HCV|Granja|Sala d.Actes|A1[34])")


def grups_disponibles():
    fulles = [f"{n}{a}{b}" for n in range(1, 7) for a in "ab" for b in "ab"]
    return [f"T{t}-{f}" for t in (1, 2) for f in fulles]


def nom_grup(grup):
    t, p = grup[1:].split("-")
    return f"Teoria {t} · Pràctiques {p}"


# --- lectura de la taula ------------------------------------------------------
def _text_bbox(pg, x0, top, x1, bot):
    """Línies de text dels caràcters que tenen el centre dins del requadre."""
    dins = lambda o: o.get("object_type") != "char" or (
        x0 - 0.5 <= (o["x0"] + o["x1"]) / 2 <= x1 + 0.5 and top - 0.5 <= (o["top"] + o["bottom"]) / 2 <= bot + 0.5)
    t = pg.filter(dins).extract_text() or ""
    return [l.strip() for l in t.split("\n") if l.strip()]


def _centre_text(pg, c):
    cs = [o for o in pg.chars if c[0] <= (o["x0"] + o["x1"]) / 2 <= c[2]
          and c[1] <= (o["top"] + o["bottom"]) / 2 <= c[3] and o["text"].strip()]
    return max(((o["top"] + o["bottom"]) / 2 for o in cs), default=c[1])


def _min(t):
    h, m = re.split(r"[.:]", t)
    return int(h) * 60 + int(m)


def _setmana(text, any_inici):
    """'SETMANA DEL 28 DE SETEMBRE AL 2 D'OCTUBRE' -> funció dia->date."""
    t = text.replace("’", "'").lower()
    m = re.search(r"setmana (?:del|de l')\s*(\d+)(?:\s+(?:de|d')\s*([a-zç]+))?\s+(?:al|a l')\s*(\d+)\s+(?:de|d')\s*([a-zç]+)", t)
    if not m:
        return None
    d1, mes1, d2, mes2 = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
    m2 = MESOS.get(mes2)
    m1 = MESOS.get(mes1) if mes1 else m2
    if not m2 or not m1:
        return None

    def data(dia):
        mes = m1 if (m1 != m2 and dia >= d1) else m2
        return date(any_inici + (1 if mes <= 8 else 0), mes, dia)
    return data


def _llegenda(text, codis):
    """'(F1: Mètodes analítics) Farmacologia (PAQ1) Aqüicultura...' -> codis."""
    cat = None
    for m in re.finditer(r"\(([^()]*)\)\s*:?\s*([^()]*)", text):
        dins, despres = m.group(1).strip(), m.group(2)
        if dins in CATEGORIES:
            cat = dins
            continue
        nom = re.split(r"\s+(?:Pràctiques|Pràctica|Seminaris)\b", despres)[0].strip(" :-|")
        detall = dins.split(":", 1)[1].strip() if ":" in dins else ""
        for c in RE_CODI.findall(dins.split(":")[0]):
            codis.setdefault(c, (nom or detall, detall if nom else "", cat))
        m3 = re.match(r"([A-Z]+)(\d+)\s*a\s*([A-Z]+)?(\d+)", dins)  # 'BQ1 a BQ3'
        if m3:
            for i in range(int(m3.group(2)), int(m3.group(4)) + 1):
                codis.setdefault(f"{m3.group(1)}{i}", (nom, "", cat))


def _nom_codi(codi, codis):
    if re.fullmatch(r"EX\d+", codi):
        return ("Examen pràctic", "", None)
    if codi in codis:
        return codis[codi]
    pref = re.sub(r"\d+$", "", codi)
    for c, v in codis.items():
        if re.sub(r"\d+$", "", c) == pref:
            return v
    return (codi, "", None)


def _pagina(pg, any_inici, codis):
    taules = pg.find_tables()
    if not taules:
        return []
    taula = max(taules, key=lambda t: len(t.cells))
    cells = [(c, _text_bbox(pg, *c)) for c in taula.cells]
    # Si una cel·la amb text en conté d'altres (cel·les combinades), ens quedem amb la gran
    grans = [c for c, l in cells if l]
    conte = lambda d, c: d != c and d[0] - 1 <= c[0] and d[1] - 1 <= c[1] and c[2] <= d[2] + 1 \
        and c[3] <= d[3] + 1 and (d[2] - d[0]) * (d[3] - d[1]) > (c[2] - c[0]) * (c[3] - c[1]) + 1
    cells = [(c, l) for c, l in cells if not any(conte(d, c) for d in grans)]
    # Text tallat entre dues cel·les ('... (4) -' + 'g 1-A1'): les ajuntem
    cells.sort(key=lambda t: (round(t[0][0]), t[0][1]))
    ajuntades = []
    for c, l in cells:
        if ajuntades:
            pc, pl = ajuntades[-1]
            if pl and l and re.search(r"[-–]\s*g?\s*$", pl[-1]) and abs(pc[0] - c[0]) < 1 \
                    and abs(pc[2] - c[2]) < 1 and 0 <= c[1] - pc[3] < 3:
                ajuntades[-1] = ((pc[0], pc[1], pc[2], c[3]), pl[:-1] + [pl[-1] + " " + l[0]] + l[1:])
                continue
        ajuntades.append((c, l))
    cells = ajuntades
    text_cap = " ".join(" ".join(l) for c, l in cells if c[1] < taula.bbox[1] + 60)
    data_de = _setmana(text_cap, any_inici)
    if not data_de:
        return []
    dies = []
    for c, l in cells:
        m = re.match(r"(\d{1,2})\s+(" + "|".join(DIES) + ")", " ".join(l))
        if m:
            dies.append((c[0], c[2], data_de(int(m.group(1))), c[3]))
    if not dies:
        return []
    x_dades = min(d[0] for d in dies)
    cap_bot = max(d[3] for d in dies)
    # Franges horàries (columna de l'esquerra): interpolació y -> minuts
    franges = []
    for c, l in cells:
        if c[2] <= x_dades + 1 and c[1] >= cap_bot - 1:
            hs = re.findall(r"(\d{1,2}[.:]\d{2})\s*-\s*(\d{1,2}[.:]\d{2})", " ".join(l).replace(" ", "")
                            .replace("-", "-"))
            hs = hs or re.findall(r"(\d{1,2}[.:]\d{2})-\s?(\d{1,2}[.:]\d{2})", " ".join(l))
            if hs:
                franges.append((c[1], c[3], _min(hs[0][0]), _min(hs[-1][1])))
    franges.sort()
    if not franges:
        return []

    def minuts(y):
        for top, bot, a, b in franges:
            if top - 1 <= y <= bot + 1:
                return round((a + (b - a) * (y - top) / max(bot - top, 1)) / 30) * 30
        return franges[0][2] if y < franges[0][0] else franges[-1][3]

    def franja(y):
        for top, bot, a, b in franges:
            if top - 0.5 <= y <= bot + 0.5:
                return a, b
        return None

    def dia_de(x):
        for x0, x1, d, _ in dies:
            if x0 - 1 <= x <= x1 + 1:
                return d
        return None

    out = []
    globals_ = []
    contingut = [(c, l) for c, l in cells if c[0] >= x_dades - 1 and c[1] >= cap_bot - 1]
    # 1) Teoria i activitats de tot el curs (línies amb 'g1-A13' o sense grup)
    practiques = []
    for c, l in contingut:
        text = " ".join(l)
        dia = dia_de((c[0] + c[2]) / 2)
        if not dia or not text.strip():
            continue
        net = re.sub(r"\s", "", text).upper()
        if net in ("FESTIU", "FESTA") or net.startswith("FESTIU"):
            continue
        if RE_TEORIA.search(text):
            fr = franja((c[1] + c[3]) / 2)
            if not fr:
                continue
            ant = 0
            for m in RE_TEORIA.finditer(text):
                part, ant = text[ant:m.end()].strip(), m.end()
                if True:
                    nom = re.split(r"\(|[\s–-]+g\s?\d", part)[0].strip(" -–")
                    ses = re.search(r"\((\d+)\)", part)
                    out.append({"dia": dia, "ini": fr[0], "fi": fr[1],
                                "assignatura": nom.capitalize(), "tipus": "Teoria",
                                "sessio": ses.group(1) if ses else "", "aula": m.group(2),
                                "teoria": m.group(1), "practica": None, "text": part})
        elif RE_GRUP.search(text):
            practiques.append((c, l, dia))
        elif RE_CODI.search(text) or RE_AULA.search(text) or len(text.replace(" ", "")) < 14:
            practiques.append((c, l, dia))  # tros (codi, aula) d'una pràctica...
            globals_.append((c, text, dia, True))  # ...o d'una activitat (aules d'examen)
        else:
            globals_.append((c, text, dia, False))
    # Activitats sense grup (actes, exàmens...): per a tothom. Les cel·les
    # d'una mateixa columna que es toquen formen una sola activitat.
    globals_.sort(key=lambda t: (t[2], round(t[0][0]), t[0][1]))
    units = []
    for c, text, dia, tros in globals_:
        u = units[-1] if units else None
        if u and u[2] == dia and abs(u[0][0] - c[0]) < 1 and abs(u[0][2] - c[2]) < 1 and -1.5 < c[1] - u[0][3] < 10:
            units[-1] = ((u[0][0], u[0][1], u[0][2], c[3]), u[1] + " " + text, dia)
        elif not tros:  # un tros sol (aula, codi) no és una activitat
            units.append((c, text, dia))
    for c, text, dia in units:
        if True:
            h = re.search(r"\((\d{1,2})(?:[.:](\d{2}))?\s*a\s*(\d{1,2})(?:[.:](\d{2}))?\s*h\)", text)
            if h:
                a = int(h.group(1)) * 60 + int(h.group(2) or 0)
                b = int(h.group(3)) * 60 + int(h.group(4) or 0)
            else:
                a, b = minuts(c[1]), minuts(c[3])
            if b <= a:
                fr = franja((c[1] + c[3]) / 2)
                b = fr[1] if fr and fr[1] > a else a + 60
            examen = re.search(r"examen", text, re.I)
            nom = re.split(r"\s*\(|\s*EXAMEN|\s*Examen", text)[0].strip(" -–") or text
            out.append({"dia": dia, "ini": a, "fi": b, "assignatura": nom.capitalize(),
                        "tipus": "Examen" if examen else "", "sessio": "", "aula": "",
                        "teoria": None, "practica": None, "text": text})
    # 2) Pràctiques: les cel·les d'una mateixa columna formen blocs
    columnes = {}
    for c, l, dia in practiques:
        columnes.setdefault((dia, round(c[0]), round(c[2])), []).append((c, l))
    for (dia, x0, x1), cs in columnes.items():
        cs.sort(key=lambda t: t[0][1])
        blocs = []
        for c, l in cs:
            text = " ".join(l)
            if not text.strip():  # cel·la buida: només allarga el bloc anterior
                if blocs:
                    blocs[-1]["bot"] = max(blocs[-1]["bot"], c[3])
                continue
            nou = bool(RE_GRUP.search(text)) and blocs and RE_GRUP.search(blocs[-1]["text"])
            if not blocs or nou:
                blocs.append({"top": c[1], "bot": c[3], "text": text, "inici_y": c[1]})
                codi_sol = re.fullmatch(r"\s*[A-Z]{1,4}\d{1,2}\s*", text)
                if codi_sol and _centre_text(pg, c) > c[3] - 5:
                    blocs[-1]["inici_y"] = None  # el codi està sobre la línia: comença a la cel·la següent
            else:
                blocs[-1]["bot"] = max(blocs[-1]["bot"], c[3])
                blocs[-1]["text"] += " " + text
                if blocs[-1]["inici_y"] is None:
                    blocs[-1]["inici_y"] = c[1]
        codi_ant = None
        for i, b in enumerate(blocs):
            codis_b = [x for x in RE_CODI.findall(b["text"]) if not x.startswith("V")]
            if not codis_b:  # el codi pot estar just a sobre de la cel·la
                sobre = _text_bbox(pg, x0, b["top"] - 14, x1, b["top"] + 1)
                codis_b = [x for x in RE_CODI.findall(" ".join(sobre)) if not x.startswith("V")]
            codi = codis_b[0] if codis_b else codi_ant
            codi_ant = codi
            grups = []
            for g in RE_GRUP.findall(b["text"]):
                grups += [x.strip() for x in g.split(",")]
            if not grups:
                continue
            if b["inici_y"] is None:
                b["inici_y"] = b["top"]
            fi_y = blocs[i + 1]["top"] if i + 1 < len(blocs) else b["bot"]
            nom, detall, cat = _nom_codi(codi, codis) if codi else ("Pràctica", "", None)
            compacte = re.sub(r"(V0-)\s+", r"\1", b["text"])
            aula = " ".join(dict.fromkeys(a.replace(" ", "") for a in RE_AULA.findall(compacte)))
            if "Quir" in b["text"]:
                aula = "Antics quiròfans HCV"
            ini, fi = minuts(b["inici_y"]), minuts(fi_y)
            if fi <= ini:
                fr = franja((b["top"] + b["bot"]) / 2)
                fi = fr[1] if fr and fr[1] > ini else ini + 60
            out.append({"dia": dia, "ini": ini, "fi": fi,
                        "assignatura": nom, "tipus": CATEGORIES.get(cat, "Pràctiques"),
                        "sessio": "", "aula": aula, "teoria": None, "practica": grups,
                        "codi": codi, "detall": detall, "text": b["text"]})
    return out


_CACHE = {}


def _totes(camins):
    """Llegeix tots els PDF un sol cop (es reaprofita per a tots els grups)."""
    if isinstance(camins, str):
        camins = [camins]
    import os
    clau = tuple((c, os.path.getmtime(c), os.path.getsize(c)) for c in camins)
    if clau not in _CACHE:
        _CACHE.clear()
        _CACHE[clau] = _llegeix_tot(camins)
    return _CACHE[clau]


def _llegeix_tot(camins):
    sessions = []
    for cami in camins:
        with pdfplumber.open(cami) as pdf:
            text0 = pdf.pages[0].extract_text() or ""
            m = re.search(r"CURS (\d{4})-(\d{4})", text0)
            any_inici = int(m.group(1)) if m else date.today().year
            codis = {}
            for pg in pdf.pages:  # primer, la llegenda de codis de totes les pàgines
                _llegenda(" ".join((pg.extract_text() or "").split("\n")[-6:]), codis)
            for pg in pdf.pages:
                sessions += _pagina(pg, any_inici, codis)
    return sessions


def _li_toca(s, teoria, fulla):
    if s["teoria"]:
        return s["teoria"] == teoria
    if s["practica"]:
        return any(fulla.startswith(g) for g in s["practica"])
    return True  # activitats per a tot el curs


def llegeix(camins, grup):
    """grup: 'T1-3ab'. Retorna (sessions, []) en el format comú dels lectors."""
    teoria, fulla = grup[1:].split("-")
    res = []
    for s in _totes(camins):
        if not _li_toca(s, teoria, fulla) or s["fi"] <= s["ini"]:
            continue
        tipus = s["tipus"]
        if s["sessio"]:
            tipus = f"{tipus} (sessió {s['sessio']})"
        if s.get("codi"):
            tipus = f"{tipus} · {s['codi']}" + (f" ({s['detall']})" if s.get("detall") else "")
        res.append({
            "dia": s["dia"].isoformat(),
            "inici": f"{s['ini'] // 60:02d}:{s['ini'] % 60:02d}",
            "fi": f"{s['fi'] // 60:02d}:{s['fi'] % 60:02d}",
            "assignatura": NOMS_TEORIA.get(s["assignatura"].lower(), s["assignatura"]) if s["teoria"]
            else (s["assignatura"] or "Classe"),
            "tipus": tipus, "aula": s["aula"],
            "text": s["text"], "subgrups": s["practica"] or ([f"T{s['teoria']}"] if s["teoria"] else []),
        })
    clau = lambda e: (e["dia"], e["inici"], e["text"])
    return sorted({clau(e): e for e in res}.values(), key=clau), []
