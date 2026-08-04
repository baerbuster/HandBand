# HandBand Music Sequencer - Technical Documentation

> Converted verbatim from `HandBand DOcumentation.pages`, which sits
> beside this file. It documents the **2025 prototype** in this folder --
> the Python/C++ system described below is `legacy/programmable-song/`,
> not the current `handband/` package.

## System Overview

**HandBand** is a real-time, emotionally-responsive music sequencer that generates bass, piano, and drum patterns based on a single slider input (0.0-1.0 representing sad→neutral→happy). The system consists of:

- **Python Frontend**: Musical logic, pattern selection, sequencing, and GUI
- **C++ Audio Engine**: Real-time synthesis, DSP effects, and audio output via PortAudio
- **Communication**: Python controls C++ synthesizers through ctypes bindings

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      PYTHON LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  GUI (Tkinter Slider) → slider_val (0.0 - 1.0)              │
│         ↓                                                     │
│  Pattern Selection (17 emotional levels)                     │
│         ↓                                                     │
│  ┌──────────────┬──────────────┬──────────────┐            │
│  │ Piano Thread │ Bass Thread  │ Drum Thread  │            │
│  │ (Polyphonic) │ (Monophonic) │ (Samples)    │            │
│  └──────┬───────┴──────┬───────┴──────┬───────┘            │
│         │              │              │                      │
│         └──────────────┴──────────────┘                      │
│                    ↓                                          │
│         Master Timing Coordinator                            │
│         (sequencer_barrier)                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ ctypes bindings
┌─────────────────────┴───────────────────────────────────────┐
│                      C++ LAYER                               │
├─────────────────────────────────────────────────────────────┤
│  SynthManager (manages multiple Synthesizer instances)       │
│         ↓                                                     │
│  ┌─────────────────────────────────────────────┐            │
│  │  Synthesizer Instance (per voice)           │            │
│  │  ├─ Oscillators (sine/square/saw/sample)    │            │
│  │  ├─ ADSR Envelope                           │            │
│  │  ├─ Filter 1 (Lowpass + Drive)              │            │
│  │  ├─ Comb Filter                             │            │
│  │  ├─ Tube Driver (saturation)                │            │
│  │  ├─ Bitcrusher                              │            │
│  │  └─ LFO (disabled for stability)            │            │
│  └─────────────────────────────────────────────┘            │
│         ↓                                                     │
│  Audio Callback (paCallback) - mixes all synths             │
│         ↓                                                     │
│  PortAudio → Hardware Output                                │
└─────────────────────────────────────────────────────────────┘
```

## Key Subsystems

### 1. Master Timing System

**Purpose**: Synchronize all instruments to a unified clock

#### Key Variables:

```
master_step = 0              # Current 16th note (0-15 in a measure)
master_seconds_per_16th      # Time per 16th note (from BPM)
master_current_bpm           # Current BPM (smoothly ramped)
master_next_trigger          # Timestamp for next step
```

#### Flow:

- sequencer_timing_only() thread acts as the master clock
- Calculates BPM ramps over BPM_RAMP_MEASURES (4 measures default)
- At each step boundary:
- Triggers drums (sample playback)
- Increments master_step
- Waits at sequencer_barrier for all synth threads

#### Thread Synchronization:

```
sequencer_barrier = threading.Barrier(3)  # Piano, Bass, Master
bass_pattern_ready = threading.Event()    # Bass signals pattern analysis complete
piano_chord_ready = threading.Event()     # Piano signals chord context ready
```

### 2. Musical Pattern System

#### Emotional Mapping:

```
PATTERN_LABELS = [
    "SadLevel8" (0.0),    # Darkest
    ...
    "Neutral" (0.5),      # Middle
    ...
    "HappyLevel8" (1.0)   # Brightest
]
```

#### Pattern Types:

- **Drum Patterns**: Binary arrays (1=hit, 0=rest) for kick/snare/cymbal
- **Bass Patterns**: Scale degree strings ('1', '3', '5', 'c'=continue, 0=rest)
- **Piano Patterns**: Roman numeral chords ('I', 'vi', 'IV', 'V7', etc.)

#### Pattern Selection:

```
target_pattern_index = int(round(slider_val * 16))  # 0-16 (17 levels)
```

### 3. Harmonic System

#### Modal Scale Selection

#### The system uses contextual modal scales based on:

- Current chord symbol
- Previous chord (for continuity)
- Next/target chord (for anticipation)
```
def get_scale_for_chord(chord_symbol, previous_chord=None, 
                        next_chord=None, target_chord=None):
    # Returns appropriate mode (ionian, dorian, phrygian, etc.)
    # Based on harmonic context
