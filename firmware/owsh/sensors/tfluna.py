"""Benewake TF-Luna LiDAR over I2C (smbus2) and a simulated sensor.

I2C register map (Benewake TF-Luna product manual, "I2C register table"; cross-checked with
budryerson/TFLuna-I2C_python):

======  ==========  ===============================================
0x00    DIST_LOW    distance, cm (little endian with 0x01)
0x01    DIST_HIGH
0x02    AMP_LOW     signal strength ("amp"/"flux")
0x03    AMP_HIGH
0x04    TEMP_LOW    chip temperature, 0.01 degC
0x05    TEMP_HIGH
0x20    SAVE        write 0x01 to save settings
0x21    SHUTDOWN/REBOOT  write 0x02 to reboot
0x22    SLAVE_ADDR  I2C address, 0x08..0x77, factory 0x10
======  ==========  ===============================================

The manual states that when strength < 100 or == 65535 the measurement is unreliable and the
sensor reports distance 0; the reflex path treats strength < 100 or distance 0 as "no return".
"""

from __future__ import annotations

import logging
import random
import threading
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger("owsh.tfluna")

REG_DIST_L = 0x00
REG_SAVE = 0x20
REG_REBOOT = 0x21
REG_SLAVE_ADDR = 0x22


@dataclass(frozen=True)
class LidarReading:
    dist_m: float  # 0.0 = sensor reported no distance
    strength: int
    temp_c: float | None = None


class TFLunaI2C:
    """One TF-Luna on an I2C bus (continuous ranging mode, factory default 100 Hz)."""

    def __init__(self, bus_no: int, addr: int) -> None:
        from smbus2 import SMBus  # noqa: PLC0415 - optional dependency (extra "pi")

        self.addr = addr
        # A separate SMBus handle per sensor/thread; the kernel i2c-dev driver serialises transfers.
        self._bus = SMBus(bus_no)

    def read(self) -> LidarReading:
        data = self._bus.read_i2c_block_data(self.addr, REG_DIST_L, 6)  # raises OSError on NACK
        dist_cm = data[0] | (data[1] << 8)
        amp = data[2] | (data[3] << 8)
        temp_raw = data[4] | (data[5] << 8)
        return LidarReading(dist_cm / 100.0, amp, temp_raw / 100.0)

    def close(self) -> None:
        try:
            self._bus.close()
        except Exception:  # noqa: BLE001
            pass


class SimLidar:
    """Simulated TF-Luna. ``source()`` returns the distance in metres; <= 0 means no return."""

    def __init__(self, source: Callable[[], float], noise_m: float = 0.01, seed: int | None = None) -> None:
        self.source = source
        self.noise_m = noise_m
        self.fail = False  # set True to simulate an unplugged sensor
        self._rng = random.Random(seed)
        self._lock = threading.Lock()

    def read(self) -> LidarReading:
        if self.fail:
            raise OSError("simulated I2C failure")
        d = float(self.source())
        if d <= 0 or d > 8.0:
            return LidarReading(0.0, 0)
        with self._lock:
            d = max(0.2, d + self._rng.gauss(0.0, self.noise_m))
        return LidarReading(round(d, 2), 1500, 30.0)

    def close(self) -> None:
        pass
