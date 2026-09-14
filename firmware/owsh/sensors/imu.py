"""MPU-6050 IMU driver, simulated IMU and the fall detector (spec §5.6).

Fall = free-fall |a| < 0.35 g for >= 80 ms, followed by an impact |a| > 2.5 g within 1 s
(measured from the end of the free-fall phase), then low motion (|a| within 1 +/- 0.15 g)
continuously for 2 s. The low-motion phase must start within ``still_timeout_s`` of the impact.
"""

from __future__ import annotations

import logging
import math
import random
import threading
from collections.abc import Callable

from ..config import ImuConfig

log = logging.getLogger("owsh.imu")

# MPU-6050 registers (InvenSense register map RM-MPU-6000A-00)
REG_SMPLRT_DIV = 0x19
REG_CONFIG = 0x1A
REG_ACCEL_CONFIG = 0x1C
REG_ACCEL_XOUT_H = 0x3B
REG_PWR_MGMT_1 = 0x6B
REG_WHO_AM_I = 0x75
ACCEL_8G = 0x10  # AFS_SEL=2 -> +/-8 g, 4096 LSB/g (impacts exceed 2.5 g, so +/-2 g is too small)
LSB_PER_G_8G = 4096.0


class FallDetector:
    IDLE, FREEFALL, AWAIT_IMPACT, AWAIT_STILL = "idle", "freefall", "await_impact", "await_still"

    def __init__(self, cfg: ImuConfig) -> None:
        self.cfg = cfg
        self.state = self.IDLE
        self._ff_start = 0.0
        self._ff_last = 0.0
        self._impact_t = 0.0
        self._still_start: float | None = None

    def reset(self) -> None:
        self.state = self.IDLE
        self._still_start = None

    def update(self, t: float, ax: float, ay: float, az: float) -> bool:
        """Feed one accelerometer sample in g. Returns True exactly once per detected fall."""
        c = self.cfg
        mag = math.sqrt(ax * ax + ay * ay + az * az)
        if self.state == self.IDLE:
            if mag < c.freefall_g:
                self.state = self.FREEFALL
                self._ff_start = self._ff_last = t
            return False
        if self.state == self.FREEFALL:
            if mag < c.freefall_g:
                self._ff_last = t
                return False
            if self._ff_last - self._ff_start >= c.freefall_min_s - 1e-9:
                self.state = self.AWAIT_IMPACT
                # fall through: this very sample may already be the impact
            else:
                self.state = self.IDLE
                return False
        if self.state == self.AWAIT_IMPACT:
            if mag > c.impact_g:
                self.state = self.AWAIT_STILL
                self._impact_t = t
                self._still_start = None
                log.info("fall: impact %.2f g", mag)
            elif t - self._ff_last > c.impact_window_s:
                self.state = self.IDLE
            return False
        if self.state == self.AWAIT_STILL:
            if abs(mag - 1.0) <= c.still_band_g:
                if self._still_start is None:
                    if t - self._impact_t > c.still_timeout_s:
                        self.reset()
                        return False
                    self._still_start = t
                elif t - self._still_start >= c.still_s - 1e-9:
                    self.reset()
                    log.warning("fall detected")
                    return True
            else:
                self._still_start = None
                if t - self._impact_t > c.still_timeout_s:
                    self.reset()
        return False


