# HandBand

**Modular Generative Emotional Feedback through song.**

HandBand reads a single number describing how you feel, and composes music from
it — in real time, from scratch, every time. Not a playlist, not a preset. One
value enters the system, and a band comes out the other side.

The bet is that music is a control surface for emotional state, and that the
mapping from state to music can be written down, then eventually learned.

---

## Status at a glance

HandBand is nine modules. Four exist. The table is the honest version — the
prose further down describes the whole design, including the parts that are
still specification.

| # | Module | Status | Where |
|---|---|---|---|
| 1 | **Input** | **Built** — GUI slider, −1 … +1 | `input.py` |
| 2 | **EMOTE** | **Built (first-pass)** — valence + arousal only | `emote.py` |
| 3 | **Musical Intelligence** | **Built** — global params + chord, bass, drum instruments | `mi/` (12 modules) |
| 4 | **Sonic Intelligence** | Not started | — |
| 5 | **Sequencer** | Not started | — |
| 6 | **Synthesizer** | Not started (prototype exists in `legacy/`) | — |
| 7 | **Mix/Master** | Not started | — |
| 8 | **Output** | Not started | — |
| 9 | **Main Orchestrator** | **Partial** — wires Input → EMOTE → views | `main.py` |

So the system currently composes a complete song — harmony, bassline, drum kit,
accent map, groove feel — and **renders it as notation rather than audio.** The
symbolic half is real and tested. The audio half is not written yet.

---

## Quick start

Requires **Python 3** and nothing else. The current system has **zero
third-party dependencies to run** — only `math`, `random`, `collections`, and
`tkinter` from the standard library. (The heavy audio stack — numpy, scipy,
pyaudio, librosa — belongs to the 2025 prototype in `legacy/`, not to this.
`pytest` is optional and only for the tests, which also run without it.)

```bash
python3 -m handband
```

That opens the main window: one slider, six checkboxes. The slider is the system
input. Each checkbox opens a view onto the same generated song.

Run it from the repo root — `handband` is a package, so everything is reached
with `python3 -m`. `tkinter` ships with python.org builds; some Linux
distributions package it separately as `python3-tk`. Developed and run on macOS.

Eight modules run standalone and print a demonstration of themselves, mostly as
ASCII grids sampled at several points across the emotional range:

```bash
python3 -m handband.mi.groove_delay_engine     # groove vectors across the emotional range
python3 -m handband.mi.bass_instrument         # contour plots, rhythm cells, degree cells
python3 -m handband.mi.chord_library           # chord symbols to intervals
python3 -m handband.mi.chord_instrument        # performance charts at three emotional states
python3 -m handband.mi.accent_pattern_engine   # accent grids per emotional state
python3 -m handband.mi.drum_instrument         # the kit against the bass it couples to
python3 -m handband.mi.instrument              # two contrasting instruments on the same data
python3 -m handband.mi.bass_modes              # chord to church mode, degree to semitone
```

`emote.py`, `mi/chord_progression_engine.py`, `mi/global_parameters.py`,
`mi/pattern_primitives.py`, and `mi/song_source.py` have no standalone demo.

### The views

| View | Shows |
|---|---|
| **EMOTE** | Live input, valence, and arousal as meters |
| **Musical Intelligence** | The chord progression grid, accent strip, groove strip |
| **Chord Instrument** | What the chord player actually does — hit / sustain / rest |
| **Bass Contour** | The Fourier curve the bassline rides, in scale degrees |
| **Bass Pattern** | The finished bass cell — the riff that repeats |
| **Score (Full Band)** | Chords, bass, and drum tab stacked like sheet music |

All six read one shared `SongSource`, so they always show the *same* song.
Generation is stochastic; without that sharing, two windows on the same input
would show unrelated music.

---

## Architecture

![HandBand module flow](HandBand%20Modular%20Flow.png)

Data flows one way. Each module knows only its own job:

```
Input          a single float, -1 .. +1
  |
EMOTE          -> valence, arousal        (the emotional coordinates)
  |
  +--> Musical Intelligence    -> WHAT to play  (notes, rhythm, form)   [BUILT]
  |
  +--> Sonic Intelligence      -> HOW it sounds (timbre, envelopes)     [planned]
              |
Sequencer      -> WHEN each note fires, sample-accurate            [planned]
              |
Synthesizer    -> per-role audio rendering                         [planned]
              |
Mix/Master     -> balance, space, glue                             [planned]
              |
Output         -> the listener                                     [planned]
```

