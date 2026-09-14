"""Helmet <-> phone protocol over the BLE Nordic UART Service (spec §8). Pure, no I/O.

* UTF-8 JSON objects terminated by ``\\n``; messages longer than MTU - 3 are split into chunks
  and the receiver buffers until ``\\n``. Max message 1024 bytes (including the newline).
* Every message has ``"t"`` (type) and ``"v": 1``; helmet messages carry ``"ts"`` (unix ms).
* Unknown types are ignored (forward compatibility).
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

log = logging.getLogger("owsh.protocol")

PROTOCOL_VERSION = 1
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # phone -> helmet (write / write-without-response)
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # helmet -> phone (notify)
MAX_MESSAGE_BYTES = 1024

HELMET_TYPES = frozenset({"hello", "status", "alert", "speech", "sos", "need_location", "pong"})
PHONE_TYPES = frozenset({"loc", "ack", "say", "cfg", "ping"})
ALERT_KINDS = frozenset({"obstacle", "drop", "step_up", "approach", "face", "sign", "fault"})
DIRECTIONS = frozenset({"left", "center", "right", "all"})
SOS_REASONS = frozenset({"button", "fall"})
SOS_STATES = frozenset({"countdown", "sent", "cancelled"})
SENSITIVITIES = frozenset({"low", "normal", "high"})
_TRUNCATABLE = ("text", "addr", "label")


class ProtocolError(ValueError):
    pass


def _dumps(obj: dict[str, Any]) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def encode(msg_type: str, ts_ms: int | None = None, **fields: Any) -> bytes:
    """Encode a helmet -> phone message. ``None`` fields are omitted. Long text fields are
    shortened so the message fits in :data:`MAX_MESSAGE_BYTES`."""
    if msg_type not in HELMET_TYPES:
        raise ProtocolError(f"unknown helmet message type {msg_type!r}")
    obj: dict[str, Any] = {"t": msg_type, "v": PROTOCOL_VERSION}
    if ts_ms is not None:
        obj["ts"] = int(ts_ms)
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, float):
            if not math.isfinite(v):
                continue
            v = round(v, 3)
        obj[k] = v
    data = _dumps(obj)
    while len(data) > MAX_MESSAGE_BYTES:
        longest = max((k for k in _TRUNCATABLE if isinstance(obj.get(k), str) and obj[k] not in ("", "…")),
                      key=lambda k: len(obj[k].encode("utf-8")), default=None)
        if longest is None:
            raise ProtocolError(f"message {msg_type} is {len(data)} bytes, max {MAX_MESSAGE_BYTES}")
        excess = len(data) - MAX_MESSAGE_BYTES
        s = obj[longest]
        # drop characters until the UTF-8 size shrinks enough (+1 for the ellipsis)
        while s and excess + 3 > 0:
            excess -= len(s[-1].encode("utf-8"))
            s = s[:-1]
        obj[longest] = s + "…" if s else ""
        data = _dumps(obj)
    return data


def encode_phone(msg_type: str, **fields: Any) -> bytes:
    """Encode a phone -> helmet message (used by tests and the simulator)."""
    obj: dict[str, Any] = {"t": msg_type, "v": PROTOCOL_VERSION}
    obj.update({k: v for k, v in fields.items() if v is not None})
    data = _dumps(obj)
    if len(data) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message too long")
    return data


def chunk(data: bytes, max_payload: int) -> list[bytes]:
    """Split an encoded message into notification payloads of at most ``max_payload`` bytes
    (``MTU - 3``). Chunks may split a UTF-8 character; the receiver reassembles bytes."""
    if max_payload < 1:
        raise ProtocolError("max_payload must be >= 1")
    return [data[i:i + max_payload] for i in range(0, len(data), max_payload)]


def chunks_for_mtu(data: bytes, mtu: int) -> list[bytes]:
    return chunk(data, max(20, mtu - 3))


class LineAssembler:
    """Receiver: feed raw chunks, get complete decoded JSON objects back."""

    def __init__(self, max_bytes: int = MAX_MESSAGE_BYTES) -> None:
        self.max_bytes = max_bytes
        self._buf = bytearray()
        self._discarding = False
        self.errors = 0

    def feed(self, data: bytes | bytearray) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for byte in bytes(data):
            if byte == 0x0A:  # "\n"
                line = bytes(self._buf)
                self._buf.clear()
                if self._discarding:
                    self._discarding = False
                    continue
                msg = self._decode(line)
                if msg is not None:
                    out.append(msg)
                continue
            if self._discarding:
                continue
            self._buf.append(byte)
            if len(self._buf) >= self.max_bytes:  # the newline would exceed the limit
                log.warning("incoming message exceeds %d bytes, discarded", self.max_bytes)
                self.errors += 1
                self._buf.clear()
                self._discarding = True
        return out

    def _decode(self, line: bytes) -> dict[str, Any] | None:
        line = line.strip(b"\r \t")
        if not line:
            return None
        try:
            obj = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.errors += 1
            log.warning("bad JSON from phone: %s", exc)
            return None
        if not isinstance(obj, dict) or not isinstance(obj.get("t"), str):
            self.errors += 1
            return None
        return obj


def _num(v: Any, lo: float, hi: float) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v) if lo <= v <= hi else None


def validate_phone(msg: dict[str, Any], say_min_level: int = 2) -> dict[str, Any] | None:
    """Validate/normalise a phone -> helmet message. Returns None for unknown or invalid ones."""
    t = msg.get("t")
    if t not in PHONE_TYPES:
        return None  # unknown types are ignored
    v = msg.get("v", PROTOCOL_VERSION)
    if v != PROTOCOL_VERSION:
        log.info("phone protocol version %r (helmet speaks %d); trying anyway", v, PROTOCOL_VERSION)
    if t == "loc":
        lat, lon = _num(msg.get("lat"), -90, 90), _num(msg.get("lon"), -180, 180)
        if lat is None or lon is None:
            return None
        out: dict[str, Any] = {"t": t, "lat": lat, "lon": lon, "acc_m": _num(msg.get("acc_m"), 0, 1e7)}
        addr = msg.get("addr")
        if isinstance(addr, str) and addr.strip():
            out["addr"] = addr.strip()[:300]
        return out
    if t in ("ack", "ping"):
        if "id" not in msg or not isinstance(msg["id"], (str, int)) or isinstance(msg["id"], bool):
            return None
        return {"t": t, "id": msg["id"]}
    if t == "say":
        text = msg.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        level = msg.get("level", 3)
        level = 3 if isinstance(level, bool) or not isinstance(level, int) else level
        # A phone can never preempt P0/P1 safety speech (spec leaves the range open; safest choice).
        return {"t": t, "text": text.strip()[:500], "level": max(say_min_level, min(4, level))}
    if t == "cfg":
        out = {"t": t}
        if isinstance(msg.get("lang"), str):
            out["lang"] = msg["lang"]
        if isinstance(msg.get("muted"), bool):
            out["muted"] = msg["muted"]
        vol = _num(msg.get("volume"), 0, 100)
        if vol is not None:
            out["volume"] = int(vol)
        if msg.get("dropoff_sensitivity") in SENSITIVITIES:
            out["dropoff_sensitivity"] = msg["dropoff_sensitivity"]
        return out
    return None  # pragma: no cover
