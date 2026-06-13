"""The ten Phase 1 acceptance criteria (terrane-design-doc.md, Part II).
Each test maps 1:1 to a numbered criterion; fixtures are the spec's list."""

import math
import os
import time

from terrane import Engine, Params
from terrane.fifths import FIFTH_STEP, fifths_angle, wrap_angle
from terrane.midi_io import load_midi_events, run_events
from terrane.terrain import Terrain

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


def run_fixture(name: str, on_step=None, tail: float = 3.0) -> Engine:
    events = load_midi_events(os.path.join(FIXTURES, name))
    engine = Engine(Params())
    run_events(engine, events, duration=events[-1].t + tail, on_step=on_step)
    return engine


# 1. Continuity: no teleports under any fixture, including abrupt tritone modulation.
def test_continuity_under_tritone_modulation():
    last = [None]
    max_jump = [0.0]

    def watch(e: Engine):
        if last[0] is not None:
            dx = e.particle.x - last[0][0]
            dy = e.particle.y - last[0][1]
            max_jump[0] = max(max_jump[0], math.hypot(dx, dy))
        last[0] = (e.particle.x, e.particle.y)

    run_fixture("tritone_modulation.mid", on_step=watch)
    assert max_jump[0] < 0.03, f"per-tick displacement {max_jump[0]:.4f} exceeds bound"


# 2. Terrain smoothness: bounded frame-to-frame potential change under slewed h.
def test_terrain_smoothness():
    grid = [(x / 3.0, y / 3.0) for x in range(4) for y in range(4)]
    prev = [None]
    max_delta = [0.0]

    def watch(e: Engine):
        cfg = e.terrain.config(e.slew.current)
        u = [Terrain.potential(cfg, gx, gy) for gx, gy in grid]
        if prev[0] is not None:
            max_delta[0] = max(max_delta[0], max(abs(a - b) for a, b in zip(u, prev[0])))
        prev[0] = u

    run_fixture("tritone_modulation.mid", on_step=watch)
    assert max_delta[0] < 0.05, f"per-tick potential change {max_delta[0]:.4f} exceeds bound"


# 3. Home convergence on a single diatonic key at default ROOTEDNESS.
def test_home_convergence():
    engine = run_fixture("diatonic_hold.mid")
    assert engine.home.crystallized
    assert engine.log.crystallized_at is not None and engine.log.crystallized_at < 15.0
    error = abs(wrap_angle(engine.home.theta - fifths_angle(0)))
    assert error < 0.25 * FIFTH_STEP, f"home {error:.3f} rad from C"


# 4. Chromatic immunity: gated home + visibly increased ruggedness.
def test_chromatic_immunity():
    theta_after_settle = [None]
    clarity_after_settle = [None]

    def watch(e: Engine):
        if 12.5 <= e.t < 12.51:
            theta_after_settle[0] = e.home.theta
            clarity_after_settle[0] = e.slew.current.clarity

    engine = run_fixture("chromatic.mid", on_step=watch)
    assert engine.home.crystallized
    drift = abs(wrap_angle(engine.home.theta - theta_after_settle[0])) / FIFTH_STEP
    assert drift < 0.3, f"home drifted {drift:.2f} fifths during chromatic material"
    assert clarity_after_settle[0] > 0.5, "settled key should read clearly"
    assert engine.slew.current.clarity < 0.35, "chromatic material should collapse clarity"
    cfg = engine.terrain.config(engine.slew.current)
    deepest = max(-w for w in cfg.weights)
    competing = sum(1 for w in cfg.weights if -w >= 0.5 * deepest)
    assert competing >= 4, f"terrain should splinter into competing wells, got {competing}"


# 5. Cadence response: V-I fires a discrete home impulse; reordered chords don't.
def test_cadence_response():
    yes = run_fixture("cadence_yes.mid")
    no = run_fixture("cadence_no.mid")
    yes_g = [c for c in yes.log.cadences if c.to_root_pc == 7]
    no_g = [c for c in no.log.cadences if c.to_root_pc == 7]
    assert yes_g, "V-I into G must be detected"
    assert max(abs(c.evidence["jump_applied"]) for c in yes_g) > 0.05
    assert not no_g, "non-cadential ordering must not fire"


# 6. Naturalization: deformation rises on modulation, relaxes as home migrates;
#    the original key, revisited, now registers as displaced.
def test_naturalization():
    trace: list[tuple[float, float]] = []

    def watch(e: Engine):
        trace.append((e.t, abs(e.slew.current.displacement)))

    engine = run_fixture("modulate_and_stay.mid", on_step=watch)
    peak = max(d for t, d in trace if 24.0 <= t <= 45.0)
    final = [d for t, d in trace if t >= trace[-1][0] - 5.0]
    assert peak > 2.5, f"modulation should deform terrain, peak {peak:.2f}"
    assert max(final) < 0.35 * peak, f"deformation should relax, final {max(final):.2f} vs peak {peak:.2f}"
    c_displacement = abs(wrap_angle(fifths_angle(0) - engine.home.theta)) / FIFTH_STEP
    assert c_displacement > 2.0, "original key should now register as remote"


# 7. Hysteresis: same destination, different routes, different particle positions.
def test_hysteresis():
    a = run_fixture("route_a.mid")
    b = run_fixture("route_b.mid")
    dist = math.hypot(a.particle.x - b.particle.x, a.particle.y - b.particle.y)
    assert dist > 0.05, f"routes should leave distinct positions, distance {dist:.4f}"


# 8. Determinism: identical fixture -> identical trajectory, bit for bit.
def test_determinism():
    def trajectory():
        positions: list[tuple[float, float]] = []
        run_fixture("diatonic_hold.mid", on_step=lambda e: positions.append((e.particle.x, e.particle.y)))
        return positions

    assert trajectory() == trajectory()


# 9. Performance: physics comfortably >= 100 Hz.
def test_performance():
    engine = Engine(Params())
    for note in (60, 64, 67):
        engine.note_on(note, 80)
    dt = 1.0 / engine.params.physics_hz
    start = time.perf_counter()
    for _ in range(2000):
        engine.step(dt)
    elapsed = time.perf_counter() - start
    rate = 2000 / elapsed
    assert rate > 1000, f"{rate:.0f} steps/s is below 10x the 100 Hz requirement"


# 10. Cold start: neutral terrain and no home until confidence crosses threshold.
def test_cold_start():
    engine = Engine(Params())
    engine.step(1.0 / engine.params.physics_hz)
    assert not engine.home.crystallized
    assert engine.slew.current.clarity < 0.01
    cfg = engine.terrain.config(engine.slew.current)
    depths = [-w for w in cfg.weights]
    assert max(depths) - min(depths) < 0.4 * max(depths), "cold terrain should be near-uniform"
    played = run_fixture("diatonic_hold.mid")
    assert played.home.crystallized and played.log.crystallized_at > 0.0
