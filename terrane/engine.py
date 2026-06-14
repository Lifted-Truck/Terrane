"""The TERRANE engine: MIDI in -> harmonic state -> home -> terrain ->
particle. Pure simulated time — the caller owns the clock, which is what
makes trajectories deterministic and the acceptance criteria testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .chords import ChordEvent, ChordTracker
from .features import GestureFeatures, gesture_force
from .fifths import displacement_in_fifths, fifths_angle
from .histogram import DecayingHistogram
from .home import CadenceEvent, HomeIntegrator, StopgapCadenceDetector
from .params import Params
from .particle import Particle
from .state import StateSlew
from .terrain import Anchor, Terrain
from .tonality_client import KeyReading, chord_evenness, harmonic_effort, read_key


@dataclass
class EventLog:
    cadences: list[CadenceEvent] = field(default_factory=list)
    crystallized_at: float | None = None
    chord_count: int = 0


class Engine:
    def __init__(self, params: Params | None = None, anchors: list[Anchor] | None = None):
        self.params = params if params is not None else Params()
        self.t = 0.0
        self.fast_hist = DecayingHistogram(self.params.hist_fast_tau)
        self.session_hist = DecayingHistogram(None)
        self.tracker = ChordTracker()
        self.home = HomeIntegrator(self.params)
        self.cadence_detector = StopgapCadenceDetector()
        self.slew = StateSlew()
        self.terrain = Terrain(self.params, anchors)
        self.particle = Particle()
        self.features = GestureFeatures()
        self.log = EventLog()
        self.last_reading: KeyReading | None = None
        self.last_chord: ChordEvent | None = None
        self.last_effort = 0.0
        self._next_key_poll = 0.0
        self._cfg = self.terrain.config(self.slew.current)

    # ---- input (timestamps implicit: events land at current engine time) ----

    def note_on(self, midi: int, velocity: int) -> None:
        w = velocity / 127.0
        self.fast_hist.add(midi % 12, w)
        self.session_hist.add(midi % 12, w)
        self.features.note_on(midi, w, self.params.fast_tau)
        self.tracker.note_on(midi, w, self.t)

    def note_off(self, midi: int) -> None:
        self.tracker.note_off(midi, self.t)

    # ---- control-rate step ----

    def step(self, dt: float) -> None:
        self.t += dt
        self.fast_hist.advance(dt)
        self.features.advance(dt, self.params.fast_tau)

        chord = self.tracker.poll(self.t)
        if chord is not None:
            self._on_chord(chord)
        elif self.t >= self._next_key_poll:
            # Catch decay-to-silence between events (clarity must fall).
            self._refresh_reading()

        self.home.update(dt, self.t, self.last_reading)
        if self.home.crystallized and self.log.crystallized_at is None:
            self.log.crystallized_at = self.home.crystallized_at

        self._set_state_targets()
        self.slew.step(dt, self.params.slew_tau)
        self._cfg = self.terrain.config(self.slew.current)

        tx, ty = self._cfg.target
        dx, dy = tx - self.particle.x, ty - self.particle.y
        norm = math.hypot(dx, dy)
        toward = (dx / norm, dy / norm) if norm > 1e-6 else (1.0, 0.0)
        force = gesture_force(
            self.features, self.particle.vx, self.particle.vy, toward, self.params
        )
        grad = self.terrain.gradient(self._cfg, self.particle.x, self.particle.y)
        self.particle.step(dt, force, grad, self.params.mass, self.params.friction)
        self.terrain.deposit_habit(self._cfg, self.particle.x, self.particle.y, dt)

    # ---- internals ----

    def _refresh_reading(self) -> None:
        self._next_key_poll = self.t + self.params.key_poll_interval
        self.last_reading = read_key(
            self.fast_hist.snapshot(), self.params.min_hist_weight
        )

    def _on_chord(self, chord: ChordEvent) -> None:
        self.log.chord_count += 1
        self._refresh_reading()

        cadence = self.cadence_detector.observe(
            chord.pcs, chord.bass_pc, chord.t, self.last_reading, self.params
        )
        if cadence is not None:
            jump = self.home.apply_cadence(cadence)
            cadence.evidence["jump_applied"] = jump
            self.log.cadences.append(cadence)

        if self.last_chord is not None:
            effort = harmonic_effort(list(self.last_chord.midi), list(chord.midi))
            self.last_effort = effort
            cx, cy = self._cfg.centers[self._cfg.dominant_index]
            dx, dy = cx - self.particle.x, cy - self.particle.y
            norm = math.hypot(dx, dy)
            ux, uy = (dx / norm, dy / norm) if norm > 1e-6 else (1.0, 0.0)
            kick = self.params.g_vl * effort
            self.particle.kick(kick * ux, kick * uy)

        evenness = chord_evenness(set(chord.pcs))
        if evenness is not None:
            self.slew.target.evenness = evenness
        self.last_chord = chord

    def _set_state_targets(self) -> None:
        target = self.slew.target
        reading = self.last_reading
        if reading is None:
            target.clarity = 0.0
            return
        target.clarity = min(reading.margin / self.params.clarity_ref, 1.0)
        if self.home.crystallized:
            target.displacement = displacement_in_fifths(
                fifths_angle(reading.tonic_pc), self.home.theta
            )
            target.mode_rel = 0.0 if reading.mode == self.home.mode else 1.0

    # ---- render snapshot ----

    def snapshot(self) -> dict:
        h = self.slew.current
        cfg = self._cfg
        return {
            "t": self.t,
            "particle": {
                "x": self.particle.x,
                "y": self.particle.y,
                "vx": self.particle.vx,
                "vy": self.particle.vy,
            },
            "terrain": {
                "centers": cfg.centers,
                "weights": cfg.weights,
                "sigmas": cfg.sigmas,
                "target": cfg.target,
                "dominant": cfg.dominant_index,
                "anchors": [a.name for a in self.terrain.anchors],
            },
            "h": {
                "displacement": h.displacement,
                "clarity": h.clarity,
                "evenness": h.evenness,
                "mode_rel": h.mode_rel,
            },
            "compass": {
                "crystallized": self.home.crystallized,
                "theta_home": self.home.theta,
                "home_mode": self.home.mode,
                "local_tonic_pc": self.last_reading.tonic_pc if self.last_reading else None,
                "local_mode": self.last_reading.mode if self.last_reading else None,
                "margin": self.last_reading.margin if self.last_reading else 0.0,
                "confidence": self.home.confidence(self.last_reading),
            },
            "features": {
                "density": self.features.density,
                "register": self.features.register,
                "last_effort": self.last_effort,
            },
            "session_hist": self.session_hist.snapshot(),
            "fast_hist": self.fast_hist.snapshot(),
            # Currently-sounding notes [midi, velocity01], so the (minimal,
            # browser-side) audio prototype can voice what is being analysed.
            "held": [[m, round(v, 3)] for m, v in sorted(self.tracker._held.items())],
        }

    # ---- manual overrides (live controls) ----

    def drop_anchor(self, tonic_pc: int | None = None, mode: str | None = None) -> None:
        """Pin home explicitly (S6.4). With no arguments, pins at the local key."""
        reading = self.last_reading
        if tonic_pc is None and reading is not None:
            tonic_pc, mode = reading.tonic_pc, reading.mode
        if tonic_pc is None:
            return
        self.home.theta = fifths_angle(tonic_pc)
        self.home.mode = mode or "major"
        self.home.crystallized = True
        self.home.crystallized_at = self.t

    def reset(self) -> None:
        self.__init__(self.params, self.terrain.anchors)
