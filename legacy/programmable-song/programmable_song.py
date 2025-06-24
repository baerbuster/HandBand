import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import time
import threading
import tkinter as tk
import math
from pedalboard import Pedalboard, Reverb
import numpy as np
import pygame.sndarray 
import pyaudio

# ============================================================================
# CONFIGURATION SECTION - ADJUST THESE VALUES TO CUSTOMIZE THE SYSTEM
# ============================================================================

## AUDIO SETTINGS
SAMPLE_RATE = 44100
BUFFER_SIZE = 1024
MASTER_VOLUME = 0.5

## TIMING SETTINGS
MIN_BPM = 80                    # Minimum BPM slider can reach
MAX_BPM = 180                   # Maximum BPM slider can reach
DEFAULT_BPM = 120               # Starting BPM
STEPS_PER_MEASURE = 16          # Number of steps in each pattern
BASS_NOTE_DURATION_FACTOR = 0.875  # Notes end before next beat (0.0-1.0)

## DRUM SETTINGS
KICK_BOOST_DB = 6.0             # Extra volume boost for kicks (dB)
KICK_FADE_IN_MS = 10            # Fade-in time to prevent clicks (ms)
DRUM_DELAY_OFFSET = 0.04        # Global drum timing offset (seconds)

## EFFECT PARAMETER RANGES
# Resonant Filter
RESONANCE_MIN = 0.1             # Minimum filter resonance
RESONANCE_MAX = 0.3             # Maximum filter resonance

# Tube Drive
TUBE_GAIN_MIN = 1.0             # Minimum tube drive gain
TUBE_GAIN_MAX = 3.0             # Maximum tube drive gain
TUBE_BIAS_MIN = 0.0             # Minimum tube bias
TUBE_BIAS_MAX = 0.2             # Maximum tube bias
TUBE_BLEND_MIN = 0.0            # Minimum tube blend
TUBE_BLEND_MAX = 0.5            # Maximum tube blend

# Bitcrusher
BITCRUSHER_BIT_DEPTH = 12       # Bit depth for bitcrusher effect
BITCRUSHER_DOWNSAMPLE_FACTOR = 3 # Downsample factor
BITCRUSHER_MIX_MAX = 0.25       # Maximum bitcrusher mix

# LFO Settings
LFO_RATE = 3.22                 # LFO frequency (Hz)
LFO_DEPTH_MIN = 0.001           # Minimum LFO depth
LFO_DEPTH_MAX = 3.81            # Maximum LFO depth

# Filter Envelope
FILTER_PEAK_FREQ = 22.53        # Peak frequency for filter envelope
FILTER_SUSTAIN_FREQ = 20        # Sustain frequency for filter envelope

# ADSR Envelope Ranges
ADSR_ATTACK_MIN = 0.018         # Minimum attack time (18ms)
ADSR_ATTACK_MAX = 0.155         # Maximum attack time (155ms)
ADSR_DECAY_MIN = 0.385          # Minimum decay time (385ms)
ADSR_DECAY_MAX = 60.0           # Maximum decay time (60s)
ADSR_RELEASE_MIN = 0.1          # Minimum release time (100ms)
ADSR_RELEASE_MAX = 1.13         # Maximum release time (1130ms)
ADSR_SUSTAIN_DB_MIN = -15.65    # Minimum sustain level (dB)
ADSR_SUSTAIN_DB_MAX = 0.0       # Maximum sustain level (dB)

# Comb Filter
COMB_DELAY_MIN = 0.005          # Minimum comb delay (5ms)
COMB_DELAY_MAX = 0.02           # Maximum comb delay (20ms)
COMB_FEEDBACK = 0.01            # Fixed comb feedback
COMB_DRIVE_BASE = 0.15          # Base comb drive amount

# Global EQ Ranges
GLOBAL_GAIN_DB_RANGE = 5.0      # ±5dB range for global gain
HIGHSHELF_DB_RANGE = 2.0        # ±2dB range for high shelf
LOWMID_DB_RANGE = 1.0           # ±1dB range for low-mid

# ---------------------------------------------------------------------------
# Global EQ Settings – actual filter parameters
# ---------------------------------------------------------------------------
# (These are used by the new bi-quad EQ helpers further below)
HIGHSHELF_FREQ_HZ     = 3000     # High-shelf starts at 3 kHz
HIGHSHELF_SLOPE_DB_OCT = 12      # 12 dB/oct ≈ 2-pole “gentle” shelf
LOWMID_CENTER_FREQ_HZ = 300      # Low-mid peaking-EQ centre
LOWMID_Q_FACTOR       = 2.0      # Q factor (bandwidth) for low-mid band

# Smoothing Factors
PARAMETER_SMOOTHING = 0.005     # How fast parameters change (0.001-0.1)
VOLUME_SMOOTHING = 0.5          # Volume crossfade speed

# Final Filter Settings
FINAL_FILTER_MIN_FREQ = 183     # Minimum final filter cutoff
FINAL_FILTER_MAX_FREQ = 20000   # Maximum final filter cutoff

## SAMPLE PATHS AND FILE NAMING
SAMPLE_BASE_PATH = "ProgrammableLoop2/ProgrammableLoop2"
KICK_SAMPLE_PREFIX = "Kick"
SNARE_SAMPLE_PREFIX = "Snare"
CYMBAL_SAMPLE_PREFIX = "Cymbal"
BASS_SAMPLE_FILENAME = "BassSynthOscillatorSample.wav"
SAMPLE_SUFFIX = ".wav"

## TONIC AND MUSICAL SETTINGS
TONIC_MIDI_NOTE = 36            # C2 - root note for bass patterns
BASE_GAIN_DB = 10               # Base gain for samples

## PATTERN LABELS
PATTERN_LABELS = [
    "SadLevel8", "SadLevel7", "SadLevel6", "SadLevel5",
    "SadLevel4", "SadLevel3", "SadLevel2", "SadLevel1", 
    "Neutral",
    "HappyLevel1", "HappyLevel2", "HappyLevel3", "HappyLevel4",
    "HappyLevel5", "HappyLevel6", "HappyLevel7", "HappyLevel8"
]

# ---------------------------------------------------------------------------
# PATTERN MATRICES – EDIT THESE TO CHANGE THE MUSICAL PATTERNS
# Each pattern is 16 steps (4 beats of 16-th notes).  The list index of every
# matrix aligns with PATTERN_LABELS order (SadLevel8 → HappyLevel8).
# ---------------------------------------------------------------------------

# Kick drum patterns (1 = kick, 0 = silence)
KICK_PATTERNS = [
    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],  # SadLevel8
    [1,0,1,0, 0,0,0,0, 1,0,0,0, 1,0,0,0],  # SadLevel7
    [1,0,0,0, 1,0,0,0, 1,0,0,1, 0,0,0,0],  # SadLevel6
    [1,0,0,0, 1,0,0,0, 1,0,1,0, 0,0,0,0],  # SadLevel5
    [1,0,1,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],  # SadLevel4
    [1,0,0,1, 0,0,0,0, 1,0,1,0, 0,0,0,0],  # SadLevel3
    [1,0,1,0, 0,0,0,0, 1,0,0,1, 0,0,0,0],  # SadLevel2
    [1,0,0,0, 0,0,0,0, 1,0,1,0, 0,0,0,0],  # SadLevel1
    [1,0,0,0, 0,0,0,0, 1,0,1,0, 0,0,0,0],  # Neutral
    [1,0,0,0, 0,0,0,0, 1,0,1,0, 0,0,0,0],  # HappyLevel1
    [1,0,0,0, 0,0,0,0, 1,0,1,0, 1,0,0,0],  # HappyLevel2
    [1,0,0,0, 1,0,0,0, 1,0,1,0, 1,0,0,0],  # HappyLevel3
    [1,0,0,0, 1,0,0,0, 1,0,0,1, 1,0,0,0],  # HappyLevel4
    [1,0,1,0, 1,0,0,0, 1,0,0,1, 1,0,0,0],  # HappyLevel5
    [1,0,1,0, 1,0,1,0, 1,0,0,1, 1,0,0,0],  # HappyLevel6
    [1,0,1,0, 1,0,1,0, 1,0,0,1, 1,0,1,0],  # HappyLevel7
    [1,0,1,1, 1,0,1,0, 1,0,0,1, 1,0,1,0],  # HappyLevel8
]

