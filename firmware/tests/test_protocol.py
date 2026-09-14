import json

import pytest

from owsh.link import protocol as p


def test_uuids_match_spec():
    assert p.SERVICE_UUID == "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
    assert p.RX_UUID == "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
    assert p.TX_UUID == "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


def test_encode_has_type_version_ts_and_newline():
    data = p.encode("alert", ts_ms=1234, id=1, level=1, kind="drop", dir="center", dist_m=None, text="Drop ahead.")
    assert data.endswith(b"\n") and data.count(b"\n") == 1
    obj = json.loads(data)
    assert obj == {"t": "alert", "v": 1, "ts": 1234, "id": 1, "level": 1, "kind": "drop", "dir": "center",
                   "text": "Drop ahead."}


def test_encode_rejects_unknown_type_and_nan():
    with pytest.raises(p.ProtocolError):
        p.encode("bogus")
    obj = json.loads(p.encode("status", ts_ms=1, fps=float("nan"), faults=[]))
    assert "fps" not in obj


@pytest.mark.parametrize("mtu", [23, 27, 64, 185, 247, 517])
def test_chunk_roundtrip_multibyte(mtu):
    text = "앞에 사람 2명, 오른쪽에 자전거. " * 12 + "emoji 🚲"
    data = p.encode("speech", ts_ms=99, text=text, level=3)
    chunks = p.chunks_for_mtu(data, mtu)
    assert all(len(c) <= max(20, mtu - 3) for c in chunks)
    assert b"".join(chunks) == data
    rx = p.LineAssembler()
    msgs = []
    for c in chunks:
        msgs += rx.feed(c)
    assert len(msgs) == 1 and msgs[0]["text"] == text


def test_two_messages_in_one_chunk_and_split_across():
    a = p.encode_phone("ping", id=1)
    b = p.encode_phone("ack", id="abc")
    stream = a + b
    rx = p.LineAssembler()
    out = rx.feed(stream[:5]) + rx.feed(stream[5:len(a) + 3]) + rx.feed(stream[len(a) + 3:])
    assert [m["t"] for m in out] == ["ping", "ack"]


def test_long_text_truncated_to_max_message():
    data = p.encode("speech", ts_ms=1, text="가" * 2000, level=3)
    assert len(data) <= p.MAX_MESSAGE_BYTES
    obj = json.loads(data)
    assert obj["text"].endswith("…") and len(obj["text"]) > 300


def test_oversized_incoming_discarded_then_recovers():
    rx = p.LineAssembler()
    assert rx.feed(b"{" + b"x" * 1500) == []
    assert rx.feed(b"still garbage\n") == []
    assert rx.feed(p.encode_phone("ping", id=7)) == [{"t": "ping", "v": 1, "id": 7}]
    assert rx.errors == 1


def test_bad_json_and_non_objects_ignored():
    rx = p.LineAssembler()
    assert rx.feed(b"not json\n[1,2]\n{\"no_type\":1}\n\n") == []
    assert rx.errors == 3


def test_validate_phone_messages():
    v = p.validate_phone
    assert v({"t": "loc", "v": 1, "lat": 37.5, "lon": 127.0, "acc_m": 8, "addr": " Seoul Station "}) == \
        {"t": "loc", "lat": 37.5, "lon": 127.0, "acc_m": 8.0, "addr": "Seoul Station"}
    assert v({"t": "loc", "lat": 137.5, "lon": 127.0}) is None
    assert v({"t": "loc", "lat": True, "lon": 1}) is None
    assert v({"t": "ack", "id": "a1b2"}) == {"t": "ack", "id": "a1b2"}
    assert v({"t": "ack"}) is None
    assert v({"t": "ping", "id": 3}) == {"t": "ping", "id": 3}
    assert v({"t": "say", "text": "hello"}) == {"t": "say", "text": "hello", "level": 3}
    assert v({"t": "say", "text": "x", "level": 0})["level"] == 2  # cannot preempt P0/P1
    assert v({"t": "say", "text": "x", "level": 9})["level"] == 4
    assert v({"t": "say", "text": "  "}) is None
    assert v({"t": "cfg", "lang": "ko", "muted": True, "volume": 55, "dropoff_sensitivity": "high"}) == \
        {"t": "cfg", "lang": "ko", "muted": True, "volume": 55, "dropoff_sensitivity": "high"}
    assert v({"t": "cfg", "volume": 500, "dropoff_sensitivity": "max", "muted": "yes"}) == {"t": "cfg"}
    assert v({"t": "future_feature", "x": 1}) is None  # unknown types ignored


def test_all_helmet_types_encode():
    for t in p.HELMET_TYPES:
        assert json.loads(p.encode(t, ts_ms=1))["t"] == t
