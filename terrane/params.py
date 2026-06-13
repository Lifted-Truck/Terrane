"""Every feel-parameter, exposed — none buried as constants (Part II, Live controls)."""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields


@dataclass
class Params:
    # --- particle ---
    mass: float = 1.0
    friction: float = 3.0

    # --- terrain ---
    slew_tau: float = 0.6            # h slew time constant (s)
    clarity_ref: float = 0.18        # margin at which clarity saturates; calibrated to kk-1982.1 — re-tune if the profile version changes
    focus_rho: float = 0.25          # radius of dominant-basin selection around the terrain target
    depth_scale: float = 1.0         # global well depth
    shallow_frac: float = 0.30       # well depth when clarity = 0 (splintered terrain)
    evenness_x_min: float = 0.18     # inharmonic end of the spectral axis (x)
    evenness_x_max: float = 0.82     # harmonic end
    disp_gain: float = 0.05          # terrain translation per fifth of displacement (y)
    mode_asym: float = 0.15          # sigma asymmetry for cross-mode relationship (sketch level)
    wall_k: float = 60.0             # soft-wall stiffness outside [0,1]^2

    # --- home ---
    rootedness: float = 0.7          # 0 = home chases local key, 1 = home fixed
    home_k_max: float = 0.4          # pull rate (rad/s per rad) at rootedness 0, full confidence
    crystallization_margin: float = 0.05
    gate_margin: float = 0.02        # below this margin, home receives no pull
    cadence_impulse: float = 0.35    # fraction of home->key angular gap applied per cadence
    cadence_margin: float = 0.05     # min key confidence for a cadence to count
    mode_flip_time: float = 8.0      # sustained cross-mode residence before home's mode flips
    min_hist_weight: float = 0.5     # near-silence gate on induction calls (Tonality contract)
    key_poll_interval: float = 0.25  # re-poll cadence for key reading between chord events

    # --- histograms ---
    hist_fast_tau: float = 15.0      # local-key window
    # session accumulator has no decay; displayed, feeds nothing in Phase 1

    # --- gesture forces ---
    fast_tau: float = 2.0            # gesture feature window
    g_density: float = 0.35          # note density -> energy injection
    g_register: float = 0.30         # register centroid -> directional bias (x)
    g_vl: float = 0.015              # velocity kick per semitone of voice-leading work
    habituation_polarity: float = 0.0  # -1 erode .. +1 carve; Phase 1 stub, wired but minimal
    habituation_gain: float = 0.0

    # --- clocks ---
    physics_hz: float = 200.0

    def to_dict(self) -> dict:
        return asdict(self)

    def update(self, values: dict) -> None:
        valid = {f.name for f in fields(self)}
        for key, value in values.items():
            if key in valid:
                setattr(self, key, float(value))