```

#### Example:

```
# I chord normally uses ionian (major scale)
# But I7 going to IV uses blues scale instead
if chord_symbol.startswith('I7'):
    if next_chord and next_chord.startswith('IV'):
        return SCALES['blues']
```

#### Key Change System

#### Pivot Chord Modulation:

```
def calculate_key_change(old_pattern, new_pattern, 
                         pivot_chord, proto_chord, target_chord):
    # Pivot chord: Last chord in old key
    # Proto chord: "Where we came from" in new progression
    # Target chord: Next chord in new progression
    
    # Calculates harmonic interval between proto→target
    # Applies that interval from pivot position
    # Returns new key offset (-11 to +11 semitones)
```

#### Quality Adjustments:

- Major/minor/dim/aug chord differences handled
- Smooths transitions by adjusting chord roots

#### Application:

```
# At measure boundary when pattern changes:
apply_key_change(calculated_offset)
current_key = new_key_offset  # Global transposition
```

### 4. Bass Sequencer Logic

#### Threading Model:

```
def synth_sequencer_thread(stop_event, synth, synth_id, slider_val_lock):
    while not stop_event:
        # Wait for piano to set chord context
        piano_chord_ready.wait()
        
        # Analyze upcoming pattern transitions
        if target_pattern != current_pattern:
            UPCOMING_PATTERN_INDEX = target_pattern
            TRANSITIONAL_CHORD_SYMBOL = proto_chord
            BASS_PREVIEW_KEY = provisional_key
        
        # Get bass degree from pattern
        degree = BASS_PATTERNS[pattern][step]
        
        # Convert to MIDI using modal scale
        midi_note = get_bass_note(degree, current_chord, base_note, ...)
        
        # Apply delay (for groove)
        delay = delay_patterns_ms[pattern][step]
        
        # Trigger note via C++
        synth.set_frequency(freq_from_midi(midi_note), synth_id)
        synth.note_on(synth_id)
```

#### Key Features:

- **Preview System**: Uses BASS_PREVIEW_KEY during transitions for smooth modulation
- **Modal Conversion**: Converts scale degrees to actual notes based on chord context
- **Delay Patterns**: Adds groove by delaying certain steps

### 5. Piano Sequencer Logic

#### Polyphony Management:

```
class PolySynth:
    voices = []  # Multiple SynthInstance objects
    active_notes = {}  # Track which voice plays which note
    
    def play_chord(self, midi_notes):
        # Stop all current notes
        for note in active_notes:
            note_off(note)
        
        # Allocate voices consistently
        for note in sorted(midi_notes):
            voice_index = get_available_voice()
            note_on(note)
```

#### Chord Progression:

```
# Piano patterns are 2D arrays:
PIANO_PATTERNS[pattern_index][measure_index][step_index]

# At each step:
chord_str = progression[measure % len(progression)][step]

if chord_str == 'c':
    # Continue previous chord
elif chord_str == 0:
    # Rest
else:
    # Parse Roman numeral to MIDI notes
    midi_notes = parse_roman_numeral_chord(chord_str, base_note)
    poly_synth.play_chord(midi_notes)
