// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// Run: node --test tests/

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  NUS_SERVICE_UUID, NUS_RX_UUID, NUS_TX_UUID, DEVICE_NAME_PREFIX, MAX_MESSAGE_BYTES,
  HELMET_TYPES, PHONE_TYPES,
  encode, chunk, encodeChunks, parseLine, LineDecoder, ProtocolError,
  makeLoc, makeAck, makeSay, makeCfg, makePing, utf8Length, truncateUtf8,
} from '../js/protocol.js';
import { computeBackoff, isAuthError, toAuthError } from '../js/ble.js';
import { SayThrottle, SAY_MIN_INTERVAL_MS } from '../js/protocol.js';

test('insufficient authentication / not paired errors are recognised', () => {
  const err = (name, message) => Object.assign(new Error(message), { name });
  for (const e of [
    err('NetworkError', 'GATT Error: Not paired.'),
    err('SecurityError', 'GATT operation not authorized.'),
    err('NetworkError', 'Authentication failed.'),
    err('NotSupportedError', 'GATT Error: insufficient authentication'),
    err('NetworkError', 'Insufficient encryption'),
  ]) assert.equal(isAuthError(e), true, e.message);
  for (const e of [
    err('NotFoundError', 'User cancelled the requestDevice() chooser.'),
    err('SecurityError', "Failed to execute 'requestDevice' on 'Bluetooth': Must be handling a user gesture to show a permission request."),
    err('NetworkError', 'GATT Server is disconnected. Cannot perform GATT operations.'),
    null,
  ]) assert.equal(isAuthError(e), false, e && e.message);
  const wrapped = toAuthError(err('NetworkError', 'GATT Error: Not paired.'));
  assert.equal(wrapped.code, 'auth');
  assert.equal(wrapped.name, 'NetworkError');
});

test('SayThrottle allows at most one say per 3 s', () => {
  let now = 1000;
  const throttle = new SayThrottle({ now: () => now });
  assert.equal(SAY_MIN_INTERVAL_MS, 3000);
  assert.equal(throttle.tryAcquire(), true);
  now += 100;
  assert.equal(throttle.tryAcquire(), false); // e.g. a second "I'm OK" right after the first
  now += 2899;
  assert.equal(throttle.tryAcquire(), false);
  now += 1;
  assert.equal(throttle.tryAcquire(), true);
});

const concat = (parts) => {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
};
const isContinuationByte = (b) => (b & 0xc0) === 0x80;

test('spec §8 constants', () => {
  assert.equal(NUS_SERVICE_UUID, '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'.toLowerCase());
  assert.equal(NUS_RX_UUID, '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'.toLowerCase());
  assert.equal(NUS_TX_UUID, '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'.toLowerCase());
  assert.equal(DEVICE_NAME_PREFIX, 'OWSH-');
  assert.equal(MAX_MESSAGE_BYTES, 1024);
  assert.deepEqual([...HELMET_TYPES], ['hello', 'status', 'alert', 'speech', 'sos', 'need_location', 'pong']);
  assert.deepEqual([...PHONE_TYPES], ['loc', 'ack', 'say', 'cfg', 'ping']);
});

test('encode adds v:1, ends with a single newline, keeps one line', () => {
  const bytes = encode({ t: 'say', text: 'line1\nline2', level: 2, v: 99 });
  const text = new TextDecoder().decode(bytes);
  assert.ok(text.endsWith('\n'));
  assert.equal(text.indexOf('\n'), text.length - 1, 'no raw newline inside the frame');
  const parsed = JSON.parse(text);
  assert.equal(parsed.v, 1);
  assert.equal(parsed.t, 'say');
  assert.equal(parsed.text, 'line1\nline2');
});

test('encode rejects non-objects, missing type and oversize messages', () => {
  assert.throws(() => encode(null), ProtocolError);
  assert.throws(() => encode([]), ProtocolError);
  assert.throws(() => encode({ text: 'x' }), ProtocolError);
  assert.throws(() => encode({ t: 'say', text: 'a'.repeat(1100) }), ProtocolError);
  // exactly at the limit is fine
  const overhead = utf8Length(JSON.stringify({ t: 'say', v: 1, text: '' }) + '\n');
  assert.equal(encode({ t: 'say', text: 'a'.repeat(MAX_MESSAGE_BYTES - overhead) }).length, MAX_MESSAGE_BYTES);
});

