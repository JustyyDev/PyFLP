# PyFLP - An FL Studio project file (.flp) parser
# Copyright (C) 2022 demberto
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details. You should have received a copy of the
# GNU General Public License along with this program. If not, see
# <https://www.gnu.org/licenses/>.

"""Contains the types used by MIDI and remote ("internal") controllers."""

from __future__ import annotations

import enum
import struct
from typing import Iterator, cast

import construct as c

from pyflp._events import DATA, EventEnum, EventTree, IndexedEvent, StructEventBase
from pyflp._models import EventModel, ModelReprMixin

__all__ = ["RemoteController", "iter_remote_controllers"]


class MIDIControllerEvent(StructEventBase):
    STRUCT = c.Struct("_u1" / c.GreedyBytes)


class RemoteControllerEvent(StructEventBase):
    STRUCT = c.Struct(
        "_u1" / c.Optional(c.Bytes(2)),  # 2
        "_u2" / c.Optional(c.Byte),  # 3
        "_u3" / c.Optional(c.Byte),  # 4
        "parameter_data" / c.Optional(c.Int16ul),  # 6
        "destination_data" / c.Optional(c.Int16sl),  # 8
        "_u4" / c.Optional(c.Bytes(8)),  # 16
        "_u5" / c.Optional(c.Bytes(4)),  # 20
    ).compile()


@enum.unique
class ControllerID(EventEnum):
    MIDI = (DATA + 18, MIDIControllerEvent)
    Remote = (DATA + 19, RemoteControllerEvent)


class RemoteController(EventModel, ModelReprMixin):
    """![](https://bit.ly/3S0i4Zf)

    *New in FL Studio v3.3.0*.
    """

    def _words(self) -> tuple[int, int, int, int, int, int, int] | None:
        """Unpack a 20-byte remote-controller record.

        Layout, checked against FL 21 files: uint16, uint32 automation channel,
        uint16, uint16 target, uint16 destination, uint32, uint32. The event
        struct stays byte-preserving; this only reads those integers.
        """
        event = cast(StructEventBase, self.events.first(ControllerID.Remote))
        payload = event.STRUCT.build(event.value)
        if len(payload) != 20:
            return None
        return struct.unpack("<HIHHHII", payload)

    @property
    def automation_channel(self) -> int | None:
        """Channel iid of the automation clip this link controls.

        ``None`` when the record is not the 20-byte form.
        """
        words = self._words()
        if words is None:
            return None
        return words[1]

    @property
    def target_id(self) -> int | None:
        """Numeric link target stored in the record.

        This is not a parameter name. Tempo links observed in one FL 21
        project use ``5``. Channel pitch uses ``4``. Channel volume uses ``0``.
        Other targets stay as the stored integer, including values above
        ``0x7FFF``.
        """
        words = self._words()
        if words is None:
            return None
        return words[3]

    @property
    def destination_id(self) -> int | None:
        """Numeric destination stored beside :attr:`target_id`.

        For channel pitch and channel volume this is the target channel iid.
        Other destinations (inserts, project tempo) are left as the integer FL
        stored. ``16384`` appears on the project tempo and master-pitch links
        and is not converted further.
        """
        words = self._words()
        if words is None:
            return None
        return words[4]

    @property
    def parameter(self) -> int | None:
        """Low 15 bits of :attr:`target_id`.

        Kept for existing callers. Prefer :attr:`target_id`, which preserves
        the high bit.
        """
        target = self.target_id
        if target is None:
            return None
        return target & 0x7FFF

    @property
    def controls_vst(self) -> bool | None:
        """Whether bit 15 of :attr:`target_id` is set.

        Older text called this bit a VST flag. That meaning is not established
        by the files this decoder was checked against, so the raw
        :attr:`target_id` is the value to keep.
        """
        target = self.target_id
        if target is None:
            return None
        return bool(target & 0x8000)


def iter_remote_controllers(root: EventTree) -> Iterator[RemoteController]:
    """Yield each remote-controller link in a project event tree."""
    for event in root.get(ControllerID.Remote):
        yield RemoteController(EventTree(init=[IndexedEvent(0, event)]))
