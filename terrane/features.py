"""Gestural features -> forces (design doc S4.1, Phase 1 subset).

Phase 1 deliberately keeps the force vocabulary simple: note density ->
energy injection, register centroid -> directional bias, voice-leading work
-> kinetic kicks (applied by the engine at chord events). The point is to
verify the feel of terrain + physics, not the final vocabulary.
"""

from __future__ import annotations

import math

from .params import Params


class GestureFeatures:
    def __init__(self) -> None:
        self.density = 0.0          # decaying events/sec estimate
        self.register = 60.0        # EMA of note pitch, velocity-weighted
        self.velocity_mean = 0.0
        self._register_weight = 0.0

    def advance(self, dt: float, tau: float) -> None:
        decay = math.exp(-dt / max(tau, 1e-6))
        self.density *= decay
        self.velocity_mean *= decay
        self._register_weight *= decay

    def note_on(self, midi: int, velocity: float, tau: float) -> None:
        self.density += 1.0 / max(tau, 1e-6)  # unit impulse -> events/sec after decay
        self.velocity_mean += velocity * (1.0 - math.exp(-1.0))
        w = velocity
        total = self._register_weight + w
        self.register = (self.register * self._register_weight + midi * w) / max(total, 1e-9)
        self._register_weight = total


def gesture_force(
    feats: GestureFeatures,
    vx: float,
    vy: float,
    toward_target: tuple[float, float],
    params: Params,
) -> tuple[float, float]:
    speed = math.hypot(vx, vy)
    if speed > 1e-6:
        ux, uy = vx / speed, vy / speed
    else:
        ux, uy = toward_target
    energy = params.g_density * feats.density
    fx = energy * ux
    fy = energy * uy
    # Register centroid biases along the spectral axis: high register -> bright/harmonic end.
    fx += params.g_register * (feats.register - 60.0) / 24.0
    return (fx, fy)
