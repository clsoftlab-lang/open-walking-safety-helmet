// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// App shell: screens, rendering, and wiring between transport (BLE or demo), SOS, location
// and settings. Screen-reader first: every screen change moves focus to its heading, helmet
// messages are announced through aria-live (assertive only for level <= 1).

import { t, has, setLanguage, getLanguage } from './i18n.js';
import { Settings, COUNTRY_PRESETS, findPreset, sanitizePhone } from './settings.js';
import { BleTransport, getBluetoothSupport, isAuthError } from './ble.js';
import { DemoHelmet } from './sim.js';
import { SosController } from './sos.js';
import { LocationService } from './location.js';
import { makeCfg, makeSay, SayThrottle } from './protocol.js';

const $ = (id) => document.getElementById(id);
const LOG_LIMIT = 50;
const STATUS_STALE_S = 25;
const MERGE_WINDOW_MS = 2500;
const LEVEL_SYMBOLS = ['■■', '▲', '◆', '●', '○'];

const settings = new Settings();
const support = getBluetoothSupport();

const app = {
  transport: null,
  connState: 'disconnected',
  attempt: 0,
  hello: null,
  status: null,
  statusAt: 0,
  staleAnnounced: false,
  log: [],
  logSeq: 0,
  route: 'connect',
  pendingCfg: {},
  wakeLock: null,
  wakePending: false,
  adapterAvailable: true,
  undervoltageAnnounced: false,
};

const isConnected = () => !!app.transport && app.connState === 'connected';

// One throttle for every `say` (SOS "I'm OK", location replies, voice test): the helmet accepts
// at most one per 3 s, so never send a second one inside that window.
const sayThrottle = new SayThrottle();

/** Resolves to false when a `say` was not sent because of the helmet's rate limit. */
function send(message) {
  if (!isConnected()) return Promise.reject(new Error('not connected'));
  if (message.t === 'say' && !sayThrottle.tryAcquire()) {
    console.debug('[owsh] say dropped (helmet allows 1 per 3 s):', message.text);
    return Promise.resolve(false);
  }
  return app.transport.send(message);
}

// ---------------------------------------------------------------------------------------------
// Announcements

function announce(text, assertive = false) {
  if (!text) return;
  const region = $(assertive ? 'announce-assertive' : 'announce-polite');
  const p = document.createElement('p');
  p.textContent = text;
  region.append(p);
  while (region.childElementCount > 3) region.firstElementChild.remove();
  setTimeout(() => p.remove(), 15000);
}

let statusMsgTimer = null;
function setSettingsStatus(text) {
  const el = $('settings-status');
  el.textContent = '';
  clearTimeout(statusMsgTimer);
  statusMsgTimer = setTimeout(() => { el.textContent = text; }, 60);
}

// ---------------------------------------------------------------------------------------------
// Services

const locationSvc = new LocationService({
  settings,
  send,
  isConnected,
  getLang: getLanguage,
  t,
});
locationSvc.addEventListener('change', () => renderLocation());

const sos = new SosController({
  els: {
    dialog: $('sos-dialog'), title: $('sos-title'), reason: $('sos-reason'), live: $('sos-live'),
    countdownPart: $('sos-countdown'), count: $('sos-count'), countText: $('sos-count-text'),
    hide: $('sos-hide'), demoCancel: $('sos-demo-cancel'),
    sentPart: $('sos-sent'), call: $('sos-call'), callText: $('sos-call-text'), sms: $('sos-sms'),
    sound: $('sos-sound'), ok: $('sos-ok'), loc: $('sos-loc'), map: $('sos-map'), mapWrap: $('sos-map-wrap'),
    guardians: $('sos-guardians'),
  },
  settings,
  location: locationSvc,
  send,
  t,
  getLang: getLanguage,
  isDemo: () => !!(app.transport && app.transport.isDemo),
  isIOS: !!support.isIOS,
  announce,
  onDemoCancel: () => app.transport && app.transport.pressButton && app.transport.pressButton(),
  onClosed: () => focusHeading(app.route),
});