The separation is the whole point. **Musical Intelligence decides what to play
and knows nothing about sound. Sonic Intelligence decides how it sounds and
knows nothing about notes.** Collapsing those two is what made the 2025
prototype unmaintainable; keeping them apart is what this architecture is for.

---

## Repo layout

```
handband/                the current system, a Python package
  __main__.py              so `python3 -m handband` runs the app
  main.py                  entry point — wires everything, owns the windows
  input.py                 module 1: the slider
  emote.py                 module 2: input -> valence, arousal
  mi/                      module 3: Musical Intelligence — WHAT to play
    global_parameters.py     tempo + key
    pattern_primitives.py    the shared toolbox every engine composes from
    chord_*.py               harmony: progression engine, chord library, instrument
    bass_*.py                bass: instrument, modal mapping
    drum_instrument.py       the kit: kick, snare, hat
    accent_pattern_engine.py where the emphasis lands
    groove_delay_engine.py   the timing feel
    instrument.py            the base class every instrument extends
    song_source.py           one shared song, so all views agree
  gui/                     six tkinter views
  tests/                   seven test suites, 297 tests

docs/                    design documents and screenshots
legacy/                  the 2025 prototype, archived — see legacy/README.md
```

---

## The generation pipeline

What actually happens when you move the slider. Every stage is at **16th-note
resolution** — the whole system speaks in slots, 16 per measure.

**1. Song form** (`create_song_form` in `mi/chord_progression_engine.py`)
Valence picks a length: 1, 2, 4, or 8 measures, exponentially weighted — sad is
short, happy is long. Arousal sets chord density. Then a repetition pattern
(`AABA`, `ABCAB`, …) emerges, built by weighing repetition against return
against novelty. **Form is generated here, in the harmonic engine, because form
emerges from harmony.** Every other engine inherits this same form rather than
inventing its own, so the arrangement shares one structure.

**2. Chord progression** (`create_chord_progression`)
Each section's chords are drawn from the diatonic pool by a weighted Markov walk
combining three forces: *valence affinity* (I is bright at +1.0, vii° is dark at
−1.0), *harmonic transition gravity* (V pulls to I with weight 4), and
*novelty pressure*. A cadence is then forced onto the ending — authentic,
plagal, half, or deceptive, chosen by valence and arousal. Above arousal 0.85,
chords take diatonic 7ths and 9ths. Finally a duration archetype (front, back,
center, alternating, symmetrical, random) spreads them across the slots.

**3. Accent map** (`mi/accent_pattern_engine.py`)
Which slots are emphasized. Depends only on the inherited form and arousal —
never on the chords themselves. Purely rhythmic.

**4. Groove vector** (`mi/groove_delay_engine.py`)
One measure of timing feel: 16 signed offsets, each a fraction of a slot.
**Arousal is the entire intensity engine** — it sets both how many slots move
and how far. **Valence contributes only direction:** positive lays back behind
the beat, negative rushes on top of it. A groove doesn't evolve section to
section — if it did, it wouldn't groove — so it's one measure, tiled.

**5. The instruments** (`mi/instrument.py` and its three implementations)
Each instrument is an *instance* with its own personality, reading the same
band-wide data and deciding how it personally responds. Five shared behaviors,
each pairing a shared emotional signal with a per-instrument parameter:

| Behavior | Shared signal | Personal parameter |
|---|---|---|
| Accent following | the accent map | `accent_follow` → dB boost |
| Groove following | the groove vector | `groove_follow` → offset multiplier |
| Note density | arousal | `max_density_rate` → hits per measure |
| Register height | arousal | `max_octave_range` → how wide it spreads |
| Syncopation | valence | `syncopation_follow` → pull toward offbeats |
| Voicing | arousal | how far off the voice-led baseline to rotate |

A deliberate design choice runs through all of it: **a weight can be lowered but
never zeroed.** Every option stays reachable at every emotional extreme. Nothing
is ever forbidden — only made unlikely.

**6. Realization**
Each instrument emits the *same per-slot shape*, so a consumer reads all three
identically:

```python
{"type": "H", "notes": [...], "accent": <dB>, "timing": <offset>}   # struck
{"type": "C"}                                                       # still ringing
{"type": "R"}                                                       # silence
```

### How each instrument thinks

