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
import wave
import soundfile as sf
from scipy.signal import butter, lfilter
from dataclasses import dataclass

        # ====================================================================#
        # CONFIGURATION SECTION - ADJUST THESE VALUES TO CUSTOMIZE THE SYSTEM #
        # ====================================================================#

#---------------------------------------------------
# GLOBAL AUDIO SETTINGS
#---------------------------------------------------

## AUDIO SETTINGS
SAMPLE_RATE = 44100
BUFFER_SIZE = 1024
DRUMS_MASTER_VOLUME = 0.5      
BASS_SYNTH_MASTER_VOLUME = 0.9

## TIMING SETTINGS
MIN_BPM = 80                    
MAX_BPM = 180                   
DEFAULT_BPM = 120               
STEPS_PER_MEASURE = 16          

## SEQUENCER TIMING SETTINGS
# Initial delay before sequencer’s first trigger
SEQUENCER_GLOBAL_DELAY = 0.03       # seconds
# Re-use existing DRUM_DELAY_OFFSET for drum timing skew
# How many measures it takes to complete a BPM transition
BPM_RAMP_MEASURES = 4

# Smoothing Factors
PARAMETER_SMOOTHING = 0.005     # How fast parameters change (0.001-0.1)
# EFFECTS_SMOOTHING is now defined per-synth in the config dictionary
VOLUME_SMOOTHING    = 0.5       # Volume crossfade speed

## SAMPLE PATHS AND FILE NAMING
SAMPLE_BASE_PATH = "ProgrammableLoop2/ProgrammableLoop2"
KICK_SAMPLE_PREFIX = "Kick"
SNARE_SAMPLE_PREFIX = "Snare"
CYMBAL_SAMPLE_PREFIX = "Cymbal"
BASS_SAMPLE_FILENAME = "BassSynthOscillatorSample.wav"
SAMPLE_SUFFIX = ".wav"

## SAMPLE PROCESSING SETTINGS
BASS_SAMPLE_TRIM_MS = 10        # Trim amount for bass sample (ms)
DEFAULT_BASS_SAMPLE_PATH = "ProgrammableLoop2/ProgrammableLoop2BassSynthOscillatorSample.wav"  # Default sample path
BASE_MIDI_NOTE = 36             # Root MIDI note of the bass sample (C2)
SAMPLE_LATENCY_COMP_MS = 0.7    # Latency compensation for sample playback (ms)

# ---------------------------------------------------------------------------
# Global EQ Settings 
# ---------------------------------------------------------------------------

# Global EQ Ranges
GLOBAL_GAIN_DB_RANGE = 5.0      # ±5dB range for global gain
HIGHSHELF_DB_RANGE = 2.0        # ±2dB range for high shelf
LOWMID_DB_RANGE = 1.0           # ±1dB range for low-mid

# (These are used by the new bi-quad EQ helpers further below)
HIGHSHELF_FREQ_HZ     = 3000     # High-shelf starts at 3 kHz
HIGHSHELF_SLOPE_DB_OCT = 12      # 12 dB/oct ≈ 2-pole “gentle” shelf
LOWMID_CENTER_FREQ_HZ = 300      # Low-mid peaking-EQ centre
LOWMID_Q_FACTOR       = 2.0      # Q factor (bandwidth) for low-mid band

# Final Filter Settings
FINAL_FILTER_MIN_FREQ = 183     # Minimum final filter cutoff
FINAL_FILTER_MAX_FREQ = 20000   # Maximum final filter cutoff


#--------------
#   DRUMS
#--------------

## DRUM SETTINGS
KICK_BOOST_DB = 6.0             # Extra volume boost for kicks (dB)
KICK_FADE_IN_MS = 10            # Fade-in time to prevent clicks (ms)
DRUM_DELAY_OFFSET = 0.04        # Global drum timing offset (seconds)

#--------------
#   Bass
#--------------

## WAVEFORM OSCILLATOR SETTINGS (used like enums, kept global)
WAVEFORM_SINE     = 1   # Pure sine wave
WAVEFORM_TRIANGLE = 2   # Triangle wave
WAVEFORM_SQUARE   = 3   # Square wave

## TONIC AND TIMING (used by sequencer, kept global)
TONIC_MIDI_NOTE = 36            # C2 - root note for bass patterns
BASS_DURATION_MULTIPLIER = 2.0       # whole-beat multiplier
BASS_NOTE_DURATION_FACTOR = 0.875  # Notes end before next beat (0.0-1.0)

# All other bass-specific parameters are now defined directly
# in the BASS_CONFIG dictionary below.

#--------------------------------------------------------------------------#
# BASS SYNTH CONFIGURATION DICTIONARY                                     #
#--------------------------------------------------------------------------#
# This dictionary holds all parameters for the bass synth. To create a new #
# synth, copy this dictionary, rename it, and change the values.           #
#--------------------------------------------------------------------------#

