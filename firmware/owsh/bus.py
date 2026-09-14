"""Thread-safe publish/subscribe event bus.

Dispatch is synchronous in the publisher's thread: this keeps the reflex path (LiDAR thread ->
arbiter -> haptic engine) free of extra queues and thread hops. Handlers MUST therefore be fast
and non-blocking (enqueue work for slow consumers such as BLE or speech). A failing handler is
logged and never breaks the publisher.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TypeVar

from .events import Event

log = logging.getLogger("owsh.bus")

E = TypeVar("E", bound=Event)
Handler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: list[tuple[type, Handler]] = []

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> Callable[[], None]:
        """Subscribe to ``event_type`` and its subclasses. Returns an unsubscribe function."""
        entry = (event_type, handler)
        with self._lock:
            self._subs.append(entry)  # type: ignore[arg-type]

        def unsubscribe() -> None:
            with self._lock:
                if entry in self._subs:
                    self._subs.remove(entry)  # type: ignore[arg-type]

        return unsubscribe

    def publish(self, event: Event) -> None:
        with self._lock:
            subs = list(self._subs)
        for etype, handler in subs:
            if isinstance(event, etype):
                try:
                    handler(event)
                except Exception:  # noqa: BLE001 - a subscriber must never kill a publisher
                    log.exception("handler %r failed for %s", handler, type(event).__name__)