**Chords** (`mi/chord_instrument.py`) — two passes. Pass 1 places hits: syncopation
weighting times an archetype shape, drawn without replacement. Pass 2 turns
every gap into sustain-then-rest, so the whole pass reduces to choosing one
sustain length per hit. That length is the staccato↔legato axis, driven by
arousal. A sustain never crosses a chord change — you don't hold an old chord
over new harmony. Pitches run voice-leading (nearest inversion to the previous
chord), then rotation by the voicing index, then an octave clamp into the
arousal-widened register.

**Bass** (`mi/bass_instrument.py`) — four tiers.
*Tier 1* is scalar decisions: octave drop, rhythm coupling, chord-tone
probability, phrase endpoint.
*Tier 2* generates a **Fourier contour** — the curve the line rides, measured in
**scale degrees rather than semitones**, so every value it passes through is
already diatonic and there are no chromatic notes to filter out. Valence tilts
it (up to a full octave of climb or fall across the cell); arousal makes it
wiggle, as a sum of equal-weight harmonics with a cutoff at `n_max = 1 + (N/2 −
1) × arousal` — one slow bump when calm, motion up to the Nyquist harmonic when
frantic. Equal weight is required: a rolloff would suppress the fast harmonics
and the cutoff would stop meaning anything.
*Tier 3* folds rhythm and contour into one cell of symbolic degrees.
*Tier 4* points those key-relative degrees at the *sounding chord*, reading each
against that chord's root and implied church mode — so the same symbolic degree
becomes a different note depending on the harmony above it (degree 3 is natural
over I, flat over ii). A note held across a chord change is **re-struck** on the
new chord rather than smeared: every pitch change is a real attack.

**Drums** (`mi/drum_instrument.py`) — kick, snare, hat, each a full `Instrument` in
its own right inside a thin container. The cell length is inherited from the
bass so the two repeat in lockstep. Elements **couple** to each other: the kick
attracts toward the bass's slots (+0.8), the snare avoids the kick's (−0.8).
Coupling multiplies a slot's weight — it never forbids one. A variant engine
(ride / hi-hat / crash switching on an emotional axis) is built and currently
off. Percussion is one-shot, so its alphabet is only `H` and `R`.

---

## Tests

297 tests across seven suites. All passing. They run two ways.

Under pytest, if you have it — the only third-party package this repo uses, and
only for this. `pytest.ini` scopes collection to `handband/tests`, so a bare
invocation from the repo root is enough:

```bash
pytest
```

Or standalone, with no dependencies at all, which prints each suite's own
section banners and pass/fail summary:

```bash
for f in handband/tests/test_*.py; do
  python3 -m "handband.tests.$(basename "$f" .py)"
done
```

| Suite | Tests |
|---|---|
| `tests/test_chord_progression_engine.py` | 94 |
| `tests/test_pattern_primitives.py` | 58 |
| `tests/test_groove_delay_engine.py` | 44 |
| `tests/test_accent_pattern_engine.py` | 40 |
| `tests/test_drum_instrument.py` | 32 |
| `tests/test_instrument.py` | 29 |
| `tests/test_global_parameters.py` | smoke test (prints a table) |

The suites are hand-rolled. Each file defines its checks as plain `test_*`
functions and drives them itself, from a `main()` behind a `__main__` guard —
so importing a suite runs nothing, which is what lets pytest collect the same
297 functions without the file executing itself first. They assert **invariants** rather
than fixed expected values, which suits a system whose output is random by
design: that a result rises monotonically with arousal, that no option is ever
unreachable at any emotional extreme, that a count never exceeds its capacity,
that the corners of the emotional range don't crash.

---

## The modules

Everything below is the original architecture document, preserved. Where the
implementation has settled a detail the design left open — or diverged from it —
that is noted in an indented block. **Design intent is kept even where the code
hasn't reached it yet;** the "evolution path" for each module is the roadmap,
not a description of the present.

### 1. Input — **BUILT**

The Input module is HandBand's sensory interface — the single point where
external reality enters the system. Its only job is to read sensor data and
normalize it to a standardized range of −1.0 to +1.0, where −1 represents one
emotional extreme (calm/low arousal), 0 is neutral baseline, and +1 is the
opposite extreme (intense/high arousal). Currently this is a GUI slider, but the
architecture is designed so we can swap in biosensors later without touching any
other module.

Input does not interpret what the value means, make musical decisions, or store
history. It's purely mechanical — just accurate sensor reading and
normalization. The rest of the system treats it as a black box that provides a
single float value. If the sensor fails, it should signal error clearly rather
than produce garbage data.

