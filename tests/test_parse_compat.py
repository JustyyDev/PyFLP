"""Parse regressions that do not need a copyrighted project file."""

from __future__ import annotations

import os
import struct
from pathlib import Path

import pytest

import pyflp
from pyflp._events import AsciiEvent, U32Event
from pyflp.channel import automation_tempo_bpm
from pyflp.project import FileFormat, ProjectID


def _write_flp(path: Path, events: list[bytes], *, ppq: int = 96, channels: int = 0) -> None:
    body = b"".join(events)
    header = struct.pack("<4sIhHH", b"FLhd", 6, FileFormat.Project, channels, ppq)
    path.write_bytes(header + b"FLdt" + struct.pack("<I", len(body)) + body)


def test_parse_synthetic_project(tmp_path: Path):
    path = tmp_path / "synthetic.flp"
    version = AsciiEvent(ProjectID.FLVersion, b"21.2.1\x00")
    tempo = U32Event(ProjectID.Tempo, (158000).to_bytes(4, "little"))
    _write_flp(path, [bytes(version), bytes(tempo)])

    project = pyflp.parse(path)
    assert project.format == FileFormat.Project
    assert project.ppq == 96
    assert str(project.version) == "21.2.1"
    assert project.tempo == 158.0


@pytest.mark.skipif(
    not os.environ.get("PYFLP_OBITUARY_FLP"),
    reason="Set PYFLP_OBITUARY_FLP to the private reconstructed project",
)
def test_parse_obituary_fixture():
    path = Path(os.environ["PYFLP_OBITUARY_FLP"])
    original = path.read_bytes()
    project = pyflp.parse(path)
    assert project.title == "Obituary"
    assert project.artists == "Bwend & Sturm"
    assert project.ppq == 96
    assert project.tempo == 158.0
    assert project.channel_count == 139
    assert len(list(project.channels)) == 139
    notes = slides = 0
    for pattern in project.patterns:
        for note in pattern.notes:
            notes += 1
            slides += int(bool(note.slide))
    assert notes == 15939
    assert slides == 2579
    automations = list(project.channels.automations)
    assert len(automations) == 31
    tempo = next(ch for ch in automations if ch.display_name == "Tempo")
    assert len(list(tempo)) == 8
    assert tempo.minimum == 1250
    assert tempo.maximum == 4250
    bpm = automation_tempo_bpm(next(iter(tempo)).value, tempo.minimum, tempo.maximum)
    assert bpm == pytest.approx(158.0)
    saved = path.with_name("obituary.roundtrip.flp")
    pyflp.save(project, saved)
    try:
        assert saved.read_bytes() == original
    finally:
        saved.unlink(missing_ok=True)
