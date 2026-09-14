"""Injectable clocks.

All timing logic uses ``Clock.now()`` (monotonic seconds) so that state machines can be
unit-tested with a :class:`FakeClock`. Wall-clock time is only used for protocol timestamps.
"""

from __future__ import annotations

import threading
import time


class Clock:
    """Real clock based on :func:`time.monotonic`."""

    def now(self) -> float:
        return time.monotonic()

    def wall_ms(self) -> int:
        return int(time.time() * 1000)

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class FakeClock(Clock):
    """Manually advanced clock for tests."""

    def __init__(self, start: float = 1000.0, wall_ms: int = 1_700_000_000_000) -> None:
        self._t = float(start)
        self._wall0 = wall_ms
        self._start = float(start)
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._t

    def wall_ms(self) -> int:
        with self._lock:
            return self._wall0 + int((self._t - self._start) * 1000)

    def advance(self, seconds: float) -> float:
        with self._lock:
            self._t += seconds
            return self._t

    def set(self, t: float) -> None:
        with self._lock:
            self._t = float(t)

    def sleep(self, seconds: float) -> None:
        self.advance(max(0.0, seconds))


SYSTEM_CLOCK = Clock()
