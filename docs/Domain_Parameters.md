# Domain Parameters

The full parameter inventory across the four domains, converted verbatim
from `HandBand Stuff.pages`. It predates the Musical/Sonic **Domain** ->
**Intelligence** rename, and it describes the 2025 prototype's parameter
set -- so read it as the source material for module 4 (Sonic
Intelligence, not started) rather than as a description of what is built.

# SONIC DOMAIN - Parameters controlling TIMBRE:

## Oscillators:

- Waveform type (sine/square/triangle/saw/sample)
- Oscillator gain
- FM depth

## Amplitude Envelope:

- Attack time
- Decay time
- Sustain level
- Release time

## Filter:

- Cutoff frequency
- Resonance
- Drive
- Key tracking amount
- Envelope modulation amount

## Filter Envelope:

- Attack time
- Decay time
- Sustain level
- Release time

## Comb Filter:

- Cutoff frequency
- Resonance
- Drive
- Key tracking amount
- Envelope modulation amount

## LFO:

- Rate
- Depth
- Level

## Effects:

- Tube saturation amount
- Tube min mix
- Tube max mix
- Bitcrusher bit depth
- Bitcrusher mix

## EQ:

- High-shelf gain (dB)
- Low-mid gain (dB)
- Global gain (dB)

# MUSIC DOMAIN

- Chord progression
- Chord Rhythm
- Bass pattern
- Bass Rhythm
- Modal Scale
- Contextual scale selection rules (based on previous/next/target chord)
- Chord octave range

# SEQUENCER DOMAIN (Timing, Rhythm, Pattern)

## Timing System

- BPM (min 80, max 180, default 120)
- BPM ramping (over configurable measures)
- Master timing centralization (master_step, master_seconds_per_16th, master_current_bpm)
- Seconds per 16th note calculation
- Next trigger time tracking

## Pattern System

- 17 emotional levels (SadLevel8 → Neutral → HappyLevel8)
- Pattern matrices for:
- Kick drums
- Snare drums
- Cymbals
- Bass
- Piano (chord progressions)
- Pattern indexing/selection
- Pattern change detection (immediate vs. measure boundary)
- Pattern wraparound/cycling

## Sequencer Steps

- 16 steps per measure (STEPS_PER_MEASURE)
- Step counter (master_step)
- Last processed step tracking
- Continue logic ('c')
- Rest logic (0)

## Progression System

- Chord progression tracking
- Measure count
- Chord index within progression
- Progression length calculation
- Progression cycling/wraparound
- Next chord detection (with lookahead)

## Rhythm & Articulation

- Delay patterns (per emotional level, per step)
- Drum accent patterns (gain per step)
- Note duration multiplier
- Kick boost/fade-in
- Delay offsets (drums, piano, bass, PortAudio)

## Thread Coordination

- Sequencer barrier (3-way sync: master, bass, piano)
- Piano chord ready event
- Bass pattern ready event
- Stop event
- Per-synth sequencer threads
- Poly-synth sequencer threads

# CROSS-DOMAIN (Affects Multiple Systems)

## Parameter Mapping

- Slider to BPM (logarithmic)
- Slider to pattern index
- Slider to log range (for time-based parameters)
- Slider to log-hybrid range (handles zero values)
- Slider to log gain
- Slider to global gain dB
- Slider to high-shelf dB
- Slider to low-mid dB

## Parameter Ramping

- Start/target values for all rampable parameters
- Ramp start time
- Ramp duration (in measures)
- Ramp progress calculation
- All ADSR parameters
- All oscillator gains
- All filter parameters
- All LFO parameters
- All tube driver parameters
- All bitcrusher parameters
- FM depth
- Global filter offsets

## Compensation Systems

- Piano volume compensation (for oscillator dip around 0.4 slider value)
- Parameter change compensation
- Compensation smoothing time
- Max compensation adjustment

## State Management

- First slider change flag
- Note playing state (per synth)
- Currently sounding chord
- Last active chord
- Global delay
- Slider value (with thread safety)
- Previous slider value

This is comprehensive! The refactor would clearly benefit from separating these concerns into their respective domain modules.
