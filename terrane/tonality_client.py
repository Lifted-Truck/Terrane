"""The single boundary with Tonality. Everything harmonic-combinatorial is
delegated; nothing here re-derives what the engine ships (design doc S11).

Contracts consumed (integrations/terrane/response.md in the Tonality repo):
- infer_key over decaying-histogram snapshots; margin is the confidence
  scalar, stable per profile version (we pin kk-1982.1 via clarity_ref).
- Near-silence raises ValueError -> rendered as "no tonal information".
- Evenness = dft_magnitudes[n-1]/n for cardinality n (documented recipe).
- voice_leading_realized for register-aware harmonic effort (gap 6, shipped).
"""

from __future__ import annotations

from dataclasses import dataclass

from mts.analysis import infer_key, voice_leading_realized
from mts.core.bitmask import mask_from_pcs
from mts.core.realization import Realization
from mts.core.setclass import dft_magnitudes

EXPECTED_PROFILE_VERSION = "kk-1982.1"


@dataclass(frozen=True)
class KeyReading:
    tonic_pc: int
    mode: str  # "major" | "minor"
    score: float
    margin: float
    profile_version: str
    # The ranking is plural by contract; keep the top of it so consumers
    # (e.g. the cadence stopgap) don't collapse to a single winner.
    top: tuple[tuple[int, str], ...] = ()


def read_key(weights: list[float], min_total: float) -> KeyReading | None:
    """Ranked key induction over a histogram snapshot, gated per the
    near-silence contract. None means: no evidence, not 'no key'."""
    if sum(weights) < min_total:
        return None
    try:
        result = infer_key(weights)
    except ValueError:
        return None
    best = result.candidates[0]
    return KeyReading(
        tonic_pc=best.tonic_pc,
        mode=best.mode,
        score=best.score,
        margin=result.margin,
        profile_version=result.profile_version,
        top=tuple((c.tonic_pc, c.mode) for c in result.candidates[:3]),
    )


def chord_evenness(pcs: set[int]) -> float | None:
    """Distance-from-nearest-even-chord in [0, 1] via the DFT recipe.
    |f_n| = |f_(12-n)|, so cardinalities above 6 index the mirror bin."""
    n = len(pcs)
    if n < 2 or n > 11:
        return None
    index = min(n, 12 - n) - 1
    return dft_magnitudes(mask_from_pcs(pcs))[index] / n


def harmonic_effort(source_midi: list[int], target_midi: list[int]) -> float:
    """Register-aware minimal voice-leading work in semitones."""
    return float(
        voice_leading_realized(
            Realization.from_midi(source_midi), Realization.from_midi(target_midi)
        ).distance
    )