class Mpu6050:
    def __init__(self, bus_no: int, addr: int) -> None:
        from smbus2 import SMBus  # noqa: PLC0415 - optional dependency

        self.addr = addr
        self._bus = SMBus(bus_no)
        who = self._bus.read_byte_data(addr, REG_WHO_AM_I)
        if who not in (0x68, 0x70, 0x72, 0x98):  # 0x68 genuine; common clones report others
            log.warning("MPU-6050 WHO_AM_I=0x%02x (unexpected, continuing)", who)
        self._bus.write_byte_data(addr, REG_PWR_MGMT_1, 0x00)  # wake, internal oscillator
        self._bus.write_byte_data(addr, REG_CONFIG, 0x03)  # DLPF ~44 Hz
        self._bus.write_byte_data(addr, REG_SMPLRT_DIV, 9)  # 1 kHz / (1 + 9) = 100 Hz
        self._bus.write_byte_data(addr, REG_ACCEL_CONFIG, ACCEL_8G)

    def read_g(self) -> tuple[float, float, float]:
        d = self._bus.read_i2c_block_data(self.addr, REG_ACCEL_XOUT_H, 6)

        def s16(hi: int, lo: int) -> int:
            v = (hi << 8) | lo
            return v - 65536 if v & 0x8000 else v

        return (s16(d[0], d[1]) / LSB_PER_G_8G, s16(d[2], d[3]) / LSB_PER_G_8G, s16(d[4], d[5]) / LSB_PER_G_8G)

    def close(self) -> None:
        try:
            self._bus.close()
        except Exception:  # noqa: BLE001
            pass


class SimImu:
    """Resting at 1 g with noise. ``trigger_fall()`` plays a free-fall/impact/still sequence."""

    def __init__(self, clock_now: Callable[[], float], seed: int | None = None) -> None:
        self.now = clock_now
        self._rng = random.Random(seed)
        self._fall_t: float | None = None
        self.fail = False

    def trigger_fall(self) -> None:
        self._fall_t = self.now()

    def read_g(self) -> tuple[float, float, float]:
        if self.fail:
            raise OSError("simulated IMU failure")
        n = lambda: self._rng.gauss(0.0, 0.02)  # noqa: E731
        if self._fall_t is not None:
            dt = self.now() - self._fall_t
            if dt < 0.25:
                return (n(), n(), 0.05)
            if dt < 0.30:
                return (1.5, 1.0, 3.2)
            if dt > 4.0:
                self._fall_t = None
            return (n(), 1.0 + n() * 0.5, n())  # lying on the side, still
        return (n(), n(), 1.0 + n())

    def close(self) -> None:
        pass


class ImuWorker:
    RETRY_S = 5.0

    def __init__(self, cfg: ImuConfig, bus, clock, heartbeat, factory: Callable[[], object]) -> None:
        self.cfg = cfg
        self.bus = bus
        self.clock = clock
        self.heartbeat = heartbeat
        self.factory = factory
        self.detector = FallDetector(cfg)
        self.device = None
        self._next_try = 0.0
        self.last_g: tuple[float, float, float] | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._n = 0

    def step(self) -> None:
        from ..events import FallDetected, ImuSample  # noqa: PLC0415

        t = self.clock.now()
        if self.device is None:
            if t < self._next_try:
                return
            try:
                self.device = self.factory()
                log.info("IMU opened")
            except Exception as exc:  # noqa: BLE001
                self._next_try = t + self.RETRY_S
                log.warning("IMU unavailable: %s", exc)
                return
        try:
            ax, ay, az = self.device.read_g()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            log.debug("IMU read failed: %s", exc)
            return
        self.heartbeat("imu")
        self.last_g = (ax, ay, az)
        self._n += 1
        if self._n % 10 == 0:  # 10 Hz is enough for the dashboard
            self.bus.publish(ImuSample(ts=t, ax=ax, ay=ay, az=az))
        if self.detector.update(t, ax, ay, az):
            self.bus.publish(FallDetected(ts=t))

    def _run(self) -> None:
        period = 1.0 / self.cfg.rate_hz
        next_t = self.clock.now()
        while not self._stop.is_set():
            try:
                self.step()
            except Exception:  # noqa: BLE001
                log.exception("imu step failed")
            next_t += period
            delay = next_t - self.clock.now()
            if delay < -period:
                next_t = self.clock.now()
                delay = 0
            self._stop.wait(max(0.0, delay))

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="imu", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self.device is not None:
            try:
                self.device.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