// ---------------------------------------------------------------------------------------------
// Screens and navigation

const SCREENS = ['connect', 'live', 'settings'];

function normalizeRoute(route) {
  if (route === 'settings') return 'settings';
  return app.transport ? 'live' : 'connect';
}

function focusHeading(route, focusId) {
  const el = (focusId && $(focusId)) || $(`h-${route}`);
  if (el) el.focus();
}

function show(route, { focus = true, focusId = null } = {}) {
  const changed = app.route !== route;
  app.route = route;
  for (const name of SCREENS) $(`screen-${name}`).hidden = name !== route;
  for (const btn of document.querySelectorAll('.nav-btn')) {
    const current = btn.dataset.nav === 'settings' ? route === 'settings' : route !== 'settings';
    if (current) btn.setAttribute('aria-current', 'page');
    else btn.removeAttribute('aria-current');
  }
  document.title = `${t(`screen.${route}`)} · ${t('app.name')}`;
  if (focus && (changed || focusId)) {
    window.scrollTo(0, 0);
    focusHeading(route, focusId);
  }
}

function go(route, { replace = false, focus = true, focusId = null } = {}) {
  const target = normalizeRoute(route);
  const hash = `#${target}`;
  if (location.hash !== hash) {
    if (replace) history.replaceState(null, '', hash);
    else history.pushState(null, '', hash);
  }
  show(target, { focus, focusId });
}

window.addEventListener('popstate', () => {
  const target = normalizeRoute(location.hash.slice(1));
  if (`#${target}` !== location.hash) history.replaceState(null, '', `#${target}`);
  show(target);
});

// ---------------------------------------------------------------------------------------------
// Connection

function attach(transport) {
  app.transport = transport;
  transport.addEventListener('state', (e) => { if (e.target === app.transport) onState(e.detail); });
  transport.addEventListener('message', (e) => { if (e.target === app.transport) onMessage(e.detail); });
  transport.addEventListener('ignored', (e) => console.debug('[owsh] ignored message', e.detail));
  transport.addEventListener('error', (e) => {
    const error = e.detail && e.detail.error;
    console.warn('[owsh] link error', error);
    if (e.target === app.transport && isAuthError(error)) showLinkError(t('connect.error.auth'));
  });
}

function setConnectError(text) {
  $('connect-error').textContent = text || '';
}

/** Shown on both the connect and live screens (role="alert"); not repeated while unchanged. */
function showLinkError(text) {
  for (const id of ['connect-error', 'link-error']) {
    const el = $(id);
    if (el.textContent !== text) el.textContent = text;
  }
}

function describeConnectError(err) {
  const msg = String((err && err.message) || err || '');
  if (isAuthError(err)) return t('connect.error.auth');
  if (err && err.code === 'not_owsh') return t('connect.error.notOwsh');
  if (err && err.name === 'NotFoundError') {
    return /adapter|bluetooth.*(off|unavailable|not available)/i.test(msg) ? t('connect.noAdapter') : t('connect.error.cancelled');
  }
  if (err && (err.name === 'SecurityError' || err.name === 'NotAllowedError')) return t('connect.error.security');
  return t('connect.error.generic', { detail: msg || 'unknown error' });
}

async function connectHelmet() {
  sos.primeAudio(); // user gesture: allow the SOS alarm to sound later
  setConnectError('');
  if (!support.supported) {
    $('ble-support').hidden = false;
    announce($('ble-support-text').textContent, true);
    return;
  }
  if (app.transport) app.transport.disconnect();
  const ble = new BleTransport();
  attach(ble);
  try {
    await ble.connect();
  } catch (err) {
    console.warn('[owsh] connect failed', err);
    if (app.transport === ble) app.transport = null;
    app.connState = 'disconnected';
    renderConnection();
    setConnectError(describeConnectError(err));
  }
}

