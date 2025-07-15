"""
Synth Configuration Module

This module contains all configuration constants and parameters for the synthesizer.
These values were extracted from the original ProgrammableSong2.14.py file and
organized into logical groups with documentation and type hints.
"""

from typing import Dict, Any, Union, List, Tuple, Optional
import os

# ============================================================================
# CORE AUDIO SETTINGS
# ============================================================================

# Audio engine configuration
SAMPLE_RATE: int = 44100
FADE_SAMPLES: int = 256
LOOP_FADE_SAMPLES: int = 256
FADE_IN_TIME: int = 10  # ms, for loading sample to avoid clicks
GAIN_SMOOTHING_TIME_SECONDS: float = 0.5
GAIN_NORMALIZATION_CAP: float = 3.0  # Max automatic boost, in ×

# Master volume control (higher = louder)
MASTER_VOLUME: float = 5.0  # 0.1 was the original level; 0.5 ≈ 5× louder

# Sample playback configuration
SAMPLE_LOOP_START_PERCENTAGE: float = 0.26  # 0-1, percent of total way in where loop begins
SAMPLE_LOOP_END_PERCENTAGE: float = 1.0
SAMPLE_BASE_FREQUENCY: float = 32.703

# Default sample path
SAMPLE_PATH: str = (
    "/Users/busterbaer/Desktop/Programmable Song/"
    "ProgrammableLoop2/ProgrammableLoop2BassSynthOscillatorSample.wav"
)

# ============================================================================
# SEQUENCER SETTINGS
# ============================================================================

# BPM and timing settings
MIN_BPM: int = 80
MAX_BPM: int = 180
DEFAULT_BPM: int = 120
BPM_RAMP_MEASURES: int = 1  # how many measures the ramp takes
STEPS_PER_MEASURE: int = 16
GLOBAL_DELAY: float = 0.0
DURATION_MULTIPLIER: float = 0.5
BASE_MIDI_NOTE: int = 36

# ============================================================================
# ADSR ENVELOPE BOUNDS
# ============================================================================

# Amplitude envelope bounds (in seconds, or dB for sustain)
MIN_ATTACK: float = 0.155
MAX_ATTACK: float = 0.018

MIN_DECAY: float = 0.385
MAX_DECAY: float = 60.0

MIN_RELEASE: float = 1.130
MAX_RELEASE: float = 0.1

MIN_SUSTAIN_DB: float = -15.65
MAX_SUSTAIN_DB: float = 0.0

# Oscillator gain bounds
MIN_OSC1_GAIN: float = 1.0  # minimum gain for sine wave
MAX_OSC1_GAIN: float = 0.063  # maximum gain for sine wave

MIN_OSC2_GAIN: float = 0.0  # minimum gain for oscillator 2 (square wave)
MAX_OSC2_GAIN: float = 1.0  # maximum gain for oscillator 2 (square wave)

# FM synthesis bounds
MIN_FM_DEPTH: float = 0.0868
MAX_FM_DEPTH: float = 0.0

# ============================================================================
# FILTER PARAMETER BOUNDS
# ============================================================================

# Filter drive scaling
FILTER_DRIVE_SCALING: float = 4.0
FILTER_ENV_MOD_SCALING: float = 1.5

# Low-pass filter parameters
MIN_FILTER_CUTOFF: float = 20.0  # Hz
MAX_FILTER_CUTOFF: float = 20.0  # Hz

MIN_FILTER_RESONANCE: float = 0.25  # Q-factor
MAX_FILTER_RESONANCE: float = 12.22

MIN_FILTER_DRIVE: float = 0.0  # %
MAX_FILTER_DRIVE: float = 25.6

MIN_FILTER_KEY_TRACK: float = 50.0  # %
MAX_FILTER_KEY_TRACK: float = 50.0

MIN_FILTER_ENV_MOD: float = 12.5  # % (depth of filter envelope modulation)
MAX_FILTER_ENV_MOD: float = 0.0

# ============================================================================
# COMB FILTER PARAMETER BOUNDS
# ============================================================================

# Comb filter configuration
COMB_FILTER_DRIVE_SCALING: float = 4.0
COMB_LIMITER_STRENGTH: float = 0.8
COMB_FEEDBACK_LIMITER: float = 0.95
COMB_MIN_DELAY_MS: float = 1.0  # ms
COMB_MAX_DELAY_MS: float = 50.0  # ms
COMB_FEEDBACK_MAX: float = 0.95
COMB_FEEDBACK_SCALING: float = 15.0
COMB_ENV_MOD_SCALING: float = 1.5  # octaves
COMB_MIN_RESONANCE: float = 0.1

# Comb filter parameter bounds
MIN_COMB_CUTOFF: float = 47.1
MAX_COMB_CUTOFF: float = 39.4

MIN_COMB_RESONANCE: float = 9.68
MAX_COMB_RESONANCE: float = 9.68

MIN_COMB_DRIVE: float = 15.4
MAX_COMB_DRIVE: float = 0

MIN_COMB_KEY_TRACK: float = 78
MAX_COMB_KEY_TRACK: float = 50

