// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// Location sharing (spec §8.2 "loc"): while connected and enabled, watch geolocation and send
// `loc` every 10 s, and immediately when the helmet sends `need_location`.
// Optional reverse geocoding (OFF by default) uses OpenStreetMap Nominatim and follows its usage
// policy: at most 1 request per 30 s from this app, results cached, the app identified by the
// browser's Referer (browsers do not allow setting User-Agent), attribution shown in Settings.

import { makeLoc, makeSay } from './protocol.js';

export const SEND_INTERVAL_MS = 10000;
export const MAX_FIX_AGE_MS = 60000; // never send a fix older than this as "current"
export const NOMINATIM_MIN_INTERVAL_MS = 30000;
export const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse';

/** Distance in metres between two lat/lon points (haversine). */
export function distanceM(a, b) {
  const R = 6371000;
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLon = (b.lon - a.lon) * rad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function osmMapUrl(lat, lon) {
  const la = lat.toFixed(6);
  const lo = lon.toFixed(6);
  return `https://www.openstreetmap.org/?mlat=${la}&mlon=${lo}#map=18/${la}/${lo}`;
}

/** Shorten Nominatim's display_name ("house, road, district, city, postcode, country"). */
export function shortAddress(displayName) {
  if (typeof displayName !== 'string') return null;
  const parts = displayName.split(',').map((s) => s.trim()).filter(Boolean);
  const text = parts.slice(0, 4).join(', ');
  return text ? text.slice(0, 200) : null;
}

export class ReverseGeocoder {
  constructor({ fetchImpl = (...a) => globalThis.fetch(...a), now = () => Date.now(), minIntervalMs = NOMINATIM_MIN_INTERVAL_MS } = {}) {
    this.fetchImpl = fetchImpl;
    this.now = now;
    this.minIntervalMs = minIntervalMs;
    this.lastRequestAt = -Infinity;
    this.cached = null; // {lat, lon, addr, lang}
    this.inflight = null;
  }

  /** Cached address if it was looked up within `radiusM` of this point. */
  cachedFor(point, lang, radiusM = 50) {
    if (this.cached && this.cached.lang === lang && distanceM(this.cached, point) <= radiusM) return this.cached.addr;
    return null;
  }

  canRequest() {
    return this.now() - this.lastRequestAt >= this.minIntervalMs;
  }

  /** Returns an address string or null. Never makes more than one request per interval. */
  async lookup(point, lang) {
    const near = this.cachedFor(point, lang, 25);
    if (near) return near;
    if (this.inflight) return this.inflight;
    if (!this.canRequest()) return this.cachedFor(point, lang, 50);
    this.lastRequestAt = this.now();
    const url = `${NOMINATIM_URL}?format=jsonv2&lat=${point.lat.toFixed(6)}&lon=${point.lon.toFixed(6)}`
      + `&zoom=18&addressdetails=0&accept-language=${encodeURIComponent(lang)}`;
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 8000) : null;
    this.inflight = (async () => {
      try {
        const response = await this.fetchImpl(url, {
          signal: controller ? controller.signal : undefined,
          credentials: 'omit',
          referrerPolicy: 'strict-origin-when-cross-origin',
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) return null;
        const data = await response.json();
        const addr = shortAddress(data && data.display_name);
        if (addr) this.cached = { lat: point.lat, lon: point.lon, addr, lang };
        return addr;
      } catch {
        return null;
      } finally {
        if (timer) clearTimeout(timer);
        this.inflight = null;
      }
    })();
    return this.inflight;
  }
}

/**
 * Emits "change" whenever its public `state` changes:
 * {active, lastFix, lastSentAt, lastAddr, error: null|'denied'|'unavailable'|'unsupported'|'stale'}
 */
export class LocationService extends EventTarget {
  constructor({ settings, send, isConnected, getLang, t, geolocation = globalThis.navigator && navigator.geolocation, geocoder = new ReverseGeocoder() }) {
    super();
    this.settings = settings;
    this.send = send;
    this.isConnected = isConnected;
    this.getLang = getLang;
    this.t = t;
    this.geolocation = geolocation;
    this.geocoder = geocoder;
    this.watchId = null;
    this.timer = null;
    this.state = { active: false, lastFix: null, lastSentAt: null, lastAddr: null, error: null };
  }

  get shouldRun() {
    return !!(this.settings.get('shareLocation') && this.isConnected());
  }

  /** Re-evaluate after a settings or connection change. */
  update() {
    if (this.shouldRun) this.#start();
    else this.#stop();
  }

  #start() {
    if (this.state.active) return;
    if (!this.geolocation) {
      this.#patch({ active: false, error: 'unsupported' });
      return;
    }
    this.watchId = this.geolocation.watchPosition(
      (pos) => this.#onFix(pos),
      (err) => this.#onError(err),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 30000 },
    );
    this.timer = setInterval(() => this.sendNow('interval'), SEND_INTERVAL_MS);
    this.#patch({ active: true, error: null });
  }

  #stop() {
    if (this.watchId !== null && this.geolocation) this.geolocation.clearWatch(this.watchId);
    this.watchId = null;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    if (this.state.active) this.#patch({ active: false });
  }

  #onFix(pos) {
    const first = !this.state.lastFix;
    this.#patch({
      lastFix: { lat: pos.coords.latitude, lon: pos.coords.longitude, acc: pos.coords.accuracy, at: Date.now() },
      error: null,
    });
    if (first) this.sendNow('first-fix');
  }

  #onError(err) {
    const error = err && err.code === 1 ? 'denied' : 'unavailable';
    this.#patch({ error });
  }

  freshFix(maxAgeMs = MAX_FIX_AGE_MS) {
    const fix = this.state.lastFix;
    return fix && Date.now() - fix.at <= maxAgeMs ? fix : null;
  }

  /**
   * Get a location fix even when sharing is off (used locally by the SOS screen only).
   * Resolves to a fix or null.
   */
  getFix({ maxAgeMs = 30000, timeoutMs = 15000 } = {}) {
    const fresh = this.freshFix(maxAgeMs);
    if (fresh) return Promise.resolve(fresh);
    if (!this.geolocation) return Promise.resolve(null);
    return new Promise((resolve) => {
      this.geolocation.getCurrentPosition(
        (pos) => {
          const fix = { lat: pos.coords.latitude, lon: pos.coords.longitude, acc: pos.coords.accuracy, at: Date.now() };
          this.#patch({ lastFix: fix });
          resolve(fix);
        },
        (err) => {
          if (err && err.code === 1) this.#patch({ error: 'denied' });
          resolve(null);
        },
        { enableHighAccuracy: true, maximumAge: maxAgeMs, timeout: timeoutMs },
      );
    });
  }

  /** Address for a fix if reverse geocoding is enabled (rate limited), else null. */
  async addressFor(fix, { waitMs = 0 } = {}) {
    if (!this.settings.get('reverseGeocode') || !fix) return null;
    const lang = this.getLang();
    const cached = this.geocoder.cachedFor(fix, lang);
    const pending = this.geocoder.lookup(fix, lang);
    if (!waitMs) return cached;
    const timeout = new Promise((resolve) => setTimeout(() => resolve(cached), waitMs));
    return Promise.race([pending, timeout]);
  }

  async sendNow(reason = 'manual') {
    if (!this.shouldRun) return false;
    const fix = this.freshFix();
    if (!fix) {
      if (this.state.lastFix) this.#patch({ error: 'stale' });
      return false;
    }
    const addr = await this.addressFor(fix, { waitMs: reason === 'need_location' ? 3000 : 0 });
    try {
      await this.send(makeLoc({ lat: fix.lat, lon: fix.lon, acc_m: fix.acc, addr }));
      this.#patch({ lastSentAt: Date.now(), lastAddr: addr || null });
      return true;
    } catch {
      return false;
    }
  }

  /** Helmet asked "Where am I?" (B2 long press). */
  async handleNeedLocation() {
    const say = (key) => this.send(makeSay(this.t(key), 3)).catch(() => {});
    if (!this.settings.get('shareLocation')) return say('loc.sayOff');
    if (!this.freshFix(15000)) {
      const fix = await this.getFix({ maxAgeMs: 15000, timeoutMs: 8000 });
      if (!fix) return say(this.state.error === 'denied' ? 'loc.sayDenied' : 'loc.sayUnavailable');
    }
    const sent = await this.sendNow('need_location');
    if (!sent) return say('loc.sayUnavailable');
    return undefined;
  }

  #patch(partial) {
    this.state = { ...this.state, ...partial };
    this.dispatchEvent(new CustomEvent('change', { detail: this.state }));
  }
}