function startDemo() {
  sos.primeAudio();
  setConnectError('');
  if (app.transport) app.transport.disconnect();
  const demo = new DemoHelmet({ lang: getLanguage() });
  attach(demo);
  demo.connect();
}

function onState({ state, name, attempt }) {
  const previous = app.connState;
  app.connState = state;
  app.attempt = attempt || 0;
  if (state === 'connected') {
    if (previous === 'reconnecting') announce(t('announce.reconnected'), true);
    else {
      go('live');
      announce(t('announce.connected', { name }));
    }
    app.staleAnnounced = false;
    $('link-error').textContent = '';
    flushCfg();
  } else if (state === 'reconnecting' && previous === 'connected') {
    announce(t('announce.lost'), true);
    try { navigator.vibrate && navigator.vibrate([200, 100, 200]); } catch { /* unsupported */ }
  } else if (state === 'disconnected') {
    app.transport = null;
    app.hello = null;
    app.status = null;
    app.statusAt = 0;
    app.undervoltageAnnounced = false;
    $('demo-fault').setAttribute('aria-pressed', 'false');
    $('demo-pause').setAttribute('aria-pressed', 'false');
    if (previous !== 'disconnected') announce(t('announce.disconnected'));
    if (app.route === 'live') go('connect', { replace: true });
  }
  locationSvc.update();
  updateWakeLock();
  renderConnection();
  renderStatus();
  renderLocation();
}

function onMessage(msg) {
  switch (msg.t) {
    case 'hello':
      app.hello = msg;
      renderStatus();
      break;
    case 'status':
      app.status = msg;
      app.statusAt = Date.now();
      app.staleAnnounced = false;
      if (typeof msg.muted === 'boolean' && msg.muted !== settings.get('helmetMuted') && !('muted' in app.pendingCfg)) {
        settings.set({ helmetMuted: msg.muted }); // reflect helmet's own mute button (B3 double press)
      }
      // undervoltage/throttled are optional booleans (omitted when unknown). Announce low power
      // once when it becomes true; re-arm only after the helmet reports false.
      if (msg.undervoltage === true && !app.undervoltageAnnounced) {
        app.undervoltageAnnounced = true;
        announce(t('status.undervoltageOn'));
      } else if (msg.undervoltage === false) {
        app.undervoltageAnnounced = false;
      }
      renderStatus();
      break;
    case 'alert':
      addLog({ type: 'alert', level: msg.level, kind: msg.kind, dir: msg.dir, dist: msg.dist_m, text: msg.text });
      break;
    case 'speech':
      addLog({ type: 'speech', level: msg.level, text: msg.text });
      break;
    case 'sos':
      sos.handle(msg);
      addLog({ type: 'sos', level: msg.state === 'cancelled' ? 2 : 0, key: `log.sos.${msg.state}` }, { announce: false });
      break;
    case 'need_location':
      addLog({ type: 'info', level: 3, key: 'loc.needLocationLog' });
      locationSvc.handleNeedLocation();
      break;
    default:
      break; // pong and future types: nothing to show
  }
}

// ---------------------------------------------------------------------------------------------
// Helmet configuration

async function sendCfg(fields) {
  if (isConnected()) {
    try {
      await send(makeCfg(fields));
      for (const key of Object.keys(fields)) delete app.pendingCfg[key];
      setSettingsStatus(t('settings.sentToHelmet'));
      return;
    } catch (err) {
      console.warn('[owsh] cfg send failed', err);
    }
  }
  Object.assign(app.pendingCfg, fields);
  setSettingsStatus(t('settings.savedPending'));
}

function flushCfg() {
  const fields = { ...app.pendingCfg };
  if (!Object.keys(fields).length) return;
  send(makeCfg(fields)).then(() => {
    for (const key of Object.keys(fields)) delete app.pendingCfg[key];
  }).catch((err) => console.warn('[owsh] pending cfg not sent', err));
}

