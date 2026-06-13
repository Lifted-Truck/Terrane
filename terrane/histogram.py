"""Exponentially decaying pitch-class histograms (maintained by TERRANE;
snapshots are handed to Tonality's infer_key per the integration contract)."""

from __future__ import annotations

import math


class DecayingHistogram:
    def __init__(self, tau: float | None):
        """tau=None means no decay (the session accumulator)."""
        self.tau = tau
        self.weights = [0.0] * 12

    def advance(self, dt: float) -> None:
        if self.tau is None or dt <= 0.0:
            return
        decay = math.exp(-dt / self.tau)
        self.weights = [w * decay for w in self.weights]

    def add(self, pc: int, weight: float) -> None:
        self.weights[pc % 12] += weight

    def total(self) -> float:
        return sum(self.weights)

    def snapshot(self) -> list[float]:
        return list(self.weights)
