// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildTelHref, buildSmsHref, buildSmsBody } from '../js/sos.js';
import { osmMapUrl, ReverseGeocoder, shortAddress } from '../js/location.js';
import { guessCountry, sanitizePhone, sanitizeSettings, defaultSettings } from '../js/settings.js';

const t = (key, p = {}) => `${key}(${Object.entries(p).map(([k, v]) => `${k}=${v}`).join('|')})`;

test('tel and sms links', () => {
  assert.equal(buildTelHref(' 1 1 9 '), 'tel:119');
  assert.equal(buildTelHref('+82 (10) 1234-5678'), 'tel:+821012345678');
  assert.equal(buildTelHref('abc'), null);
  assert.equal(buildSmsHref(['010-1111-2222', '', '+1 555 0100'], 'a b&c', false), 'sms:01011112222,+15550100?body=a%20b%26c');
  assert.equal(buildSmsHref([], 'x', true), 'sms:&body=x');
});

test('SMS body contains an OpenStreetMap link with mlat/mlon', () => {
  const body = buildSmsBody(t, { reason: 'fall', time: '14:05', fix: { lat: 37.5665, lon: 126.978, acc: 12.4 }, addr: 'Seoul' });
  assert.match(body, /https:\/\/www\.openstreetmap\.org\/\?mlat=37\.566500&mlon=126\.978000/);
  assert.match(body, /sos\.smsReason\.fall/);
  assert.match(body, /addr=Seoul/);
  assert.match(buildSmsBody(t, { reason: 'x', time: '1', fix: null }), /sos\.smsNoLocation/);
  assert.equal(osmMapUrl(-1.5, 2), 'https://www.openstreetmap.org/?mlat=-1.500000&mlon=2.000000#map=18/-1.500000/2.000000');
});

test('Nominatim lookups are limited to one request per 30 s and cached', async () => {
  let now = 0;
  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(url);
    return { ok: true, json: async () => ({ display_name: `Place ${calls.length}, Road, District, City, 12345, Country` }) };
  };
  const g = new ReverseGeocoder({ fetchImpl, now: () => now });
  const a = { lat: 37.5, lon: 127.0 };
  const far = { lat: 37.6, lon: 127.1 };
  assert.equal(await g.lookup(a, 'ko'), 'Place 1, Road, District, City');
  assert.match(calls[0], /accept-language=ko/);
  now = 10000;
  assert.equal(await g.lookup(far, 'ko'), null); // too soon: no request
  assert.equal(await g.lookup(a, 'ko'), 'Place 1, Road, District, City'); // cached, no request
  assert.equal(calls.length, 1);
  now = 30001;
  assert.equal(await g.lookup(far, 'ko'), 'Place 2, Road, District, City');
  assert.equal(calls.length, 2);
  assert.equal(shortAddress(''), null);
});

test('settings: country guess, phone sanitising, validation', () => {
  assert.equal(guessCountry(['ko-KR']), 'KR');
  assert.equal(guessCountry(['en-US', 'ko']), 'US');
  assert.equal(guessCountry(['de-DE']), 'EU');
  assert.equal(guessCountry(['ko']), 'KR');
  assert.equal(guessCountry(['ko', 'en-US']), 'KR'); // preference order, region-less first tag
  assert.equal(guessCountry(['en', 'ja']), 'JP');
  assert.equal(guessCountry(['xx']), 'OTHER');
  assert.equal(sanitizePhone('+44 (0) 999'), '+440999');
  const d = defaultSettings(['en-AU']);
  assert.equal(d.emergencyNumber, '000');
  assert.equal(d.reverseGeocode, false);
  const s = sanitizeSettings({ helmetVolume: 150, dropoffSensitivity: 'max', guardians: ['1', 2], lang: 'fr', shareLocation: true }, d);
  assert.equal(s.helmetVolume, 80);
  assert.equal(s.dropoffSensitivity, 'normal');
  assert.deepEqual(s.guardians, ['1', '', '']);
  assert.equal(s.lang, 'system');
  assert.equal(s.shareLocation, true);
});
