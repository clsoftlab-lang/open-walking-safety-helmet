// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// Tiny i18n: flat JSON dictionaries in ../i18n/<lang>.json with {placeholder} substitution.
// Markup carries English defaults; data-i18n replaces textContent, data-i18n-attr="attr:key;attr:key"
// replaces attributes. Missing keys fall back to English, then to the markup / the key itself.

export const SUPPORTED_LANGUAGES = Object.freeze(['en', 'ko']);
const RTL = new Set(['ar', 'he', 'fa', 'ur']);

let english = {};
let active = {};
let current = 'en';
const cache = new Map();

export function resolveLanguage(preference, languages = globalThis.navigator ? navigator.languages || [navigator.language] : []) {
  if (SUPPORTED_LANGUAGES.includes(preference)) return preference;
  for (const tag of languages) {
    const base = String(tag || '').toLowerCase().split('-')[0];
    if (SUPPORTED_LANGUAGES.includes(base)) return base;
  }
  return 'en';
}

async function load(lang) {
  if (cache.has(lang)) return cache.get(lang);
  try {
    const response = await fetch(new URL(`../i18n/${lang}.json`, import.meta.url));
    if (!response.ok) throw new Error(String(response.status));
    const dict = await response.json();
    cache.set(lang, dict);
    return dict;
  } catch (error) {
    console.warn(`[i18n] could not load ${lang}:`, error);
    return {};
  }
}

export function has(key) {
  return Object.prototype.hasOwnProperty.call(active, key) || Object.prototype.hasOwnProperty.call(english, key);
}

export function t(key, params = {}) {
  let text = active[key] ?? english[key] ?? key;
  if (params && typeof text === 'string') {
    text = text.replace(/\{(\w+)\}/g, (match, name) => (params[name] !== undefined && params[name] !== null ? String(params[name]) : match));
  }
  return text;
}

export function getLanguage() {
  return current;
}

export async function setLanguage(preference) {
  const lang = resolveLanguage(preference);
  if (!Object.keys(english).length) english = await load('en');
  active = lang === 'en' ? english : await load(lang);
  current = lang;
  if (globalThis.document) {
    document.documentElement.lang = lang;
    document.documentElement.dir = RTL.has(lang) ? 'rtl' : 'ltr';
    applyTranslations(document);
  }
  return lang;
}

export function applyTranslations(root) {
  for (const el of root.querySelectorAll('[data-i18n]')) {
    const key = el.getAttribute('data-i18n');
    if (has(key)) el.textContent = t(key);
  }
  for (const el of root.querySelectorAll('[data-i18n-attr]')) {
    for (const pair of el.getAttribute('data-i18n-attr').split(';')) {
      const [attr, key] = pair.split(':').map((s) => s && s.trim());
      if (attr && key && has(key)) el.setAttribute(attr, t(key));
    }
  }
}
