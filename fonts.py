"""Catàleg d'horaris que el servei vigila.

Per afegir un grau nou: afegeix-hi una entrada amb l'URL (o URLs) dels PDF, el
lector que sap llegir aquell format i, si cal, els grups.
Per afegir una altra universitat, afegeix una clau nova a UNIVERSITATS.
"""
from lectors import uab_medicina_1r, uab_veterinaria

UNIVERSITATS = {
    "uab": {
        "nom": "Universitat Autònoma de Barcelona",
        "titulacions": {
            "medicina-1": {
                "nom": "Grau en Medicina · 1r curs (Bellaterra)",
                "urls": ["https://www.uab.cat/doc/DOC_HorariMed1_UCMB"],
                "lector": uab_medicina_1r,
                "ntfy": "horaris-uab-medicina1",  # tema d'avisos: <prefix>-<grup>
            },
            "veterinaria-3": {
                "nom": "Grau en Veterinària · 3r curs",
                "urls": ["https://www.uab.cat/ca/veterinaria/doc/vethoraris3r1rsemestre.pdf",
                         "https://www.uab.cat/ca/veterinaria/doc/vethoraris3r2nsemestre.pdf"],
                "lector": uab_veterinaria,
                "grups": ["T1-5ab", "T2-5ab"],  # teoria 1 o 2 + pràctiques 5ab
                "ntfy": "horaris-uab-vet3",
            },
        },
    },
}


def grups(tit):
    return tit.get("grups") or tit["lector"].grups_disponibles()


def nom_grup(tit, grup):
    f = getattr(tit["lector"], "nom_grup", None)
    return f(grup) if f else f"Grup {grup}"


def totes():
    """[(id_font, universitat, titulació)] p.ex. ('uab/medicina-1', {...}, {...})."""
    return [(f"{u}/{t}", uni, tit)
            for u, uni in UNIVERSITATS.items()
            for t, tit in uni["titulacions"].items()]


def busca(id_font):
    u, t = id_font.split("/", 1)
    return UNIVERSITATS[u]["titulacions"][t]
