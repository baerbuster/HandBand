# g++ -std=c++17 -fPIC -shared synthlib.cpp -o libsynth.so -I/opt/homebrew/opt/portaudio/include -I/opt/homebrew/opt/libsndfile/include -L/opt/homebrew/opt/portaudio/lib -L/opt/homebrew/opt/libsndfile/lib -lportaudio -lsndfile -pthread

# Undo Flag

#===========================#
#       IMPORTS             #
#===========================#

import ctypes
import time
import threading
import tkinter as tk
import math

        #==================================================================#
        #------------------C-O-N-F-I-G-U-R-A-B-L-E-S-----------------------#
        #==================================================================#

# -------------------------- MASTER VOLUME CONTROLS ------------------------
bass_master_volume = 5.0
piano_master_volume = 1.0

# -------------------------- GENERAL CONTROLS ------------------------------
SAMPLE_RATE = 44100
MIN_BPM = 80
MAX_BPM = 180
DEFAULT_BPM = 120
BPM_RAMP_MEASURES = 1  # how many measures the ramp takes
STEPS_PER_MEASURE = 16

# ------------------------------------------------------------
# PATTERN DICTIONARIES
# ------------------------------------------------------------

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
    #['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c','c','c', ]
]

PIANO_PATTERNS = [
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
    ['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c',0,0, ],
]

# At the global level, after your existing BASS_PATTERNS definition
PATTERN_SETS = {
    "bass": BASS_PATTERNS,
    "piano": PIANO_PATTERNS,
}

# ------------------------------------------------------------
# Synth Configuration Dictionaries
# ------------------------------------------------------------
BASS_CONFIG = {
    "name": "bass",
    "patternSet": "bass",
    "masterVolume": bass_master_volume,
    "durationMultiplier": 0.5,
    "min_osc1_gain": 1.0,
    "max_osc1_gain": 0.063,
    "min_osc2_gain": 0.0,
    "max_osc2_gain": 1.0,
    "sampleLoopStartPercentage": 0.26,
    "sampleLoopEndPercentage": 1.0,
    "sampleBaseFrequency": 32.703,
    "samplePath": "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/ProgrammableLoop2BassSynthOscillatorSample.wav",
    "baseMidiNote": 36,
    "patternIndex": 0,
    "noteIsPlaying": False,
    # ADSR bounds
    "minAttack": 0.155,
    "maxAttack": 0.018,
    "minDecay": 0.385,
    "maxDecay": 60.0,
    "minSustainDb": -15.65,
    "maxSustainDb": 0.0,
    "minRelease": 1.130,
    "maxRelease": 0.1,
    # FM-depth bounds
    "minFmDepth": 0.0868,
    "maxFmDepth": 0.0,
    # LFO Params
    "min_LFO_rate": 3.22,
    "max_LFO_rate": 5.98,
    "min_LFO_depth": 3.81,
    "max_LFO_depth": 6.18,
    "min_LFO_Level": 100.0,
    "max_LFO_Level": 0.0,
    # Tube Driver parameters
    "min_tube_amount": 0.0,
    "max_tube_amount": 78.5,
    "min_tube_min_mix": 12.8,
    "max_tube_min_mix": 0.0,
    "min_tube_max_mix": 87.4,
    "max_tube_max_mix": 100.0,
    # Bitcrusher parameters
    "min_bit_depth": 16.0,
    "max_bit_depth": 12.0,
    "min_bit_mix": 0.0,
    "max_bit_mix": 5.0,
    # Filter parameters
    "min_filter_cutoff": 20.0,
    "max_filter_cutoff": 20.0,
    "min_filter_resonance": 0.25,
    "max_filter_resonance": 12.22,
    "min_filter_drive": 0.0,
    "max_filter_drive": 25.6,
    "min_filter_key_track": 50.0,
    "max_filter_key_track": 50.0,
    "min_filter_env_mod": 12.5,
    "max_filter_env_mod": 0.0,
    # Comb filter parameters
    "min_comb_cutoff": 47.1,
    "max_comb_cutoff": 39.4,
    "min_comb_resonance": 9.68,
    "max_comb_resonance": 9.68,
    "min_comb_drive": 15.4,
    "max_comb_drive": 0.0,
    "min_comb_key_track": 78.0,
    "max_comb_key_track": 50.0,
    "min_comb_env_mod": 100.0,
    "max_comb_env_mod": 8.88,
    # Global filter parameters
    "min_global_cutoff": 85.64,
    "max_global_cutoff": 296.4,
    "min_global_resonance": 13.61,
    "max_global_resonance": 0.25,
    # Filter envelope parameters
    "min_filter_env_attack": 1.074,
    "max_filter_env_attack": 0.001,
    "min_filter_env_decay": 0.246,
    "max_filter_env_decay": 1.816,
    "min_filter_env_sustain": -50.0,
    "max_filter_env_sustain": -50.0,
    "min_filter_env_release": 0.310,
    "max_filter_env_release": 12.63,
}

PIANO_CONFIG = {
    "name": "piano",
    "patternSet": "piano",
    "masterVolume": piano_master_volume,
    "durationMultiplier": 0.5,
    "min_osc1_gain": 1.0,
    "max_osc1_gain": 1.0,
    "min_osc2_gain": 0.0,
    "max_osc2_gain": 0.0,
    "sampleLoopStartPercentage": 0.0,
    "sampleLoopEndPercentage": 1.0,
    "sampleBaseFrequency": 0.0,
    "samplePath": None,
    "baseMidiNote": 60,
    "patternIndex": 0,
    "noteIsPlaying": False,
    # ADSR bounds
    "minAttack": 0.001,
    "maxAttack": 0.001,
    "minDecay": 3.56,
    "maxDecay": 3.56,
    "minSustainDb": 0.0,
    "maxSustainDb": 0.0,
    "minRelease": 0.33,
    "maxRelease": 0.33,
    # FM-depth bounds
    "minFmDepth": 0.0,
    "maxFmDepth": 0.0,
    # LFO Params
    "min_LFO_rate": 0.01,
    "max_LFO_rate": 0.01,
    "min_LFO_depth": 0.01,
    "max_LFO_depth": 0.01,
    "min_LFO_Level": 0.0,
    "max_LFO_Level": 0.0,
    # Tube Driver parameters
    "min_tube_amount": 0.0,
    "max_tube_amount": 0.0,
    "min_tube_min_mix": 0.0,
    "max_tube_min_mix": 0.0,
    "min_tube_max_mix": 0.0,
    "max_tube_max_mix": 0.0,
    # Bitcrusher parameters
    "min_bit_depth": 16.0,
    "max_bit_depth": 16.0,
    "min_bit_mix": 0.0,
    "max_bit_mix": 0.0,
    # Filter parameters
    "min_filter_cutoff": 2000.0,
    "max_filter_cutoff": 2000.0,
    "min_filter_resonance": 0.25,
    "max_filter_resonance": 0.25,
    "min_filter_drive": 0.0,
    "max_filter_drive": 0.0,
    "min_filter_key_track": 0.0,
    "max_filter_key_track": 0.0,
    "min_filter_env_mod": 0.0,
    "max_filter_env_mod": 0.0,
    # Comb filter parameters
    "min_comb_cutoff": 2000.0,
    "max_comb_cutoff": 2000.0,
    "min_comb_resonance": 0.01,
    "max_comb_resonance": 0.01,
    "min_comb_drive": 0.0,
    "max_comb_drive": 0.0,
    "min_comb_key_track": 0.0,
    "max_comb_key_track": 0.0,
    "min_comb_env_mod": 0.0,
    "max_comb_env_mod": 0.0,
    # Global filter parameters
    "min_global_cutoff": 125.0,
    "max_global_cutoff": 125.0,
    "min_global_resonance": 0.25,
    "max_global_resonance": 0.25,
    # Filter envelope parameters
    "min_filter_env_attack": 0.01,
    "max_filter_env_attack": 0.01,
    "min_filter_env_decay": 0.05,
    "max_filter_env_decay": 0.05,
    "min_filter_env_sustain": -20.0,
    "max_filter_env_sustain": -20.0,
    "min_filter_env_release": 0.300,
    "max_filter_env_release": 0.300,
}

        #==================================================================#
        #--------------U-T-I-L-I-T-Y---V-A-R-I-A-B-L-E-S-------------------#
        #==================================================================#

GLOBAL_DELAY = 0.0 # Delays start of program, incase of buffer problems
FADE_SAMPLES = 256 # Prevents audio clicks during transitions
FADE_IN_TIME = 10 # ms, for loading sample to avoid clicks
GAIN_SMOOTHING_TIME_SECONDS = 0.5 # Smooths parameter value transitions
LOOP_FADE_SAMPLES = 256 # Loop-fade length for sample looping (in samples)

