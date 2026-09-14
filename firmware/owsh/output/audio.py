"""Speech output with a priority queue (spec §7.1).

Queue rules (implemented in the pure :class:`SpeechQueueCore`):

* A higher-priority message interrupts the one being spoken; same or lower priority waits.
* Queued P1/P2 messages older than ``stale_s`` (2 s) are dropped - a late "Stop" is harmful.
* At most ``max_queue`` (3) items wait; when full, the least important (then oldest) item is
  dropped. A P0 item is never dropped in favour of a less important one.
* Mute silences P3-P4 only. Answers to an explicit button request (``requested=True``) are still
  spoken, otherwise a muted user pressing "describe scene" would get silence.

Backends, in ``auto`` order: piper CLI (if a voice model is configured), espeak-ng, pyttsx3,
print. Fixed phrases can be pre-rendered to WAV under ``data/cache/tts/`` (piper/espeak-ng).
"""

from __future__ import annotations

import hashlib
import itertools
import logging
import shutil
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..clock import Clock
from ..config import AudioConfig
from ..events import Level

log = logging.getLogger("owsh.audio")


@dataclass(order=False)
class SpeechItem:
    text: str
    level: Level
    created: float
    requested: bool = False
    cacheable: bool = False
    seq: int = field(default=0)


class SpeechQueueCore:
    """Pure queue logic. Not thread-safe by itself (the worker holds a lock)."""

    def __init__(self, max_queue: int = 3, stale_s: float = 2.0) -> None:
        self.max_queue = max_queue
        self.stale_s = stale_s
        self.muted = False
        self.items: list[SpeechItem] = []
        self.current: SpeechItem | None = None
        self._seq = itertools.count()
        self.dropped: list[tuple[SpeechItem, str]] = []

    def _drop(self, item: SpeechItem, reason: str) -> None:
        self.dropped.append((item, reason))
        del self.dropped[:-50]
        log.info("speech_drop reason=%s level=P%d text=%r", reason, item.level, item.text)

    def push(self, item: SpeechItem) -> bool:
        """Queue ``item``. Returns True if the current utterance must be interrupted."""
        if self.muted and item.level >= Level.P3 and not item.requested:
            self._drop(item, "muted")
            return False
        if any(q.text == item.text and q.level == item.level for q in self.items):
            self._drop(item, "duplicate")
            return False
        item.seq = next(self._seq)
        self.items.append(item)
        if len(self.items) > self.max_queue:
            # least important = highest level number, then oldest
            victim = max(self.items, key=lambda q: (int(q.level), -q.seq))
            self.items.remove(victim)
            self._drop(victim, "queue_full")
        cur = self.current
        return cur is not None and item in self.items and item.level < cur.level

    def pop(self, now: float) -> SpeechItem | None:
        """Next item to speak (most important, then oldest); stale P1/P2 are discarded."""
        for q in list(self.items):
            if q.level in (Level.P1, Level.P2) and now - q.created > self.stale_s:
                self.items.remove(q)
                self._drop(q, "stale")
        if not self.items:
            return None
        best = min(self.items, key=lambda q: (int(q.level), q.seq))
        self.items.remove(best)
        return best

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        if muted:
            for q in [q for q in self.items if q.level >= Level.P3 and not q.requested]:
                self.items.remove(q)
                self._drop(q, "muted")


# ------------------------------------------------------------------------------ backends
class TtsBackend:
    name = "base"

    def speak(self, text: str, lang: str, cacheable: bool = False) -> None:
        """Blocking. Must return early when :meth:`stop` is called from another thread."""
        raise NotImplementedError

    def stop(self) -> None:
        pass

    def set_volume(self, volume: int) -> None:
        pass

    def close(self) -> None:
        self.stop()


class PrintBackend(TtsBackend):
    name = "print"

    def __init__(self, sink: Callable[[str], None] | None = None) -> None:
        self.sink = sink or (lambda s: print(s, flush=True))
        self.spoken: list[str] = []

    def speak(self, text: str, lang: str, cacheable: bool = False) -> None:
        self.spoken.append(text)
        try:
            self.sink(f"[SPEECH {lang}] {text}")
        except UnicodeEncodeError:  # Windows consoles without UTF-8
            self.sink(f"[SPEECH {lang}] {text.encode('ascii', 'replace').decode()}")


