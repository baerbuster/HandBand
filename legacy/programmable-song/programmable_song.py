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

    next_trigger = time.time()
    step = 0

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
                delay_ms = delay_patterns_ms[current_group_index][step]
                gain_db = global_accents[current_group_index][step]
                play_sample_with_delay_and_gain(labels[current_group_index], delay_ms, gain_db)

            if snare_patterns[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step]
                gain_db = global_accents[current_group_index][step]
                play_snare_with_delay_and_gain(labels[current_group_index], delay_ms, gain_db)

            if cymbal_patterns[current_group_index][step]:
                delay_ms = delay_patterns_ms[current_group_index][step]
                gain_db   = global_accents[current_group_index][step]
                play_cymbal_with_delay_and_gain(labels[current_group_index],
                                                delay_ms, gain_db)

            if step % 4 == 0:
                midi_note = 45
                duration = seconds_per_16th * 0.9375 * 4
                synth.schedule_note(time.time() + 0.05, midi_note, duration)

            
            step = (step + 1) % steps_per_measure
            next_trigger += seconds_per_16th
        else:
            time.sleep(min(0.001, next_trigger - now))

def on_slider_change(val):
    global slider_val
    with slider_val_lock:
        slider_val = float(val)

import threading
import time
import numpy as np
import pyaudio

def lowpass_filter_resonant(wave, cutoff_freqs, resonance, sample_rate):
    out = np.zeros_like(wave)
    f = 2 * np.sin(np.pi * cutoff_freqs / sample_rate)
    q = resonance
    low = 0.0
    band = 0.0
    for i in range(len(wave)):
        notch = wave[i] - q * band
        low += f[i] * band
        high = notch - low
        band += f[i] * high
        out[i] = low
    return out


def comb_filter_modulated(wave, sample_rate, base_delay=1/47.1, feedback=0.968, drive=0.1538, env_percent=1.0):
    # base_delay is inverse of cutoff freq (47.1 Hz)
    samples = len(wave)
    out = np.copy(wave) * (1 + drive)  # apply drive boost
    delay_samples = int(sample_rate * base_delay)
    for i in range(delay_samples, samples):
        out[i] += feedback * out[i - delay_samples]
    return out