# Thresholds, parameter bounds
GAIN_NORMALIZATION_CAP = 3.0
COMB_MIN_DELAY_MS      = 1.0 # ms
COMB_MAX_DELAY_MS      = 50.0 # ms
COMB_FEEDBACK_MAX      = 0.95
COMB_FEEDBACK_LIMITER  = 0.95
COMB_MIN_RESONANCE     = 0.1
TUBE_BYPASS_THRESHOLD = 0.01
BITCRUSHER_BYPASS_THRESHOLD = 0.01
BITCRUSHER_MAX_DEPTH = 16.0
BITCRUSHER_MIN_DEPTH = 1.0
BITCRUSHER_DITHER_THRESHOLD = 8.0
BITCRUSHER_MIX_SCALE_THRESHOLD = 4.0

# Scaling, intensity of parameter
FILTER_DRIVE_SCALING = 4.0
COMB_FILTER_DRIVE_SCALING = 4.0
COMB_LIMITER_STRENGTH = 0.8
COMB_FEEDBACK_SCALING  = 15.0
COMB_ENV_MOD_SCALING   = 1.5
COMB_FEEDBACK_SCALING  = 15.0
FILTER_ENV_MOD_SCALING = 1.5
TUBE_DRIVE_SCALING = 3.0
TUBE_INTENSITY_SCALING = 2.0

TUBE_CUBIC_COEFF = 0.33
TUBE_QUINTIC_COEFF = 0.05

SYNTH_INSTANCES = {}  # Will store SynthInstance objects keyed by synth_id
synth_id = None # Global variable to store the synthesizer ID

# Locking Mechanisms
slider_val_lock = threading.Lock()
bpm_lock = threading.Lock()

# Mutable runtime state ------------------------------------------------------
current_bpm: float        = DEFAULT_BPM        # updated continuously
slider_val:  float        = 0.5                # GUI slider position (0–1)
current_pattern_index: int  = 8                  # 8 = "Neutral" starting pattern
steps_per_measure: int    = STEPS_PER_MEASURE
previous_slider_val: float = 0.5               # Track previous slider value for change detection

# ------------------------------------------------------------
# RAMP BOOKKEEPING
# ------------------------------------------------------------

# ----------------------- Tempo-ramp bookkeeping --------------------
start_bpm:       float | None = DEFAULT_BPM
target_bpm:      float | None = DEFAULT_BPM
ramp_start_time: float | None = None
ramp_duration: float | None = None
start_attack = {}
target_attack = {}
start_decay = {}
target_decay = {}
start_release = {}
target_release = {}
start_sustain = {}
target_sustain = {}
start_sine_gain = {}
target_sine_gain = {}
start_square_gain = {}
target_square_gain = {}
start_fm_depth = {}
target_fm_depth = {}

# ----------------------- FILTER-PARAMETER RAMP BOOKKEEPING --------------------
start_filter_cutoff = {}
target_filter_cutoff = {}
start_filter_resonance = {}
target_filter_resonance = {}
start_filter_drive = {}
target_filter_drive = {}
start_filter_key_track = {}
target_filter_key_track = {}
start_filter_env_mod = {}
target_filter_env_mod = {}

# ----------------------- COMB-FILTER RAMP BOOKKEEPING --------------------
start_comb_cutoff = {}
target_comb_cutoff = {}
start_comb_resonance = {}
target_comb_resonance = {}
start_comb_drive = {}
target_comb_drive = {}
start_comb_key_track = {}
target_comb_key_track = {}
start_comb_env_mod = {}
target_comb_env_mod = {}

# ----------------------- GLOBAL-FILTER RAMP BOOKKEEPING --------------------
start_global_cutoff = {}
target_global_cutoff = {}
start_global_resonance = {}
target_global_resonance = {}

# ----------------------- FILTER-ENVELOPE RAMP BOOKKEEPING --------------------
start_filter_env_attack = {}
target_filter_env_attack = {}
start_filter_env_decay = {}
target_filter_env_decay = {}
start_filter_env_sustain = {}
target_filter_env_sustain = {}
start_filter_env_release = {}
target_filter_env_release = {}

# ----------------------- LFO PARAMETER RAMP BOOKKEEPING --------------------
start_lfo_rate = {}
target_lfo_rate = {}
start_lfo_depth = {}
target_lfo_depth = {}
start_lfo_level = {}
target_lfo_level = {}

# ----------------------- TUBE DRIVER PARAMETER RAMP BOOKKEEPING --------------
start_tube_amount = {}
target_tube_amount = {}
start_tube_min_mix = {}
target_tube_min_mix = {}
start_tube_max_mix = {}
target_tube_max_mix = {}

# ----------------------- BITCRUSHER PARAMETER RAMP BOOKKEEPING --------------
start_bit_depth = {}
target_bit_depth = {}
start_bit_mix = {}
target_bit_mix = {}


#==================================
#       Synth Config Class        #
#==================================

class SynthConfig:
    """
    Configuration container for synthesizer instances.
    Loads values from a configuration dictionary.
    """

    def __init__(self, config_dict=None):
        """
        Initialize a SynthConfig object from a configuration dictionary.
        If no dictionary is provided, default values will be used.
        """
        if config_dict is None:
            config_dict = BASS_CONFIG  # Use bass config as default

        self.patternSet = config_dict.get("patternSet", "bass")

        # Basic synth parameters
        self.name = config_dict.get("name", "default")
        self.masterVolume = config_dict.get("masterVolume", 5.0)
        self.durationMultiplier = config_dict.get("durationMultiplier", 1.0)
        
        # Oscillator gains
        self.minOsc1Gain = config_dict.get("min_osc1_gain", 1.0)
        self.maxOsc1Gain = config_dict.get("max_osc1_gain", 0.063)
        self.minOsc2Gain = config_dict.get("min_osc2_gain", 0.0)
        self.maxOsc2Gain = config_dict.get("max_osc2_gain", 1.0)
        
        # Sample parameters
        self.sampleLoopStartPercentage = config_dict.get("sampleLoopStartPercentage", 0.26)
        self.sampleLoopEndPercentage = config_dict.get("sampleLoopEndPercentage", 1.0)
        self.sampleBaseFrequency = config_dict.get("sampleBaseFrequency", 32.703)
        self.samplePath = config_dict.get("samplePath", "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/ProgrammableLoop2BassSynthOscillatorSample.wav")
        
        # Sequencer parameters
        self.baseMidiNote = config_dict.get("baseMidiNote", 36)
        self.patternIndex = config_dict.get("patternIndex", 0)
        self.noteIsPlaying = config_dict.get("noteIsPlaying", False)
        
        # ADSR bounds
        self.minAttack = config_dict.get("minAttack", 0.155)
        self.maxAttack = config_dict.get("maxAttack", 0.018)
        self.minDecay = config_dict.get("minDecay", 0.385)
        self.maxDecay = config_dict.get("maxDecay", 60.0)
        self.minSustainDb = config_dict.get("minSustainDb", -15.65)
        self.maxSustainDb = config_dict.get("maxSustainDb", 0.0)
        self.minRelease = config_dict.get("minRelease", 1.130)
        self.maxRelease = config_dict.get("maxRelease", 0.1)
        
        # FM-depth bounds
        self.minFmDepth = config_dict.get("minFmDepth", 0.0868)
        self.maxFmDepth = config_dict.get("maxFmDepth", 0.0)

        # Filter parameters
        self.minFilterCutoff = config_dict.get("min_filter_cutoff", 20.0)
        self.maxFilterCutoff = config_dict.get("max_filter_cutoff", 20.0)
        self.minFilterResonance = config_dict.get("min_filter_resonance", 0.25)
        self.maxFilterResonance = config_dict.get("max_filter_resonance", 12.22)
        self.minFilterDrive = config_dict.get("min_filter_drive", 0.0)
        self.maxFilterDrive = config_dict.get("max_filter_drive", 25.6)
        self.minFilterKeyTrack = config_dict.get("min_filter_key_track", 50.0)
        self.maxFilterKeyTrack = config_dict.get("max_filter_key_track", 50.0)
        self.minFilterEnvMod = config_dict.get("min_filter_env_mod", 12.5)
        self.maxFilterEnvMod = config_dict.get("max_filter_env_mod", 0.0)
        
        # Comb filter parameters
        self.minCombCutoff = config_dict.get("min_comb_cutoff", 47.1)
        self.maxCombCutoff = config_dict.get("max_comb_cutoff", 39.4)
        self.minCombResonance = config_dict.get("min_comb_resonance", 9.68)
        self.maxCombResonance = config_dict.get("max_comb_resonance", 9.68)
        self.minCombDrive = config_dict.get("min_comb_drive", 15.4)
        self.maxCombDrive = config_dict.get("max_comb_drive", 0.0)
        self.minCombKeyTrack = config_dict.get("min_comb_key_track", 78.0)
        self.maxCombKeyTrack = config_dict.get("max_comb_key_track", 50.0)
        self.minCombEnvMod = config_dict.get("min_comb_env_mod", 100.0)
        self.maxCombEnvMod = config_dict.get("max_comb_env_mod", 8.88)
        
        # Global filter parameters
        self.minGlobalCutoff = config_dict.get("min_global_cutoff", 85.64)
        self.maxGlobalCutoff = config_dict.get("max_global_cutoff", 296.4)
        self.minGlobalResonance = config_dict.get("min_global_resonance", 13.61)
        self.maxGlobalResonance = config_dict.get("max_global_resonance", 0.25)
        
        # Filter envelope parameters
        self.minFilterEnvAttack = config_dict.get("min_filter_env_attack", 1.074)
        self.maxFilterEnvAttack = config_dict.get("max_filter_env_attack", 0.001)
        self.minFilterEnvDecay = config_dict.get("min_filter_env_decay", 0.246)
        self.maxFilterEnvDecay = config_dict.get("max_filter_env_decay", 1.816)
        self.minFilterEnvSustain = config_dict.get("min_filter_env_sustain", -50.0)
        self.maxFilterEnvSustain = config_dict.get("max_filter_env_sustain", -50.0)
        self.minFilterEnvRelease = config_dict.get("min_filter_env_release", 0.310)
        self.maxFilterEnvRelease = config_dict.get("max_filter_env_release", 12.63)
        
        # LFO parameters
        self.minLFOrate = config_dict.get("min_LFO_rate", 3.22)
        self.maxLFOrate = config_dict.get("max_LFO_rate", 5.98)
        self.minLFOdepth = config_dict.get("min_LFO_depth", 3.81)
        self.maxLFOdepth = config_dict.get("max_LFO_depth", 6.18)
        self.minLFOLevel = config_dict.get("min_LFO_Level", 100.0)
        self.maxLFOLevel = config_dict.get("max_LFO_Level", 0.0)
        
        # Tube Driver parameters
        self.minTubeAmount = config_dict.get("min_tube_amount", 0.0)
        self.maxTubeAmount = config_dict.get("max_tube_amount", 78.5)
        self.minTubeMinMix = config_dict.get("min_tube_min_mix", 12.8)
        self.maxTubeMinMix = config_dict.get("max_tube_min_mix", 0.0)
        self.minTubeMaxMix = config_dict.get("min_tube_max_mix", 87.4)
        self.maxTubeMaxMix = config_dict.get("max_tube_max_mix", 100.0)
        
        # Bitcrusher parameters
        self.minBitDepth = config_dict.get("min_bit_depth", 16.0)
        self.maxBitDepth = config_dict.get("max_bit_depth", 12.0)
        self.minBitMix = config_dict.get("min_bit_mix", 0.0)
        self.maxBitMix = config_dict.get("max_bit_mix", 5.0)