**Evolution path.** From GUI slider to single biosensor (HRV or skin
conductance) to multi-sensor fusion, and eventually integration with a novel
Causal Inference-based Neurosymbolic Intelligence for context-aware calibration.
But through all phases, the interface stays simple: get the current state value,
check if sensor is connected, and report what type of sensor is active. No
downstream module needs to know or care what's actually providing that number.

> **As built:** a `tkinter` slider at 0.001 resolution, exposing
> `get_input_value()`. The window is also the application's main window — the
> orchestrator attaches its controls to it. The error-signalling contract and
> the connected/sensor-type queries are specified but not yet implemented.

### 2. EMOTE — **BUILT (first-pass)**

**EMOTE — the Emotional Mathematical Optimization Translation Engine** — is
HandBand's core intelligence layer that transforms the single emotional state
value from Input into multiple abstract dimensions. Its job is nonlinear
multi-dimensional mapping — taking that one −1 to +1 number and running it
through different mathematical transformation curves to generate independent
parameters. Each dimension has its own scaling relationship to the input,
meaning an emotional state doesn't translate to proportional changes across all
dimensions — some might scale exponentially, others logarithmically, others
linearly. EMOTE contains all the pure mathematical functions and music theory
primitives needed for these transformations, but it never makes domain-specific
decisions about notes or sounds. It outputs abstract numerical values that
Musical Intelligence and Sonic Intelligence can interpret however they need to.

#### Scientific foundation

EMOTE's foundation rests on **Russell's Circumplex Model of Affect**, the most
empirically validated framework in emotion research, which demonstrates that
emotional experience can be reliably captured through two independent orthogonal
dimensions: **valence** (pleasure–displeasure) and **arousal**
(activation–deactivation). Validated across thousands of empirical studies since
1980, the model shows that all emotional states occupy positions within a
two-dimensional space. These dimensions are mathematically independent — you can
experience any combination, from high-arousal positive states (excitement,
elation) to low-arousal negative states (depression, fatigue).

The transformation functions are informed by psychophysical principles,
particularly **Stevens' Power Law**, which demonstrates that human perception
often scales as a power function of stimulus intensity. While Stevens' research
focused on sensory perception, the underlying principle — that perceptual
experience follows nonlinear transformations of input — applies to emotional
state mapping as well.

#### The two current dimensions

**Valence** maps linearly to the input — the most fundamental, directly
proportional relationship between input and emotional quality. As input moves
from −1 (negative/dysregulated) through 0 (neutral) to +1 (positive/regulated),
valence changes at a constant rate.

**Arousal** follows a power law transformation, mapping the absolute value of
input raised to a configurable exponent. This creates the characteristic
**U-shaped curve** where emotional extremes — *both* negative and positive —
produce high physiological activation, while the neutral center represents calm,
low-arousal states.

```python
valence = input_value
arousal = abs(input_value) ** arousal_exp     # arousal_exp = 2.0
```

> **As built:** exactly the two dimensions above, and only those. `arousal_exp`
> is a module-level configurable.

#### The full dimensional suite — **DESIGN TARGET, NOT YET IMPLEMENTED**

The design calls for EMOTE to compute the complete suite of
information-theoretic dimensions from the input signal, regardless of which
domains will actually use them. These include Shannon's core measures — entropy
(uncertainty and information content), redundancy (predictability and
compressibility), and mutual information (correlation between signals). Signal
characteristics like bandwidth (spread of frequency content), dynamic range
(difference between extremes), signal-to-noise ratio, spectral density
(distribution across frequencies), and temporal density (distribution across
time). Pattern and structure measures including periodicity (regularity of
patterns), complexity (shortest description length), self-similarity (fractal
dimension), and correlation (dependencies between elements). Rate of change
metrics covering first derivative (velocity of change), second derivative
(acceleration), and variance or volatility.

EMOTE makes no assumptions about which dimensions matter for any given domain or
emotional state — it simply computes all of them and provides the full
mathematical profile. Domain applications downstream select whichever subset is
relevant to their output medium, and eventually the feedback loop discovers
through causal inference which dimensions actually drive effective emotional
navigation.

> **Reality check:** none of these are computed today. Most require a *signal
> over time*, and Input currently provides an instantaneous scalar with no
> history — so this expansion depends on Input gaining a time series first.
> The music-theory primitives the opening paragraph places in EMOTE currently
> live downstream in `mi/pattern_primitives.py` and `mi/chord_library.py`.

