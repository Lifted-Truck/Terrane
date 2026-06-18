"""Synthetic MIDI test fixtures (design doc Part II). Deterministic by
construction — chord lists are literal, no randomness. Regenerate with:
    python -m terrane.fixtures
"""

from __future__ import annotations

import os

import mido

MAJ = (0, 4, 7)
MIN = (0, 3, 7)
DOM7 = (0, 4, 7, 10)
MIN7 = (0, 3, 7, 10)
MAJ7 = (0, 4, 7, 11)
AUG = (0, 4, 8)            # perfectly even → evenness 1.0 (far harmonic end of x)
QUARTAL = (0, 5, 10)       # stacked fourths, fairly even
CLUSTER = (0, 1, 2)        # dense → low evenness (far inharmonic end of x)
CLUSTER4 = (0, 1, 2, 3)


def chord(root_pc: int, quality: tuple[int, ...]) -> list[int]:
    """Root-position voicing with the bass in octave 3 (bass pc = root,
    which the stopgap cadence detector's root proxy relies on)."""
    bass = 48 + (root_pc % 12)
    return [bass + i for i in quality]


def write_chords(path: str, chords: list[tuple[list[int], float]], velocity: int = 80) -> None:
    """chords = [(midi_notes, duration_seconds), ...] played back to back."""
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    ticks_per_second = 960  # 480 tpb at 120 bpm

    def t(seconds: float) -> int:
        return round(seconds * ticks_per_second)

    gap = 0.04  # release-to-next-attack gap so held sets fully separate
    for notes, dur in chords:
        for i, n in enumerate(notes):
            track.append(mido.Message("note_on", note=n, velocity=velocity, time=t(gap) if i == 0 else 0))
        for i, n in enumerate(notes):
            track.append(mido.Message("note_off", note=n, velocity=0, time=t(dur - gap) if i == 0 else 0))
    mid.save(path)


def _seq(progression: list[tuple[int, tuple[int, ...]]], dur: float) -> list[tuple[list[int], float]]:
    return [(chord(r, q), dur) for r, q in progression]


# Progressions as (root_pc, quality). C=0, D=2, E=4, F=5, G=7, A=9, B=11.
C_SETTLE = [(0, MAJ), (9, MIN), (5, MAJ), (0, MAJ)]          # I vi IV I — no V-I adjacency
C_DIATONIC = [(0, MAJ), (5, MAJ), (7, MAJ), (0, MAJ),        # I IV V I vi IV V I
              (9, MIN), (5, MAJ), (7, MAJ), (0, MAJ)]


