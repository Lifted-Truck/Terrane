"""The relational home system (design doc S6): home is a slow particle on the
circle of fifths, confidence-gated, cadence-impulsed, ROOTEDNESS-damped."""

from __future__ import annotations

from dataclasses import dataclass, field

from .fifths import FIFTH_STEP, fifths_angle, wrap_angle
from .params import Params
from .tonality_client import KeyReading


@dataclass(frozen=True)
class CadenceEvent:
    """Shaped like Tonality's planned gap-7 evidenced events so the stopgap
    detector below can be deleted, not refactored, when that ships."""

    t: float
    kind: str  # "authentic"
    from_root_pc: int
    to_root_pc: int
    evidence: dict


class StopgapCadenceDetector:
    """THROWAWAY (see integrations/terrane/response.md, gap 7).

    Root proxy = bass pc (fixtures use root position). V-I = root motion down
    a perfect fifth landing on the current key's tonic with confident margin.
    """

    def __init__(self) -> None:
        self._prev_bass: int | None = None

    def observe(
        self,
        pcs: frozenset[int],
        bass_pc: int,
        t: float,
        reading: KeyReading | None,
        params: Params,
    ) -> CadenceEvent | None:
        prev, self._prev_bass = self._prev_bass, bass_pc
        if prev is None or reading is None:
            return None
        if reading.margin < params.cadence_margin:
            return None
        if (prev - bass_pc) % 12 != 7:
            return None
        # Arrival must be a root-position major or minor triad whose tonic is
        # among the top-ranked key candidates — a cadence tonicizes a key the
        # exposure-based estimator already considers plausible, even when it
        # isn't (yet) the winner. Consumes the plural ranking by design.
        rel = frozenset((p - bass_pc) % 12 for p in pcs)
        if rel == {0, 4, 7}:
            mode = "major"
        elif rel == {0, 3, 7}:
            mode = "minor"
        else:
            return None
        ranked = [tonic for tonic, m in reading.top if m == mode]
        if bass_pc not in ranked:
            return None
        return CadenceEvent(
            t=t,
            kind="authentic",
            from_root_pc=prev,
            to_root_pc=bass_pc,
            evidence={
                "margin": reading.margin,
                "root_motion": -7,
                "arrival_mode": mode,
                "arrival_rank": [t_ for t_, _ in reading.top].index(bass_pc),
            },
        )


@dataclass
class HomeIntegrator:
    params: Params
    crystallized: bool = False
    theta: float = 0.0
    mode: str = "major"
    crystallized_at: float | None = None
    _cross_mode_since: float | None = field(default=None, repr=False)

    def _pull_rate(self) -> float:
        r = min(max(self.params.rootedness, 0.0), 1.0)
        return self.params.home_k_max * (1.0 - r) ** 2

    def confidence(self, reading: KeyReading | None) -> float:
        if reading is None or reading.margin < self.params.gate_margin:
            return 0.0
        return min(reading.margin / self.params.clarity_ref, 1.0)

    def update(self, dt: float, t: float, reading: KeyReading | None) -> None:
        if not self.crystallized:
            if reading is not None and reading.margin >= self.params.crystallization_margin:
                self.theta = fifths_angle(reading.tonic_pc)
                self.mode = reading.mode
                self.crystallized = True
                self.crystallized_at = t
            return
        conf = self.confidence(reading)
        if conf <= 0.0 or reading is None:
            self._cross_mode_since = None
            return
        gap = wrap_angle(fifths_angle(reading.tonic_pc) - self.theta)
        self.theta += dt * self._pull_rate() * conf * gap
        # Mode flips only after sustained, confident, near-home cross-mode play.
        if reading.mode != self.mode and abs(gap) < 0.75 * FIFTH_STEP:
            if self._cross_mode_since is None:
                self._cross_mode_since = t
            elif t - self._cross_mode_since >= self.params.mode_flip_time:
                self.mode = reading.mode
                self._cross_mode_since = None
        else:
            self._cross_mode_since = None

    def apply_cadence(self, event: CadenceEvent) -> float:
        """Discrete impulse toward the cadenced tonic. Returns the jump applied."""
        if not self.crystallized:
            return 0.0
        gap = wrap_angle(fifths_angle(event.to_root_pc) - self.theta)
        jump = self.params.cadence_impulse * gap
        self.theta += jump
        return jump
