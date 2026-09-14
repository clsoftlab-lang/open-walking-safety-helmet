// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// Web Bluetooth transport for the Nordic UART Service (spec §8).
// Events (CustomEvent.detail):
//   "state"   {state: 'disconnected'|'connecting'|'connected'|'reconnecting', name, attempt?, delayMs?}
//   "message" decoded helmet message object
//   "ignored" {reason, type?} a received line that was not understood
//   "error"   {error}

import {
  NUS_SERVICE_UUID, NUS_RX_UUID, NUS_TX_UUID, DEVICE_NAME_PREFIX, DEFAULT_MTU,
  HELMET_TYPES, LineDecoder, encode, chunk,
} from './protocol.js';

/** Exponential backoff with optional +/- jitter fraction. Pure; exported for tests. */
export function computeBackoff(attempt, { initialMs = 1000, maxMs = 30000, factor = 2, jitter = 0.2 } = {}) {
  const base = Math.min(maxMs, initialMs * factor ** Math.max(0, attempt));
  if (!jitter) return base;
  const spread = base * jitter;
  return Math.round(base - spread + Math.random() * 2 * spread);
}

// The helmet requires an encrypted, bonded link (Just Works pairing). When the phone is not bonded,
// or the helmet's pairing window is closed, Chromium reports GATT failures such as
// "GATT Error: Not paired.", "GATT operation not authorized.", "Authentication failed." or, on some
// platforms, insufficient authentication / encryption. The DOMException name varies by platform,
// so the message is what identifies it.
const AUTH_MESSAGE = /not paired|pairing|authenticat|not authori[sz]ed|authori[sz]ation|encrypt|insufficient|bond/i;

/** True when a Web Bluetooth error means "this phone is not paired/bonded with the helmet". */
export function isAuthError(err) {
  if (!err) return false;
  if (err.code === 'auth') return true;
  const message = String(err.message || '');
  return AUTH_MESSAGE.test(message) && !/user gesture/i.test(message);
}

/** Wrap an auth failure as Error{code:'auth'} (DOMException.code is read-only). */
export function toAuthError(err) {
  if (!isAuthError(err) || err.code === 'auth') return err;
  const error = new Error(err.message);
  error.name = err.name || 'Error';
  error.code = 'auth';
  error.cause = err;
  return error;
}

/**
 * Honest capability check. Returns {supported, reason} where reason is one of
 * null | 'ios' | 'firefox' | 'safari' | 'insecure' | 'other'.
 */
export function getBluetoothSupport(nav = globalThis.navigator, win = globalThis) {
  const ua = (nav && nav.userAgent) || '';
  const isIOS = /iPad|iPhone|iPod/.test(ua) || (nav && nav.platform === 'MacIntel' && nav.maxTouchPoints > 1);
  const isFirefox = /Firefox\/|FxiOS/.test(ua);
  const isSafari = /Safari\//.test(ua) && !/Chrome|Chromium|CriOS|Edg|OPR|Android/.test(ua);
  const hasApi = !!(nav && nav.bluetooth && typeof nav.bluetooth.requestDevice === 'function');
  if (hasApi && win.isSecureContext !== false) return { supported: true, reason: null, isIOS };
  let reason = 'other';
  if (isIOS) reason = 'ios'; // every iOS browser uses WebKit, which has no Web Bluetooth (Bluefy adds it)
  else if (isFirefox) reason = 'firefox';
  else if (isSafari) reason = 'safari';
  else if (win.isSecureContext === false) reason = 'insecure'; // Chromium hides the API on http pages
  return { supported: false, reason, isIOS };
}

export class BleTransport extends EventTarget {
  constructor({ mtu = DEFAULT_MTU, backoff = {} } = {}) {
    super();
    // Web Bluetooth does not expose the negotiated MTU, so we write conservative 20 byte chunks.
    this.mtu = mtu;
    this.backoff = { initialMs: 1000, maxMs: 30000, factor: 2, jitter: 0.2, ...backoff };
    this.isDemo = false;
    this.device = null;
    this.rx = null;
    this.tx = null;
    this.state = 'disconnected';
    this.attempt = 0;
    this.userClosed = false;
    this.opening = false;
    this.reconnectTimer = null;
    this.writeQueue = Promise.resolve();
    this.decoder = new LineDecoder({
      accept: HELMET_TYPES,
      onIgnored: (info) => this.#emit('ignored', info),
    });
    this.onValue = (event) => {
      const value = event.target.value; // DataView
      for (const message of this.decoder.push(value)) this.#emit('message', message);
    };
    this.onDisconnected = () => this.#handleDisconnect();
  }

