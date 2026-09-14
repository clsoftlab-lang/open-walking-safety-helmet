"""Scene description text (spec §5.3 "Describe scene"): up to 5 objects sorted by closeness
(bbox height), grouped by class and direction, e.g. "2 people ahead, bicycle on the right"."""

from __future__ import annotations

from ..events import TrackInfo
from ..i18n import I18n


def describe_scene(tracks: list[TrackInfo] | tuple[TrackInfo, ...], i18n: I18n, max_objects: int = 5) -> str:
    if not tracks:
        return i18n.t("describe.nothing")
    closest = sorted(tracks, key=lambda tr: tr.height_frac, reverse=True)[:max_objects]
    groups: dict[tuple[str, str], int] = {}
    for tr in closest:  # dict keeps first-seen (closest-first) order
        key = (tr.label, tr.direction.value)
        groups[key] = groups.get(key, 0) + 1
    parts = [
        i18n.t("describe.group", what=i18n.class_name(label, count), dir=i18n.t(f"describe.dir.{direction}"))
        for (label, direction), count in groups.items()
    ]
    text = ", ".join(parts)
    text = text[:1].upper() + text[1:]
    return text + "."