BASS_CONFIG = {
    # --- Wave-form & musical settings -----------------------------------
    "WAVEFORM_SINE": 1,
    "WAVEFORM_TRIANGLE": 2,
    "WAVEFORM_SQUARE": 3,
    "DEFAULT_WAVEFORM_TYPE": 1,  # WAVEFORM_SINE
    "TONIC_MIDI_NOTE": 36,
    "BASE_GAIN_DB": 10,

    # --- Oscillator volume ----------------------------------------------
    "OSC1_VOLUME_DB_RANGE": 40,
    "OSC1_VOLUME_DB_CONVERSION": 20,

    # --- Note timing -----------------------------------------------------
    "BASS_DURATION_MULTIPLIER": 2.0,
    "BASS_NOTE_DURATION_FACTOR": 0.875,

    # --- AMP ADSR --------------------------------------------------------
    "ADSR_ATTACK_MIN": 0.018,
    "ADSR_ATTACK_MAX": 0.155,
    "ADSR_DECAY_MIN":  0.385,
    "ADSR_DECAY_MAX":  60.0,
    "ADSR_RELEASE_MIN": 0.1,
    "ADSR_RELEASE_MAX": 1.13,
    "ADSR_SUSTAIN_DB_MIN": -15.65,
    "ADSR_SUSTAIN_DB_MAX": 0.0,

    # --- LFO -------------------------------------------------------------
    "LFO_RATE_HZ": 3.22,
    "LFO_DEPTH_MIN_CENTS": 0.001,
    "LFO_DEPTH_MAX_CENTS": 3.81,

    # --- Tube drive ------------------------------------------------------
    "TUBE_GAIN_MIN":  1.0,
    "TUBE_GAIN_MAX":  3.0,
    "TUBE_BIAS_MIN":  0.0,
    "TUBE_BIAS_MAX":  0.2,
    "TUBE_BLEND_MIN": 0.0,
    "TUBE_BLEND_MAX": 0.5,

    # --- Bit-crusher -----------------------------------------------------
    "BITCRUSHER_BIT_DEPTH": 12,
    "BITCRUSHER_DOWNSAMPLE_FACTOR": 3,
    "BITCRUSHER_MIX_MAX": 0.25,

    # --- Effects ---------------------------------------------------------
    "EFFECTS_SMOOTHING": 0.005,

    # --- Filter chain (primary / comb / global) -------------------------
    # Primary
    "FILTER_PRIMARY_CUTOFF_MIN_HZ": 20.0,
    "FILTER_PRIMARY_CUTOFF_MAX_HZ": 20.0,
    "FILTER_PRIMARY_RESONANCE_MIN_Q": 0.01,
    "FILTER_PRIMARY_RESONANCE_MAX_Q": 3.6,
    "FILTER_PRIMARY_DRIVE_MIN": 0.01,
    "FILTER_PRIMARY_DRIVE_MAX": 2.7,
    "FILTER_PRIMARY_DRIVE_CURVE": 0.3,
    "FILTER_PRIMARY_ENVELOPE_AMOUNT_MIN": 0.12,
    "FILTER_PRIMARY_ENVELOPE_AMOUNT_MAX": 0.0,

    # Comb
    "FILTER_COMB_DELAY_MIN_MS": 2,
    "FILTER_COMB_DELAY_MAX_MS": 18,
    "FILTER_COMB_FEEDBACK_MIN": 0.1,
    "FILTER_COMB_FEEDBACK_MAX": 0.3,
    "FILTER_COMB_CUTOFF_MIN_HZ": 47,
    "FILTER_COMB_CUTOFF_MAX_HZ": 39.9,
    "FILTER_COMB_RESONANCE_MIN_Q": 2.9,
    "FILTER_COMB_RESONANCE_MAX_Q": 2.9,
    "FILTER_COMB_ENVELOPE_AMOUNT_MIN": 1.0,
    "FILTER_COMB_ENVELOPE_AMOUNT_MAX": 0.1,
    "FILTER_COMB_DRIVE_MIN": 1.5,
    "FILTER_COMB_DRIVE_MAX": 0.01,
    "FILTER_COMB_DRIVE_CURVE": 0.5,

    # Global
    "FILTER_GLOBAL_CUTOFF_MIN_HZ": 85.6,
    "FILTER_GLOBAL_CUTOFF_MAX_HZ": 296.0,
    "FILTER_GLOBAL_RESONANCE_MIN_Q": 4,
    "FILTER_GLOBAL_RESONANCE_MAX_Q": 0.01,

    # Envelope
    "FILTER_ENVELOPE_ATTACK_MIN_MS": 0.1,
    "FILTER_ENVELOPE_ATTACK_MAX_MS": 1074,
    "FILTER_ENVELOPE_DECAY_MIN_MS": 246.0,
    "FILTER_ENVELOPE_DECAY_MAX_MS": 1816.0,
    "FILTER_ENVELOPE_SUSTAIN_MIN_HZ": 20.0,
    "FILTER_ENVELOPE_SUSTAIN_MAX_HZ": 22.53,
    "FILTER_ENVELOPE_RELEASE_MIN_MS": 310.0,
    "FILTER_ENVELOPE_RELEASE_MAX_MS": 12460.0,
    "FILTER_ENVELOPE_RELEASE_TARGET_HZ": 50.0,

    # Misc processing
    "FILTER_NYQUIST_SAFETY_FACTOR": 0.9,
    "FILTER_RESONANCE_THRESHOLD": 0.2,
    "FILTER_RESONANCE_GAIN_SCALE": 8.0,
    "FILTER_RESONANCE_Q_FIXED": 1.0,
    "FILTER_GLOBAL_RESONANCE_THRESHOLD": 0.7,
    "FILTER_GLOBAL_RESONANCE_GAIN_SCALE": 6.0,
    "FILTER_GLOBAL_RESONANCE_Q": 1.5,
    "FILTER_ENVELOPE_SMOOTH_SAMPLES": 32,
}

# ---------------------------------------------------------------------------
# PATTERN MATRICES – EDIT THESE TO CHANGE THE MUSICAL PATTERNS
# Each pattern is 16 steps (4 beats of 16-th notes).  The list index of every
# matrix aligns with PATTERN_LABELS order.
# ---------------------------------------------------------------------------

## PATTERN LABELS
PATTERN_LABELS = [
    "SadLevel8", "SadLevel7", "SadLevel6", "SadLevel5",
    "SadLevel4", "SadLevel3", "SadLevel2", "SadLevel1", 
    "Neutral",
    "HappyLevel1", "HappyLevel2", "HappyLevel3", "HappyLevel4",
    "HappyLevel5", "HappyLevel6", "HappyLevel7", "HappyLevel8"
]

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
current_pattern_index: int  = 8                  # 8 = “Neutral” starting pattern
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
labels = PATTERN_LABELS

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

# BPM-RAMP HELPER
def update_bpm_from_slider(slider: float) -> float:
    """
    Update BPM with smooth ramping transitions based on slider position.

    This manages the global tempo-ramp state so that every time the user moves
    the slider, the tempo glides to the new value over a musical duration
    (``BPM_RAMP_MEASURES`` measures).  It returns the *current* BPM that the
    sequencer should use **right now**.

    Parameters
    ----------
    slider : float
        Current GUI slider value in the 0‒1 range.

    Returns
    -------
        # ------------------------------------------------------------------
        # Fetch current slider value for all remaining per-note processing
        # ------------------------------------------------------------------
        with slider_val_lock:
            slider = slider_val

    float
        env, attack = self.adsr_envelope(total_samples, slider)
    """
    global current_bpm, start_bpm, target_bpm, ramp_start_time, ramp_duration

    with bpm_lock:
        # Desired BPM derived from slider position
        new_target_bpm = slider_to_bpm(slider)

        # Start a new ramp whenever the target BPM changes
        if new_target_bpm != target_bpm:
            start_bpm        = current_bpm
            target_bpm       = new_target_bpm
            ramp_start_time  = time.time()
            ramp_duration    = (60 / start_bpm) * BPM_RAMP_MEASURES

        # If ramping, interpolate from start_bpm → target_bpm
        if ramp_start_time and ramp_duration:
            elapsed   = time.time() - ramp_start_time
            progress  = min(elapsed / ramp_duration, 1.0)
            current_bpm = start_bpm + (target_bpm - start_bpm) * progress

            # Ramp finished?
            if progress >= 1.0:
                current_bpm     = target_bpm
                start_bpm       = target_bpm
                ramp_start_time = None
                ramp_duration   = None

        return current_bpm

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

def freq_from_midi(midi_note):
    # Convert MIDI note number to Hz (used by Synth.render_note)
    return 440.0 * 2 ** ((midi_note - 69) / 12)

def get_extended_duration(pattern, start_index, base_duration):
    """
    Calculate the total duration for a bass note including tied continuations.

    Looks ahead in the pattern from ``start_index`` to count how many
    `'c'` symbols follow (indicating tied/continued notes), then multiplies
    ``base_duration`` by the total number of steps the note should sustain.

    Parameters
    ----------
    pattern : list
        Bass pattern containing degree strings, `'c'` for continuation,
        and ``0`` for rest.
    start_index : int
        Starting position in the pattern to begin counting from.
    base_duration : float
        Duration of a single *step* in **seconds**.

    Returns
    -------
    float
        Total duration for the note including all tied continuations.
    """
    length = len(pattern)
    total_steps = 1  # count the current note itself
    i = (start_index + 1) % length
    while pattern[i] == 'c':
        total_steps += 1
        i = (i + 1) % length
        if i == start_index:          # pattern of all 'c's → safety break
            break
    return base_duration * total_steps

# ============================================================================
# AUDIO LOADING
# ============================================================================

