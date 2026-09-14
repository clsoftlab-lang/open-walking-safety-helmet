from owsh.bus import EventBus
from owsh.events import ButtonGesture
from owsh.input.buttons import ButtonInput, ButtonStateMachine


def machine(cfg, name="b2", has_double=True, long_s=1.5):
    return ButtonStateMachine(name, cfg.buttons, has_double, long_s)


def press(m, t0, t1, polls=()):
    out = m.on_edge(True, t0)
    out += m.poll(t0 + 0.05)
    for p in polls:
        out += m.poll(p)
    out += m.on_edge(False, t1)
    out += m.poll(t1 + 0.05)
    return out


def test_short_press_single_button_immediate(cfg):
    m = machine(cfg, "b1", has_double=False)
    assert press(m, 0.0, 0.2) == ["press", "short"]


def test_short_press_waits_for_double_gap(cfg):
    m = machine(cfg)
    assert press(m, 0.0, 0.2) == ["press"]
    assert m.poll(0.55) == []  # 0.35 s after release
    assert m.poll(0.61) == ["short"]  # >= 0.4 s after release
    assert m.poll(1.0) == []


def test_double_press(cfg):
    m = machine(cfg)
    out = press(m, 0.0, 0.15)
    out += press(m, 0.45, 0.6)  # second press 0.30 s after first release
    assert out == ["press", "press", "double"]
    assert m.poll(2.0) == []


def test_two_slow_presses_are_two_shorts(cfg):
    m = machine(cfg)
    out = press(m, 0.0, 0.15)
    out += m.poll(0.7)
    out += press(m, 1.0, 1.15)
    out += m.poll(1.7)
    assert out == ["press", "short", "press", "short"]


def test_long_press_fires_while_held(cfg):
    m = machine(cfg, "b1", has_double=False)
    assert m.on_edge(True, 0.0) == []  # not yet debounced
    assert m.poll(0.04) == ["press"]
    assert m.poll(1.49) == []
    assert m.poll(1.51) == ["long"]
    assert m.poll(2.5) == []
    assert m.on_edge(False, 3.0) == []
    assert m.poll(3.1) == []


def test_b3_long_requires_3s_hold(cfg):
    bus = EventBus()
    got = []
    bus.subscribe(ButtonGesture, lambda e: got.append((e.button, e.gesture)))
    from owsh.clock import FakeClock

    bi = ButtonInput(cfg.buttons, bus, FakeClock())
    bi.edge("b3", True, 0.0)
    bi.poll(0.05)
    bi.poll(1.6)
    bi.poll(2.9)
    assert ("b3", "long") not in got
    bi.poll(3.01)
    assert got == [("b3", "press"), ("b3", "long")]


def test_medium_press_ignored(cfg):
    m = machine(cfg, "b1", has_double=False)
    assert press(m, 0.0, 1.0) == ["press"]  # 0.8 s <= 1.0 s < 1.5 s


def test_debounce_bounce_does_not_stick(cfg):
    m = machine(cfg, "b3", long_s=3.0)
    out = m.on_edge(True, 0.0)
    out += m.on_edge(False, 0.005)  # bounce
    out += m.on_edge(True, 0.010)
    out += m.poll(0.045)
    assert out == ["press"]
    # the real release is accepted once stable
    out = m.on_edge(False, 0.1)
    out += m.poll(0.2)
    out += m.poll(0.6)
    assert out == ["short"]
    assert m.poll(5.0) == []  # never a phantom long press


def test_cancel_swallows_current_press_cycle(cfg):
    m = machine(cfg, "b3", long_s=3.0)
    m.on_edge(True, 0.0)
    assert m.poll(0.05) == ["press"]
    m.cancel()
    assert m.poll(3.5) == []  # no long -> no new SOS
    assert m.on_edge(False, 4.0) == []
    assert m.poll(4.1) == []
    assert press(m, 5.0, 5.1) == ["press"]  # next cycle works normally
    assert m.poll(5.6) == ["short"]


def test_inject_keyboard_gesture(cfg):
    bus = EventBus()
    got = []
    bus.subscribe(ButtonGesture, lambda e: got.append((e.button, e.gesture)))
    from owsh.clock import FakeClock

    bi = ButtonInput(cfg.buttons, bus, FakeClock())
    bi.inject("b2", "double")
    assert got == [("b2", "press"), ("b2", "double")]
    got.clear()
    bus.subscribe(ButtonGesture, lambda e: bi.cancel_all() if e.gesture == "press" else None)
    bi.inject("b3", "short")
    assert got == [("b3", "press")]  # swallowed after cancel
