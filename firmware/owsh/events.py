"""Event types and the priority ``Level`` enum (spec §6.1).

Every event carries ``ts``: the monotonic time of the *source* sample (e.g. the LiDAR reading
that caused a zone change). It is propagated to the haptic engine so the reflex latency
LiDAR sample -> motor on (spec §11 T2) can be logged and measured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class Level(IntEnum):
    """Priority. Lower value = more important. P0 preempts everything."""

    P0 = 0  # CRITICAL: SOS countdown, system FAULT
    P1 = 1  # IMMINENT: Z1 obstacle, DROP, APPROACH P1
    P2 = 2  # WARNING: Z2 obstacle, STEP UP, APPROACH P2, avoid-person
    P3 = 3  # INFO: Z3 notice, friend face, OCR result, scene description
    P4 = 4  # STATUS: ready, button tick, mute toggled

    def preempts(self, other: "Level") -> bool:
        return int(self) < int(other)


class Direction(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    ALL = "all"


@dataclass(frozen=True)
class Event:
    ts: float


@dataclass(frozen=True)
class Heartbeat(Event):
    component: str


@dataclass(frozen=True)
class LidarSample(Event):
    sensor: str  # "forward" | "down"
    dist_m: float | None  # None = no return / invalid
    strength: int = 0


@dataclass(frozen=True)
class ZoneChanged(Event):
    zone: int  # 0 = clear, 3 = notice, 2 = warning, 1 = imminent
    previous: int
    dist_m: float | None


@dataclass(frozen=True)
class DropoffDetected(Event):
    kind: str  # "drop" | "step_up"
    dist_m: float | None
    d0_m: float
    big: bool = False  # large drop / no return -> "Drop ahead" instead of "Step down ahead"


@dataclass(frozen=True)
class ImuSample(Event):
    ax: float
    ay: float
    az: float


@dataclass(frozen=True)
class FallDetected(Event):
    pass


@dataclass(frozen=True)
class TrackInfo:
    track_id: int
    label: str
    score: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in frame pixels
    height_frac: float
    angle_deg: float
    direction: Direction
    ttc_s: float | None
    age_s: float
    is_mover: bool
    missed_s: float = 0.0  # time since the last matching detection (0 = detected in this frame)


@dataclass(frozen=True)
class Detections(Event):
    frame_w: int
    frame_h: int
    tracks: tuple[TrackInfo, ...] = ()
    fps: float = 0.0


@dataclass(frozen=True)
class ApproachAlert(Event):
    track_id: int
    label: str
    direction: Direction
    ttc_s: float
    level: Level
    height_frac: float


@dataclass(frozen=True)
class FaceSeen(Event):
    name: str
    tag: str  # "friend" | "avoid"
    direction: Direction
    score: float


@dataclass(frozen=True)
class FaultChanged(Event):
    component: str
    active: bool
    detail: str = ""


@dataclass(frozen=True)
class ButtonGesture(Event):
    button: str  # "b1" | "b2" | "b3"
    gesture: str  # "press" | "short" | "long" | "double"


@dataclass(frozen=True)
class SpeechSpoken(Event):
    text: str
    level: Level


@dataclass(frozen=True)
class PhoneMessage(Event):
    msg: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhoneConnection(Event):
    connected: bool


@dataclass(frozen=True)
class PowerWarning(Event):
    kind: str  # "undervoltage" | "overheat"
    temp_c: float | None = None
