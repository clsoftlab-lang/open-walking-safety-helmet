// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// SOS flow on the phone (spec §7.3 step 4, §8 "sos"/"ack").
// countdown -> full-screen alert, the helmet's buttons cancel (the protocol has no phone cancel).
// sent      -> send `ack`, loud WebAudio alarm with gaps (so a screen reader stays audible),
//              vibration, location, big Call / SMS buttons. A web app cannot place a call or send
//              an SMS by itself: the user or a bystander must confirm in the phone's own app.
// cancelled -> close and announce.

import { makeAck, makeSay } from './protocol.js';
import { osmMapUrl } from './location.js';
import { sanitizePhone } from './settings.js';

export const COUNTDOWN_S = 10;

export function buildTelHref(number) {
  const n = sanitizePhone(number);
  return n ? `tel:${n}` : null;
}

/** Android uses "sms:a,b?body=", iOS uses "sms:a,b&body=". */
export function buildSmsHref(numbers, body, isIOS = false) {
  const list = (numbers || []).map(sanitizePhone).filter(Boolean);
  return `sms:${list.join(',')}${isIOS ? '&' : '?'}body=${encodeURIComponent(body)}`;
}

export function buildSmsBody(t, { reason, time, fix, addr }) {
  const reasonKey = reason === 'fall' || reason === 'button' ? reason : 'unknown';
  const parts = [];
  if (fix) {
    parts.push(t('sos.smsLocation', { url: osmMapUrl(fix.lat, fix.lon), acc: Math.round(fix.acc) }));
    if (addr) parts.push(t('sos.smsAddress', { addr }));
  } else {
    parts.push(t('sos.smsNoLocation'));
  }
  return t('sos.smsBody', { reason: t(`sos.smsReason.${reasonKey}`), time, location: parts.join(' ') });
}

/** Siren generated with WebAudio (no audio files): 1.5 s sweeps, 0.8 s silence, repeated. */
export class AlarmTone {
  constructor() {
    this.ctx = null;
    this.osc = null;
    this.gain = null;
    this.timer = null;
  }

  /** Call from a user gesture (e.g. the Connect click) so the alarm may start later without one. */
  prime() {
    try {
      const AC = globalThis.AudioContext || globalThis.webkitAudioContext;
      if (!AC) return;
      if (!this.ctx) this.ctx = new AC();
      if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
    } catch { /* audio unavailable */ }
  }

  get playing() {
    return this.timer !== null;
  }

  get audible() {
    return this.playing && !!this.ctx && this.ctx.state === 'running';
  }

  start() {
    this.prime();
    if (!this.ctx || this.timer) return this.audible;
    const ctx = this.ctx;
    try {
      this.gain = ctx.createGain();
      this.gain.gain.value = 0;
      this.osc = ctx.createOscillator();
      this.osc.type = 'square';
      this.osc.frequency.value = 700;
      this.osc.connect(this.gain).connect(ctx.destination);
      this.osc.start();
    } catch {
      return false;
    }
    const burst = () => {
      if (!this.osc) return;
      const t0 = ctx.currentTime + 0.05;
      const f = this.osc.frequency;
      const g = this.gain.gain;
      f.cancelScheduledValues(t0);
      g.cancelScheduledValues(t0);
      for (let i = 0; i < 3; i++) {
        const s = t0 + i * 0.5;
        f.setValueAtTime(700, s);
        f.linearRampToValueAtTime(1500, s + 0.45);
      }
      g.setValueAtTime(0, t0);
      g.linearRampToValueAtTime(0.6, t0 + 0.02);
      g.setValueAtTime(0.6, t0 + 1.45);
      g.linearRampToValueAtTime(0, t0 + 1.5);
    };
    burst();
    this.timer = setInterval(burst, 2300);
    return this.audible;
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    try {
      if (this.osc) {
        this.gain.gain.cancelScheduledValues(0);
        this.gain.gain.value = 0;
        this.osc.stop();
        this.osc.disconnect();
        this.gain.disconnect();
      }
    } catch { /* already stopped */ }
    this.osc = null;
    this.gain = null;
  }
}

