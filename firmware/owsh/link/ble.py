"""BLE link to the phone app: Nordic UART Service GATT server via ``bless`` (spec §8).

Security (a nearby stranger must not be able to mute the helmet or lower drop-off sensitivity):

1. **Link-layer encryption.** With ``ble.security: encrypt`` (default) the RX characteristic gets
   the BlueZ flag ``encrypt-write`` and TX gets ``encrypt-read`` + ``encrypt-notify``. BlueZ then
   refuses writes and notification subscriptions until the phone has paired (the phone shows its
   normal pairing dialog). ``authenticated`` uses the ``encrypt-authenticated-*`` flags, which
   need MITM-protected pairing (passkey/numeric comparison); the helmet has no display or keypad,
   so that level only works with an external agent that can show a passkey.
   *Fallback:* bless exposes no API for these flags, so they are added to bless' BlueZ
   characteristic object before the GATT application is registered. If that internal attribute
   is missing (other bless versions, macOS/Windows backends) the ``*_encryption_required``
   attribute permissions are still set and a warning is logged; the application-layer checks
   below remain active.
2. **Bonded-only (``ble.bonded_only: true``).** Messages from the phone are accepted only while the
   connected device is in BlueZ' bonded (paired) device list. While no phone is bonded yet the
   helmet is pairable; once one is bonded, pairing is only open for ``pairing_window_s`` (120 s)
   after every boot, so a new phone is paired by restarting the helmet. A new bond is announced by
   voice ("New phone paired").
3. The controller confirms safety-reducing ``cfg`` changes by voice and rate-limits ``say``.

When ``bless`` (or a Bluetooth adapter) is unavailable a :class:`NullLink` is used: it only logs,
reports ``connected = False`` and lets the rest of the helmet run (SOS then uses the local
no-phone alarm, spec §7.3 step 5).
"""

from __future__ import annotations

import asyncio
import collections
import logging
import queue
import re
import shutil
import subprocess
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..clock import Clock
from ..config import BleConfig
from . import protocol

log = logging.getLogger("owsh.ble")

Receiver = Callable[[dict[str, Any]], None]
ConnectionCallback = Callable[[bool], None]
SECURITY_LEVELS = ("none", "encrypt", "authenticated")


def device_name(prefix: str = "OWSH") -> str:
    """``OWSH-XXXX`` with the last 4 hex digits of the Bluetooth MAC (fallback: host MAC)."""
    mac = ""
    try:
        mac = Path("/sys/class/bluetooth/hci0/address").read_text().strip()
    except OSError:
        pass
    hexdigits = mac.replace(":", "").upper() if mac else f"{uuid.getnode():012X}"
    return f"{prefix}-{hexdigits[-4:]}"


# ------------------------------------------------------------------------------ security
def security_flags(level: str) -> tuple[list[str], list[str]]:
    """BlueZ ``GattCharacteristic1.Flags`` to add for (RX write characteristic, TX notify)."""
    if level == "authenticated":
        return ["encrypt-authenticated-write"], ["encrypt-authenticated-read", "encrypt-authenticated-notify"]
    if level == "encrypt":
        return ["encrypt-write"], ["encrypt-read", "encrypt-notify"]
    return [], []


def apply_bluez_flags(bless_characteristic: Any, extra: list[str]) -> bool:
    """Append BlueZ flags to a bless BlueZ characteristic before registration. False if the
    backend does not expose them (see module docstring, fallback)."""
    flags = getattr(getattr(bless_characteristic, "gatt", None), "_flags", None)
    if not isinstance(flags, list):
        return False
    for f in extra:
        if f not in flags:
            flags.append(f)
    return True