```

#### Chord Context Sharing:

```
# Piano sets global state for bass to use:
CURRENT_CHORD_SYMBOL = degree  # e.g., "vi", "V7"
CURRENT_CHORD_ROOT = get_chord_root(degree)  # e.g., "6", "5"
piano_chord_ready.set()  # Signal bass thread
```

### 6. Drum Sequencer

#### Sample-Based Playback:

```
# Pre-loaded samples for each emotional level
kick_cache = {label: pygame.mixer.Sound(path) for label in PATTERN_LABELS}
snare_cache = {...}
cymbal_cache = {...}
```

#### Triggering:

```
def trigger_drums_for_step(step, pattern_index, drum_delay_ms):
    # For each drum type:
    if KICK_PATTERNS[pattern][step]:
        delay = delay_patterns_ms[pattern][step]
        gain = DRUM_ACCENT_PATTERNS[pattern][step]
        play_kick_sample_with_delay_and_gain(label, delay, gain)
```

#### EQ Processing:

```
# Applies global EQ to match synthesizer timbre
def apply_global_eq_to_sound(sound, slider):
    highshelf_db = slider_to_global_highshelf_db(slider)
    lowmid_db = slider_to_lowmid_db(slider)
    # Apply biquad filters...
```

### 7. C++ Synthesizer Engine

#### Synthesizer Class Structure

```
class Synthesizer {
    // Core State
    double phase;              // Oscillator phase (0-2π)
    double frequency;          // Current frequency (Hz)
    EnvelopeState envelopeState;  // ATTACK, DECAY, SUSTAIN, RELEASE, IDLE
    
    // Oscillators (variable count or legacy 2-osc)
    int oscCount;              // 0 = legacy mode
    int oscWaveform[MAX_OSC];  // SINE, SQUARE, TRIANGLE, SAW, SAMPLE
    double currentOscGain[MAX_OSC];
    
    // ADSR Envelope
    double attackTime, decayTime, sustainLevel, releaseTime;
    unsigned long sampleCount;  // Tracks position in envelope
    
    // Filters
    double b0, b1, b2, a1, a2;  // Biquad coefficients
    double z1, z2;              // Filter state (Direct Form II)
    
    // Effects
    std::vector<double> combDelayLine;  // Comb filter buffer
    // Tube driver, bitcrusher params...
};
```

#### Audio Callback Flow

```
static int paCallback(...) {
    // For each frame:
    for (unsigned long i = 0; i < framesPerBuffer; i++) {
        float mixedOutput = 0.0f;
        
        // For each active synthesizer:
        for (Synthesizer* synth : activeSynths) {
            
            // 1. Calculate ADSR envelope
            switch (envelopeState) {
                case ATTACK: amplitudeMultiplier = sampleCount / attackSamples;
                case DECAY:  amplitudeMultiplier = 1.0 → sustainLevel;
                // etc.
            }
            
            // 2. Generate oscillator waveforms
            double rawSine = sin(phase + fmDepth * sin(phase));
            double rawSquare = rawSine >= 0 ? 1.0 : -1.0;
            // etc.
            
            // 3. Mix oscillators with gains
            combined = currentOscGain[0] * osc1 + currentOscGain[1] * osc2;
            
            // 4. Apply gain normalization
            normalizer = 1.0 / sqrt(gainPower);
            combined *= normalizer;
            
            // 5. Process through effect chain
            combined = processFilter(combined);      // Lowpass + drive
            combined = processCombFilter(combined);  // Comb filter
            combined = processTubeDriver(combined);  // Saturation
            combined = processBitcrusher(combined);  // Digital distortion
            
            // 6. Apply master volume and envelope
            outputSample = amplitude * amplitudeMultiplier * combined * masterVolume;
            
            // 7. Mix into output
            mixedOutput += outputSample;
            
            // 8. Update phase for next sample
            phase += phaseIncrement;
        }
        
        // Limiter and output
        out[i] = clamp(mixedOutput, -1.0, 1.0);
    }
}
```

#### Filter Processing

#### Biquad Lowpass Filter:

```
double Synthesizer::processFilter(double inSample) {
    // Pre-drive saturation
    double x = tanh(inSample * (1.0 + drivePct * 4.0));
    
    // Direct Form II Transposed
    double y = b0 * x + z1;
    z1 = b1 * x - a1 * y + z2;
    z2 = b2 * x - a2 * y;
    
    return y;
}
```

#### Coefficient Calculation:

```
void calculateBiquadCoefficients(double cutoffHz, double resonanceQ) {
    // Includes modulation from:
    // - Global cutoff offset
    // - Key tracking (follows note pitch)
    // - Filter envelope
    
    effectiveCutoff = currentFilterCutoff 
                    * globalCutoffScale 
                    * pow(keyRatio, keyTrackPct)
                    * pow(10, envLevel * envModPct);
    
    // Standard biquad cookbook formulas...
}
```

#### Comb Filter:

```
double processCombFilter(double inSample) {
    // Delay-based resonator
    double delayedSample = combDelayLine[readPos];
    double output = inSample + feedback * delayedSample;
    combDelayLine[writePos] = tanh(output);  // Soft limiter
    return output;
}
```

## Critical Timing & Synchronization

### The Three-Phase Step Cycle

```
# At each 16th note boundary:

