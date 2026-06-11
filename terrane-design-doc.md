# TERRANE — Design Document & Phase 1 Specification

*Working title. (Terrain + "terrane": a crustal fragment with its own geological history, accreted onto a larger mass. Rename at will.)*

**Status:** Architecture frozen. Phase 1 specced. Phases 2+ deliberately unroadmapped.
**Origin:** Distilled from a design conversation, June 2026. This document is the canonical record of the architecture and the rationale behind each resolved design fork. Future implementation sessions should treat Part I as load-bearing: do not "simplify" a decision without consulting the rationale appendix.

---

# Part I — Design Document

## 1. Concept

A synthesizer whose sound is a function not of the current note but of the *path taken to get there*. The instrument listens to what has been played — gesture, rhythm, density, repetition, and especially the geometry of chords and progressions — and moves its timbre through a vast space of possible sounds in response. As patterns emerge in the playing, the instrument transforms.

Core properties the design must deliver:

- **Hysteresis.** The same input played after different histories produces different sounds. The instrument remembers *how* you arrived, not just *where* you are.
- **Continuity.** The sound never jumps. All transformation is motion.
- **Legibility.** The player must be able to feel (and, in the prototype, see) the causality. Deterministic dynamics: the same performance history always produces the same trajectory.
- **Vastness.** The reachable timbre space is enormous, but navigation through it is structured, not random.
- **No generative AI in the compositional core.** The player composes; the instrument's response is deterministic dynamics. This is an adaptive instrument, not a co-writer.

## 2. Architecture Overview: Two Coupled Manifolds

The instrument couples two geometric spaces:

1. **Harmonic space** — Tymoczko's chord orbifold and the circle of fifths. Chords are points; progressions are paths; voice leading is the metric. This space comes with intrinsic structure (center/boundary, singularities, distances, winding) that the design exploits rather than invents.
2. **Timbre space** — a low-dimensional latent space whose coordinates drive synthesis parameters (cepstral spectral-envelope coefficients, wavetable morph coordinates, filter pole positions).

The coupling: **motion and state in harmonic space reshape the *terrain* of timbre space; gesture and rhythm push a *particle* through that terrain.** The particle's position is the sound.

### The governing split: state → terrain, motion → force

A clean rule resolves which harmonic quantities do what:

- **Harmonic *state*** (current key relative to home, tonal clarity, chord evenness) configures the **terrain** — the potential field the particle lives in.
- **Harmonic *motion*** (voice-leading work, harmonic acceleration) and all **gestural/rhythmic features** act as **forces** on the particle.

A modulation doesn't shove the sound; it rearranges the geography, and the sound *slides* into the new arrangement at a rate set by the particle's physics.

## 3. Four Nested Timescales

The entire instrument is one mechanism — a damped particle in a potential field — instantiated at four speeds:

| Layer | Timescale | Metaphor | What it is |
|---|---|---|---|
| **Particle** | milliseconds–seconds | Weather | Timbre position + velocity, driven by gesture forces and terrain gradients |
| **Terrain** | harmonic rhythm (seconds) | Seasons | Potential field configured by current harmonic state |
| **Home** | minutes | Climate | Tonal center the terrain is defined *relative to*; itself a slow particle in key space |
| **Plasticity** | sessions | Erosion | Accumulated history permanently deforms the terrain; repeated progressions wear grooves |

Each layer is the same physics with different mass and friction. Timescale separation is the load-bearing principle: it is what makes the system feel alive rather than chaotic.

## 4. The Listener (Feature Extraction)

All features are computed over **multiple simultaneous timescales** — a fast window (~2 s), a medium window (~30 s), and a whole-session accumulator. Short-term gesture and long-term behavior can pull in different directions; that tension is musical.

### 4.1 Gestural / rhythmic features (→ forces)
- **Note density** (events per second, per window)
- **Velocity statistics** (mean, variance, contour)
- **Register centroid** (weighted mean pitch)
- **Interval entropy** (distribution of melodic intervals)
- **Rhythmic regularity** — autocorrelation of onset times; peaked = regular, flat = free
- **Repetition index** — n-gram matching over recent pitch/rhythm sequences
- **Predictability** — entropy of a running pitch-class transition matrix; peaked matrix = predictable playing, flat = exploratory

