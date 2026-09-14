"""Raspberry Pi power supply / temperature warnings and safe power-off.

``get_throttled`` bits (Raspberry Pi firmware): bit 0 = under-voltage now, bit 1 = ARM frequency
capped now, bit 2 = currently throttled, bit 3 = soft temperature limit active; bits 16-19 are the
"has occurred since boot" versions. Source: ``/sys/devices/platform/soc/soc:firmware/get_throttled``
(hex text) or ``vcgencmd get_throttled`` (``throttled=0x50005``).

Warnings (P2 voice):
* under-voltage continuously for >= ``undervoltage_hold_s`` (10 s) -> "Power is low. Charge the
  battery soon."; repeated at most every ``undervoltage_repeat_s`` (5 min) while it persists,
  also across short recoveries (a flapping supply must not nag every 10 s).
* CPU temperature >= ``overheat_c`` (80 degC) -> "Helmet is overheating."; repeated at most every
  ``overheat_repeat_s`` (5 min) while above ``overheat_clear_c`` (75 degC); re-armed below it.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from ..config import PowerConfig

log = logging.getLogger("owsh.power")

UNDERVOLTAGE_NOW = 1 << 0
THROTTLED_NOW = 1 << 2
SYSFS_THROTTLED = Path("/sys/devices/platform/soc/soc:firmware/get_throttled")
SYSFS_TEMP = Path("/sys/class/thermal/thermal_zone0/temp")


def parse_throttled(text: str | None) -> int | None:
    if not text:
        return None
    value = text.strip()
    if "=" in value:
        value = value.split("=", 1)[1].strip()
    try:
        return int(value, 16)
    except ValueError:
        return None


def read_throttled(runner: Callable[..., object] = subprocess.run) -> int | None:
    try:
        return parse_throttled(SYSFS_THROTTLED.read_text())
    except OSError:
        pass
    if shutil.which("vcgencmd") is None:
        return None
    try:
        res = runner(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_throttled(getattr(res, "stdout", ""))


def read_cpu_temp_c() -> float | None:
    try:
        return int(SYSFS_TEMP.read_text().strip()) / 1000.0
    except (OSError, ValueError):
        return None


class PowerMonitor:
    """Pure: feed ``update(t, throttled_bits, temp_c)`` every poll; returns warnings to speak."""

    def __init__(self, cfg: PowerConfig) -> None:
        self.cfg = cfg
        self.undervoltage: bool | None = None
        self.throttled: bool | None = None
        self.temp_c: float | None = None
        self._uv_since: float | None = None
        self._uv_last_warn: float | None = None
        self._hot_last_warn: float | None = None

    def update(self, t: float, bits: int | None, temp_c: float | None) -> list[str]:
        c = self.cfg
        out: list[str] = []
        self.temp_c = temp_c
        if bits is None:
            self.undervoltage = self.throttled = None
            self._uv_since = None
        else:
            self.undervoltage = bool(bits & UNDERVOLTAGE_NOW)
            self.throttled = bool(bits & THROTTLED_NOW)
            if self.undervoltage:
                if self._uv_since is None:
                    self._uv_since = t
                if t - self._uv_since >= c.undervoltage_hold_s - 1e-9 and (
                        self._uv_last_warn is None or t - self._uv_last_warn >= c.undervoltage_repeat_s - 1e-9):
                    self._uv_last_warn = t
                    out.append("undervoltage")
            else:
                self._uv_since = None
        if temp_c is not None:
            if temp_c >= c.overheat_c:
                if self._hot_last_warn is None or t - self._hot_last_warn >= c.overheat_repeat_s - 1e-9:
                    self._hot_last_warn = t
                    out.append("overheat")
            elif temp_c < c.overheat_clear_c:
                self._hot_last_warn = None
        return out


class PowerWorker:
    def __init__(self, cfg: PowerConfig, clock, on_status: Callable[[PowerMonitor], None],
                 on_warning: Callable[[str], None], bits_reader: Callable[[], int | None] = read_throttled,
                 temp_reader: Callable[[], float | None] = read_cpu_temp_c) -> None:
        self.cfg = cfg
        self.clock = clock
        self.monitor = PowerMonitor(cfg)
        self.on_status = on_status
        self.on_warning = on_warning
        self.bits_reader = bits_reader
        self.temp_reader = temp_reader
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def step(self) -> list[str]:
        warnings = self.monitor.update(self.clock.now(), self.bits_reader(), self.temp_reader())
        self.on_status(self.monitor)
        for w in warnings:
            log.warning("power warning: %s (temp=%s)", w, self.monitor.temp_c)
            self.on_warning(w)
        return warnings

    def _run(self) -> None:
        while True:
            try:
                self.step()
            except Exception:  # noqa: BLE001
                log.exception("power monitor failed")
            if self._stop.wait(self.cfg.poll_s):
                return

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="power", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


class PowerControl:
    """Safe power-off. In simulation it only logs."""

    def __init__(self, sim: bool, runner: Callable[..., object] = subprocess.run) -> None:
        self.sim = sim
        self.runner = runner
        self.requested = False

    def poweroff(self) -> bool:
        self.requested = True
        if self.sim:
            log.warning("poweroff requested (simulation: not executed)")
            return True
        # The service user may power off via polkit/logind, or via the sudoers rule that
        # scripts/setup_pi.sh installs for "systemctl poweroff".
        for cmd in (["systemctl", "poweroff"], ["sudo", "-n", "systemctl", "poweroff"]):
            try:
                res = self.runner(cmd, capture_output=True, text=True, timeout=10)
            except (OSError, subprocess.SubprocessError) as exc:
                log.error("%s failed: %s", " ".join(cmd), exc)
                continue
            if getattr(res, "returncode", 1) == 0:
                log.warning("poweroff: %s", " ".join(cmd))
                return True
            log.error("%s returned %s: %s", " ".join(cmd), getattr(res, "returncode", "?"),
                      (getattr(res, "stderr", "") or "")[:200])
        return False