test('chunk respects MTU - 3 and concatenates back to the original', () => {
  const bytes = encode({ t: 'status', uptime_s: 12, cpu_temp_c: 51.5, fps: 9.1, faults: ['camera_blocked'], muted: false });
  for (const mtu of [4, 23, 24, 64, 185, 247, 517]) {
    const parts = chunk(bytes, mtu);
    assert.ok(parts.every((p) => p.length >= 1 && p.length <= mtu - 3), `mtu ${mtu}`);
    assert.deepEqual(concat(parts), bytes);
  }
  assert.throws(() => chunk(bytes, 3), ProtocolError);
  assert.equal(encodeChunks({ t: 'ping', id: 1 }, 23)[0].length <= 20, true);
});

test('round trip: Korean text split mid-character across 20 byte chunks', () => {
  const alert = {
    t: 'alert', id: 'a-17', level: 1, kind: 'drop', dir: 'all', dist_m: 1.4,
    text: '앞에 내려가는 계단이 있습니다. 멈추세요! 🚧 Step down ahead', ts: 1789000000000,
  };
  const bytes = encode(alert);
  const parts = chunk(bytes, 23);
  assert.ok(parts.slice(1).some((p) => isContinuationByte(p[0])),
    'test must actually split a multi-byte character across chunks');

  const decoder = new LineDecoder();
  const received = [];
  for (const part of parts) received.push(...decoder.push(part));
  assert.equal(received.length, 1);
  assert.deepEqual(received[0], { ...alert, v: 1 });
});

test('round trip: one byte at a time, DataView and ArrayBuffer inputs', () => {
  const msg = { t: 'speech', text: '민아 씨가 왼쪽 앞에 있습니다', level: 3, ts: 1 };
  const bytes = encode(msg);
  const decoder = new LineDecoder();
  const out = [];
  bytes.forEach((b, i) => {
    const one = new Uint8Array([b]);
    const input = i % 2 ? new DataView(one.buffer) : one.buffer;
    out.push(...decoder.push(input));
  });
  assert.deepEqual(out, [{ ...msg, v: 1 }]);
});

test('several messages in one chunk and a message spanning pushes', () => {
  const a = encode({ t: 'hello', fw: '1.0.0', lang: 'ko', features: ['lidar'], ts: 1 });
  const b = encode({ t: 'need_location', ts: 2 });
  const c = encode({ t: 'pong', id: 7, ts: 3 });
  const all = concat([a, b, c]);
  const decoder = new LineDecoder();
  const first = decoder.push(all.subarray(0, a.length + b.length + 5));
  assert.deepEqual(first.map((m) => m.t), ['hello', 'need_location']);
  const second = decoder.push(all.subarray(a.length + b.length + 5));
  assert.deepEqual(second.map((m) => m.t), ['pong']);
});

test('unknown message types are ignored and decoding continues', () => {
  const ignored = [];
  const decoder = new LineDecoder({ onIgnored: (info) => ignored.push(info) });
  const input = concat([
    encode({ t: 'future_thing', x: 1 }),
    encode({ t: 'loc', lat: 1, lon: 2, acc_m: 3 }), // phone->helmet type is unknown to the phone
    encode({ t: 'speech', text: 'ok', level: 4 }),
  ]);
  const out = decoder.push(input);
  assert.deepEqual(out.map((m) => m.t), ['speech']);
  assert.deepEqual(ignored.map((i) => [i.reason, i.type]), [['unknown_type', 'future_thing'], ['unknown_type', 'loc']]);
});

test('bad JSON, wrong version, invalid fields and invalid UTF-8 are ignored; decoder recovers', () => {
  const reasons = [];
  const decoder = new LineDecoder({ onIgnored: (i) => reasons.push(i.reason) });
  const enc = new TextEncoder();
  const input = concat([
    enc.encode('{not json\n'),
    enc.encode('[1,2]\n'),
    enc.encode('{"t":"alert","v":2,"level":1,"text":"x"}\n'),
    enc.encode('{"t":"alert","v":1,"level":7,"text":"x"}\n'),
    enc.encode('{"t":"sos","v":1,"id":"s1","state":"exploded"}\n'),
    new Uint8Array([0xff, 0xfe, 0x0a]),
    enc.encode('\n'), // blank keep-alive line: silently skipped
    encode({ t: 'sos', id: 's1', reason: 'fall', state: 'sent' }),
  ]);
  const out = decoder.push(input);
  assert.deepEqual(out.map((m) => m.state), ['sent']);
  assert.deepEqual(reasons, ['json', 'not_object', 'version', 'invalid', 'invalid', 'utf8']);
});

