"""Lectors de PDF d'horaris. Cada facultat publica un format diferent, així que
cada format té el seu lector. Tots tenen la mateixa funció:

    llegeix(cami_pdf, grup) -> (sessions_de_tot_el_grup, sessions_de_subgrups)

on cada sessió és un dict amb: dia (AAAA-MM-DD), inici (HH:MM), fi (HH:MM),
assignatura, tipus, aula, text (text original del PDF) i subgrups.
"""