# PHASE 1: Piano Analysis (immediate)
piano_chord_ready.clear()
current_chord_symbol = pattern[measure][step]
CURRENT_CHORD_ROOT = get_chord_root(current_chord_symbol)
piano_chord_ready.set()  # ← Bass can now read chord context

# PHASE 2: Bass Pattern Analysis
bass_pattern_ready.clear()
if slider_moved:
    UPCOMING_PATTERN_INDEX = new_pattern
    UPCOMING_PROTO_CHORD = calculate_transition_chord()
    BASS_PREVIEW_KEY = calculate_provisional_key()
bass_pattern_ready.set()  # ← Master knows bass is ready

# PHASE 3: Synchronization Barrier
sequencer_barrier.wait()  # All three threads wait here

# Only when all three threads hit the barrier do they continue
# to the next step. This ensures perfect synchronization.
```

### Why This Works

- **Piano goes first**: Sets harmonic context needed by bass
- **Bass analyzes**: Can look ahead for smooth transitions
- **Barrier sync**: Ensures no thread gets ahead/behind
- **Master increments**: Only master advances master_step
```
```

## Parameter Smoothing System

### The Problem

Instant parameter changes cause audio clicks/pops.

### The Solution

```
// In audio callback, smooth towards target:
double smoothingStep = 1.0 / gainSmoothingSamples;

if (currentSineGain < targetSineGain) {
    currentSineGain += smoothingStep;
    if (currentSineGain > targetSineGain)
        currentSineGain = targetSineGain;
}
```

#### Smoothed Parameters:

- Oscillator gains
- ADSR envelope times
- Filter cutoff/resonance
- All effect parameters

**Smoothing Duration**: GAIN_SMOOTHING_TIME_SECONDS (0.5s default)

## Musical Theory Implementation

**Scale Degree **→** MIDI Conversion**

```
def get_bass_note(degree_str, chord_symbol, base_midi_note, ...):
    # 1. Get chord root offset
    chord_root_offset = interval_to_semitone[get_chord_root(chord_symbol)]
    
    # 2. Get modal scale for this chord
    modal_scale = get_scale_for_chord(chord_symbol, prev_chord, next_chord)
    # e.g., ['1','2','b3','4','5','b6','b7','8'] for dorian
    
    # 3. Map degree to scale position
    scale_position = int(degree_str) - 1  # '3' → index 2
    modal_degree = modal_scale[scale_position]  # '3' → 'b3' in dorian
    
    # 4. Convert to semitones
    modal_interval = interval_to_semitone[modal_degree]
    
    # 5. Calculate final MIDI note
    midi_note = base_midi_note + chord_root_offset + modal_interval + current_key
    
    return clamp_bass_to_octave(midi_note)
