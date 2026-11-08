from __future__ import annotations

import struct

from pyflp._events import EventTree, IndexedEvent
from pyflp.controller import (
    ControllerID,
    RemoteController,
    RemoteControllerEvent,
    iter_remote_controllers,
)


def test_remote_controller_words_and_roundtrip():
    payload = struct.pack("<HIHHHII", 0, 62, 0, 5, 16384, 8, 469)
    event = RemoteControllerEvent(ControllerID.Remote, payload)
    assert event.STRUCT.build(event.value) == payload

    link = RemoteController(EventTree(init=[IndexedEvent(0, event)]))
    assert link.automation_channel == 62
    assert link.target_id == 5
    assert link.destination_id == 16384
    assert link.parameter == 5
    assert link.controls_vst is False

    high = struct.pack("<HIHHHII", 0, 70, 0, 32803, 11009, 8, 469)
    high_event = RemoteControllerEvent(ControllerID.Remote, high)
    assert high_event.STRUCT.build(high_event.value) == high
    high_link = RemoteController(EventTree(init=[IndexedEvent(0, high_event)]))
    assert high_link.target_id == 32803
    assert high_link.parameter == 32803 & 0x7FFF
    assert high_link.controls_vst is True

    root = EventTree(init=[IndexedEvent(0, event), IndexedEvent(1, high_event)])
    assert [item.automation_channel for item in iter_remote_controllers(root)] == [62, 70]
