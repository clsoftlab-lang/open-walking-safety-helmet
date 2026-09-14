"""Spoken phrases (spec §7.1). ``owsh/i18n/<lang>.json`` maps message id -> text with
``{placeholders}``. Missing keys fall back to English, then to the key itself, so a missing
translation never silences a warning.
"""

from __future__ import annotations

import json
import logging
import string
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger("owsh.i18n")

I18N_DIR = Path(__file__).resolve().parent
FALLBACK_LANG = "en"
# A language is "verified" only after review by a native speaker who is blind or an O&M
# instructor (spec, global project rules). Unverified languages get a first-boot notice.
VERIFIED_LANGS = frozenset({"en", "ko"})


def available_languages() -> list[str]:
    return sorted(p.stem for p in I18N_DIR.glob("*.json"))


@lru_cache(maxsize=None)
def load_phrases(lang: str) -> dict[str, str]:
    path = I18N_DIR / f"{lang}.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError(f"{path} must be a flat object of strings")
    return data


def placeholders(text: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(text) if field}


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class I18n:
    def __init__(self, lang: str = FALLBACK_LANG) -> None:
        self._lock = threading.Lock()
        self._lang = FALLBACK_LANG
        self.set_lang(lang)

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def verified(self) -> bool:
        return self._lang in VERIFIED_LANGS

    def set_lang(self, lang: str) -> bool:
        if lang not in available_languages():
            log.warning("language %r not available, keeping %r", lang, self._lang)
            return False
        with self._lock:
            self._lang = lang
        return True

    def has(self, key: str) -> bool:
        return key in load_phrases(self._lang) or key in load_phrases(FALLBACK_LANG)

    def t(self, key: str, **params: Any) -> str:
        phrases = load_phrases(self._lang)
        text = phrases.get(key)
        if text is None:
            text = load_phrases(FALLBACK_LANG).get(key)
            if text is None:
                log.error("missing phrase %r", key)
                text = key
            else:
                log.warning("phrase %r missing in %s, using %s", key, self._lang, FALLBACK_LANG)
        try:
            return text.format_map(_SafeDict({k: v for k, v in params.items()}))
        except (ValueError, IndexError):
            return text

    def sentence(self, key: str, **params: Any) -> str:
        """Like :meth:`t` but capitalises the first letter (for phrases that start with a
        placeholder such as ``{what} approaching``)."""
        text = self.t(key, **params)
        return text[:1].upper() + text[1:] if text else text

    def class_name(self, label: str, count: int = 1) -> str:
        base = f"class.{label}"
        if not self.has(f"{base}.one"):
            base = "class.object"
        if count <= 1:
            return self.t(f"{base}.one")
        return self.t(f"{base}.many", count=count)

    def component(self, component: str) -> str:
        key = f"component.{component}"
        return self.t(key) if self.has(key) else component
