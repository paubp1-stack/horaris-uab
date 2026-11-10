"""Catàleg d'horaris que el servei vigila.

Per afegir un grau nou: afegeix-hi una entrada amb l'URL del PDF, el lector
que sap llegir aquell format i els grups que s'han comprovat que funcionen.
Per afegir una altra universitat, afegeix una clau nova a UNIVERSITATS.
"""
from lectors import uab_medicina_1r

UNIVERSITATS = {
    "uab": {
        "nom": "Universitat Autònoma de Barcelona",
        "titulacions": {
            "medicina-1": {
                "nom": "Grau en Medicina · 1r curs (Bellaterra)",
                "url": "https://www.uab.cat/doc/DOC_HorariMed1_UCMB",
                "lector": uab_medicina_1r,
                "grups": ["104"],
                # tema de ntfy per als avisos: <prefix>-<grup>
                "ntfy": "horaris-uab-medicina1",
            },
        },
    },
}


def totes():
    """[(id_font, universitat, titulació)] p.ex. ('uab/medicina-1', {...}, {...})."""
    return [(f"{u}/{t}", uni, tit)
            for u, uni in UNIVERSITATS.items()
            for t, tit in uni["titulacions"].items()]


def busca(id_font):
    u, t = id_font.split("/", 1)
    return UNIVERSITATS[u]["titulacions"][t]
