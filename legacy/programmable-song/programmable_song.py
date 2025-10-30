# g++ -std=c++17 -fPIC -shared synthlib.cpp -o libsynth.so -I/opt/homebrew/opt/portaudio/include -I/opt/homebrew/opt/libsndfile/include -L/opt/homebrew/opt/portaudio/lib -L/opt/homebrew/opt/libsndfile/lib -lportaudio -lsndfile -pthread



# bunghole master
# Undo Flag

#===========================#
#       IMPORTS             #
#===========================#
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import sys
import pygame
import numpy as np
import ctypes
import time
import threading
import tkinter as tk
import math

        #==================================================================#
        #------------------C-O-N-F-I-G-U-R-A-B-L-E-S-----------------------#
        #==================================================================#

debugging_eq = False  # Set to True to enable diagnostic output

# -------------------------- MASTER VOLUME CONTROLS ------------------------
bass_master_volume = 10.0
piano_master_volume = 20.0
DRUMS_MASTER_VOLUME = 1.0 

DRUM_DELAY_OFFSET = 0.0
PIANO_DELAY_OFFSET = 0.0
PORTAUDIO_SLOWDOWN = 0.15

# -------------------------- GENERAL CONTROLS ------------------------------
SAMPLE_RATE = 44100
MIN_BPM = 80
MAX_BPM = 180
DEFAULT_BPM = 120
BPM_RAMP_MEASURES = 4  # how many measures the ramp takes
STEPS_PER_MEASURE = 16

## SAMPLE PATHS AND FILE NAMING
SAMPLE_BASE_PATH = "ProgrammableLoop2/ProgrammableLoop2"
KICK_SAMPLE_PREFIX = "Kick"
SNARE_SAMPLE_PREFIX = "Snare"
CYMBAL_SAMPLE_PREFIX = "Cymbal"
SAMPLE_SUFFIX = ".wav"

first_slider_change = True

# Add these new globals for immediate target detection:
UPCOMING_PATTERN_INDEX = None
UPCOMING_TARGET_CHORD = None  
UPCOMING_PROTO_CHORD = None
UPCOMING_KEY_CHANGE = None
BASS_PREVIEW_KEY = None

# Master Timing Centralization
master_step = 0
master_seconds_per_16th = 0.125  # Default value
master_current_bpm = DEFAULT_BPM
master_next_trigger = 0

# Define the major scale degrees in semitones from the key root
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]  # W-W-H-W-W-W-H

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

# ---------------------------------------------------------------------------
# Parameter Change Compensation Settings
# ---------------------------------------------------------------------------

# Parameter-Change Compensation (not continuous normalization)
COMPENSATION_ENABLED = True
COMPENSATION_SMOOTHING_TIME = 0.05  # seconds for smooth transitions
COMPENSATION_MAX_ADJUSTMENT_DB = 6.0  # max compensation allowed

# Track parameter states for compensation
_last_slider_val = 0.5
_last_filter_state = {}
_last_tube_state = {}
_compensation_gain = {}  # per synth_id

# Final Filter Settings
FINAL_FILTER_MIN_FREQ = 183     # Minimum final filter cutoff
FINAL_FILTER_MAX_FREQ = 20000   # Maximum final filter cutoff

#--------------
#   DRUMS
#--------------

## DRUM SETTINGS
KICK_BOOST_DB = 6.0             # Extra volume boost for kicks (dB)
KICK_FADE_IN_MS = 10            # Fade-in time to prevent clicks (ms) 

# ------------------------------------------------------------
# PATTERN DICTIONARIES
# ------------------------------------------------------------

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
    ['1','c','c','c',  'c','c','c','c',  '1','c','c','c',  'c','c','c','c',  ], #SadLevel8
    #['1',0,'2',0, '3',0,'4',0, '5',0,'6',0, '7',0,'8',0, ],
    ['1','c','c','c', 'c','c','c','c', '3','c','c','c', 'c','c','c','c', ],
    #['1',0,'2',0, '3',0,'4',0, '5',0,'6',0, '7',0,'8',0, ],
    ['1','c','c','c', '1','c','c','c', '3','c','c','c', '3','c','c','c', ],
    ['1','c','c','c', '1','c','c','c', '5','c','c','c', '3','c','c','c', ],
    ['1','c','c',0, '1','c','c',0, '5','c','c',0, '3','c','c',0, ],
    ['1','c','c',0, '3','c','c',0, '5','c','c',0, '3','c','c',0, ],
    ['1','c','1','c', '3','c','c',0, '5','c',0,'5', '3',0,0,0, ],
    ['1','c','1',0, '3','c','3',0, '5','c','5',0, '3','c','3',0, ],
    ['1','1','1',0, '3','c','3',0, '5','c','5',0, '3','c','3',0, ], #Neutral
    #['7','7','7','7', '7','7','7','7', '7','7','7','7', '7','7','7','7', ],
    ['1','c','-7',0, '-7',0,'1','1', 'c',0,'2',0, '-7',0,'-7',0, ],
    #['1',0,'2',0, '3',0,'4',0, '5',0,'6',0, '7',0,'8',0, ],
    ['1','c','-7',0, '1','c','2',0, '3','c','3',0, '1','c','1',0, ],
    #['1',0,'2',0, '3',0,'4',0, '5',0,'6',0, '7',0,'8',0, ],
    ['1','c','-7',0, '2','c','3',0, '5','c','4',0, '2','c','2',0, ],
    ['1','c','-7',0, '-6',0,'-7','1', 'c',0,'1',0, '-6',0,'-6',0, ],
    ['1','c','-6',0, '-5',0,'-6','1', 'c','1','-6',0, '-5',0,'-6',0, ],
    ['1',0,'-6',0, '-5',0,'-6','1', 0,0,'-6',0, '-5',0,'-6',0, ],
    ['1','c',0,0, '-5',0,'-6',0, '1',0,0,'-4', '-5',0,'-5',0, ],
    ['1',0,0,0,  '-5',0,0,0, '1',0,0,'-4', '-#4',0,'-5',0, ], #HappyLevel8
    #['1','c','c','c', 'c','c','c','c', 'c','c','c','c', 'c','c','c','c', ]
]

PIANO_PATTERNS = [
    [   # Sad Level 8
        ['vi','c','c',0, 'vi','c','c',0, 'vi','c','vi','c', 'vi','c','vi','c'  ],
        ['ii7','c','c',0, 'ii7','c','c',0, 'ii7','c','ii7','c', 'ii7','c','ii7','c', ],
        ['iv7','c','c',0, 'iv7','c','c',0, 'iv7','c','iv7','c', 'iv7','c','iv7','c', ],
        ['III7','c','c',0, 'III7','c','c',0, 'III7','c','III7','c', 'III7','c','III7','c', ]],
    [   # Sad Level 7
        ['vi','c','c','c', 0,0,'vi','c', 'vi','c','vi','c', 'vi','c','vi','c' ],
        ['ii','c','c','c', 0,0,'ii','c', 'ii','c','ii','c', 'ii','c','ii','c' ],
        ['vi','c','c','c', 0,0,'vi','c', 'vi','c','vi','c', 'vi','c','vi','c'  ],
        ['III','c','c','c', 0,0,'III','c', 'III','c','III','c', 'III','c','III','c' ],],
    [   # Sad Level 6
        ['vi','c','c','c', 0,0,'vi','c', 'vi','c','c','c', 0,0,'vi','c',],
        ['iv','c','c','c', 0,0,'iv','c', 'iv','c','c','c', 0,0,'iv','c',],
        ['biiº7','c','c','c', 0,0,'biiº7','c', 'biiº7','c','c','c', 0,0,'biiº7','c',],
        ['V7','c','c','c', 0,0,'V7','c', 'V7','c','c','c', 0,0,'V7','c',],],
    [   # Sad Level 5
        ['vi','c','vi','c', 0,0,'vi','c', 'vi','c','vi','c', 0,0,'vi','c',],
        ['bVI','c','bVI','c', 0,0,'bVI','c', 'bVI','c','bVI','c', 0,0,'bVI','c',],
        ['iº','c','iº','c', 0,0,'iº','c', 'iº','c','iº','c', 0,0,'iº','c',],
        ['V7','c','V7','c', 0,0,'V7','c', 'V7','c','V7','c', 0,0,'V7','c',],],
    [   # Sad Level 4
        ['vi','c','c','c', 0,0,0,0, 'vi','c','c','c', 'vi','c','c','c',],
        ['bIII','c','c','c', 0,0,0,0, 'bIII','c','c','c', 'bIII','c','c','c',],
        ['bVII','c','c','c', 0,0,0,0, 'bVII','c','c','c', 'bVII','c','c','c',],
        ['iiº*','c','c','c', 0,0,0,0, 'iiº*','c','c','c', 'iiº*','c','c','c',],],
    [   # Sad Level 3
        ['vi','c','c','vi', 0,0,0,0, 'vi','c','vi','c', 0,0,0,0,],
        ['ii','c','c','ii', 0,0,0,0, 'ii','c','ii','c', 0,0,0,0,],
        ['IV','c','c','IV', 0,0,0,0, 'IV','c','IV','c', 0,0,0,0,],
        ['bVII','c','c','bVII', 0,0,0,0, 'bVII','c','bVII','c', 0,0,0,0,],],
    [   # Sad Level 2
        ['I','c','c','c', 'c',0,'I','c', 'c','c','c','c', 0,0,0,0,],
        ['vi','c','c','c', 'c',0,'vi','c', 'c','c','c','c', 0,0,0,0,],
        ['IV','c','c','c', 'c',0,'IV','c', 'c','c','c','c', 0,0,0,0,],
        ['iv','c','c','c', 'c',0,'iv','c', 'c','c','c','c', 0,0,0,0,],],
    [   # Sad Level 1
        ['vi','c','c','c', 'vi','c','c','c', 'c','c','c','c', 'c','c',0,0,],
        ['iii','c','c','c', 'iii','c','c','c', 'c','c','c','c', 'c','c',0,0,],
        ['IV','c','c','c', 'IV','c','c','c', 'c','c','c','c', 'c','c',0,0,],
        ['V','c','c','c', 'V','c','c','c', 'c',0,'V','c', 'c',0,'V',0,],],
    [   # Neutral
        ['I','c','c','c', 'c','c',0,0, 'I','c','c','c', 'c','c',0,0,],
        ['vi','c','c','c', 'c','c',0,0, 'vi','c','c','c', 'c','c',0,0,],
        ['IV','c','c','c', 'c','c',0,0, 'IV','c','c','c', 'c','c',0,0,],
        ['V','c','c','c', 'c','c',0,0, 'V','c','c','c', 'c','c',0,0,],],
    [   # Happy Level 1
        ['I','c','c','c', 'c',0,'I','c', 'c','c','c','c', 'c','c',0,0,],
        ['I+','c','c','c', 'c',0,'I+','c', 'c','c','c','c', 'c','c',0,0,],
        ['IV','c','c','c', 'c',0,'IV','c', 'c','c','c','c', 'c','c',0,0,],
        ['V','c','c','c', 'c',0,'V','c', 'c','c','c','c', 'c','c',0,0,],],
    [   # Happy Level 2
        ['I',0,'I',0, 'I','c','c','c', 0,0,'I','c', 0,'I',0,0,],
        ['I',0,'I',0, 'I','c','c','c', 0,0,'I','c', 0,'I',0,0,],
        ['IV',0,'IV',0, 'IV','c','c','c', 0,0,'IV','c', 0,'IV',0,0,],
        ['V',0,'V',0, 'V','c','c','c', 0,0,'V','c', 0,'V',0,0,],],
    [   # Happy Level 3
        ['I',0,0,'I', 0,0,'I',0, 0,0,'I',0, 0,'I',0,0,],
        ['IV',0,0,'IV', 0,0,'IV',0, 0,0,'IV',0, 0,'IV',0,0,],
        ['I',0,0,'I', 0,0,'I',0, 0,0,'I',0, 0,'I',0,0,],
        ['V',0,0,'V', 0,0,'V',0, 0,0,'V',0, 0,'V',0,0,],],
    [   # Happy Level 4
        ['I',0,0,'I', 0,0,'I',0, 0,0,'I',0, 'I','c','c','c',],
        ['IV',0,0,'IV', 0,0,'IV',0, 0,0,'IV',0, 'IV','c','c','c',],
        ['V',0,0,'V', 0,0,'V',0, 0,0,'V',0, 'V','c','c','c',],
        ['I',0,0,'I', 0,0,'I',0, 0,0,'I',0, 'I','c','c','c',],],
    [   # Happy Level 5
        ['I','c',0,'I', 'I','c',0,'I', 'I','c',0,0, 'I',0,'I',0,],
        ['II','c',0,'II', 'II','c',0,'II', 'II','c',0,0, 'II',0,'II',0,],
        ['V','c',0,'V', 'V','c',0,'V', 'V','c',0,0, 'V',0,'V',0,],
        ['I','c',0,'I', 'I','c',0,'I', 'I','c',0,0, 'I',0,'I',0,],],
    [   # Happy Level 6
        ['I','I','I',0, 'I','I','I',0, 'IV','IV','IV',0, 'IV','IV','IV',0,],
        ['I','I','I',0, 'I','I','I',0, 0,0,'I',0, 0,0,'I',0,],
        ['II','II','II',0, 'II','II','II',0, 'V','V','V',0, 'V','V','V',0,],
        ['I','I','I',0, 'I','I','I',0, 0,0,'I',0, 0,0,'I',0,],],
    [   # Happy Level 7
        ['I',0,'I',0, 'I',0,'I',0, 0,0,'II',0, 0,0,'II',0,],
        ['V',0,'V',0, 'V',0,'V',0, 0,0,'V',0, 0,'V',0,'V',],
        ['I',0,'I',0, 'I',0,'I',0, 0,0,'#ivº7',0, 0,0,'#ivº7',0,],
        ['V',0,'V',0, 'V',0,'V',0, 0,0,'I',0, 0,'I',0,0,],],
    [   # Happy Level 8
        [0,0,'I',0, 0,0,'I',0, 0,0,'II',0, 0,0,'II',0,],
        [0,0,'V',0, 0,0,'V',0, 0,0,'VII',0, 0,0,'VII',0,],
        [0,0,'I',0, 0,0,'I',0, 0,0,'#IV',0, 0,0,'#IV',0,],
        [0,0,'V',0, 0,0,'V',0, 0,0,'IV',0, 0,0,'IV',0,],]
]