### 4.2 Harmonic-state features (→ terrain)
Chord identification from held MIDI notes (trivial in v1; audio chord tracking is explicitly deferred, possibly forever).

- **Local key + confidence** — Krumhansl-Schmuckler correlation against a decaying pitch-class histogram (fast time constant). Confidence = correlation strength and/or margin over the second-best key.
- **Tonal clarity** — the confidence scalar itself; low for chromatic/ambiguous/polytonal material.
- **Chord evenness** — distance of the current chord from the nearest perfectly even chord (e.g., augmented triad for trichords). In the orbifold: distance from center (even) toward boundary (clusters).
- **Mode relationship** — major/minor of local key relative to home; parallel vs. relative relationships are geometrically distinct.
- **Displacement from home** — signed angular distance on the circle of fifths between local key and home (see §6).

### 4.3 Harmonic-motion features (→ forces)
- **Voice-leading work** — minimal voice-leading distance between successive chords (assignment problem: Hungarian algorithm over voice pairings, taxicab metric), summed over a rolling window. "Harmonic effort." Parsimonious neo-Riemannian moves (P/L/R, single semitones) inject almost no energy; lurching progressions inject a lot. Maps to kinetic-energy injection into the particle.
- **Harmonic rhythm** — rate of chord change = path velocity in chord space.
- **Harmonic acceleration** — its derivative; candidate driver for transient timbral behavior.

### 4.4 Pattern/loop features (→ plasticity)
- **Closed-loop detection** — chord-sequence n-grams that return to their starting point (I–vi–IV–V–I and kin). Each traversal deposits a small permanent deepening of the basins along the loop's path through timbre space.
- **Winding number** around the orbifold's singular points, accumulated as a slow secular variable ("harmonic angular momentum"). Speculative; deferred beyond Phase 1.

## 5. The Timbre Space

A low-dimensional latent space (start with 2D for the prototype; 3–6D plausible later) whose coordinates map to synthesis parameters:

- **Cepstral coefficients** → spectral envelope (smooth, perceptually meaningful; spectral-envelope smoothness is itself an "evenness" axis, mirroring the harmonic one)
- **Wavetable morph coordinates** → position in a morph field between wavetable anchors (optimal-transport and cepstral source-filter morphing apply directly)
- **Filter pole positions** → resonant character (pole-piloting approach)

**Construction: hand-built, not learned (v1 decision).** Place ~6–12 **timbral anchors** — hand-chosen landmarks — in the space, with interpolation between them. A learned space (small VAE over a frame corpus) remains a future option, but the hand-built version is more legible, more debuggable, and probably more musical. Anchor count and placement are explicitly feel-parameters (see Open Questions).

One axis of the space should be designated the **harmonic↔inharmonic spectral axis** (periodic/harmonic spectra at one end; inharmonic, beating, noisy spectra at the other), because the evenness mapping targets it directly (§7).

## 6. The Relational Home System

**Decision: terrain is relational, not absolute.** The terrain is defined by harmonic distance from an established *home*, not by chromatic key identity. C major does not have a fixed timbre; "being at home" does. The instrument is transposition-invariant, and the 24-key configuration problem collapses to a small relational vocabulary: at-home, dominant-side, subdominant-side, relative, parallel, remote.

### 6.1 Home as a particle
Home is a point on the circle of fifths (angle θ_home + mode flag) with inertia and friction — the same physics as the timbre particle, at a much slower timescale.

- **Update:** dθ_home/dt = k · confidence · wrap(θ_local − θ_home), where k is set by the ROOTEDNESS control.
- **Confidence gating:** when tonal clarity is low, home receives *no pull*. Chromatic and atonal passages flatten/splinter the terrain (§7) but leave home untouched, waiting. The instrument loses its sense of where it lives only if you genuinely settle somewhere else.
- **Cadential weighting:** detected V–I motion into a key gives home a discrete impulse toward it. Keys are established by cadence more than by exposure; the estimator should believe the same thing.

### 6.2 Emergent long-form behavior (this is the payoff — protect it)
- **Naturalization.** Modulate somewhere remote and stay: terrain is initially strongly deformed, the sound exotic. Home migrates toward you; the deformation relaxes over minutes; the new key naturalizes. The instrument acclimates the way a listener does.
- **You can't go home again.** Return to the original key after home has drifted, and the place you started now sounds foreign. The instrument enforces it.

