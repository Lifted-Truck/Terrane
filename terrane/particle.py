"""The damped particle (design doc S8): m*x'' = -grad U + F - gamma*v,
semi-implicit Euler at control rate. Forces move it; nothing ever sets x."""

from __future__ import annotations


class Particle:
    def __init__(self, x: float = 0.5, y: float = 0.5):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0

    def kick(self, dvx: float, dvy: float) -> None:
        self.vx += dvx
        self.vy += dvy

    def step(
        self,
        dt: float,
        force: tuple[float, float],
        grad: tuple[float, float],
        mass: float,
        friction: float,
    ) -> None:
        ax = (force[0] - grad[0] - friction * self.vx) / mass
        ay = (force[1] - grad[1] - friction * self.vy) / mass
        self.vx += dt * ax
        self.vy += dt * ay
        self.x += dt * self.vx
        self.y += dt * self.vy