SYNTH_INSTANCES = {}  # Global registry of all synth instances

# --------------------------------------------------------------------------
#      SynthInstance – wraps one C++ Synthesizer instance with a config
# --------------------------------------------------------------------------
class SynthInstance:
    def __init__(self, config_dict):
        self.config_obj = SynthConfig(config_dict)
        self.config = config_dict
        self.synth_id = synth.create_synth()

        # Register this instance in the global registry
        SYNTH_INSTANCES[self.synth_id] = self

        # Basic sanity check
        if not synth.has_synth(self.synth_id):
            raise RuntimeError(f"Could not create synth instance (id {self.synth_id})")

        # Apply the sample configuration parameters
        synth.set_sample_loop_start_percentage(
            self.config["sampleLoopStartPercentage"],
            self.synth_id
        )
        synth.set_sample_loop_end_percentage(
            self.config["sampleLoopEndPercentage"],
            self.synth_id
        )
        synth.set_sample_base_frequency(
            self.config["sampleBaseFrequency"],
            self.synth_id
        )
        if self.config["samplePath"] is not None:
            synth.set_sample_path(
                self.config["samplePath"].encode("utf-8"),
                self.synth_id
            )
        
        # Apply master volume and oscillator gains
        synth.set_master_volume(self.config["masterVolume"], self.synth_id)
        
        # Set standard DSP parameters
        synth.set_sample_rate(SAMPLE_RATE, self.synth_id)
        synth.set_fade_samples(FADE_SAMPLES, self.synth_id)
        synth.set_fade_in_time(FADE_IN_TIME, self.synth_id)
        synth.set_gain_smoothing_time_seconds(GAIN_SMOOTHING_TIME_SECONDS, self.synth_id)
        synth.set_filter_drive_scaling(FILTER_DRIVE_SCALING, self.synth_id)
        synth.set_comb_filter_drive_scaling(COMB_FILTER_DRIVE_SCALING, self.synth_id)
        synth.set_comb_limiter_strength(COMB_LIMITER_STRENGTH, self.synth_id)
        synth.set_tube_bypass_threshold(TUBE_BYPASS_THRESHOLD, self.synth_id)
        synth.set_tube_drive_scaling(TUBE_DRIVE_SCALING, self.synth_id)
        synth.set_tube_cubic_coeff(TUBE_CUBIC_COEFF, self.synth_id)
        synth.set_tube_quintic_coeff(TUBE_QUINTIC_COEFF, self.synth_id)
        synth.set_tube_intensity_scaling(TUBE_INTENSITY_SCALING, self.synth_id)
        synth.set_bitcrusher_bypass_threshold(BITCRUSHER_BYPASS_THRESHOLD, self.synth_id)
        synth.set_bitcrusher_max_depth(BITCRUSHER_MAX_DEPTH, self.synth_id)
        synth.set_bitcrusher_min_depth(BITCRUSHER_MIN_DEPTH, self.synth_id)
        synth.set_bitcrusher_dither_threshold(BITCRUSHER_DITHER_THRESHOLD, self.synth_id)
        synth.set_bitcrusher_mix_scale_threshold(BITCRUSHER_MIX_SCALE_THRESHOLD, self.synth_id)
        synth.set_filter_env_mod_scaling(FILTER_ENV_MOD_SCALING, self.synth_id)
        
        # Set comb filter parameters
        synth.set_comb_min_delay_ms(COMB_MIN_DELAY_MS, self.synth_id)
        synth.set_comb_max_delay_ms(COMB_MAX_DELAY_MS, self.synth_id)
        synth.set_comb_feedback_max(COMB_FEEDBACK_MAX, self.synth_id)
        synth.set_comb_feedback_scaling(COMB_FEEDBACK_SCALING, self.synth_id)
        synth.set_comb_feedback_limiter(COMB_FEEDBACK_LIMITER, self.synth_id)
        synth.set_comb_env_mod_scaling(COMB_ENV_MOD_SCALING, self.synth_id)
        synth.set_comb_min_resonance(COMB_MIN_RESONANCE, self.synth_id)
        synth.set_gain_normalization_cap(GAIN_NORMALIZATION_CAP, self.synth_id)
        synth.set_loop_fade_samples(LOOP_FADE_SAMPLES, self.synth_id)
        
        # Initialize oscillator gains from slider value 0.5 (neutral)
        slider_val = 0.5
        synth.set_sine_gain(
            slider_to_log_gain(slider_val, self.config["min_osc1_gain"], self.config["max_osc1_gain"]), 
            self.synth_id
        )
        synth.set_square_gain(
            slider_to_log_gain(slider_val, self.config["min_osc2_gain"], self.config["max_osc2_gain"]), 
            self.synth_id
        )
        
        # Initialize ADSR parameters based on neutral slider value
        synth.set_attack(
            slider_to_log_range(slider_val, self.config["minAttack"], self.config["maxAttack"]),
            self.synth_id
        )
        synth.set_decay(
            slider_to_log_range(1 - slider_val, self.config["minDecay"], self.config["maxDecay"]),
            self.synth_id
        )
        synth.set_sustain_level(
            self.config["minSustainDb"] + slider_val * (self.config["maxSustainDb"] - self.config["minSustainDb"]),
            self.synth_id
        )
        synth.set_release(
            slider_to_log_range(1 - slider_val, self.config["minRelease"], self.config["maxRelease"]),
            self.synth_id
        )
        
        # Initialize FM depth
        synth.set_fm_depth(
            slider_to_log_hybrid_range(slider_val, self.config["minFmDepth"], self.config["maxFmDepth"]),
            self.synth_id
        )
        
        # Initialize LFO parameters
        synth.set_lfo_rate(
            self.config["min_LFO_rate"] + slider_val * (self.config["max_LFO_rate"] - self.config["min_LFO_rate"]),
            self.synth_id
        )
        synth.set_lfo_depth(
            self.config["min_LFO_depth"] + slider_val * (self.config["max_LFO_depth"] - self.config["min_LFO_depth"]),
            self.synth_id
        )
        synth.set_lfo_level(
            self.config["min_LFO_Level"] + slider_val * (self.config["max_LFO_Level"] - self.config["min_LFO_Level"]),
            self.synth_id
        )
        
        # Initialize tube driver parameters
        synth.set_tube_amount(
            self.config["min_tube_amount"] + slider_val * (self.config["max_tube_amount"] - self.config["min_tube_amount"]),
            self.synth_id
        )
        synth.set_tube_min_mix(
            self.config["min_tube_min_mix"] + slider_val * (self.config["max_tube_min_mix"] - self.config["min_tube_min_mix"]),
            self.synth_id
        )
        synth.set_tube_max_mix(
            self.config["min_tube_max_mix"] + slider_val * (self.config["max_tube_max_mix"] - self.config["min_tube_max_mix"]),
            self.synth_id
        )
        
        # Initialize bitcrusher parameters
        synth.set_bit_depth(
            self.config["min_bit_depth"] + slider_val * (self.config["max_bit_depth"] - self.config["min_bit_depth"]),
            self.synth_id
        )
        synth.set_bit_mix(
            self.config["min_bit_mix"] + slider_val * (self.config["max_bit_mix"] - self.config["min_bit_mix"]),
            self.synth_id
        )
        
        # Initialize filter parameters
        synth.set_filter_cutoff(
            slider_to_log_range(slider_val, self.config["min_filter_cutoff"], self.config["max_filter_cutoff"]),
            self.synth_id
        )
        synth.set_filter_resonance(
            slider_to_log_range(1 - slider_val, self.config["min_filter_resonance"], self.config["max_filter_resonance"]),
            self.synth_id
        )
        synth.set_filter_drive(
            self.config["min_filter_drive"] + slider_val * (self.config["max_filter_drive"] - self.config["min_filter_drive"]),
            self.synth_id
        )
        synth.set_filter_key_tracking(
            self.config["min_filter_key_track"] + slider_val * (self.config["max_filter_key_track"] - self.config["min_filter_key_track"]),
            self.synth_id
        )
        synth.set_filter_env_mod(
            self.config["min_filter_env_mod"] + slider_val * (self.config["max_filter_env_mod"] - self.config["min_filter_env_mod"]),
            self.synth_id
        )
        
        # Initialize comb filter parameters
        synth.set_comb_cutoff(
            slider_to_log_range(slider_val, self.config["min_comb_cutoff"], self.config["max_comb_cutoff"]),
            self.synth_id
        )
        synth.set_comb_resonance(
            slider_to_log_range(1 - slider_val, self.config["min_comb_resonance"], self.config["max_comb_resonance"]),
            self.synth_id
        )
        synth.set_comb_drive(
            self.config["min_comb_drive"] + slider_val * (self.config["max_comb_drive"] - self.config["min_comb_drive"]),
            self.synth_id
        )
        synth.set_comb_key_tracking(
            self.config["min_comb_key_track"] + slider_val * (self.config["max_comb_key_track"] - self.config["min_comb_key_track"]),
            self.synth_id
        )
        synth.set_comb_env_mod(
            self.config["min_comb_env_mod"] + slider_val * (self.config["max_comb_env_mod"] - self.config["min_comb_env_mod"]),
            self.synth_id
        )
        
        # Initialize global filter parameters
        synth.set_global_cutoff(
            self.config["min_global_cutoff"] + slider_val * (self.config["max_global_cutoff"] - self.config["min_global_cutoff"]),
            self.synth_id
        )
        synth.set_global_resonance(
            self.config["min_global_resonance"] + slider_val * (self.config["max_global_resonance"] - self.config["min_global_resonance"]),
            self.synth_id
        )
        
        # Initialize filter envelope parameters
        synth.set_filter_env_attack(
            slider_to_log_range(slider_val, self.config["min_filter_env_attack"], self.config["max_filter_env_attack"]),
            self.synth_id
        )
        synth.set_filter_env_decay(
            slider_to_log_range(1 - slider_val, self.config["min_filter_env_decay"], self.config["max_filter_env_decay"]),
            self.synth_id
        )
        synth.set_filter_env_sustain(
            self.config["min_filter_env_sustain"] + slider_val * (self.config["max_filter_env_sustain"] - self.config["min_filter_env_sustain"]),
            self.synth_id
        )
        synth.set_filter_env_release(
            slider_to_log_range(1 - slider_val, self.config["min_filter_env_release"], self.config["max_filter_env_release"]),
            self.synth_id
        )
        
        # Start the synth
        synth.start_synth(self.synth_id)

    # Convenience proxy helpers (optional, can be expanded later)
    def note_on(self):  synth.note_on(self.synth_id)
    def note_off(self): synth.note_off(self.synth_id)
    
    # Set frequency method
    def set_frequency(self, freq):
        synth.set_frequency(freq, self.synth_id)