## DELAY PATTERN SETTINGS
# Base delay amounts in milliseconds for sad patterns (SadLevel8 → SadLevel1)
DELAY_BASE_SAD_MS = [12, 10, 8, 6, 5, 4, 3, 0]
# Happy delays are calculated as: sad_delay * DELAY_HAPPY_FACTOR
DELAY_HAPPY_FACTOR = 0.25

# At the global level, after your existing BASS_PATTERNS definition
SYNTH_PATTERN_SETS = {
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
    "osc1_waveform": "sine",
    "osc2_waveform": "sample",  
    "min_osc1_gain": 1.0,
    "max_osc1_gain": 0.5,
    "min_osc2_gain": 0.0,
    "max_osc2_gain": 2.0,
    "sampleLoopStartPercentage": 0.26,
    "sampleLoopEndPercentage": 1.0,
    "sampleBaseFrequency": 16.352,
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
    "min_filter_cutoff": 50.0,
    "max_filter_cutoff": 50.0,
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
    "oscillators": [
        {"waveform": "sample", "min_gain": 0.0,  "max_gain": 1.0,
         "samplePath": "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/JP Square PWM.wav",
         "sampleLoopStartPercentage": 0.0,
         "sampleLoopEndPercentage": 1.0,
         "sampleBaseFrequency": 21.785,
         "highpass_cutoff": 100,
         "highpass_enabled": True},
        {"waveform": "sample", "min_gain": 0.0,  "max_gain": 0.79,
         "samplePath": "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/JP Square PWM.wav",
         "sampleLoopStartPercentage": 0.0,
         "sampleLoopEndPercentage": 1.0,
         "sampleBaseFrequency": 43.725,
         "highpass_cutoff": 100,
         "highpass_enabled": True},
        {"waveform": "sample", "min_gain": 1.0,  "max_gain": 0.0,
         "samplePath": "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/Piano HIGH C2.wav",
         "sampleLoopStartPercentage": 0.5,
         "sampleLoopEndPercentage": 1.0,
         "sampleBaseFrequency": 65.41,
         "highpass_cutoff": 100,
         "highpass_enabled": True},
         {"waveform": "sample", "min_gain": 0.79,  "max_gain": 0.0,
         "samplePath": "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/Piano Tape Hiss C.wav",
         "sampleLoopStartPercentage": 0.41,
         "sampleLoopEndPercentage": 1.0,
         "sampleBaseFrequency": 65.41,
         "highpass_cutoff": 100,
         "highpass_enabled": True}],
    "osc1_waveform": None,
    "osc2_waveform": None,
    "min_osc1_gain": 0.0,
    "max_osc1_gain": 0.0,
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
    "minAttack": 0.05,
    "maxAttack": 0.05,
    "minDecay": 0.01,
    "maxDecay": 60.0,
    "minSustainDb": 0.0,
    "maxSustainDb": 0.0,
    "minRelease": 4.0,
    "maxRelease": 0.1,
    # FM-depth bounds
    "minFmDepth": 0.0,
    "maxFmDepth": 0.0,
    # LFO Params
    "min_LFO_rate": 0.562,
    "max_LFO_rate": 0.01,
    "min_LFO_depth": 0.0618,
    "max_LFO_depth": 0.01,
    "min_LFO_Level": 0.25,
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
    "min_filter_cutoff": 20000.0,
    "max_filter_cutoff": 20000.0,
    "min_filter_resonance": 9.79,
    "max_filter_resonance": 20.83,
    "min_filter_drive": 0.05,
    "max_filter_drive": 0.0,
    "min_filter_key_track": 0.7,
    "max_filter_key_track": 0.5,
    "min_filter_env_mod": 0.6,
    "max_filter_env_mod": 0.4,
    # Comb filter parameters
    "min_comb_cutoff": 20000.0,
    "max_comb_cutoff": 20000.0,
    "min_comb_resonance": 0.25,
    "max_comb_resonance": 0.25,
    "min_comb_drive": 0.0,
    "max_comb_drive": 0.0,
    "min_comb_key_track": 0.0,
    "max_comb_key_track": 0.0,
    "min_comb_env_mod": 0.0,
    "max_comb_env_mod": 0.0,
    # Global filter parameters
    "min_global_cutoff": 20.0,
    "max_global_cutoff": 20.0,
    "min_global_resonance": 0.25,
    "max_global_resonance": 0.25,
    # Filter envelope parameters
    "min_filter_env_attack": 0.001,
    "max_filter_env_attack": .006,
    "min_filter_env_decay": 0.99,
    "max_filter_env_decay": 1.874,
    "min_filter_env_sustain": -11.31,
    "max_filter_env_sustain": -50.0,
    "min_filter_env_release": 3.75,
    "max_filter_env_release": 12.300,
}

        #==================================================================#
        #--------------U-T-I-L-I-T-Y---V-A-R-I-A-B-L-E-S-------------------#
        #==================================================================#

# Threading synchronization events for sequencer coordination
bass_pattern_ready = threading.Event()
piano_chord_ready = threading.Event()

# Master timing coordination (wait for 2 threads - piano and bass)
sequencer_barrier = threading.Barrier(3)

GLOBAL_DELAY = 0.0 # Delays start of program, incase of buffer problems
FADE_SAMPLES = 256 # Prevents audio clicks during transitions
FADE_IN_TIME = 10 # ms, for loading sample to avoid clicks
GAIN_SMOOTHING_TIME_SECONDS = 0.5 # Smooths parameter value transitions
LOOP_FADE_SAMPLES = 256 # Loop-fade length for sample looping (in samples)

CURRENT_CHORD_ROOT = "1"  # Default to tonic
CURRENT_CHORD_SYMBOL = PIANO_PATTERNS[8][0][0]  # The actual chord being played by piano
TRANSITIONAL_CHORD_SYMBOL = None  # Bass uses this during key transitions
PREVIOUS_CHORD_SYMBOL = None  # Track the previous chord for contextual scale selection

# Thresholds, parameter bounds
GAIN_NORMALIZATION_CAP = 100.0
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

# Musical State Management
current_key = 0  # 0-11 representing C through B (0=C, 1=C#, 2=D, etc.)
previous_key = 0  # Track key changes for smooth transitions
key_change_pending = False  # Flag for when a key change is scheduled
pending_key = 0  # The key we're transitioning to

# Progression tracking
current_progression_step = 0  # Which step in the current chord progression
current_chord_index = 0  # Which chord pattern within that step
progression_measure_count = 0  # Track measures for progression timing

# Pivot chord system state
pivot_chord = None  # The chord we're pivoting from
proto_chord = None  # The chord in new progression we're "coming from"
target_chord = None  # The next chord in the new progression
phantom_chord = None  # Calculated phantom chord when no pivot exists

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
start_sample_gain = {}
target_sample_gain = {}
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
POLY_SYNTH_INSTANCES = {}  # Will store PolySynth objects keyed by name

# --------------------------------------------------------------------------
#      SynthInstance – wraps one C++ Synthesizer instance with a config
# --------------------------------------------------------------------------
class SynthInstance:
    def __init__(self, config_dict):
        self.config_obj = SynthConfig(config_dict)
        self.config = config_dict
        self.synth_id = synth.create_synth()

        # Register this instance in the global registry (but skip piano voices)
        if config_dict.get("patternSet") != "piano":
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
        
        # Initialize oscillators (variable count if provided)
        osc_list = self.config.get("oscillators")
        slider_val = 0.5

        if osc_list and isinstance(osc_list, list) and len(osc_list) > 0:
            synth.set_osc_count(len(osc_list), self.synth_id)
            for idx, osc in enumerate(osc_list):
                wf = WAVEFORM_TYPES.get(osc.get("waveform", "sine"), 0)
                # Correct arg order: (index, type, synthId)
                synth.set_osc_waveform_at(idx, wf, self.synth_id)

                # If this oscillator uses a sample, set its path and parameters
                if wf == WAVEFORM_TYPES["sample"]:
                    path = osc.get("samplePath")
                    if path:
                        synth.set_sample_path_at(path.encode("utf-8"), idx, self.synth_id)
                        
                        # Set the sample loop start percentage
                        loop_start = osc.get("sampleLoopStartPercentage", 0.0)
                        synth.set_sample_loop_start_percentage_at(loop_start, idx, self.synth_id)
                        
                        # Set the sample loop end percentage
                        loop_end = osc.get("sampleLoopEndPercentage", 1.0)
                        synth.set_sample_loop_end_percentage_at(loop_end, idx, self.synth_id)
                        
                        # Set the sample base frequency
                        base_freq = osc.get("sampleBaseFrequency", 440.0)
                        synth.set_sample_base_frequency_at(base_freq, idx, self.synth_id)
                        
                        # Apply high-pass filter settings if specified
                        highpass_cutoff = osc.get("highpass_cutoff", 0.0)
                        highpass_enabled = osc.get("highpass_enabled", False)
                        synth.set_highpass_cutoff_at(highpass_cutoff, idx, self.synth_id)
                        synth.set_highpass_enabled_at(highpass_enabled, idx, self.synth_id)

                min_g = float(osc.get("min_gain", 0.0))
                max_g = float(osc.get("max_gain", 1.0))
                g = slider_to_log_gain(slider_val, min_g, max_g)
                synth.set_osc_gain_at(g, idx, self.synth_id)
        else:
            # Legacy 2-osc path (unchanged behavior)
            synth.set_sine_gain(
                slider_to_log_gain(slider_val, self.config["min_osc1_gain"], self.config["max_osc1_gain"]),
                self.synth_id
            )
            synth.set_sample_gain(
                slider_to_log_gain(slider_val, self.config["min_osc2_gain"], self.config["max_osc2_gain"]),
                self.synth_id
            )
            synth.set_osc1_waveform(
                WAVEFORM_TYPES[self.config.get("osc1_waveform", "sine")],
                self.synth_id
            )
            synth.set_osc2_waveform(
                WAVEFORM_TYPES[self.config.get("osc2_waveform", "sample")],
                self.synth_id
            )

        # In the SynthInstance.__init__ method, after the oscillator waveform and gain setting
        if osc_list and isinstance(osc_list, list) and len(osc_list) > 0:
            synth.set_osc_count(len(osc_list), self.synth_id)
            for idx, osc in enumerate(osc_list):
                wf = WAVEFORM_TYPES.get(osc.get("waveform", "sine"), 0)
                # Correct arg order: (index, type, synthId)
                synth.set_osc_waveform_at(idx, wf, self.synth_id)

                # If this oscillator uses a sample, set its path
                if wf == WAVEFORM_TYPES["sample"]:
                    path = osc.get("samplePath")
                    if path:
                        synth.set_sample_path_at(path.encode("utf-8"), idx, self.synth_id)
                        
                        # Set the sample loop start percentage
                        loop_start = osc.get("sampleLoopStartPercentage", 0.0)
                        synth.set_sample_loop_start_percentage_at(loop_start, idx, self.synth_id)
                        
                        # Set the sample loop end percentage
                        loop_end = osc.get("sampleLoopEndPercentage", 1.0)
                        synth.set_sample_loop_end_percentage_at(loop_end, idx, self.synth_id)
                        
                        # Set the sample base frequency
                        base_freq = osc.get("sampleBaseFrequency", 440.0)
                        synth.set_sample_base_frequency_at(base_freq, idx, self.synth_id)

                min_g = float(osc.get("min_gain", 0.0))
                max_g = float(osc.get("max_gain", 1.0))
                g = slider_to_log_gain(slider_val, min_g, max_g)
                synth.set_osc_gain_at(g, idx, self.synth_id)

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

# --------------------------------------------------------------------------
# PolySynth - manages multiple SynthInstance objects to enable polyphony
# --------------------------------------------------------------------------
class PolySynth:
    def __init__(self, config_dict, voice_count=4):
        """
        Create a polyphonic synthesizer by managing multiple SynthInstance objects.
        
        Args:
            config_dict: Configuration dictionary to initialize each voice
            voice_count: Number of simultaneous notes that can be played
        """
        # Create multiple synth instances for polyphony
        self.voices = []
        self.voice_count = voice_count
        self.config = config_dict
        
        # Create the specified number of synth voices
        for i in range(voice_count):
            voice = SynthInstance(config_dict)
            self.voices.append(voice)
            
        # Tracking which voices are playing which notes
        self.active_notes = {}  # {midi_note: voice_index}
        
        # Voice allocation index for round-robin assignment
        self.next_voice_index = 0
    
    def get_available_voice(self):
        """
        Find an available voice, prioritizing voices that aren't currently playing.
        If all voices are in use, use round-robin allocation for voice stealing.
        """
        # First try to find a voice that's not currently playing
        used_voices = set(self.active_notes.values())
        for i in range(self.voice_count):
            if i not in used_voices:
                # Found an unused voice, use it
                self.next_voice_index = (i + 1) % self.voice_count
                return i
        
        # If all voices are in use, use round-robin for voice stealing
        voice_index = self.next_voice_index
        self.next_voice_index = (self.next_voice_index + 1) % self.voice_count
        return voice_index
    
    def note_on(self, midi_note):
        """Play a single note using an available voice"""
        if midi_note in self.active_notes:
            # Note already playing, stop it first
            voice_index = self.active_notes[midi_note]
            self.note_off(midi_note)
        
        # Find a voice to play this note
        voice_index = self.get_available_voice()
        voice = self.voices[voice_index]

        # Set frequency and trigger note
        freq = freq_from_midi(midi_note)
        synth.set_frequency(freq, voice.synth_id)  # Use C++ function directly
        synth.note_on(voice.synth_id)  # Use C++ function directly
        
        # Record which voice is playing this note
        self.active_notes[midi_note] = voice_index
    
    def note_off(self, midi_note):
        """Stop a currently playing note"""
        if midi_note in self.active_notes:
            voice_index = self.active_notes[midi_note]
            synth.note_off(self.voices[voice_index].synth_id)  # Use C++ function directly
            del self.active_notes[midi_note]
    
    def play_chord(self, midi_notes):
        """
        Play multiple notes simultaneously as a chord.
        
        Args:
            midi_notes: List of MIDI note numbers to play
        """

        # First stop ALL currently playing notes
        current_notes = list(self.active_notes.keys())
        for note in current_notes:
            self.note_off(note)
        
        # Add a small delay after stopping notes to ensure the synth engine has time to process
        time.sleep(0.001)
        
        # Sort the notes to ensure consistent voice allocation
        sorted_notes = sorted(midi_notes)
        
        # Reset voice allocation to ensure consistent starting point
        self.next_voice_index = 0

        # Now play all notes in the new chord with consistent voice allocation
        voice_assignments = {}
        for note in sorted_notes:
            # Find which voice will be used before we call note_on
            voice_index = self.get_available_voice()
            voice_assignments[note] = voice_index
            self.note_on(note)
            # Add a tiny delay between notes to prevent race conditions
            time.sleep(0.001)

    # Set frequency method
    def set_frequency(self, freq):
        synth.set_frequency(freq, self.synth_id)