MIN_COMB_ENV_MOD: float = 100  # % (depth of filter envelope modulation)
MAX_COMB_ENV_MOD: float = 8.88

# ============================================================================
# GLOBAL FILTER CONTROLS
# ============================================================================

# Global filter controls (affect both filters)
MIN_GLOBAL_CUTOFF: float = 85.64  # Hz (same as individual MIN)
MAX_GLOBAL_CUTOFF: float = 296.4  # Hz (same as individual MAX)

MIN_GLOBAL_RESONANCE: float = 13.61  # Q-factor (same as individual MIN)
MAX_GLOBAL_RESONANCE: float = 0.25  # Q-factor (same as individual MAX)

# ============================================================================
# FILTER ENVELOPE BOUNDS
# ============================================================================

# ADSR parameters for filter envelope
MIN_FILTER_ENV_ATTACK: float = 1.074  # seconds
MAX_FILTER_ENV_ATTACK: float = 0.001  # seconds

MIN_FILTER_ENV_DECAY: float = 0.246  # seconds
MAX_FILTER_ENV_DECAY: float = 1.816  # seconds

MIN_FILTER_ENV_SUSTAIN: float = -50.0  # dB
MAX_FILTER_ENV_SUSTAIN: float = -50.0  # dB (full)

MIN_FILTER_ENV_RELEASE: float = 0.310  # seconds
MAX_FILTER_ENV_RELEASE: float = 12.63  # seconds

# ============================================================================
# LFO PARAMETER BOUNDS
# ============================================================================

# LFO rate, depth, and level bounds
MIN_LFO_RATE: float = 3.22  # Hz
MAX_LFO_RATE: float = 5.98  # Hz

MIN_LFO_DEPTH: float = 3.81  # %
MAX_LFO_DEPTH: float = 6.18  # %

MIN_LFO_LEVEL: float = 100  # %
MAX_LFO_LEVEL: float = 0.0  # %

# ============================================================================
# TUBE DRIVER PARAMETER BOUNDS
# ============================================================================

# Tube driver configuration
TUBE_BYPASS_THRESHOLD: float = 0.01
TUBE_DRIVE_SCALING: float = 3.0
TUBE_CUBIC_COEFF: float = 0.33
TUBE_QUINTIC_COEFF: float = 0.05
TUBE_INTENSITY_SCALING: float = 2.0

# Tube driver parameter bounds (all values as percent 0-100)
MIN_TUBE_AMOUNT: float = 0.0  # overall drive amount
MAX_TUBE_AMOUNT: float = 78.5

MIN_TUBE_MIN_MIX: float = 12.8  # dry/wet mix when input is quiet
MAX_TUBE_MIN_MIX: float = 0.0

MIN_TUBE_MAX_MIX: float = 87.4  # dry/wet mix when input is hot
MAX_TUBE_MAX_MIX: float = 100.0

# ============================================================================
# BITCRUSHER PARAMETER BOUNDS
# ============================================================================

# Bitcrusher configuration
BITCRUSHER_BYPASS_THRESHOLD: float = 0.01
BITCRUSHER_MAX_DEPTH: float = 16.0
BITCRUSHER_MIN_DEPTH: float = 1.0
BITCRUSHER_DITHER_THRESHOLD: float = 8.0
BITCRUSHER_MIX_SCALE_THRESHOLD: float = 4.0

# Bitcrusher parameter bounds
MIN_BIT_DEPTH: float = 16.0  # bits (cleanest)
MAX_BIT_DEPTH: float = 12.0  # bits (moderately crushed)

MIN_BIT_MIX: float = 0.0  # % dry
MAX_BIT_MIX: float = 5.0  # % wet

# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

# Pattern labels
PATTERN_LABELS: List[str] = [
    "SadLevel8", "SadLevel7", "SadLevel6", "SadLevel5",
    "SadLevel4", "SadLevel3", "SadLevel2", "SadLevel1", 
    "Neutral",
    "HappyLevel1", "HappyLevel2", "HappyLevel3", "HappyLevel4",
    "HappyLevel5", "HappyLevel6", "HappyLevel7", "HappyLevel8"
]

