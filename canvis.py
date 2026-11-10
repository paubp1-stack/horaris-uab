"""Compara dues versions de l'horari d'un grup i en treu els canvis."""
from collections import defaultdict


def _clau(s):
    # Una sessió es considera "la mateixa" si és el mateix dia, assignatura i
    # tipus; si en canvia l'hora o l'aula, és una modificació.
    return (s["dia"], s["assignatura"], s["tipus"])


def compara(abans, ara):
    """Retorna {'afegides': [...], 'eliminades': [...], 'modificades': [(vella, nova)]}."""
    a, b = defaultdict(list), defaultdict(list)
    for s in abans:
        a[_clau(s)].append(s)
    for s in ara:
        b[_clau(s)].append(s)
    afegides, eliminades, modificades = [], [], []
    for k in set(a) | set(b):
        va = sorted(a.get(k, []), key=lambda s: s["inici"])
        vb = sorted(b.get(k, []), key=lambda s: s["inici"])
        if len(va) == len(vb):
            for x, y in zip(va, vb):
                if (x["inici"], x["fi"], x.get("aula")) != (y["inici"], y["fi"], y.get("aula")):
                    modificades.append((x, y))
        else:
            igual = lambda s: (s["inici"], s["fi"], s.get("aula"))
            iva, ivb = [igual(s) for s in va], [igual(s) for s in vb]
            eliminades += [s for s in va if igual(s) not in ivb]
            afegides += [s for s in vb if igual(s) not in iva]
    ordre = lambda s: (s["dia"], s["inici"])
    return {"afegides": sorted(afegides, key=ordre),
            "eliminades": sorted(eliminades, key=ordre),
            "modificades": sorted(modificades, key=lambda p: ordre(p[1]))}


def hi_ha_canvis(c):
    return any(c.values())


def resum(c, maxim=8):
    """Text curt per a una notificació."""
    linies = []
    for vella, nova in c["modificades"]:
        canvi = []
        if (vella["inici"], vella["fi"]) != (nova["inici"], nova["fi"]):
            canvi.append(f"{vella['inici']}-{vella['fi']} → {nova['inici']}-{nova['fi']}")
        if vella.get("aula") != nova.get("aula"):
            canvi.append(f"aula {vella.get('aula') or '?'} → {nova.get('aula') or '?'}")
        linies.append(f"✏️ {nova['dia']} {nova['assignatura']}: {', '.join(canvi)}")
    for s in c["afegides"]:
        linies.append(f"➕ {s['dia']} {s['inici']}-{s['fi']} {s['assignatura']} {s['tipus']}".rstrip())
    for s in c["eliminades"]:
        linies.append(f"➖ {s['dia']} {s['inici']}-{s['fi']} {s['assignatura']} {s['tipus']}".rstrip())
    if len(linies) > maxim:
        linies = linies[:maxim] + [f"… i {len(linies) - maxim} canvis més"]
    return "\n".join(linies)
