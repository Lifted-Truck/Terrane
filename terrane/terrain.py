"""Gaussian-sum potential terrain (design doc S7).

Domain is [0,1]^2. The x axis is the designated harmonic<->inharmonic
spectral axis (S5); y carries the fifths-displacement translation.

Mappings (S7.3, load-bearing):
- clarity -> ruggedness: weights interpolate between one deep basin nearest
  the terrain target (clarity 1) and uniform shallow wells (clarity 0).
- evenness -> basin position: the terrain target's x slides along the
  spectral axis; the dominant basin is additionally pulled toward it.
- fifths displacement -> translation of the whole configuration (y).
- mode relationship -> sigma asymmetry (sketch level).

Only weights/centers change with h; the particle's position is never
touched. Continuity is the physics' job, and the physics gets it for free.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .params import Params
from .state import HarmonicState


@dataclass
class Anchor:
    name: str
    x: float
    y: float
    depth: float  # > 0; applied as a negative (well) weight
    sigma: float


def default_anchors() -> list[Anchor]:
    """8 hand-placed timbral anchors. Names are Phase 2 sound charters;
    in Phase 1 they are landmarks. Positions/depths/sigmas are live controls."""
    return [
        Anchor("glass", 0.80, 0.75, 1.00, 0.16),
        Anchor("reed", 0.78, 0.30, 0.90, 0.15),
        Anchor("brass", 0.55, 0.55, 0.95, 0.17),
        Anchor("wood", 0.50, 0.20, 0.85, 0.15),
        Anchor("bell", 0.45, 0.85, 0.90, 0.15),
        Anchor("grit", 0.25, 0.40, 0.90, 0.16),
        Anchor("smoke", 0.22, 0.70, 0.85, 0.15),
        Anchor("static", 0.10, 0.15, 0.80, 0.14),
    ]


@dataclass
class TerrainConfig:
    """Effective per-frame Gaussian parameters."""

    centers: list[tuple[float, float]]
    weights: list[float]  # negative = well
    sigmas: list[tuple[float, float]]  # anisotropic (sx, sy)
    target: tuple[float, float]
    dominant_index: int


class Terrain:
    def __init__(self, params: Params, anchors: list[Anchor] | None = None):
        self.params = params
        self.anchors = anchors if anchors is not None else default_anchors()
        self.habit = [0.0] * len(self.anchors)  # habituation stub accumulator

    def target_point(self, h: HarmonicState) -> tuple[float, float]:
        p = self.params
        tx = p.evenness_x_min + h.evenness * (p.evenness_x_max - p.evenness_x_min)
        ty = 0.5 + p.disp_gain * h.displacement
        return (tx, ty)

    def config(self, h: HarmonicState) -> TerrainConfig:
        p = self.params
        tx, ty = self.target_point(h)
        shift_y = p.disp_gain * h.displacement
        focus = []
        for a in self.anchors:
            d2 = (a.x - tx) ** 2 + (a.y + shift_y - ty) ** 2
            focus.append(math.exp(-d2 / (2.0 * p.focus_rho**2)))
        peak = max(focus) or 1.0

        centers: list[tuple[float, float]] = []
        weights: list[float] = []
        sigmas: list[tuple[float, float]] = []
        for a, f in zip(self.anchors, focus):
            rel = f / peak
            # clarity 1: depth concentrated on the basin nearest the target;
            # clarity 0: uniform shallow wells (splintered, restless).
            depth = p.depth_scale * a.depth * (
                h.clarity * rel + (1.0 - h.clarity) * p.shallow_frac
            )
            idx = len(weights)
            depth *= 1.0 + p.habituation_gain * p.habituation_polarity * self.habit[idx]
            cx = a.x + 0.20 * rel * h.clarity * (tx - a.x)  # evenness pull on the active basin
            cy = a.y + shift_y
            stretch = 1.0 + p.mode_asym * h.mode_rel
            centers.append((cx, cy))
            weights.append(-depth)
            sigmas.append((a.sigma * stretch, a.sigma / stretch))
        dominant = max(range(len(weights)), key=lambda i: -weights[i])
        return TerrainConfig(centers, weights, sigmas, (tx, ty), dominant)

    @staticmethod
    def potential(cfg: TerrainConfig, x: float, y: float) -> float:
        u = 0.0
        for (cx, cy), w, (sx, sy) in zip(cfg.centers, cfg.weights, cfg.sigmas):
            dx, dy = x - cx, y - cy
            u += w * math.exp(-(dx * dx / (2 * sx * sx) + dy * dy / (2 * sy * sy)))
        return u

    def gradient(self, cfg: TerrainConfig, x: float, y: float) -> tuple[float, float]:
        gx = gy = 0.0
        for (cx, cy), w, (sx, sy) in zip(cfg.centers, cfg.weights, cfg.sigmas):
            dx, dy = x - cx, y - cy
            g = w * math.exp(-(dx * dx / (2 * sx * sx) + dy * dy / (2 * sy * sy)))
            gx += g * (-dx / (sx * sx))
            gy += g * (-dy / (sy * sy))
        # Soft walls keep the particle in the viewport without position clamps.
        p = self.params
        if x < 0.0:
            gx += 2 * p.wall_k * x
        elif x > 1.0:
            gx += 2 * p.wall_k * (x - 1.0)
        if y < 0.0:
            gy += 2 * p.wall_k * y
        elif y > 1.0:
            gy += 2 * p.wall_k * (y - 1.0)
        return (gx, gy)

    def deposit_habit(self, cfg: TerrainConfig, x: float, y: float, dt: float) -> None:
        """Habituation stub: residence near an anchor accumulates slowly."""
        if self.params.habituation_gain == 0.0:
            return
        i = cfg.dominant_index
        cx, cy = cfg.centers[i]
        if (x - cx) ** 2 + (y - cy) ** 2 < cfg.sigmas[i][0] ** 2:
            self.habit[i] = min(self.habit[i] + 0.01 * dt, 1.0)