**Evolution path.** From hardcoded transformations to learned optimization.
Initially, the mathematical relationships between input state and dimensional
outputs are manually defined based on intuition and music theory. As the
feedback loop closes with biosensor input, EMOTE begins discovering which
dimensions and which transformation curves actually succeed at moving users
between emotional states. It learns personal calibration — that for a specific
user, moving from anxious to focused requires a particular dimensional profile
that might differ from another user's optimal profile. Eventually EMOTE
integrates with a novel Causal Inference-based Neurosymbolic Intelligence to
access historical context and state definitions, allowing it to understand not
just "input is at −0.3" but "user wants to reach their recorded 'deep focus'
state and has been trending toward scattered attention for the past hour." The
system discovers its own categories and optimal pathways rather than relying on
predetermined emotional mappings, while maintaining the scientific framework of
valence–arousal space as its foundation.

### 3. Musical Intelligence — **BUILT**

Musical Intelligence is the bridge between EMOTE's abstract information theory
and concrete musical decisions. It subscribes to whichever dimensions from EMOTE
are relevant to its domain and interprets them through transformation functions.
Musical Intelligence operates in two layers: a **Global Layer** that interprets
EMOTE dimensions to establish key, tonality, chord progressions, tempo, meter,
and overall harmonic density, followed by **Role-Specific Interpreters** that
translate this shared musical context into specific parts. The Percussion
Interpreter handles rhythmic patterns, accent placement, and groove. The Bass
Interpreter constructs basslines and manages root movement. The Harmony
Interpreter determines chord voicings, harmonic rhythm, and texture. The Melody
Interpreter creates melodic lines, counterpoint, and lead material.

Musical Intelligence only decides **WHAT** to play — the symbolic structure of
the output — without any knowledge of timbre, synthesis, or sound design. *It's
much closer to the sheet music of the program.* It has no knowledge of how
things will sound, only what will be played. Its output is purely structural
information that Sequencer will organize temporally and Synthesizer will render
as actual audio.

Musical Intelligence works with scales and modes, chord structures, harmonic
progressions, melodic intervals, rhythm patterns, accent patterns, groove
patterns, voice leading concepts, tonality, tempo, and meter. These elements
combine to create the complete symbolic musical structure that downstream
modules will realize as actual sound.

> **As built:**
>
> - **Global Layer** → `mi/global_parameters.py`. Tempo from valence via a
>   logarithmic curve, `min_bpm × (max_bpm/min_bpm)^v`, so perceptual change
>   feels even across the slider — 80→100 feels like 140→180. Key is fixed at C
>   (`CURRENT_KEY = 0`) and read by everything downstream rather than assumed.
>   Meter is fixed at 16 slots per measure. Register width is deliberately *not*
>   global — each instrument owns its own arousal-driven register height.
> - **Harmony Interpreter** → `mi/chord_progression_engine.py`,
>   `mi/chord_library.py`, `mi/chord_instrument.py`.
> - **Bass Interpreter** → `mi/bass_instrument.py`, `mi/bass_modes.py`.
> - **Percussion Interpreter** → `mi/drum_instrument.py`,
>   `mi/accent_pattern_engine.py`, `mi/groove_delay_engine.py`.
> - **Melody Interpreter** → not started.
>
> Chord vocabulary is currently **diatonic**: I, ii, iii, IV, V, vi, vii° plus
> their 7th and 9th extensions. `mi/chord_library.py` already parses far beyond
> that — borrowed roots, altered fifths, sus, and chromatic colors (♯9, ♭9, ♯11,
> ♭13) — so the vocabulary can widen without touching the parser. `mi/bass_modes.py`
> is diatonic-only by the same reasoning and grows a contextual branch when
> non-diatonic chords arrive.

