// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import { ALERT_KINDS, DIRECTIONS, SOS_STATES, SOS_REASONS } from '../js/protocol.js';
import { COUNTRY_PRESETS } from '../js/settings.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const load = (lang) => JSON.parse(readFileSync(join(root, 'i18n', `${lang}.json`), 'utf8'));
const en = load('en');
const ko = load('ko');
const placeholders = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

test('en.json and ko.json have identical keys', () => {
  const enKeys = Object.keys(en).sort();
  const koKeys = Object.keys(ko).sort();
  assert.deepEqual(enKeys.filter((k) => !(k in ko)), [], 'missing in ko.json');
  assert.deepEqual(koKeys.filter((k) => !(k in en)), [], 'missing in en.json');
});

test('no empty strings, same placeholders in every language, Korean actually translated', () => {
  for (const key of Object.keys(en)) {
    assert.equal(typeof en[key], 'string', key);
    assert.ok(en[key].trim(), `empty en ${key}`);
    assert.ok(ko[key].trim(), `empty ko ${key}`);
    assert.deepEqual(placeholders(ko[key]), placeholders(en[key]), `placeholders differ: ${key}`);
  }
  const hangul = Object.values(ko).filter((v) => /[가-힣]/.test(v)).length;
  assert.ok(hangul / Object.keys(ko).length > 0.9, 'most Korean strings contain Hangul');
});

test('every key used by the markup and scripts exists', () => {
  const used = new Set();
  const html = readFileSync(join(root, 'index.html'), 'utf8');
  for (const m of html.matchAll(/data-i18n="([^"]+)"/g)) used.add(m[1]);
  for (const m of html.matchAll(/data-i18n-attr="([^"]+)"/g)) {
    for (const pair of m[1].split(';')) used.add(pair.split(':')[1].trim());
  }
  for (const file of readdirSync(join(root, 'js'))) {
    const src = readFileSync(join(root, 'js', file), 'utf8');
    for (const m of src.matchAll(/\bt\(\s*'([^'$]+)'/g)) used.add(m[1]);
    for (const m of src.matchAll(/\b(?:say|announceKey)\(\s*'([a-z]+\.[^']+)'/g)) used.add(m[1]);
    for (const m of src.matchAll(/key:\s*'([a-z]+\.[A-Za-z.]+)'/g)) used.add(m[1]);
  }
  // keys built dynamically with template literals
  for (const s of ['disconnected', 'connecting', 'connected', 'reconnecting']) used.add(`conn.${s}`).add(`live.state.${s}`);
  for (const r of ['ios', 'firefox', 'safari', 'insecure', 'other']) used.add(`connect.unsupported.${r}`);
  for (const l of [0, 1, 2, 3, 4]) used.add(`level.${l}`);
  for (const k of ALERT_KINDS) used.add(`kind.${k}`);
  for (const d of DIRECTIONS) used.add(`dir.${d}`);
  for (const s of SOS_STATES) used.add(`log.sos.${s}`);
  for (const r of [...SOS_REASONS, 'unknown']) used.add(`sos.reason.${r}`).add(`sos.smsReason.${r}`);
  for (const s of ['connect', 'live', 'settings']) used.add(`screen.${s}`);
  for (const p of COUNTRY_PRESETS) for (const n of p.numbers) for (const s of n.services) used.add(`service.${s}`);
  used.add('country.EU').add('country.OTHER');

  const missing = [...used].filter((k) => !(k in en)).sort();
  assert.deepEqual(missing, [], 'keys used but not defined in en.json');
});
