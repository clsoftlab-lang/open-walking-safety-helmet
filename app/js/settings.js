// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// Settings stored on this phone only (localStorage, every access wrapped in try/catch; falls back
// to memory when storage is blocked, e.g. private mode). Emergency numbers are per-country
// presets that the user can edit; nothing is hard-coded to one country (spec global rules).

const STORAGE_KEY = 'owsh.settings.v1';

/**
 * Country presets. The first number is filled in as "number to call"; the user can edit it.
 * services: ambulance | fire | police | all. Always tell users to verify for their area.
 */
export const COUNTRY_PRESETS = Object.freeze([
  { code: 'KR', numbers: [{ number: '119', services: ['ambulance', 'fire'] }, { number: '112', services: ['police'] }] },
  { code: 'US', numbers: [{ number: '911', services: ['all'] }] },
  { code: 'CA', numbers: [{ number: '911', services: ['all'] }] },
  { code: 'MX', numbers: [{ number: '911', services: ['all'] }] },
  { code: 'BR', numbers: [{ number: '192', services: ['ambulance'] }, { number: '193', services: ['fire'] }, { number: '190', services: ['police'] }] },
  { code: 'EU', numbers: [{ number: '112', services: ['all'] }] },
  { code: 'GB', numbers: [{ number: '999', services: ['all'] }, { number: '112', services: ['all'] }] },
  { code: 'IE', numbers: [{ number: '112', services: ['all'] }, { number: '999', services: ['all'] }] },
  { code: 'TR', numbers: [{ number: '112', services: ['all'] }] },
  { code: 'RU', numbers: [{ number: '112', services: ['all'] }, { number: '103', services: ['ambulance'] }] },
  { code: 'IN', numbers: [{ number: '112', services: ['all'] }, { number: '108', services: ['ambulance'] }] },
  { code: 'JP', numbers: [{ number: '119', services: ['ambulance', 'fire'] }, { number: '110', services: ['police'] }] },
  { code: 'CN', numbers: [{ number: '120', services: ['ambulance'] }, { number: '119', services: ['fire'] }, { number: '110', services: ['police'] }] },
  { code: 'TW', numbers: [{ number: '119', services: ['ambulance', 'fire'] }, { number: '110', services: ['police'] }] },
  { code: 'HK', numbers: [{ number: '999', services: ['all'] }] },
  { code: 'SG', numbers: [{ number: '995', services: ['ambulance', 'fire'] }, { number: '999', services: ['police'] }] },
  { code: 'PH', numbers: [{ number: '911', services: ['all'] }] },
  { code: 'VN', numbers: [{ number: '115', services: ['ambulance'] }, { number: '114', services: ['fire'] }, { number: '113', services: ['police'] }] },
  { code: 'TH', numbers: [{ number: '1669', services: ['ambulance'] }, { number: '191', services: ['police'] }] },
  { code: 'ID', numbers: [{ number: '112', services: ['all'] }] },
  { code: 'AU', numbers: [{ number: '000', services: ['all'] }, { number: '112', services: ['all'] }] },
  { code: 'NZ', numbers: [{ number: '111', services: ['all'] }] },
  { code: 'ZA', numbers: [{ number: '10177', services: ['ambulance', 'fire'] }, { number: '10111', services: ['police'] }, { number: '112', services: ['all'] }] },
  { code: 'KE', numbers: [{ number: '999', services: ['all'] }, { number: '112', services: ['all'] }] },
  { code: 'NG', numbers: [{ number: '112', services: ['all'] }] },
  { code: 'OTHER', numbers: [{ number: '112', services: ['all'] }] },
]);

