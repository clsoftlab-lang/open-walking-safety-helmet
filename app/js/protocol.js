// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// Helmet <-> phone protocol, system design spec §8 (single source of truth).
// Pure module: no DOM, no Bluetooth, no timers. Runs in browsers and in Node (tests).
//
// Framing: UTF-8 JSON object terminated by "\n". Longer than (MTU - 3) bytes -> split into
// chunks; the receiver buffers until "\n". Max message 1024 bytes (we count the whole frame,
// including the terminating newline). Every message has "t" (type) and "v": 1.
// Unknown types are ignored (forward compatibility).

export const NUS_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
/** Phone -> helmet (write / write-without-response). */
export const NUS_RX_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e';
/** Helmet -> phone (notify). */
export const NUS_TX_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e';

export const DEVICE_NAME_PREFIX = 'OWSH-';
export const PROTOCOL_VERSION = 1;
export const MAX_MESSAGE_BYTES = 1024;
/** BLE default ATT MTU. Web Bluetooth does not expose the negotiated MTU, so this is the safe value. */
export const DEFAULT_MTU = 23;
export const ATT_OVERHEAD_BYTES = 3;

/** Helmet -> phone message types (§8.1). */
export const HELMET_TYPES = Object.freeze(['hello', 'status', 'alert', 'speech', 'sos', 'need_location', 'pong']);
/** Phone -> helmet message types (§8.2). */
export const PHONE_TYPES = Object.freeze(['loc', 'ack', 'say', 'cfg', 'ping']);

export const ALERT_KINDS = Object.freeze(['obstacle', 'drop', 'step_up', 'approach', 'face', 'sign', 'fault']);
export const DIRECTIONS = Object.freeze(['left', 'center', 'right', 'all']);
export const SOS_REASONS = Object.freeze(['button', 'fall']);
export const SOS_STATES = Object.freeze(['countdown', 'sent', 'cancelled']);
export const DROPOFF_SENSITIVITIES = Object.freeze(['low', 'normal', 'high']);
export const MIN_LEVEL = 0;
export const MAX_LEVEL = 4;

const NEWLINE = 0x0a;
const textEncoder = new TextEncoder();

export class ProtocolError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ProtocolError';
  }
}

const isPlainObject = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);
const isFiniteNumber = (x) => typeof x === 'number' && Number.isFinite(x);
const isLevel = (x) => Number.isInteger(x) && x >= MIN_LEVEL && x <= MAX_LEVEL;
const isId = (x) => (typeof x === 'string' && x.length > 0) || Number.isInteger(x);

/** Byte length of a string in UTF-8. */
export function utf8Length(text) {
  return textEncoder.encode(text).length;
}

/**
 * Encode one message as a newline-terminated UTF-8 JSON frame.
 * Adds "v": 1. JSON.stringify escapes newlines inside strings, so the frame is always one line.
 * @param {object} message must contain a non-empty string "t"
 * @returns {Uint8Array}
 */
export function encode(message) {
  if (!isPlainObject(message)) throw new ProtocolError('message must be an object');
  if (typeof message.t !== 'string' || message.t.length === 0) {
    throw new ProtocolError('message.t must be a non-empty string');
  }
  const { t, v: _ignored, ...rest } = message;
  const bytes = textEncoder.encode(JSON.stringify({ t, v: PROTOCOL_VERSION, ...rest }) + '\n');
  if (bytes.length > MAX_MESSAGE_BYTES) {
    throw new ProtocolError(`message is ${bytes.length} bytes, max is ${MAX_MESSAGE_BYTES}`);
  }
  return bytes;
}

/**
 * Split an encoded frame into chunks of at most (mtu - 3) bytes.
 * Splitting may cut a multi-byte UTF-8 character; the receiver reassembles bytes before decoding.
 * @param {Uint8Array} bytes
 * @param {number} mtu negotiated ATT MTU (default 23 -> 20 byte chunks)
 * @returns {Uint8Array[]}
 */
export function chunk(bytes, mtu = DEFAULT_MTU) {
  if (!(bytes instanceof Uint8Array)) throw new ProtocolError('bytes must be a Uint8Array');
  const size = Math.floor(mtu) - ATT_OVERHEAD_BYTES;
  if (!(size >= 1)) throw new ProtocolError(`mtu must be at least ${ATT_OVERHEAD_BYTES + 1}`);
  const out = [];
  for (let i = 0; i < bytes.length; i += size) out.push(bytes.subarray(i, Math.min(i + size, bytes.length)));
  return out;
}

/** encode + chunk. */
export function encodeChunks(message, mtu = DEFAULT_MTU) {
  return chunk(encode(message), mtu);
}