# Apply a short linear fade-in to *kick drum* samples to eliminate pops.
def fade_in_kick_sample(sound, sample_rate):
    """
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
            volume = DRUMS_MASTER_VOLUME * (10 ** (total_gain_db / 20))
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
            volume = DRUMS_MASTER_VOLUME * (10 ** (total_gain_db / 20))
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
            volume = DRUMS_MASTER_VOLUME * (10 ** (total_gain_db/20))
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()

# Helper: trigger *all* drum types for a single sequencer step
def trigger_drums_for_step(step: int,
                           pattern_index: int,
                           drum_delay_ms: float) -> None:
    # (pattern-matrix, corresponding play-function) pairs
    drum_map = [
        (KICK_PATTERNS,   play_kick_sample_with_delay_and_gain),
        (SNARE_PATTERNS,  play_snare_with_delay_and_gain),
        (CYMBAL_PATTERNS, play_cymbal_with_delay_and_gain),
    ]
    for pattern_matrix, play_fn in drum_map:
        if pattern_matrix[pattern_index][step]:
            delay_ms = (
                delay_patterns_ms[pattern_index][step] + drum_delay_ms
            )
            gain_db = DRUM_ACCENT_PATTERNS[pattern_index][step]
            play_fn(labels[pattern_index], delay_ms, gain_db)

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

#def get_degree_name(midi_note, tonic_note=tonic):
#    # Convert MIDI note to scale-degree name (mainly for debugging/analysis)
#    diff = midi_note - tonic_note
#    wrapped = diff % 12
#    if diff >= 0:
#        return scale_degree_map.get(wrapped, '?')
#    else:
#        # For below-tonic notes look up the negative equivalent label
#        return scale_degree_map.get(wrapped - 12, '?')

# (formerly commented-out resonant filter moved to active section above)

#def global_resonance_filter(wave, sample_rate,
#                            freq=85.61, resonance=13.65):
#    """Static resonant peak filter (legacy helper, not in current chain)."""
#    q      = resonance / 10
#    w0     = 2 * np.pi * freq / sample_rate
#    alpha  = np.sin(w0) / (2 * q)
#    b0, b2 =  alpha, -alpha
#    a0     = 1 + alpha
#    b      = np.array([b0, 0, b2]) / a0
#    a      = np.array([1, -2*np.cos(w0)/a0, (1-alpha)/a0])
#    return np.convolve(wave, b, 'same') - np.convolve(wave, a[1:], 'same')

#def comb_filter_modulated(wave, sample_rate,
#                          base_delay=1/47.1, feedback=0.3,
#                          drive=1.1538, env_percent=1.0):
#    """Simple feed-forward comb used for subtle body/chorus."""
#    out           = np.copy(wave) * (1 + drive)
#    delay_samples = int(sample_rate * base_delay)
#    for i in range(delay_samples, len(wave)):
#        out[i] += feedback * out[i - delay_samples]
#    return out

        # --- Comb filter (restored) ---------------------------------------
#        combined_wave = comb_filter_modulated(
#            combined_wave, sample_rate=self.sample_rate,
#            base_delay=delay_time, feedback=feedback, drive=drive
#        )




        # ===========================================================================#
        #                           S~E~Q~U~E~N~C~E~R                                #
        # ===========================================================================#

def sequencer(stop_event):
    global current_pattern_index, current_bpm, start_bpm, target_bpm, ramp_start_time, ramp_duration
    # Initial setup - timing variables and delay offsets
    global_delay = SEQUENCER_GLOBAL_DELAY
    next_trigger = time.time() + global_delay
    step = 0
    bass_pattern_index = 0  # to cycle through midi_note_pattern
    drum_delay = DRUM_DELAY_OFFSET
    # Main sequencer loop - read input, calculate timing, trigger events
    while not stop_event.is_set():
        with slider_val_lock:
            slider = slider_val
        # Convert slider to target pattern index
        target_pattern_index = int(round(slider * (len(labels) - 1)))
        # Update BPM with smooth ramping
        bpm_to_use = update_bpm_from_slider(slider)
        # Calculate timing for current BPM
        seconds_per_beat = 60 / bpm_to_use
        seconds_per_16th = seconds_per_beat / 4
        now = time.time()
        # Check if it's time to trigger the next step
        if now >= next_trigger:
            # Switch patterns only at step 0
            if target_pattern_index != current_pattern_index and step == 0:
                current_pattern_index = target_pattern_index
            # --- Trigger all drums for this step ---------------------------
            trigger_drums_for_step(step,
                                   current_pattern_index,
                                   drum_delay * 1000)
            # Schedule bass note for current step
            selected_bass_pattern = BASS_PATTERNS[current_pattern_index]
            degree = selected_bass_pattern[bass_pattern_index % len(selected_bass_pattern)]
            base_duration = seconds_per_16th * BASS_NOTE_DURATION_FACTOR * BASS_DURATION_MULTIPLIER  # whole beat
            now = time.time()
            if degree == 0 or degree == 'c':
                # Don't schedule; just advance
                note = None
            else:
                degree_str = degree if isinstance(degree, str) else str(degree)
                note = tonic + interval_to_semitone[degree_str]
                duration = get_extended_duration(selected_bass_pattern,
                                                 bass_pattern_index % len(selected_bass_pattern),
                                                 base_duration)
                bass_synth.schedule_note(now, note, duration)
            bass_pattern_index += 1
            # Advance to next step and set next trigger time
            step = (step + 1) % steps_per_measure
            next_trigger += seconds_per_16th
        else:
            # Sleep until next trigger time
            time_to_sleep = next_trigger - now
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

        # ===========================================================================#
        #                           S~Y~N~T~H~E~S~I~Z~E~R                            #
        # ===========================================================================#

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def butter_lowpass(cutoff: float, fs: int, order: int = 4):
    nyq = 0.5 * fs                       # Nyquist frequency
    normal_cutoff = cutoff / nyq         # Normalised cut-off (0‒1)
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

# ---------------------------------------------------------------------------
# FILTER CHAIN HELPER FUNCTIONS
# ---------------------------------------------------------------------------

@dataclass
class FilterParams:
    """Container for all filter chain parameters."""
    # Primary
    primary_cutoff: float
    primary_res_q: float
    primary_env_amt: float
    primary_drive: float
    # Comb
    comb_delay_ms: float
    comb_feedback: float
    comb_cutoff: float
    comb_res_q: float
    comb_env_amt: float
    comb_drive: float
    # Global
    global_cutoff: float
    global_res_q: float
    # Processing constants
    nyquist_safety_factor: float
    resonance_threshold: float
    resonance_gain_scale: float
    resonance_q_fixed: float
    global_resonance_threshold: float
    global_resonance_gain_scale: float
    global_resonance_q: float


def _log_interp(v_min: float, v_max: float, t: float) -> float:
    """Safe logarithmic interpolation with linear fallback."""
    # Log interpolation if valid range, otherwise linear
    if v_max > v_min and v_min > 0:
        log_min = math.log(v_min)
        log_max = math.log(v_max)
        return math.exp(log_min + t * (log_max - log_min))
    return v_min + (v_max - v_min) * t

def calculate_filter_parameters(slider: float, config: dict) -> FilterParams:
    """Compute every filter-chain parameter from a single slider (0‒1)."""

    # Primary filter params - log scaled
    primary_cutoff  = _log_interp(config['FILTER_PRIMARY_CUTOFF_MIN_HZ'],
                                  config['FILTER_PRIMARY_CUTOFF_MAX_HZ'], slider)
    primary_res_q   = _log_interp(config['FILTER_PRIMARY_RESONANCE_MIN_Q'],
                                  config['FILTER_PRIMARY_RESONANCE_MAX_Q'], slider)
    primary_env_amt = _log_interp(config['FILTER_PRIMARY_ENVELOPE_AMOUNT_MIN'],
                                  config['FILTER_PRIMARY_ENVELOPE_AMOUNT_MAX'], slider)
    primary_drive   = _log_interp(config['FILTER_PRIMARY_DRIVE_MIN'],
                                  config['FILTER_PRIMARY_DRIVE_MAX'], slider)

    # Comb filter params - log scaled (delay inverted)
    comb_delay_ms = _log_interp(config['FILTER_COMB_DELAY_MIN_MS'],
                                config['FILTER_COMB_DELAY_MAX_MS'], 1 - slider)
    comb_feedback = _log_interp(config['FILTER_COMB_FEEDBACK_MIN'],
                                config['FILTER_COMB_FEEDBACK_MAX'], slider)
    comb_cutoff   = _log_interp(config['FILTER_COMB_CUTOFF_MIN_HZ'],
                                config['FILTER_COMB_CUTOFF_MAX_HZ'], slider)
    comb_res_q    = _log_interp(config['FILTER_COMB_RESONANCE_MIN_Q'],
                                config['FILTER_COMB_RESONANCE_MAX_Q'], slider)
    comb_env_amt  = _log_interp(config['FILTER_COMB_ENVELOPE_AMOUNT_MIN'],
                                config['FILTER_COMB_ENVELOPE_AMOUNT_MAX'], slider)
    comb_drive    = _log_interp(config['FILTER_COMB_DRIVE_MIN'],
                                config['FILTER_COMB_DRIVE_MAX'], slider)

    # Global filter params - log scaled
    global_cutoff = _log_interp(config['FILTER_GLOBAL_CUTOFF_MIN_HZ'],
                                config['FILTER_GLOBAL_CUTOFF_MAX_HZ'], slider)
    global_res_q  = _log_interp(config['FILTER_GLOBAL_RESONANCE_MIN_Q'],
                                config['FILTER_GLOBAL_RESONANCE_MAX_Q'], slider)

    return FilterParams(
        primary_cutoff, primary_res_q, primary_env_amt, primary_drive,
        comb_delay_ms, comb_feedback, comb_cutoff, comb_res_q,
        comb_env_amt, comb_drive,
        global_cutoff, global_res_q,
        nyquist_safety_factor=config['FILTER_NYQUIST_SAFETY_FACTOR'],
        resonance_threshold=config['FILTER_RESONANCE_THRESHOLD'],
        resonance_gain_scale=config['FILTER_RESONANCE_GAIN_SCALE'],
        resonance_q_fixed=config['FILTER_RESONANCE_Q_FIXED'],
        global_resonance_threshold=config['FILTER_GLOBAL_RESONANCE_THRESHOLD'],
        global_resonance_gain_scale=config['FILTER_GLOBAL_RESONANCE_GAIN_SCALE'],
        global_resonance_q=config['FILTER_GLOBAL_RESONANCE_Q']
    )

def apply_primary_filter(sig: np.ndarray, params: FilterParams,
                         filter_envelope: np.ndarray,
                         sample_rate: int) -> np.ndarray:
    """Primary LPF + resonance + drive."""
    nyq = 0.5 * sample_rate
    # Envelope modulates cutoff frequency
    mod_cut = params.primary_cutoff + (filter_envelope - 20.0) * params.primary_env_amt
    mod_cut = np.clip(mod_cut, 20.0, nyq * params.nyquist_safety_factor)
    avg_cut = float(np.mean(mod_cut))

    # 2-pole low-pass filter
    b_lp, a_lp = butter(2, avg_cut / nyq, btype='low')
    sig = lfilter(b_lp, a_lp, sig)

    # Resonant peak if above threshold
    if params.primary_res_q > params.resonance_threshold:
        gain_db = (params.primary_res_q - params.resonance_threshold) * params.resonance_gain_scale
        A = 10 ** (gain_db / 40)
        w0 = 2 * math.pi * avg_cut / sample_rate
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / (2 * params.resonance_q_fixed)
        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A
        sig = lfilter([b0/a0, b1/a0, b2/a0],
                      [1.0, a1/a0, a2/a0], sig)

    # Soft drive / saturation
    if params.primary_drive > 1.0:
        sig = np.tanh(sig * params.primary_drive) / params.primary_drive
    return sig

def apply_comb_filter(sig: np.ndarray, params: FilterParams,
                      filter_envelope: np.ndarray,
                      sample_rate: int) -> np.ndarray:
    """Enhanced ANA2-style comb filter."""
    nyq = 0.5 * sample_rate
    delay_samp = max(1, int(sample_rate * params.comb_delay_ms / 1000))
    if delay_samp >= len(sig):
        return sig

    # Envelope modulates comb cutoff
    comb_mod_cut = params.comb_cutoff + (filter_envelope - 20.0) * params.comb_env_amt
    comb_mod_cut = np.clip(comb_mod_cut, 20.0, nyq * params.nyquist_safety_factor)
    comb_avg_cut = float(np.mean(comb_mod_cut))

    # Pre-filter before delay line
    b_pre, a_pre = butter(2, comb_avg_cut / nyq, btype='low')
    proc = lfilter(b_pre, a_pre, sig)

    # Drive saturation before delay
    if params.comb_drive > 1.0:
        proc = np.tanh(proc * params.comb_drive) / params.comb_drive

    # Delay + feedback loop
    out = proc.copy()
    for i in range(delay_samp, len(proc)):
        out[i] += params.comb_feedback * out[i - delay_samp]

    # Optional resonance peak on output
    if params.comb_res_q > 0.2:
        gain_db = (params.comb_res_q - 0.2) * 6.0
        A = 10 ** (gain_db / 40)
        w0 = 2 * math.pi * comb_avg_cut / sample_rate
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / 2
        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A
        out = lfilter([b0/a0, b1/a0, b2/a0],
                      [1.0, a1/a0, a2/a0], out)
    return out

def apply_global_filter(sig: np.ndarray, params: FilterParams,
                        sample_rate: int) -> np.ndarray:
    """Global LPF + resonance peak."""
    nyq = 0.5 * sample_rate
    
    # Global lowpass filter
    b_lp, a_lp = butter(2, params.global_cutoff / nyq, btype='low')
    sig = lfilter(b_lp, a_lp, sig)

    # Global resonance peak if above threshold
    if params.global_res_q > params.global_resonance_threshold:
        gain_db = (params.global_res_q - params.global_resonance_threshold) * params.global_resonance_gain_scale
        A = 10 ** (gain_db / 40)
        w0 = 2 * math.pi * params.global_cutoff / sample_rate
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / (2 * params.global_resonance_q)
        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A
        sig = lfilter([b0/a0, b1/a0, b2/a0],
                      [1.0, a1/a0, a2/a0], sig)
    return sig

# ---------------------------------------------------------------------------
# FILTER CHAIN
# ---------------------------------------------------------------------------

def filter_chain(wave: np.ndarray,
                 filter_envelope: np.ndarray,
                 slider: float,
                 sample_rate: int,
                 config: dict) -> np.ndarray:

    if wave.size == 0:
        return wave

    # 1) Derive all parameters from slider ------------------------------
    params = calculate_filter_parameters(slider, config)

    # 2) Primary low-pass filter stage ----------------------------------
    sig = apply_primary_filter(wave, params, filter_envelope, sample_rate)

    # 3) Comb filter stage ----------------------------------------------
    sig = apply_comb_filter(sig, params, filter_envelope, sample_rate)

    # 4) Global low-pass (master filter) --------------------------------
    sig = apply_global_filter(sig, params, sample_rate)

    return sig

# ---------------------------------------------------------------------------
# EFFECTS FUNCTIONS
# ---------------------------------------------------------------------------

def tube_drive(signal, gain=3.0, bias=0.2, blend=0.5):
    """Symmetric tanh soft-clip with bias, blended dry/wet."""
    driven     = gain * signal + bias
    saturated  = np.tanh(driven) - np.mean(np.tanh(driven))
    return (1 - blend) * signal + blend * saturated

def bitcrusher(signal, bit_depth=8, downsample_factor=4, mix=1.0):
    """Naïve bit-depth & down-sample crusher, blended dry/wet."""
    max_int  = 2 ** bit_depth - 1
    crushed  = np.floor((signal + 1) / 2 * max_int) / max_int * 2 - 1
    crushed  = np.repeat(crushed[::downsample_factor], downsample_factor)
    crushed  = crushed[:len(signal)]
    return (1 - mix) * signal + mix * crushed

def final_lowpass(data: np.ndarray,
                          cutoff: float,
                          fs: int,
                          order: int = 4) -> np.ndarray:
    b, a = butter_lowpass(cutoff, fs, order=order)
    return lfilter(b, a, data)

# ---------------------------------------------------------------------------
# ACTUAL SYNTH
# ---------------------------------------------------------------------------

class Synth:
    
    # ------------------------------------------------------------------
    # INITIALIZER
    # ------------------------------------------------------------------
    def __init__(self, sample_rate,
                 buffer_size: int = 1024,
                 sample_path: str | None = None,
                 waveform_type: int | None = None,
                 config: dict | None = None):
        self.sample_rate = sample_rate              # Audio samples per second
        self.buffer_size = buffer_size              # Audio chunk size
        # ---------------- CONFIG DICTIONARY --------------------------
        # Allows each Synth instance to use its own parameter set
        self.config = config or BASS_CONFIG

        self.p = pyaudio.PyAudio()                  # Audio driver connection
        self.stream = self.p.open(                  # Audio output stream
            format=pyaudio.paFloat32,
            channels=1,
            rate=sample_rate,
            output=True,
            frames_per_buffer=buffer_size
        )
        self.lock = threading.Lock()                # Thread safety lock
        self.active_notes = []                      # Currently playing notes
        self.note_queue = []                        # Notes waiting to play
        self.thread = threading.Thread(             # Background audio engine
            target=self.run, daemon=True
        )
        self.thread.start()
        self.osc1_volume = 1.0                      # FM oscillator volume
        self.master_volume = 1.0                    # Overall output volume
        self.prev_resonance = None                  # Previous resonance value
        self.lowpass_low = 0.0                      # Filter low state
        self.lowpass_band = 0.0                     # Filter band state

        # --------------------------------------------------------------
        # LOAD BASS SAMPLE (configurable per-instance with error handling)
        # --------------------------------------------------------------
        self.has_sample = False                       # track successful load

        if sample_path is None:
            sample_path = DEFAULT_BASS_SAMPLE_PATH

        try:
            # --- Attempt to read the sample file ----------------------
            self.sample_wave, self.sample_rate_wave = sf.read(
                sample_path, dtype='float32'
            )

            # Convert stereo → mono if required
            if self.sample_wave.ndim > 1:
                self.sample_wave = np.mean(self.sample_wave, axis=1)

            # Optional leading-edge trim to remove clicks
            trim_ms = BASS_SAMPLE_TRIM_MS
            trim_samples = int(self.sample_rate_wave * trim_ms / 1000)
            self.sample_wave = self.sample_wave[trim_samples:]

            self.has_sample = True
            print(f"✓ Sample loaded: {sample_path}")

        except Exception as e:
            # ----------------------------------------------------------
            # Graceful fallback: FM-only synth (no sample oscillator)
            # ----------------------------------------------------------
            print(f"⚠️  Could not load sample '{sample_path}': {e}")
            print("⚠️  Falling back to FM-only synth (no sample oscillator).")

            self.sample_wave = np.array([], dtype=np.float32)
            self.sample_rate_wave = self.sample_rate
            self.has_sample = False

        # --------------------------------------------------------------
        # WAVEFORM TYPE (sine / triangle / square)
        # --------------------------------------------------------------
        # Falls back to global default if not explicitly provided
        self.waveform_type = (
            waveform_type
            if waveform_type is not None
            else self.config['DEFAULT_WAVEFORM_TYPE']
        )

    # ------------------------------------------------------------------
    # SIGNAL CHAIN
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # OSC-1 VOLUME MAPPER  (moved from global-scope)
    # ------------------------------------------------------------------
    def slider_to_osc1_volume(self, slider: float) -> float:
        """
        Map slider position (0‒1) to a **linear** amplitude value for the
        first oscillator using this synth’s configuration.
        """
        db_range      = self.config['OSC1_VOLUME_DB_RANGE']
        db_conversion = self.config['OSC1_VOLUME_DB_CONVERSION']
        db = -db_range * slider
        return 10 ** (db / db_conversion)

    # Clamp Volume for even mix of oscillators
    def set_master_volume(self, volume):
        # Clamp volume between 0.0 and 1.0
        self.master_volume = max(0.0, min(volume, 1.0))

    # PURE WAVE OSCILLATOR
    def lfo(self, rate, depth_cents, carrier_freq, duration):
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        depth = carrier_freq * (2 ** (depth_cents / 1200) - 1)
        return np.sin(2 * np.pi * rate * t) * depth
    def pure_wave_oscillator(self,
                             carrier_freq: float,
                             mod_freq: float,
                             mod_index: float,
                             duration: float,
                             waveform_type: int = WAVEFORM_SINE,
                             lfo_wave: np.ndarray | None = None) -> np.ndarray:
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)

        # Apply LFO
        modulated_carrier = carrier_freq if lfo_wave is None else carrier_freq + lfo_wave

        # FM modulator (0 → pure tone)
        modulator = np.sin(2 * np.pi * mod_freq * t)
        phase = 2 * np.pi * modulated_carrier * t + mod_index * modulator

        # ----------- BASE WAVEFORM SELECTION --------------------------
        if waveform_type == WAVEFORM_SQUARE:
            # Square: sign of sine → {-1, 1}
            base_wave = np.sign(np.sin(phase))
        elif waveform_type == WAVEFORM_TRIANGLE:
            # Triangle: scaled arcsin(sin) → [-1, 1]
            base_wave = (2 / np.pi) * np.arcsin(np.sin(phase))
        else:
            # Default SINE
            base_wave = np.sin(phase)

        wave = base_wave
        return wave.astype(np.float32)

    # SAMPLE OSCILLATOR
    def sample_oscillator(self, duration, midi_note):
        # If no sample:
        if not self.has_sample or self.sample_wave.size == 0:
            total_samples = int(self.sample_rate * duration)
            return np.zeros(total_samples, dtype=np.float32)

        # SAMPLE-OSCILLATOR PATH
        base_midi_note = BASE_MIDI_NOTE  # Root note from config
        semitone_diff = midi_note - base_midi_note
        playback_rate = 2 ** (semitone_diff / 12)

        # ---------------------- RESAMPLING -----------------------------
        if self.sample_rate_wave != self.sample_rate:
            factor = len(self.sample_wave) * self.sample_rate / self.sample_rate_wave
            resampled = np.interp(
                np.linspace(0, len(self.sample_wave), int(factor), endpoint=False),
                np.arange(len(self.sample_wave)),
                self.sample_wave
            )
        else:
            resampled = self.sample_wave

        # Pitch-shift by altering playback rate
        new_len = int(len(resampled) / playback_rate)
        resampled = np.interp(
            np.linspace(0, len(resampled), new_len, endpoint=False),
            np.arange(len(resampled)),
            resampled
        )

        # -------------------- LATENCY COMP -----------------------------
        latency_ms = SAMPLE_LATENCY_COMP_MS   # Latency compensation from config
        latency_samples = int(self.sample_rate * latency_ms / 1000)
        if len(resampled) > latency_samples:
            resampled = resampled[latency_samples:]
        else:
            resampled = np.zeros_like(resampled)

        # ------------------ LOOP & CROSSFADE ---------------------------
        total_samples = int(self.sample_rate * duration)
        output = np.zeros(total_samples, dtype=np.float32)

        if len(resampled) < total_samples:
            crossfade_samples = min(100, len(resampled) // 4)  # X-fade size
            fade_in  = np.linspace(0, 1, crossfade_samples)    # Fade-in curve
            fade_out = np.linspace(1, 0, crossfade_samples)    # Fade-out curve

            position = 0
            while position < total_samples:
                samples_to_copy = min(len(resampled),                # Chunk size
                                      total_samples - position)

                if position + samples_to_copy >= total_samples:
                    # Final chunk
                    output[position:position + samples_to_copy] = resampled[:samples_to_copy]
                else:
                    if position + len(resampled) <= total_samples:
                        output[position:position + len(resampled)] += resampled  # Full copy

                        next_position = position + len(resampled) - crossfade_samples
                        if next_position + crossfade_samples <= total_samples:
                            output[next_position:next_position + crossfade_samples] *= fade_out  # Fade current

                            if next_position + crossfade_samples + len(resampled) <= total_samples:
                                next_loop_start = next_position + crossfade_samples
                                output[next_loop_start:next_loop_start + crossfade_samples] += (  # Fade next
                                    resampled[:crossfade_samples] * fade_in)
                    else:
                        samples_remaining = total_samples - position  # Tail part
                        output[position:] += resampled[:samples_remaining]

                position += len(resampled) - crossfade_samples        # Advance index
        else:
            output = resampled[:total_samples]  # Trim excess

        return output

    # ADSR ENVELOPE
    def adsr_envelope(self,
                      length: int,
                      slider: float,
                      decay: float | None = None,
                      sustain_level: float | None = None,
                      release: float | None = None):
        """Generate ADSR envelope – ranges come from CONFIG constants."""

        # ----------- CONFIG-DRIVEN RANGES -----------------------------
        min_attack   = self.config['ADSR_ATTACK_MIN']
        max_attack   = self.config['ADSR_ATTACK_MAX']
        min_decay    = self.config['ADSR_DECAY_MIN']
        max_decay    = self.config['ADSR_DECAY_MAX']
        min_release  = self.config['ADSR_RELEASE_MIN']
        max_release  = self.config['ADSR_RELEASE_MAX']
        min_db       = self.config['ADSR_SUSTAIN_DB_MIN']
        max_db       = self.config['ADSR_SUSTAIN_DB_MAX']

        # ----------- TIME INTERPOLATION (log) -------------------------
        attack_time   = max_attack * (min_attack / max_attack) ** slider
        decay_time    = min_decay  * (max_decay  / min_decay)  ** slider
        release_time  = max_release * (min_release / max_release) ** slider

        attack_samples  = max(1, int(self.sample_rate * attack_time))
        decay_samples   = max(1, int(self.sample_rate * decay_time))
        release_samples = max(1, int(self.sample_rate * release_time))

        sustain_samples = max(0, length - attack_samples - decay_samples - release_samples)

        # Length adjust (rounding safety)
        total = attack_samples + decay_samples + sustain_samples + release_samples
        diff  = length - total
        if diff > 0:
            sustain_samples += diff
        elif diff < 0:
            sustain_samples = max(0, sustain_samples + diff)

        # ----------- BUILD ENVELOPE SEGMENTS --------------------------
        attack_env = np.linspace(0.0, 1.0, attack_samples, endpoint=False)

        sustain_db   = min_db + (max_db - min_db) * slider
        sustain_lin  = 10 ** (sustain_db / 20)

        decay_env    = np.linspace(1.0, sustain_lin, decay_samples, endpoint=False)
        sustain_env  = np.full(sustain_samples, sustain_lin, dtype=np.float32)
        release_env  = np.linspace(sustain_lin, 0.0, release_samples, endpoint=True)

        envelope = np.concatenate((attack_env, decay_env, sustain_env, release_env))

        # Pad / trim (floating-point rounding)
        if len(envelope) < length:
            envelope = np.pad(envelope, (0, length - len(envelope)),
                              mode='constant', constant_values=0.0)
        elif len(envelope) > length:
            envelope = envelope[:length]

        assert len(envelope) == length, (
            f"Envelope length {len(envelope)} != expected {length}"
        )
        return envelope, attack_time

    # FILTER ENVELOPE
    def filter_envelope(self, length, peak_freq=None, sustain_freq=None, slider=0.0):
        """Generate filter-cutoff envelope fully driven by CONFIG."""

        # ------------------- FREQUENCY RANGES ------------------------
        sustain_hz = (
            self.config['FILTER_ENVELOPE_SUSTAIN_MIN_HZ'] +
            (self.config['FILTER_ENVELOPE_SUSTAIN_MAX_HZ'] - self.config['FILTER_ENVELOPE_SUSTAIN_MIN_HZ']) * slider
        )
        peak_hz = sustain_hz + sustain_hz * 0.1265   # 12.65 % upward swing
        release_target_hz = self.config['FILTER_ENVELOPE_RELEASE_TARGET_HZ']

        # -------------------- TIME RANGES (s) ------------------------
        min_attack_s  = self.config['FILTER_ENVELOPE_ATTACK_MIN_MS']   / 1000.0
        max_attack_s  = self.config['FILTER_ENVELOPE_ATTACK_MAX_MS']   / 1000.0
        min_decay_s   = self.config['FILTER_ENVELOPE_DECAY_MIN_MS']    / 1000.0
        max_decay_s   = self.config['FILTER_ENVELOPE_DECAY_MAX_MS']    / 1000.0
        min_release_s = self.config['FILTER_ENVELOPE_RELEASE_MIN_MS']  / 1000.0
        max_release_s = self.config['FILTER_ENVELOPE_RELEASE_MAX_MS']  / 1000.0

        # Log-interpolated times
        attack_time  = max_attack_s * (min_attack_s  / max_attack_s)  ** slider
        decay_time   = min_decay_s  * (max_decay_s   / min_decay_s)   ** slider
        release_time = min_release_s * (max_release_s / min_release_s) ** slider

        # ------------------ SAMPLE COUNTS ----------------------------
        attack_samples  = max(1, int(self.sample_rate * attack_time))
        decay_samples   = max(1, int(self.sample_rate * decay_time))
        release_samples = max(1, int(self.sample_rate * release_time))
        sustain_samples = max(0, length - attack_samples - decay_samples - release_samples)

        # Adjust rounding errors
        total = attack_samples + decay_samples + sustain_samples + release_samples
        diff  = length - total
        if diff > 0:
            sustain_samples += diff
        elif diff < 0:
            sustain_samples = max(0, sustain_samples + diff)

        # ------------------ BUILD SEGMENTS ---------------------------
        attack_env  = np.linspace(sustain_hz, peak_hz, attack_samples,  endpoint=False)
        decay_env   = np.linspace(peak_hz,   sustain_hz, decay_samples, endpoint=False)
        sustain_env = np.full(sustain_samples, sustain_hz, dtype=np.float32)
        release_env = np.linspace(sustain_hz, release_target_hz, release_samples, endpoint=True)

        envelope = np.concatenate((attack_env, decay_env, sustain_env, release_env))

        # Ensure exact length
        if len(envelope) < length:
            envelope = np.pad(envelope, (0, length - len(envelope)), mode='edge')
        elif len(envelope) > length:
            envelope = envelope[:length]

        return envelope

    # Queue up notes
    def schedule_note(self, start_time, midi_note, duration):
        with self.lock:
            self.note_queue.append((start_time, midi_note, duration))

    # OSCILLATOR GENERATION
    def _generate_oscillators(self, midi_note: int,
                              duration: float) -> tuple[np.ndarray, np.ndarray]:
        """Generate and mix FM + Sample oscillators with smoothed volumes.
        Optimised to skip oscillator generation when their volumes
        would fall below a negligible threshold.
        """
        freq = freq_from_midi(midi_note)
        total_samples = int(self.sample_rate * duration)

        # ---- Fetch current slider positions ---------------------------
        with slider_val_lock:
            osc1_slider = slider_val    # controls FM amount
            slider       = slider_val    # overall tonal slider

        # ---- Desired target volumes  ----------------------------------
        target_osc1_vol = self.slider_to_osc1_volume(osc1_slider)
        target_sample_vol_db = -40 * ((1 - slider) ** 4)
        target_sample_vol = 10 ** (target_sample_vol_db / 20)

        SILENCE_THRESHOLD = 0.01        # below ‑40 dB ≈ silent
        smoothing = 0.5                 # volume-crossfade smoothing

        # Ensure previous-volume attrs exist
        if not hasattr(self, 'prev_osc1_volume'):
            self.prev_osc1_volume = 0.0
        if not hasattr(self, 'prev_sample_volume'):
            self.prev_sample_volume = 0.0

        # ---- Initialise output buffer ---------------------------------
        combined_wave = np.zeros(total_samples, dtype=np.float32)

        # ----------------------------------------------------------------
        # 1) PURE WAVE OSCILLATOR
        # ----------------------------------------------------------------
        if target_osc1_vol > SILENCE_THRESHOLD:
            mod_freq  = freq * 2
            mod_index = 0.0868 * (1 - osc1_slider)
            fm_wave   = self.pure_wave_oscillator(freq,
                                                 mod_freq,
                                                 mod_index,
                                                 duration,
                                                 waveform_type=self.waveform_type)

            # Smooth volume
            self.prev_osc1_volume = ((1 - smoothing) * self.prev_osc1_volume
                                     + smoothing * target_osc1_vol)
            combined_wave += fm_wave * self.prev_osc1_volume
        else:
            # Decay stored volume towards zero for seamless fades
            self.prev_osc1_volume *= (1 - smoothing)

        # ----------------------------------------------------------------
        # 2) SAMPLE OSCILLATOR  
        # ----------------------------------------------------------------
        if self.has_sample and target_sample_vol > SILENCE_THRESHOLD:
            sample_wave = self.sample_oscillator(duration, midi_note)

            # Smooth Sample volume
            self.prev_sample_volume = ((1 - smoothing) * self.prev_sample_volume
                                       + smoothing * target_sample_vol)
            combined_wave += sample_wave * self.prev_sample_volume
        else:
            self.prev_sample_volume *= (1 - smoothing)

        # ----------------------------------------------------------------
        # 3) LFO
        # ----------------------------------------------------------------
        lfo_rate        = self.config['LFO_RATE_HZ']
        min_depth_cents = self.config['LFO_DEPTH_MIN_CENTS']
        max_depth_cents = self.config['LFO_DEPTH_MAX_CENTS']
        lfo_depth_cents = max_depth_cents * (min_depth_cents / max_depth_cents) ** slider
        lfo_wave = self.lfo(lfo_rate, lfo_depth_cents, freq, duration)

        return combined_wave, lfo_wave

    # ENVELOPE APPLICATION
    def _apply_envelopes(self,
                         combined_wave: np.ndarray,
                         duration: float,
                         total_samples: int,
                         slider: float) -> np.ndarray:
        """
        Apply ADSR amplitude envelope, generate / smooth filter-envelope and
        run the full ANA2 filter chain (primary LPF → comb → global LPF).
        """
        # === Amplitude ADSR ===========================================
        env, _ = self.adsr_envelope(total_samples, slider)
        combined_wave *= env

        # === Filter envelope (frequency) ==============================
        filter_env = self.filter_envelope(total_samples,
                                          peak_freq=22.53,
                                          sustain_freq=20)
        filter_env = filter_env * (1 - slider) + np.mean(filter_env) * slider

        # Anti-crackle smoothing (tiny moving-average)
        smooth_window = self.config['FILTER_ENVELOPE_SMOOTH_SAMPLES']
        if smooth_window > 1:
            kernel = np.ones(smooth_window, dtype=np.float32) / smooth_window
            filter_env = np.convolve(filter_env, kernel, mode='same')

        # Global Cutoff for Filter Envelope
        log_min = np.log(self.config['FILTER_GLOBAL_CUTOFF_MIN_HZ'])
        log_max = np.log(self.config['FILTER_GLOBAL_CUTOFF_MAX_HZ'])
        target_cutoff = np.exp(log_min * (1 - slider) + log_max * slider)

        # Smooth cutoff changes
        if not hasattr(self, 'prev_global_cutoff'):
            self.prev_global_cutoff = target_cutoff
        else:
            self.prev_global_cutoff = (
                0.995 * self.prev_global_cutoff + 0.005 * target_cutoff
            )
        filter_env *= self.prev_global_cutoff / 20.0

        # Gentle pre-clip to tame transients
        combined_wave = np.tanh(combined_wave * 0.8) / 0.8

        # Filter Chain
        combined_wave = filter_chain(combined_wave,
                                     filter_env,
                                     slider,
                                     self.sample_rate,
                                     self.config)

        # DC-blocking high-pass  (~20 Hz)
        combined_wave = lfilter([1, -1], [1, -0.99], combined_wave)
        return combined_wave

    # EFFECTS CHAIN
    def _apply_effects_chain(self,
                             combined_wave: np.ndarray,
                             lfo_wave: np.ndarray,
                             slider: float) -> np.ndarray:
        """
        Apply LFO amplitude-modulation, tube-drive saturation and bit-crusher
        with parameter smoothing.  All per-instance state is stored on *self*
        so multiple Synth objects remain isolated.
        """
        # --- 1) LFO amplitude modulation ------------------------------
        combined_wave *= (1 + lfo_wave)

        # --- 2) Tube-drive saturation ---------------------------------
        smoothing = self.config['EFFECTS_SMOOTHING']
        if not hasattr(self, 'prev_tube_gain'):
            self.prev_tube_gain  = 1.0
            self.prev_tube_bias  = 0.0
            self.prev_tube_blend = 0.0

        target_gain  = 1.0 + (self.config['TUBE_GAIN_MAX'] - self.config['TUBE_GAIN_MIN']) * (slider ** 2)
        target_bias  = self.config['TUBE_BIAS_MAX'] * (slider ** 1.5)
        target_blend = self.config['TUBE_BLEND_MAX'] * (slider ** 0.5)

        self.prev_tube_gain  = ((1 - smoothing) * self.prev_tube_gain
                                + smoothing * target_gain)
        self.prev_tube_bias  = ((1 - smoothing) * self.prev_tube_bias
                                + smoothing * target_bias)
        self.prev_tube_blend = ((1 - smoothing) * self.prev_tube_blend
                                + smoothing * target_blend)

        combined_wave = tube_drive(combined_wave,
                                   gain=self.prev_tube_gain,
                                   bias=self.prev_tube_bias,
                                   blend=self.prev_tube_blend)

        # --- 3) Bit-crusher -------------------------------------------
        if not hasattr(self, 'prev_bitcrusher_mix'):
            self.prev_bitcrusher_mix = 0.0

        # Bitcrusher mix scales with slider (√response for finer control)
        target_mix = self.config['BITCRUSHER_MIX_MAX'] * (slider ** 0.5)
        self.prev_bitcrusher_mix = ((1 - smoothing) * self.prev_bitcrusher_mix
                                    + smoothing * target_mix)

        combined_wave = bitcrusher(combined_wave,
                                   bit_depth=self.config['BITCRUSHER_BIT_DEPTH'],
                                   downsample_factor=self.config['BITCRUSHER_DOWNSAMPLE_FACTOR'],
                                   mix=self.prev_bitcrusher_mix)
        return combined_wave

    # FINAL PROCESSING
    def _apply_final_processing(self,
                                combined_wave: np.ndarray,
                                slider: float) -> np.ndarray:
        """
        Apply the final processing stage:
          1. Smooth-param final low-pass filter
          2. Short fade-out to avoid clicks
          3. Global EQ (matches drum chain)
          4. Hard-limiter & RMS normalisation
          5. Master-volume scaling
        """
        # --- 1) Smooth final low-pass ---------------------------------
        smoothing   = PARAMETER_SMOOTHING  # From config
        log_min     = np.log(FINAL_FILTER_MIN_FREQ)
        log_max     = np.log(FINAL_FILTER_MAX_FREQ)
        target_cut  = np.exp(log_min * (1 - slider) + log_max * slider)

        if not hasattr(self, "prev_cutoff"):
            self.prev_cutoff = target_cut
        self.prev_cutoff = (1 - smoothing) * self.prev_cutoff + smoothing * target_cut

        combined_wave = final_lowpass(combined_wave,
                                      cutoff=self.prev_cutoff,
                                      fs=self.sample_rate,
                                      order=4)

        # --- 2) 10 ms fade-out ----------------------------------------
        fade_samp = int(0.01 * self.sample_rate)
        if fade_samp > 0 and len(combined_wave) > fade_samp:
            combined_wave[-fade_samp:] *= np.linspace(1.0, 0.0, fade_samp)

        # --- 3) Global EQ ---------------------------------------------
        combined_wave = apply_global_eq_to_array(combined_wave, slider)

        # --- 4) Limiter & RMS normalisation ---------------------------
        combined_wave = np.clip(combined_wave, -0.95, 0.95)

        def _norm_rms(buf: np.ndarray,
                      target_rms: float = 0.1,
                      eps: float = 1e-8) -> np.ndarray:
            rms = np.sqrt(np.mean(buf ** 2)) + eps
            return buf * (target_rms / rms)

        combined_wave = _norm_rms(combined_wave)

        # --- 5) Master volume ----------------------------------------
        combined_wave *= self.master_volume

        return combined_wave

    # Actually Create The Note
    def render_note(self, midi_note, duration):
        freq = freq_from_midi(midi_note)
        total_samples = int(self.sample_rate * duration)
        if total_samples <= 0:
            return np.array([], dtype=np.float32)

        # Generate and mix oscillators (FM + Sample) and obtain LFO
        combined_wave, lfo_wave = self._generate_oscillators(midi_note, duration)

        # Get current slider value for all remaining per-note processing
        with slider_val_lock:
            slider = slider_val

        # ---------- NEW helper handles ADSR + filter chain --------------
        combined_wave = self._apply_envelopes(combined_wave,
                                              duration,
                                              total_samples,
                                              slider)

        # Refresh slider in case it changed during envelope processing
        with slider_val_lock:
            slider = slider_val

        # Apply EFFECTS chain
        combined_wave = self._apply_effects_chain(combined_wave,
                                                  lfo_wave,
                                                  slider)

        # -------------------- FINAL PROCESSING ---------------------------
        combined_wave = self._apply_final_processing(combined_wave, slider)
        return combined_wave

    # Queue Up The Next Note Pattern
    def schedule_pattern(self, base_time, midi_notes, step_duration, delay_pattern_sec):
        with self.lock:
            for i, midi_note in enumerate(midi_notes):
                if midi_note is None:
                    continue
                delay = delay_pattern_sec[i] if i < len(delay_pattern_sec) else 0
                start = base_time + i * step_duration + delay
                self.note_queue.append((start, midi_note, step_duration))

    # Hit It
    def run(self):
        while True:  # Main loop
            now = time.time()
            with self.lock:
                # Play due notes
                for (start_time, midi_note, duration) in self.note_queue:
                    if start_time <= now:
                        wave = self.render_note(midi_note, duration)
                        self.active_notes.append((wave, 0))
                # Remove played notes
                self.note_queue = [n for n in self.note_queue if n[0] > now]

            # Init output buffer
            buffer = np.zeros(self.buffer_size, dtype=np.float32)
            new_active = []
            # Mix active notes
            for wave, idx in self.active_notes:
                end_idx = idx + self.buffer_size
                segment = wave[idx:end_idx]
                buffer[:len(segment)] += segment
                if end_idx < len(wave):
                    new_active.append((wave, end_idx))
            self.active_notes = new_active

            buffer = np.clip(buffer, -1.0, 1.0)  # Clip audio

            # Send to audio
            self.stream.write(buffer.tobytes())

            time.sleep(self.buffer_size / self.sample_rate * 0.01)  # Tiny sleep

# Instantiate Synth
bass_synth = Synth(sample_rate, config=BASS_CONFIG)
bass_synth.set_master_volume(BASS_SYNTH_MASTER_VOLUME)  # From config

        # ===========================================================================#
        #                           G~U~I                                            #
        # ===========================================================================#

# ============================================================================
# GUI CONFIGURATION SECTION –  DEVELOPER-TUNABLE UI CONSTANTS
# ============================================================================

## WINDOW SETTINGS
GUI_WINDOW_TITLE    = "Sequencer BPM Control"
GUI_WINDOW_WIDTH    = 400
GUI_WINDOW_HEIGHT   = 150
GUI_WINDOW_GEOMETRY = f"{GUI_WINDOW_WIDTH}x{GUI_WINDOW_HEIGHT}"

## LABEL SETTINGS
GUI_LABEL_TEXT      = "BPM (log scale)"
GUI_LABEL_PADDING_Y = 10

## SLIDER SETTINGS
GUI_SLIDER_MIN         = 0
GUI_SLIDER_MAX         = 1
GUI_SLIDER_RESOLUTION  = 0.001
GUI_SLIDER_LENGTH_PX   = 300
GUI_SLIDER_ORIENTATION = tk.HORIZONTAL  # Uses tkinter constant

# ============================================================================
# GUI EVENT HANDLERS
# ============================================================================

# Updates global slider value for sequencer
def on_slider_change(val):
    global slider_val
    with slider_val_lock:
        slider_val = float(val)

# ============================================================================
# GUI WINDOW SETUP
# ============================================================================

# Create the Tk root window only once
root = tk.Tk()
root.title(GUI_WINDOW_TITLE)
root.geometry(GUI_WINDOW_GEOMETRY)

# ============================================================================
# GUI CONTROLS CREATION
# ============================================================================

# BPM control label
label = tk.Label(root, text=GUI_LABEL_TEXT)
label.pack(pady=GUI_LABEL_PADDING_Y)

# BPM slider control
slider = tk.Scale(root,
                  from_=GUI_SLIDER_MIN,
                  to=GUI_SLIDER_MAX,
                  resolution=GUI_SLIDER_RESOLUTION,
                  orient=GUI_SLIDER_ORIENTATION,
                  length=GUI_SLIDER_LENGTH_PX,
                  command=on_slider_change)
slider.set(bpm_to_slider(DEFAULT_BPM))
slider.pack()

# ============================================================================
# SEQUENCER THREAD MANAGEMENT
# ============================================================================

# Start sequencer background thread
stop_event = threading.Event()
sequencer_thread = threading.Thread(target=sequencer, args=(stop_event,), daemon=True)
sequencer_thread.start()

# ============================================================================
# WINDOW CLEANUP HANDLING
# ============================================================================

# Clean shutdown when window closes
def on_close():
    stop_event.set()
    sequencer_thread.join()
    # Any other cleanup like pygame.mixer.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# ============================================================================
# GUI MAIN LOOP
# ============================================================================

root.mainloop()