// ---------------------------------------------------------------------------------------------
// Screen wake lock (phones pause web apps when the screen is off)

async function updateWakeLock() {
  const want = settings.get('keepAwake') && !!app.transport && document.visibilityState === 'visible';
  if (want && !app.wakeLock && !app.wakePending && navigator.wakeLock) {
    app.wakePending = true;
    try {
      const lock = await navigator.wakeLock.request('screen');
      app.wakeLock = lock;
      lock.addEventListener('release', () => { if (app.wakeLock === lock) app.wakeLock = null; });
    } catch { /* denied or unsupported */ }
    app.wakePending = false;
    if (!(settings.get('keepAwake') && app.transport) && app.wakeLock) updateWakeLock();
  } else if (!want && app.wakeLock) {
    const lock = app.wakeLock;
    app.wakeLock = null;
    try { await lock.release(); } catch { /* already released */ }
  }
}
document.addEventListener('visibilitychange', updateWakeLock);

// ---------------------------------------------------------------------------------------------
// Rendering

const timeFormat = (options = { hour: '2-digit', minute: '2-digit', second: '2-digit' }) => new Intl.DateTimeFormat(getLanguage(), options);

function countryName(code) {
  if (code === 'EU' || code === 'OTHER') return t(`country.${code}`);
  try {
    return new Intl.DisplayNames([getLanguage()], { type: 'region' }).of(code) || code;
  } catch {
    return code;
  }
}

function numbersText(preset) {
  return preset.numbers
    .map((n) => `${n.number} ${n.services.map((s) => t(`service.${s}`)).join('/')}`)
    .join(', ');
}

function renderSupport() {
  const box = $('ble-support');
  const button = $('btn-connect');
  if (!support.supported) {
    box.hidden = false;
    $('ble-support-text').textContent = t(`connect.unsupported.${support.reason}`);
    button.setAttribute('aria-disabled', 'true');
    button.setAttribute('aria-describedby', 'ble-support-text');
  } else if (!app.adapterAvailable) {
    box.hidden = false;
    $('ble-support-text').textContent = t('connect.noAdapter');
  } else {
    box.hidden = true;
    button.removeAttribute('aria-disabled');
    button.removeAttribute('aria-describedby');
  }
}

function renderEmergencySummary() {
  const code = settings.get('country');
  $('emergency-summary').textContent = t('connect.emergencySummary', {
    number: settings.get('emergencyNumber'),
    country: countryName(code),
  });
}

function renderConnection() {
  const tr = app.transport;
  const state = tr ? app.connState : 'disconnected';
  const pill = $('conn-pill');
  pill.dataset.state = state;
  $('conn-pill-text').textContent = t(`conn.${state}`);
  $('conn-state').textContent = t(`live.state.${state}`, { name: tr ? tr.name : '', attempt: app.attempt });
  $('btn-disconnect').hidden = !tr;
  $('demo-badge').hidden = !(tr && tr.isDemo);
  $('demo-controls').hidden = !(tr && tr.isDemo);
}

function formatUptime(seconds) {
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return t('status.hoursMinutes', { h, m });
  if (m > 0) return t('status.minutes', { m });
  return t('status.seconds', { s });
}

function faultName(id) {
  const key = `fault.${id}`;
  return has(key) ? t(key) : t('fault.unknown', { id });
}