# Load the synth library
synth = ctypes.CDLL('./libsynth.so')

# ============================================================================
# BINDINGS
# ============================================================================

# # ------------------ SYNTH MANAGEMENT BINDINGS -------------------------
synth.initialize_synth_system.argtypes = []
synth.initialize_synth_system.restype = None
synth.create_synth.argtypes = []
synth.create_synth.restype = ctypes.c_int
synth.has_synth.argtypes = [ctypes.c_int]
synth.has_synth.restype = ctypes.c_bool
synth.delete_synth.argtypes = [ctypes.c_int]
synth.delete_synth.restype = ctypes.c_bool
# ------------------ SYNTH LIFECYCLE BINDINGS -------------------------
synth.start_synth.argtypes = [ctypes.c_int]
synth.start_synth.restype = None
synth.note_on.argtypes = [ctypes.c_int]
synth.note_on.restype = None
synth.note_off.argtypes = [ctypes.c_int]
synth.note_off.restype = None
synth.stop_synth.argtypes = [ctypes.c_int]
synth.stop_synth.restype = None
synth.shutdown_synth_system.argtypes = []
synth.shutdown_synth_system.restype = None
# ------------------ CORE AUDIO BINDINGS -------------------------
synth.set_frequency.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_frequency.restype = None
synth.set_sample_rate.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_rate.restype = None
synth.set_gain_smoothing_time_seconds.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_gain_smoothing_time_seconds.restype = None
# ------------------ GAIN NORMALISATION CAP BINDING -------------------------
synth.set_gain_normalization_cap.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_gain_normalization_cap.restype  = None
# ------------------ LOOP-FADE SAMPLE COUNT BINDING -------------------------
synth.set_loop_fade_samples.argtypes = [ctypes.c_uint, ctypes.c_int]
synth.set_loop_fade_samples.restype  = None
synth.set_sample_loop_start_percentage.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_loop_start_percentage.restype = None
synth.set_sample_loop_end_percentage.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_loop_end_percentage.restype = None
# ------------------------ SAMPLE PATH BINDING -------------------------------
synth.set_sample_path.argtypes = [ctypes.c_char_p, ctypes.c_int]   # C-style string and synthId
synth.set_sample_path.restype  = None
synth.set_sample_base_frequency.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_base_frequency.restype = None
synth.set_square_gain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_square_gain.restype = None
synth.set_sine_gain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sine_gain.restype = None
synth.set_fade_samples.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_fade_samples.restype = None
synth.set_fade_in_time.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_fade_in_time.restype = None
# ------------------------ FM BINDINGS -------------------------------
synth.set_fm_depth.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_fm_depth.restype = None
# ------------------------ ADSR BINDINGS -------------------------------
synth.set_attack.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_attack.restype = None
synth.set_decay.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_decay.restype = None
synth.set_sustain_level.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sustain_level.restype = None
synth.set_release.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_release.restype = None
# ------------------------------ FILTER BINDINGS -----------------------------
synth.set_filter_cutoff.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_cutoff.restype  = None
synth.set_filter_resonance.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_resonance.restype  = None
synth.set_filter_drive.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_drive.restype  = None
synth.set_filter_key_tracking.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_key_tracking.restype  = None
synth.set_filter_env_mod.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_env_mod.restype  = None
synth.set_filter_drive_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_drive_scaling.restype = None
# ---------------------- COMB FILTER BINDINGS ------------------------
synth.set_comb_min_delay_ms.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_min_delay_ms.restype  = None
synth.set_comb_max_delay_ms.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_max_delay_ms.restype  = None
synth.set_comb_feedback_max.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_feedback_max.restype  = None
synth.set_comb_feedback_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_feedback_scaling.restype = None
synth.set_comb_feedback_limiter.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_feedback_limiter.restype  = None
synth.set_comb_env_mod_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_env_mod_scaling.restype = None
synth.set_comb_min_resonance.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_min_resonance.restype  = None
synth.set_comb_limiter_strength.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_limiter_strength.restype = None
synth.set_comb_filter_drive_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_filter_drive_scaling.restype = None
synth.set_comb_cutoff.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_cutoff.restype  = None
synth.set_comb_resonance.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_resonance.restype  = None
synth.set_comb_drive.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_drive.restype  = None
synth.set_comb_key_tracking.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_key_tracking.restype  = None
synth.set_comb_env_mod.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_comb_env_mod.restype  = None
# ---------------------------- GLOBAL BINDINGS -------------------------------
synth.set_global_cutoff.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_global_cutoff.restype  = None
synth.set_global_resonance.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_global_resonance.restype  = None
# ------------------------- FILTER ENVELOPE BINDINGS --------------------------
synth.set_filter_env_attack.argtypes  = [ctypes.c_double, ctypes.c_int]
synth.set_filter_env_attack.restype   = None
synth.set_filter_env_decay.argtypes   = [ctypes.c_double, ctypes.c_int]
synth.set_filter_env_decay.restype    = None
synth.set_filter_env_sustain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_env_sustain.restype  = None
synth.set_filter_env_release.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_env_release.restype  = None
synth.set_filter_env_mod_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_env_mod_scaling.restype = None
# ------------------------ TUBE DRIVER BINDINGS ------------------------------
synth.set_tube_amount.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_amount.restype  = None
synth.set_tube_min_mix.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_min_mix.restype  = None
synth.set_tube_max_mix.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_max_mix.restype  = None
synth.set_tube_intensity_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_intensity_scaling.restype = None
synth.set_tube_quintic_coeff.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_quintic_coeff.restype = None
synth.set_tube_cubic_coeff.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_cubic_coeff.restype = None
synth.set_tube_drive_scaling.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_drive_scaling.restype = None
synth.set_tube_bypass_threshold.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_tube_bypass_threshold.restype = None
# ------------------------ BITCRUSHER BINDINGS ------------------------------
synth.set_bit_depth.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bit_depth.restype  = None
synth.set_bit_mix.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bit_mix.restype  = None
synth.set_bitcrusher_mix_scale_threshold.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bitcrusher_mix_scale_threshold.restype = None
synth.set_bitcrusher_dither_threshold.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bitcrusher_dither_threshold.restype = None
synth.set_bitcrusher_min_depth.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bitcrusher_min_depth.restype = None
synth.set_bitcrusher_max_depth.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bitcrusher_max_depth.restype = None
synth.set_bitcrusher_bypass_threshold.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_bitcrusher_bypass_threshold.restype = None
# ------------------------------ LFO BINDINGS ------------------------------
synth.set_lfo_rate.argtypes  = [ctypes.c_double, ctypes.c_int]
synth.set_lfo_rate.restype   = None
synth.set_lfo_depth.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_lfo_depth.restype  = None
synth.set_lfo_level.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_lfo_level.restype  = None
# ------------------------ MASTER VOLUME BINDING -----------------------------
synth.set_master_volume.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_master_volume.restype  = None