  get name() {
    return (this.device && this.device.name) || 'OWSH';
  }

  get connected() {
    return this.state === 'connected';
  }

  /** Must be called from a user gesture (click). Shows the browser's device chooser. */
  async connect() {
    // Filter by name prefix and require the NUS service after connecting. The 128-bit NUS UUID
    // plus the name do not fit together in one 31-byte advertisement, so filtering on both in the
    // chooser can hide a real helmet. optionalServices grants access to NUS once connected.
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ namePrefix: DEVICE_NAME_PREFIX }],
      optionalServices: [NUS_SERVICE_UUID],
    });
    if (this.device && this.device !== device) this.device.removeEventListener('gattserverdisconnected', this.onDisconnected);
    this.device = device;
    this.userClosed = false;
    this.attempt = 0;
    device.addEventListener('gattserverdisconnected', this.onDisconnected);
    this.#setState('connecting');
    try {
      await this.#open();
    } catch (error) {
      this.userClosed = true;
      try { if (device.gatt.connected) device.gatt.disconnect(); } catch { /* ignore */ }
      this.#setState('disconnected');
      throw toAuthError(error);
    }
  }

  async #open() {
    this.opening = true;
    try {
      const server = await this.device.gatt.connect();
      let service;
      try {
        service = await server.getPrimaryService(NUS_SERVICE_UUID);
      } catch (cause) {
        const error = new Error('Device has no Nordic UART Service');
        error.code = 'not_owsh';
        error.cause = cause;
        throw error;
      }
      const rx = await service.getCharacteristic(NUS_RX_UUID);
      const tx = await service.getCharacteristic(NUS_TX_UUID);
      if (this.tx) this.tx.removeEventListener('characteristicvaluechanged', this.onValue);
      this.decoder.reset();
      tx.addEventListener('characteristicvaluechanged', this.onValue);
      await tx.startNotifications();
      this.rx = rx;
      this.tx = tx;
      this.attempt = 0;
      this.#setState('connected');
    } finally {
      this.opening = false;
    }
  }

  #handleDisconnect() {
    this.rx = null;
    if (this.userClosed) {
      this.#setState('disconnected');
      return;
    }
    if (this.opening || this.reconnectTimer) return; // an attempt is already in progress/scheduled
    this.#scheduleReconnect();
  }

  #scheduleReconnect() {
    const delayMs = computeBackoff(this.attempt, this.backoff);
    this.attempt += 1;
    this.#setState('reconnecting', { attempt: this.attempt, delayMs });
    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      if (this.userClosed) return;
      try {
        await this.#open();
      } catch (error) {
        this.#emit('error', { error: toAuthError(error) });
        if (!this.userClosed) this.#scheduleReconnect();
      }
    }, delayMs);
  }

  /** Encode, chunk and write one message. Writes are serialised (GATT allows one at a time). */
  send(message) {
    const parts = chunk(encode(message), this.mtu);
    const run = async () => {
      const rx = this.rx;
      if (!rx || this.state !== 'connected') throw new Error('not connected');
      try {
        for (const part of parts) {
          if (typeof rx.writeValueWithResponse === 'function' && rx.properties.write) await rx.writeValueWithResponse(part);
          else if (typeof rx.writeValueWithoutResponse === 'function') await rx.writeValueWithoutResponse(part);
          else await rx.writeValue(part);
        }
      } catch (err) {
        const error = toAuthError(err);
        if (error.code === 'auth') this.#emit('error', { error }); // e.g. insufficient authentication
        throw error;
      }
    };
    const result = this.writeQueue.then(run);
    this.writeQueue = result.catch(() => {});
    return result;
  }

  disconnect() {
    this.userClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.device && this.device.gatt.connected) {
      this.device.gatt.disconnect(); // fires gattserverdisconnected -> 'disconnected'
    } else {
      this.#setState('disconnected');
    }
  }

  #setState(state, extra = {}) {
    this.state = state;
    this.#emit('state', { state, name: this.name, ...extra });
  }

  #emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail }));
  }
}