def global_resonance_filter(wave, sample_rate, freq=85.61, resonance=13.65):
    # Simple resonant peak using bandpass-like filter
    # Convert resonance to Q factor (this is a loose mapping, adjust as needed)
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
        self.active_notes = []  # list of (wave, current_index)
        self.note_queue = []    # list of (start_time, midi_note, duration)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def fm_wave(self, carrier_freq, mod_freq, mod_index, duration):
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)

        # LFO parameters
        lfo_rate = 3.22  # Hz
        lfo_depth_cents = 3.81  # cents

        # Convert cents to frequency modulation depth (Hz)
        lfo_depth = carrier_freq * (2**(lfo_depth_cents / 1200) - 1)

        # LFO signal modulating carrier freq subtly
        lfo = np.sin(2 * np.pi * lfo_rate * t) * lfo_depth

        # Modulate carrier freq with LFO
        modulated_carrier_freq = carrier_freq + lfo

        modulator = np.sin(2 * np.pi * mod_freq * t)
        wave = np.sin(2 * np.pi * modulated_carrier_freq * t + mod_index * modulator).astype(np.float32)
        return wave



    def adsr_envelope(self, length, attack=0.155, decay=0.385, sustain_level=0.17, release=1.13):
        attack_samples = max(1, int(self.sample_rate * attack))
        decay_samples = max(1, int(self.sample_rate * decay))
        release_samples = max(1, int(self.sample_rate * release))
        sustain_samples = max(0, length - attack_samples - decay_samples - release_samples)

        total_samples = attack_samples + decay_samples + sustain_samples + release_samples
        diff = length - total_samples
        if diff > 0:
            sustain_samples += diff
        elif diff < 0:
            sustain_samples = max(0, sustain_samples + diff)

        attack_env = np.linspace(0, 1, attack_samples, endpoint=False)
        decay_env = np.linspace(1, sustain_level, decay_samples, endpoint=False)
        sustain_env = np.full(sustain_samples, sustain_level)
        release_env = np.linspace(sustain_level, 0, release_samples, endpoint=True)

        envelope = np.concatenate([attack_env, decay_env, sustain_env, release_env])

        if len(envelope) < length:
            envelope = np.append(envelope, 0)
        elif len(envelope) > length:
            envelope = envelope[:length]

        assert len(envelope) == length, f"Envelope length {len(envelope)} != expected {length}"
        return envelope

    def filter_envelope(self, length, peak_freq=22.53, sustain_freq=20, attack=1.074, decay=0.246, release=0.31):
        attack_samples = int(self.sample_rate * attack)
        decay_samples = int(self.sample_rate * decay)
        release_samples = int(self.sample_rate * release)
        sustain_samples = max(0, length - attack_samples - decay_samples - release_samples)

        mod_range = 0.1265 * sustain_freq  # 12.65% of 20 Hz = ~2.53 Hz
        peak_freq = sustain_freq + mod_range  # 20 + 2.53 = 22.53 Hz
        attack_env = np.linspace(sustain_freq, peak_freq, attack_samples, endpoint=False)

        decay_env = np.linspace(peak_freq, sustain_freq, decay_samples, endpoint=False)
        sustain_env = np.full(sustain_samples, sustain_freq)
        release_env = np.linspace(sustain_freq, 50, release_samples, endpoint=True)  # fades out

        env = np.concatenate([attack_env, decay_env, sustain_env, release_env])
        if len(env) < length:
            env = np.pad(env, (0, length - len(env)), 'edge')
        return env

    def schedule_note(self, start_time, midi_note, duration):
        with self.lock:
            self.note_queue.append((start_time, midi_note, duration))

    def render_note(self, midi_note, duration):
        freq = freq_from_midi(midi_note)
        total_samples = int(self.sample_rate * duration)
        if total_samples <= 0:
            return np.array([], dtype=np.float32)
        
        # FM synthesis with 8.68% modulation index
        mod_freq = freq * 2
        mod_index = 0.0868
        wave = self.fm_wave(freq, mod_freq, mod_index, duration)

        env = self.adsr_envelope(total_samples)
        
        fade_samples = int(0.005 * self.sample_rate)
        if fade_samples * 2 > total_samples:
            fade_samples = total_samples // 2
        
        wave *= env
        
        
        global_cutoff = 85.61


        # Resonant lowpass filter with resonance=0.25 and cutoff envelope modulated between 20 and 22.53 Hz
        filter_env = self.filter_envelope(total_samples, peak_freq=22.53, sustain_freq=20)
        filter_env *= global_cutoff / 20  # since 20Hz is your base

        wave = lowpass_filter_resonant(wave, filter_env, resonance=0.25, sample_rate=self.sample_rate)

        scaled_comb_freq = 47.1 * (global_cutoff / 20)  # scale around 20Hz base
        base_delay = 1 / scaled_comb_freq
        wave = comb_filter_modulated(wave, sample_rate=self.sample_rate,
                             base_delay=base_delay, feedback=0.968, drive=0.1538)
        
        wave = butter_lowpass_filter(wave, cutoff=183, fs=self.sample_rate, order=4)


        # Volume control (using your existing slider logic)
        with slider_val_lock:
           slider = slider_val
        total_gain_db = base_gain_db \
            + slider_to_global_gain_db(slider) \
            + slider_to_global_highshelf_db(slider) \
            + slider_to_lowmid_db(slider)
        volume = 1.1 ** (total_gain_db / 20)
        wave *= volume

        fade_in_samples = int(0.01 * self.sample_rate)  # 10ms fade-in
        wave[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)

        fade_out_samples = int(0.01 * self.sample_rate)  # 10ms fade-out
        wave[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)


        return wave


    def set_delay_pattern(self, pattern_ms):
        self.current_delay_pattern = [d / 1000 for d in pattern_ms]

    def schedule_pattern(self, base_time, midi_notes, step_duration):
        with self.lock:
            for i, midi_note in enumerate(midi_notes):
                if midi_note is None:
                    continue
                delay = self.current_delay_pattern[i] if i < len(self.current_delay_pattern) else 0
                start = base_time + i * step_duration + delay
                self.note_queue.append((start, midi_note, step_duration))
                
    def run(self):
        while True:
            now = time.time()
            with self.lock:
                print(f"[{now:.4f}] Note queue length: {len(self.note_queue)}")
                for (start_time, midi_note, duration) in self.note_queue:
                    print(f"  Scheduled note start_time={start_time:.4f}, midi_note={midi_note}, duration={duration}")
                    if start_time <= now:
                        print(f"  -> Activating note {midi_note} at {now:.4f}")
                        wave = self.render_note(midi_note, duration)
                        print(f"     Rendered wave length: {len(wave)} samples")
                        self.active_notes.append((wave, 0))
                self.note_queue = [n for n in self.note_queue if n[0] > now]
                print(f"[{now:.4f}] Notes remaining in queue after pruning: {len(self.note_queue)}")
                print(f"[{now:.4f}] Active notes count before buffer processing: {len(self.active_notes)}")

            buffer = np.zeros(self.buffer_size, dtype=np.float32)
            new_active = []
            for wave, idx in self.active_notes:
                end_idx = idx + self.buffer_size
                segment = wave[idx:end_idx]
                buffer[:len(segment)] += segment
                if end_idx < len(wave):
                    new_active.append((wave, end_idx))
            self.active_notes = new_active
            print(f"[{now:.4f}] Active notes count after buffer processing: {len(self.active_notes)}")

            buffer = np.clip(buffer, -1.0, 1.0)
            self.stream.write(buffer.tobytes())

            time.sleep(self.buffer_size / self.sample_rate * 0.01)



# Instantiate once globally somewhere after sample_rate is set:
synth = Synth(sample_rate)


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