class PairingPolicy:
    """Pure decisions for the bonded-only allowlist."""

    def __init__(self, bonded_only: bool, window_s: float, boot_t: float, security: str = "encrypt") -> None:
        self.bonded_only = bonded_only
        self.window_s = window_s
        self.boot_t = boot_t
        self.security = security

    def pairable(self, now: float, bonded_count: int) -> bool:
        if not self.bonded_only or bonded_count == 0:
            return True
        return now - self.boot_t < self.window_s

    def rx_allowed(self, peer_bonded: bool | None) -> bool:
        """``peer_bonded`` None = cannot be determined on this platform: then rely on link-layer
        encryption, which is only guaranteed when ``security`` is not "none"."""
        if not self.bonded_only:
            return True
        if peer_bonded is None:
            return self.security != "none"
        return peer_bonded

    @staticmethod
    def new_bonds(previous: set[str], current: set[str]) -> set[str]:
        return current - previous


_DEVICE_RE = re.compile(r"^\s*Device\s+([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s*(.*)$")


def parse_bluetoothctl_devices(text: str) -> dict[str, str]:
    """``Device AA:BB:CC:DD:EE:FF Name`` lines -> {address: name}."""
    out = {}
    for line in (text or "").splitlines():
        m = _DEVICE_RE.match(line)
        if m:
            out[m.group(1).upper()] = m.group(2).strip()
    return out


