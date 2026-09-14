import threading
import time

from owsh.clock import SYSTEM_CLOCK
from owsh.events import Level
from owsh.output.audio import PrintBackend, SpeechItem, SpeechOutput, SpeechQueueCore, TtsBackend


def item(text, level, created=0.0, requested=False):
    return SpeechItem(text=text, level=Level(level), created=created, requested=requested)


def test_priority_order_and_fifo_within_level():
    q = SpeechQueueCore()
    q.push(item("info", 3))
    q.push(item("warn", 2))
    q.push(item("info2", 3))
    assert [q.pop(0.0).text for _ in range(3)] == ["warn", "info", "info2"]
    assert q.pop(0.0) is None


def test_higher_priority_interrupts_same_or_lower_waits():
    q = SpeechQueueCore()
    q.current = item("describe scene", 3)
    assert q.push(item("Stop.", 1)) is True
    q.current = item("Stop.", 1)
    assert q.push(item("Stop again", 1)) is False  # same level waits
    assert q.push(item("info", 3)) is False
    assert q.push(item("fault", 0)) is True


def test_stale_p1_p2_dropped_but_not_p0_or_p3():
    q = SpeechQueueCore(stale_s=2.0)
    q.push(item("p1", 1, created=0.0))
    q.push(item("p2", 2, created=0.5))
    q.push(item("p0", 0, created=0.0))
    assert q.pop(2.4).text == "p0"
    assert q.pop(2.4).text == "p2"  # 1.9 s old
    q.push(item("p1b", 1, created=0.0))
    q.push(item("p3", 3, created=0.0))
    assert q.pop(5.0).text == "p3"  # p1b stale (5 s) dropped, p3 kept
    assert any(d[1] == "stale" for d in q.dropped)


def test_max_three_queued_drops_least_important():
    q = SpeechQueueCore(max_queue=3)
    q.push(item("a3", 3))
    q.push(item("b2", 2))
    q.push(item("c4", 4))
    q.push(item("d1", 1))
    assert len(q.items) == 3
    assert "c4" not in [i.text for i in q.items]
    q.push(item("e4", 4))  # itself least important -> dropped
    assert "e4" not in [i.text for i in q.items]
    q.push(item("f0", 0))
    q.push(item("g0", 0))
    q.push(item("h0", 0))
    assert [i.level for i in q.items] == [Level.P0, Level.P0, Level.P0]


def test_mute_only_affects_p3_p4():
    q = SpeechQueueCore(max_queue=10)
    q.push(item("info queued", 3))
    q.set_muted(True)
    assert q.items == []  # queued P3 removed
    q.push(item("info", 3))
    q.push(item("status", 4))
    q.push(item("warn", 2))
    q.push(item("stop", 1))
    q.push(item("fault", 0))
    q.push(item("answer to a button press", 3, requested=True))
    assert sorted(i.text for i in q.items) == ["answer to a button press", "fault", "stop", "warn"]


def test_duplicates_suppressed():
    q = SpeechQueueCore()
    q.push(item("Obstacle ahead.", 2))
    q.push(item("Obstacle ahead.", 2))
    assert len(q.items) == 1


class SlowBackend(TtsBackend):
    name = "slow"

    def __init__(self):
        self.spoken = []
        self.stopped = threading.Event()
        self.started = threading.Event()

    def speak(self, text, lang, cacheable=False):
        self.spoken.append(text)
        self.started.set()
        if text.startswith("long"):
            self.stopped.clear()
            self.stopped.wait(5.0)

    def stop(self):
        self.stopped.set()


def test_speech_output_preempts_running_utterance(cfg):
    backend = SlowBackend()
    spoken_events = []
    out = SpeechOutput(cfg.audio, backend, SYSTEM_CLOCK, lambda: "en",
                       on_spoken=lambda t, lvl: spoken_events.append((t, lvl)))
    out.start()
    try:
        out.say("long description of the scene", Level.P3)
        assert backend.started.wait(2.0)
        t0 = time.monotonic()
        out.say("Stop.", Level.P1)
        deadline = time.monotonic() + 2.0
        while "Stop." not in backend.spoken and time.monotonic() < deadline:
            time.sleep(0.01)
        assert "Stop." in backend.spoken
        assert time.monotonic() - t0 < 1.0  # did not wait for the 5 s utterance
        assert ("Stop.", Level.P1) in spoken_events
        assert out.last_text == "Stop."
    finally:
        out.close()


def test_print_backend_records():
    lines = []
    b = PrintBackend(lines.append)
    b.speak("안녕하세요", "ko")
    assert b.spoken == ["안녕하세요"] and "안녕하세요" in lines[0]
