from owsh.arbiter import Arbiter, Cooldown, SosManager
from owsh.events import ApproachAlert, Direction, DropoffDetected, FaceSeen, FaultChanged, Level, ZoneChanged


def make(cfg, clock, haptics, speech, link, i18n):
    return Arbiter(cfg, clock, haptics, speech, link, i18n)


def test_cooldown():
    c = Cooldown()
    assert c.ready("a", 0.0, 5.0)
    assert not c.ready("a", 4.9, 5.0)
    assert c.ready("b", 4.9, 5.0)
    assert c.ready("a", 5.0, 5.0)


def test_zone_patterns_and_voice(cfg, clock, haptics, speech, link, i18n):
    link.set_connected(True)
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_zone(ZoneChanged(ts=clock.now(), zone=3, previous=0, dist_m=1.8))
    assert haptics.active["zone"] == "zone3" and speech.items == []  # Z3: no voice
    a.on_zone(ZoneChanged(ts=clock.now(), zone=2, previous=3, dist_m=1.0))
    assert haptics.active["zone"] == "zone2"
    assert speech.items == [("Obstacle ahead.", Level.P2, False)]
    a.on_zone(ZoneChanged(ts=clock.now(), zone=1, previous=2, dist_m=0.5))
    assert haptics.active["zone"] == "zone1"
    assert speech.items[-1] == ("Stop.", Level.P1, False)
    # back to Z2 within 5 s: no second "Obstacle ahead" (came from Z1, and cooldown)
    clock.advance(1.0)
    a.on_zone(ZoneChanged(ts=clock.now(), zone=2, previous=1, dist_m=0.8))
    a.on_zone(ZoneChanged(ts=clock.now(), zone=3, previous=2, dist_m=1.5))
    a.on_zone(ZoneChanged(ts=clock.now(), zone=2, previous=3, dist_m=1.1))
    assert [t for t, _, _ in speech.items].count("Obstacle ahead.") == 1
    clock.advance(5.0)
    a.on_zone(ZoneChanged(ts=clock.now(), zone=3, previous=2, dist_m=1.5))
    a.on_zone(ZoneChanged(ts=clock.now(), zone=2, previous=3, dist_m=1.1))
    assert [t for t, _, _ in speech.items].count("Obstacle ahead.") == 2
    a.on_zone(ZoneChanged(ts=clock.now(), zone=0, previous=2, dist_m=None))
    assert "zone" not in haptics.active
    alerts = [m for m in link.messages() if m["t"] == "alert"]
    assert alerts[0]["kind"] == "obstacle" and alerts[0]["level"] == 3 and alerts[1]["level"] == 2
    assert any(m["level"] == 1 and m["text"] == "Stop." for m in alerts)