// ---------------------------------------------------------------------------------------------
// Validation of received messages. Deliberately lenient about optional fields (a helmet with
// newer firmware must still work), strict only where a malformed value would mislead the user.

const validators = {
  // helmet -> phone
  hello: (m) => (m.features === undefined || Array.isArray(m.features)),
  status: (m) => (m.faults === undefined || Array.isArray(m.faults)),
  alert: (m) => isLevel(m.level) && typeof m.text === 'string'
    && (m.dist_m === undefined || m.dist_m === null || isFiniteNumber(m.dist_m)),
  speech: (m) => typeof m.text === 'string' && (m.level === undefined || isLevel(m.level)),
  sos: (m) => isId(m.id) && SOS_STATES.includes(m.state),
  need_location: () => true,
  pong: (m) => isId(m.id),
  // phone -> helmet
  loc: (m) => isFiniteNumber(m.lat) && m.lat >= -90 && m.lat <= 90
    && isFiniteNumber(m.lon) && m.lon >= -180 && m.lon <= 180
    && isFiniteNumber(m.acc_m) && m.acc_m >= 0
    && (m.addr === undefined || typeof m.addr === 'string'),
  ack: (m) => isId(m.id),
  say: (m) => typeof m.text === 'string' && m.text.length > 0 && (m.level === undefined || isLevel(m.level)),
  cfg: (m) => validateCfgFields(m) === null,
  ping: (m) => isId(m.id),
};

function validateCfgFields(m) {
  let count = 0;
  if (m.lang !== undefined) { if (typeof m.lang !== 'string' || !m.lang) return 'lang'; count++; }
  if (m.muted !== undefined) { if (typeof m.muted !== 'boolean') return 'muted'; count++; }
  if (m.volume !== undefined) {
    if (!Number.isInteger(m.volume) || m.volume < 0 || m.volume > 100) return 'volume';
    count++;
  }
  if (m.dropoff_sensitivity !== undefined) {
    if (!DROPOFF_SENSITIVITIES.includes(m.dropoff_sensitivity)) return 'dropoff_sensitivity';
    count++;
  }
  return count > 0 ? null : 'empty';
}

/**
 * Parse one line (without the newline).
 * @param {string} line
 * @param {readonly string[]} acceptTypes types this receiver understands; others are ignored
 * @returns {{ok: true, message: object} | {ok: false, reason: string, type?: string}}
 */
export function parseLine(line, acceptTypes = HELMET_TYPES) {
  if (line.trim() === '') return { ok: false, reason: 'empty' };
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    return { ok: false, reason: 'json' };
  }
  if (!isPlainObject(message)) return { ok: false, reason: 'not_object' };
  if (typeof message.t !== 'string') return { ok: false, reason: 'no_type' };
  if (message.v !== PROTOCOL_VERSION) return { ok: false, reason: 'version', type: message.t };
  if (!acceptTypes.includes(message.t)) return { ok: false, reason: 'unknown_type', type: message.t };
  const validate = validators[message.t];
  if (validate && !validate(message)) return { ok: false, reason: 'invalid', type: message.t };
  if (message.t === 'speech' && message.level === undefined) message.level = 3;
  if (message.t === 'say' && message.level === undefined) message.level = 3;
  return { ok: true, message };
}

function toBytes(data) {
  if (data instanceof Uint8Array) return data;
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  if (ArrayBuffer.isView(data)) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  if (typeof data === 'string') return textEncoder.encode(data);
  throw new ProtocolError('unsupported chunk type');
}

/**
 * Streaming receiver. Feed it BLE notification payloads in any split; it returns complete,
 * valid messages. Bytes are buffered (not strings) so multi-byte characters split across chunks
 * are decoded correctly. 0x0A never occurs inside a multi-byte UTF-8 sequence, so splitting on
 * the newline byte is safe. A line longer than the max message size is discarded up to the next
 * newline (resynchronisation).
 */
export class LineDecoder {
  /**
   * @param {{accept?: readonly string[], maxBytes?: number, onIgnored?: (info: object) => void}} [options]
   */
  constructor({ accept = HELMET_TYPES, maxBytes = MAX_MESSAGE_BYTES, onIgnored = null } = {}) {
    this.accept = accept;
    this.maxLineBytes = maxBytes - 1; // frame includes the newline
    this.onIgnored = onIgnored;
    this.buffer = new Uint8Array(this.maxLineBytes);
    this.length = 0;
    this.discarding = false;
    this.utf8 = new TextDecoder('utf-8', { fatal: true });
  }

  reset() {
    this.length = 0;
    this.discarding = false;
  }

