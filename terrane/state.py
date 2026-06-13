"""The slewed harmonic state vector h (design doc S7.1): terrain morphs
continuously even though chord events are discrete."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class HarmonicState:
    displacement: float = 0.0  # signed fifths from home
    clarity: float = 0.0       # 0..1, from key-induction margin
    evenness: float = 0.5      # 0..1, DFT recipe
    mode_rel: float = 0.0      # 0 = same mode as home, 1 = cross-mode


class StateSlew:
    def __init__(self) -> None:
        self.current = HarmonicState()
        self.target = HarmonicState()

    def step(self, dt: float, tau: float) -> None:
        alpha = 1.0 - math.exp(-dt / max(tau, 1e-6))
        c, g = self.current, self.target
        c.displacement += alpha * (g.displacement - c.displacement)
        c.clarity += alpha * (g.clarity - c.clarity)
        c.evenness += alpha * (g.evenness - c.evenness)
        c.mode_rel += alpha * (g.mode_rel - c.mode_rel)