# Bass patterns (musical sequences)
BASS_PATTERNS: List[List[Union[str, int]]] = [
    ['1','c','c','c',  'c','c','c','c', '1','c','c','c', 'c','c','c','c', ],  # SadLevel8
    ['1','c','c','c', 'c','c','c','c', 'b3','c','c','c', 'c','c','c','c', ],
    ['1','c','c','c', '1','c','c','c', 'b3','c','c','c', 'b3','c','c','c', ],
    ['1','c','c','c', '1','c','c','c', '5','c','c','c', 'b3','c','c','c', ],
    ['1','c','c',0, '1','c','c',0, '5','c','c',0, 'b3','c','c',0, ],
    ['1','c','c',0, 'b3','c','c',0, '5','c','c',0, 'b3','c','c',0, ],
    ['1','c','1','c', 'b3','c','c',0, '5','c',0,'5', 'b3',0,0,0, ],
    ['1','c','1',0, 'b3','c','b3',0, '5','c','5',0, 'b3','c','b3',0, ],
    ['1','c','1',0, '3','c','3',0, '5','c','5',0, '3','c','3',0, ],  # Neutral
    ['1','c','-7',0, '-7',0,'1','1', 'c',0,'2',0, '-7',0,'-7',0, ],
    ['1','c','-b7',0, '1','c','2',0, '3','c','3',0, '1','c','1',0, ],
    ['1','c','-b7',0, '2','c','3',0, '5','c','4',0, '2','c','2',0, ],
    ['1','c','-7',0, '-6',0,'-7','1', 'c',0,'1',0, '-6',0,'-6',0, ],
    ['1','c','-6',0, '-5',0,'-6','1', 'c','1','-6',0, '-5',0,'-6',0, ],
    ['1',0,'-6',0, '-5',0,'-6','1', 0,0,'-6',0, '-5',0,'-6',0, ],
    ['1','c',0,0, '-5',0,'-6',0, '1',0,0,'-4', '-5',0,'-5',0, ],
    ['1',0,0,0,  '-5',0,0,0, '1',0,0,'-4', '-#4',0,'-5',0, ],  # HappyLevel8
]

# Interval to semitone mapping for musical patterns
INTERVAL_TO_SEMITONE: Dict[str, int] = {
    # Below-tonic (negative) degrees
    '-1': -12, '-b2': -11, '-2': -10, '-b3': -9,  '-3': -8,  '-4': -7,
    '-#4': -6, '-b5': -6,  '-5': -5,  '-b6': -4,  '-6': -3,  '-b7': -2,
    '-7': -1,
    # Tonic and above
    '1': 0, 'b2': 1, '2': 2, 'b3': 3, '3': 4, '4': 5, '#4': 6, 'b5': 6,
    '5': 7, 'b6': 8, '6': 9, 'b7': 10, '7': 11, '8': 12
}

# ============================================================================
# DEFAULT SYNTH CONFIGURATIONS
# ============================================================================

# Create preset configurations for different synth types
DEFAULT_BASS_CONFIG: Dict[str, Any] = {
    'sample_rate': SAMPLE_RATE,
    'master_volume': 0.5,
    'attack': 0.01,
    'decay': 0.2,
    'sustain': -6.0,
    'release': 0.3,
    'sine_gain': 0.2,
    'square_gain': 0.8,
    'fm_depth': 0.0,
    'filter_cutoff': 500.0,
    'filter_resonance': 1.0,
    'filter_drive': 10.0,
    'filter_key_tracking': 50.0,
    'filter_env_mod': 30.0,
    'filter_env_attack': 0.001,
    'filter_env_decay': 0.5,
    'filter_env_sustain': -20.0,
    'filter_env_release': 0.3,
}

DEFAULT_LEAD_CONFIG: Dict[str, Any] = {
    'sample_rate': SAMPLE_RATE,
    'master_volume': 0.4,
    'attack': 0.02,
    'decay': 0.1,
    'sustain': -3.0,
    'release': 0.2,
    'sine_gain': 0.7,
    'square_gain': 0.3,
    'fm_depth': 0.02,
    'filter_cutoff': 2000.0,
    'filter_resonance': 3.0,
    'filter_drive': 20.0,
    'filter_key_tracking': 80.0,
    'filter_env_mod': 50.0,
    'filter_env_attack': 0.01,
    'filter_env_decay': 0.3,
    'filter_env_sustain': -10.0,
    'filter_env_release': 0.2,
    'lfo_rate': 4.5,
    'lfo_depth': 5.0,
    'lfo_level': 30.0,
}

DEFAULT_PAD_CONFIG: Dict[str, Any] = {
    'sample_rate': SAMPLE_RATE,
    'master_volume': 0.3,
    'attack': 0.5,
    'decay': 1.0,
    'sustain': -6.0,
    'release': 1.5,
    'sine_gain': 0.5,
    'square_gain': 0.5,
    'fm_depth': 0.01,
    'filter_cutoff': 800.0,
    'filter_resonance': 0.5,
    'filter_drive': 5.0,
    'filter_key_tracking': 30.0,
    'filter_env_mod': 20.0,
    'filter_env_attack': 0.8,
    'filter_env_decay': 1.2,
    'filter_env_sustain': -15.0,
    'filter_env_release': 2.0,
    'lfo_rate': 0.5,
    'lfo_depth': 10.0,
    'lfo_level': 50.0,
}

# Function to get a configuration by name
def get_preset_config(preset_name: str) -> Dict[str, Any]:
    """
    Get a preset configuration by name.
    
    Args:
        preset_name: The name of the preset configuration.
        
    Returns:
        A dictionary containing the preset configuration.
    """
    presets = {
        'bass': DEFAULT_BASS_CONFIG,
        'lead': DEFAULT_LEAD_CONFIG,
        'pad': DEFAULT_PAD_CONFIG,
    }
    
    return presets.get(preset_name.lower(), DEFAULT_BASS_CONFIG)