class _ProcessBackend(TtsBackend):
    """Runs external processes; stop() kills them."""

    def __init__(self, cfg: AudioConfig, cache_dir: Path) -> None:
        self.cfg = cfg
        self.cache_dir = cache_dir
        self._proc_lock = threading.Lock()
        self._procs: list[subprocess.Popen] = []
        self._stopped = threading.Event()

    def _run(self, args: list[str], stdin: bytes | None = None) -> int:
        with self._proc_lock:
            if self._stopped.is_set():
                return -1
            proc = subprocess.Popen(args, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self._procs.append(proc)
        try:
            _, err = proc.communicate(stdin)
            if proc.returncode not in (0, -9, -15) and not self._stopped.is_set():
                log.warning("%s exited %s: %s", args[0], proc.returncode, (err or b"")[:200])
            return proc.returncode
        finally:
            with self._proc_lock:
                if proc in self._procs:
                    self._procs.remove(proc)

    def _cache_path(self, text: str, voice: str) -> Path:
        h = hashlib.sha256(f"{self.name}|{voice}|{self.cfg.rate_wpm}|{text}".encode()).hexdigest()[:24]
        return self.cache_dir / f"{h}.wav"

    def _play(self, wav: Path) -> None:
        self._run([self.cfg.player, "-q", str(wav)])

    def speak(self, text: str, lang: str, cacheable: bool = False) -> None:
        self._stopped.clear()
        self._speak(text, lang, cacheable)

    def _speak(self, text: str, lang: str, cacheable: bool) -> None:  # pragma: no cover
        raise NotImplementedError

    def stop(self) -> None:
        self._stopped.set()
        with self._proc_lock:
            for p in self._procs:
                try:
                    p.kill()
                except OSError:
                    pass


class EspeakBackend(_ProcessBackend):
    name = "espeak-ng"

    def __init__(self, cfg: AudioConfig, cache_dir: Path) -> None:
        super().__init__(cfg, cache_dir)
        self.bin = shutil.which("espeak-ng")
        if not self.bin:
            raise RuntimeError("espeak-ng not found")
        self.volume = cfg.volume

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, int(volume)))

    def _args(self, lang: str) -> list[str]:
        voice = self.cfg.espeak_voices.get(lang, lang)
        amp = str(int(self.volume * 2))  # espeak amplitude 0..200
        return [self.bin, "-v", voice, "-s", str(self.cfg.rate_wpm), "-a", amp]  # type: ignore[list-item]

    def _speak(self, text: str, lang: str, cacheable: bool) -> None:
        if cacheable and shutil.which(self.cfg.player):
            wav = self._cache_path(text, lang + str(self.volume))
            if not wav.exists():
                wav.parent.mkdir(parents=True, exist_ok=True)
                tmp = wav.with_suffix(".tmp.wav")
                if self._run([*self._args(lang), "-w", str(tmp), text]) == 0 and tmp.exists():
                    tmp.replace(wav)
            if wav.exists() and not self._stopped.is_set():
                self._play(wav)
                return
        self._run([*self._args(lang), text])


class PiperBackend(_ProcessBackend):
    name = "piper"

    def __init__(self, cfg: AudioConfig, cache_dir: Path) -> None:
        super().__init__(cfg, cache_dir)
        self.bin = shutil.which(cfg.piper_bin)
        if not self.bin or not cfg.piper_model or not Path(cfg.piper_model).exists():
            raise RuntimeError("piper binary or voice model not available")
        if not shutil.which(cfg.player):
            raise RuntimeError(f"audio player {cfg.player!r} not found")

    def _speak(self, text: str, lang: str, cacheable: bool) -> None:
        wav = self._cache_path(text, self.cfg.piper_model)
        if not wav.exists():
            wav.parent.mkdir(parents=True, exist_ok=True)
            tmp = wav.with_suffix(".tmp.wav")
            rc = self._run([self.bin, "--model", self.cfg.piper_model, "--output_file", str(tmp)],  # type: ignore[list-item]
                           stdin=text.encode("utf-8"))
            if rc != 0 or not tmp.exists():
                return
            tmp.replace(wav)
        if not self._stopped.is_set():
            self._play(wav)
        if not cacheable:
            try:
                wav.unlink()
            except OSError:
                pass


