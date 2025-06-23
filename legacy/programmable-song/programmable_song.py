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

# === Globals ===
sample_rate = 44100
bpm_lock = threading.Lock()
slider_val_lock = threading.Lock()

min_bpm = 80
max_bpm = 180
default_bpm = 120
base_gain_db = 10
rest_duration = 0

tonic = 36

current_bpm = default_bpm
slider_val = 0.5

steps_per_measure = 16
current_group_index = 8

start_bpm = default_bpm
target_bpm = default_bpm
ramp_start_time = None
ramp_duration = None

note_duration = 60/current_bpm

# Kick trigger patterns for each slider level (label)
kick_patterns = [
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

snare_patterns = [
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

cymbal_patterns = [
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

bass_patterns = [
    ['1','c','c','c',  'c','c','c','c', '1','c','c','c', '1','c','c','c', ], #SadLevel8
    ['1','c','b2','c', 'b3','c','4','c', '5','c','b6','c', 'b7','c','8','c', ],
    ['1','c','2','c', 'b3','c','4','c', '5','c','b6','c', 'b7','c','8','c', ],
    ['1','c','2','c', 'b3','c','4','c', '5','c','b6','c', 'b7','c','8','c', ],
    ['1','c','2','c', 'b3','c','4','c', '5','c','b6','c', 'b7','c','8','c', ],
    ['1','c','2','c', 'b3','c','4','c', '5','c','6','c', 'b7','c','8','c', ],
    ['1','c','2','c', 'b3','c','4','c', '5','c','6','c', 'b7','c','8','c', ],
    ['1','c','2','c', 'b3','c','4','c', '5','c','6','c', 'b7','c','8','c', ],
    ['1','c','2','c', '3','c','4','c', '5','c','6','c', 'b7','c','8','c', ], #Neutral
    ['1','c','2','c', '3','c','4','c', '5','c','6','c', 'b7','c','8','c', ],
    ['1','c','2','c', '3','c','4','c', '5','c','6','c', 'b7','c','8','c', ],
    ['1','c','2','c', '3','c','4','c', '5','c','6','c', '7','c','8','c', ],
    ['1','c','2','c', '3','c','4','c', '5','c','6','c', '7','c','8','c', ],
    ['1','c','2','c', '3','c','4','c', '5','c','6','c', '7','c','8','c', ],
    ['1','c','2','c', '3','c','#4','c', '5','c','6','c', '7','c','8','c', ],
    ['1','c','2','c', '3','c','#4','c', '5','c','6','c', '7','c','8','c', ],
    ['1','c','c','c',  'c','c','c','c', '1','c','c','c', '1','c','c','c', ], #HappyLevel8
]


# Delay patterns
# Delay patterns
delay_patterns_ms = []
base_sad = [100, 79, 63, 50, 40, 32, 25, 0]  # 8 sad levels

# 1) Sad delays (levels 8→1)
for d in base_sad:
    delay_patterns_ms.append([0]*4 + [d]*12)

# 2) Neutral (level 0)
delay_patterns_ms.append([0]*16)

# 3) Happy delays (levels 1→8)
happy = [int(0.25 * d) for d in reversed(base_sad)]
for d in happy:
    pattern = [0]*16
    for i in [1,3,5,7,9,11,13,15]:
        pattern[i] = d
    delay_patterns_ms.append(pattern)


# Global accent matrix (gain in dB)
global_accents = [
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # SadLevel8
    [0.03, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.09, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.19, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.34, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.56, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.90, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [1.39, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [2.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],  # Neutral first beat = 2.0
    [1.39, 0.00, 0.00, 0.00, 0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.50, 0.00, 0.00, 0.00],
    [0.90, 0.00, 0.00, 0.00, 0.75, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.75, 0.00, 0.00, 0.00],
    [0.56, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00],
    [0.34, 0.00, 0.00, 0.00, 1.25, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.25, 0.00, 0.00, 0.00],
    [0.19, 0.00, 0.00, 0.00, 1.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.50, 0.00, 0.00, 0.00],
    [0.09, 0.00, 0.00, 0.00, 1.75, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.75, 0.00, 0.00, 0.00],
    [0.03, 0.00, 0.00, 0.00, 1.90, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.90, 0.00, 0.00, 0.00],
    [0.00, 0.00, 0.00, 0.00, 2.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 2.00, 0.00, 0.00, 0.00],  # HappyLevel8 first beat = 0.0
]

pygame.mixer.init()

def slider_to_bpm(val):
    log_min = math.log(min_bpm)
    log_max = math.log(max_bpm)
    bpm_log = log_min + val * (log_max - log_min)
    return math.exp(bpm_log)

def bpm_to_slider(bpm_val):
    log_min = math.log(min_bpm)
    log_max = math.log(max_bpm)
    return (math.log(bpm_val) - log_min) / (log_max - log_min)

def slider_to_global_gain_db(slider):
    # Move from -5 dB at slider=0 to 0 dB at slider=0.5 and up to +5 dB at slider=1
    if slider <= 0.5:
        t = slider / 0.5
        gain_db = -5 + 5 * (math.log10(1 + 9 * t))
    else:
        t = (slider - 0.5) / 0.5
        gain_db = 0 + 5 * (math.log10(1 + 9 * t))
    return gain_db

def slider_to_global_highshelf_db(slider):
    # -2 dB at 0, 0 dB at 0.5, +2 dB at 1, logarithmic interpolation in between
    if slider <= 0.5:
        t = slider / 0.5
        # interpolate logarithmically from -2 to 0 dB
        gain_db = -2 + 2 * (math.log10(1 + 9 * t))
    else:
        t = (slider - 0.5) / 0.5
        # interpolate logarithmically from 0 to +2 dB
        gain_db = 0 + 2 * (math.log10(1 + 9 * t))
    return gain_db

def slider_to_lowmid_db(slider):
    # -1 dB at 0, 0 dB at 0.5, +1 dB at 1 over 100–200 Hz, logarithmic in between
    if slider <= 0.5:
        t = slider / 0.5
        gain_db = 1 - (1 * math.log10(1 + 9 * t))
    else:
        t = (slider - 0.5) / 0.5
        gain_db = 0 - (1 * math.log10(1 + 9 * t))
    return gain_db

# Reverse map: interval name to semitone offset
interval_to_semitone = {
    '-1':-12, '-b2':-11, '-2':-10,
    '-b3':-9, '-3':-8, '-4':-7,
    '-#4':-6, '-b5':-6, '-5':-5,
    '-b6':-4, '-6':-3, '-b7':-2, '-7':-1,
    '1': 0, 'b2': 1, '2': 2, 'b3': 3,
    '3': 4, '4': 5, '#4': 6, 'b5': 6, '5': 7,
    'b6': 8, '6': 9, 'b7': 10, '7': 11,
    '8': 12
}

def midi_notes_from_degrees(degrees, tonic_note=tonic):
    midi_notes = []
    for deg in degrees:
        semitone = interval_to_semitone.get(deg)
        if semitone is None:
            raise ValueError(f"Unknown scale degree: {deg}")
        midi_notes.append(tonic_note + semitone)
    return midi_notes

def get_degree_name(midi_note, tonic_note=tonic):
    diff = midi_note - tonic_note
    wrapped = diff % 12
    if diff >= 0:
        return scale_degree_map.get(wrapped, '?')
    else:
        return scale_degree_map.get(wrapped - 12, '?')  # negative equivalent
bass_scales = {
    "scale1": ["1", "b2", "b3", "4", "5", "b6", "b7", "8"],
    "scale2": ["1", "2", "b3", "4", "5", "b6", "b7", "8"],
    "scale3": ["1", "2", "b3", "4", "5", "6", "b7", "8"],
    "scale4": ["1", "2", "3", "4", "5", "6", "b7", "8"],
    "scale5": ["1", "2", "3", "4", "5", "6", "7", "8"],
    "scale6": ["1", "2", "3", "#4", "5", "6", "7", "8"]
}

midi_pattern_library = {
    name: midi_notes_from_degrees(degrees, tonic_note=tonic)
    for name, degrees in bass_scales.items()
}

def freq_from_midi(midi_note):
    # MIDI note 69 = A4 = 440 Hz
    return 440.0 * 2 ** ((midi_note - 69) / 12)


labels = [
    "SadLevel8", "SadLevel7", "SadLevel6", "SadLevel5",
    "SadLevel4", "SadLevel3", "SadLevel2", "SadLevel1",
    "Neutral",
    "HappyLevel1", "HappyLevel2", "HappyLevel3",
    "HappyLevel4", "HappyLevel5", "HappyLevel6",
    "HappyLevel7", "HappyLevel8"
]

import numpy as np
import pygame

def fade_in_sound(sound, sample_rate, fade_ms=10):
    fade_samples = int(sample_rate * fade_ms / 1000)
    
    raw = pygame.sndarray.array(sound).astype(np.float32)
    
    # If stereo, shape is (samples, channels)
    if raw.ndim == 2:
        fade_envelope = np.linspace(0, 1, fade_samples)[:, None]
    else:
        fade_envelope = np.linspace(0, 1, fade_samples)
    
    raw[:fade_samples] *= fade_envelope
    
    # Clip to valid range
    np.clip(raw, -32768, 32767, out=raw)
    
    # Convert back to int16 (assuming 16-bit)
    processed = raw.astype(np.int16)
    
    return pygame.sndarray.make_sound(processed)


sample_cache = {}
def load_samples():
    prefix = "ProgrammableLoop2/ProgrammableLoop2"
    fix = prefix + "Kick"
    suffix = ".wav"
    for label in labels:
        path = fix + label + suffix
        try:
            sound = pygame.mixer.Sound(path)
            sound = fade_in_sound(sound, sample_rate, fade_ms=10)
            sample_cache[label] = sound
        except Exception as e:
            print(f"Error loading {path}: {e}")

load_samples()

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


def play_sample_with_delay_and_gain(label, delay_ms, gain_db):
    def delayed_play():
        time.sleep(delay_ms / 1000)
        sound = sample_cache.get(label)
        if sound:
            with slider_val_lock:
                slider = slider_val
            global_gain_db = slider_to_global_gain_db(slider)
            global_highshelf_db = slider_to_global_highshelf_db(slider)
            # Combine gains (total_gain_db applies to volume; highshelf is conceptual here)
            total_gain_db = gain_db + global_gain_db + global_highshelf_db
            lowmid_db = slider_to_lowmid_db(slider)
            # Combine gains (total_gain_db applies to volume; highshelf is conceptual here)
            total_gain_db = gain_db + global_gain_db + global_highshelf_db + lowmid_db
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
            total_gain_db = gain_db + slider_to_global_gain_db(slider) + slider_to_global_highshelf_db(slider) + slider_to_lowmid_db(slider)
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
            total_gain_db = gain_db \
                + slider_to_global_gain_db(slider) \
                + slider_to_global_highshelf_db(slider) \
                + slider_to_lowmid_db(slider)
            volume = 10 ** (total_gain_db/20)
            sound.set_volume(min(1.0, max(0.0, volume)))
            sound.play()
    threading.Thread(target=delayed_play).start()


def sequencer(stop_event):
    global current_group_index, current_bpm, start_bpm, target_bpm, ramp_start_time, ramp_duration

    global_delay = 0.03
    next_trigger = time.time() + global_delay
    step = 0
    note_index = 0  # to cycle through midi_note_pattern
    kick_time = 0
    drum_delay = 0.04
    last_note_end_time = 0  # global or at the start of your sequencer function or script




    morph_active = False
    morph_start_index = current_group_index
    morph_end_index = current_group_index
    morph_step_count = steps_per_measure
    morph_current_step = 0

    while not stop_event.is_set():
        with slider_val_lock:
            slider = slider_val

        goal_group_index = int(round(slider * (len(labels) - 1)))

        if goal_group_index != morph_end_index and not morph_active:
            morph_active = True
            morph_start_index = current_group_index
            morph_end_index = goal_group_index
            morph_current_step = 0

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
            if morph_active:
                group_distance = abs(morph_end_index - morph_start_index)
                step_size = 1 if group_distance < 4 else 2 if group_distance <= 8 else 3 if group_distance <= 12 else 4
                if morph_start_index < morph_end_index:
                    new_index = morph_start_index + step_size * morph_current_step
                    new_index = min(new_index, morph_end_index)
                else:
                    new_index = morph_start_index - step_size * morph_current_step
                    new_index = max(new_index, morph_end_index)
                current_group_index = int(new_index)
                morph_current_step += 1
                if morph_current_step > morph_step_count or current_group_index == morph_end_index:
                    morph_active = False
                    current_group_index = morph_end_index

            if kick_patterns[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step] + drum_delay * 1000
                gain_db = global_accents[current_group_index][step]
                kick_time = time.time()
                play_sample_with_delay_and_gain(labels[current_group_index], delay_ms, gain_db)

            if snare_patterns[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step] + drum_delay * 1000
                gain_db = global_accents[current_group_index][step]
                play_snare_with_delay_and_gain(labels[current_group_index], delay_ms, gain_db)

            if cymbal_patterns[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step] + drum_delay * 1000
                gain_db   = global_accents[current_group_index][step]
                play_cymbal_with_delay_and_gain(labels[current_group_index],
                                                delay_ms, gain_db)

            selected_bass_pattern = bass_patterns[current_group_index]


            
            
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
            base_duration = seconds_per_16th * 0.9375 * 2  # whole beat
            now = time.time()

            if degree == 0 or degree == 'c':
                # Don't schedule; just advance
                note = None
            else:
                degree_str = degree if isinstance(degree, str) else str(degree)
                note = tonic + interval_to_semitone[degree_str]
                duration = get_extended_duration(selected_bass_pattern, note_index % len(selected_bass_pattern), base_duration)
                
                synth.schedule_note(now, note, duration)

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
    out = np.zeros_like(wave)
    f = 2 * np.sin(np.pi * cutoff_freqs / sample_rate)
    q = resonance
    for i in range(len(wave)):
        sample = np.tanh(wave[i] * drive)
        notch = sample - q * band
        low += f[i] * band
        high = notch - low
        band += f[i] * high
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

        total_samples = int(self.sample_rate * duration)
        if len(resampled) < total_samples:
            repeats = total_samples // len(resampled) + 1
            resampled = np.tile(resampled, repeats)

        latency_ms = 0.7  # try tuning this value by ear
        latency_samples = int(self.sample_rate * latency_ms / 1000)

        if len(resampled) > latency_samples:
            resampled = resampled[latency_samples:]
        else:
            resampled = np.zeros_like(resampled)

        # Ensure it's still the right length
        if len(resampled) < total_samples:
            repeats = total_samples // len(resampled) + 1
            resampled = np.tile(resampled, repeats)

        return resampled[:total_samples]

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

        combined_wave = fm_wave + sample_wave


        # ADSR envelope
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

        low_res = 0.3
        high_res = 2.0
        target_resonance = low_res + (high_res - low_res) * (slider ** 0.5)

        if self.prev_resonance is None:
            self.prev_resonance = target_resonance
        elif slider_changed:
            smoothing_factor = 0.005
            self.prev_resonance = (1 - smoothing_factor) * self.prev_resonance + smoothing_factor * target_resonance

        resonance = self.prev_resonance



        with slider_val_lock:
            slider = slider_val
        target_drive = 1 + 0.2757 * slider

        if not hasattr(self, 'prev_drive'):
            self.prev_drive = target_drive
        else:
            smoothing_factor = 0.005  # adjust between 0.05 and 0.2 as needed
            self.prev_drive = (1 - smoothing_factor) * self.prev_drive + smoothing_factor * target_drive

        drive = self.prev_drive



        combined_wave, self.lowpass_low, self.lowpass_band = lowpass_filter_resonant(
    combined_wave, filter_env, resonance, self.sample_rate, drive,
    self.lowpass_low, self.lowpass_band
)



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

        combined_wave = comb_filter_modulated(
            combined_wave, sample_rate=self.sample_rate,
            base_delay=delay_time, feedback=feedback, drive=drive
        )



        combined_wave *= (1 + lfo_wave)  # or scale/offset as needed

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


        fade_in_samples = max(1, int(self.sample_rate * attack))
        combined_wave[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)

        fade_out_samples = int(0.01 * self.sample_rate)  # Keep fade-out short
        combined_wave[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

        


        combined_wave *= self.master_volume

        def normalize_rms(signal, target_rms=0.1, eps=1e-8):
            rms = np.sqrt(np.mean(signal**2)) + eps
            return signal * (target_rms / rms)

        combined_wave = normalize_rms(combined_wave, target_rms=0.1)

        

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
                        delay_ms = (now - start_time) * 1000
                        print(f"[SCHEDULER] Note {midi_note} scheduled for {start_time:.6f}, triggered at {now:.6f}, delay = {delay_ms:.2f} ms")
                
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

            
            # After mixing all active notes into 'buffer'
            diffs = np.diff(buffer)
            crackle_indices = np.where(np.abs(diffs) > 0.3)[0]  # tweak threshold if needed

            if len(crackle_indices) > 0:
                print(f"[CRACKLE DETECTED] Large jumps at samples: {crackle_indices}")

            buffer = np.clip(buffer, -1.0, 1.0)

            buffer_start_time = time.time()
            print(f"[DEBUG] Buffer min: {buffer.min()}, max: {buffer.max()}, mean: {buffer.mean()}")

            self.stream.write(buffer.tobytes())
            buffer_end_time = time.time()
            write_duration_ms = (buffer_end_time - buffer_start_time) * 1000
            expected_ms = (self.buffer_size / self.sample_rate) * 1000
            print(f"[STREAM] Buffer write took {write_duration_ms:.2f} ms, expected {expected_ms:.2f} ms")


            time.sleep(self.buffer_size / self.sample_rate * 0.01)




# Instantiate once globally somewhere after sample_rate is set:
synth = Synth(sample_rate)
synth.set_master_volume(0.75)  # sets volume to 50%



# Create the Tk root window only once
root = tk.Tk()
root.title("Sequencer BPM Control")
root.geometry('400x150')

label = tk.Label(root, text="BPM (log scale)")
label.pack(pady=10)

slider = tk.Scale(root, from_=0, to=1, resolution=0.001,
                  orient=tk.HORIZONTAL, length=300,
                  command=on_slider_change)
slider.set(bpm_to_slider(default_bpm))
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