def test_stop_voice_rate_limited(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    for _ in range(5):
        a.on_zone(ZoneChanged(ts=clock.now(), zone=1, previous=2, dist_m=0.5))
        a.on_zone(ZoneChanged(ts=clock.now(), zone=2, previous=1, dist_m=0.8))
        clock.advance(0.5)
    assert speech.texts().count("Stop.") == 1


def test_dropoff_and_step(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_dropoff(DropoffDetected(ts=clock.now(), kind="drop", dist_m=3.0, d0_m=2.2, big=False))
    assert haptics.names()[-1] == "drop" and speech.items[-1] == ("Step down ahead.", Level.P1, False)
    a.on_dropoff(DropoffDetected(ts=clock.now(), kind="drop", dist_m=None, d0_m=2.2, big=True))
    assert speech.items[-1] == ("Drop ahead.", Level.P1, False)
    a.on_dropoff(DropoffDetected(ts=clock.now(), kind="step_up", dist_m=1.2, d0_m=2.2))
    assert haptics.names()[-1] == "step_up" and speech.items[-1] == ("Step up ahead.", Level.P2, False)


def test_approach(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_approach(ApproachAlert(ts=clock.now(), track_id=4, label="bicycle", direction=Direction.RIGHT,
                                ttc_s=1.2, level=Level.P1, height_frac=0.3))
    assert haptics.played[-1] == ("approach_right", "approach_right", {"level": Level.P1})
    assert speech.items[-1] == ("Watch out, bicycle on the right!", Level.P1, False)
    a.on_approach(ApproachAlert(ts=clock.now(), track_id=5, label="car", direction=Direction.LEFT,
                                ttc_s=3.2, level=Level.P2, height_frac=0.12))
    assert speech.items[-1] == ("Car approaching from the left.", Level.P2, False)


def test_face_friend_avoid_cooldown(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_face(FaceSeen(ts=0, name="Mina", tag="friend", direction=Direction.LEFT, score=0.6))
    assert haptics.names()[-1] == "person_friend_left"
    assert speech.items[-1] == ("Mina is ahead on the left.", Level.P3, False)
    clock.advance(30)
    a.on_face(FaceSeen(ts=0, name="Mina", tag="friend", direction=Direction.LEFT, score=0.6))
    assert len(speech.items) == 1
    a.on_face(FaceSeen(ts=0, name="X", tag="avoid", direction=Direction.CENTER, score=0.5))
    assert haptics.names()[-1] == "person_avoid_center" and speech.items[-1][1] == Level.P2
    clock.advance(31)
    a.on_face(FaceSeen(ts=0, name="Mina", tag="friend", direction=Direction.RIGHT, score=0.6))
    assert speech.items[-1][0] == "Mina is ahead on the right."


def test_critical_fault_repeats_every_10s_and_recovers(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_fault(FaultChanged(ts=clock.now(), component="camera_blocked", active=True))
    assert haptics.names() == ["fault"]
    text, level, _ = speech.items[-1]
    assert level == Level.P0
    assert text == "Camera is covered or too dark. Distance sensors still active."
    a.tick(clock.advance(5.0))
    assert haptics.names() == ["fault"]
    a.tick(clock.advance(5.0))
    assert haptics.names() == ["fault", "fault"]
    assert speech.items[-1] == ("Fault: Camera view.", Level.P0, False)
    a.on_fault(FaultChanged(ts=clock.now(), component="camera_blocked", active=False))
    assert speech.items[-1] == ("Camera recovered.", Level.P2, False)
    a.tick(clock.advance(20.0))
    assert haptics.names() == ["fault", "fault"]


def test_lidar_fault_stops_zone_and_no_still_active_claim(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_zone(ZoneChanged(ts=clock.now(), zone=1, previous=2, dist_m=0.5))
    a.on_fault(FaultChanged(ts=clock.now(), component="lidar_forward", active=True))
    assert "zone" not in haptics.active
    assert speech.items[-1] == ("Front distance sensor not working.", Level.P0, False)
    a.on_fault(FaultChanged(ts=clock.now(), component="camera", active=True))
    assert "still active" not in speech.items[-1][0]


def test_non_critical_fault_announced_once(cfg, clock, haptics, speech, link, i18n):
    a = make(cfg, clock, haptics, speech, link, i18n)
    a.on_fault(FaultChanged(ts=clock.now(), component="faces", active=True))
    assert speech.items[-1] == ("Face recognition not working.", Level.P2, False)
    a.tick(clock.advance(30))
    assert "fault" not in haptics.names() and len(speech.items) == 1


def test_korean_fault_text(cfg, clock, haptics, speech, link):
    from owsh.i18n import I18n

    a = make(cfg, clock, haptics, speech, link, I18n("ko"))
    a.on_fault(FaultChanged(ts=clock.now(), component="camera_blocked", active=True))
    assert speech.items[-1][0] == "카메라가 가려졌거나 너무 어둡습니다. 거리 센서는 계속 작동합니다."


# ---------------------------------------------------------------------------- SOS
def sos(cfg, clock, haptics, speech, link, i18n):
    return SosManager(cfg, clock, haptics, speech, link, i18n)


def test_sos_countdown_then_no_phone_alarm_then_phone(cfg, clock, haptics, speech, link, i18n):
    s = sos(cfg, clock, haptics, speech, link, i18n)
    assert s.trigger("button")
    assert haptics.played[-1] == ("sos_countdown", "sos", {"repeats": 10})
    assert speech.items[-1] == ("Emergency alert in 10 seconds. Press any button to cancel.", Level.P0, True)
    s.tick(clock.advance(9.9))
    assert s.state == s.COUNTDOWN
    s.tick(clock.advance(0.2))
    assert s.state == s.NO_PHONE
    assert haptics.played[-1] == ("sos_countdown", "sos", {"repeats": 60})
    assert speech.items[-1][0] == "Phone not connected."
    n = len(speech.items)
    for _ in range(10):
        s.tick(clock.advance(1.0))
    assert len(speech.items) == n + 1  # repeated after 10 s
    for _ in range(51):
        s.tick(clock.advance(1.0))
    assert s.state == s.PENDING and "sos" not in haptics.active
    link.set_connected(True)
    s.on_connection(True)
    assert s.state == s.SENT
    sent = [m for m in link.messages() if m["t"] == "sos"]
    assert sent[-1]["state"] == "sent" and sent[-1]["reason"] == "button"
    s.tick(clock.advance(5.0))
    assert len([m for m in link.messages() if m["t"] == "sos"]) == len(sent) + 1  # resend every 5 s
    s.on_ack("wrong-id")
    assert s.state == s.SENT
    s.on_ack(sent[-1]["id"])
    assert s.state == s.IDLE and speech.items[-1][0] == "Emergency alert sent."


def test_sos_cancel_during_countdown(cfg, clock, haptics, speech, link, i18n):
    link.set_connected(True)
    s = sos(cfg, clock, haptics, speech, link, i18n)
    s.trigger("fall")
    assert speech.texts()[:2] == ["Fall detected.", "Emergency alert in 10 seconds. Press any button to cancel."]
    clock.advance(4)
    assert s.cancel()
    assert s.state == s.IDLE and "sos" in haptics.stopped
    states = [m["state"] for m in link.messages() if m["t"] == "sos"]
    assert states == ["countdown", "cancelled"]
    s.tick(clock.advance(20))
    assert [m["state"] for m in link.messages() if m["t"] == "sos"] == ["countdown", "cancelled"]


def test_sos_sent_when_phone_connected(cfg, clock, haptics, speech, link, i18n):
    link.set_connected(True)
    s = sos(cfg, clock, haptics, speech, link, i18n)
    s.trigger("button")
    assert not s.trigger("button")  # already running
    s.tick(clock.advance(10.0))
    assert s.state == s.SENT and not s.cancellable
    assert speech.items[-1] == ("Sending emergency alert to the phone.", Level.P1, True)
