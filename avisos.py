"""Avisos al mòbil amb ntfy (app gratuïta per a Android i iPhone).

L'usuari instal·la l'app ntfy, s'hi subscriu a un "tema" (un nom difícil
d'endevinar) i posa aquest mateix nom al formulari del servei.
"""
import os

import requests

NTFY = os.environ.get("NTFY_SERVIDOR", "https://ntfy.sh")


def envia(tema, titol, missatge, url=None):
    if not tema:
        return
    cos = {"topic": tema, "title": titol, "message": missatge,
           "tags": ["calendar"], "priority": 4}
    if url:
        cos["click"] = url
    try:
        # publicació en JSON: admet accents i emojis al títol
        requests.post(NTFY, json=cos, timeout=15)
    except requests.RequestException as e:
        print(f"[avís] no s'ha pogut enviar a {tema}: {e}")