export class SosController {
  /**
   * @param {object} o
   * @param {Record<string, HTMLElement>} o.els
   */
  constructor({ els, settings, location, send, t, getLang, isDemo, isIOS, announce, onDemoCancel, onClosed }) {
    Object.assign(this, { els, settings, location, send, t, getLang, isDemo, isIOS, announce, onDemoCancel, onClosed });
    this.alarm = new AlarmTone();
    this.state = 'idle'; // idle | countdown | sent | dismissed
    this.id = null;
    this.reason = null;
    this.remaining = COUNTDOWN_S;
    this.countTimer = null;
    this.vibrateTimer = null;
    this.fix = null;
    this.addr = null;
    this.sentAt = null;
    this.returnFocus = null;

    els.dialog.addEventListener('cancel', (e) => e.preventDefault()); // Escape must not dismiss an emergency
    els.hide.addEventListener('click', () => this.#close());
    els.demoCancel.addEventListener('click', () => this.onDemoCancel && this.onDemoCancel());
    els.sound.addEventListener('click', () => this.#toggleSound());
    els.ok.addEventListener('click', () => this.#imOk());
  }

  primeAudio() {
    this.alarm.prime();
  }

  get active() {
    return this.state === 'countdown' || this.state === 'sent';
  }

  handle(msg) {
    const { id, state } = msg;
    if (state === 'countdown') {
      if (this.id === id && this.state !== 'idle') return; // repeat
      this.#reset();
      Object.assign(this, { id, reason: msg.reason, state: 'countdown' });
      this.#renderCountdown();
      this.#open();
    } else if (state === 'sent') {
      this.#ack(id); // helmet repeats `sos` every 5 s until acked: always ack
      if (this.id === id && (this.state === 'sent' || this.state === 'dismissed')) return;
      if (this.id !== id) this.#reset();
      Object.assign(this, { id, reason: msg.reason, state: 'sent', sentAt: new Date() });
      this.#stopCountdown();
      this.#renderSent();
      this.#open();
      this.#startAlarm();
      this.#locate();
    } else if (state === 'cancelled') {
      if (this.id !== null && this.id !== id) return;
      const wasActive = this.active;
      this.#reset();
      this.#close();
      if (wasActive) setTimeout(() => this.announce(this.t('sos.cancelled'), true), 150);
    }
  }

  /** Re-render texts after a language change. */
  refresh() {
    if (this.state === 'countdown') this.#renderCountdown(false);
    if (this.state === 'sent' || (this.state === 'dismissed' && this.els.dialog.open)) this.#renderSent();
  }

  #reset() {
    this.#stopCountdown();
    this.#stopAlarm();
    Object.assign(this, { state: 'idle', id: null, reason: null, fix: null, addr: null, sentAt: null });
  }

  #ack(id) {
    Promise.resolve().then(() => this.send(makeAck(id))).catch(() => { /* retried on next repeat */ });
  }

  #reasonText() {
    const key = this.reason === 'fall' || this.reason === 'button' ? this.reason : 'unknown';
    return this.t(`sos.reason.${key}`);
  }

