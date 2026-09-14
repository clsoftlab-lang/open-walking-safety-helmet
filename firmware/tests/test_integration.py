"""End-to-end in --sim without camera: reflex latency, SOS by button, fault injection."""

import time

import pytest

from owsh.app import App, RunOptions
from owsh.config import Config


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.005)
    return False


@pytest.fixture
def app(tmp_path):
    cfg = Config()
    cfg.vision.enabled = False
    cfg.faces.enabled = False
    cfg.ocr.enabled = False
    cfg.general.data_dir = str(tmp_path)
    cfg.sim.noise_m = 0.0
    a = App(cfg, RunOptions(sim=True, window=False, tts="print", ble=False))
    a.start()
    yield a
    a.close()


def test_reflex_obstacle_to_motor_latency(app):
    assert wait_for(lambda: app.watchdog.active_faults() == [] and app.reflex.last["down"] is not None)
    time.sleep(0.2)
    app.sim_state.forward_m = 0.5
    assert wait_for(lambda: app.haptics.intensities[1] >= 1.0, 1.0)
    assert app.haptics.backend.duties[1] == 0.75  # capped at the backend
    assert app.haptics.last_latency_ms is not None and app.haptics.last_latency_ms <= 60.0  # spec T2
    assert wait_for(lambda: "Stop." in app.speech.backend.spoken, 2.0)
    app.sim_state.forward_m = 0.0
    assert wait_for(lambda: app.reflex.zone.zone == 0, 1.5)


def test_reflex_works_without_vision_and_lidar_fault_injection(app):
    assert app.vision is None
    time.sleep(0.3)
    app.sim_lidars["forward"].fail = True
    assert wait_for(lambda: "lidar_forward" in app.watchdog.active_faults(), 2.0)
    assert wait_for(lambda: any("Front distance sensor not working" in s for s in app.speech.backend.spoken), 2.0)
    app.sim_lidars["forward"].fail = False
    assert wait_for(lambda: "lidar_forward" not in app.watchdog.active_faults(), 2.0)


def test_sos_hold_b3_and_cancel_with_any_button(app):
    app.buttons.edge("b3", True)
    assert wait_for(lambda: app.sos.state == app.sos.COUNTDOWN, 4.0)
    app.buttons.edge("b3", False)
    time.sleep(0.1)
    assert app.sos.state == app.sos.COUNTDOWN
    app.buttons.edge("b1", True)
    assert wait_for(lambda: app.sos.state == app.sos.IDLE, 1.0)
    app.buttons.edge("b1", False)
    time.sleep(0.6)
    assert app.sos.state == app.sos.IDLE
    assert any("cancelled" in s for s in app.speech.backend.spoken)


def test_drop_off_in_sim(app):
    time.sleep(0.3)
    app.sim_state.down_m = 0.0  # no return -> DROP
    assert wait_for(lambda: "Drop ahead." in app.speech.backend.spoken, 2.0)


def test_dashboard_render_and_keys_without_window(app):
    from owsh.sim.dashboard import Dashboard

    dash = Dashboard(app)
    img = dash.render()
    assert img.ndim == 3 and img.shape[1] > 640
    assert dash.handle_key(ord("3"))  # B3 short -> status report
    assert wait_for(lambda: any("Phone not connected" in s for s in app.speech.backend.spoken), 2.0)
    assert dash.handle_key(ord("d"))  # B3 double -> mute
    assert wait_for(lambda: app.speech.muted, 1.0)
    assert dash.handle_key(ord("l"))  # unplug forward LiDAR
    assert app.sim_lidars["forward"].fail
    assert not dash.handle_key(27)  # Esc quits


def test_phone_messages_through_link(app):
    from owsh.link import protocol

    msgs = []
    app.link.receiver = lambda m: msgs.append(m)
    rx = protocol.LineAssembler()
    for chunk in protocol.chunks_for_mtu(protocol.encode_phone("cfg", dropoff_sensitivity="high", volume=40), 23):
        for raw in rx.feed(chunk):
            app.link.deliver(raw)
    assert msgs == [{"t": "cfg", "volume": 40, "dropoff_sensitivity": "high"}]
    app.controller.on_phone(msgs[0])
    assert app.reflex.dropoff.sensitivity == "high"


def spoken(app, fragment):
    return any(fragment in s for s in app.speech.backend.spoken)


def test_safety_reducing_cfg_is_confirmed_by_voice(app):
    c = app.controller
    c.on_phone({"t": "cfg", "muted": True})
    assert app.speech.muted
    assert wait_for(lambda: spoken(app, "Voice info muted by phone"), 2.0)
    c.on_phone({"t": "cfg", "volume": 20})
    assert wait_for(lambda: spoken(app, "Volume set to 20 percent by phone"), 2.0)
    c.on_phone({"t": "cfg", "dropoff_sensitivity": "low"})
    assert app.reflex.dropoff.sensitivity == "low"
    assert wait_for(lambda: spoken(app, "Drop-off sensitivity set to low by phone"), 3.0)
    n = len(app.speech.backend.spoken)
    c.on_phone({"t": "cfg", "volume": 60})  # not safety-reducing: no confirmation
    time.sleep(0.3)
    assert not any("Volume set to 60" in s for s in app.speech.backend.spoken[n:])


def test_phone_say_rate_limited(app):
    c = app.controller
    c.on_phone({"t": "say", "text": "first message", "level": 3})
    c.on_phone({"t": "say", "text": "second message", "level": 3})
    assert wait_for(lambda: spoken(app, "first message"), 2.0)
    time.sleep(0.3)
    assert not spoken(app, "second message")
    app.cfg.ble.say_min_interval_s = 0.1
    time.sleep(0.15)
    c.on_phone({"t": "say", "text": "third message", "level": 3})
    assert wait_for(lambda: spoken(app, "third message"), 2.0)


def test_shutdown_chord_in_sim(app):
    app.cfg.power.shutdown_delay_s = 0.05
    app.buttons.inject_shutdown_chord()
    assert wait_for(lambda: spoken(app, "Shutting down."), 2.0)
    assert wait_for(lambda: app.power_control.requested, 2.0)
    assert app.sos.state == app.sos.IDLE


def test_status_contains_power_fields(app, cfg):
    from owsh.link.ble import FakeLink
    from owsh.sensors.power import UNDERVOLTAGE_NOW, PowerMonitor

    link = FakeLink(app.cfg.ble, app.clock, connected=True)
    app.link = link
    mon = PowerMonitor(app.cfg.power)
    mon.update(0.0, UNDERVOLTAGE_NOW, 50.0)
    app.controller.power = mon
    app.controller.send_status(force=True)
    status = [m for m in link.messages() if m["t"] == "status"][-1]
    assert status["undervoltage"] is True and status["throttled"] is False
