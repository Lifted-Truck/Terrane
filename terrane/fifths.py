"""Circle-of-fifths geometry. Angles in radians; one fifth = 2*pi/12."""

from __future__ import annotations

import math

TWO_PI = 2.0 * math.pi
FIFTH_STEP = TWO_PI / 12.0


def fifths_index(pc: int) -> int:
    """Position of a pitch class on the circle of fifths (C=0, G=1, D=2, ...)."""
    return (pc * 7) % 12


def fifths_angle(pc: int) -> float:
    return fifths_index(pc) * FIFTH_STEP


def wrap_angle(delta: float) -> float:
    """Wrap to (-pi, pi]."""
    return (delta + math.pi) % TWO_PI - math.pi


def displacement_in_fifths(theta_local: float, theta_home: float) -> float:
    """Signed fifths displacement of the local key from home, in (-6, 6]."""
    return wrap_angle(theta_local - theta_home) / FIFTH_STEP