function renderStatus() {
  const s = app.status;
  const dd = (id, text) => { $(id).textContent = text; };
  const faultsEl = $('st-faults');
  faultsEl.textContent = '';
  const warning = $('status-warning');
  warning.hidden = true;
  warning.textContent = '';

  $('st-fw').textContent = app.hello && app.hello.fw ? String(app.hello.fw) : '–';
  const flag = (row, value, onKey, offKey) => {
    $(`${row}-row`).hidden = typeof value !== 'boolean'; // omitted = unknown: hide the row
    $(row).textContent = value === true ? `⚠ ${t(onKey)}` : value === false ? t(offKey) : '';
  };
  flag('st-power', s && s.undervoltage, 'status.undervoltageOn', 'status.undervoltageOff');
  flag('st-thermal', s && s.throttled, 'status.throttledOn', 'status.throttledOff');
  if (!s) {
    faultsEl.textContent = app.transport ? t('status.waiting') : '–';
    for (const id of ['st-fps', 'st-temp', 'st-voice', 'st-uptime', 'st-updated']) dd(id, '–');
    return;
  }
  const faults = Array.isArray(s.faults) ? s.faults : [];
  if (faults.length === 0) {
    faultsEl.textContent = t('status.noFaults');
  } else {
    const ul = document.createElement('ul');
    ul.className = 'fault-list';
    for (const f of faults) {
      const li = document.createElement('li');
      li.textContent = faultName(String(f));
      ul.append(li);
    }
    faultsEl.append(ul);
  }
  dd('st-fps', typeof s.fps === 'number' ? t('status.fpsValue', { fps: s.fps.toFixed(1) }) : t('status.unknown'));
  if (typeof s.cpu_temp_c === 'number') {
    const temp = s.cpu_temp_c.toFixed(0);
    dd('st-temp', s.cpu_temp_c >= 80 ? t('status.tempHot', { temp }) : t('status.tempValue', { temp }));
  } else dd('st-temp', t('status.unknown'));
  dd('st-voice', s.muted === true ? t('status.voiceMuted') : s.muted === false ? t('status.voiceOn') : t('status.unknown'));
  dd('st-uptime', typeof s.uptime_s === 'number' ? formatUptime(s.uptime_s) : t('status.unknown'));

  const age = Math.round((Date.now() - app.statusAt) / 1000);
  dd('st-updated', age < 3 ? t('status.justNow') : t('status.secondsAgo', { s: age }));
  const messages = [];
  if (faults.length) messages.push(t('status.faultWarning'));
  if (s.undervoltage === true) messages.push(t('status.undervoltageOn'));
  if (s.throttled === true) messages.push(t('status.throttledOn'));
  if (app.transport && age > STATUS_STALE_S) messages.push(t('status.stale', { s: age }));
  if (messages.length) {
    warning.hidden = false;
    warning.textContent = `⚠ ${messages.join(' ')}`;
  }
}

function renderLocation() {
  const st = locationSvc.state;
  let main;
  let detail = '';
  if (!settings.get('shareLocation')) main = t('loc.off');
  else if (!isConnected()) main = t('loc.notConnected');
  else if (st.error === 'denied') main = t('loc.denied');
  else if (st.error === 'unsupported') main = t('loc.unsupported');
  else if (!st.lastSentAt) main = st.error === 'unavailable' ? t('loc.unavailable') : t('loc.waiting');
  else {
    main = t('loc.sharing');
    const parts = [];
    if (st.lastFix) {
      parts.push(t('loc.lastSent', {
        time: timeFormat().format(st.lastSentAt),
        acc: Math.round(st.lastFix.acc),
      }));
    }
    if (st.lastAddr) parts.push(t('loc.lastSentAddr', { addr: st.lastAddr }));
    if (st.error === 'stale') parts.push(t('loc.stale'));
    detail = parts.join(' ');
  }
  $('loc-state').textContent = main;
  $('loc-detail').textContent = detail;
}

// ----- log -------------------------------------------------------------------------------------

function entryText(entry) {
  return entry.key ? t(entry.key) : entry.text;
}

function levelName(level) {
  return t(`level.${level}`);
}