### 6.3 ROOTEDNESS (top-level performance control)
Home's inertia. Maxed: home is fixed at session start; every departure stays exotic forever (a fixed pole star). Minimized: home chases the local key; everything naturalizes almost immediately; remoteness is barely possible. The expressive middle is where long-form structure lives.

### 6.4 Cold start
The session opens with no home and a neutral, flattish terrain. Home crystallizes out of the playing once estimator confidence crosses a threshold, and the terrain blooms into shape around it. Tuning the instrument = declaring a tonic to it by playing. A manual **drop-anchor** override (pin home explicitly) costs nothing and will be wanted.

## 7. The Terrain

### 7.1 Form
Potential field as a sum of Gaussians centered on the timbral anchors, with depths and positions as functions of harmonic state **h** = (displacement-from-home, clarity, evenness, mode relationship):

> U(x) = Σᵢ wᵢ(h) · exp( −‖x − cᵢ(h)‖² / 2σᵢ² )

Negative weights are wells; positive are hills. Gradients are analytic and cheap — the particle integration runs at control rate without strain. **h is slewed** (smoothed) so terrain morphs continuously even when chord events are discrete.

### 7.2 The continuity guarantee (why terrain-shaping is the right call)
When harmony changes, the terrain reconfigures — but only the *forces* change instantaneously, never the particle's position. The floor tilts and the sound slides. A pivot-chord modulation produces a shallow new gradient and a lazy drift; an abrupt tritone modulation tears the basin out from under the particle and it accelerates hard toward the new one. **Harmonic surprise is automatically rendered as timbral urgency, with continuity guaranteed by the physics.** No crossfades are designed; they emerge.

Hysteresis survives intact: arriving in E♭ from B♭ vs. from E natural leaves the particle in different places on the same new terrain — possibly settling in different basins entirely. Same chord, different history, different sound.

### 7.3 Harmonic-state → terrain mappings (load-bearing)
- **Clarity → ruggedness.** High key clarity → one deep dominant basin; sound focused and stable. Ambiguous/chromatic harmony → terrain flattens or splinters into shallow competing wells; the particle wanders restlessly. Harmonic ambiguity becomes timbral instability with no explicit rule saying so.
- **Evenness → basin position** along the harmonic↔inharmonic spectral axis. Even chords pull the active basin toward harmonic/periodic spectra; clustered chords toward inharmonic/noisy ones. The geometry of the harmony directly modulates the geometry of the spectrum.
- **Fifths displacement → translation.** Displacement from home translates the whole configuration through morph space; sharpward and flatward are opposed timbral directions. Long modulatory journeys accumulate real displacement; returning home after a journey means the same room at a different time of day.
- **Mode relationship → basin asymmetry** (parallel vs. relative relationships deform differently). Sketch-level; tune in Phase 2.

### 7.4 Plasticity (slowest layer)
Every traversal of a detected closed harmonic loop deposits a small permanent deepening along the basins it visited. **Session persistence is a first-class design axis:** per-session reset is an effect; lifetime persistence (serialized terrain state, loaded at startup) is an instrument that develops a personality — one that has slowly migrated to a region of the space shaped by its player's habits. Both modes should exist.

## 8. The Particle (Dynamics)

**Decision: features map to forces, not positions.** Position-mapping makes a fancy macro knob (same input → same sound, no history). Force-mapping gives path dependence for free.

State: position **x**, velocity **v**, mass m, friction γ.

> m·ẍ = −∇U(x) + Σⱼ Fⱼ(features) − γ·v

Integrate with semi-implicit Euler at control rate (≥100 Hz). Gesture/rhythm features and harmonic-motion features (voice-leading work, harmonic acceleration) supply the Fⱼ terms. Deterministic: same MIDI in → same trajectory out (any stochastic element must be seeded).

