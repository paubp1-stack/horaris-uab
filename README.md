# Horaris de la universitat → Google Calendar (100 % gratuït)

Web perquè qualsevol estudiant triï la seva titulació i grup i tingui els
horaris al calendari, actualitzats sols quan la universitat canvia el PDF.
No cal cap servidor: tot funciona amb GitHub (gratuït).

## Com funciona

- **GitHub Actions** (`.github/workflows/actualitza.yml`) executa
  `genera.py` un cop al dia. Baixa cada PDF del catàleg (`fonts.py`) i, si
  ha canviat:
  - genera `docs/cal/<universitat>/<titulació>/<grup>.ics` i `.json`;
  - compara amb la versió anterior i envia un avís al tema de **ntfy** del
    grup (p. ex. `horaris-uab-medicina1-104`).
- **GitHub Pages** publica la carpeta `docs/`: la web (`index.html`) i els
  calendaris.
- L'estudiant té tres opcions a la web:
  1. **Afegir l'enllaç .ics** a Google Calendar (un clic; Google el revisa
     tot sol, però pot trigar fins a un dia a mostrar un canvi).
  2. **Actualització ràpida** amb Google Apps Script (`docs/apps-script.js`):
     un script al seu propi compte que actualitza el calendari cada hora.
  3. **Avisos al mòbil** amb l'app ntfy.

Protecció: si un PDF nou dona menys de la meitat de sessions que l'anterior
(per exemple, perquè la universitat n'ha canviat el format), no s'actualitza
res i l'error queda a `docs/estat.json`.

## Estat actual

| Universitat | Titulació | Grups comprovats |
|---|---|---|
| UAB | Medicina 1r (Bellaterra) | 104 i subgrups G11, G15, G16b |
| UAB | Veterinària 3r | teoria 1-2 × subgrups de pràctiques 1aa-6bb |

Cada facultat publica el PDF en un format diferent, així que cada format
necessita el seu lector a `lectors/`. Per afegir un grau: escriure (o
reutilitzar) el lector, afegir-lo a `fonts.py` i comprovar-ne els grups.

## Posar-lo en marxa (una sola vegada)

1. Crea un repositori **públic** a GitHub (GitHub Pages és gratuït només en
   repositoris públics) i puja-hi tots els fitxers, inclosa la carpeta
   `.github`.
2. *Settings → Pages*: **Deploy from a branch**, branca `main`, carpeta
   `/docs`. La web quedarà a `https://<usuari>.github.io/<repositori>/`.
3. *Settings → Actions → General → Workflow permissions*:
   **Read and write permissions**.
4. Pestanya *Actions*: activa els workflows si t'ho demana, obre
   **Actualitza horaris** i clica **Run workflow** per provar-lo.

## Limitacions de la versió gratuïta

- GitHub pot endarrerir les tasques programades (la revisió diària pot arribar una mica més tard).
- GitHub atura les tasques programades d'un repositori públic després de 60
  dies sense activitat. `genera.py` actualitza `docs/estat.json` un cop al
  dia per evitar-ho.
- Els temes de ntfy són públics: qualsevol que en sàpiga el nom pot llegir
  els avisos (són horaris públics) o enviar-hi missatges.

## Provar-ho en local

```bash
pip install -r requirements.txt
python genera.py --sense-avisos
python -m http.server -d docs 8000   # http://localhost:8000
```

## Fitxers

- `genera.py` – baixa els PDF, genera els calendaris i envia avisos
- `lectors/uab_medicina_1r.py` – lector del PDF de Medicina 1r
- `lectors/uab_veterinaria.py` – lector dels PDF de Veterinària
- `fonts.py` – catàleg d'universitats, titulacions, URL, grups i temes ntfy
- `canvis.py` – compara dues versions d'un horari
- `ics.py` – genera el calendari .ics
- `avisos.py` – avisos al mòbil amb ntfy
- `docs/` – la web, l'Apps Script i els calendaris generats