class BluezControl:
    """Thin ``bluetoothctl`` wrapper (bonded/connected lists, pairable on/off)."""

    def __init__(self, runner: Callable[..., Any] = subprocess.run) -> None:
        self.runner = runner
        self.available = shutil.which("bluetoothctl") is not None or runner is not subprocess.run

    def _ctl(self, *args: str) -> str | None:
        if not self.available:
            return None
        try:
            res = self.runner(["bluetoothctl", *args], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("bluetoothctl %s failed: %s", " ".join(args), exc)
            return None
        return res.stdout if getattr(res, "returncode", 1) == 0 else None

    def _devices(self, kind: str, legacy: str) -> dict[str, str] | None:
        out = self._ctl("devices", kind)  # BlueZ >= 5.65
        devices = parse_bluetoothctl_devices(out or "")
        if not devices and legacy:
            legacy_out = self._ctl(legacy)  # older BlueZ
            if legacy_out is not None:
                return parse_bluetoothctl_devices(legacy_out)
        return devices if out is not None else None

    def bonded(self) -> dict[str, str] | None:
        return self._devices("Paired", "paired-devices")

    def connected(self) -> dict[str, str] | None:
        return self._devices("Connected", "")

    def set_pairable(self, on: bool) -> None:
        self._ctl("pairable", "on" if on else "off")


# ---------------------------------------------------------------------------------- links
class Link:
    name = "base"

    def __init__(self, cfg: BleConfig, clock: Clock) -> None:
        self.cfg = cfg
        self.clock = clock
        self.receiver: Receiver | None = None
        self.on_connection: ConnectionCallback | None = None
        self.on_error: Callable[[str | None], None] | None = None  # None = recovered
        self.on_new_bond: Callable[[str], None] | None = None
        self.policy: PairingPolicy | None = None
        self.peer_bonded: bool | None = None
        self.rejected = 0
        self.sent: collections.deque[bytes] = collections.deque(maxlen=200)  # for tests / dashboard

    @property
    def connected(self) -> bool:
        return False

    def send(self, msg_type: str, **fields: Any) -> None:
        try:
            data = protocol.encode(msg_type, ts_ms=self.clock.wall_ms(), **fields)
        except protocol.ProtocolError as exc:
            log.error("cannot encode %s: %s", msg_type, exc)
            return
        self.sent.append(data)
        self._send_bytes(data)

    def _send_bytes(self, data: bytes) -> None:
        log.debug("link(%s) tx %s", self.name, data[:120])

    def rx_allowed(self) -> bool:
        return self.policy is None or self.policy.rx_allowed(self.peer_bonded)

    def deliver(self, raw_msg: dict[str, Any]) -> None:
        """Validate a decoded phone message and hand it to the receiver."""
        if not self.rx_allowed():
            self.rejected += 1
            log.warning("rejected phone message %r from a device that is not bonded", raw_msg.get("t"))
            return
        msg = protocol.validate_phone(raw_msg, self.cfg.phone_say_min_level)
        if msg is None:
            log.info("ignored phone message %r", raw_msg.get("t"))
            return
        if self.receiver:
            self.receiver(msg)

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass


class NullLink(Link):
    name = "none"


class FakeLink(Link):
    """In-memory link for tests and simulation (``connected`` is settable)."""

    name = "fake"

    def __init__(self, cfg: BleConfig, clock: Clock, connected: bool = False) -> None:
        super().__init__(cfg, clock)
        self._connected = connected

    @property
    def connected(self) -> bool:
        return self._connected

    def set_connected(self, value: bool) -> None:
        self._connected = value
        if self.on_connection:
            self.on_connection(value)

    def messages(self) -> list[dict[str, Any]]:
        import json  # noqa: PLC0415

        return [json.loads(d) for d in self.sent]


class BleLink(Link):
    name = "ble"
    BOND_CHECK_S = 10.0

    def __init__(self, cfg: BleConfig, clock: Clock, control: BluezControl | None = None) -> None:
        super().__init__(cfg, clock)
        from bless import (  # noqa: PLC0415,F401 - raises when unavailable
            BlessServer,
            GATTAttributePermissions,
            GATTCharacteristicProperties,
        )

        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=200)
        self._assembler = protocol.LineAssembler()
        self._connected = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: str | None = None
        self.device_name = device_name(cfg.name_prefix)
        self.control = control or BluezControl()
        self.policy = PairingPolicy(cfg.bonded_only, cfg.pairing_window_s, clock.now(), cfg.security)
        self._bonded: set[str] | None = None
        self._pairable: bool | None = None
        self.security_applied = False

    @property
    def connected(self) -> bool:
        return self._connected

    def _send_bytes(self, data: bytes) -> None:
        if not self._connected:
            return
        try:
            self._queue.put_nowait(data)
        except queue.Full:
            log.warning("BLE send queue full, dropping oldest")
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(data)
            except (queue.Empty, queue.Full):
                pass

    def _on_write(self, characteristic: Any, value: Any, **_: Any) -> None:
        try:
            if str(characteristic.uuid).upper() != protocol.RX_UUID:
                return
            for msg in self._assembler.feed(bytes(value)):
                self.deliver(msg)
        except Exception:  # noqa: BLE001
            log.exception("BLE write handler failed")

    def _bond_housekeeping(self) -> None:
        """Runs in an executor thread: bonded list, new-bond announcement, pairable state."""
        bonded = self.control.bonded()
        if bonded is None:
            return
        current = set(bonded)
        if self._bonded is not None:
            for addr in PairingPolicy.new_bonds(self._bonded, current):
                log.warning("new bonded phone %s (%s)", addr, bonded.get(addr, ""))
                if self.on_new_bond:
                    self.on_new_bond(bonded.get(addr, addr))
        self._bonded = current
        pairable = self.policy.pairable(self.clock.now(), len(current))  # type: ignore[union-attr]
        if pairable != self._pairable:
            self.control.set_pairable(pairable)
            self._pairable = pairable
            log.info("BLE pairable=%s (bonded phones: %d)", pairable, len(current))

    def _check_peer(self) -> bool | None:
        connected = self.control.connected()
        bonded = self.control.bonded()
        if connected is None or bonded is None or not connected:
            return None
        return any(addr in bonded for addr in connected)

    async def _main(self) -> None:
        from bless import BlessServer, GATTAttributePermissions, GATTCharacteristicProperties  # noqa: PLC0415

        loop = asyncio.get_running_loop()
        server = BlessServer(name=self.device_name, loop=loop)
        server.read_request_func = lambda characteristic, **_: characteristic.value
        server.write_request_func = self._on_write
        secure = self.cfg.security != "none"
        rx_perm = GATTAttributePermissions.writeable
        tx_perm = GATTAttributePermissions.readable
        if secure:
            rx_perm |= GATTAttributePermissions.write_encryption_required
            tx_perm |= GATTAttributePermissions.read_encryption_required
        await server.add_new_service(protocol.SERVICE_UUID)
        await server.add_new_characteristic(
            protocol.SERVICE_UUID, protocol.RX_UUID,
            GATTCharacteristicProperties.write | GATTCharacteristicProperties.write_without_response,
            None, rx_perm)
        await server.add_new_characteristic(
            protocol.SERVICE_UUID, protocol.TX_UUID,
            GATTCharacteristicProperties.notify | GATTCharacteristicProperties.read,
            bytearray(b""), tx_perm)
        if secure:
            rx_flags, tx_flags = security_flags(self.cfg.security)
            ok = apply_bluez_flags(server.get_characteristic(protocol.RX_UUID), rx_flags) and \
                apply_bluez_flags(server.get_characteristic(protocol.TX_UUID), tx_flags)
            self.security_applied = ok
            if not ok:
                log.warning("BLE backend does not expose BlueZ security flags; relying on attribute "
                            "permissions and the bonded-only application check")
        await server.start()
        log.info("BLE advertising as %s (Nordic UART Service, security=%s, bonded_only=%s)",
                 self.device_name, self.cfg.security, self.cfg.bonded_only)
        if self.error is not None:
            self.error = None
            if self.on_error:
                self.on_error(None)
        tx = server.get_characteristic(protocol.TX_UUID)
        next_check = 0.0
        next_bond_check = 0.0
        try:
            while not self._stop.is_set():
                now = loop.time()
                if now >= next_bond_check:
                    next_bond_check = now + self.BOND_CHECK_S
                    await loop.run_in_executor(None, self._bond_housekeeping)
                if now >= next_check:
                    next_check = now + 0.5
                    try:
                        conn = bool(await server.is_connected())
                    except Exception:  # noqa: BLE001
                        conn = False
                    if conn != self._connected:
                        if conn:
                            self.peer_bonded = await loop.run_in_executor(None, self._check_peer)
                            log.info("phone connected (bonded=%s)", self.peer_bonded)
                        else:
                            self.peer_bonded = None
                            self._assembler = protocol.LineAssembler()
                            log.info("phone disconnected")
                        self._connected = conn
                        if self.on_connection:
                            self.on_connection(conn)
                try:
                    data = self._queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.02)
                    continue
                for part in protocol.chunk(data, self.cfg.chunk_size):
                    tx.value = bytearray(part)
                    server.update_value(protocol.SERVICE_UUID, protocol.TX_UUID)
                    await asyncio.sleep(self.cfg.chunk_gap_ms / 1000.0)
        finally:
            try:
                await server.stop()
            except Exception:  # noqa: BLE001
                pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                asyncio.run(self._main())
            except Exception as exc:  # noqa: BLE001
                self.error = str(exc)
                log.error("BLE server failed: %s (retrying in 10 s)", exc)
                if self.on_error:
                    self.on_error(self.error)
                if self._connected:
                    self._connected = False
                    if self.on_connection:
                        self.on_connection(False)
                self._stop.wait(10.0)

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="ble", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)


def create_link(cfg: BleConfig, clock: Clock, enabled: bool = True) -> tuple[Link, str | None]:
    """Return (link, error). Falls back to :class:`NullLink` with the reason."""
    if not (enabled and cfg.enabled):
        return NullLink(cfg, clock), None
    try:
        return BleLink(cfg, clock), None
    except Exception as exc:  # noqa: BLE001 - bless missing, no BlueZ/WinRT backend, ...
        log.warning("BLE unavailable, using no-op link: %s", exc)
        return NullLink(cfg, clock), str(exc)
