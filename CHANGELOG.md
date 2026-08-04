# Changelog

Notable changes to HandBand. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The `v1.0` – `v3.1` tags below belong to the **2025 prototype**, now archived in
`legacy/`. Its history was reconstructed from dated file snapshots, so those
tags mark real development but were applied retroactively. The current system
starts at `v0.1.0` — a separate lineage, sharing ideas but no code.

---

## [0.1.0] — 2026-08-04

First tagged release of the current system. It composes a complete song from a
single emotional input and **renders it as notation rather than audio.** The
symbolic half is real and tested; the audio half is not written yet.

### Added

- **Input** (module 1) — tkinter slider, −1 … +1, at 0.001 resolution.
- **EMOTE** (module 2, first pass) — valence and arousal only. Valence is
  linear in the input; arousal is a power law on its absolute value, giving the
  U-shaped curve where both emotional extremes read as high activation.
- **Musical Intelligence** (module 3) — 12 modules under `handband/mi/`:
  - Global parameters: tempo from valence via a logarithmic curve, so
    perceptual change is even across the slider; key fixed at C.
  - Chord progression engine: song form, weighted Markov walk over the diatonic
    pool, forced cadences, 7ths and 9ths above arousal 0.85, duration
    archetypes.
  - Chord, bass, and drum instruments over a shared `Instrument` base — accent
    following, groove following, note density, register height, syncopation,
    voicing. All three emit the same per-slot shape, so one consumer reads all
    of them.
  - Bass: Fourier contour in scale degrees with an arousal-derived harmonic
    cutoff, then chord-relative realization against each chord's implied mode.
  - Drums: kick, snare and hat as full instruments, coupled to each other and
    to the bass.
  - Accent pattern and groove delay engines.
- **Main orchestrator** (module 9, partial) — wires Input → EMOTE → six views
  over one shared `SongSource`, so every window shows the same generated song.
- **Six tkinter views** under `handband/gui/` — EMOTE meters, progression grid,
  chord instrument, bass contour, bass pattern, and a combined Score.
- **297 tests** across 7 suites, asserting invariants rather than fixed values,
  which suits a system whose output is random by design.
- **CI** on every push and pull request, across Python 3.10–3.13.

### Not in this release

Modules 4 through 8 — Sonic Intelligence, Sequencer, Synthesizer, Mix/Master,
and Output. HandBand produces no sound yet. `docs/Domain_Parameters.md` is the
source material for module 4; a working C++ synthesis engine for module 6
exists in `legacy/` but is not wired to this architecture.

---

## Prototype lineage (archived)

These tags mark the 2025 prototype in `legacy/programmable-song/` — a realtime
generative song engine in Python driving a C++ synthesis library through
`ctypes`. It ran and it made music. It also grew into a single 199 KB file,
which is why the current architecture separates symbolic decisions from sound.
See `legacy/README.md` and `legacy/TECHNICAL_DOCUMENTATION.md`.

- **[v3.1]** — 2025-10-30 — final state of the prototype.
- **[v3.0]** — 2025-08-04
- **[v2.0]** — 2025-06-09
- **[v1.0]** — 2025-04-29 — first version that ran end to end.

[0.1.0]: https://github.com/baerbuster/HandBand/releases/tag/v0.1.0
[v3.1]: https://github.com/baerbuster/HandBand/releases/tag/v3.1
[v3.0]: https://github.com/baerbuster/HandBand/releases/tag/v3.0
[v2.0]: https://github.com/baerbuster/HandBand/releases/tag/v2.0
[v1.0]: https://github.com/baerbuster/HandBand/releases/tag/v1.0