**Evolution path.** From hardcoded progressions to learned harmonic
intelligence. Initially, chord progressions, scale selections, and voice leading
rules are manually defined based on music theory intuition. As the feedback loop
closes with biosensor input, Musical Intelligence begins learning which
interpretations of EMOTE's dimensional outputs actually succeed at emotional
navigation — discovering that certain entropy values map to specific harmonic
densities, or that particular periodicity profiles translate to rhythmic
patterns that reliably induce target states. The system learns personal harmonic
preferences, finding that some users respond to modal interchange while others
need simpler diatonic movement. Eventually Musical Intelligence moves beyond
selecting from preset progressions to generating novel harmonic sequences,
creating chord progressions and melodic patterns that have never existed but
that EMOTE's dimensional profile suggests will work. This evolution happens in
coordination with EMOTE's learning — the two layers co-train, so Musical
Intelligence's interpretations inform which dimensional profiles EMOTE discovers
are effective. Musical Intelligence integrates with a novel Causal
Inference-based Neurosymbolic Intelligence to understand not
just the immediate emotional target but the broader context of user preferences,
time of day, and cumulative listening history, allowing it to compose music that
serves long-term optimization goals rather than just immediate state changes.

> Every tunable in this layer is a named, centralized constant rather than an
> inline magic number — deliberately, so the whole parameter set can eventually
> become a trainable model rather than a hand-tuned one.

### 4. Sonic Intelligence — **NOT STARTED**

Sonic Intelligence is the bridge between Musical Intelligence's symbolic
structure and the actual timbral characteristics of sound. It subscribes to
whichever dimensions from EMOTE are relevant to sound design and interprets them
through transformation functions. Sonic Intelligence operates in two layers: a
**Global Sonic Layer** that interprets EMOTE dimensions to establish overall
timbral aesthetic, spectral character, and textural density, followed by
**Role-Specific Sonic Interpreters** that apply this shared sonic context to
each musical role. The Percussion Sonic Interpreter handles drum timbres,
transient shaping, and rhythmic texture. The Bass Sonic Interpreter determines
low-frequency character, harmonic content, and sustain characteristics. The
Harmony Sonic Interpreter establishes chord timbres, spatial width, and harmonic
color. The Melody Sonic Interpreter creates lead timbres, articulation, and
expressive shaping.

Sonic Intelligence only decides **HOW** things sound — the timbral and textural
qualities — without knowledge of what notes are being played or when. Its output
is synthesis parameter configurations that Synthesizer will use to generate
actual audio.

Sonic Intelligence works with envelope shaping, filtering and filter modulation,
modulation systems, distortion and saturation, spectral processing, waveform
selection and mixing, spatial positioning, and dynamic processing. These
elements combine to create the complete timbral profile that transforms Musical
Intelligence's symbolic structure into perceptually distinct sound.

**Evolution path.** From hardcoded synthesis parameters to learned timbral
intelligence. Initially, envelope curves, filter settings, and effect chains are
manually defined based on sound design intuition. As the feedback loop closes
with biosensor input, Sonic Intelligence begins learning which interpretations
of EMOTE's dimensional outputs actually succeed at emotional navigation —
discovering that certain complexity values map to specific filter resonance
profiles, or that particular spectral density dimensions translate to waveform
mixing ratios that reliably induce target states. The system learns personal
timbral preferences, finding that some users respond to warm saturated tones
while others need clean precise articulation. Eventually Sonic Intelligence
moves beyond selecting from preset patches to generating novel timbral
configurations, creating synthesis parameter combinations that have never
existed but that EMOTE's dimensional profile suggests will work. This evolution
happens in coordination with both EMOTE and Musical Intelligence's learning —
all three layers co-train, so Sonic Intelligence's timbral realizations inform
which musical and dimensional profiles prove effective. Sonic Intelligence
integrates with a novel Causal Inference-based Neurosymbolic Intelligence to
understand not just the immediate sonic target but the broader context of
listening environment, time of day, and cumulative exposure, allowing it to
shape sound that serves long-term optimization goals rather than just immediate
aesthetic preferences.

### 5. Sequencer — **NOT STARTED**

Sequencer is HandBand's universal temporal coordinator, running at audio sample
rate to provide the master clock for the entire system. It operates at 44.1 kHz,
translating between continuous audio time and quantized musical time,
calculating which musical step, beat, and measure correspond to each sample
count based on tempo and meter information from Musical Intelligence. It
triggers note-on and note-off events at precisely the right sample moments,
manages loop wraparound to maintain consistent cycle length, and ensures
sample-accurate synchronization across all Synthesizer instances. Sequencer has
no interpretive role — it executes timing decisions made by Musical Intelligence
with mathematical precision, providing the infrastructure that allows all other
modules to operate in coordinated time.

Sequencer works with sample-accurate timing calculations, tempo and meter
conversion, event scheduling and triggering, loop boundary management, latency
compensation, and multi-synthesizer synchronization. These elements combine to
translate Musical Intelligence's abstract temporal structure into the precise
sample-by-sample timing that Synthesizer needs to generate continuous audio.