function renderLogItem(entry) {
  const li = document.createElement('li');
  li.className = 'log-item';
  li.dataset.level = String(entry.level);
  li.dataset.id = String(entry.id);

  const head = document.createElement('p');
  head.className = 'log-head';
  const badge = document.createElement('span');
  badge.className = 'level-badge';
  const symbol = document.createElement('span');
  symbol.setAttribute('aria-hidden', 'true');
  symbol.textContent = `${LEVEL_SYMBOLS[entry.level] || '•'} `;
  badge.append(symbol, document.createTextNode(levelName(entry.level)));
  const sep = document.createElement('span');
  sep.className = 'visually-hidden';
  sep.textContent = ': ';
  const text = document.createElement('span');
  text.className = 'log-text';
  text.textContent = entryText(entry);
  head.append(badge, sep, text);

  const meta = document.createElement('p');
  meta.className = 'log-meta';
  const bits = [];
  if (entry.kind && has(`kind.${entry.kind}`)) bits.push(t(`kind.${entry.kind}`));
  if (entry.dir && has(`dir.${entry.dir}`)) bits.push(t(`dir.${entry.dir}`));
  if (typeof entry.dist === 'number') bits.push(t('log.distance', { d: entry.dist.toFixed(1) }));
  const time = document.createElement('time');
  time.dateTime = new Date(entry.at).toISOString();
  time.textContent = timeFormat().format(entry.at);
  meta.append(document.createTextNode(bits.length ? `${bits.join(' · ')} · ` : ''), time);

  li.append(head, meta);
  return li;
}

function renderLogSummary() {
  $('log-summary').textContent = app.log.length ? t('log.count', { count: app.log.length }) : t('log.empty');
}

function rerenderLog() {
  const list = $('log');
  list.replaceChildren(...app.log.map(renderLogItem));
  renderLogSummary();
}

/** The helmet sends both `alert` and `speech` for one event; show and announce it once. */
function findMergeCandidate(entry) {
  if (!entry.text || (entry.type !== 'alert' && entry.type !== 'speech')) return null;
  const now = Date.now();
  return app.log.find((e) => now - e.at <= MERGE_WINDOW_MS && e.text === entry.text
    && e.type !== entry.type && (e.type === 'alert' || e.type === 'speech')) || null;
}

function addLog(entry, { announce: shouldAnnounce = true } = {}) {
  const twin = findMergeCandidate(entry);
  if (twin) {
    if (entry.type === 'alert') {
      Object.assign(twin, { type: 'alert', kind: entry.kind, dir: entry.dir, dist: entry.dist, level: entry.level });
      const old = $('log').querySelector(`[data-id="${twin.id}"]`);
      if (old) old.replaceWith(renderLogItem(twin));
    }
    return;
  }
  entry.at = Date.now();
  entry.id = ++app.logSeq;
  app.log.unshift(entry);
  const list = $('log');
  list.prepend(renderLogItem(entry));
  while (app.log.length > LOG_LIMIT) {
    const removed = app.log.pop();
    const el = list.querySelector(`[data-id="${removed.id}"]`);
    if (el) el.remove();
  }
  renderLogSummary();
  if (shouldAnnounce && settings.get('announceMessages')) {
    const level = Number.isInteger(entry.level) ? entry.level : 3;
    announce(`${levelName(level)}: ${entryText(entry)}`, level <= 1);
  }
}

// ----- settings form -----------------------------------------------------------------------------

function buildCountryOptions() {
  const select = $('set-country');
  const options = COUNTRY_PRESETS.map((preset) => {
    const opt = document.createElement('option');
    opt.value = preset.code;
    opt.textContent = preset.code === 'OTHER'
      ? t('country.OTHER')
      : t('settings.presetOption', { country: countryName(preset.code), numbers: numbersText(preset) });
    return opt;
  });
  const others = options.pop();
  options.sort((a, b) => a.textContent.localeCompare(b.textContent, getLanguage()));
  select.replaceChildren(...options, others);
  select.value = settings.get('country');
}

function renderEmergencyOther() {
  const preset = findPreset(settings.get('country'));
  $('set-emergency-other').textContent = settings.get('country') === 'OTHER'
    ? t('settings.emergencyOtherCountry')
    : t('settings.emergencyOther', { list: numbersText(preset) });
}