# Load the synth library
synth = ctypes.CDLL('./libsynth.so')

# ============================================================================
# BINDINGS
# ============================================================================

WAVEFORM_TYPES = {
    "sine": 0,
    "square": 1,
    "triangle": 2,
    "saw": 3,
    "sample": 4,
}

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
synth.set_osc_count.argtypes = [ctypes.c_int, ctypes.c_int]
synth.set_osc_count.restype  = None

synth.set_osc_waveform_at.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
synth.set_osc_waveform_at.restype  = None

synth.set_osc_gain_at.argtypes = [ctypes.c_double, ctypes.c_int, ctypes.c_int]
synth.set_osc_gain_at.restype  = None


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
synth.set_sample_path_at.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
synth.set_sample_path_at.restype  = None
synth.set_sample_base_frequency.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_base_frequency.restype = None
synth.set_sample_gain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_gain.restype = None
synth.set_sine_gain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sine_gain.restype = None
synth.set_osc1_waveform.argtypes = [ctypes.c_int, ctypes.c_int]
synth.set_osc1_waveform.restype  = None
synth.set_osc2_waveform.argtypes = [ctypes.c_int, ctypes.c_int]
synth.set_osc2_waveform.restype  = None
synth.set_fade_samples.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_fade_samples.restype = None
synth.set_fade_in_time.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_fade_in_time.restype = None
# Add these new bindings in the bindings section
synth.set_sample_loop_start_percentage_at.argtypes = [ctypes.c_double, ctypes.c_int, ctypes.c_int]
synth.set_sample_loop_start_percentage_at.restype = None
synth.set_sample_loop_end_percentage_at.argtypes = [ctypes.c_double, ctypes.c_int, ctypes.c_int]
synth.set_sample_loop_end_percentage_at.restype = None
synth.set_sample_base_frequency_at.argtypes = [ctypes.c_double, ctypes.c_int, ctypes.c_int]
synth.set_sample_base_frequency_at.restype = None
# High-pass filter bindings
synth.set_highpass_cutoff_at.argtypes = [ctypes.c_double, ctypes.c_int, ctypes.c_int]
synth.set_highpass_cutoff_at.restype = None
synth.set_highpass_enabled_at.argtypes = [ctypes.c_bool, ctypes.c_int, ctypes.c_int]
synth.set_highpass_enabled_at.restype = None
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
synth.get_master_volume.argtypes = [ctypes.c_int]
synth.get_master_volume.restype = ctypes.c_double
# EQ Filter functions
synth.set_highshelf_eq.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_int]
synth.set_highshelf_eq.restype = None
synth.set_highpass_cutoff_at.argtypes = [ctypes.c_double, ctypes.c_int, ctypes.c_int]
synth.set_highpass_cutoff_at.restype = None
synth.set_highpass_enabled_at.argtypes = [ctypes.c_bool, ctypes.c_int, ctypes.c_int]
synth.set_highpass_enabled_at.restype = None
synth.set_peaking_eq.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int]
synth.set_peaking_eq.restype = None
synth.set_lowshelf_eq.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_int]
synth.set_lowshelf_eq.restype = None

# ============================================================================
# AUDIO SYSTEM INITIALIZATION
# ============================================================================
# Initialize pygame's audio mixer **before** any pygame.mixer.Sound() calls so
# that all drum samples can be loaded and played back correctly.
pygame.mixer.init()

def get_note_in_key(degree_str, base_midi_note, chord_root="1"):
    """
    Convert a scale degree string to a MIDI note that's in the current key.
    
    Args:
        degree_str: String representing the scale degree (e.g., "1", "b3", "5")
        base_midi_note: Base MIDI note number (e.g., 60 for middle C)
        chord_root: String representing the chord root (e.g., "1" for C, "5" for G)
        
    Returns:
        MIDI note number that's in the major key
    """
    # Parse the degree string to get its semitone offset from the chord root
    if degree_str in interval_to_semitone:
        # Get semitones for this degree and the chord root
        degree_semitones = interval_to_semitone[degree_str]
        chord_root_semitones = interval_to_semitone.get(chord_root, 0)
        
        # Calculate absolute semitones from the tonic
        absolute_semitones = chord_root_semitones + degree_semitones
        
        # Make sure the note is in the major key
        octave = absolute_semitones // 12
        scale_position = absolute_semitones % 12
        
        # Calculate the final MIDI note
        midi_note = base_midi_note + (octave * 12) + scale_position
        return midi_note

# ============================================================================
# MASTER AUDIO FUNCTIONS
# ============================================================================
# ============================================================================
# SIMPLE PIANO VOLUME COMPENSATION 
# ============================================================================

def get_piano_volume_multiplier(slider_val):
    """Get volume multiplier to compensate for piano oscillator dip around 0.4"""
    
    # Create a compensation curve that boosts around 0.4 where the dip occurs
    if slider_val >= 0.3 and slider_val <= 0.5:
        # Create a boost curve centered at 0.4
        distance_from_center = abs(slider_val - 0.4)
        max_distance = 0.1  # 0.3 to 0.5 range
        
        # Normalize distance (0 = at center, 1 = at edges)
        normalized_distance = distance_from_center / max_distance
        
        # Create boost that's strongest at center (slider_val = 0.4)
        boost_amount = 1.0 - normalized_distance  # 1.0 at center, 0.0 at edges
        boost_db = boost_amount * 3.0  # Up to 3dB boost at 0.4
        
        return 10.0 ** (boost_db / 20.0)  # Convert dB to linear
    
    return 1.0  # No compensation outside the problem range

def apply_simple_piano_compensation(poly_synth, slider_val):
    """Apply simple volume compensation for piano dip"""
    
    multiplier = get_piano_volume_multiplier(slider_val)
    
    # Apply to all voices
    for voice in poly_synth.voices:
        original_volume = voice.config["masterVolume"]
        synth.set_master_volume(original_volume * multiplier, voice.synth_id)

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
    global first_slider_change, debugging_eq
    
    # Debug output to help understand what's happening
    if debugging_eq:
        print(f"EQ applied with slider={slider}, first_change={first_slider_change}")
        sys.stdout.flush()  # Force output to appear immediately
    
    # Skip processing on first change to avoid glitches
    if first_slider_change:
        first_slider_change = False
        return sound
    
    raw = pygame.sndarray.array(sound).astype(np.float32)

    highshelf_db = slider_to_global_highshelf_db(slider)
    lowmid_db    = slider_to_lowmid_db(slider)

    # Early exit if no EQ change
    if abs(highshelf_db) < 0.1 and abs(lowmid_db) < 0.1:
        return sound

    def process_channel(channel_data: np.ndarray) -> np.ndarray:
        if abs(highshelf_db) >= 0.1:
            b, a = highshelf_biquad_coeffs(HIGHSHELF_FREQ_HZ,
                                           highshelf_db, SAMPLE_RATE)
            channel_data = apply_biquad_filter(channel_data, b, a)
        if abs(lowmid_db) >= 0.1:
            b, a = peaking_biquad_coeffs(LOWMID_CENTER_FREQ_HZ,
                                         lowmid_db, LOWMID_Q_FACTOR,
                                         SAMPLE_RATE)
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
                                           highshelf_db, SAMPLE_RATE)
            buf = apply_biquad_filter(buf, b, a)
        if abs(lowmid_db) >= 0.1:
            b, a = peaking_biquad_coeffs(LOWMID_CENTER_FREQ_HZ,
                                         lowmid_db, LOWMID_Q_FACTOR,
                                         SAMPLE_RATE)
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

def apply_global_eq(sound, slider_val):
    """
    Apply global EQ based on slider position:
    - High shelf boost/cut at HIGHSHELF_FREQ_HZ
    - Low-mid boost/cut at LOWMID_CENTER_FREQ_HZ
    - Overall gain adjustment
    """
    # Convert 0-1 slider to -1...+1 range for EQ adjustments
    eq_val = (slider_val - 0.5) * 2.0  
    
    # Apply high shelf EQ (boost highs when slider > 0.5, cut when < 0.5)
    highshelf_gain = eq_val * HIGHSHELF_DB_RANGE
    synth.set_highshelf_eq(HIGHSHELF_FREQ_HZ, highshelf_gain, synth_id)
    
    # Apply low-mid EQ (boost when slider < 0.5, cut when > 0.5)
    lowmid_gain = -eq_val * LOWMID_DB_RANGE
    synth.set_peaking_eq(LOWMID_CENTER_FREQ_HZ, lowmid_gain, LOWMID_Q_FACTOR, synth_id)
    
    # Apply overall gain adjustment
    gain_adjustment = eq_val * GLOBAL_GAIN_DB_RANGE
    current_volume = synth.get_master_volume(synth_id)
    synth.set_master_volume(current_volume * (10 ** (gain_adjustment / 20)), synth_id)

# ============================================================================
# MIDI AND MUSICAL UTILITIES
# ============================================================================

# Slider Level Labels
labels = PATTERN_LABELS

# Interval name → semitone offset mapping  (ACTIVELY USED by bass pattern logic)
interval_to_semitone = {
    # Below-tonic (negative) degrees
    '-1': -12, '-b2': -11, '-2': -10, '-b3': -9,  '-3': -8,  '-4': -7,
    '-#4': -6, '-b5': -6,  '-5': -5,  '-b6': -4,  '-6': -3,  '-b7': -2,
    '-7': -1,
    # Tonic and above
    '1': 0, '#1': 1, 'b2': 1, '2': 2, '#2': 3, 'b3': 3, '3': 4, '#3': 4, 'b4':4, '4': 5, '#4': 6, 'b5': 6,
    '5': 7, '#5': 8, 'b6': 8, '6': 9, '#6': 10, 'b7': 10, '7': 11, '#7': 12, '8': 12
}

# Roman numeral to scale degree mapping including chromatic variants
roman_to_scale_degree = {
    # Major scale degrees (uppercase)
    'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5', 'VI': '6', 'VII': '7',
    
    # Minor scale degrees (lowercase)
    'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7',
    
    # Chromatic alterations - flats
    'bI': 'b1', 'bII': 'b2', 'bIII': 'b3', 'bIV': 'b4', 'bV': 'b5', 'bVI': 'b6', 'bVII': 'b7',
    'bi': 'b1', 'bii': 'b2', 'biii': 'b3', 'biv': 'b4', 'bv': 'b5', 'bvi': 'b6', 'bvii': 'b7',
    
    # Chromatic alterations - sharps
    '#I': '#1', '#II': '#2', '#III': '#3', '#IV': '#4', '#V': '#5', '#VI': '#6', '#VII': '#7',
    '#i': '#1', '#ii': '#2', '#iii': '#3', '#iv': '#4', '#v': '#5', '#vi': '#6', '#vii': '#7',
}

# Map scale degrees to positions in the major scale (0-based)
scale_degree_to_position = {
    '1': 0,  # C
    '2': 1,  # D
    '3': 2,  # E
    '4': 3,  # F
    '5': 4,  # G
    '6': 5,  # A
    '7': 6,  # B
    'b1': 0,  # C (treat flats/sharps as their base note for position purposes)
    'b2': 1,  # D flat
    'b3': 2,  # E flat
    'b4': 3,  # F flat
    'b5': 4,  # G flat
    'b6': 5,  # A flat
    'b7': 6,  # B flat
    '#1': 0,  # C sharp
    '#2': 1,  # D sharp
    '#3': 2,  # E sharp
    '#4': 3,  # F sharp
    '#5': 4,  # G sharp
    '#6': 5,  # A sharp
    '#7': 6,  # B sharp
}

SCALES = {
    'ionian': ['1','2','3','4','5','6','7','8'],
    'dorian': ['1','2','b3','4','5','6','b7','8'],
    'phrygian': ['1','b2','b3','4','5','b6','b7','8'],
    'lydian': ['1','2','3','#4','5','6','7','8'],
    'mixolydian': ['1','2','3','4','5','6','b7','8'],
    'aeolian': ['1','2','b3','4','5','b6','b7','8'],
    'locrian': ['1','b2','b3','4','b5','b6','b7','8'],
    'natural_minor': ['1','2','b3','4','5','b6','b7','8'],
    'melodic_minor': ['1','2','b3','4','5','6','7','8'],
    'harmonic_minor': ['1','2','b3','4','5','b6','7','8'],
    'diminished_scale': ['1','2','b3','4','b5','b6','b7', '8'], # dropped nat6 for computer ease
    'locrian_nat2': ['1','2','b3','4','b5','b6','b7','8'],
    'whole_tone': ['1','2','3','#4','#5','#6', '#6'],  # 6-note scale
    'lydian_augmented': ['1','2','3','#4','#5','6','7','8'],  # Mode 3 of melodic minor
    'lydian_dominant': ['1','2','3','#4','5','6','b7','8'],
    'lydian_b3' : ['1','2','b3','#4','5','6','7','8'],
    'phrygian_dominant' : ['1','b2','3','4','5','b6','b7','8'],
    'phrygian_major' : ['1','b2','3','4','5','b6','b7','8'],
    'mixolydian_b6' : ['1','2','3','4','5','b6','b7','8'],
    'phrygian_dominant_#4' : ['1','b2','3','#4','5','b6','b7','8'],
    'dorian_b2' : ['1','b2','b3','4','5','6','b7','8'],
    'blues' : ['1','2','b3','4','b5','5','b7','8']
}