> **Interface already fixed.** Musical Intelligence emits a per-slot stream in one
> uniform shape — `{"type": "H", "notes": [...], "accent": <dB>, "timing":
> <offset>}` for a strike, `{"type": "C"}` for a hold, `{"type": "R"}` for
> silence — identical across chords, bass, and every drum element. Turning that
> stream into note-on/note-off events is the Sequencer's job, and it is the next
> module to build.

### 6. Synthesizer — **NOT STARTED** *(prototype exists in `legacy/`)*

Synthesizer is HandBand's audio rendering engine, instantiated per musical role
to generate actual waveforms from symbolic musical information and sonic
parameters. Each role has its own Synthesizer instance — Bass Synthesizer,
Harmony Synthesizer, Percussion Synthesizer, and Melody Synthesizer — configured
for its specific requirements. Synthesizer receives note-on and note-off events
from Sequencer specifying **when** to play, symbolic note information from
Musical Intelligence specifying **what** to play, and timbral parameters from
Sonic Intelligence specifying **how** to sound. It handles both synthesized
waveform generation and sample-based playback, with each instance configured to
use whichever approach suits its role — percussion typically uses sample
playback while bass, harmony, and melody use oscillator synthesis, though any
combination is possible. It generates audio at a configurable sample rate,
managing polyphony and voice allocation as needed for its role. Synthesizer
applies sample-level smoothing to all parameter changes to prevent audio
artifacts like clicks and pops, interpolating between parameter values according
to transition curves specified by Sonic Intelligence. Synthesizer has no
interpretive role — it executes rendering commands with sample-accurate
precision, providing the DSP infrastructure that transforms abstract musical and
sonic decisions into actual sound waves.

Synthesizer works with oscillator generation and mixing, sample playback and
looping, ADSR envelope processing, filter chains and modulation, LFO and FM
synthesis, effects processing including distortion and saturation, voice
allocation for polyphonic parts, sample-level parameter interpolation, and audio
buffer management. These elements combine to render Musical Intelligence's
symbolic structure with Sonic Intelligence's timbral characteristics into
continuous audio streams that are mixed and sent to Output.

> A working C++ synthesis engine — oscillators, filters, ADSR, effects, click
> detection, sample playback through `ctypes` — exists in
> `legacy/programmable-song/synthlib.cpp`. It is not wired to this architecture
> and does not build from what's in the repo, but it is the reference for what
> module 6 becomes.

### 7. Mix/Master — **NOT STARTED**

Mix/Master is HandBand's audio mixing and mastering module, receiving individual
audio streams from all Synthesizer instances and combining them into a final
stereo mix. It handles per-role level balancing and panning to create spatial
width, summing all role outputs while preventing clipping through gain staging.
Mix/Master applies a master processing chain including EQ for tonal balance,
compression for dynamic control, and limiting for safety. It manages per-role
send/return effects like reverb and delay that create shared acoustic space
across all parts. Mix/Master operates at the same sample rate as Synthesizer,
processing audio buffers in real time with minimal added latency. It has no
interpretive role — it executes mixing decisions and applies professional
mastering techniques to ensure the final output is balanced, cohesive, and
technically sound.

Mix/Master works with audio stream summing and routing, per-role gain staging
and panning, spatial processing and stereo width, master EQ and tonal shaping,
multiband compression and limiting, send/return effect chains, metering and
level monitoring, and clipping prevention. These elements combine to transform
multiple individual Synthesizer outputs into a polished final mix ready for
Output delivery.

**Evolution path.** From hardcoded mixing ratios to executing learned mixing
intelligence from the Global Sonic Layer. Initially, per-role levels, panning
positions, master EQ curves, and compression settings are manually defined based
on mixing engineering best practices. As the feedback loop closes with biosensor
input, Mix/Master begins executing mixing decisions learned by the Global Sonic
Layer — discovering that certain spectral balance profiles or compression
characteristics succeed at emotional navigation for specific users. The system
learns personal mixing preferences, finding that some users respond to wider
stereo fields and brighter master EQ while others need centered mono sources and
warmer tones. Eventually Mix/Master executes sophisticated environment-aware
mastering decisions informed by a novel Causal Inference-based Neurosymbolic
Intelligence, adjusting compression ratios for noisy listening environments,
compensating master EQ for different playback systems, and adapting overall
loudness to time of day and user context. This evolution happens in coordination
with the Global Sonic Layer's learning — Mix/Master doesn't learn independently
but rather becomes increasingly sophisticated at executing the mixing vision
that the Global Sonic Layer develops through experience.