const EUROPE_112 = new Set(['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IT',
  'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'NO', 'IS', 'LI', 'CH']);

export function findPreset(code) {
  return COUNTRY_PRESETS.find((p) => p.code === code) || COUNTRY_PRESETS[COUNTRY_PRESETS.length - 1];
}

// Languages spoken mainly in one preset country; used when a tag has no region ("ko").
const LANGUAGE_COUNTRY = { ko: 'KR', ja: 'JP' };

/**
 * Guess the country from browser languages in preference order (e.g. ["ko", "en-US"] -> KR).
 * Only a guess: the UI always shows the number and asks the user to check it. Falls back to OTHER (112).
 */
export function guessCountry(languages = []) {
  for (const tag of languages) {
    const parts = String(tag).split(/[-_]/);
    const region = parts.slice(1).find((p) => /^[A-Za-z]{2}$/.test(p));
    if (region) {
      const code = region.toUpperCase();
      if (COUNTRY_PRESETS.some((p) => p.code === code)) return code;
      if (EUROPE_112.has(code)) return 'EU';
    }
    const byLanguage = LANGUAGE_COUNTRY[parts[0].toLowerCase()];
    if (byLanguage) return byLanguage;
  }
  return 'OTHER';
}

/** Keep digits, and a leading "+". */
export function sanitizePhone(value) {
  const text = String(value || '').trim();
  const digits = text.replace(/[^0-9]/g, '');
  if (!digits) return '';
  return (text.startsWith('+') ? '+' : '') + digits;
}

export function defaultSettings(languages = globalThis.navigator ? navigator.languages || [navigator.language] : []) {
  const country = guessCountry(languages);
  return {
    lang: 'system',
    country,
    emergencyNumber: findPreset(country).numbers[0].number,
    guardians: ['', '', ''],
    helmetMuted: false,
    helmetVolume: 80,
    dropoffSensitivity: 'normal',
    shareLocation: false,
    reverseGeocode: false, // privacy: off by default
    keepAwake: true,
    announceMessages: true,
  };
}

export function sanitizeSettings(raw, defaults = defaultSettings()) {
  const s = { ...defaults };
  if (!raw || typeof raw !== 'object') return s;
  if (['system', 'en', 'ko'].includes(raw.lang)) s.lang = raw.lang;
  if (COUNTRY_PRESETS.some((p) => p.code === raw.country)) s.country = raw.country;
  if (typeof raw.emergencyNumber === 'string' && sanitizePhone(raw.emergencyNumber)) s.emergencyNumber = sanitizePhone(raw.emergencyNumber);
  if (Array.isArray(raw.guardians)) s.guardians = [0, 1, 2].map((i) => (typeof raw.guardians[i] === 'string' ? raw.guardians[i].slice(0, 32) : ''));
  if (typeof raw.helmetMuted === 'boolean') s.helmetMuted = raw.helmetMuted;
  if (Number.isInteger(raw.helmetVolume) && raw.helmetVolume >= 0 && raw.helmetVolume <= 100) s.helmetVolume = raw.helmetVolume;
  if (['low', 'normal', 'high'].includes(raw.dropoffSensitivity)) s.dropoffSensitivity = raw.dropoffSensitivity;
  for (const key of ['shareLocation', 'reverseGeocode', 'keepAwake', 'announceMessages']) {
    if (typeof raw[key] === 'boolean') s[key] = raw[key];
  }
  return s;
}

function createStorage() {
  const memory = new Map();
  let local = null;
  try {
    local = globalThis.localStorage;
    const probe = '__owsh_probe__';
    local.setItem(probe, '1');
    local.removeItem(probe);
  } catch {
    local = null;
  }
  return {
    persistent: !!local,
    get(key) {
      try { if (local) return local.getItem(key); } catch { /* fall through */ }
      return memory.has(key) ? memory.get(key) : null;
    },
    set(key, value) {
      memory.set(key, value);
      try { if (local) local.setItem(key, value); } catch { /* quota or blocked: memory only */ }
    },
  };
}

/** Emits "change" with detail {changed: string[], settings}. */
export class Settings extends EventTarget {
  constructor(storage = createStorage()) {
    super();
    this.storage = storage;
    let raw = null;
    try { raw = JSON.parse(storage.get(STORAGE_KEY) || 'null'); } catch { raw = null; }
    this.values = sanitizeSettings(raw);
  }

  get(key) {
    const value = this.values[key];
    return Array.isArray(value) ? [...value] : value;
  }

  all() {
    return { ...this.values, guardians: [...this.values.guardians] };
  }

  set(patch) {
    const next = sanitizeSettings({ ...this.values, ...patch }, this.values);
    const changed = Object.keys(next).filter((k) => JSON.stringify(next[k]) !== JSON.stringify(this.values[k]));
    if (changed.length === 0) return changed;
    this.values = next;
    try { this.storage.set(STORAGE_KEY, JSON.stringify(next)); } catch { /* ignore */ }
    this.dispatchEvent(new CustomEvent('change', { detail: { changed, settings: this.all() } }));
    return changed;
  }
}