### 8.1 Habituation polarity (open design axis — expose, don't decide)
Repetition can carve a basin (the sound *stabilizes* when you repeat — convergent, mirror-like) or repeated patterns can lose force / actively repel (the sound *erodes or flees* under repetition — divergent, adversarial; sustaining a sound requires continued novelty). These are opposite musical philosophies and both are compelling. **HABITUATION POLARITY is a top-level control**, possibly the single most expressive macro in the instrument. (Resolved fork from early design: the instrument need not be globally "responsive" or "adversarial" — the polarity is performable.)

### 8.2 Connection to the variational synthesis engine (future direction)
The performance history can *generate the constraint sets* for the variational engine: spectral statistics of the last N minutes become constraints the engine either converges toward (the instrument starts to sound like what you've been playing — a feedback identity) or is forced away from (the instrument refuses to repeat itself — an anti-habituation engine with genuinely strange long-form behavior). Deferred; revisit after Phase 2.

## 9. Speculative / Deferred Ideas (recorded so nothing is lost)
- **Singularities.** The orbifold's singular points (unisons, doubled voicings) are where the space folds. Passing near them could trigger discontinuous events: phase reset, sudden constraint flip. Geometric punctuation. Phase 3+.
- **Winding number** around singular points as accumulated "harmonic angular momentum" — a slow secular variable the player builds without realizing it.
- **Tonnetz displacement vector** as a 2D steering input (major-third vs. minor-third axes of travel), supplementing the 1D fifths displacement.
- **Terrain anisotropy / ridges** — regions that are sticky, ridges that are hard to cross, so certain timbral transitions require sustained harmonic "effort."
- **Audio-input chord tracking** for non-MIDI sources.
- **Learned latent space** (VAE over a wavetable/spectral-frame corpus) replacing or augmenting hand-built anchors.

## 10. Platform Strategy
- **Phase 1 (visualization prototype):** with Tonality (Python) as the harmonic brain (§11), the recommended shape is a **local Python backend (Tonality client + histogram + home + terrain + particle) feeding a browser frontend over websocket** (canvas render, Web MIDI in browser or `mido`/`rtmidi` in backend). This preserves Claude Code self-verifiability — fixtures run headlessly against the backend with acceptance criteria as tests — while consuming Tonality natively instead of reimplementing estimators in JS. *Recommendation, not commitment — override if the Max-native path is preferred.*
- **Phase 2 sandbox:** Max/MSP — dynamics in JS/gen~, driving a wavetable/cepstral engine; harmonic analysis remains a Tonality call at chord-event rate (OSC or MCP bridge).
- **Destination:** JUCE plugin, once the dynamics model is proven by play.

## 11. Tonality Integration

TERRANE's entire harmonic-analysis layer is a **Tonality client** (github.com/Lifted-Truck/Tonality — live truth in that repo's ROADMAP.md). Division of labor per Tonality's thesis: exact pitch-class combinatorics in the engine; dynamics, terrain, and feel in TERRANE. Do not reimplement what Tonality ships.

**Direct mappings (shipped Tonality capability → TERRANE component):**
- **Ranked key induction with margins** → local key + confidence. Replaces the hand-rolled Krumhansl-Schmuckler estimator originally specced in Phase 1. The margin *is* the confidence scalar; the honest `is_ambiguous` flag feeds the clarity→ruggedness mapping directly.
- **Exact voice-leading distance** → harmonic effort (kinetic-energy injection). Already exact; delete the Hungarian-algorithm implementation note.
- **Set-class identity + DFT harmonic-color embedding** → evenness, and potentially much more: DFT coefficient magnitudes measure evenness/balance intrinsically, and the embedding is a richer harmonic-state input than a single evenness scalar — candidate additional terrain coordinates.
- **Exhaustive chord naming / multi-notation parsing** → chord identification, including honest handling of ambiguous sets (C6 = Am7) rather than forced guesses.
- **MIDI read/write + key-aware dataset pipeline** → test-fixture generation and offline trajectory analysis.

**Philosophical alignment:** "reduce, never invent" is the same commitment as confidence-gated home drift — both systems refuse to fabricate tonal context they don't have evidence for. Ambiguity is surfaced (plural, ranked, evidenced answers) and TERRANE renders it as terrain instability rather than hiding it.