```

### Chord Parsing

```
def parse_roman_numeral_chord(chord_str, base_midi_note):
    # "V7" → ["G", "B", "D", "F"] in C major
    
    # 1. Extract Roman numeral and quality
    roman_part = extract_roman("V7")  # → "V"
    is_major = roman_part.isupper()   # → True
    
    # 2. Get root note
    root_degree = roman_to_scale_degree["V"]  # → "5"
    root_semitones = interval_to_semitone["5"]  # → 7
    root_midi = base_midi_note + root_semitones + current_key
    
    # 3. Build triad
    third_semitones = 4 if is_major else 3
    fifth_semitones = 7
    
    chord_notes = [root_midi, 
                   root_midi + third_semitones,
                   root_midi + fifth_semitones]
    
    # 4. Add extensions
    if "7" in chord_str:
        seventh_semitones = 11 if "M7" else 10
        chord_notes.append(root_midi + seventh_semitones)
    
    return sorted(chord_notes)
```

## Delay and Groove System

**Sad Patterns** (mechanical feel):

```
DELAY_BASE_SAD_MS = [12, 10, 8, 6, 5, 4, 3, 0]  # ms
# Only beats 2 and 4 delayed
delay_patterns_ms[sad_level] = [0,0,0,0, delay, 0,0,0, 0,0,0,0, delay, 0,0,0]
```

**Happy Patterns** (swung feel):

```
DELAY_HAPPY_FACTOR = 0.25  # Reduced delay
# All off-beats slightly delayed
delay_patterns_ms[happy_level] = [0,d,0,d, 0,d,0,d, 0,d,0,d, 0,d,0,d]
```

#### Application:

```
# Drums
threading.Timer(delay_ms / 1000, play_sample).start()

# Bass/Piano  
time.sleep(delay_ms / 1000)
trigger_note()
```

## Common Gotchas & Solutions

### 1. Thread Safety

**Problem**: Multiple threads modifying synth parameters **Solution**: All C++ parameter access wrapped in std::lock_guard<std::mutex>

```
extern "C" void set_frequency(double freq, int synthId) {
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->frequency = freq;
    synth->updatePhaseIncrement();
}
```

### 2. Audio Explosions

**Problem**: Filters/effects cause volume spikes **Solution**:

- Gain normalization after oscillator mixing
- Soft clipping in filters (tanh)
- Final limiter before output
```
// Normalize oscillator mix
double gainPower = gain1² + gain2²;
normalizer = 1.0 / sqrt(gainPower);
combined *= min(GAIN_NORMALIZATION_CAP, normalizer);

// Soft clip
output = tanh(output);

// Hard limit
out[i] = clamp(mixedOutput, -1.0, 1.0);
```

### 3. Pattern Transition Clicks

**Problem**: Instant pattern change mid-measure sounds bad **Solution**: Only change patterns at master_step == 0 (measure boundary)

```
if target_pattern_index != current_pattern and current_step == 0:
    current_pattern = target_pattern
    apply_key_change()
```

### 4. Bass/Piano Desynchronization

**Problem**: Piano and bass playing different chords **Solution**: Event-based signaling ensures piano always sets context first

```
# Piano
CURRENT_CHORD_SYMBOL = new_chord
piano_chord_ready.set()