  /**
   * @param {Uint8Array|ArrayBuffer|DataView|string} data
   * @returns {object[]} complete valid messages, in order
   */
  push(data) {
    const bytes = toBytes(data);
    const messages = [];
    for (let i = 0; i < bytes.length; i++) {
      const b = bytes[i];
      if (b === NEWLINE) {
        if (this.discarding) {
          this.discarding = false;
          this.#ignored({ reason: 'too_long' });
        } else {
          this.#finishLine(messages);
        }
        this.length = 0;
      } else if (!this.discarding) {
        if (this.length >= this.maxLineBytes) {
          this.discarding = true;
          this.length = 0;
        } else {
          this.buffer[this.length++] = b;
        }
      }
    }
    return messages;
  }

  #finishLine(messages) {
    if (this.length === 0) return; // blank line: keep-alive, not an error
    let text;
    try {
      text = this.utf8.decode(this.buffer.subarray(0, this.length));
    } catch {
      this.#ignored({ reason: 'utf8' });
      return;
    }
    const result = parseLine(text, this.accept);
    if (result.ok) messages.push(result.message);
    else if (result.reason !== 'empty') this.#ignored(result);
  }

  #ignored(info) {
    if (this.onIgnored) {
      try { this.onIgnored(info); } catch { /* never let a logger break decoding */ }
    }
  }
}

// ---------------------------------------------------------------------------------------------
// Builders for phone -> helmet messages (validated before sending).

function checked(message) {
  const result = validators[message.t](message);
  if (!result) throw new ProtocolError(`invalid ${message.t} message`);
  encode(message); // throws if too long
  return message;
}

/** Trim a string (by whole code points) so that it is at most maxBytes long in UTF-8. */
export function truncateUtf8(text, maxBytes) {
  if (utf8Length(text) <= maxBytes) return text;
  const chars = Array.from(text);
  let lo = 0;
  let hi = chars.length;
  while (lo < hi) { // largest prefix that fits
    const mid = Math.ceil((lo + hi) / 2);
    if (utf8Length(chars.slice(0, mid).join('')) <= maxBytes) lo = mid;
    else hi = mid - 1;
  }
  return chars.slice(0, lo).join('');
}

/**
 * @param {{lat: number, lon: number, acc_m: number, addr?: string|null}} p
 */
export function makeLoc({ lat, lon, acc_m, addr }) {
  const message = {
    t: 'loc',
    lat: Math.round(lat * 1e6) / 1e6,
    lon: Math.round(lon * 1e6) / 1e6,
    acc_m: Math.round(acc_m * 10) / 10,
  };
  if (typeof addr === 'string' && addr.trim()) {
    const base = utf8Length(JSON.stringify({ ...message, v: PROTOCOL_VERSION, addr: '' }) + '\n');
    // JSON escaping can grow the string (quotes, backslashes); leave headroom for it.
    let text = truncateUtf8(addr.trim(), MAX_MESSAGE_BYTES - base);
    while (text && utf8Length(JSON.stringify({ ...message, v: PROTOCOL_VERSION, addr: text }) + '\n') > MAX_MESSAGE_BYTES) {
      text = Array.from(text).slice(0, -1).join('');
    }
    if (text) message.addr = text;
  }
  return checked(message);
}

export function makeAck(id) {
  return checked({ t: 'ack', id });
}

export function makeSay(text, level = 3) {
  return checked({ t: 'say', text: truncateUtf8(String(text), 900), level });
}

/**
 * @param {{lang?: string, muted?: boolean, volume?: number, dropoff_sensitivity?: string}} fields
 */
export function makeCfg(fields) {
  const message = { t: 'cfg' };
  for (const key of ['lang', 'muted', 'volume', 'dropoff_sensitivity']) {
    if (fields[key] !== undefined) message[key] = fields[key];
  }
  return checked(message);
}

/** The helmet accepts at most one `say` per 3 s (extra ones are dropped by the helmet). */
export const SAY_MIN_INTERVAL_MS = 3000;

/** Phone-side guard so we never send more than one `say` inside the helmet's rate-limit window. */
export class SayThrottle {
  constructor({ intervalMs = SAY_MIN_INTERVAL_MS, now = () => Date.now() } = {}) {
    this.intervalMs = intervalMs;
    this.now = now;
    this.lastAt = -Infinity;
  }

  /** Returns true (and records the send) if a `say` may be sent now. */
  tryAcquire() {
    const t = this.now();
    if (t - this.lastAt < this.intervalMs) return false;
    this.lastAt = t;
    return true;
  }
}

export function makePing(id) {
  return checked({ t: 'ping', id });
}