### 8. Output — **NOT STARTED**

Output is HandBand's audio delivery module, receiving mixed audio streams from
all Synthesizer instances and managing their transmission to playback hardware.
It handles audio hardware interface configuration, buffer management to minimize
latency while preventing dropouts, sample format conversion as needed for the
target device, and final volume control. Output maintains consistent timing with
Sequencer to ensure sample-accurate delivery, managing the audio driver's
callback system to request the next buffer of samples at precisely the right
moments. Output has no interpretive role — it simply delivers the audio stream
that Synthesizer has generated with maximum fidelity and minimum latency.

Output works with audio hardware interface management, circular buffer systems,
latency compensation and monitoring, sample format conversion between internal
processing format and hardware requirements, device selection and configuration,
and master volume control. These elements combine to reliably deliver HandBand's
generated audio to the user's listening environment.

**Evolution path.** From audio-only delivery to multi-sensory and conceptual
output modalities. Initially handling only audio playback through speakers or
headphones, Output evolves to support visual rendering to displays, haptic
feedback through vibration or tactile interfaces, and eventually explores
olfactory and gustatory outputs where technically feasible. The ultimate vision
includes abstract conceptual outputs such as direct neural interfaces or
augmented reality overlays that can deliver optimization interventions beyond
traditional sensory channels. Each modality follows the same architectural
pattern — receiving rendered output from domain-specific synthesis, managing the
appropriate hardware interface, and delivering with precise timing coordination.
As new output modalities are added, they integrate with Sequencer's universal
timing system to maintain synchronization across all sensory channels, creating
coherent multi-modal experiences rather than isolated stimuli.

### 9. Main Orchestrator — **PARTIAL**

The top-level coordinator: it constructs each module, wires them together, and
owns the application lifecycle.

> **As built:** `main.py` constructs Input and EMOTE, builds one shared
> `SongSource` so every view renders the same generated song, and manages six
> lazily-created child windows behind checkboxes. It does not yet coordinate a
> real-time audio loop, because modules 4 through 8 do not exist. The design
> document leaves this section as a heading only — the orchestrator's full
> specification is still to be written.

---

## Configuration

There is no config file yet. Every module keeps its tunables in a named
`Configurables` block or a set of module-level constants at the top of the file
— `arousal_exp` in `emote.py`, `CURRENT_KEY` in `mi/global_parameters.py`,
`MAX_ACCENT_DB` in `mi/instrument.py`, the whole tunable block in
`mi/drum_instrument.py`, and so on. This is deliberate: the long-term intent is
for that parameter set to become trainable, which means it has to be named and
centralized before it can be learned. The "Config Dictionaries and File Loading"
module named in the original architecture is not yet built.

## Glossary

**Valence** — the pleasure–displeasure axis, −1 … +1. Drives tempo, progression
length, cadence type, syncopation, contour tilt, groove direction, bass fill.

**Arousal** — the activation–deactivation axis, 0 … 1. Drives chord density,
accent density, groove intensity, note density, register width, articulation,
voicing dispersion, contour wiggle.

**Slot** — one 16th note. The system's atomic time unit; 16 slots per measure.

**Cell** — a short rhythmic pattern that repeats across the song. The bass and
drums generate one cell and tile it, which is what makes a part read as a riff
rather than a line that wanders.

**Form** — the section-repetition pattern (`AABA`, `ABCAB`, …). Generated once
by the harmonic engine and inherited by every other engine.

**H / C / R** — the per-slot alphabet: **H**it (strike), **C**ontinue (still
ringing), **R**est (silence). The bass's internal rhythm calls a rest `X` before
realization converts it to `R`.

---

## The 2025 prototype

`legacy/programmable-song/` holds the system HandBand grew out of — a realtime
generative song engine in Python driving a C++ synthesis library, developed
April–October 2025. It ran and it made music. It also grew into a single 199 KB
file, which is exactly why the current architecture separates symbolic decisions
from sound.

Its history was reconstructed from dated file snapshots and is preserved in this
repo's commit log; `v1.0`, `v2.0`, `v3.0`, and `v3.1` are tagged. See
[`legacy/README.md`](legacy/README.md) for the full account, including what
carried forward and why it's archived.
