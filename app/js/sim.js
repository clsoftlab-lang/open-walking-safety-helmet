// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
//
// "Demo helmet": a simulated helmet with the same interface and events as BleTransport.
// Every message goes through the real protocol path (encode -> 20 byte chunks -> LineDecoder)
// in both directions, so the demo also exercises framing and chunking.

import {
  HELMET_TYPES, PHONE_TYPES, LineDecoder, encode, chunk, DEFAULT_MTU, SAY_MIN_INTERVAL_MS,
} from './protocol.js';

// Phrases the helmet itself would speak (firmware owns these; mirrored here for the demo only).
const PHRASES = {
  en: {
    ready: 'Helmet ready. The helmet assists your cane or guide dog, it does not replace them.',
    obstacle: 'Obstacle ahead',
    stop: 'Stop',
    drop: 'Step down ahead',
    step_up: 'Step up ahead',
    approach_left: 'Bicycle approaching on the left',
    approach_right: 'Person approaching on the right',
    friend: 'Mina is ahead on the left',
    sign: 'Warning sign: WET FLOOR',
    scene: '2 people ahead, bicycle on the right',
    sos_countdown: 'Emergency alert in 10 seconds. Press any button to cancel.',
    sos_sent: 'Emergency alert sent',
    sos_cancelled: 'Emergency alert cancelled',
    camera_blocked: 'Camera is covered or too dark. Distance sensors still active.',
    camera_recovered: 'Camera recovered',
    muted: 'Voice muted', unmuted: 'Voice on',
    where_addr: 'You are near {addr}',
    where_coords: 'Latitude {lat}, longitude {lon}, accurate to {acc} metres',
    no_location: 'Location not available from phone',
    phone_ack: 'Phone received the emergency alert',
  },
  ko: {
    ready: '헬멧이 준비되었습니다. 헬멧은 흰지팡이나 안내견을 돕는 장치이며, 대신하지 않습니다.',
    obstacle: '앞에 장애물이 있습니다',
    stop: '멈추세요',
    drop: '앞에 내려가는 계단이 있습니다',
    step_up: '앞에 올라가는 턱이 있습니다',
    approach_left: '왼쪽에서 자전거가 다가옵니다',
    approach_right: '오른쪽에서 사람이 다가옵니다',
    friend: '민아 씨가 왼쪽 앞에 있습니다',
    sign: '경고 표지판: 미끄럼 주의',
    scene: '앞에 사람 2명, 오른쪽에 자전거',
    sos_countdown: '10초 뒤 긴급 신고를 보냅니다. 취소하려면 아무 버튼이나 누르세요.',
    sos_sent: '긴급 신고를 보냈습니다',
    sos_cancelled: '긴급 신고를 취소했습니다',
    camera_blocked: '카메라가 가려졌거나 너무 어둡습니다. 거리 센서는 계속 작동합니다.',
    camera_recovered: '카메라가 복구되었습니다',
    muted: '음성 안내를 껐습니다', unmuted: '음성 안내를 켰습니다',
    where_addr: '현재 위치는 {addr} 근처입니다',
    where_coords: '위도 {lat}, 경도 {lon}, 오차 약 {acc}미터',
    no_location: '휴대폰에서 위치를 받지 못했습니다',
    phone_ack: '휴대폰이 긴급 신고를 받았습니다',
  },
};

const SCRIPT = [
  { key: 'obstacle', level: 2, kind: 'obstacle', dir: 'center', dist_m: 1.1 },
  { key: 'approach_left', level: 2, kind: 'approach', dir: 'left', label: 'bicycle' },
  { key: 'friend', level: 3, kind: 'face', dir: 'left', label: 'Mina' },
  { key: 'drop', level: 1, kind: 'drop', dir: 'all', dist_m: 1.6 },
  { key: 'sign', level: 3, kind: 'sign', dir: 'center' },
  { key: 'step_up', level: 2, kind: 'step_up', dir: 'center', dist_m: 1.3 },
  { key: 'approach_right', level: 2, kind: 'approach', dir: 'right', label: 'person' },
  { key: 'stop', level: 1, kind: 'obstacle', dir: 'center', dist_m: 0.5 },
];