**Latency analysis:** Tonality's APIs are batch, not incremental — but TERRANE's harmonic events occur at *harmonic rhythm* (seconds), not control rate. Only the particle physics is control-rate, and it is purely local. TERRANE maintains its own decaying pitch-class histogram and calls Tonality per chord event with a snapshot; microsecond table-driven identity answers make per-event batch calls comfortably real-time-adequate for Phase 1. Incremental/streaming APIs would make this cleaner, not possible.

> **Status (2026-06-11):** the relay below happened and Tonality answered — see `integrations/terrane/{brief,response,brief-2}.md` in the Tonality repo. Verdicts: items 1 and 3 (evenness) shipped/documented; VL pairing shipped at identity level (realization level = Tonality gap 6); cadence events = gap 7; streaming = gap 5; TERRANE recorded as target application A5. Build against INTEGRATION.md's documented recipes; pin key-profile version `kk-1982.1`.

**Candidate Tonality roadmap entries to relay to the repo agent (TERRANE as motivating consumer, alongside target app A4):**
1. *Incremental/streaming session API* — stateful decaying pitch-class histogram with event-driven key induction; the shared prerequisite for all real-time consumers.
2. *Cadence detection as an evidenced event* — V–I (and related) root-motion detection with per-signal evidence, fitting the plural/ranked/evidenced model; consumed by TERRANE's home-impulse mechanism.
3. *Evenness / distance-from-nearest-even-chord as a first-class query*, if not already trivially derivable from the DFT embedding (if derivable, document the mapping in INTEGRATION.md instead).
4. *TERRANE row in INTEGRATION.md* — synth/visualizer consuming key induction, VL distance, set-class/DFT, chord naming at harmonic-event rate.

Longer-term resonance worth recording: Tonality's Phase 4.6 vision of **declarative, versioned RULESETS** and TERRANE's **serialized terrain plasticity** are sibling ideas — both persist extracted musical habit as a versionable artifact. A future bridge (terrain state referencing or co-versioned with a ruleset) is plausible and should be kept in view when either is designed.

---

# Part II — Phase 1 Specification: Visualization Prototype

## Goal
**No audio.** MIDI in → harmonic state → home → terrain → particle → render. The single question Phase 1 answers: *does the geography breathe musically when played at?* Everything downstream depends on the answer, which is why Phases 2+ are not roadmapped here.

## Pipeline
1. **MIDI input** — live (Web MIDI / Max midiin) *and* file/fixture playback for testing.
2. **Pitch-class histogram** — exponentially decaying, two time constants, maintained by TERRANE (fast ~10–30 s for local key; the session accumulator feeds nothing in Phase 1 but should be computed and displayed).
3. **Local key estimator** — **Tonality** ranked key induction per chord event over a histogram snapshot → (key, mode, confidence = margin, is_ambiguous). Do not reimplement; see §11. (Fallback only if integration blocks the build: minimal Krumhansl-Schmuckler, clearly marked as throwaway.)
4. **Home integrator** — θ_home on the circle of fifths + mode flag; pull = k·confidence·wrap(θ_local − θ_home); cadence detector (V–I root motion with confidence above threshold — TERRANE-local until Tonality ships cadence events, see §11 relay item 2) applies a discrete impulse; ROOTEDNESS sets k.
5. **Harmonic state vector h** — (signed fifths displacement from home, clarity, chord evenness, mode relationship), slewed.
6. **Terrain** — Gaussian-sum potential over a 2D latent slice; weights/centers as functions of h per §7.3 (clarity→ruggedness and evenness→position are required; fifths→translation required; mode→asymmetry optional).
7. **Particle** — semi-implicit Euler, ≥100 Hz; gesture forces in Phase 1 can be simple (note density → energy injection, register centroid → directional bias, voice-leading work → kinetic kicks) — the point is to verify the *feel* of terrain + physics, not the final force vocabulary.
8. **Render** — terrain as contour lines (live-morphing), particle as a dot with a fading trail, anchors labeled, plus a **fifths compass**: a circle-of-fifths dial showing local key, home, confidence, and the pull between them. Cold-start state visibly distinct (flat terrain, dimmed compass) until home crystallizes.

## Live controls (every feel-parameter exposed — none buried as constants)
- Particle mass, friction
- Per-anchor basin depth and width (σ)
- Anchor positions (draggable, ideally)
- Terrain morph slew rate
- ROOTEDNESS (home inertia k)
- Cadence impulse strength
- Confidence-gating curve / crystallization threshold
- Gesture-force gains (density, register, VL-work)
- HABITUATION POLARITY (stub acceptable in Phase 1 — wired but minimal)
- Drop-anchor button (pin home manually); session reset

