"""TERRANE Phase 1 — visualization prototype.

Canonical spec: terrane-design-doc.md (Part II). The harmonic-analysis layer
is a Tonality client (see CLAUDE.md); dynamics, terrain, and feel live here.
"""

from .params import Params
from .engine import Engine

__all__ = ["Params", "Engine"]