export class DemoHelmet extends EventTarget {
  constructor({ lang = 'en', alertIntervalMs = [8000, 13000] } = {}) {
    super();
    this.isDemo = true;
    this.name = 'OWSH-DEMO';
    this.state = 'disconnected';
    this.lang = PHRASES[lang] ? lang : 'en';
    this.alertIntervalMs = alertIntervalMs;
    this.mtu = DEFAULT_MTU;
    this.timers = new Set();
    this.startedAt = 0;
    this.seq = 0;
    this.scriptIndex = 0;
    this.paused = false;
    this.muted = false;
    this.volume = 80;
    this.dropoff = 'normal';
    this.faults = [];
    this.temp = 52;
    this.lastLoc = null;
    this.lastSayAt = -Infinity;
    this.statusCount = 0;
    this.waitingForLocation = null;
    this.sos = null; // {id, reason, state, timer}
    this.toPhone = new LineDecoder({ accept: HELMET_TYPES, onIgnored: (i) => this.#emit('ignored', i) });
    this.toHelmet = new LineDecoder({ accept: PHONE_TYPES, onIgnored: (i) => console.warn('[demo helmet] ignored', i) });
  }

  get connected() {
    return this.state === 'connected';
  }

  async connect() {
    this.#setState('connecting');
    await new Promise((resolve) => this.#after(500, resolve));
    this.startedAt = Date.now();
    this.#setState('connected');
    this.#after(300, () => {
      this.#helmet({ t: 'hello', fw: '1.0.0-demo', lang: this.lang, features: ['lidar_fwd', 'lidar_down', 'vision', 'faces', 'imu', 'sos', 'demo'] });
      this.#status();
      this.#say('ready', 4);
    });
    this.#every(10000, () => this.#status());
    this.#scheduleNextAlert();
  }

  disconnect() {
    for (const handle of this.timers) { clearTimeout(handle); clearInterval(handle); }
    this.timers.clear();
    this.sos = null;
    this.#setState('disconnected');
  }

  /** Phone -> helmet. Goes through encode/chunk/decode like a real link. */
  async send(message) {
    if (!this.connected) throw new Error('not connected');
    const parts = chunk(encode(message), this.mtu);
    await new Promise((resolve) => setTimeout(resolve, 15 * parts.length));
    for (const part of parts) for (const msg of this.toHelmet.push(part)) this.#receive(msg);
  }

  // ----- demo controls -----------------------------------------------------------------------

  setPaused(paused) {
    this.paused = paused;
  }

  triggerSos(reason = 'button') {
    if (!this.connected || this.sos) return;
    const id = `sos-${Date.now().toString(36)}`;
    this.sos = { id, reason, state: 'countdown', timer: null, repeat: null };
    this.#helmet({ t: 'sos', id, reason, state: 'countdown' });
    this.#say('sos_countdown', 0);
    this.sos.timer = this.#after(10000, () => {
      if (!this.sos || this.sos.id !== id) return;
      this.sos.state = 'sent';
      const sendSos = () => this.#helmet({ t: 'sos', id, reason, state: 'sent' });
      sendSos();
      this.#say('sos_sent', 0);
      this.sos.repeat = this.#every(5000, () => (this.sos && this.sos.id === id ? sendSos() : null));
    });
  }

  /** Any helmet button press during countdown cancels (spec §7.2). */
  pressButton() {
    if (this.sos && this.sos.state === 'countdown') {
      clearTimeout(this.sos.timer);
      this.timers.delete(this.sos.timer);
      this.#helmet({ t: 'sos', id: this.sos.id, reason: this.sos.reason, state: 'cancelled' });
      this.#say('sos_cancelled', 2);
      this.sos = null;
    }
  }

  whereAmI() {
    if (!this.connected) return;
    this.#helmet({ t: 'need_location' });
    const token = {};
    this.waitingForLocation = token;
    this.#after(12000, () => {
      if (this.waitingForLocation === token) {
        this.waitingForLocation = null;
        this.#say('no_location', 3);
      }
    });
  }

  toggleCameraFault() {
    if (!this.connected) return false;
    if (this.faults.includes('camera_blocked')) {
      this.faults = this.faults.filter((f) => f !== 'camera_blocked');
      this.#status();
      this.#say('camera_recovered', 4);
      return false;
    }
    this.faults = [...this.faults, 'camera_blocked'];
    this.#status();
    this.#alert({ key: 'camera_blocked', level: 0, kind: 'fault', dir: 'all' });
    return true;
  }

  // ----- internals -----------------------------------------------------------------------------

  #receive(msg) {
    switch (msg.t) {
      case 'ping':
        this.#helmet({ t: 'pong', id: msg.id });
        break;
      case 'ack':
        if (this.sos && this.sos.id === msg.id && this.sos.state === 'sent') {
          clearInterval(this.sos.repeat);
          this.timers.delete(this.sos.repeat);
          this.sos = null; // acked: stop repeating, allow a new demo SOS later
          this.#say('phone_ack', 3);
        }
        break;
      case 'say': {
        const now = Date.now();
        if (now - this.lastSayAt < SAY_MIN_INTERVAL_MS) { // helmet rate limit: 1 say per 3 s
          console.warn('[demo helmet] say dropped by rate limit:', msg.text);
          break;
        }
        this.lastSayAt = now;
        this.#helmet({ t: 'speech', text: msg.text, level: msg.level });
        break;
      }
      case 'loc':
        this.lastLoc = msg;
        if (this.waitingForLocation) {
          this.waitingForLocation = null;
          if (msg.addr) this.#say('where_addr', 3, { addr: msg.addr });
          else this.#say('where_coords', 3, { lat: msg.lat.toFixed(4), lon: msg.lon.toFixed(4), acc: Math.round(msg.acc_m) });
        }
        break;
      case 'cfg': {
        let changed = false;
        if (typeof msg.lang === 'string' && PHRASES[msg.lang]) { this.lang = msg.lang; changed = true; }
        if (typeof msg.muted === 'boolean' && msg.muted !== this.muted) {
          this.muted = msg.muted;
          changed = true;
          this.#say(this.muted ? 'muted' : 'unmuted', 2);
        }
        if (Number.isInteger(msg.volume)) this.volume = msg.volume;
        if (msg.dropoff_sensitivity) this.dropoff = msg.dropoff_sensitivity;
        if (changed) this.#status();
        break;
      }
      default:
        break;
    }
  }

  #scheduleNextAlert() {
    const [min, max] = this.alertIntervalMs;
    this.#after(min + Math.random() * (max - min), () => {
      if (!this.paused && !(this.sos && this.sos.state === 'countdown')) {
        this.#alert(SCRIPT[this.scriptIndex % SCRIPT.length]);
        this.scriptIndex += 1;
      }
      if (this.connected) this.#scheduleNextAlert();
    });
  }

  #alert({ key, level, kind, dir, dist_m, label }) {
    const text = this.#phrase(key);
    const msg = { t: 'alert', id: `a${++this.seq}`, level, kind, dir, text };
    if (dist_m !== undefined) msg.dist_m = dist_m;
    if (label !== undefined) msg.label = label;
    this.#helmet(msg);
    if (level <= 2 || !this.muted) this.#helmet({ t: 'speech', text, level });
  }

  #say(key, level, params) {
    if (level >= 3 && this.muted) return; // mute silences P3-P4 speech only (§7.1)
    this.#helmet({ t: 'speech', text: this.#phrase(key, params), level });
  }

  #phrase(key, params = {}) {
    const text = (PHRASES[this.lang] && PHRASES[this.lang][key]) || PHRASES.en[key] || key;
    return text.replace(/\{(\w+)\}/g, (m, name) => (params[name] !== undefined ? params[name] : m));
  }

  #status() {
    this.temp = Math.min(68, Math.max(45, this.temp + (Math.random() - 0.45) * 2));
    const fps = this.faults.includes('camera_blocked') ? 0 : 8.5 + Math.random() * 2.5;
    const n = this.statusCount++;
    const status = {
      t: 'status',
      uptime_s: Math.round((Date.now() - this.startedAt) / 1000),
      cpu_temp_c: Math.round(this.temp * 10) / 10,
      fps: Math.round(fps * 10) / 10,
      faults: [...this.faults],
      muted: this.muted,
    };
    // Power/thermal flags: omitted in the first report (unknown), then a repeating demo cycle of
    // 12 reports (~2 min): low power in reports 3-4, thermal throttling in reports 7-9.
    if (n > 0) {
      status.undervoltage = n % 12 === 3 || n % 12 === 4;
      status.throttled = n % 12 >= 7 && n % 12 <= 9;
      if (status.throttled) status.cpu_temp_c = Math.max(status.cpu_temp_c, 81.5);
    }
    this.#helmet(status);
  }

  /** Helmet -> phone through the real framing path. */
  #helmet(message) {
    if (!this.connected) return;
    const parts = chunk(encode({ ...message, ts: Date.now() }), this.mtu);
    for (const part of parts) {
      for (const msg of this.toPhone.push(part)) this.#emit('message', msg);
    }
  }

  #after(ms, fn) {
    const handle = setTimeout(() => { this.timers.delete(handle); fn(); }, ms);
    this.timers.add(handle);
    return handle;
  }

  #every(ms, fn) {
    const handle = setInterval(fn, ms);
    this.timers.add(handle);
    return handle;
  }

  #setState(state) {
    this.state = state;
    this.#emit('state', { state, name: this.name });
  }

  #emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail }));
  }
}
