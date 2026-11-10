"""Genera calendaris .ics (subscripció) a partir de les sessions."""
import hashlib
from datetime import datetime, timezone

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Madrid
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def id_sessio(id_font, grup, s):
    """Identificador estable d'una sessió (per actualitzar-la sense duplicar)."""
    clau = f"{id_font}|{grup}|{s['dia']}|{s['assignatura']}|{s['tipus']}|{s['inici']}"
    return hashlib.sha1(clau.encode()).hexdigest()


def titol(s):
    return f"{s['assignatura']} · {s['tipus']}" if s["tipus"] else s["assignatura"]


def descripcio(s, nom_titulacio, grup):
    linies = [f"{nom_titulacio} · {grup}"]
    if s.get("aula"):
        linies.append(f"Aula: {s['aula']}")
    linies.append(f"Text del PDF: {s['text']}")
    return "\n".join(linies)


def _esc(t):
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _plega(linia):
    """Les línies .ics no poden passar de 75 octets."""
    b = linia.encode()
    if len(b) <= 75:
        return linia
    trossos, actual = [], b""
    for ch in linia:
        cb = ch.encode()
        if len(actual) + len(cb) > (75 if not trossos else 74):
            trossos.append(actual.decode())
            actual = b""
        actual += cb
    trossos.append(actual.decode())
    return "\r\n ".join(trossos)


def _dt(dia, hora):
    return dia.replace("-", "") + "T" + hora.replace(":", "") + "00"


def genera(id_font, nom_titulacio, grup, sessions):
    ara = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    l = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Horaris UAB//CA",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         f"X-WR-CALNAME:{_esc(nom_titulacio)} · {_esc(grup)}",
         "X-WR-TIMEZONE:Europe/Madrid",
         "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H"]
    l += VTIMEZONE.split("\n")
    for s in sessions:
        l += ["BEGIN:VEVENT",
              f"UID:{id_sessio(id_font, grup, s)}@horaris-uab",
              f"DTSTAMP:{ara}",
              f"DTSTART;TZID=Europe/Madrid:{_dt(s['dia'], s['inici'])}",
              f"DTEND;TZID=Europe/Madrid:{_dt(s['dia'], s['fi'])}",
              f"SUMMARY:{_esc(titol(s))}",
              f"DESCRIPTION:{_esc(descripcio(s, nom_titulacio, grup))}"]
        if s.get("aula"):
            l.append(f"LOCATION:{_esc(s['aula'])}")
        l.append("END:VEVENT")
    l.append("END:VCALENDAR")
    return "\r\n".join(_plega(x) for x in l) + "\r\n"