# ============================================================================
# MIDI AND MUSICAL UTILITIES
# ============================================================================

## PATTERN LABELS
PATTERN_LABELS = [
    "SadLevel8", "SadLevel7", "SadLevel6", "SadLevel5",
    "SadLevel4", "SadLevel3", "SadLevel2", "SadLevel1", 
    "Neutral",
    "HappyLevel1", "HappyLevel2", "HappyLevel3", "HappyLevel4",
    "HappyLevel5", "HappyLevel6", "HappyLevel7", "HappyLevel8"
]

# Slider Level Labels
labels = PATTERN_LABELS

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
    global current_bpm, start_bpm, target_bpm, ramp_start_time, ramp_duration
    global start_attack, target_attack
    global start_decay, target_decay
    global start_release, target_release
    global start_sustain, target_sustain
    global start_sine_gain, target_sine_gain
    global start_square_gain, target_square_gain
    global start_fm_depth, target_fm_depth
    # --- filter globals ---
    global start_filter_cutoff,   target_filter_cutoff
    global start_filter_resonance, target_filter_resonance
    global start_filter_drive,    target_filter_drive
    global start_filter_key_track, target_filter_key_track
    global start_filter_env_mod,  target_filter_env_mod
    # --- comb globals ---
    global start_comb_cutoff,   target_comb_cutoff
    global start_comb_resonance, target_comb_resonance
    global start_comb_drive,    target_comb_drive
    global start_comb_key_track, target_comb_key_track
    global start_comb_env_mod,  target_comb_env_mod
    # --- global filter offsets ---
    global start_global_cutoff, target_global_cutoff
    global start_global_resonance, target_global_resonance
    # --- filter envelope globals ---
    global start_filter_env_attack,  target_filter_env_attack
    global start_filter_env_decay,   target_filter_env_decay
    global start_filter_env_sustain, target_filter_env_sustain
    global start_filter_env_release, target_filter_env_release

    # ------------------------- LFO ramp globals -------------------------
    global start_lfo_rate, target_lfo_rate
    global start_lfo_depth, target_lfo_depth
    global start_lfo_level, target_lfo_level

    # ------------------------ Tube-driver ramp globals ------------------------
    global start_tube_amount, target_tube_amount
    global start_tube_min_mix, target_tube_min_mix
    global start_tube_max_mix, target_tube_max_mix

    # ------------------------ Bitcrusher ramp globals -------------------------
    global start_bit_depth, target_bit_depth
    global start_bit_mix,   target_bit_mix

    with bpm_lock:
        new_target_bpm = slider_to_bpm(slider)

        if new_target_bpm != target_bpm:
            start_bpm        = current_bpm
            target_bpm       = new_target_bpm
            ramp_start_time  = time.time()
            ramp_duration    = (60 / start_bpm) * 4 * BPM_RAMP_MEASURES

        if ramp_start_time and ramp_duration:
            elapsed  = time.time() - ramp_start_time
            progress = min(elapsed / ramp_duration, 1.0)
            current_bpm = start_bpm + (target_bpm - start_bpm) * progress

            # Update ALL synths based on ramp progress
            for current_synth_id in SYNTH_INSTANCES:
                # ADSR parameters
                if current_synth_id in start_attack and current_synth_id in target_attack:
                    synth.set_attack(start_attack[current_synth_id] + (target_attack[current_synth_id] - start_attack[current_synth_id]) * progress, current_synth_id)
                
                if current_synth_id in start_decay and current_synth_id in target_decay:
                    synth.set_decay(start_decay[current_synth_id] + (target_decay[current_synth_id] - start_decay[current_synth_id]) * progress, current_synth_id)
                
                if current_synth_id in start_release and current_synth_id in target_release:
                    synth.set_release(start_release[current_synth_id] + (target_release[current_synth_id] - start_release[current_synth_id]) * progress, current_synth_id)
                
                if current_synth_id in start_sustain and current_synth_id in target_sustain:
                    synth.set_sustain_level(start_sustain[current_synth_id] + (target_sustain[current_synth_id] - start_sustain[current_synth_id]) * progress, current_synth_id)
                
                # Oscillator gains
                if current_synth_id in start_sine_gain and current_synth_id in target_sine_gain:
                    synth.set_sine_gain(start_sine_gain[current_synth_id] + (target_sine_gain[current_synth_id] - start_sine_gain[current_synth_id]) * progress, current_synth_id)
                
                if current_synth_id in start_square_gain and current_synth_id in target_square_gain:
                    synth.set_square_gain(start_square_gain[current_synth_id] + (target_square_gain[current_synth_id] - start_square_gain[current_synth_id]) * progress, current_synth_id)
                
                # FM depth
                if current_synth_id in start_fm_depth and current_synth_id in target_fm_depth:
                    interpolated_fm_depth = start_fm_depth[current_synth_id] + (target_fm_depth[current_synth_id] - start_fm_depth[current_synth_id]) * progress
                    synth.set_fm_depth(interpolated_fm_depth, current_synth_id)

                # ----------------------- LFO parameter ramps -----------------------
                if current_synth_id in start_lfo_rate and current_synth_id in target_lfo_rate:
                    synth.set_lfo_rate(
                        start_lfo_rate[current_synth_id] + (target_lfo_rate[current_synth_id] - start_lfo_rate[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_lfo_depth and current_synth_id in target_lfo_depth:
                    synth.set_lfo_depth(
                        start_lfo_depth[current_synth_id] + (target_lfo_depth[current_synth_id] - start_lfo_depth[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_lfo_level and current_synth_id in target_lfo_level:
                    synth.set_lfo_level(
                        start_lfo_level[current_synth_id] + (target_lfo_level[current_synth_id] - start_lfo_level[current_synth_id]) * progress,
                        current_synth_id
                    )

                # -------------------- filter parameter ramps --------------------
                if current_synth_id in start_filter_cutoff and current_synth_id in target_filter_cutoff:
                    synth.set_filter_cutoff(
                        start_filter_cutoff[current_synth_id] + (target_filter_cutoff[current_synth_id] - start_filter_cutoff[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_resonance and current_synth_id in target_filter_resonance:
                    synth.set_filter_resonance(
                        start_filter_resonance[current_synth_id] + (target_filter_resonance[current_synth_id] - start_filter_resonance[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_drive and current_synth_id in target_filter_drive:
                    synth.set_filter_drive(
                        start_filter_drive[current_synth_id] + (target_filter_drive[current_synth_id] - start_filter_drive[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_key_track and current_synth_id in target_filter_key_track:
                    synth.set_filter_key_tracking(
                        start_filter_key_track[current_synth_id] + (target_filter_key_track[current_synth_id] - start_filter_key_track[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_env_mod and current_synth_id in target_filter_env_mod:
                    synth.set_filter_env_mod(
                        start_filter_env_mod[current_synth_id] + (target_filter_env_mod[current_synth_id] - start_filter_env_mod[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                # -------------------- comb parameter ramps --------------------
                if current_synth_id in start_comb_cutoff and current_synth_id in target_comb_cutoff:
                    synth.set_comb_cutoff(
                        start_comb_cutoff[current_synth_id] + (target_comb_cutoff[current_synth_id] - start_comb_cutoff[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_comb_resonance and current_synth_id in target_comb_resonance:
                    synth.set_comb_resonance(
                        start_comb_resonance[current_synth_id] + (target_comb_resonance[current_synth_id] - start_comb_resonance[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_comb_drive and current_synth_id in target_comb_drive:
                    synth.set_comb_drive(
                        start_comb_drive[current_synth_id] + (target_comb_drive[current_synth_id] - start_comb_drive[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_comb_key_track and current_synth_id in target_comb_key_track:
                    synth.set_comb_key_tracking(
                        start_comb_key_track[current_synth_id] + (target_comb_key_track[current_synth_id] - start_comb_key_track[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_comb_env_mod and current_synth_id in target_comb_env_mod:
                    synth.set_comb_env_mod(
                        start_comb_env_mod[current_synth_id] + (target_comb_env_mod[current_synth_id] - start_comb_env_mod[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                # -------------------- global offset ramps --------------------
                if current_synth_id in start_global_cutoff and current_synth_id in target_global_cutoff:
                    synth.set_global_cutoff(
                        start_global_cutoff[current_synth_id] + (target_global_cutoff[current_synth_id] - start_global_cutoff[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_global_resonance and current_synth_id in target_global_resonance:
                    synth.set_global_resonance(
                        start_global_resonance[current_synth_id] + (target_global_resonance[current_synth_id] - start_global_resonance[current_synth_id]) * progress,
                        current_synth_id
                    )

                # -------------------- filter envelope ramps --------------------
                if current_synth_id in start_filter_env_attack and current_synth_id in target_filter_env_attack:
                    synth.set_filter_env_attack(
                        start_filter_env_attack[current_synth_id] + (target_filter_env_attack[current_synth_id] - start_filter_env_attack[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_env_decay and current_synth_id in target_filter_env_decay:
                    synth.set_filter_env_decay(
                        start_filter_env_decay[current_synth_id] + (target_filter_env_decay[current_synth_id] - start_filter_env_decay[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_env_sustain and current_synth_id in target_filter_env_sustain:
                    synth.set_filter_env_sustain(
                        start_filter_env_sustain[current_synth_id] + (target_filter_env_sustain[current_synth_id] - start_filter_env_sustain[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_filter_env_release and current_synth_id in target_filter_env_release:
                    synth.set_filter_env_release(
                        start_filter_env_release[current_synth_id] + (target_filter_env_release[current_synth_id] - start_filter_env_release[current_synth_id]) * progress,
                        current_synth_id
                    )

                # ----------------------- Tube driver parameter ramps -----------------------
                if current_synth_id in start_tube_amount and current_synth_id in target_tube_amount:
                    synth.set_tube_amount(
                        start_tube_amount[current_synth_id] + (target_tube_amount[current_synth_id] - start_tube_amount[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_tube_min_mix and current_synth_id in target_tube_min_mix:
                    synth.set_tube_min_mix(
                        start_tube_min_mix[current_synth_id] + (target_tube_min_mix[current_synth_id] - start_tube_min_mix[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_tube_max_mix and current_synth_id in target_tube_max_mix:
                    synth.set_tube_max_mix(
                        start_tube_max_mix[current_synth_id] + (target_tube_max_mix[current_synth_id] - start_tube_max_mix[current_synth_id]) * progress,
                        current_synth_id
                    )

                # ----------------------- Bitcrusher parameter ramps -----------------------
                if current_synth_id in start_bit_depth and current_synth_id in target_bit_depth:
                    synth.set_bit_depth(
                        start_bit_depth[current_synth_id] + (target_bit_depth[current_synth_id] - start_bit_depth[current_synth_id]) * progress,
                        current_synth_id
                    )
                
                if current_synth_id in start_bit_mix and current_synth_id in target_bit_mix:
                    synth.set_bit_mix(
                        start_bit_mix[current_synth_id] + (target_bit_mix[current_synth_id] - start_bit_mix[current_synth_id]) * progress,
                        current_synth_id
                    )

            if progress >= 1.0:
                current_bpm     = target_bpm
                start_bpm       = target_bpm
                ramp_start_time = None
                ramp_duration   = None

        return current_bpm

def slider_to_log_range(val: float, min_val: float, max_val: float) -> float:
    if min_val == 0 or max_val == 0:
        raise ValueError("Log mapping requires non-zero min and max.")
    log_min = math.log(min_val)
    log_max = math.log(max_val)
    log_val = log_min + val * (log_max - log_min)
    return math.exp(log_val)

def slider_to_log_hybrid_range(val: float, min_val: float, max_val: float) -> float:
    """
    Convert a slider value (0-1) to a log-scaled parameter value between min_val and max_val.
    Handles special cases where min_val or max_val are zero.
    """
    if val == 0.0 and min_val == 0.0:
        return 0.0
    
    # Handle min_val = 0 case by using a small non-zero value for log scaling
    if min_val == 0:
        small_val = 1e-3
        log_min = math.log(small_val)
    else:
        log_min = math.log(min_val)

    # Handle max_val = 0 case by using a small non-zero value for log scaling
    if val == 1.0 and max_val == 0.0:
        return 0.0
    if max_val == 0.0:
        small_val = 1e-3
        log_max = math.log(small_val)
    else:
        log_max = math.log(max_val)

    log_val = log_min + val * (log_max - log_min)
    return math.exp(log_val)

def slider_to_log_gain(val: float, min_gain: float, max_gain: float) -> float:
    if val == 0.0 and min_gain == 0.0:
        return 0.0  # exact zero only at val = 0
    if min_gain == 0.0:
        # Use a small positive number to approximate zero, but not too small
        small_val = 1e-3
        log_min = math.log(small_val)
    else:
        log_min = math.log(min_gain)

    if val == 1.0 and max_gain == 0.0:
        return 0.0
    if max_gain == 0.0:
        small_val = 1e-3
        log_max = math.log(small_val)
    else:
        log_max = math.log(max_gain)

    log_val = log_min + val * (log_max - log_min)
    return math.exp(log_val)



        #==================================================================#
        #------------------------S~E~Q~U~E~N~C~E~R-------------------------#
        #==================================================================#

def synth_sequencer_thread(stop_event, synth, synth_id, slider_val_lock):
    """Dedicated sequencer thread for a single synth instance."""
    step = 0
    next_trigger = time.time() + GLOBAL_DELAY
    pattern_index = 0
    note_is_playing = False
    current_pattern_index_local = 0
    
    while not stop_event.is_set():
        # Safely get the current slider value
        with slider_val_lock:
            current_slider_val = slider_val
        
        # Convert slider to target pattern index
        target_pattern_index = int(round(current_slider_val * (len(labels) - 1)))
        
        # Update BPM with smooth ramping
        current_bpm = update_bpm_from_slider(current_slider_val)
        seconds_per_beat = 60 / current_bpm
        seconds_per_16th = seconds_per_beat / 4
        
        # Get the synth instance
        synth_instance = SYNTH_INSTANCES[synth_id]

        if hasattr(synth_instance, 'config_obj'):
            duration_multiplier = synth_instance.config_obj.durationMultiplier
        else:
            duration_multiplier = synth_instance.config.get("durationMultiplier", 0.5)
            
        # Try to use the SynthConfig object first, then fall back to dict
        if hasattr(synth_instance, 'config_obj'):
            base_midi_note = synth_instance.config_obj.baseMidiNote
            pattern_set_name = synth_instance.config_obj.patternSet
        else:
            # Fall back to dictionary access
            base_midi_note = synth_instance.config.get("baseMidiNote", 36)
            pattern_set_name = synth_instance.config.get("patternSet", "bass")
        
        # Get the pattern set for this synth
        pattern_set = PATTERN_SETS.get(pattern_set_name, BASS_PATTERNS)  # Fallback to BASS_PATTERNS
        
        # Actual Music Triggers
        now = time.time()
        if now >= next_trigger:
            # Handle pattern change at measure boundary (step == 0)
            if target_pattern_index != current_pattern_index_local and step == 0:
                current_pattern_index_local = target_pattern_index
                # Stop any playing notes on pattern change
                if note_is_playing:
                    synth.note_off(synth_id)
                    note_is_playing = False
            
            # Use this synth's pattern set
            selected_pattern = pattern_set[current_pattern_index_local]
            degree = selected_pattern[pattern_index % len(selected_pattern)]
            next_degree = selected_pattern[(pattern_index + 1) % len(selected_pattern)]
            
            # Note processing logic
            if degree == 0 or (degree == 'c' and next_degree == 'c'):
                if degree == 0 and note_is_playing:
                    synth.note_off(synth_id)
                    note_is_playing = False
                # pass
            elif degree == 'c' and next_degree != 'c':
                time.sleep(seconds_per_16th * duration_multiplier)
                synth.note_off(synth_id)
                note_is_playing = False
            elif degree not in (0, 'c') and next_degree == 'c':
                if isinstance(degree, str) and degree in interval_to_semitone:
                    midi_note = base_midi_note + interval_to_semitone[degree]
                else:
                    midi_note = base_midi_note  # fallback to tonic if malformed
                synth.set_frequency(freq_from_midi(midi_note), synth_id)
                synth.note_on(synth_id)
                note_is_playing = True
            else:
                if isinstance(degree, str) and degree in interval_to_semitone:
                    midi_note = base_midi_note + interval_to_semitone[degree]
                else:
                    midi_note = base_midi_note  # fallback to tonic if malformed
                synth.set_frequency(freq_from_midi(midi_note), synth_id)
                synth.note_on(synth_id)
                note_is_playing = True
                time.sleep(seconds_per_16th * duration_multiplier)
                synth.note_off(synth_id)
                note_is_playing = False
            
            # Increment this synth's pattern index
            pattern_index += 1
            
            # Update step and next trigger time
            step = (step + 1) % STEPS_PER_MEASURE
            next_trigger += seconds_per_16th
        else:
            time.sleep(max(0.001, min(0.01, next_trigger - now)))

def sequencer_timing_only(stop_event, synth, slider_val_lock):
    global current_pattern_index, previous_slider_val, synth_id
    
    # Create a thread for each synth instance
    synth_threads = []
    
    # Start a separate thread for each synth instance
    for current_synth_id in SYNTH_INSTANCES:
        thread = threading.Thread(
            target=synth_sequencer_thread,
            args=(stop_event, synth, current_synth_id, slider_val_lock),
            daemon=True
        )
        thread.start()
        synth_threads.append(thread)
    
    # Main thread now just waits for stop event
    while not stop_event.is_set():
        # Update global pattern index for UI/display purposes if needed
        with slider_val_lock:
            current_slider_val = slider_val
        
        target_pattern_index = int(round(current_slider_val * (len(labels) - 1)))
        if target_pattern_index != current_pattern_index:
            current_pattern_index = target_pattern_index
        
        # Sleep to avoid hogging CPU
        time.sleep(0.1)
    
    # Wait for all threads to finish when stopping
    for thread in synth_threads:
        thread.join(timeout=1.0)

# ============================================================================
# GUI EVENT HANDLERS
# ============================================================================

def on_slider_change(val):
    global slider_val
    global start_attack, target_attack
    global start_decay, target_decay
    global start_release, target_release
    global start_sustain, target_sustain
    global start_sine_gain, target_sine_gain
    global start_square_gain, target_square_gain
    global start_bpm, target_bpm, ramp_start_time, ramp_duration
    global start_fm_depth, target_fm_depth
    # ----------------------- LFO globals -----------------------
    global start_lfo_rate, target_lfo_rate
    global start_lfo_depth, target_lfo_depth
    global start_lfo_level, target_lfo_level
    # --- filter globals ---
    global start_filter_cutoff,   target_filter_cutoff
    global start_filter_resonance, target_filter_resonance
    global start_filter_drive,    target_filter_drive
    global start_filter_key_track, target_filter_key_track
    global start_filter_env_mod,  target_filter_env_mod
    # --- comb globals ---
    global start_comb_cutoff,   target_comb_cutoff
    global start_comb_resonance, target_comb_resonance
    global start_comb_drive,    target_comb_drive
    global start_comb_key_track, target_comb_key_track
    global start_comb_env_mod,  target_comb_env_mod
    # --- global filter offsets ---
    global start_global_cutoff, target_global_cutoff
    global start_global_resonance, target_global_resonance
    # --- filter-envelope globals ---
    global start_filter_env_attack,  target_filter_env_attack
    global start_filter_env_decay,   target_filter_env_decay
    global start_filter_env_sustain, target_filter_env_sustain
    global start_filter_env_release, target_filter_env_release

    # ----------------------- Tube driver globals -----------------------
    global start_tube_amount, target_tube_amount
    global start_tube_min_mix, target_tube_min_mix
    global start_tube_max_mix, target_tube_max_mix

    # ----------------------- Bitcrusher globals -----------------------
    global start_bit_depth, target_bit_depth
    global start_bit_mix,   target_bit_mix
    
    # Access the global synth_id
    global synth_id

    with slider_val_lock:
        new_val = float(val)
        slider_val = new_val

        # Update EVERY synth in the registry
        for current_synth_id, synth_instance in SYNTH_INSTANCES.items():
            config = synth_instance.config

            # ADSR envelope parameters
            target_attack[current_synth_id] = slider_to_log_range(new_val, config["minAttack"], config["maxAttack"])
            target_decay[current_synth_id] = slider_to_log_range(1 - new_val, config["minDecay"], config["maxDecay"])
            target_release[current_synth_id] = slider_to_log_range(1 - new_val, config["minRelease"], config["maxRelease"])
            target_sustain[current_synth_id] = config["minSustainDb"] + new_val * (config["maxSustainDb"] - config["minSustainDb"])

            # Oscillator gains
            target_sine_gain[current_synth_id] = slider_to_log_gain(new_val, config["min_osc1_gain"], config["max_osc1_gain"])
            target_square_gain[current_synth_id] = slider_to_log_gain(new_val, config["min_osc2_gain"], config["max_osc2_gain"])

            # Store start points for ramps
            start_attack[current_synth_id] = target_attack[current_synth_id]
            start_decay[current_synth_id] = target_decay[current_synth_id]
            start_release[current_synth_id] = target_release[current_synth_id]
            start_sustain[current_synth_id] = target_sustain[current_synth_id]
            
            # Immediate update so sustain tracks the slider like other ADSR params
            synth.set_sustain_level(target_sustain[current_synth_id], current_synth_id)
            
            start_sine_gain[current_synth_id] = target_sine_gain[current_synth_id]
            start_square_gain[current_synth_id] = target_square_gain[current_synth_id]

            # FM depth
            target_fm_depth[current_synth_id] = slider_to_log_hybrid_range(new_val, config["minFmDepth"], config["maxFmDepth"])
            start_fm_depth[current_synth_id] = target_fm_depth[current_synth_id]
            synth.set_fm_depth(target_fm_depth[current_synth_id], current_synth_id)  # immediate update

            # --------------------------- LFO TARGETS ---------------------------
            # Rate / Depth / Level scale positively with slider happiness
            target_lfo_rate[current_synth_id] = config["min_LFO_rate"] + new_val * (config["max_LFO_rate"] - config["min_LFO_rate"])
            target_lfo_depth[current_synth_id] = config["min_LFO_depth"] + new_val * (config["max_LFO_depth"] - config["min_LFO_depth"])
            target_lfo_level[current_synth_id] = config["min_LFO_Level"] + new_val * (config["max_LFO_Level"] - config["min_LFO_Level"])

            # Store start points for upcoming ramps
            start_lfo_rate[current_synth_id] = target_lfo_rate[current_synth_id]
            start_lfo_depth[current_synth_id] = target_lfo_depth[current_synth_id]
            start_lfo_level[current_synth_id] = target_lfo_level[current_synth_id]

            # Immediate push to synth so user hears change right away
            synth.set_lfo_rate(target_lfo_rate[current_synth_id], current_synth_id)
            synth.set_lfo_depth(target_lfo_depth[current_synth_id], current_synth_id)
            synth.set_lfo_level(target_lfo_level[current_synth_id], current_synth_id)

            # ---------------------- FILTER PARAMETER TARGETS ---------------------
            # Cutoff: logarithmic, higher at higher slider values
            target_filter_cutoff[current_synth_id] = slider_to_log_range(
                new_val, config["min_filter_cutoff"], config["max_filter_cutoff"]
            )
            # Resonance: logarithmic, higher at LOWER slider values
            target_filter_resonance[current_synth_id] = slider_to_log_range(
                1 - new_val, config["min_filter_resonance"], config["max_filter_resonance"]
            )
            # Drive, Key-tracking, Env-mod: linear 0-100 %
            target_filter_drive[current_synth_id] = config["min_filter_drive"] + new_val * (
                config["max_filter_drive"] - config["min_filter_drive"]
            )
            target_filter_key_track[current_synth_id] = config["min_filter_key_track"] + new_val * (
                config["max_filter_key_track"] - config["min_filter_key_track"]
            )
            target_filter_env_mod[current_synth_id] = config["min_filter_env_mod"] + new_val * (
                config["max_filter_env_mod"] - config["min_filter_env_mod"]
            )

            # Initialize ramp start points
            start_filter_cutoff[current_synth_id] = target_filter_cutoff[current_synth_id]
            start_filter_resonance[current_synth_id] = target_filter_resonance[current_synth_id]
            start_filter_drive[current_synth_id] = target_filter_drive[current_synth_id]
            start_filter_key_track[current_synth_id] = target_filter_key_track[current_synth_id]
            start_filter_env_mod[current_synth_id] = target_filter_env_mod[current_synth_id]

            # Immediate update so changes are audible even before a ramp begins
            synth.set_filter_cutoff(target_filter_cutoff[current_synth_id], current_synth_id)
            synth.set_filter_resonance(target_filter_resonance[current_synth_id], current_synth_id)
            synth.set_filter_drive(target_filter_drive[current_synth_id], current_synth_id)
            synth.set_filter_key_tracking(target_filter_key_track[current_synth_id], current_synth_id)
            synth.set_filter_env_mod(target_filter_env_mod[current_synth_id], current_synth_id)

            # ----------------------- COMB PARAMETER TARGETS ----------------------
            target_comb_cutoff[current_synth_id] = slider_to_log_range(
                new_val, config["min_comb_cutoff"], config["max_comb_cutoff"]
            )
            target_comb_resonance[current_synth_id] = slider_to_log_range(
                1 - new_val, config["min_comb_resonance"], config["max_comb_resonance"]
            )
            target_comb_drive[current_synth_id] = config["min_comb_drive"] + new_val * (
                config["max_comb_drive"] - config["min_comb_drive"]
            )
            target_comb_key_track[current_synth_id] = config["min_comb_key_track"] + new_val * (
                config["max_comb_key_track"] - config["min_comb_key_track"]
            )
            target_comb_env_mod[current_synth_id] = config["min_comb_env_mod"] + new_val * (
                config["max_comb_env_mod"] - config["min_comb_env_mod"]
            )

            start_comb_cutoff[current_synth_id] = target_comb_cutoff[current_synth_id]
            start_comb_resonance[current_synth_id] = target_comb_resonance[current_synth_id]
            start_comb_drive[current_synth_id] = target_comb_drive[current_synth_id]
            start_comb_key_track[current_synth_id] = target_comb_key_track[current_synth_id]
            start_comb_env_mod[current_synth_id] = target_comb_env_mod[current_synth_id]

            synth.set_comb_cutoff(target_comb_cutoff[current_synth_id], current_synth_id)
            synth.set_comb_resonance(target_comb_resonance[current_synth_id], current_synth_id)
            synth.set_comb_drive(target_comb_drive[current_synth_id], current_synth_id)
            synth.set_comb_key_tracking(target_comb_key_track[current_synth_id], current_synth_id)
            synth.set_comb_env_mod(target_comb_env_mod[current_synth_id], current_synth_id)

            # ----------------------- GLOBAL OFFSET TARGETS ----------------------
            target_global_cutoff[current_synth_id] = config["min_global_cutoff"] + new_val * (
                config["max_global_cutoff"] - config["min_global_cutoff"]
            )
            target_global_resonance[current_synth_id] = config["min_global_resonance"] + new_val * (
                config["max_global_resonance"] - config["min_global_resonance"]
            )

            start_global_cutoff[current_synth_id] = target_global_cutoff[current_synth_id]
            start_global_resonance[current_synth_id] = target_global_resonance[current_synth_id]

            synth.set_global_cutoff(target_global_cutoff[current_synth_id], current_synth_id)
            synth.set_global_resonance(target_global_resonance[current_synth_id], current_synth_id)

            # ----------------------- FILTER ENVELOPE TARGETS --------------------
            # Log-scale for A/D/R, linear for sustain (dB) and amount (%)
            target_filter_env_attack[current_synth_id] = slider_to_log_range(
                new_val, config["min_filter_env_attack"], config["max_filter_env_attack"]
            )
            target_filter_env_decay[current_synth_id] = slider_to_log_range(
                1 - new_val, config["min_filter_env_decay"], config["max_filter_env_decay"]
            )
            target_filter_env_sustain[current_synth_id] = config["min_filter_env_sustain"] + new_val * (
                config["max_filter_env_sustain"] - config["min_filter_env_sustain"]
            )
            target_filter_env_release[current_synth_id] = slider_to_log_range(
                1 - new_val, config["min_filter_env_release"], config["max_filter_env_release"]
            )

            # Initialise ramp start points
            start_filter_env_attack[current_synth_id] = target_filter_env_attack[current_synth_id]
            start_filter_env_decay[current_synth_id] = target_filter_env_decay[current_synth_id]
            start_filter_env_sustain[current_synth_id] = target_filter_env_sustain[current_synth_id]
            start_filter_env_release[current_synth_id] = target_filter_env_release[current_synth_id]

            # Immediate update to synth
            synth.set_filter_env_attack(target_filter_env_attack[current_synth_id], current_synth_id)
            synth.set_filter_env_decay(target_filter_env_decay[current_synth_id], current_synth_id)
            synth.set_filter_env_sustain(target_filter_env_sustain[current_synth_id], current_synth_id)
            synth.set_filter_env_release(target_filter_env_release[current_synth_id], current_synth_id)

            # ------------------------ TUBE DRIVER TARGETS -------------------------
            # Amount (drive) grows with slider value
            target_tube_amount[current_synth_id] = config["min_tube_amount"] + new_val * (config["max_tube_amount"] - config["min_tube_amount"])

            # Quiet-level wet-mix falls as slider rises (happier = cleaner on quiet parts)
            target_tube_min_mix[current_synth_id] = config["min_tube_min_mix"] + new_val * (config["max_tube_min_mix"] - config["min_tube_min_mix"])

            # Hot-level wet-mix rises with slider value (more saturation on loud parts)
            target_tube_max_mix[current_synth_id] = config["min_tube_max_mix"] + new_val * (config["max_tube_max_mix"] - config["min_tube_max_mix"])

            # Ramp bookkeeping
            start_tube_amount[current_synth_id] = target_tube_amount[current_synth_id]
            start_tube_min_mix[current_synth_id] = target_tube_min_mix[current_synth_id]
            start_tube_max_mix[current_synth_id] = target_tube_max_mix[current_synth_id]

            # Immediate push so the user hears the change right away
            synth.set_tube_amount(target_tube_amount[current_synth_id], current_synth_id)
            synth.set_tube_min_mix(target_tube_min_mix[current_synth_id], current_synth_id)
            synth.set_tube_max_mix(target_tube_max_mix[current_synth_id], current_synth_id)

            # ------------------------ BITCRUSHER TARGETS --------------------------
            # Bit-depth decreases (toward MAX_BIT_DEPTH which is lower) as slider rises
            target_bit_depth[current_synth_id] = config["min_bit_depth"] + new_val * (config["max_bit_depth"] - config["min_bit_depth"])
            # Mix increases with slider
            target_bit_mix[current_synth_id] = config["min_bit_mix"] + new_val * (config["max_bit_mix"] - config["min_bit_mix"])

            # Ramp bookkeeping
            start_bit_depth[current_synth_id] = target_bit_depth[current_synth_id]
            start_bit_mix[current_synth_id] = target_bit_mix[current_synth_id]

            # Immediate push so the user hears the change right away
            synth.set_bit_depth(target_bit_depth[current_synth_id], current_synth_id)
            synth.set_bit_mix(target_bit_mix[current_synth_id], current_synth_id)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    stop_event = threading.Event()

    # Initialize the synthesizer system
    synth.initialize_synth_system()
    
    bass_synth = SynthInstance(BASS_CONFIG)
    
    piano_synth = SynthInstance(PIANO_CONFIG)

    sequencer_thread = threading.Thread(
        target=sequencer_timing_only,
        args=(stop_event, synth, slider_val_lock),
        daemon=True)
    sequencer_thread.start()

        #==================================================================#
        #-----------------------------G-U-I--------------------------------#
        #==================================================================#


    # GUI window setup and controls
    root = tk.Tk()
    root.title("Sequencer BPM Control")
    root.geometry(f"{400}x{150}")

    label = tk.Label(root, text="BPM (log scale)")
    label.pack(pady=10)

    slider = tk.Scale(root,
                      from_=0,
                      to=1,
                      resolution=0.001,
                      orient=tk.HORIZONTAL,
                      length=300,
                      command=on_slider_change)
    slider.set(bpm_to_slider(DEFAULT_BPM))
    slider.pack()

    def on_close():
        stop_event.set()
        sequencer_thread.join()
        
        # Clean up all synth instances
        for current_synth_id, synth_instance in SYNTH_INSTANCES.items():
            # Stop any playing notes
            synth.note_off(current_synth_id)
            # Clean up the synth instance
            synth.stop_synth(current_synth_id)
            synth.delete_synth(current_synth_id)
        
        # Shut down the entire synth system
        synth.shutdown_synth_system()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()