CHORD_TO_SCALE = {
    'I': 'ionian',
    'i': 'natural_minor',
    'ii': 'dorian', 
    'iii': 'phrygian',
    'IV': 'lydian',
    'V': 'mixolydian',
    'vi': 'aeolian',
    'viiº': 'locrian',
    # Add chromatic chords as needed
}

def get_scale_for_chord(chord_symbol, previous_chord=None, next_chord=None, target_chord=None):
    """Get the appropriate modal scale for a given chord with contextual logic"""
    # Strip extensions to get base chord
    base_chord = chord_symbol.replace('+', '').replace('º', '').replace('7', '').replace('M', '').replace('*', '')
    
    # General rule for any diminished chord (º, º*, º7), except viiº and viiº7
    if ('º' in chord_symbol and 
        not chord_symbol.startswith('viiº7') and 
        not chord_symbol.startswith('viiº')):
        return SCALES['locrian_nat2']
    
    # General rule for any augmented chord (+)
    if ('+' in chord_symbol):
        # If coming from the major version of the same chord, use whole_tone
        if previous_chord and previous_chord == base_chord:  # e.g., I → I+ or ii → ii+
            return SCALES['whole_tone']
        else:  # All other cases
            return SCALES['lydian_augmented']
        
    # Special contextual logic for i (minor tonic) chords
    if chord_symbol.startswith('i7'):
        if previous_chord:
            if previous_chord in ['V', 'V+', 'V7', 'V*', 'viiº', 'viiº7']:
                return SCALES['dorian']  # has ♭7 but more color than natural minor
            if previous_chord in ['iiº*', 'IV', 'viº*']:
                return SCALES['aeolian']  # natural minor, matches ♭7 perfectly
        return SCALES['natural_minor']
    elif base_chord == 'i':
        # Check if previous chord was V or viiº (dominant function)
        if previous_chord:
            if previous_chord in ['V', 'V+', 'V7', 'V*', 'viiº', 'viiº7']:
                return SCALES['harmonic_minor']
            # Add this new section for melodic minor
            if previous_chord in ['iiº*', 'IV', 'viº*']:
                return SCALES['melodic_minor']
        # Default to natural minor for all other cases
        return SCALES['aeolian']
    
    if chord_symbol.startswith('I7'):
        if (next_chord and next_chord.startswith('IV')) or (target_chord and target_chord.startswith('IV')):
            return SCALES['blues']
        else:
            return SCALES['mixolydian']
    
    if chord_symbol.startswith('bii7'):
        if (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')):
            return SCALES['lydian_dominant']  # ♭7 + #11 for tritone sub
        elif (next_chord and next_chord.startswith('I')) or (target_chord and target_chord.startswith('I')):
            return SCALES['lydian_dominant']  # functioning as V7 substitute  
        else:
            return SCALES['dorian']  # safe ♭7-compatible default
    elif base_chord == 'bii' or base_chord == 'bi':
        # Check if we're heading toward V (either in progression or via transition)
        # Check if we're heading toward V (either in progression or via transition)
        if (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')):
            return SCALES['melodic_minor']
        else:
            return SCALES['dorian']

    if chord_symbol.startswith('bII*') or chord_symbol.startswith('#I*'):
        return SCALES['ionian']  # natural 6 for major 6 chord
    elif chord_symbol.startswith('bIIM7') or chord_symbol.startswith('#IM7'):
        return SCALES['ionian']  # natural 7th for major 7th chord
    elif chord_symbol.startswith('bII7') or chord_symbol.startswith('#I7'):
        return SCALES['lydian_dominant']  # ♭7 for dominant 7th
    elif base_chord == 'bII' or base_chord == '#I':
        if (next_chord and next_chord.startswith('I')) or (target_chord and target_chord.startswith('I')):
            return SCALES['phrygian_dominant']
        else:
            return SCALES['ionian']

    if chord_symbol.startswith('II7') or (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')):
        return SCALES['mixolydian']
    elif chord_symbol.startswith('II'):
        return SCALES['lydian']
    
    if chord_symbol.startswith('#ii') or chord_symbol.startswith('biii'):
        return SCALES['aeolian']
    
    if chord_symbol.startswith('#II7') or chord_symbol.startswith('bIII7'):
        return SCALES['lydian_dominant']
    elif chord_symbol.startswith('#II') or chord_symbol.startswith('bIII'):
        return SCALES['lydian']
    
    if chord_symbol.startswith('III*'):
        return SCALES['ionian']  # natural 6 for major 6 chord
    elif chord_symbol.startswith('IIIM7'):
        return SCALES['ionian']  # natural 7th for major 7th chord
    elif chord_symbol.startswith('III'):
        return SCALES['mixolydian_b6']
    
    if chord_symbol.startswith('iv7'):
        return SCALES['natural_minor']  # ♭7 matches chord's minor 7th
    elif chord_symbol.startswith('iv'):
        if (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')):
            return SCALES['harmonic_minor']
        else:
            return SCALES['natural_minor']
        
    if chord_symbol.startswith('#iv') or chord_symbol.startswith('bv'):
        return SCALES['phrygian']
    
    if chord_symbol.startswith('#IV*') or chord_symbol.startswith('bV*'):
        return SCALES['lydian']  # natural 6 for major 6 chord
    elif chord_symbol.startswith('#IVM7') or chord_symbol.startswith('bVM7'):
        return SCALES['lydian']  # natural 7th for major 7th chord
    elif chord_symbol.startswith('#IV7') or chord_symbol.startswith('bV7'):
        return SCALES['phrygian_dominant_#4']  # ♭7 for dominant 7th
    elif chord_symbol.startswith('#IV') or chord_symbol.startswith('bV'):
        return SCALES['phrygian_dominant_#4']  # existing triad logic
    
    if chord_symbol.startswith('v'):
        return SCALES['dorian']
    
    if chord_symbol.startswith('#v') or chord_symbol.startswith('bvi'):
        if ((next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')) or 
            (next_chord and next_chord.startswith('I')) or (target_chord and target_chord.startswith('I')) or 
            (next_chord and next_chord.startswith('i')) or (target_chord and target_chord.startswith('i'))):
            return SCALES['dorian_b2']
        elif ((next_chord and next_chord.startswith('IV')) or (target_chord and target_chord.startswith('IV')) or 
            (next_chord and next_chord.startswith('iv')) or (target_chord and target_chord.startswith('iv'))): 
            return SCALES['aeolian']
        elif previous_chord in ['bIII', 'bVI']:
            return SCALES['dorian']
        else:
            return SCALES['phrygian']

    if chord_symbol.startswith('#V*') or chord_symbol.startswith('bVI*'):
        return SCALES['ionian']  # natural 6 for major 6 chord
    elif chord_symbol.startswith('#VM7') or chord_symbol.startswith('bVIM7'):
        if previous_chord in ['IV','ii7'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V')) or
            (next_chord and next_chord.startswith('v')) or
            (target_chord and target_chord.startswith('v'))
        ):
            return SCALES['ionian']  # natural 7 for M7 chord
        elif (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')): 
            return SCALES['lydian']  # already natural 7
        elif previous_chord in ['V+']:
            return SCALES['lydian']  # natural 7 substitute for phrygian_major
        else:
            return SCALES['ionian']  # natural 7 default
    elif chord_symbol.startswith('#V7') or chord_symbol.startswith('bVI7'):
        if previous_chord in ['IV','ii7'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V')) or
            (next_chord and next_chord.startswith('v')) or
            (target_chord and target_chord.startswith('v'))
        ):
            return SCALES['mixolydian_b6']  # ♭7 for dominant 7
        elif (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')): 
            return SCALES['mixolydian']  # ♭7 substitute for lydian
        elif previous_chord in ['V+']:
            if (next_chord and next_chord.startswith('i')) or (target_chord and target_chord.startswith('i')) or (
                (next_chord and next_chord.startswith('iv')) or (target_chord and target_chord.startswith('iv'))
            ): 
                return SCALES['mixolydian']  # ♭7 substitute for phrygian_major
            else:
                return SCALES['whole_tone']  # ambiguous 7th
        else:
            return SCALES['mixolydian']  # ♭7 substitute for ionian
    elif chord_symbol.startswith('#V') or chord_symbol.startswith('bVI'):
        if previous_chord in ['IV','ii7'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V')) or
            (next_chord and next_chord.startswith('v')) or
            (target_chord and target_chord.startswith('v'))
        ):
            return SCALES['mixolydian_b6']
        elif (next_chord and next_chord.startswith('V')) or (target_chord and target_chord.startswith('V')): 
            return SCALES['lydian']
        elif previous_chord in ['V+']:
            if (next_chord and next_chord.startswith('i')) or (target_chord and target_chord.startswith('i')) or (
                (next_chord and next_chord.startswith('iv')) or (target_chord and target_chord.startswith('iv'))
            ): 
                return SCALES['phrygian_major']
            else:
                return SCALES['whole_tone']
        else:
            return SCALES['ionian']
        
    if chord_symbol.startswith('VIM7'):
        return SCALES['lydian']  # or ionian - both have natural 7
    elif chord_symbol.startswith('VI7'):
        if previous_chord in ['V7', 'V'] and (
            (next_chord and next_chord.startswith('ii')) or 
            (target_chord and target_chord.startswith('ii')) or
            (next_chord and next_chord.startswith('IV')) or
            (target_chord and target_chord.startswith('IV'))
        ):
            return SCALES['dorian']  # ♭7 works
        elif previous_chord in ['bVII', 'bIII']:
            return SCALES['mixolydian']  # ♭7 works
        else:
            return SCALES['dorian']  # ♭7 default instead of ionian
    elif chord_symbol.startswith('VI'):
        if previous_chord in ['V7', 'V'] and (
            (next_chord and next_chord.startswith('ii')) or 
            (target_chord and target_chord.startswith('ii')) or
            (next_chord and next_chord.startswith('IV')) or
            (target_chord and target_chord.startswith('IV'))
        ):
            return SCALES['dorian']
        elif previous_chord in ['IV', 'IVM7'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V'))
        ):
            return SCALES['lydian']
        elif previous_chord in ['bVII', 'bIII']:
            return SCALES['mixolydian']
        else:
            return SCALES['ionian']
        
    if chord_symbol.startswith('bvii') or chord_symbol.startswith('#vi'):
        if previous_chord in ['iv', 'v'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['IV', 'V'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I')) or
            (next_chord and next_chord.startswith('IV')) or
            (target_chord and target_chord.startswith('IV'))
        ):
            return SCALES['dorian']
        elif previous_chord in ['V7'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i')) or
            (next_chord and next_chord.startswith('iv')) or
            (target_chord and target_chord.startswith('iv'))
        ):
            return SCALES['phrygian']
        else:
            return SCALES['aeolian']

    if chord_symbol.startswith('bVIIM7') or chord_symbol.startswith('#VIM7'):
        if previous_chord in ['IV', 'ii7']:
            return SCALES['lydian']  # natural 7 works
        elif previous_chord in ['IV', 'bIII']:
            return SCALES['ionian']  # natural 7 works
        else:
            return SCALES['ionian']  # natural 7 default
    elif chord_symbol.startswith('bVII7') or chord_symbol.startswith('#VI7'):
        if previous_chord in ['V', 'V7']:
            return SCALES['mixolydian']  # ♭7 works
        elif previous_chord in ['IV', 'ii7']:
            return SCALES['mixolydian']  # ♭7 substitute for lydian
        elif previous_chord in ['IV', 'bIII']:
            return SCALES['mixolydian']  # ♭7 substitute for ionian  
        else:
            return SCALES['mixolydian']  # ♭7 default
    elif chord_symbol.startswith('bVII') or chord_symbol.startswith('#VI'):
        if previous_chord in ['V', 'V7'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I')) or
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i'))
        ):
            return SCALES['mixolydian']
        elif previous_chord in ['IV', 'ii7'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V')) or
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I'))
        ):
            return SCALES['lydian']
        elif previous_chord in ['IV', 'bIII'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I')) or
            (next_chord and next_chord.startswith('IV')) or
            (target_chord and target_chord.startswith('IV'))
        ):
            return SCALES['ionian']
        else:
            return SCALES['mixolydian']
    
    if chord_symbol.startswith('vii7'):
        if previous_chord in ['V', 'V7'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i')) or
            (next_chord and next_chord.startswith('iv')) or
            (target_chord and target_chord.startswith('iv'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['ii7', 'iv'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V'))
        ):
            return SCALES['phrygian']
        elif previous_chord in ['vi', 'VI'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i'))
        ):
            return SCALES['dorian']
        elif previous_chord in ['I', 'IM7'] and (
            (next_chord and next_chord.startswith('vi')) or
            (target_chord and target_chord.startswith('vi')) or
            (next_chord and next_chord.startswith('iv')) or
            (target_chord and target_chord.startswith('iv'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['iii'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i')) or
            (next_chord and next_chord.startswith('VI')) or
            (target_chord and target_chord.startswith('VI'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['bVI'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i'))
        ):
            return SCALES['aeolian']  # ♭7 substitute for harmonic_minor
        elif (next_chord and next_chord.startswith('III')) or (target_chord and target_chord.startswith('III')) or (
            (next_chord and next_chord.startswith('bIII')) or (target_chord and target_chord.startswith('bIII'))
        ):
            return SCALES['dorian']
        else:
            return SCALES['aeolian']
    elif chord_symbol.startswith('vii'):
        if previous_chord in ['V', 'V7'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i')) or
            (next_chord and next_chord.startswith('iv')) or
            (target_chord and target_chord.startswith('iv'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['ii7', 'iv'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V'))
        ):
            return SCALES['phrygian']
        elif previous_chord in ['vi', 'VI'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i'))
        ):
            return SCALES['dorian']
        elif previous_chord in ['I', 'IM7'] and (
            (next_chord and next_chord.startswith('vi')) or
            (target_chord and target_chord.startswith('vi')) or
            (next_chord and next_chord.startswith('iv')) or
            (target_chord and target_chord.startswith('iv'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['iii'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i')) or
            (next_chord and next_chord.startswith('VI')) or
            (target_chord and target_chord.startswith('VI'))
        ):
            return SCALES['aeolian']
        elif previous_chord in ['bVI'] and (
            (next_chord and next_chord.startswith('i')) or
            (target_chord and target_chord.startswith('i'))
        ):
            return SCALES['harmonic_minor']
        elif (next_chord and next_chord.startswith('III')) or (target_chord and target_chord.startswith('III')) or (
            (next_chord and next_chord.startswith('bIII')) or (target_chord and target_chord.startswith('bIII'))
        ):
            return SCALES['dorian']
        else:
            return SCALES['aeolian']
        
    if chord_symbol.startswith('VII*'):
        return SCALES['ionian']  # natural 6 for major 6 chord
    elif chord_symbol.startswith('VIIM7'):
        if previous_chord in ['IV', 'ii']:
            return SCALES['ionian']  # natural 7 works
        elif previous_chord in ['VI']:
            return SCALES['lydian']  # natural 7 works
        elif (next_chord and next_chord.startswith('iii')):
            return SCALES['ionian']  # natural 7 works
        else:
            return SCALES['ionian']  # natural 7 default
    elif chord_symbol.startswith('VII7'):
        if previous_chord in ['V', 'V7']:
            return SCALES['lydian_dominant']  # ♭7 works
        elif previous_chord in ['IV', 'ii']:
            return SCALES['mixolydian']  # ♭7 substitute for ionian
        elif previous_chord in ['bVII', 'bIII']:
            return SCALES['mixolydian_b6']  # ♭7 works
        elif previous_chord in ['VI']:
            return SCALES['mixolydian']  # ♭7 substitute for lydian
        elif (next_chord and next_chord.startswith('vi')):
            return SCALES['mixolydian']  # ♭7 works
        elif not previous_chord:
            return SCALES['lydian_dominant']  # ♭7 works
        elif previous_chord in ['III', 'iii']:
            return SCALES['mixolydian']  # ♭7 works
        else:
            return SCALES['mixolydian']  # ♭7 default
    elif chord_symbol.startswith('VII'):
        if previous_chord in ['V', 'V7'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I'))
        ):
            return SCALES['lydian_dominant']
        elif previous_chord in ['IV', 'ii'] and (
            (next_chord and next_chord.startswith('V')) or
            (target_chord and target_chord.startswith('V'))
        ):
            return SCALES['ionian']
        elif previous_chord in ['bVII', 'bIII'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I')) or
            (next_chord and next_chord.startswith('IV')) or
            (target_chord and target_chord.startswith('IV'))
        ):
            return SCALES['mixolydian_b6']
        elif previous_chord in ['VI'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I'))
        ):
            return SCALES['lydian']
        elif (next_chord and next_chord.startswith('vi')) or (target_chord and target_chord.startswith('vi')):
            return SCALES['mixolydian']
        elif not previous_chord and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I'))
        ):
            return SCALES['lydian_dominant']
        elif previous_chord in ['III', 'iii'] and (
            (next_chord and next_chord.startswith('I')) or
            (target_chord and target_chord.startswith('I'))
        ):
            return SCALES['mixolydian']
        elif (next_chord and next_chord.startswith('iii')) or (target_chord and target_chord.startswith('iii')):
            return SCALES['ionian']
        else:
            return SCALES['ionian']
        
    # If it's already a Roman numeral, use normal modal mapping
    if base_chord in CHORD_TO_SCALE:
        mode = CHORD_TO_SCALE.get(base_chord, 'ionian')
        return SCALES[mode]
    
    # If it's a scale degree (like "1", "5"), convert to Roman numeral first
    scale_degree_to_roman = {v: k for k, v in roman_to_scale_degree.items() if k.isupper()}
    roman_numeral = scale_degree_to_roman.get(chord_symbol, 'I')
    base_roman = roman_numeral.replace('+', '').replace('º', '').replace('7', '').replace('M', '').replace('*', '')
    mode = CHORD_TO_SCALE.get(base_roman, 'ionian')
    return SCALES[mode]

def get_bass_note(degree_str, chord_symbol, base_midi_note, next_chord=None, target_chord=None):
    """
    Convert a bass pattern degree to a modal note based on the current chord.
    """
    if degree_str in ('c', 0):
        return degree_str
    
    # Get the chord root offset
    chord_root_degree = get_chord_root(chord_symbol)
    if chord_root_degree and chord_root_degree in interval_to_semitone:
        chord_root_offset = interval_to_semitone[chord_root_degree]
    else:
        chord_root_offset = 0
    
    # Get the scale for this chord
    # Get previous chord context for scale selection
    previous_chord = TRANSITIONAL_CHORD_SYMBOL or PREVIOUS_CHORD_SYMBOL
    modal_scale = get_scale_for_chord(chord_symbol, previous_chord, next_chord, target_chord)
    #print(f"MODAL SCALE DEBUG: Using {modal_scale} for chord {chord_symbol}, degree {degree_str}")
    # Convert degree to scale position - handle both positive and negative degrees
    try:
        degree_num = int(degree_str)
        abs_degree = abs(degree_num)
        
        # Map to scale position (1-8 maps to 0-7)
        scale_position = abs_degree - 1
        if 0 <= scale_position < len(modal_scale):
            modal_degree = modal_scale[scale_position]
            modal_interval = interval_to_semitone[modal_degree]
            
            if degree_num > 0:
                # Positive: same octave as root
                result_note = base_midi_note + chord_root_offset + modal_interval
            else:
                # Negative: one octave below root
                result_note = base_midi_note + chord_root_offset + modal_interval - 12
                
            result_note = clamp_bass_to_octave(result_note)
            return result_note
        
    except ValueError:
        # Not a simple number, continue to complex degree handling
        pass
    
    # Fallback to original interval system for complex degrees
    if degree_str in interval_to_semitone:
        result_note = base_midi_note + chord_root_offset + interval_to_semitone[degree_str]
        result_note = clamp_bass_to_octave(result_note)
        return result_note
    
    result_note = base_midi_note + chord_root_offset  # Calculate first
    result_note = clamp_bass_to_octave(result_note)  # Then clamp
    return result_note  # Return the clamped result

def parse_roman_numeral_chord(chord_str, base_midi_note, original_base_midi_note):
    """
    Dynamically convert a Roman numeral chord notation to a list of MIDI notes.
    
    Args:
        chord_str: String containing a Roman numeral chord (e.g., "V7", "vi", "iiº")
        base_midi_note: The base MIDI note for the key (e.g., 60 for C)
        
    Returns:
        List of MIDI note numbers
    """

    # Handle 'c' (continue) and 0 (rest) immediately
    if chord_str == 'c' or chord_str == 0:
        return chord_str
    
    # Extract the Roman numeral part (including any chromatic prefix)
    roman_part = ""
    i = 0
    
    # Check for chromatic prefix
    if i < len(chord_str) and (chord_str[i] == 'b' or chord_str[i] == '#'):
        roman_part += chord_str[i]
        i += 1
    
    # Get the Roman numeral itself
    while i < len(chord_str) and chord_str[i] in "ivIV":
        roman_part += chord_str[i]
        i += 1
    
    # Extract any symbols/modifiers after the Roman numeral
    modifier_part = chord_str[i:]
    
    # Determine the scale degree of the root
    if roman_part in roman_to_scale_degree:
        root_degree = roman_to_scale_degree[roman_part]
    else:
        print(f"Warning: Unknown Roman numeral {roman_part}")
        root_degree = "b5"  # Default to tonic
    
    # Get the position of the root in the scale
    root_position = scale_degree_to_position.get(root_degree, 6)  # Default to ugly if not found
    
    # Extract the base Roman numeral without chromatic alterations
    base_roman = ''.join([c for c in roman_part if c in "ivIV"])
    
    # Determine chord quality (major/minor/diminished/augmented)
    is_major = base_roman.isupper()
    is_diminished = "º" in modifier_part
    is_augmented = "+" in modifier_part
    
    # Build chord using scale degrees, not intervals
    chord_notes = []
    
    # Add root note
    root_midi = base_midi_note + interval_to_semitone[root_degree]
    while root_midi > (original_base_midi_note + 11):
        root_midi -= 12
    while root_midi < original_base_midi_note:
        root_midi += 12
    chord_notes.append(root_midi)
    
    # For major chords, third is 2 scale degrees up (e.g., I -> III)
    # For minor chords, third is 2 scale degrees up but flat (e.g., i -> iii)
    third_semitones = 4 if is_major else 3
    third_midi = root_midi + third_semitones
    while third_midi > (original_base_midi_note + 11):
        third_midi -= 12
    while third_midi < original_base_midi_note:
        third_midi +=12
    chord_notes.append(third_midi)

    # For regular chords, fifth is 7 semitones
    # For diminished chords, fifth is 6 semitones
    # For augmented chords, fifth is 8 semitones
    if is_diminished:
        fifth_semitones = 6
    elif is_augmented:
        fifth_semitones = 8
    else:
        fifth_semitones = 7

    fifth_midi = root_midi + fifth_semitones
    while fifth_midi > (original_base_midi_note + 11):
        fifth_midi -= 12
    while fifth_midi < original_base_midi_note:
        fifth_midi +=12

    chord_notes.append(fifth_midi)

    # Add extensions if specified
    if "*" in modifier_part:  # Add 6th
        sixth_semitones = 9
        sixth_midi = root_midi +sixth_semitones
        while sixth_midi > (original_base_midi_note + 11):
            sixth_midi -= 12
        while sixth_midi < original_base_midi_note:
            sixth_midi += 12
        chord_notes.append(sixth_midi)
    elif "M7" in modifier_part:  # Add major 7th
        #seventh_degree = (root_position + 6) % 7 + 1
        #seventh_str = str(seventh_degree)
        #if seventh_str in interval_to_semitone:
        #    seventh_midi = base_midi_note + interval_to_semitone[seventh_str]
        #    chord_notes.append(seventh_midi)
        seventh_semitones = 11
        seventh_midi = root_midi + seventh_semitones
        while seventh_midi > (original_base_midi_note + 11):
            seventh_midi -= 12
        while seventh_midi < original_base_midi_note:
            seventh_midi += 12
        chord_notes.append(seventh_midi)
    elif "7" in modifier_part:  # Add minor/dominant 7th
        #seventh_degree = (root_position + 6) % 7 + 1
        #seventh_str = str(seventh_degree)
        # For dominant 7ths (major chord with minor 7th)
        #if is_major:
        #    seventh_str = "b" + seventh_str
        #if seventh_str in interval_to_semitone:
        #    seventh_midi = base_midi_note + interval_to_semitone[seventh_str]
        #    chord_notes.append(seventh_midi)
        seventh_semitones = 10
        seventh_midi = root_midi + seventh_semitones
        while seventh_midi > (original_base_midi_note + 11):
            seventh_midi -= 12
        while seventh_midi < original_base_midi_note:
            seventh_midi += 12
        chord_notes.append(seventh_midi) 

    # Sort the notes to ensure consistent voice allocation
    return sorted(list(set(chord_notes)))  # Remove any duplicates

def get_chord_root(chord_str):
    """
    Extract the root note of a Roman numeral chord.
    
    Args:
        chord_str: String containing a Roman numeral chord (e.g., "V7", "vi", "iiº")
        
    Returns:
        String with the scale degree of the root (e.g., "5", "6", "2")
    """
    if chord_str is None:
        return None
    
    # Handle 'c' (continue) and 0 (rest) immediately
    if chord_str == 'c' or chord_str == 0:
        return None
    
    # Extract the Roman numeral part (including any chromatic prefix)
    roman_part = ""
    i = 0
    
    # Check for chromatic prefix
    if i < len(chord_str) and (chord_str[i] == 'b' or chord_str[i] == '#'):
        roman_part += chord_str[i]
        i += 1
    
    # Get the Roman numeral itself
    while i < len(chord_str) and chord_str[i] in "ivIV":
        roman_part += chord_str[i]
        i += 1
    
    # Map to scale degree
    if roman_part in roman_to_scale_degree:
        return roman_to_scale_degree[roman_part]
    else:
        print(f"Warning: Unknown Roman numeral {roman_part}")
        return "b5"  # Default to tonic

import inspect

def freq_from_midi(midi_note):
    caller_frame = inspect.stack()[1].frame
    caller = inspect.stack()[1].function
    
    # Try to get synth info from caller's local variables, fallback if missing
    synth_id = caller_frame.f_locals.get('synth_id', 'UnknownSynth')
    pattern_set_name = caller_frame.f_locals.get('pattern_set_name', 'UnknownPatternSet')
    degree = caller_frame.f_locals.get('degree', 'UnknownDegree')
    
   
    return 440.0 * 2 ** ((midi_note - 69) / 12)

def parse_chord(chord_str, base_midi_note):
    """
    Convert a chord notation like "1+3+5" to a list of MIDI notes.
    
    Args:
        chord_str: String containing intervals separated by '+' (e.g., "1+3+5")
        base_midi_note: The base MIDI note to which intervals are added
        
    Returns:
        List of MIDI note numbers
    """
    notes = []
    for degree in chord_str.split('+'):
        if degree in interval_to_semitone:
            midi_note = base_midi_note + interval_to_semitone[degree]
            notes.append(midi_note)
    return notes

# Count progressions at a given emotional level
def get_progression_length(pattern_index):
    """Get the number of chords in the progression for this pattern level"""
    return len(PIANO_PATTERNS[pattern_index])

# Get a specific chord pattern from the progression
def get_chord_pattern(pattern_index, chord_index):
    """Get a specific chord pattern from the progression"""
    progression = PIANO_PATTERNS[pattern_index]
    return progression[chord_index % len(progression)]

# Cycle through the progression
def get_current_chord_in_progression(pattern_index, progression_step):
    """Get the current chord based on how far we are in the progression"""
    progression = PIANO_PATTERNS[pattern_index]
    chord_index = progression_step % len(progression)
    return progression[chord_index]

# Get progression info
def get_progression_info(pattern_index):
    """Return progression length and all chord patterns"""
    progression = PIANO_PATTERNS[pattern_index]
    return {
        'length': len(progression),
        'chords': progression
    }

def transpose_note_to_key(midi_note, from_key=0, to_key=None):
    """Transpose a MIDI note from one key to another"""
    if to_key is None:
        to_key = current_key
    return midi_note + (to_key - from_key)

def transpose_pattern_to_key(pattern, key_offset):
    """Transpose all notes in a pattern by key offset"""
    # Handle bass patterns, piano patterns, etc.
    pass

def find_next_chord_in_pattern(pattern_set, current_pattern_index, current_measure, current_step, 
                              search_ahead_steps=32, target_pattern_index=None):
    """
    Scan through pattern(s) to find the next actual chord, regardless of position.
    
    Args:
        pattern_set: The pattern set to search (PIANO_PATTERNS, etc.)
        current_pattern_index: Current pattern being played
        current_measure: Current measure within pattern
        current_step: Current step within measure (0-15)
        search_ahead_steps: How many steps ahead to search
        target_pattern_index: If transitioning, the target pattern to search
        
    Returns:
        dict with 'chord', 'steps_ahead', 'measure', 'step' of next chord, or None
    """
    
    # Start search from current position
    search_pattern = target_pattern_index if target_pattern_index is not None else current_pattern_index
    pattern = pattern_set[search_pattern]
    
    current_absolute_step = (current_measure * 16) + current_step
    
    for steps_ahead in range(1, search_ahead_steps + 1):
        future_absolute_step = current_absolute_step + steps_ahead
        
        # Handle pattern wraparound
        future_measure = (future_absolute_step // 16) % len(pattern)
        future_step = future_absolute_step % 16
        
        # Get the chord at this position
        measure_pattern = pattern[future_measure]
        if future_step < len(measure_pattern):
            chord = measure_pattern[future_step]
            
            # Skip 'c' (continue) and 0 (rest) - look for actual chords
            if chord not in ['c', 0] and isinstance(chord, str):
                # Check for Roman numeral chords (your pattern format)
                if any(c in "ivIV" for c in chord) or any(c in "º+*7M#b" for c in chord):
                    return {
                        'chord': chord,
                        'steps_ahead': steps_ahead,
                        'measure': future_measure,
                        'step': future_step,
                        'absolute_step': future_absolute_step
                    }
    
    return None  # No chord found in search range

def calculate_key_change(old_pattern_index, new_pattern_index, pivot_chord, proto_chord, target_chord):
    """
    Calculate what key change should occur based on pattern transition and pivot chord analysis.
    """
    global current_key
    
    #print(f"current key at time of calculation is {current_key}")
    # Helper function to check if a chord is a major triad
    def is_major_triad(chord_str):
        if not chord_str or chord_str in ['c', 0]:
            return False
        base_chord = chord_str.replace('#', '').replace('b', '').replace('7', '').replace('M', '').replace('*', '')
        return base_chord in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'] and base_chord.isupper()

    def is_minor_triad(chord_str):
        if not chord_str or chord_str in ['c',0]:
            return False
        base_chord = chord_str.replace('#', '').replace('b', '').replace('7', '').replace('M', '').replace('*', '')
        return base_chord in ['i','ii','iii','iv','v','vi','vii'] and base_chord.islower()

    def is_diminished_triad(chord_str):
        if not chord_str or chord_str in ['c', 0]:
            return False
        base_chord = chord_str.replace('#', '').replace('b', '').replace('7', '').replace('M', '').replace('*', '')
        return base_chord in ['iº', 'iiº', 'iiiº', 'ivº', 'vº', 'viº', 'viiº'] and 'º' in chord_str

    def is_augmented_triad(chord_str):
        if not chord_str or chord_str in ['c', 0]:
            return False
        base_chord = chord_str.replace('#', '').replace('b', '').replace('7', '').replace('M', '').replace('*', '')
        return base_chord in ['I+', 'II+', 'III+', 'IV+', 'V+', 'VI+', 'VII+'] and '+' in chord_str

    def get_chord_root_semitone(chord_str):
        #print(f"accesing get_chord_root_semitone")
        if chord_str is None:
            #print(f"chord is coming back none")
            return None
        if chord_str in roman_to_scale_degree:
            #print(f"chord is in roman_to_scale_degree")
            scale_degree = roman_to_scale_degree[chord_str]
            if scale_degree in interval_to_semitone:
                return interval_to_semitone[scale_degree]
        
        # Try stripping all extensions and quality symbols
        base_chord = chord_str.replace('+', '').replace('º', '').replace('7', '').replace('M', '').replace('*', '')
        if base_chord in roman_to_scale_degree:
            
            scale_degree = roman_to_scale_degree[base_chord]
            if scale_degree in interval_to_semitone:
                return interval_to_semitone[scale_degree]
        
        #print(f"base_chord not in roman_to_scale_degree, base_chord = {base_chord}")
        return None
    # Get chord roots - all functions will need this
    pivot_root = get_chord_root_semitone(pivot_chord)
    proto_root = get_chord_root_semitone(proto_chord)
    target_root = get_chord_root_semitone(target_chord)
    
    def calculate_standard_key_change():
        """Standard harmonic interval matching key change calculation"""
        if pivot_root is not None and proto_root is not None and target_root is not None:
            
            proto_to_target_interval = (target_root - proto_root) % 12
            #print(f" Proto_To_target_interval: {proto_to_target_interval} = target root: {target_root} - proto_root: {proto_root}")
            pivot_absolute_semitone = (current_key + pivot_root) % 12
            #print(f"pivot_absolute_semitone: {pivot_absolute_semitone}, current_key: {current_key}, pivot_root: {pivot_root}")
            desired_target_pitch = (pivot_absolute_semitone + proto_to_target_interval) % 12
            #print(f"Desired_target_pitch: {desired_target_pitch}")
            key_change_to = (desired_target_pitch - target_root) % 12
            #print(f"key_change_to: {key_change_to}")
            
            if key_change_to > 6:
                key_change_to -= 12
            
            return key_change_to
        else:
            print(f"It elsed!")
            return 0
    
    # Determine chord types
    pivot_is_major = is_major_triad(pivot_chord)
    #if pivot_is_major:
        #print(f"pivot is major: {pivot_chord}")
    proto_is_major = is_major_triad(proto_chord)
    #if proto_is_major:
        #print(f"proto is major:{proto_chord}")
    target_is_major = is_major_triad(target_chord)
    #if target_is_major:
        #print(f"target is major: {target_chord}")

    pivot_is_minor = is_minor_triad(pivot_chord)
    #if pivot_is_minor:
        #print(f"pivot is minor: {pivot_chord}")
    proto_is_minor = is_minor_triad(proto_chord)
    #if proto_is_minor:
        #print(f"proto is minor: {proto_chord}")
    target_is_minor = is_minor_triad(target_chord)
    #if target_is_minor:
        #print(f"target is minor: {target_chord}")
    
    pivot_is_dim = is_diminished_triad(pivot_chord)
    #if pivot_is_dim:
        #print(f"pivot is dim: {pivot_chord}")
    proto_is_dim = is_diminished_triad(proto_chord)
    #if proto_is_dim:
        #print(f"proto is dim: {proto_chord}")
    target_is_dim = is_diminished_triad(target_chord)
    #if target_is_dim:
        #print(f"target is dim: {target_chord}")

    pivot_is_aug = is_augmented_triad(pivot_chord)
    #if pivot_is_aug:
        #print(f"pivot is aug: {pivot_chord}")
    proto_is_aug = is_augmented_triad(proto_chord)
    #if proto_is_aug:
        #print(f"proto is aug: {proto_chord}")
    target_is_aug = is_augmented_triad(target_chord)
    #if target_is_aug:
        #print(f"target is aug: {target_chord}")


    # AUG pivot cases
    if pivot_is_aug and proto_is_aug:
        return calculate_standard_key_change()

    elif pivot_is_aug and proto_is_major:
        return calculate_standard_key_change()

    elif pivot_is_aug and proto_is_minor:
        original_pivot = pivot_root
        pivot_root = (pivot_root + 1) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_aug and proto_is_dim:
        original_pivot = pivot_root
        pivot_root = (pivot_root - 2) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    # MAJOR pivot cases
    elif pivot_is_major and proto_is_aug:
        return calculate_standard_key_change()

    elif pivot_is_major and proto_is_major:
        return calculate_standard_key_change()

    elif pivot_is_major and proto_is_minor:
        original_pivot = pivot_root
        pivot_root = (pivot_root - 3) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_major and proto_is_dim:
        original_pivot = pivot_root
        pivot_root = (pivot_root + 4) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result
    
    # MINOR pivot cases
    elif pivot_is_minor and proto_is_aug:
        original_pivot = pivot_root
        pivot_root = (pivot_root - 1) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_minor and proto_is_major:
        original_pivot = pivot_root
        pivot_root = (pivot_root - 4) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_minor and proto_is_minor:
        return calculate_standard_key_change()

    elif pivot_is_minor and proto_is_dim:
        original_pivot = pivot_root
        pivot_root = (pivot_root - 3) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    # DIM pivot cases
    elif pivot_is_dim and proto_is_aug:
        original_pivot = pivot_root
        pivot_root = (pivot_root - 4) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_dim and proto_is_major:
        original_pivot = pivot_root
        #print(f"pivot root before slide: {pivot_root}")
        pivot_root = (pivot_root - 4) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_dim and proto_is_minor:
        original_pivot = pivot_root
        pivot_root = (pivot_root + 5) % 12
        result = calculate_standard_key_change()
        pivot_root = original_pivot
        return result

    elif pivot_is_dim and proto_is_dim:
        return calculate_standard_key_change()

    else:
        return 0
    
def apply_key_change(key_changer):
    """
    Apply a key change by the specified number of semitones.
    
    Args:
        key_changer: new key!
    """
    global current_key
    
    #print(f"Current key at time of application changes from {current_key}")
    if key_changer != 0:
        old_key = current_key
        current_key = key_changer
    #print(f" to {current_key}")

def apply_provisional_key_change(key_changer):
    """
    Calculate what the target key would be if this change were applied,
    but don't actually change the global current_key.
    
    Returns the provisional target key for bass context only.
    """
    global current_key
    
    if key_changer != 0:
        provisional_key = key_changer
        return provisional_key
    else:
        return current_key
    
def clamp_bass_to_octave(midi_note, min_midi=24, max_midi=46):
    """
    Clamp bass note to a specific MIDI range by shifting octaves.
    Default range: C1 (24) to C3 (47) - typical bass range
    """
    while midi_note < min_midi:
        midi_note += 12
    while midi_note > max_midi:
        midi_note -= 12
    return midi_note

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
    global start_sample_gain, target_sample_gain
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
                
                if current_synth_id in start_sample_gain and current_synth_id in target_sample_gain:
                    synth.set_sample_gain(start_sample_gain[current_synth_id] + (target_sample_gain[current_synth_id] - start_sample_gain[current_synth_id]) * progress, current_synth_id)
                
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
            sound = fade_in_kick_sample(sound, SAMPLE_RATE)
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

# EQ processing caches for thread-safe drum playback
kick_eq_cache = {}
snare_eq_cache = {}
cymbal_eq_cache = {}

def get_eq_processed_sound(original_sound, cache_dict, cache_key, slider_val):
    """Get EQ-processed sound from cache or create it"""
    # Quantize slider to reduce cache size (100 steps should be enough)
    quantized_slider = round(slider_val * 100) / 100.0
    eq_key = f"{cache_key}_{int(quantized_slider * 100)}"
    
    if eq_key not in cache_dict:
        cache_dict[eq_key] = apply_global_eq_to_sound(original_sound, quantized_slider)
    
    return cache_dict[eq_key]

def clear_eq_caches():
    """Clear all EQ caches when needed"""
    global kick_eq_cache, snare_eq_cache, cymbal_eq_cache
    kick_eq_cache.clear()
    snare_eq_cache.clear()
    cymbal_eq_cache.clear()

# ============================================================================
# SAMPLE-BASED PLAY FUNCTIONS
# ============================================================================


def play_kick_sample_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms / 1000)
        original_sound = kick_cache.get(label)
        if original_sound:
            with slider_val_lock:
                slider = slider_val
            # Get EQ-processed sound from cache (thread-safe)
            sound = get_eq_processed_sound(original_sound, kick_eq_cache, label, slider)

            # --- Pure volume / gain (no pseudo EQ) -------------------------
            global_gain_db = slider_to_global_gain_db(slider)
            kick_boost_db = KICK_BOOST_DB        # extra punch for kicks
            total_gain_db = gain_db + kick_boost_db # + global_gain_db
            volume = DRUMS_MASTER_VOLUME * (10 ** (total_gain_db / 20))
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()

def play_snare_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms/1000)
        actual_play_time = time.time()
        #print(f"SNARE ACTUAL PLAY: step {master_step} played at {actual_play_time:.6f}")
        original_sound = snare_cache.get(label)
        if original_sound:
            with slider_val_lock:
                slider = slider_val
            # Get EQ-processed sound from cache (thread-safe)
            sound = get_eq_processed_sound(original_sound, snare_eq_cache, label, slider)

            # Volume only (EQ already applied)
            total_gain_db = gain_db + slider_to_global_gain_db(slider)
            volume = DRUMS_MASTER_VOLUME * (10 ** (total_gain_db / 20))
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()

def play_cymbal_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms/1000)
        original_sound = cymbal_cache.get(label)
        if original_sound:
            with slider_val_lock:
                slider = slider_val
            # Get EQ-processed sound from cache (thread-safe)
            sound = get_eq_processed_sound(original_sound, cymbal_eq_cache, label, slider)

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
    
    import time
    drum_trigger_time = time.time()
    #print(f"DRUM TRIGGER TIME: Step {step} triggered at {drum_trigger_time:.6f}")
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



        #==================================================================#
        #------------------------S~E~Q~U~E~N~C~E~R-------------------------#
        #==================================================================#

def synth_sequencer_thread(stop_event, synth, synth_id, slider_val_lock,):
    """Dedicated sequencer thread for a single synth instance."""
    global master_step, master_seconds_per_16th, master_current_bpm
    
    pattern_index = 0
    note_is_playing = False
    current_pattern_index_local = 8
    last_processed_step = -1

    # NEW: Add progression tracking
    measure_count = 0
    current_chord_index = 0
    
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
        
    # Determine if this is the bass synth
    is_bass_synth = pattern_set_name == "bass" or synth_instance.config.get("name") == "bass"
        
    while not stop_event.is_set():

        # Safely get the current slider value
        with slider_val_lock:
            current_slider_val = slider_val
        
        # Convert slider to target pattern index
        target_pattern_index = int(round(current_slider_val * (len(labels) - 1)))
        
        # Use master timing (no local BPM calculation)
        current_step = master_step
        seconds_per_16th = master_seconds_per_16th
        current_bpm = master_current_bpm

        # IMMEDIATE PATTERN CHANGE DETECTION (don't wait for measure boundary)
        global UPCOMING_PATTERN_INDEX, UPCOMING_TARGET_CHORD, UPCOMING_PROTO_CHORD, TRANSITIONAL_CHORD_SYMBOL
        if target_pattern_index != current_pattern_index_local and is_bass_synth and UPCOMING_PATTERN_INDEX != target_pattern_index:
            
            # Calculate transition immediately when slider moves
            UPCOMING_PATTERN_INDEX = target_pattern_index
            
            # Get current piano chord as pivot
            if current_chord_index < len(PIANO_PATTERNS[current_pattern_index_local]):
                pivot_chord = CURRENT_CHORD_SYMBOL  # Use the actual chord that's currently playing
            else:
                pivot_chord = "I"
            
            # Get what the target pattern would be at this same measure
            target_measure = (current_chord_index + 1) % len(PIANO_PATTERNS[target_pattern_index])
            target_chord_result = find_next_chord_in_pattern(PIANO_PATTERNS, target_pattern_index, target_measure, 0)
            UPCOMING_TARGET_CHORD = target_chord_result['chord'] if target_chord_result else PIANO_PATTERNS[target_pattern_index][target_measure][0]
            
            # Get the proto chord - the chord that comes before the target chord
            target_pattern = PIANO_PATTERNS[target_pattern_index]
            target_chord_index = target_measure  # We already calculated this above
            proto_chord_index = current_chord_index % len(PIANO_PATTERNS[target_pattern_index])
            proto_chord_result = find_next_chord_in_pattern([target_pattern], 0, proto_chord_index, 0)
            UPCOMING_PROTO_CHORD = proto_chord_result['chord'] if proto_chord_result else target_pattern[proto_chord_index][0]

            #print(f"Bass Thread just finished getting a bunch from piano")
            
            TRANSITIONAL_CHORD_SYMBOL = UPCOMING_PROTO_CHORD  # Make bass use proto chord immediately
            
            # CALCULATE KEY CHANGE IMMEDIATELY (but don't apply it yet)
            global UPCOMING_KEY_CHANGE, BASS_PREVIEW_KEY
            UPCOMING_KEY_CHANGE = calculate_key_change(
                current_pattern_index_local,
                target_pattern_index, 
                pivot_chord,
                UPCOMING_PROTO_CHORD,
                UPCOMING_TARGET_CHORD
            )
            
            # Apply provisional key change for bass preview context only
            BASS_PREVIEW_KEY = apply_provisional_key_change(UPCOMING_KEY_CHANGE)
            
            # Update bass root note based on preview key
            if UPCOMING_PROTO_CHORD is not None:
                chord_root = get_chord_root(UPCOMING_PROTO_CHORD)
                if chord_root:
                    CURRENT_CHORD_ROOT = chord_root
                else:
                    print(f"WARNING: Could not get root for chord {UPCOMING_PROTO_CHORD}")
            else:
                print("WARNING: UPCOMING_PROTO_CHORD is None, skipping root update")
                
            
        elif target_pattern_index == current_pattern_index_local and is_bass_synth:
            # Clear upcoming variables if we're back to current pattern
            UPCOMING_PATTERN_INDEX = None
            UPCOMING_TARGET_CHORD = None
            TRANSITIONAL_CHORD_SYMBOL = None
            UPCOMING_PROTO_CHORD = None
            BASS_PREVIEW_KEY = None

            

        # Get the pattern set for this synth
        pattern_set = SYNTH_PATTERN_SETS.get(pattern_set_name, BASS_PATTERNS)  # Fallback to BASS_PATTERNS
        
        # Actual Music Triggers
        # Wait for new step from master
        if current_step != last_processed_step:
            bass_pattern_ready.clear()
            #print(f"starting Bass Loop, step: {current_step}")


            # Wait for piano to set chord context first
            piano_chord_ready.wait()
            #print(f"Bass received piano chord signal, starting pattern analysis...")
            
            last_processed_step = current_step

            # PHASE 2: Bass pattern analysis (sets UPCOMING_* variables)  
            bass_pattern_ready.set()  # Signal: "Pattern analysis complete!"
            
            
            # Handle actual pattern change at measure boundary using upcoming info
            if UPCOMING_PATTERN_INDEX is not None and current_step == 0:
                current_pattern_index_local = UPCOMING_PATTERN_INDEX
                # Clear the upcoming variables after completing transition
                UPCOMING_PATTERN_INDEX = None
                UPCOMING_TARGET_CHORD = None
                UPCOMING_PROTO_CHORD = None
                # Stop any playing notes on pattern change
                if note_is_playing:
                    synth.note_off(synth_id)
                    note_is_playing = False
            
            # Use this synth's pattern set and get the current degree
            if pattern_set_name == "piano":
                time.sleep(0.01)
                continue
            else:
                # Use normal patterns for non-piano synths
                selected_pattern = pattern_set[current_pattern_index_local]
                pattern_position = pattern_index % len(selected_pattern)
                degree = selected_pattern[pattern_position]
                next_degree = selected_pattern[(pattern_index + 1) % len(selected_pattern)]
            
            # Update measure count when we complete 16 steps (one measure) 
            if current_step == 0 and pattern_index > 0:
                measure_count += 1
                # Reset measure count when progression completes
                progression_length = len(PIANO_PATTERNS[current_pattern_index_local])
                if measure_count >= progression_length:
                    measure_count = 0
                current_chord_index = measure_count
            
            # Check if this is the bass synth
            if is_bass_synth and degree not in (0, 'c'):
                # If it's a degree within our interval system (not just a raw MIDI note)
                if isinstance(degree, str) and degree in interval_to_semitone:
                    # Use transitional chord if set, otherwise use current piano chord
                    current_chord_symbol = TRANSITIONAL_CHORD_SYMBOL if TRANSITIONAL_CHORD_SYMBOL else CURRENT_CHORD_SYMBOL
                    #print(f"BASS DEBUG: Step {pattern_index}, Degree: {degree}, MIDI: {midi_note if 'midi_note' in locals() else 'calculating...'}")
                    #print(f"KEY DEBUG: current_key={current_key}, BASS_PREVIEW_KEY={BASS_PREVIEW_KEY}, transposed_base={base_midi_note + (BASS_PREVIEW_KEY if BASS_PREVIEW_KEY is not None else current_key)}")
                    #print(f"Step: {current_step}, current_chord_symbol: {current_chord_symbol}")
                    # Apply key transposition to bass - use preview key during transitions
                    if BASS_PREVIEW_KEY is not None:
                        transposed_base_midi_note = base_midi_note + BASS_PREVIEW_KEY
                    else:
                        transposed_base_midi_note = base_midi_note + current_key

                    
                    # Determine next chord with wraparound for progression cycling
                    if UPCOMING_PATTERN_INDEX is not None:
                        next_chord_progression_length = len(PIANO_PATTERNS[UPCOMING_PATTERN_INDEX])
                        next_chord_current_measure = measure_count % next_chord_progression_length
                        next_chord_next_measure_index = (next_chord_current_measure + 1) % next_chord_progression_length
                        next_chord_next_measure = PIANO_PATTERNS[UPCOMING_PATTERN_INDEX][next_chord_next_measure_index]
                        next_chord_result = find_next_chord_in_pattern(PIANO_PATTERNS, UPCOMING_PATTERN_INDEX, next_chord_current_measure, 0, target_pattern_index=UPCOMING_PATTERN_INDEX)
                        next_chord = next_chord_result['chord'] if next_chord_result else None
                    else:
                        progression_length = len(PIANO_PATTERNS[current_pattern_index_local])
                        current_measure_in_progression = measure_count % progression_length
                        next_measure_index = (current_measure_in_progression + 1) % progression_length
                        next_measure = PIANO_PATTERNS[current_pattern_index_local][next_measure_index]
                        next_chord_result = find_next_chord_in_pattern(PIANO_PATTERNS, current_pattern_index_local, current_measure_in_progression, current_step)
                        next_chord = next_chord_result['chord'] if next_chord_result else None
                    #print(f"PROGRESSION DEBUG: measure_count={measure_count}, current_measure_in_progression={current_measure_in_progression if UPCOMING_PATTERN_INDEX is None else next_chord_current_measure}, progression_length={progression_length if UPCOMING_PATTERN_INDEX is None else next_chord_progression_length}")
                    # Use upcoming target chord if slider has moved
                    target_chord = UPCOMING_TARGET_CHORD if UPCOMING_TARGET_CHORD else None

                    #print(f"BASS CHORD DEBUG: next_chord={next_chord}, target_chord={target_chord}, proto_chord = {UPCOMING_PROTO_CHORD}, step={current_step}")
                    # Calculate the note using the modal scale for the current chord  
                    midi_note = get_bass_note(
                        degree_str=degree,
                        chord_symbol=current_chord_symbol,
                        base_midi_note=transposed_base_midi_note,
                        next_chord=next_chord,
                        target_chord=target_chord
                    )

                    # Use this calculated note
                    freq = freq_from_midi(midi_note)
                    #print(f"BASS MODAL DEBUG: Degree {degree} → MIDI {midi_note} using chord {current_chord_symbol} in key {BASS_PREVIEW_KEY} from pattern {current_pattern_index_local}")

                    def delayed_bass_note(synth_id, freq):
                        #print(f"FIRST SAMPLE TO SPEAKER - Synth {synth_id} at {time.time():.6f}")
                        synth.set_frequency(freq, synth_id)
                        synth.note_on(synth_id)

                    freq = freq_from_midi(midi_note)
                    threading.Timer(PORTAUDIO_SLOWDOWN, delayed_bass_note, args=(synth_id, freq)).start()
                    
                    note_is_playing = True
                    
                    # Handle note duration based on the next step
                    if next_degree != 'c':
                        time.sleep(seconds_per_16th * duration_multiplier)
                        synth.note_off(synth_id)
                        note_is_playing = False
                    
                    # Skip the normal note processing
                    pattern_index = current_step  
                    pattern_index += 1  # Do the increment here
                    sequencer_barrier.wait()  # Hit the barrier 
                    continue

            
            # Apply delay for bass synth (matching drum delay)
            if is_bass_synth and degree not in (0, 'c'):  # Only delay actual notes
                # Get the delay from the same pattern used by drums
                step_idx = current_step % len(delay_patterns_ms[current_pattern_index_local])
                note_delay = delay_patterns_ms[current_pattern_index_local][step_idx]
                if note_delay > 0:
                    time.sleep(note_delay / 1000.0)  # Convert ms to seconds
                
                
            
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
                if isinstance(degree, str) and (degree in interval_to_semitone or any(c in "ivIV" for c in degree)):
                    midi_note = base_midi_note + interval_to_semitone[degree]
                    
                else:
                    midi_note = base_midi_note  # fallback to tonic if malformed
                synth.set_frequency(freq_from_midi(midi_note), synth_id)
                synth.note_on(synth_id)
                note_is_playing = True
            else:
                if isinstance(degree, str) and (degree in interval_to_semitone or any(c in "ivIV" for c in degree)):
                    midi_note = base_midi_note + interval_to_semitone[degree]
                else:
                    midi_note = None  # fallback to tonic if malformed
                synth.set_frequency(freq_from_midi(midi_note), synth_id)
                synth.note_on(synth_id)
                note_is_playing = True
                time.sleep(seconds_per_16th * duration_multiplier)
                synth.note_off(synth_id)
                note_is_playing = False
            
            # Increment this synth's pattern index
            pattern_index += 1
            
            # Signal master timing that bass is complete
            sequencer_barrier.wait()
            
            
        else:
            time.sleep(0.0001)  # Small sleep while waiting for next step

def poly_synth_sequencer_thread(stop_event, synth_name, slider_val_lock):
    """Dedicated sequencer thread for a polyphonic synth."""
    global CURRENT_CHORD_ROOT, CURRENT_CHORD_SYMBOL, TRANSITIONAL_CHORD_SYMBOL, PREVIOUS_CHORD_SYMBOL, pivot_chord, target_chord, proto_chord, current_key, chord_str
    global master_step, master_seconds_per_16th, master_current_bpm

    last_processed_step = -1
    pattern_index = 0
    current_pattern_index_local = 8
    last_active_chord = None
    measure_count = 0

    # Get the first chord of the starting pattern
    initial_progression = PIANO_PATTERNS[8]  # Neutral pattern
    first_chord_result = find_next_chord_in_pattern([initial_progression], 0, 0, 0)
    first_chord = first_chord_result['chord'] if first_chord_result else initial_progression[0][0]
    if first_chord != 'c' and first_chord != 0:
        last_active_chord = first_chord

    currently_sounding_chord = last_active_chord  # What chord is actually playing right now
    
    # Get the PolySynth instance
    poly_synth = POLY_SYNTH_INSTANCES[synth_name]
    
    while not stop_event.is_set():
        
        # Safely get the current slider value
        with slider_val_lock:
            current_slider_val = slider_val
        
        # Convert slider to target pattern index
        target_pattern_index = int(round(current_slider_val * (len(labels) - 1)))
        
        # Use master timing
        current_step = master_step
        seconds_per_16th = master_seconds_per_16th
        current_bpm = master_current_bpm

        # Get configuration parameters
        pattern_set_name = poly_synth.config["patternSet"]
        duration_multiplier = poly_synth.config.get("durationMultiplier", 0.5)
        
        # Get the pattern set for this synth
        pattern_set = SYNTH_PATTERN_SETS.get(pattern_set_name, BASS_PATTERNS)
        
        # Wait for new step from master
        if current_step != last_processed_step:
            # Clear events for fresh synchronization each step
            piano_chord_ready.clear()
            #print(f"Starting Poly_SYnth Loop, step: {current_step}")
            last_processed_step = current_step

            # Handle pattern change at measure boundary
            # DEBUG: Log at measure boundary (step 0)
            if current_step == 0:
                print(f"MEASURE BOUNDARY - Step: {current_step}, Pattern: {current_pattern_index_local}, Target: {target_pattern_index}")
            if target_pattern_index != current_pattern_index_local and current_step == 0:
                #print(f"Step 2 Poly_SYnth Loop, step: {current_step}")
                current_pattern_index_local = target_pattern_index
                # Capture what's actually playing right now as the pivot
                if currently_sounding_chord is not None:
                    pivot_chord = currently_sounding_chord
                elif last_active_chord is not None:
                    pivot_chord = last_active_chord
                
                # What chord would we have been coming from in the new progression?
                # If we're at measure_count in the new progression, 
                # proto would be the previous chord in that progression
                new_progression = PIANO_PATTERNS[target_pattern_index]
                current_position = measure_count % len(new_progression)
                #print(f"Current_Position: {current_position}")
                if current_position > 0:
                    proto_chord_result = find_next_chord_in_pattern([new_progression], 0, current_position, 0)
                    proto_chord = proto_chord_result['chord'] if proto_chord_result else new_progression[current_position][0]
                else:
                    proto_chord_result = find_next_chord_in_pattern([new_progression], 0, 0, 0)
                    proto_chord = proto_chord_result['chord'] if proto_chord_result else new_progression[0][0]
                
                # Target is the next chord we'll play
                target_measure = (current_position+1) % len(new_progression)
                target_chord_result = find_next_chord_in_pattern([new_progression], 0, target_measure, 0)
                target_chord = target_chord_result['chord'] if target_chord_result else new_progression[target_measure][0]
                
                
                # Calculate and apply key change
                key_change = calculate_key_change(
                    current_pattern_index_local, 
                    target_pattern_index,
                    pivot_chord,
                    proto_chord, 
                    target_chord
                )
                apply_key_change(key_change)
                #print(f"KEY_CHANGE: {key_change}")
                # Set bass to immediately use proto chord context for smooth transition
                TRANSITIONAL_CHORD_SYMBOL = proto_chord
                
                
                # Stop any active notes when changing patterns
                current_notes = list(poly_synth.active_notes.keys())
                for note in current_notes:
                    poly_synth.note_off(note)
            
            base_midi_note = poly_synth.config["baseMidiNote"] + current_key
            # Increment measure count when we complete 16 steps (one measure)
            if current_step == 0 and pattern_index > 0:
                measure_count += 1
                
            # Use this synth's pattern set and get the current degree
            if pattern_set_name == "piano":
                # Use progression instead of single pattern
                current_chord_pattern = get_current_chord_in_progression(
                    current_pattern_index_local, 
                    measure_count
                )
                selected_pattern = current_chord_pattern
                

            else:
                selected_pattern = pattern_set[current_pattern_index_local]


            pattern_position = pattern_index % len(selected_pattern)
            degree = selected_pattern[pattern_position]
            
            # Handle each type of note/chord
            if degree == 0:
                # Explicit rest - stop any active notes
                current_notes = list(poly_synth.active_notes.keys())
                for note in current_notes:
                    poly_synth.note_off(note)
                last_active_chord = None
            
            elif degree == 'c' and last_active_chord is not None:
                # Continue previous chord/note - do nothing
                currently_sounding_chord = last_active_chord
            
            # Handle Roman numeral chord notation
            elif isinstance(degree, str) and degree != 'c' and any(char in "ivIV" for char in degree):
                # It's a Roman numeral chord - parse and play it
                
                # Get the chord root from the Roman numeral
                chord_root = get_chord_root(degree)
                if chord_root:
                    CURRENT_CHORD_ROOT = chord_root  # No need for global here anymore
                    
                # Track previous chord for contextual scale selection
                PREVIOUS_CHORD_SYMBOL = CURRENT_CHORD_SYMBOL
                #print(f"Updating Current Chord Symbol Now")
                CURRENT_CHORD_SYMBOL = degree
                
                # Clear transitional state since piano is now playing the actual chord
                TRANSITIONAL_CHORD_SYMBOL = None
                
                # Parse the chord to get MIDI notes
                original_base = poly_synth.config["baseMidiNote"]
                chord_notes = parse_roman_numeral_chord(degree, base_midi_note, original_base)
                
                # Only play if chord_notes is a list (not 'c' or 0)
                if isinstance(chord_notes, list):
                    # Always play the chord fresh to ensure proper triggering
                    def delayed_piano_chord(poly_synth, chord_notes, degree, current_key, current_step):
                        #print(f"FIRST SAMPLE TO SPEAKER - Piano at {time.time():.6f}")
                        poly_synth.play_chord(chord_notes)
                        #print(f"PIANO: {chord_notes}, CHORD: {degree}, Key: {current_key}, step: {current_step}")

                    # Apply delay pattern for piano (same as bass)
                    step_idx = current_step % len(delay_patterns_ms[current_pattern_index_local])
                    note_delay = delay_patterns_ms[current_pattern_index_local][step_idx]
                    total_delay = (note_delay / 1000.0) + PIANO_DELAY_OFFSET  # Convert ms to seconds
                    time.sleep(PIANO_DELAY_OFFSET + total_delay)
                    # DEBUG: Log before piano chord trigger
                    print(f"BEFORE PIANO CHORD - Step: {current_step}, Measure: {measure_count}, Chord: {degree}")

                    threading.Timer(PORTAUDIO_SLOWDOWN, delayed_piano_chord, args=(poly_synth, chord_notes, degree, current_key, current_step)).start()
                    print(f"PIANO: {chord_notes}, CHORD: {degree}, Key: {current_key}, step: {current_step}")
                    last_active_chord = degree
                    currently_sounding_chord = degree
                    
   
                    
            # Handle traditional interval-based chord notation (e.g., 1+3+5)
            elif isinstance(degree, str) and '+' in degree:
                # It's a chord with interval notation - parse and play it

                
                # Set the global chord root to the first part of this chord
                chord_parts = degree.split('+')
                if chord_parts:
                    CURRENT_CHORD_ROOT = chord_parts[0]  # No need for global here anymore

                
                # With this more verbose version:
                chord_notes = parse_chord(degree, base_midi_note)

                
                # First stop ALL currently playing notes
                current_notes = list(poly_synth.active_notes.keys())

                for note in current_notes:
                    poly_synth.note_off(note)
                # Small delay to ensure notes are stopped
                time.sleep(0.01)
                # Now play only the exact notes we specified
                poly_synth.play_chord(chord_notes)
                last_active_chord = degree
                
            elif degree not in (0, 'c'):
                # Single note
                
                if isinstance(degree, str) and degree in interval_to_semitone:
                    midi_note = base_midi_note + interval_to_semitone[degree]
                    
                    # Stop any currently playing notes
                    current_notes = list(poly_synth.active_notes.keys())
                    for note in current_notes:
                        poly_synth.note_off(note)
                    
                    # Play the new note
                    poly_synth.note_on(midi_note)
                    last_active_chord = degree
                    
                    # For non-chord single notes, use the duration multiplier
                    time.sleep(seconds_per_16th * duration_multiplier)
                    poly_synth.note_off(midi_note)
                    last_active_chord = None
             

             # PHASE 1: Piano sets chord first
            piano_chord_ready.set()  # Signal: "Chord context ready!"
            
            
            # Wait for bass pattern analysis to complete
            bass_pattern_ready.wait()
            #print(f"Piano finished, bass pattern analysis complete.")
                
            
            # Increment pattern index and update step
            pattern_index += 1
            
            sequencer_barrier.wait()
            
        else:
            time.sleep(0.001)  # Small sleep while waiting for next step

def sequencer_timing_only(stop_event, synth, slider_val_lock):
    global current_pattern_index, previous_slider_val, synth_id
    global master_step, master_seconds_per_16th, master_current_bpm, master_next_trigger
    
    master_step = 0
    master_next_trigger = time.time() + GLOBAL_DELAY
    drum_delay = DRUM_DELAY_OFFSET
    
    # Create a thread for each synth instance
    synth_threads = []
    
            # Create threads for polyphonic synths
    poly_synth_threads = []
    
    # Start a thread for each polyphonic synth
    for synth_name in POLY_SYNTH_INSTANCES:
        thread = threading.Thread(
            target=poly_synth_sequencer_thread,
            args=(stop_event, synth_name, slider_val_lock),
            daemon=True
        )
        thread.start()
        poly_synth_threads.append(thread)

    # Start a separate thread for each synth instance
    for current_synth_id in SYNTH_INSTANCES:
        thread = threading.Thread(
            target=synth_sequencer_thread,
            args=(stop_event, synth, current_synth_id, slider_val_lock),
            daemon=True
        )
        thread.start()
        synth_threads.append(thread)
    
    while not stop_event.is_set():
        with slider_val_lock:
            current_slider_val = slider_val
        
        target_pattern_index = int(round(current_slider_val * (len(labels) - 1)))
        if target_pattern_index != current_pattern_index and master_step == 0:
            current_pattern_index = target_pattern_index
        
        # Update BPM with smooth ramping (MASTER ONLY)
        master_current_bpm = update_bpm_from_slider(current_slider_val)
        seconds_per_beat = 60 / master_current_bpm
        master_seconds_per_16th = seconds_per_beat / 4
        
        # Timing check for step advancement
        now = time.time()
        if now >= master_next_trigger:
            # Trigger drums for this step
            trigger_drums_for_step(master_step, current_pattern_index, drum_delay * 1000)
            # Wait for all sequencers to complete current step
            sequencer_barrier.wait()

            # Advance step counter
            master_step = (master_step + 1) % STEPS_PER_MEASURE
            master_next_trigger += master_seconds_per_16th

        time.sleep(0.001)  # Small sleep to avoid CPU hogging

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
    global start_sample_gain, target_sample_gain
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
    
    # Add compensation globals
    global _last_slider_val

    with slider_val_lock:
        new_val = float(val)
        old_val = _last_slider_val
        slider_val = new_val

        # Update EVERY synth in the registry
        for current_synth_id, synth_instance in SYNTH_INSTANCES.items():
            config = synth_instance.config
            
            # Apply compensation BEFORE changing parameters if there's a significant change
            #if abs(new_val - old_val) > 0.01:  # Only compensate for significant changes
            #    apply_parameter_compensation(synth_instance, old_val, new_val)

            # ADSR envelope parameters
            target_attack[current_synth_id] = slider_to_log_range(new_val, config["minAttack"], config["maxAttack"])
            target_decay[current_synth_id] = slider_to_log_range(1 - new_val, config["minDecay"], config["maxDecay"])
            target_release[current_synth_id] = slider_to_log_range(1 - new_val, config["minRelease"], config["maxRelease"])
            target_sustain[current_synth_id] = config["minSustainDb"] + new_val * (config["maxSustainDb"] - config["minSustainDb"])

            # Oscillator gains
            target_sine_gain[current_synth_id] = slider_to_log_gain(new_val, config["min_osc1_gain"], config["max_osc1_gain"])
            target_sample_gain[current_synth_id] = slider_to_log_gain(new_val, config["min_osc2_gain"], config["max_osc2_gain"])

            # Store start points for ramps
            start_attack[current_synth_id] = target_attack[current_synth_id]
            start_decay[current_synth_id] = target_decay[current_synth_id]
            start_release[current_synth_id] = target_release[current_synth_id]
            start_sustain[current_synth_id] = target_sustain[current_synth_id]
            
            # Immediate update so sustain tracks the slider like other ADSR params
            synth.set_sustain_level(target_sustain[current_synth_id], current_synth_id)
            
            start_sine_gain[current_synth_id] = target_sine_gain[current_synth_id]
            start_sample_gain[current_synth_id] = target_sample_gain[current_synth_id]

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
            
            
        # Update polyphonic synths (like piano) that have oscillators with min/max gains
        for poly_synth_name, poly_synth in POLY_SYNTH_INSTANCES.items():
            if hasattr(poly_synth, 'config') and 'oscillators' in poly_synth.config:
                osc_list = poly_synth.config['oscillators']
                
                # Apply simple compensation for piano volume dip
                apply_simple_piano_compensation(poly_synth, new_val)
                
                for voice in poly_synth.voices:
                    for idx, osc in enumerate(osc_list):
                        if idx < len(osc_list):
                            min_g = float(osc.get("min_gain", 0.0))
                            max_g = float(osc.get("max_gain", 1.0))
                            g = slider_to_log_gain(new_val, min_g, max_g)
                            synth.set_osc_gain_at(g, idx, voice.synth_id)
        
        # Update the last slider value for next comparison
        _last_slider_val = new_val

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    stop_event = threading.Event()

    # Initialize the synthesizer system
    synth.initialize_synth_system()
    
    # Temporarily override start_synth to prevent auto-starting
    original_start_synth = synth.start_synth
    synth.start_synth = lambda x: None
    
    # Create synths without auto-starting
    bass_synth = SynthInstance(BASS_CONFIG)
    piano_poly = PolySynth(PIANO_CONFIG, voice_count=4)

    POLY_SYNTH_INSTANCES["piano"] = piano_poly
    
    # Pre-initialize all parameters
    on_slider_change(slider_val)  # Use default slider value (0.5)
    
    # Restore start_synth function and start all synths explicitly
    synth.start_synth = original_start_synth
    for current_synth_id in SYNTH_INSTANCES:
        synth.start_synth(current_synth_id)
    
    # Give audio system time to stabilize
    time.sleep(0.5)
    
    # Now start sequencer thread
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

    label = tk.Label(root, text="HandBand")
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
