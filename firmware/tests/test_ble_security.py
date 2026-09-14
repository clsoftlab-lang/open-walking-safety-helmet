import types

from owsh.link import protocol
from owsh.link.ble import (
    BluezControl,
    FakeLink,
    PairingPolicy,
    apply_bluez_flags,
    parse_bluetoothctl_devices,
    security_flags,
)


def test_security_flags():
    assert security_flags("none") == ([], [])
    assert security_flags("encrypt") == (["encrypt-write"], ["encrypt-read", "encrypt-notify"])
    rx, tx = security_flags("authenticated")
    assert rx == ["encrypt-authenticated-write"] and "encrypt-authenticated-notify" in tx


def test_apply_bluez_flags_and_fallback():
    char = types.SimpleNamespace(gatt=types.SimpleNamespace(_flags=["write", "write-without-response"]))
    assert apply_bluez_flags(char, ["encrypt-write"])
    assert apply_bluez_flags(char, ["encrypt-write"])  # idempotent
    assert char.gatt._flags == ["write", "write-without-response", "encrypt-write"]
    assert not apply_bluez_flags(types.SimpleNamespace(), ["encrypt-write"])  # other backends


def test_pairing_policy():
    p = PairingPolicy(bonded_only=True, window_s=120, boot_t=1000.0)
    assert p.pairable(5000.0, bonded_count=0)  # first phone can always pair
    assert p.pairable(1119.0, bonded_count=1)  # window after boot
    assert not p.pairable(1121.0, bonded_count=1)
    assert p.rx_allowed(True) and not p.rx_allowed(False)
    assert p.rx_allowed(None)  # unknown peer: link-layer encryption enforced (security=encrypt)
    assert not PairingPolicy(True, 120, 0, security="none").rx_allowed(None)
    open_policy = PairingPolicy(bonded_only=False, window_s=0, boot_t=0)
    assert open_policy.rx_allowed(False) and open_policy.pairable(1e9, 3)
    assert PairingPolicy.new_bonds({"A"}, {"A", "B"}) == {"B"}


def test_parse_bluetoothctl_devices():
    text = "Device 11:22:33:AA:bb:CC Galaxy S24\n[bluetooth]# junk\nDevice 01:02:03:04:05:06 \n"
    assert parse_bluetoothctl_devices(text) == {"11:22:33:AA:BB:CC": "Galaxy S24", "01:02:03:04:05:06": ""}


def test_bluez_control_with_fake_runner():
    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        out = ""
        if cmd[1:] == ["devices", "Paired"]:
            out = "Device 11:22:33:44:55:66 Phone\n"
        if cmd[1:] == ["devices", "Connected"]:
            out = "Device 11:22:33:44:55:66 Phone\n"
        return types.SimpleNamespace(returncode=0, stdout=out, stderr="")

    ctl = BluezControl(runner)
    assert ctl.bonded() == {"11:22:33:44:55:66": "Phone"}
    assert ctl.connected() == {"11:22:33:44:55:66": "Phone"}
    ctl.set_pairable(False)
    assert calls[-1] == ["bluetoothctl", "pairable", "off"]


def test_link_rejects_messages_from_unbonded_peer(cfg, clock):
    link = FakeLink(cfg.ble, clock, connected=True)
    got = []
    link.receiver = got.append
    link.policy = PairingPolicy(cfg.ble.bonded_only, cfg.ble.pairing_window_s, clock.now(), cfg.ble.security)
    msg = {"t": "cfg", "v": 1, "muted": True}
    link.peer_bonded = False
    link.deliver(msg)
    assert got == [] and link.rejected == 1
    link.peer_bonded = True
    link.deliver(msg)
    assert got == [{"t": "cfg", "muted": True}]


def test_ble_defaults_are_secure(cfg):
    assert cfg.ble.security == "encrypt" and cfg.ble.bonded_only is True
    assert cfg.ble.say_min_interval_s == 3.0 and cfg.ble.pairing_window_s == 120.0
    assert cfg.ble.confirm_volume_below == 30
    assert protocol.validate_phone({"t": "say", "text": "x", "level": 0})["level"] == 2