function syncForm() {
  const s = settings.all();
  $('set-lang').value = s.lang;
  $('set-country').value = s.country;
  if (document.activeElement !== $('set-emergency')) $('set-emergency').value = s.emergencyNumber;
  document.querySelectorAll('.guardian').forEach((input) => {
    if (document.activeElement !== input) input.value = s.guardians[Number(input.dataset.index)] || '';
  });
  $('set-muted').checked = s.helmetMuted;
  $('set-volume').value = String(s.helmetVolume);
  renderVolume();
  for (const radio of document.querySelectorAll('input[name="dropoff"]')) radio.checked = radio.value === s.dropoffSensitivity;
  $('set-share').checked = s.shareLocation;
  $('set-geocode').checked = s.reverseGeocode;
  $('set-wake').checked = s.keepAwake;
  $('announce-toggle').checked = s.announceMessages;
  renderEmergencyOther();
}

function renderVolume() {
  const v = Number($('set-volume').value);
  $('set-volume-out').textContent = `${v}%`;
  $('set-volume').setAttribute('aria-valuetext', t('settings.volumeValue', { v }));
}

function renderAll() {
  show(app.route, { focus: false });
  renderSupport();
  renderEmergencySummary();
  renderConnection();
  renderStatus();
  renderLocation();
  rerenderLog();
  buildCountryOptions();
  syncForm();
  sos.refresh();
}

settings.addEventListener('change', async (e) => {
  const { changed } = e.detail;
  if (changed.includes('lang')) {
    await setLanguage(settings.get('lang'));
    renderAll();
  }
  if (changed.includes('shareLocation') || changed.includes('reverseGeocode')) {
    locationSvc.update();
    renderLocation();
  }
  if (changed.includes('keepAwake')) updateWakeLock();
  if (changed.includes('country') || changed.includes('emergencyNumber')) renderEmergencySummary();
  syncForm();
});

// ---------------------------------------------------------------------------------------------
// Events

