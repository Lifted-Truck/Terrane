"""MIDI file -> timed note events, and the deterministic fixture runner used
by both the test suite and server-side fixture playback."""

from __future__ import annotations

from dataclasses import dataclass

import mido

from .engine import Engine


@dataclass(frozen=True)
class NoteEvent:
    t: float
    kind: str  # "on" | "off"
    midi: int
    velocity: int


def load_midi_events(path: str) -> list[NoteEvent]:
    events: list[NoteEvent] = []
    for track_time, msg in _absolute_messages(mido.MidiFile(path)):
        if msg.type == "note_on" and msg.velocity > 0:
            events.append(NoteEvent(track_time, "on", msg.note, msg.velocity))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            events.append(NoteEvent(track_time, "off", msg.note, 0))
    events.sort(key=lambda e: (e.t, e.kind == "on", e.midi))
    return events


def _absolute_messages(mid: mido.MidiFile):
    t = 0.0
    for msg in mid:  # mido merges tracks and yields delta seconds
        t += msg.time
        if not msg.is_meta:
            yield t, msg


def run_events(
    engine: Engine,
    events: list[NoteEvent],
    duration: float,
    on_step=None,
) -> None:
    """Drive the engine through events on a fixed control-rate grid.
    Events are applied at the first tick at-or-after their timestamp, so the
    same fixture always produces the same trajectory, bit for bit."""
    dt = 1.0 / engine.params.physics_hz
    steps = int(duration / dt)
    idx = 0
    for _ in range(steps):
        while idx < len(events) and events[idx].t <= engine.t:
            e = events[idx]
            if e.kind == "on":
                engine.note_on(e.midi, e.velocity)
            else:
                engine.note_off(e.midi)
            idx += 1
        engine.step(dt)
        if on_step is not None:
            on_step(engine)
