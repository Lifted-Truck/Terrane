# TERRANE — Phase 1 (visualization prototype)

An adaptive instrument whose sound is a function of the *path* taken to reach
a note, not just the note. Harmonic state reshapes a timbre-space *terrain*
(a Gaussian-sum potential field); gesture and harmonic motion push a damped
*particle* through it. The particle's position is the sound. Phase 1 has **no
audio** — it answers one question: *does the geography breathe musically when
played at?*

Canonical spec: [`terrane-design-doc.md`](terrane-design-doc.md). The
harmonic-analysis layer is a client of the [Tonality](https://github.com/Lifted-Truck/Tonality)
engine — nothing harmonic-combinatorial is reimplemented here (see
[`CLAUDE.md`](CLAUDE.md) and design-doc §11).

## Layout

```
terrane/
  histogram.py        decaying pitch-class histograms (two time constants)
  tonality_client.py  the single Tonality boundary (key induction, evenness, VL)
  chords.py           held-MIDI -> chord events (the clean note on/off boundary)
  home.py             relational home: confidence-gated drift + cadence impulse + ROOTEDNESS
  state.py            slewed harmonic state vector h
  terrain.py          Gaussian-sum potential; the §7.3 h -> terrain mappings
  particle.py         damped particle, semi-implicit Euler
  features.py         gesture features -> forces
  engine.py           the pipeline, on a caller-owned clock (deterministic)
  midi_io.py          MIDI file -> events; deterministic fixture runner
  fixtures.py         synthetic MIDI test fixtures
  server.py           physics loop + websocket + static frontend
frontend/index.html   canvas render, fifths compass, live controls, Web MIDI
tests/                the 10 Phase 1 acceptance criteria
```

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e /path/to/Tonality   # the harmonic engine
.venv/bin/pip install -e .                     # TERRANE + deps (mido, websockets)
.venv/bin/python -m terrane.fixtures           # generate fixtures/*.mid
```

`kk-1982.1` is the pinned Tonality key-profile version; margin → control-curve
calibration assumes it (design-doc §11).

## Run

```sh
.venv/bin/python -m terrane.server   # then open http://localhost:8800
```

Play with a MIDI controller, the computer keyboard (`a w s e d f t g y h u j k`
= C4–C5), or click a fixture button. Drag anchors; every feel-parameter is a
live slider. **Drop anchor** pins home at the current local key; **Session
reset** returns to cold start.

## Test

```sh
.venv/bin/pytest        # 10 acceptance criteria from design-doc Part II
```

Continuity, terrain smoothness, home convergence, chromatic immunity, cadence
response, naturalization, hysteresis, determinism, performance (≥100 Hz),
cold start.

## Status

Phase 1 backend + frontend implemented; all acceptance criteria pass. Next is
the **manual audition** — playing at it to revise force gains, terrain
mappings, and timescale constants. That revision is the deliverable of Phase 1;
Phases 2+ (audio) are deliberately unspecced until the audition.