## Acceptance criteria (self-verifiable by Claude Code where possible)
1. **Continuity:** particle position is continuous across any terrain reconfiguration — per-frame displacement bounded; no teleports under any fixture, including abrupt tritone modulation.
2. **Terrain smoothness:** under slewed h, frame-to-frame potential-field change is bounded; no visual popping.
3. **Home convergence:** on a fixture holding one diatonic key, home converges within a target time at default ROOTEDNESS.
4. **Chromatic immunity:** on an atonal/chromatic fixture, home's drift stays below a small bound (confidence gating verified) while terrain ruggedness visibly increases.
5. **Cadence response:** a V–I fixture produces a measurable discrete home impulse; the same chords in non-cadential order do not.
6. **Naturalization:** a modulate-and-stay fixture shows terrain deformation rising then relaxing as home migrates; the original key, revisited, now registers as displaced.
7. **Hysteresis:** two fixtures arriving at the same key via different routes leave the particle in measurably different positions.
8. **Determinism:** identical fixture → identical trajectory, bit-for-bit (seeded).
9. **Performance:** physics ≥100 Hz, render ≥60 fps on commodity hardware.
10. **Cold start:** neutral terrain until confidence threshold; crystallization is visualized as an event.

## Test fixtures (synthetic MIDI, included in repo)
- Diatonic progression held in one key (convergence)
- Pivot-chord modulation to the dominant; abrupt tritone modulation (continuity, urgency contrast)
- Modulate-and-stay, ≥3 minutes (naturalization)
- Chromatic/atonal sequence (gating, ruggedness)
- Repeated 4-chord loop, many traversals (repetition/plasticity stub)
- Two-route-same-destination pair (hysteresis)

## Build shape
One or two autonomous Claude Code runs against the acceptance criteria, then a **manual audition checkpoint**: play at it live, watch whether the geography breathes. Expect the audition to revise force gains, terrain mappings, and possibly the timescale constants — that revision *is* the deliverable of Phase 1.

## Phases 2+ (one sentence each — do not spec until Phase 1 auditions)
- **Phase 2:** Audio engine — map particle position to cepstral envelope / wavetable morph / filter poles in Max; finalize anchor sounds.
- **Phase 3:** Plasticity and session persistence — loop detection, terrain serialization, lifetime-memory mode.
- **Phase 4:** Habituation polarity, variational-engine constraint coupling, singularity events, Tonnetz steering.
- **Phase 5:** JUCE port.

---

# Appendix — Resolved Design Forks and Rationale

| Fork | Decision | Rationale |
|---|---|---|
| Features → positions vs. **forces** | Forces | Position-mapping is a macro knob with no history; forces give hysteresis and path dependence for free. |
| Harmony as force channel vs. **terrain-shaping** | Terrain-shaping | Rhythm and gesture mean different things in different harmonic regions; a modulation rearranges the geography rather than nudging the sound — the harmony transforms the *instrument*. Continuity is guaranteed because terrain changes alter forces, never position. |
| Absolute vs. **relational** terrain | Relational | Mirrors how tonality is actually perceived; transposition-invariant; collapses 24 key configurations to a small relational vocabulary; enables naturalization and you-can't-go-home-again as emergent behavior. Cost: requires home estimation — paid via the home-as-particle mechanism. |
| Learned vs. **hand-built** latent space | Hand-built anchors (v1) | Legible, debuggable, likely more musical initially; learned space remains open. |
| Responsive vs. adversarial instrument | **Neither — performable polarity** | Both philosophies are compelling; HABITUATION POLARITY becomes a top-level expressive control rather than an identity decision. |
| Duration-based vs. **cadence-weighted** home estimation | Cadence-weighted (plus confidence-gated duration) | Keys are established by cadence more than exposure; perceptual honesty. |
| Comprehensive roadmap vs. **frozen design + Phase 1 only** | Phase 1 only | The oracle for everything past Phase 1 is subjective (does it feel alive when played); a premature roadmap encodes confidence not yet earned. |