function wireEvents() {
  $('btn-connect').addEventListener('click', connectHelmet);
  $('btn-demo').addEventListener('click', startDemo);
  $('btn-disconnect').addEventListener('click', () => app.transport && app.transport.disconnect());

  for (const btn of document.querySelectorAll('[data-nav]')) {
    btn.addEventListener('click', () => go(btn.dataset.nav, { focusId: btn.dataset.focus || null }));
  }

  // demo controls
  const demo = () => (app.transport && app.transport.isDemo ? app.transport : null);
  $('demo-sos').addEventListener('click', () => { sos.primeAudio(); demo() && demo().triggerSos('button'); });
  $('demo-fall').addEventListener('click', () => { sos.primeAudio(); demo() && demo().triggerSos('fall'); });
  $('demo-where').addEventListener('click', () => demo() && demo().whereAmI());
  $('demo-fault').addEventListener('click', (e) => {
    if (!demo()) return;
    e.currentTarget.setAttribute('aria-pressed', String(demo().toggleCameraFault()));
  });
  $('demo-pause').addEventListener('click', (e) => {
    if (!demo()) return;
    const paused = e.currentTarget.getAttribute('aria-pressed') !== 'true';
    demo().setPaused(paused);
    e.currentTarget.setAttribute('aria-pressed', String(paused));
  });

  // log
  $('announce-toggle').addEventListener('change', (e) => settings.set({ announceMessages: e.target.checked }));
  $('btn-clear-log').addEventListener('click', () => {
    app.log = [];
    rerenderLog();
    announce(t('log.cleared'));
  });

  // settings
  $('settings-form').addEventListener('submit', (e) => e.preventDefault());
  $('set-lang').addEventListener('change', (e) => settings.set({ lang: e.target.value }));
  $('set-country').addEventListener('change', (e) => {
    const preset = findPreset(e.target.value);
    settings.set({ country: preset.code, emergencyNumber: preset.numbers[0].number });
    $('set-emergency').value = settings.get('emergencyNumber');
    setEmergencyError('');
    setSettingsStatus(t('settings.savedNumber', { number: settings.get('emergencyNumber') }));
  });
  $('set-emergency').addEventListener('change', (e) => {
    const number = sanitizePhone(e.target.value);
    if (!number) {
      setEmergencyError(t('settings.emergencyInvalid'));
      return;
    }
    setEmergencyError('');
    settings.set({ emergencyNumber: number });
    e.target.value = number;
    setSettingsStatus(t('settings.savedNumber', { number }));
  });
  for (const input of document.querySelectorAll('.guardian')) {
    input.addEventListener('change', () => {
      const guardians = settings.get('guardians');
      guardians[Number(input.dataset.index)] = input.value.trim();
      settings.set({ guardians });
      setSettingsStatus(t('settings.saved'));
    });
  }
  $('set-muted').addEventListener('change', (e) => {
    settings.set({ helmetMuted: e.target.checked });
    sendCfg({ muted: e.target.checked });
  });
  $('set-volume').addEventListener('input', renderVolume);
  $('set-volume').addEventListener('change', (e) => {
    const volume = Number(e.target.value);
    settings.set({ helmetVolume: volume });
    sendCfg({ volume });
  });
  for (const radio of document.querySelectorAll('input[name="dropoff"]')) {
    radio.addEventListener('change', () => {
      if (!radio.checked) return;
      settings.set({ dropoffSensitivity: radio.value });
      sendCfg({ dropoff_sensitivity: radio.value });
    });
  }
  $('btn-test-voice').addEventListener('click', async () => {
    if (!isConnected()) {
      setSettingsStatus(t('settings.notConnected'));
      return;
    }
    try {
      const sent = await send(makeSay(t('settings.testVoiceText'), 2));
      setSettingsStatus(sent === false ? t('settings.sayTooSoon') : t('settings.testVoiceSent'));
    } catch {
      setSettingsStatus(t('settings.notConnected'));
    }
  });
  $('set-share').addEventListener('change', (e) => settings.set({ shareLocation: e.target.checked }));
  $('set-geocode').addEventListener('change', (e) => settings.set({ reverseGeocode: e.target.checked }));
  $('set-wake').addEventListener('change', (e) => settings.set({ keepAwake: e.target.checked }));
}

function setEmergencyError(text) {
  const input = $('set-emergency');
  $('set-emergency-error').textContent = text;
  if (text) input.setAttribute('aria-invalid', 'true');
  else input.removeAttribute('aria-invalid');
}

function tick() {
  if (app.status) {
    renderStatus();
    const age = (Date.now() - app.statusAt) / 1000;
    if (isConnected() && age > STATUS_STALE_S && !app.staleAnnounced) {
      app.staleAnnounced = true;
      announce(t('status.stale', { s: Math.round(age) }), true);
    }
  }
}

async function checkAdapter() {
  if (!support.supported || !navigator.bluetooth.getAvailability) return;
  try {
    app.adapterAvailable = await navigator.bluetooth.getAvailability();
    renderSupport();
  } catch { /* not implemented everywhere */ }
}

function registerServiceWorker() {
  if (!('serviceWorker' in navigator) || !window.isSecureContext) return;
  navigator.serviceWorker.register('./sw.js').catch((err) => console.warn('[owsh] service worker not registered', err));
}

async function init() {
  await setLanguage(settings.get('lang'));
  wireEvents();
  const initial = normalizeRoute(location.hash.slice(1));
  if (location.hash && location.hash !== `#${initial}`) history.replaceState(null, '', `#${initial}`);
  app.route = initial;
  renderAll();
  checkAdapter();
  setInterval(tick, 5000);
  registerServiceWorker();
}

init();