def build_all(out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []

    def w(name: str, chords: list[tuple[list[int], float]]) -> None:
        path = os.path.join(out_dir, name)
        write_chords(path, chords)
        written.append(path)

    # 1. Diatonic progression held in one key (convergence)
    w("diatonic_hold.mid", _seq(C_DIATONIC * 4, 1.0))

    # 2a. Pivot-chord modulation to the dominant (lazy drift)
    pivot = C_DIATONIC * 2 + [(9, MIN), (2, DOM7), (7, MAJ)] + \
            [(7, MAJ), (0, MAJ), (2, DOM7), (7, MAJ)] * 6
    w("pivot_modulation.mid", _seq(pivot, 1.0))

    # 2b. Abrupt tritone modulation (urgency, continuity stress test)
    tritone = C_DIATONIC * 2 + [(6, MAJ), (11, MAJ), (1, DOM7), (6, MAJ)] * 6
    w("tritone_modulation.mid", _seq(tritone, 1.0))

    # 3. Modulate-and-stay, >= 3 minutes (naturalization). C ~24s, E ~170s.
    e_major = [(4, MAJ), (9, MAJ), (11, DOM7), (4, MAJ),
               (1, MIN), (9, MAJ), (11, DOM7), (4, MAJ)]
    stay = C_DIATONIC * 3 + [(0, MAJ), (11, DOM7), (4, MAJ)] + e_major * 21
    w("modulate_and_stay.mid", _seq(stay, 1.0))

    # 4. Chromatic/atonal sequence after a settled start (gating, ruggedness).
    clusters = []
    for k in range(45):  # ~45 s of near-uniform pc coverage
        root = (k * 5 + (k * k) % 7) % 12
        shape = [(0, 1, 2), (0, 1, 3, 6), (0, 2, 3), (0, 1, 4, 5)][k % 4]
        clusters.append(([48 + (root + i) % 24 for i in shape], 1.0))
    w("chromatic.mid", _seq(C_SETTLE * 3, 1.0) + clusters)

    # 5. Repeated 4-chord loop, many traversals (repetition/plasticity stub)
    w("loop4.mid", _seq([(0, MAJ), (9, MIN), (5, MAJ), (7, MAJ)] * 30, 1.0))

    # 6. Two-route-same-destination pair (hysteresis). Both end identically in
    # Eb — but briefly: a long shared tail would erase the very history the
    # pair exists to measure.
    eb_tail = [(3, MAJ), (8, MAJ), (10, DOM7), (3, MAJ)]
    route_a = C_SETTLE * 2 + [(0, MAJ), (5, MAJ), (10, MAJ), (3, MAJ)] * 3 + eb_tail
    route_b = C_SETTLE * 2 + [(0, MAJ), (7, MAJ), (2, MAJ), (9, MAJ), (4, MAJ),
                              (11, MAJ), (6, MAJ), (1, MAJ), (8, MAJ), (3, MAJ)] + eb_tail
    w("route_a.mid", _seq(route_a, 1.0))
    w("route_b.mid", _seq(route_b, 1.0))

    # --- Demonstration walks (manifold-travel showcases, not acceptance tests) ---
    # Each starts by settling C so home crystallizes, then drives the harmonic
    # target across a deliberate path. Played through the same fixture player.

    # Walk A — fifths journey (y-axis travel). Diatonic triads only (clarity
    # stays high), modulating by fifths WITHOUT V-I cadences (I-V-IV-I per key,
    # so home is not impulse-pulled and lags behind via ROOTEDNESS). Displacement
    # swings sharpward then flatward → the target sweeps up then down the y axis.
    def key_block(k):
        return [(k % 12, MAJ), ((k + 7) % 12, MAJ), ((k + 5) % 12, MAJ), (k % 12, MAJ)]
    # Establish with cadential C major (V-I anchors home firmly at C, avoiding
    # the C-major / A-minor relative ambiguity of the I-vi-IV-I settle phrase).
    intro = C_DIATONIC
    sharpward = [0, 7, 2, 9, 4]          # C G D A E
    flatward = [4, 9, 2, 7, 0, 5, 10, 3]  # back down, then F Bb Eb
    journey = list(intro)
    for k in sharpward + flatward:
        journey += key_block(k)
    w("walk_fifths_journey.mid", _seq(journey, 1.5))

    # Walk B — spectral sweep (x-axis travel). Hold the tonal center near C so
    # home stays put, but morph chord evenness from dense clusters → sevenths →
    # triads → augmented and back. The target slides along the harmonic↔inharmonic
    # axis; the particle tracks it left↔right when clarity permits.
    sweep_qualities = [CLUSTER4, CLUSTER, MIN7, DOM7, MAJ7, MAJ, QUARTAL, AUG,
                       QUARTAL, MAJ, MAJ7, DOM7, MIN7, CLUSTER, CLUSTER4]
    spectral = list(intro) + [(0, q) for q in sweep_qualities] + [(0, q) for q in reversed(sweep_qualities)]
    w("walk_spectral_sweep.mid", _seq(spectral, 1.6))

    # Walks C & D drive the ball to specific regions / around a loop USING
    # harmony — chord quality sets the x position (evenness → harmonic↔inharmonic
    # axis), modulation sets y (fifths displacement). Each "station" first sets
    # its key with two diatonic triads (keeping clarity high so the well is deep
    # enough to pull the particle), then dwells on a colour chord whose evenness
    # places the target. Because clarity (histogram margin) and evenness (current
    # chord) are decoupled, an augmented or cluster chord over an established key
    # moves the ball to the edge while the basin stays committed.
    def harmonic_walk(stations, cycles=1):
        chords = _seq(C_DIATONIC, 1.0)                       # establish C
        for _ in range(cycles):
            for key, q in stations:
                chords.append((chord(key % 12, MAJ), 0.8))   # set the key
                chords.append((chord((key + 7) % 12, MAJ), 0.8))
                chords.append((chord(key % 12, q), 1.4))     # dwell on the colour
                chords.append((chord(key % 12, q), 1.4))
        return chords

    # Walk C — region tour: brass(centre) → glass(right-high) → smoke(left-high)
    # → grit(left-low) → reed(right-low) → brass. Sharp modulation lifts y,
    # augmented pushes x right, clusters push x left.
    tour = [(0, MAJ), (2, AUG), (2, CLUSTER), (-2, CLUSTER), (-2, AUG), (0, MAJ)]
    w("walk_region_tour.mid", harmonic_walk(tour))

    # Walk D — harmonic loop: a six-station ring that changes one axis at a time
    # (key OR quality), so the ball rounds the manifold in a rough circle rather
    # than lurching across it. Runs three laps. Best heard/seen under the
    # "Anchored" character (home held → cleaner vertical swing).
    loop = [(2, AUG), (2, CLUSTER), (0, CLUSTER), (-2, CLUSTER), (-2, AUG), (0, AUG)]
    w("walk_harmonic_loop.mid", harmonic_walk(loop, cycles=3))

    # 7. Cadence pair: same chord multiset, with/without V-I adjacency into G.
    g_section_yes = [(7, MAJ), (4, MIN), (0, MAJ), (2, DOM7),
                     (7, MAJ), (4, MIN), (0, MAJ), (2, DOM7), (7, MAJ)]
    g_section_no = [(7, MAJ), (2, DOM7), (4, MIN), (0, MAJ),
                    (7, MAJ), (2, DOM7), (4, MIN), (0, MAJ), (7, MAJ)]
    w("cadence_yes.mid", _seq(C_SETTLE * 3 + g_section_yes, 1.0))
    w("cadence_no.mid", _seq(C_SETTLE * 3 + g_section_no, 1.0))

    return written


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in build_all(os.path.join(here, "fixtures")):
        print(path)
