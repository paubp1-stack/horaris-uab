/**
 * Horaris de la universitat → Google Calendar (actualització automàtica)
 *
 * Aquest script funciona al TEU compte de Google i només toca el calendari
 * que crea ell mateix. Cada hora mira si l'horari del teu grup ha canviat
 * i actualitza el calendari.
 *
 * Per activar-lo: desa (icona del disquet), tria la funció "activa" a dalt
 * i clica "Executa". Google et demanarà permís el primer cop.
 */

// Enllaç de l'horari del teu grup (la web ja l'omple per tu):
const URL_HORARI = 'ENGANXA_AQUI_EL_TEU_ENLLAC';

/** Executa-la UN COP per activar l'actualització automàtica. */
function activa() {
  if (!/^https?:\/\//.test(URL_HORARI)) {
    throw new Error("Primer posa l'enllaç del teu grup a URL_HORARI (línia 14).");
  }
  ScriptApp.getProjectTriggers()
    .filter(function (t) { return t.getHandlerFunction() === 'sincronitza'; })
    .forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('sincronitza').timeBased().everyHours(1).create();
  sincronitza();
  Logger.log('Fet! El calendari s\'actualitzarà sol.');
}

/** Atura l'actualització automàtica (el calendari es queda com està). */
function desactiva() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  Logger.log('Actualització automàtica aturada.');
}

function sincronitza() {
  const resp = UrlFetchApp.fetch(URL_HORARI + '?t=' + Date.now(), { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) {
    throw new Error('No s\'ha pogut llegir l\'horari (' + resp.getResponseCode() + ').');
  }
  const dades = JSON.parse(resp.getContentText());
  const cal = calendari_(dades.titulacio + ' · Grup ' + dades.grup);

  // Només a partir d'una setmana enrere: les classes passades no cal tocar-les.
  const desDe = new Date(Date.now() - 7 * 24 * 3600 * 1000);
  const desDeTxt = Utilities.formatDate(desDe, 'Europe/Madrid', 'yyyy-MM-dd');
  const desitjades = {};
  dades.sessions.forEach(function (s) { if (s.dia >= desDeTxt) desitjades[s.id] = s; });

  const fins = new Date(Date.now() + 2 * 365 * 24 * 3600 * 1000);
  const vistes = {};
  let creades = 0, canviades = 0, esborrades = 0;

  cal.getEvents(desDe, fins).forEach(function (ev) {
    const id = ev.getTag('horaris-id');
    if (!id) return;                         // no és nostre: no el toquem
    const s = desitjades[id];
    if (!s || vistes[id]) {                  // ja no existeix (o duplicat)
      ev.deleteEvent(); esborrades++; return;
    }
    vistes[id] = true;
    if (ev.getTag('horaris-empremta') !== empremta_(s)) {
      ev.setTitle(s.titol);
      ev.setTime(data_(s.dia, s.inici), data_(s.dia, s.fi));
      ev.setLocation(s.aula || '');
      ev.setDescription(s.descripcio);
      estil_(ev, s);
      ev.setTag('horaris-empremta', empremta_(s));
      canviades++;
    }
  });

  let aturat = false;
  Object.keys(desitjades).forEach(function (id) {
    if (vistes[id] || aturat) return;
    const s = desitjades[id];
    try {
      const ev = cal.createEvent(s.titol, data_(s.dia, s.inici), data_(s.dia, s.fi),
        { location: s.aula || '', description: s.descripcio });
      ev.setTag('horaris-id', id);
      ev.setTag('horaris-empremta', empremta_(s));
      estil_(ev, s);
      creades++;
      if (creades % 25 === 0) Utilities.sleep(1000);  // Google limita les creacions ràpides
    } catch (e) {
      // Si Google ens frena, la propera execució (d'aquí una hora) continua.
      Logger.log('Aturat temporalment: ' + e);
      aturat = true;
    }
  });
  Logger.log('Noves: ' + creades + ' · Canviades: ' + canviades + ' · Esborrades: ' + esborrades);
}

function calendari_(nom) {
  const props = PropertiesService.getUserProperties();
  const id = props.getProperty('CALENDARI');
  let cal = id ? CalendarApp.getCalendarById(id) : null;
  if (!cal) {
    cal = CalendarApp.createCalendar(nom.slice(0, 100), { color: CalendarApp.Color.GREEN });
    cal.setTimeZone('Europe/Madrid');
    props.setProperty('CALENDARI', cal.getId());
  }
  return cal;
}

function data_(dia, hora) {
  return Utilities.parseDate(dia + ' ' + hora, 'Europe/Madrid', 'yyyy-MM-dd HH:mm');
}

function estil_(ev, s) {
  if ((s.tipus || '').indexOf('Examen') === 0) {
    ev.setColor(CalendarApp.EventColor.RED);
    ev.removeAllReminders();
    ev.addPopupReminder(24 * 60);        // 1 dia abans
    ev.addPopupReminder(7 * 24 * 60);    // 1 setmana abans
  }
}

function empremta_(s) {
  const txt = [s.titol, s.dia, s.inici, s.fi, s.aula, s.descripcio, s.tipus].join('|');
  return Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, txt,
    Utilities.Charset.UTF_8));
}