class Pyttsx3Backend(TtsBackend):
    """Desktop development backend. The engine is created lazily in the speech thread."""

    name = "pyttsx3"

    def __init__(self, cfg: AudioConfig) -> None:
        import pyttsx3  # noqa: PLC0415,F401 - verify importable now

        self.cfg = cfg
        self._engine = None
        self._volume = cfg.volume

    def _ensure(self):
        if self._engine is None:
            import pyttsx3  # noqa: PLC0415

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.cfg.rate_wpm)
            self._engine.setProperty("volume", self._volume / 100.0)
        return self._engine

    def _select_voice(self, engine, lang: str) -> None:
        try:
            for v in engine.getProperty("voices"):
                blob = f"{v.id} {v.name} {getattr(v, 'languages', '')}".lower()
                if (lang == "ko" and ("korean" in blob or "ko-kr" in blob or "ko_kr" in blob)) or \
                   (lang == "en" and ("english" in blob or "en-us" in blob or "en_us" in blob)):
                    engine.setProperty("voice", v.id)
                    return
        except Exception:  # noqa: BLE001
            pass

    def speak(self, text: str, lang: str, cacheable: bool = False) -> None:
        engine = self._ensure()
        self._select_voice(engine, lang)
        engine.say(text)
        engine.runAndWait()

    def stop(self) -> None:
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:  # noqa: BLE001
                pass

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, int(volume)))
        if self._engine is not None:
            try:
                self._engine.setProperty("volume", self._volume / 100.0)
            except Exception:  # noqa: BLE001
                pass


def create_tts_backend(cfg: AudioConfig, cache_dir: Path, sim: bool,
                       override: str | None = None) -> tuple[TtsBackend, str | None]:
    """Return (backend, error). ``error`` is set when the requested/any real backend failed
    and the print fallback is used (-> FAULT ``audio``, spec §5.7 "audio backend init failure")."""
    wanted = override or cfg.backend
    if wanted == "print":
        return PrintBackend(), None
    order = [wanted] if wanted != "auto" else (["pyttsx3", "espeak-ng"] if sim else ["piper", "espeak-ng", "pyttsx3"])
    errors = []
    for name in order:
        try:
            if name == "piper":
                if not cfg.piper_model and wanted == "auto":
                    continue
                return PiperBackend(cfg, cache_dir), None
            if name == "espeak-ng":
                return EspeakBackend(cfg, cache_dir), None
            if name == "pyttsx3":
                return Pyttsx3Backend(cfg), None
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
            log.warning("TTS backend %s unavailable: %s", name, exc)
    return PrintBackend(), "; ".join(errors) or "no TTS backend"


# ------------------------------------------------------------------------------- worker
class SpeechOutput:
    """Speech thread around :class:`SpeechQueueCore` and a :class:`TtsBackend`."""

    def __init__(self, cfg: AudioConfig, backend: TtsBackend, clock: Clock,
                 lang_getter: Callable[[], str],
                 on_spoken: Callable[[str, Level], None] | None = None,
                 on_backend_error: Callable[[str], None] | None = None) -> None:
        self.cfg = cfg
        self.backend = backend
        self.clock = clock
        self.lang_getter = lang_getter
        self.on_spoken = on_spoken
        self.on_backend_error = on_backend_error
        self.core = SpeechQueueCore(cfg.max_queue, cfg.stale_s)
        self._cond = threading.Condition()
        self._stop = False
        self._thread: threading.Thread | None = None
        self.last_text: str | None = None
        self.last_line: str = ""

    @property
    def muted(self) -> bool:
        return self.core.muted

    def set_muted(self, muted: bool) -> None:
        with self._cond:
            self.core.set_muted(muted)

    def say(self, text: str, level: Level, requested: bool = False, cacheable: bool = False) -> None:
        if not text:
            return
        item = SpeechItem(text=text, level=Level(level), created=self.clock.now(),
                          requested=requested, cacheable=cacheable)
        with self._cond:
            interrupt = self.core.push(item)
            self._cond.notify_all()
        if interrupt:
            log.info("speech_preempt by level=P%d text=%r", item.level, text)
            self.backend.stop()

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._stop:
                    item = self.core.pop(self.clock.now())
                    if item is not None:
                        break
                    self._cond.wait(0.2)
                if self._stop:
                    return
                self.core.current = item
            try:
                lang = self.lang_getter()
                log.info("speech_start level=P%d text=%r", item.level, item.text)
                self.last_line = item.text
                if self.on_spoken:
                    self.on_spoken(item.text, item.level)
                if item.level <= Level.P3 or item.requested:
                    self.last_text = item.text
                self.backend.speak(item.text, lang, item.cacheable)
            except Exception as exc:  # noqa: BLE001
                log.exception("TTS backend failed")
                if self.on_backend_error:
                    self.on_backend_error(str(exc))
                if not isinstance(self.backend, PrintBackend):
                    self.backend = PrintBackend()
                    self.backend.speak(item.text, self.lang_getter())
            finally:
                with self._cond:
                    self.core.current = None

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="speech", daemon=True)
            self._thread.start()

    def close(self) -> None:
        with self._cond:
            self._stop = True
            self._cond.notify_all()
        self.backend.stop()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