SNARE_PATTERNS = [
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ], #SadLevel8
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ], #Neutral
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,1,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,1,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,1,0,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,1,0, 0,0,0,0, 1,0,0,0, ],
    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,1, ], #HappyLevel8
]

CYMBAL_PATTERNS = [
    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0, ], #SadLevel8
    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0, ],
    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0, ],
    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0, ],
    [1,0,1,0, 1,0,0,0, 1,0,0,0, 1,0,0,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,0,0, 1,0,0,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,0,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0, ], #Neutral
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 0,0,1,0, 1,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 0,0,1,0, 0,0,1,0, 1,0,1,0, ],
    [1,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0, ],
    [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0, ], #HappyLevel8
]

DRUM_ACCENT_PATTERNS = [
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel8
    [0.03, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel7
    [0.09, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel6
    [0.19, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel5
    [0.34, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel4
    [0.56, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel3
    [0.90, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel2
    [1.39, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel1
    [2.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # Neutral
    [1.39, 0.00, 0.00, 0.00, 0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.50, 0.00, 0.00, 0.00],  # HappyLevel1
    [0.90, 0.00, 0.00, 0.00, 0.75, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.75, 0.00, 0.00, 0.00],  # HappyLevel2
    [0.56, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00],  # HappyLevel3
    [0.34, 0.00, 0.00, 0.00, 1.25, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.25, 0.00, 0.00, 0.00],  # HappyLevel4
    [0.19, 0.00, 0.00, 0.00, 1.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.50, 0.00, 0.00, 0.00],  # HappyLevel5
    [0.09, 0.00, 0.00, 0.00, 1.75, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.75, 0.00, 0.00, 0.00],  # HappyLevel6
    [0.03, 0.00, 0.00, 0.00, 1.90, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.90, 0.00, 0.00, 0.00],  # HappyLevel7
    [0.00, 0.00, 0.00, 0.00, 2.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 2.00, 0.00, 0.00, 0.00],  # HappyLevel8
]

BASS_PATTERNS = [
    ['1','c','c','c',  'c','c','c','c', '1','c','c','c', 'c','c','c','c', ], #SadLevel8
    ['1','c','c','c', 'c','c','c','c', 'b3','c','c','c', 'c','c','c','c', ],
    ['1','c','c','c', '1','c','c','c', 'b3','c','c','c', 'b3','c','c','c', ],
    ['1','c','c','c', '1','c','c','c', '5','c','c','c', 'b3','c','c','c', ],
    ['1','c','c',0, '1','c','c',0, '5','c','c',0, 'b3','c','c',0, ],
    ['1','c','c',0, 'b3','c','c',0, '5','c','c',0, 'b3','c','c',0, ],
    ['1','c','1','c', 'b3','c','c',0, '5','c',0,'5', 'b3',0,0,0, ],
    ['1','c','1',0, 'b3','c','b3',0, '5','c','5',0, 'b3','c','b3',0, ],
    ['1','c','1',0, '3','c','3',0, '5','c','5',0, '3','c','3',0, ], #Neutral
    ['1','c','-7',0, '-7',0,'1','1', 'c',0,'2',0, '-7',0,'-7',0, ],
    ['1','c','-b7',0, '1','c','2',0, '3','c','3',0, '1','c','1',0, ],
    ['1','c','-b7',0, '2','c','3',0, '5','c','4',0, '2','c','2',0, ],
    ['1','c','-7',0, '-6',0,'-7','1', 'c',0,'1',0, '-6',0,'-6',0, ],
    ['1','c','-6',0, '-5',0,'-6','1', 'c','1','-6',0, '-5',0,'-6',0, ],
    ['1',0,'-6',0, '-5',0,'-6','1', 0,0,'-6',0, '-5',0,'-6',0, ],
    ['1','c',0,0, '-5',0,'-6',0, '1',0,0,'-4', '-5',0,'-5',0, ],
    ['1',0,0,0,  '-5',0,0,0, '1',0,0,'-4', '-#4',0,'-5',0, ], #HappyLevel8
]

## DELAY PATTERN SETTINGS
# Base delay amounts in milliseconds for sad patterns (SadLevel8 → SadLevel1)
DELAY_BASE_SAD_MS = [100, 79, 63, 50, 40, 32, 25, 0]
# Happy delays are calculated as: sad_delay * DELAY_HAPPY_FACTOR
DELAY_HAPPY_FACTOR = 0.25

# ============================================================================
# END CONFIGURATION SECTION
# ============================================================================

# ============================================================================
# RUNTIME GLOBALS – initialised from CONFIG  (DO NOT edit values here)
# ============================================================================

# Thread-safety locks
bpm_lock = threading.Lock()
slider_val_lock = threading.Lock()

# Audio / musical bases
sample_rate: int = SAMPLE_RATE
tonic: int       = TONIC_MIDI_NOTE

# Mutable runtime state ------------------------------------------------------
current_bpm: float        = DEFAULT_BPM        # updated continuously
slider_val:  float        = 0.5                # GUI slider position (0–1)
current_group_index: int  = 8                  # 8 = “Neutral” starting pattern
steps_per_measure: int    = STEPS_PER_MEASURE

# Tempo-ramp bookkeeping
start_bpm:       float | None = DEFAULT_BPM
target_bpm:      float | None = DEFAULT_BPM
ramp_start_time: float | None = None
ramp_duration:   float | None = None

# Delay patterns
# ---------------
delay_patterns_ms = []

# 1) Sad delays (levels 8→1)
for d in DELAY_BASE_SAD_MS:
    delay_patterns_ms.append([0]*4 + [d]*12)

# 2) Neutral (level 0)
delay_patterns_ms.append([0]*16)

# 3) Happy delays (levels 1→8)
happy = [int(DELAY_HAPPY_FACTOR * d) for d in reversed(DELAY_BASE_SAD_MS)]
for d in happy:
    pattern = [0]*16
    for i in [1,3,5,7,9,11,13,15]: #Only on 2 and 4 of each measure
        pattern[i] = d
    delay_patterns_ms.append(pattern)

# Slider Level Labels
labels = [
    "SadLevel8", "SadLevel7", "SadLevel6", "SadLevel5",
    "SadLevel4", "SadLevel3", "SadLevel2", "SadLevel1",
    "Neutral",
    "HappyLevel1", "HappyLevel2", "HappyLevel3",
    "HappyLevel4", "HappyLevel5", "HappyLevel6",
    "HappyLevel7", "HappyLevel8"
]

# ============================================================================
# AUDIO SYSTEM INITIALIZATION
# ============================================================================
# Initialize pygame's audio mixer **before** any pygame.mixer.Sound() calls so
# that all drum samples can be loaded and played back correctly.
pygame.mixer.init()

# ============================================================================
# SLIDER CONVERSION UTILITIES
# ============================================================================

def slider_to_bpm(val: float) -> float:
    """
    Convert GUI slider position (0‒1, logarithmic scale) to a BPM value.

    Used continuously while the application is running to translate the
    user-controlled slider value into an instantaneous BPM target.
    """
    log_min = math.log(MIN_BPM)
    log_max = math.log(MAX_BPM)
    bpm_log = log_min + val * (log_max - log_min)
    return math.exp(bpm_log)

def bpm_to_slider(bpm_val: float) -> float:
    """
    Convert a BPM value back to slider position (0‒1) using the same
    logarithmic mapping as :func:`slider_to_bpm`.

    Currently called once on start-up so the GUI slider initially reflects
    ``DEFAULT_BPM`` rather than sitting at an arbitrary position.
    """
    log_min = math.log(MIN_BPM)
    log_max = math.log(MAX_BPM)
    return (math.log(bpm_val) - log_min) / (log_max - log_min)

# ============================================================================
# MASTER AUDIO FUNCTIONS
# ============================================================================

# Convert slider position (0-1) to global volume adjustment in dB (±5dB range)
def slider_to_global_gain_db(slider):
    # Convert slider position to global volume adjustment (±5dB range)
    if slider <= 0.5:
        t = slider / 0.5
        gain_db = -GLOBAL_GAIN_DB_RANGE + GLOBAL_GAIN_DB_RANGE * (math.log10(1 + 9 * t))
    else:
        t = (slider - 0.5) / 0.5
        gain_db = GLOBAL_GAIN_DB_RANGE * (math.log10(1 + 9 * t))
    return gain_db

# Convert slider position (0-1) to high-shelf EQ boost/cut in dB (±2dB range)
def slider_to_global_highshelf_db(slider):
    # Convert slider position to high-shelf EQ boost/cut (±2dB range)
    if slider <= 0.5:
        t = slider / 0.5
        gain_db = -HIGHSHELF_DB_RANGE + HIGHSHELF_DB_RANGE * (math.log10(1 + 9 * t))
    else:
        t = (slider - 0.5) / 0.5
        gain_db = HIGHSHELF_DB_RANGE * (math.log10(1 + 9 * t))
    return gain_db

# Convert slider position (0-1) to low-mid EQ boost/cut in dB (±1dB range)
def slider_to_lowmid_db(slider):
    # Convert slider position to low-mid EQ boost/cut (±1dB range)
    if slider <= 0.5:
        t = slider / 0.5
        gain_db = LOWMID_DB_RANGE - (LOWMID_DB_RANGE * math.log10(1 + 9 * t))
    else:
        t = (slider - 0.5) / 0.5
        gain_db = -(LOWMID_DB_RANGE * math.log10(1 + 9 * t))
    return gain_db

# Generate biquad coefficients for 2nd-order high-shelf filter (12dB/oct slope)
def highshelf_biquad_coeffs(freq_hz: float, gain_db: float, fs: int):
    """
    Return biquad coefficients for a 2-pole high-shelf filter.
    Slope is fixed (Q≈0.707) giving ~12 dB/oct response.
    """
    if abs(gain_db) < 1e-3:        # no boost/cut
        return [1.0, 0.0, 0.0], [1.0, 0.0, 0.0]

    A   = 10 ** (gain_db / 40)     # √(linear gain)
    w0  = 2 * np.pi * freq_hz / fs
    cos = np.cos(w0)
    sin = np.sin(w0)
    Q   = 0.707  # gentle slope
    alpha = sin / (2 * Q) * np.sqrt((A + 1/A) * (1/Q - 1) + 2)

    b0 =    A*((A+1) + (A-1)*cos + 2*np.sqrt(A)*alpha)
    b1 = -2*A*((A-1) + (A+1)*cos)
    b2 =    A*((A+1) + (A-1)*cos - 2*np.sqrt(A)*alpha)
    a0 =        (A+1) - (A-1)*cos + 2*np.sqrt(A)*alpha
    a1 =  2*((A-1) - (A+1)*cos)
    a2 =        (A+1) - (A-1)*cos - 2*np.sqrt(A)*alpha

    return [b0/a0, b1/a0, b2/a0], [1.0, a1/a0, a2/a0]

# Generate biquad coefficients for peaking (bell) EQ filter

def peaking_biquad_coeffs(freq_hz: float, gain_db: float, Q: float, fs: int):
    """
    Return biquad coefficients for a peaking (bell) EQ filter.
    """
    if abs(gain_db) < 1e-3:
        return [1.0, 0.0, 0.0], [1.0, 0.0, 0.0]

    A   = 10 ** (gain_db / 40)
    w0  = 2 * np.pi * freq_hz / fs
    cos = np.cos(w0)
    sin = np.sin(w0)
    alpha = sin / (2 * Q)

    b0 = 1 + alpha*A
    b1 = -2*cos
    b2 = 1 - alpha*A
    a0 = 1 + alpha/A
    a1 = -2*cos
    a2 = 1 - alpha/A

    return [b0/a0, b1/a0, b2/a0], [1.0, a1/a0, a2/a0]

# Apply biquad filter to audio data using scipy.signal.lfilter

def apply_biquad_filter(data: np.ndarray, b: list, a: list):
    """Light wrapper around scipy.signal.lfilter for biquad processing."""
    from scipy.signal import lfilter
    return lfilter(b, a, data)

# Apply real-time global EQ to drum samples (pygame Sound objects)

def apply_global_eq_to_sound(sound: pygame.mixer.Sound, slider: float):
    """
    Apply *dynamic* global EQ (high-shelf & low-mid peaking) to a drum sample
    based on current slider position, returning a *new* pygame Sound.
    """
    raw = pygame.sndarray.array(sound).astype(np.float32)

    highshelf_db = slider_to_global_highshelf_db(slider)
    lowmid_db    = slider_to_lowmid_db(slider)

    # Early exit if no EQ change
    if abs(highshelf_db) < 0.1 and abs(lowmid_db) < 0.1:
        return sound

    def process_channel(channel_data: np.ndarray) -> np.ndarray:
        if abs(highshelf_db) >= 0.1:
            b, a = highshelf_biquad_coeffs(HIGHSHELF_FREQ_HZ,
                                           highshelf_db, sample_rate)
            channel_data = apply_biquad_filter(channel_data, b, a)
        if abs(lowmid_db) >= 0.1:
            b, a = peaking_biquad_coeffs(LOWMID_CENTER_FREQ_HZ,
                                         lowmid_db, LOWMID_Q_FACTOR,
                                         sample_rate)
            channel_data = apply_biquad_filter(channel_data, b, a)
        return channel_data

    if raw.ndim == 2:  # stereo
        for ch in range(raw.shape[1]):
            raw[:, ch] = process_channel(raw[:, ch])
    else:              # mono
        raw = process_channel(raw)

    # Clip & convert back to int16
    np.clip(raw, -32768, 32767, out=raw)
    return pygame.sndarray.make_sound(raw.astype(np.int16))

# Apply real-time global EQ to bass synth output (numpy arrays)
# NumPy version of Global EQ – for Synth output
def apply_global_eq_to_array(audio_array: np.ndarray, slider: float) -> np.ndarray:
    """
    Apply dynamic global EQ (high-shelf & low-mid peaking) to a NumPy audio
    array (mono or stereo).  Used by the bass synth so that it shares the same
    global EQ behaviour as the drum samples.
    """
    highshelf_db = slider_to_global_highshelf_db(slider)
    lowmid_db    = slider_to_lowmid_db(slider)

    # Early-exit if changes are insignificant
    if abs(highshelf_db) < 0.1 and abs(lowmid_db) < 0.1:
        return audio_array

    def process_channel(buf: np.ndarray) -> np.ndarray:
        if abs(highshelf_db) >= 0.1:
            b, a = highshelf_biquad_coeffs(HIGHSHELF_FREQ_HZ,
                                           highshelf_db, sample_rate)
            buf = apply_biquad_filter(buf, b, a)
        if abs(lowmid_db) >= 0.1:
            b, a = peaking_biquad_coeffs(LOWMID_CENTER_FREQ_HZ,
                                         lowmid_db, LOWMID_Q_FACTOR,
                                         sample_rate)
            buf = apply_biquad_filter(buf, b, a)
        return buf

    # Work on a copy to avoid mutating the caller's buffer
    out = audio_array.copy()

    if out.ndim == 2:            # stereo
        for ch in range(out.shape[1]):
            out[:, ch] = process_channel(out[:, ch])
    else:                        # mono
        out = process_channel(out)

    return out


# ============================================================================
# MIDI AND MUSICAL UTILITIES
# ============================================================================

# Interval name → semitone offset mapping  (ACTIVELY USED by bass pattern logic)
interval_to_semitone = {
    # Below-tonic (negative) degrees
    '-1': -12, '-b2': -11, '-2': -10, '-b3': -9,  '-3': -8,  '-4': -7,
    '-#4': -6, '-b5': -6,  '-5': -5,  '-b6': -4,  '-6': -3,  '-b7': -2,
    '-7': -1,
    # Tonic and above
    '1': 0, 'b2': 1, '2': 2, 'b3': 3, '3': 4, '4': 5, '#4': 6, 'b5': 6,
    '5': 7, 'b6': 8, '6': 9, 'b7': 10, '7': 11, '8': 12
}

def get_degree_name(midi_note, tonic_note=tonic):
    # Convert MIDI note to scale-degree name (mainly for debugging/analysis)
    diff = midi_note - tonic_note
    wrapped = diff % 12
    if diff >= 0:
        return scale_degree_map.get(wrapped, '?')
    else:
        # For below-tonic notes look up the negative equivalent label
        return scale_degree_map.get(wrapped - 12, '?')

def freq_from_midi(midi_note):
    # Convert MIDI note number to Hz (used by Synth.render_note)
    return 440.0 * 2 ** ((midi_note - 69) / 12)

# ============================================================================
# AUDIO LOADING
# ============================================================================

def fade_in_kick_sample(sound, sample_rate):
    """
    Apply a short linear fade-in to *kick drum* samples to eliminate pops.
    Fade length is controlled by the configurable constant ``KICK_FADE_IN_MS``.
    """
    fade_samples = int(sample_rate * KICK_FADE_IN_MS / 1000)

    # Extract raw audio as float32 for processing
    raw = pygame.sndarray.array(sound).astype(np.float32)

    # Build fade envelope (mono or stereo)
    if raw.ndim == 2:
        fade_env = np.linspace(0, 1, fade_samples, dtype=np.float32)[:, None]
    else:
        fade_env = np.linspace(0, 1, fade_samples, dtype=np.float32)

    raw[:fade_samples] *= fade_env

    # Clip to int16 range and convert back
    np.clip(raw, -32768, 32767, out=raw)
    processed_int16 = raw.astype(np.int16)
    return pygame.sndarray.make_sound(processed_int16)

# ===Load Kick Samples ===
kick_cache = {}
def load_kick_samples():
    prefix = "ProgrammableLoop2/ProgrammableLoop2"
    fix = prefix + "Kick"
    suffix = ".wav"
    for label in labels:
        path = fix + label + suffix
        try:
            sound = pygame.mixer.Sound(path)
            # Apply short fade-in to kick samples only
            sound = fade_in_kick_sample(sound, sample_rate)
            kick_cache[label] = sound
        except Exception as e:
            print(f"Error loading {path}: {e}")
load_kick_samples()

# === Load Snare Samples ===
snare_cache = {}
def load_snare_samples():
    prefix = "ProgrammableLoop2/ProgrammableLoop2Snare"
    suffix = ".wav"
    for label in labels:
        path = prefix + label + suffix
        try:
            snare_cache[label] = pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Error loading {path}: {e}")
load_snare_samples()

# === Load Cymbal Samples ===
cymbal_cache = {}
def load_cymbal_samples():
    prefix = "ProgrammableLoop2/ProgrammableLoop2Cymbal"
    suffix = ".wav"
    for label in labels:
        path = prefix + label + suffix
        try:
            cymbal_cache[label] = pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Error loading {path}: {e}")
load_cymbal_samples()

# ============================================================================
# SAMPLE-BASED PLAY FUNCTIONS
# ============================================================================


def play_kick_sample_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms / 1000)
        sound = kick_cache.get(label)
        if sound:
            with slider_val_lock:
                slider = slider_val
            # --- Real-time GLOBAL EQ ---------------------------------------
            sound = apply_global_eq_to_sound(sound, slider)

            # --- Pure volume / gain (no pseudo EQ) -------------------------
            global_gain_db = slider_to_global_gain_db(slider)
            kick_boost_db = KICK_BOOST_DB        # extra punch for kicks
            total_gain_db = gain_db + global_gain_db + kick_boost_db
            volume = 10 ** (total_gain_db / 20)
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()

def play_snare_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms/1000)
        sound = snare_cache.get(label)
        if sound:
            with slider_val_lock:
                slider = slider_val
            # Apply real EQ filtering
            sound = apply_global_eq_to_sound(sound, slider)

            # Volume only (EQ already applied)
            total_gain_db = gain_db + slider_to_global_gain_db(slider)
            volume = 10 ** (total_gain_db/20)
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()

def play_cymbal_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms/1000)
        sound = cymbal_cache.get(label)
        if sound:
            with slider_val_lock:
                slider = slider_val
            # Apply real EQ filtering
            sound = apply_global_eq_to_sound(sound, slider)

            # Volume only (EQ already applied)
            total_gain_db = gain_db + slider_to_global_gain_db(slider)
            volume = 10 ** (total_gain_db/20)
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()

# ============================================================================
# UNUSED (kept for potential future use)
# ============================================================================

# <UNUSED?> note_duration not referenced elsewhere; kept for future use
#note_duration: float = 60 / current_bpm   # noqa: F841

#bass_scales = {
#    "scale1": ["1", "b2", "b3", "4", "5", "b6", "b7", "8"],
#    "scale2": ["1", "2", "b3", "4", "5", "b6", "b7", "8"],
#    "scale3": ["1", "2", "b3", "4", "5", "6", "b7", "8"],
#    "scale4": ["1", "2", "3", "4", "5", "6", "b7", "8"],
#    "scale5": ["1", "2", "3", "4", "5", "6", "7", "8"],
#    "scale6": ["1", "2", "3", "#4", "5", "6", "7", "8"]
#}

#def midi_notes_from_degrees(degrees, tonic_note=tonic):
#    """Convert scale-degree strings to MIDI note numbers. Currently UNUSED."""
#    midi_notes = []
#    for deg in degrees:
#        semitone = interval_to_semitone.get(deg)
#        if semitone is None:
#            raise ValueError(f"Unknown scale degree: {deg}")
#        midi_notes.append(tonic_note + semitone)
#    return midi_notes

# UNUSED: pre-baked library of MIDI-note lists for each bass scale
#midi_pattern_library = {
#    name: midi_notes_from_degrees(degrees, tonic_note=tonic)
#    for name, degrees in bass_scales.items()
#}

        # ============================================================================
        #                           S~E~Q~U~E~N~C~E~R                                # 
        # ============================================================================

def sequencer(stop_event):
    global current_group_index, current_bpm, start_bpm, target_bpm, ramp_start_time, ramp_duration

    global_delay = 0.03
    next_trigger = time.time() + global_delay
    step = 0
    note_index = 0  # to cycle through midi_note_pattern
    kick_time = 0
    drum_delay = 0.04
    last_note_end_time = 0  # global or at the start of your sequencer function or script

    while not stop_event.is_set():
        with slider_val_lock:
            slider = slider_val

        goal_group_index = int(round(slider * (len(labels) - 1)))

        with bpm_lock:
            new_target_bpm = slider_to_bpm(slider)
            if new_target_bpm != target_bpm:
                start_bpm = current_bpm
                target_bpm = new_target_bpm
                ramp_start_time = time.time()
                ramp_duration = (60 / start_bpm) * 4

            if ramp_start_time and ramp_duration:
                elapsed = time.time() - ramp_start_time
                progress = min(elapsed / ramp_duration, 1.0)
                current_bpm = start_bpm + (target_bpm - start_bpm) * progress
                if progress >= 1.0:
                    current_bpm = target_bpm
                    start_bpm = target_bpm
                    ramp_start_time = None
                    ramp_duration = None

            bpm_to_use = current_bpm

        seconds_per_beat = 60 / bpm_to_use
        seconds_per_16th = seconds_per_beat / 4

        now = time.time()
        
        if now >= next_trigger:
            # Switch pattern only at the start of a 16-step cycle
            if goal_group_index != current_group_index and step == 0:
                current_group_index = goal_group_index

            if KICK_PATTERNS[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step] + drum_delay * 1000
                gain_db = DRUM_ACCENT_PATTERNS[current_group_index][step]
                kick_time = time.time()
                play_kick_sample_with_delay_and_gain(labels[current_group_index], delay_ms, gain_db)

            if SNARE_PATTERNS[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step] + drum_delay * 1000
                gain_db = DRUM_ACCENT_PATTERNS[current_group_index][step]
                play_snare_with_delay_and_gain(labels[current_group_index], delay_ms, gain_db)

            if CYMBAL_PATTERNS[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step] + drum_delay * 1000
                gain_db   = DRUM_ACCENT_PATTERNS[current_group_index][step]
                play_cymbal_with_delay_and_gain(labels[current_group_index],
                                                delay_ms, gain_db)

            selected_bass_pattern = BASS_PATTERNS[current_group_index]


            
            
            def get_extended_duration(pattern, start_index, base_duration):
                length = len(pattern)
                total_steps = 1  # count current note
                i = (start_index + 1) % length
                while pattern[i] == 'c':
                    total_steps += 1
                    i = (i + 1) % length
                    if i == start_index:
                        break  # avoid infinite loop if pattern all 'c's
                return base_duration * total_steps

            degree = selected_bass_pattern[note_index % len(selected_bass_pattern)]
            base_duration = seconds_per_16th * 0.875 * 2  # whole beat
            now = time.time()

            if degree == 0 or degree == 'c':
                # Don't schedule; just advance
                note = None
            else:
                degree_str = degree if isinstance(degree, str) else str(degree)
                note = tonic + interval_to_semitone[degree_str]
                duration = get_extended_duration(selected_bass_pattern, note_index % len(selected_bass_pattern), base_duration)
                
                bass_synth.schedule_note(now, note, duration)

            note_index += 1





            
            step = (step + 1) % steps_per_measure
            next_trigger += seconds_per_16th
        else:
            time_to_sleep = next_trigger - now
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

        

def on_slider_change(val):
    global slider_val
    with slider_val_lock:
        slider_val = float(val)

import threading
import time
import numpy as np
import pyaudio
import wave

def lowpass_filter_resonant(wave, cutoff_freqs, resonance, sample_rate, drive, low, band):
    """
    Stable state-variable low-pass filter with resonance.
    Fixes previous crackle by:
        1. Clamping cutoff to < Nyquist to avoid aliasing
        2. Limiting resonance (feedback) to < 1.0 for stability
        3. Applying drive once (vectorised) – avoids per-sample discontinuity
        4. Clamping internal state (low / band) to prevent runaway build-up
    """
    # Pre-compute constants
    cut = np.clip(cutoff_freqs, 0.0, sample_rate * 0.45)
    f      = 2.0 * np.sin(np.pi * cut / sample_rate)
    q      = np.clip(resonance, 0.0, 0.99)          # feedback <1 ⇒ stable
    drive  = np.clip(drive, 0.1, 2.0)

    # Apply drive once – cheaper & smoother than per-sample
    driven_wave = np.tanh(wave * drive)

    out = np.zeros_like(driven_wave)

    for i in range(len(driven_wave)):
        sample = driven_wave[i]

        # State-variable equations
        notch = sample - q * band
        low  += f[i] * band
        high  = notch - low
        band += f[i] * high

        # Clamp states to avoid numerical runaway
        low  = np.clip(low,  -2.0, 2.0)
        band = np.clip(band, -2.0, 2.0)

        out[i] = low

    return out, low, band



def comb_filter_modulated(wave, sample_rate, base_delay=1/47.1, feedback=0.3, drive=1.1538, env_percent=1.0):
    samples = len(wave)
    out = np.copy(wave) * (1 + drive)
    delay_samples = int(sample_rate * base_delay)
    for i in range(delay_samples, samples):
        out[i] += feedback * out[i - delay_samples]
    return out

def global_resonance_filter(wave, sample_rate, freq=85.61, resonance=13.65):
    q = resonance / 10  
    w0 = 2 * np.pi * freq / sample_rate
    alpha = np.sin(w0) / (2 * q)

    b0 = alpha
    b1 = 0
    b2 = -alpha
    a0 = 1 + alpha
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha

    b = np.array([b0, b1, b2]) / a0
    a = np.array([1, a1 / a0, a2 / a0])

    return np.convolve(wave, b, mode='same') - np.convolve(wave, a[1:], mode='same')

from scipy.signal import butter, lfilter

def butter_lowpass(cutoff, fs, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=4):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def slider_to_osc1_volume(slider):
    # Interpolate dB from 0 dB at slider=0 to -40 dB at slider=1
    # So at slider=0.5, db = -20 dB (halfway)
    db = -40 * (slider) 
    return 10 ** (db / 20)


# Dummy freq_from_midi, slider_val, slider_val_lock, base_gain_db, slider_to_global_gain_db, slider_to_global_highshelf_db, slider_to_lowmid_db
# These must be defined elsewhere in your full code as per original

def tube_drive(signal, gain=3.0, bias=0.2, blend=0.5):
    # Apply gain and bias
    driven = gain * signal + bias
    # Apply tanh for soft saturation
    saturated = np.tanh(driven)
    # Remove DC bias post-saturation
    saturated -= np.mean(saturated)
    # Blend dry and wet
    return (1 - blend) * signal + blend * saturated

def bitcrusher(signal, bit_depth=8, downsample_factor=4, mix=1.0):
    max_int = 2 ** bit_depth - 1
    crushed = np.floor((signal + 1) / 2 * max_int) / max_int * 2 - 1
    crushed = crushed[::downsample_factor]
    crushed = np.repeat(crushed, downsample_factor)
    crushed = crushed[:len(signal)]
    return (1 - mix) * signal + mix * crushed

class Synth:
    def __init__(self, sample_rate, buffer_size=1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=sample_rate,
                                  output=True,
                                  frames_per_buffer=buffer_size)
        self.lock = threading.Lock()
        self.active_notes = []  
        self.note_queue = []    
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        self.osc1_volume = 1.0  
        self.master_volume = 1.0  # full volume by default
        self.prev_resonance = None
        self.lowpass_low = 0.0
        self.lowpass_band = 0.0




        import soundfile as sf

        self.sample_wave, self.sample_rate_wave = sf.read('ProgrammableLoop2/ProgrammableLoop2BassSynthOscillatorSample.wav', dtype='float32')

        # Convert stereo to mono if needed
        if self.sample_wave.ndim > 1:
            self.sample_wave = np.mean(self.sample_wave, axis=1)

        # Optional trim
        trim_ms = 10
        trim_samples = int(self.sample_rate_wave * trim_ms / 1000)
        self.sample_wave = self.sample_wave[trim_samples:]

        
    def set_master_volume(self, volume):
        # Clamp volume between 0.0 and 1.0
        self.master_volume = max(0.0, min(volume, 1.0))

    def lfo(self, rate, depth_cents, carrier_freq, duration):
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        depth = carrier_freq * (2 ** (depth_cents / 1200) - 1)
        return np.sin(2 * np.pi * rate * t) * depth

    def fm_wave(self, carrier_freq, mod_freq, mod_index, duration, lfo_wave=None):
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)

        if lfo_wave is None:
            modulated_carrier_freq = carrier_freq
        else:
            modulated_carrier_freq = carrier_freq + lfo_wave

        modulator = np.sin(2 * np.pi * mod_freq * t)
        wave = np.sin(2 * np.pi * modulated_carrier_freq * t + mod_index * modulator).astype(np.float32)
        return wave


    def adsr_envelope(self, length, slider, decay=0.385, sustain_level=0.17, release=1.13):
        min_attack = 0.018  # 18 ms
        max_attack = 0.155  # 155 ms
        # Logarithmic interpolation
        attack = max_attack * (min_attack / max_attack) ** slider

        attack_samples = max(1, int(self.sample_rate * attack))
        min_decay = 0.385     # 385 ms
        max_decay = 60.0      # 60000 ms = 60 s
        decay = min_decay * (max_decay / min_decay) ** slider  # logarithmic interpolation
        decay_samples = max(1, int(self.sample_rate * decay))

        min_release = 0.1   # 100 ms
        max_release = 1.13  # 1130 ms
        release = max_release * (min_release / max_release) ** slider  # logarithmic interpolation
        release_samples = max(1, int(self.sample_rate * release))

        sustain_samples = max(0, length - attack_samples - decay_samples - release_samples)

        total_samples = attack_samples + decay_samples + sustain_samples + release_samples
        diff = length - total_samples
        if diff > 0:
            sustain_samples += diff
        elif diff < 0:
            sustain_samples = max(0, sustain_samples + diff)

        attack_env = np.linspace(0, 1, attack_samples, endpoint=False)
        min_db = -15.65
        max_db = 0.0
        sustain_level_db = min_db + (max_db - min_db) * slider  # linear in dB space
        sustain_level = 10 ** (sustain_level_db / 20)


        decay_env = np.linspace(1, sustain_level, decay_samples, endpoint=False)
        sustain_env = np.full(sustain_samples, sustain_level)

        release_env = np.linspace(sustain_level, 0, release_samples, endpoint=True)

        envelope = np.concatenate([attack_env, decay_env, sustain_env, release_env])

        if len(envelope) < length:
            envelope = np.append(envelope, 0)
        elif len(envelope) > length:
            envelope = envelope[:length]

        assert len(envelope) == length, f"Envelope length {len(envelope)} != expected {length}"
        return envelope, attack

    def filter_envelope(self, length, peak_freq=22.53, sustain_freq=20, slider=0.0):
        # Logarithmic attack time: 1.074s → ~0s
        min_attack = 1e-5
        max_attack = 1.074
        log_min_attack = np.log(min_attack)
        log_max_attack = np.log(max_attack)
        attack = np.exp(log_max_attack * (1 - slider) + log_min_attack * slider)

        # Logarithmic decay time: 0.246s → 1.816s
        min_decay = 0.246
        max_decay = 1.816
        log_min_decay = np.log(min_decay)
        log_max_decay = np.log(max_decay)
        decay = np.exp(log_min_decay * (1 - slider) + log_max_decay * slider)

        # Logarithmic release time: 0.31s → 12.46s
        min_release = 0.31
        max_release = 12.46
        log_min_release = np.log(min_release)
        log_max_release = np.log(max_release)
        release = np.exp(log_min_release * (1 - slider) + log_max_release * slider)

        attack_samples = int(self.sample_rate * attack)
        decay_samples = int(self.sample_rate * decay)
        release_samples = int(self.sample_rate * release)
        sustain_samples = max(0, length - attack_samples - decay_samples - release_samples)

        mod_range = 0.1265 * sustain_freq
        peak_freq = sustain_freq + mod_range
        attack_env = np.linspace(sustain_freq, peak_freq, attack_samples, endpoint=False)
        decay_env = np.linspace(peak_freq, sustain_freq, decay_samples, endpoint=False)
        sustain_env = np.full(sustain_samples, sustain_freq)
        release_env = np.linspace(sustain_freq, 50, release_samples, endpoint=True)

        env = np.concatenate([attack_env, decay_env, sustain_env, release_env])
        if len(env) < length:
            env = np.pad(env, (0, length - len(env)), 'edge')
        return env




    def sample_oscillator(self, duration, midi_note):
        base_midi_note = 36  # root of the original sample
        semitone_diff = midi_note - base_midi_note
        playback_rate = 2 ** (semitone_diff / 12)

        if self.sample_rate_wave != self.sample_rate:
            factor = len(self.sample_wave) * self.sample_rate / self.sample_rate_wave
            resampled = np.interp(
                np.linspace(0, len(self.sample_wave), int(factor), endpoint=False),
                np.arange(len(self.sample_wave)),
                self.sample_wave
            )
        else:
            resampled = self.sample_wave

        # Apply pitch shifting by changing the playback rate
        new_len = int(len(resampled) / playback_rate)
        resampled = np.interp(
            np.linspace(0, len(resampled), new_len, endpoint=False),
            np.arange(len(resampled)),
            resampled
        )

        # Latency compensation
        latency_ms = 0.7  # try tuning this value by ear
        latency_samples = int(self.sample_rate * latency_ms / 1000)

        if len(resampled) > latency_samples:
            resampled = resampled[latency_samples:]
        else:
            resampled = np.zeros_like(resampled)

        # Create output buffer for the full duration
        total_samples = int(self.sample_rate * duration)
        output = np.zeros(total_samples, dtype=np.float32)
        
        # If the sample is shorter than needed, use crossfading to loop it
        if len(resampled) < total_samples:
            # Define crossfade window (in samples)
            crossfade_samples = min(100, len(resampled) // 4)  # 100 samples or 1/4 of sample length
            
            # Create crossfade windows
            fade_in = np.linspace(0, 1, crossfade_samples)
            fade_out = np.linspace(1, 0, crossfade_samples)
            
            # Fill output buffer with crossfaded loops
            position = 0
            while position < total_samples:
                # Calculate how much of the sample we can copy
                samples_to_copy = min(len(resampled), total_samples - position)
                
                if position + samples_to_copy >= total_samples:
                    # Last segment - just copy what's needed
                    output[position:position+samples_to_copy] = resampled[:samples_to_copy]
                else:
                    # Not the last segment - apply crossfade
                    if position + len(resampled) <= total_samples:
                        # Full sample fits
                        output[position:position+len(resampled)] += resampled
                        
                        # Apply crossfade with next loop if there's room
                        next_position = position + len(resampled) - crossfade_samples
                        if next_position + crossfade_samples <= total_samples:
                            # Apply fade out to current loop end
                            output[next_position:next_position+crossfade_samples] *= fade_out
                            
                            # Apply fade in to next loop start (if it fits)
                            if next_position + crossfade_samples + len(resampled) <= total_samples:
                                # Apply fade in to beginning of next loop
                                next_loop_start = next_position + crossfade_samples
                                output[next_loop_start:next_loop_start+crossfade_samples] += resampled[:crossfade_samples] * fade_in
                    else:
                        # Only part of the sample fits
                        samples_remaining = total_samples - position
                        output[position:] += resampled[:samples_remaining]
                
                position += len(resampled) - crossfade_samples  # Overlap by crossfade amount
        else:
            # Sample is longer than needed, just take what we need
            output = resampled[:total_samples]

        return output

    def schedule_note(self, start_time, midi_note, duration):
        with self.lock:
            self.note_queue.append((start_time, midi_note, duration))

    def render_note(self, midi_note, duration):
        freq = freq_from_midi(midi_note)
        total_samples = int(self.sample_rate * duration)
        if total_samples <= 0:
            return np.array([], dtype=np.float32)

       # Existing FM sine oscillator wave
        mod_freq = freq * 2
        with slider_val_lock:
            osc1_slider = slider_val
        mod_index = 0.0868 * (1 - osc1_slider)  # Linear: 0.0868 at 0 slider, 0 at 1 slider

        # --- ORIGINAL FM SYNTHESIS (restored) -----------------------------
        fm_wave = self.fm_wave(freq, mod_freq, mod_index, duration)
        

        lfo_rate = 3.22
        min_depth = 0.001
        max_depth = 3.81
        with slider_val_lock:
            s = slider_val
        lfo_depth_cents = max_depth * (min_depth / max_depth) ** s
        lfo_wave = self.lfo(lfo_rate, lfo_depth_cents, freq, duration)



        # New sample oscillator wave
        sample_wave = self.sample_oscillator(duration, midi_note)
        with slider_val_lock:
            slider = slider_val
        
        smoothing = 0.5  # adjust for transition speed

        target_osc1_vol = slider_to_osc1_volume(osc1_slider)
        target_sample_vol_db = -40 * ((1 - slider) ** 4)

        target_sample_vol = 10 ** (target_sample_vol_db / 20)

        if not hasattr(self, 'prev_osc1_volume'):
            self.prev_osc1_volume = target_osc1_vol
        if not hasattr(self, 'prev_sample_volume'):
            self.prev_sample_volume = target_sample_vol

        self.prev_osc1_volume = (1 - smoothing) * self.prev_osc1_volume + smoothing * target_osc1_vol
        self.prev_sample_volume = (1 - smoothing) * self.prev_sample_volume + smoothing * target_sample_vol

        fm_wave *= self.prev_osc1_volume
        sample_wave *= self.prev_sample_volume

        # Mix FM and sample oscillators
        combined_wave = fm_wave + sample_wave


        # ---------------- ADSR envelope (restored) ------------------------
        env, attack = self.adsr_envelope(total_samples, slider)
        combined_wave *= env
        

        with slider_val_lock:
            slider = slider_val

        # Store previous slider value and check for significant change
        slider_threshold = 0.001
        if not hasattr(self, 'prev_slider_cutoff'):
            self.prev_slider_cutoff = slider

        slider_changed = abs(slider - self.prev_slider_cutoff) > slider_threshold
        self.prev_slider_cutoff = slider  # update stored slider

        # Compute filter envelope
        filter_env = self.filter_envelope(total_samples, peak_freq=22.53, sustain_freq=20)
        filter_env = filter_env * (1 - slider) + np.mean(filter_env) * slider

        # Compute target cutoff
        log_min = np.log(85.61)
        log_max = np.log(246)
        target_global_cutoff = np.exp(log_min * (1 - slider) + log_max * slider)

        # Smooth cutoff only if slider changed
        if not hasattr(self, 'prev_global_cutoff'):
            self.prev_global_cutoff = target_global_cutoff
        elif slider_changed:
            smoothing_factor = 0.005
            self.prev_global_cutoff = (1 - smoothing_factor) * self.prev_global_cutoff + smoothing_factor * target_global_cutoff

        # Apply smoothed cutoff
        global_cutoff = self.prev_global_cutoff
        filter_env *= global_cutoff / 20



  

        with slider_val_lock:
            slider = slider_val

        resonance_threshold = 0.001
        if not hasattr(self, 'prev_slider_resonance'):
            self.prev_slider_resonance = slider

        slider_changed = abs(slider - self.prev_slider_resonance) > resonance_threshold
        self.prev_slider_resonance = slider

        # Far more conservative resonance range to avoid crackle
        low_res = 0.1
        high_res = 0.3
        target_resonance = low_res + (high_res - low_res) * (slider ** 0.5)

        if self.prev_resonance is None:
            self.prev_resonance = target_resonance
        elif slider_changed:
            smoothing_factor = 0.005
            self.prev_resonance = (1 - smoothing_factor) * self.prev_resonance + smoothing_factor * target_resonance

        resonance = self.prev_resonance



        with slider_val_lock:
            slider = slider_val
        # Disable drive boost entirely for stability
        target_drive = 1.0

        if not hasattr(self, 'prev_drive'):
            self.prev_drive = target_drive
        else:
            smoothing_factor = 0.005  # adjust between 0.05 and 0.2 as needed
            self.prev_drive = (1 - smoothing_factor) * self.prev_drive + smoothing_factor * target_drive

        drive = self.prev_drive



        # ------------------------------------------------------------------
        # Anti-crackle processing
        #   1.  Use *fresh* filter state every note (no carry-over).
        #   2.  Gentle soft-limit before filtering to tame transients.
        #   3.  Reduce drive for very long notes to avoid self-oscillation.
        #   4.  DC-block afterwards to remove residual bias.
        # ------------------------------------------------------------------

        # Soft-limit the signal (gentler, lower gain factor)
        combined_wave = np.tanh(combined_wave * 0.8) / 0.8

        # Long notes ⇒ halve the drive
        if duration > 2.0:
            drive *= 0.5

        # Local filter state (reset each call)
        local_low, local_band = 0.0, 0.0

        # ------------------------------------------------------------------
        # SIMPLE FIX:
        #   Replace crackle-prone resonant SVF with a single, stable
        #   2-pole Butterworth low-pass once per note.  We use the *average*
        #   of the dynamic filter-envelope as the cutoff for this note,
        #   clamped safely below Nyquist.
        # ------------------------------------------------------------------
        avg_cutoff = float(np.clip(np.mean(filter_env),
                                   20.0,
                                   0.45 * self.sample_rate))
        combined_wave = butter_lowpass_filter(
            combined_wave,
            cutoff=avg_cutoff,
            fs=self.sample_rate,
            order=2
        )

        # Simple DC-blocking high-pass (~20 Hz)
        # Stronger DC-blocking
        combined_wave = lfilter([1, -1], [1, -0.99], combined_wave)



        with slider_val_lock:
            slider = slider_val

        # Define smoothing factor and threshold for slider changes
        smoothing = 0.005
        slider_threshold = 0.001  # tweak as needed

        # Initialize previous slider and parameters on first run
        if not hasattr(self, 'prev_slider'):
            self.prev_slider = slider
        if not hasattr(self, 'prev_comb_drive'):
            self.prev_comb_drive = 0.15 * np.exp(-5 * slider)
        if not hasattr(self, 'prev_delay_time'):
            max_delay_s = 0.02
            min_delay_s = 0.005
            self.prev_delay_time = max_delay_s * (1 - slider) + min_delay_s * slider

        target_drive = 0.15 * np.exp(-5 * slider)
        self.prev_comb_drive = (1 - smoothing) * self.prev_comb_drive + smoothing * target_drive

        max_delay_s = 0.02
        min_delay_s = 0.005
        target_delay = max_delay_s * (1 - slider) + min_delay_s * slider
        self.prev_delay_time = (1 - smoothing) * self.prev_delay_time + smoothing * target_delay

        self.prev_slider = slider


        drive = self.prev_comb_drive
        delay_time = self.prev_delay_time
        feedback = 0.01  # fixed low feedback for chill effect

        # --- Comb filter (restored) ---------------------------------------
        combined_wave = comb_filter_modulated(
            combined_wave, sample_rate=self.sample_rate,
            base_delay=delay_time, feedback=feedback, drive=drive
        )



# ---------------- LFO amplitude modulation (restored) --------------------
        combined_wave *= (1 + lfo_wave)  # subtle vibrato/AM

        with slider_val_lock:
            slider = slider_val

        smoothing = 0.005

        if not hasattr(self, 'prev_tube_gain'):
            self.prev_tube_gain = 1.0
        if not hasattr(self, 'prev_tube_bias'):
            self.prev_tube_bias = 0.0
        if not hasattr(self, 'prev_tube_blend'):
            self.prev_tube_blend = 0.0

        target_gain = 1.0 + (3.0 - 1.0) * (slider ** 2)
        target_bias = 0.0 + 0.2 * (slider ** 1.5)
        target_blend = 0.5 * (slider ** 0.5)

        self.prev_tube_gain = (1 - smoothing) * self.prev_tube_gain + smoothing * target_gain
        self.prev_tube_bias = (1 - smoothing) * self.prev_tube_bias + smoothing * target_bias
        self.prev_tube_blend = (1 - smoothing) * self.prev_tube_blend + smoothing * target_blend

        combined_wave = tube_drive(
            combined_wave,
            gain=self.prev_tube_gain,
            bias=self.prev_tube_bias,
            blend=self.prev_tube_blend
        )


        with slider_val_lock:
            slider = slider_val

        if slider < 0.001:
            # Effect fully off, just pass through
            combined_wave_processed = combined_wave
        else:
            smoothing = 0.005
            min_mix = 0.0
            max_mix = 0.25

            if not hasattr(self, 'prev_bitcrusher_mix'):
                self.prev_bitcrusher_mix = 0.0  # start fully off

            target_mix = max_mix * (slider ** 0.5)

            self.prev_bitcrusher_mix = (1 - smoothing) * self.prev_bitcrusher_mix + smoothing * target_mix

            combined_wave_processed = bitcrusher(
                combined_wave,
                bit_depth=12,
                downsample_factor=3,
                mix=self.prev_bitcrusher_mix
            )

        combined_wave = combined_wave_processed

        with slider_val_lock:
            slider = slider_val

        smoothing = 0.005
        min_cutoff = 183
        max_cutoff = 20000
        log_min = np.log(min_cutoff)
        log_max = np.log(max_cutoff)
        target_cutoff = np.exp(log_min * (1 - slider) + log_max * slider)

        if not hasattr(self, 'prev_cutoff'):
            self.prev_cutoff = target_cutoff

        self.prev_cutoff = (1 - smoothing) * self.prev_cutoff + smoothing * target_cutoff

        cutoff = self.prev_cutoff

        combined_wave = butter_lowpass_filter(combined_wave, cutoff=cutoff, fs=self.sample_rate, order=4)


        fade_out_samples = int(0.01 * self.sample_rate)  # Keep fade-out short
        combined_wave[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

        


        combined_wave *= self.master_volume

        # Hard limiter to guarantee no clipping
        combined_wave = np.clip(combined_wave, -0.95, 0.95)

        def normalize_rms(signal, target_rms=0.1, eps=1e-8):
            rms = np.sqrt(np.mean(signal**2)) + eps
            return signal * (target_rms / rms)

        combined_wave = normalize_rms(combined_wave, target_rms=0.1)

        # ------------------------------------------------------------------
        # Apply GLOBAL EQ (high-shelf & low-mid) at the very end so the bass
        # synth responds to the same slider-controlled tonal shaping as drums.
        # ------------------------------------------------------------------
        with slider_val_lock:
            slider = slider_val
        combined_wave = apply_global_eq_to_array(combined_wave, slider)

        return combined_wave

    def schedule_pattern(self, base_time, midi_notes, step_duration, delay_pattern_sec):
        with self.lock:
            for i, midi_note in enumerate(midi_notes):
                if midi_note is None:
                    continue
                delay = delay_pattern_sec[i] if i < len(delay_pattern_sec) else 0
                start = base_time + i * step_duration + delay
                self.note_queue.append((start, midi_note, step_duration))

    def run(self):
        while True:
            now = time.time()
            with self.lock:
                for (start_time, midi_note, duration) in self.note_queue:
                    if start_time <= now:
                        wave = self.render_note(midi_note, duration)
                        self.active_notes.append((wave, 0))
                self.note_queue = [n for n in self.note_queue if n[0] > now]

            buffer = np.zeros(self.buffer_size, dtype=np.float32)
            new_active = []
            for wave, idx in self.active_notes:
                end_idx = idx + self.buffer_size
                segment = wave[idx:end_idx]
                buffer[:len(segment)] += segment
                if end_idx < len(wave):
                    new_active.append((wave, end_idx))
            self.active_notes = new_active

            
            buffer = np.clip(buffer, -1.0, 1.0)

            # Output audio buffer
            self.stream.write(buffer.tobytes())

            time.sleep(self.buffer_size / self.sample_rate * 0.01)




# Instantiate once globally somewhere after sample_rate is set:
bass_synth = Synth(sample_rate)
bass_synth.set_master_volume(0.5)  # sets volume to 50%



# Create the Tk root window only once
root = tk.Tk()
root.title("Sequencer BPM Control")
root.geometry('400x150')

label = tk.Label(root, text="BPM (log scale)")
label.pack(pady=10)

slider = tk.Scale(root, from_=0, to=1, resolution=0.001,
                  orient=tk.HORIZONTAL, length=300,
                  command=on_slider_change)
slider.set(bpm_to_slider(DEFAULT_BPM))
slider.pack()

stop_event = threading.Event()
sequencer_thread = threading.Thread(target=sequencer, args=(stop_event,), daemon=True)
sequencer_thread.start()

def on_close():
    stop_event.set()
    sequencer_thread.join()
    # Any other cleanup like pygame.mixer.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()