  #renderCountdown(restart = true) {
    const { els, t } = this;
    els.dialog.dataset.state = 'countdown';
    els.title.textContent = t('sos.countdownTitle');
    els.reason.textContent = this.#reasonText();
    els.countdownPart.hidden = false;
    els.sentPart.hidden = true;
    els.demoCancel.hidden = !this.isDemo();
    if (restart) {
      this.remaining = COUNTDOWN_S;
      this.#stopCountdown();
      this.countTimer = setInterval(() => {
        this.remaining = Math.max(0, this.remaining - 1);
        this.#renderCount();
        if (this.remaining === 5) els.live.textContent = t('sos.countdownLive', { s: 5 });
        if (this.remaining === 0) {
          this.#stopCountdown();
          els.live.textContent = t('sos.waiting');
        }
      }, 1000);
      els.live.textContent = '';
    }
    this.#renderCount();
  }

  #renderCount() {
    const { els, t } = this;
    els.count.textContent = String(this.remaining);
    els.countText.textContent = this.remaining > 0 ? t('sos.countdownLive', { s: this.remaining }) : t('sos.waiting');
  }

  #stopCountdown() {
    if (this.countTimer) clearInterval(this.countTimer);
    this.countTimer = null;
  }

  #renderSent() {
    const { els, t, settings } = this;
    els.dialog.dataset.state = 'sent';
    els.title.textContent = t('sos.sentTitle');
    els.reason.textContent = this.#reasonText();
    els.countdownPart.hidden = true;
    els.sentPart.hidden = false;
    els.live.textContent = '';

    const number = settings.get('emergencyNumber');
    const tel = buildTelHref(number);
    els.callText.textContent = t('sos.call', { number: sanitizePhone(number) });
    if (tel) els.call.setAttribute('href', tel);
    else els.call.removeAttribute('href');

    const guardians = settings.get('guardians').map(sanitizePhone).filter(Boolean);
    els.guardians.textContent = guardians.length ? t('sos.guardiansList', { list: guardians.join(', ') }) : t('sos.noGuardians');
    this.#renderLocation();
    this.#renderSoundButton();
  }

  #renderLocation() {
    const { els, t } = this;
    const time = new Intl.DateTimeFormat(this.getLang(), { hour: '2-digit', minute: '2-digit' }).format(this.sentAt || new Date());
    if (this.fix) {
      const { lat, lon, acc } = this.fix;
      els.loc.textContent = t('sos.locationValue', { lat: lat.toFixed(5), lon: lon.toFixed(5), acc: Math.round(acc) })
        + (this.addr ? ` ${t('sos.smsAddress', { addr: this.addr })}` : '');
      els.map.href = osmMapUrl(lat, lon);
      els.mapWrap.hidden = false;
    } else {
      els.loc.textContent = this.locating ? t('sos.locating') : t('sos.locationUnavailable');
      els.mapWrap.hidden = true;
    }
    const body = buildSmsBody(t, { reason: this.reason, time, fix: this.fix, addr: this.addr });
    els.sms.href = buildSmsHref(this.settings.get('guardians'), body, this.isIOS);
  }

  async #locate() {
    const id = this.id;
    this.locating = true;
    this.#renderLocation();
    const fix = await this.location.getFix({ maxAgeMs: 30000, timeoutMs: 15000 });
    if (this.id !== id) return;
    this.fix = fix;
    this.locating = false;
    this.#renderLocation();
    if (fix) {
      const addr = await this.location.addressFor(fix, { waitMs: 5000 });
      if (this.id !== id) return;
      this.addr = addr;
      this.#renderLocation();
    }
  }

  #startAlarm() {
    this.alarm.start();
    const vibrate = () => { try { navigator.vibrate && navigator.vibrate([600, 200, 600, 200, 600]); } catch { /* unsupported */ } };
    vibrate();
    if (!this.vibrateTimer) this.vibrateTimer = setInterval(vibrate, 3000);
    this.#renderSoundButton();
  }

  #stopAlarm() {
    this.alarm.stop();
    if (this.vibrateTimer) clearInterval(this.vibrateTimer);
    this.vibrateTimer = null;
    try { navigator.vibrate && navigator.vibrate(0); } catch { /* unsupported */ }
    this.#renderSoundButton();
  }

  #toggleSound() {
    if (this.alarm.audible) {
      this.#stopAlarm();
      this.els.live.textContent = this.t('sos.silenced');
    } else {
      this.alarm.stop();
      this.#startAlarm(); // this click is a user gesture, so audio is allowed now
    }
  }

  #renderSoundButton() {
    const on = this.alarm.audible;
    this.els.sound.textContent = this.t(on ? 'sos.silence' : 'sos.playAlarm');
  }

  #imOk() {
    this.#stopAlarm();
    this.state = 'dismissed';
    // One `say` per dismissal; the app-level SayThrottle drops it if another `say` went out < 3 s ago.
    Promise.resolve().then(() => this.send(makeSay(this.t('sos.dismissedSay'), 2))).catch(() => {});
    this.#close();
  }

  #open() {
    const { dialog, title } = this.els;
    if (!dialog.open) {
      this.returnFocus = document.activeElement;
      dialog.showModal();
    }
    requestAnimationFrame(() => title.focus());
  }

  #close() {
    const { dialog } = this.els;
    if (!dialog.open) return;
    dialog.close();
    const target = this.returnFocus;
    this.returnFocus = null;
    if (target && document.contains(target) && !target.closest('[hidden]') && typeof target.focus === 'function') target.focus();
    else if (this.onClosed) this.onClosed();
  }
}