# Bass waits
piano_chord_ready.wait()  # Blocks until piano is done
use_CURRENT_CHORD_SYMBOL_for_scale_lookup()
```

## Configuration Deep Dive

### Synth Configuration Dictionary

```
BASS_CONFIG = {
    "name": "bass",
    "patternSet": "bass",  # Which pattern array to use
    "masterVolume": 10.0,
    
    # Oscillator setup
    "osc1_waveform": "sine",
    "osc2_waveform": "sample",
    "min_osc1_gain": 1.0,    # Gain at slider=0 (sad)
    "max_osc1_gain": 0.5,    # Gain at slider=1 (happy)
    
    # ADSR bounds (sad → happy)
    "minAttack": 0.155,   # Slower attack when sad
    "maxAttack": 0.018,   # Faster attack when happy
    "minDecay": 0.385,
    "maxDecay": 60.0,
    
    # Filter bounds
    "min_filter_cutoff": 50.0,    # Dark when sad
    "max_filter_cutoff": 50.0,    # (same, no change)
    "min_filter_resonance": 0.25,
    "max_filter_resonance": 12.22,  # More resonance when happy
    
    # ... many more parameters
}
```

#### How It's Used:

```
# 1. Create instance
bass_synth = SynthInstance(BASS_CONFIG)

# 2. On slider change, interpolate between min/max
def on_slider_change(val):
    attack = slider_to_log_range(val, 
                                  config["minAttack"], 
                                  config["maxAttack"])
    synth.set_attack(attack, synth_id)
```

## Initialization Sequence

```
# 1. C++ System Init
synth.initialize_synth_system()  # Pa_Initialize()

# 2. Create Synth Instances
bass_synth = SynthInstance(BASS_CONFIG)
piano_poly = PolySynth(PIANO_CONFIG, voice_count=4)

# 3. Pre-Initialize Parameters
on_slider_change(0.5)  # Set neutral state

# 4. Start Audio Stream
for synth_id in SYNTH_INSTANCES:
    synth.start_synth(synth_id)  # Pa_OpenStream(), Pa_StartStream()

# 5. Start Sequencer Threads
sequencer_thread = threading.Thread(target=sequencer_timing_only)
sequencer_thread.start()

# 6. Launch GUI
root = tk.Tk()
slider = tk.Scale(command=on_slider_change)
root.mainloop()
```

## Debugging Tools

### Audio Explosion Detector

```
static float last_output = 0.0f;
if (mixedOutput > 0.05f) {  // Loud sample
    std::cout << "EXPLOSION - Output: " << mixedOutput 
              << " Previous: " << last_output << std::endl;
}
```

### Timing Diagnostics

```
drum_trigger_time = time.time()
print(f"DRUM TRIGGER: Step {step} at {drum_trigger_time:.6f}")
```

### Pattern Analysis

```
print(f"KEY_CHANGE: {key_change} from pattern {old} to {new}")
print(f"PIVOT: {pivot_chord}, PROTO: {proto_chord}, TARGET: {target_chord}")
```

## Performance Characteristics

- **Sample Rate: 44.1 kHz**
- **Buffer Size**: 256 samples (~5.8ms latency)
- **CPU Usage**: ~15-25% on modern CPU (3 synths active)
- **Thread Count**: 4 (Master, Piano, Bass, GUI)
- **Real-time Safety**: All audio processing lock-free except parameter updates

## Future Improvements (from code TODOs)

- **LFO Re-enabling**: Currently disabled for stability, could add pitch vibrato
- **Memory Management**: Could use object pools for synth voices
- **Pattern Expansion**: More diverse drum patterns, chord voicings
- **Performance**: SIMD optimization for filter processing
- **UI**: Visualize current chord, key, pattern level

This documentation should give you a solid understanding of how the system works from the 30,000-foot view down to the implementation details. The key insight is that it's a **multi-layered system** where:

- **GUI **→** Slider value (emotional state)**
- **Slider **→** Pattern selection (17 levels)**
- **Patterns **→** Musical events (notes, chords, drum hits)**
- **Events **→** Synth parameters (frequencies, envelopes)**
- **Synths **→** Audio samples (DSP processing)**
- **Samples **→** Hardware (PortAudio output)**

All carefully synchronized through threading barriers and event signaling.
