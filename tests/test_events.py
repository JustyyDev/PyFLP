from __future__ import annotations

import pytest

from pyflp._events import AsciiEvent, EventEnum, EventTree, U8Event, WORD
from pyflp.exceptions import EventIDOutOfRange, InvalidEventChunkSize


def test_id_out_of_range():
    with pytest.raises(EventIDOutOfRange, match=str(tuple(range(0, WORD)))):
        U8Event(EventEnum(128), b"\x00")

    with pytest.raises(ValueError):
        AsciiEvent(EventEnum(0), b"1234-decode-me-baby")


def test_invalid_chunk_size():
    with pytest.raises(InvalidEventChunkSize, match="1"):
        U8Event(EventEnum(0), b"12")


def test_eventenum_lookup_on_empty_base():
    """Regression: EventEnum has no members, but EventEnum(id) must resolve.

    Python 3.11.9+ and 3.12+ raise TypeError from enum before _missing_ runs.
    """
    import pyflp
    from pyflp.channel import ChannelID
    from pyflp.project import ProjectID

    assert pyflp  # importing the package registers every EventEnum subclass
    assert EventEnum(21) is ChannelID.Type
    assert EventEnum(ChannelID.Type) is ChannelID.Type
    assert EventEnum(ProjectID.FLVersion) is ProjectID.FLVersion

    used = {int(member) for sub in EventEnum.__subclasses__() for member in sub}
    free = next(i for i in range(255, -1, -1) if i not in used)
    pseudo = EventEnum(free)
    assert int(pseudo) == free
    assert EventEnum(free) is pseudo

    with pytest.raises(ValueError):
        EventEnum(256)
    with pytest.raises(ValueError):
        EventEnum(-1)


def test_event_tree():
    root = EventTree()
    child = EventTree(root)
    assert child in root.children
    event = U8Event(EventEnum(0), b"\x01")
    child.append(event)
    assert root.first(EventEnum(0)) == event
    child.remove(EventEnum(0))
    assert not root