test('over-long line is discarded and the decoder resynchronises at the next newline', () => {
  const reasons = [];
  const decoder = new LineDecoder({ onIgnored: (i) => reasons.push(i.reason) });
  const junk = new TextEncoder().encode('x'.repeat(3000));
  assert.deepEqual(decoder.push(junk), []);
  const out = decoder.push(concat([new Uint8Array([0x0a]), encode({ t: 'pong', id: 'p' })]));
  assert.deepEqual(out.map((m) => m.t), ['pong']);
  assert.deepEqual(reasons, ['too_long']);
});

test('speech without level defaults to 3; parseLine direct use', () => {
  const r = parseLine('{"t":"speech","v":1,"text":"hi"}');
  assert.equal(r.ok, true);
  assert.equal(r.message.level, 3);
  assert.equal(parseLine('   ').reason, 'empty');
});

test('phone -> helmet builders round-trip through a helmet-side decoder', () => {
  const decoder = new LineDecoder({ accept: PHONE_TYPES });
  const msgs = [
    makeLoc({ lat: 37.5665123456, lon: 126.978, acc_m: 12.34, addr: '서울특별시 중구 세종대로 110' }),
    makeAck('sos-1'),
    makeSay('휴대폰에서 보낸 시험 메시지입니다.'),
    makeCfg({ muted: true, volume: 70, dropoff_sensitivity: 'high' }),
    makePing(42),
  ];
  const bytes = concat(msgs.flatMap((m) => encodeChunks(m, 23)));
  const out = decoder.push(bytes);
  assert.deepEqual(out.map((m) => m.t), ['loc', 'ack', 'say', 'cfg', 'ping']);
  assert.equal(out[0].lat, 37.566512);
  assert.equal(out[0].addr, '서울특별시 중구 세종대로 110');
  assert.equal(out[2].level, 3);
  assert.equal(out[3].volume, 70);
});

test('builders validate input', () => {
  assert.throws(() => makeCfg({}), ProtocolError);
  assert.throws(() => makeCfg({ volume: 101 }), ProtocolError);
  assert.throws(() => makeCfg({ dropoff_sensitivity: 'max' }), ProtocolError);
  assert.throws(() => makeCfg({ muted: 'yes' }), ProtocolError);
  assert.throws(() => makeLoc({ lat: 91, lon: 0, acc_m: 1 }), ProtocolError);
  assert.throws(() => makeLoc({ lat: NaN, lon: 0, acc_m: 1 }), ProtocolError);
  assert.throws(() => makeAck(undefined), ProtocolError);
  assert.throws(() => makeSay(''), ProtocolError);
});

test('makeLoc truncates a very long (multi-byte) address so the frame fits 1024 bytes', () => {
  const addr = '가"나\\다'.repeat(400);
  const msg = makeLoc({ lat: -33.8688, lon: 151.2093, acc_m: 5, addr });
  const bytes = encode(msg);
  assert.ok(bytes.length <= MAX_MESSAGE_BYTES);
  assert.ok(msg.addr.length > 100);
  assert.ok(addr.startsWith(msg.addr));
  assert.equal(truncateUtf8('한글', 4), '한'); // never cuts inside a character
});

test('reconnect backoff grows exponentially and is capped', () => {
  const opts = { initialMs: 1000, maxMs: 30000, factor: 2, jitter: 0 };
  assert.deepEqual([0, 1, 2, 3, 4, 5, 6, 20].map((n) => computeBackoff(n, opts)),
    [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000]);
  for (let i = 0; i < 50; i++) {
    const d = computeBackoff(3, { ...opts, jitter: 0.2 });
    assert.ok(d >= 6400 && d <= 9600);
  }
});
