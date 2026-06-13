"""Chord-event detection from held MIDI notes (trivial in v1 per the spec).

A chord event fires when the held-note set has changed, contains at least
two notes, and has been stable for a settle time. The note on/off + timestamp
boundary here is the clean event boundary Tonality's future streaming
adapter (gap 5) will slot into.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChordEvent:
    t: float
    midi: tuple[int, ...]  # sorted, with doublings
    pcs: frozenset[int]
    bass_pc: int


class ChordTracker:
    def __init__(self, settle: float = 0.03, min_notes: int = 2):
        self.settle = settle
        self.min_notes = min_notes
        self._held: dict[int, float] = {}  # midi -> velocity
        self._dirty_at: float | None = None
        self._last: tuple[int, ...] = ()

    def note_on(self, midi: int, velocity: float, t: float) -> None:
        self._held[midi] = velocity
        self._dirty_at = t

    def note_off(self, midi: int, t: float) -> None:
        self._held.pop(midi, None)
        # Releases mark dirty but only a sufficiently large held set fires.
        self._dirty_at = t

    def poll(self, t: float) -> ChordEvent | None:
        if self._dirty_at is None or t - self._dirty_at < self.settle:
            return None
        self._dirty_at = None
        held = tuple(sorted(self._held))
        if len(held) < self.min_notes or held == self._last:
            return None
        self._last = held
        return ChordEvent(
            t=t,
            midi=held,
            pcs=frozenset(m % 12 for m in held),
            bass_pc=held[0] % 12,
        )
