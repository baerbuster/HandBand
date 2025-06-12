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
base_gain_db = 0
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

sample_cache = {}
def load_samples():
    prefix = "ProgrammableLoop2/ProgrammableLoop2"
    fix = prefix + "Kick"
    suffix = ".wav"
    for label in labels:
        path = fix + label + suffix
        try:
            sample_cache[label] = pygame.mixer.Sound(path)
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
                synth.add_note_to_queue(time.time(), midi_note, duration)
            
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

class Synth:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=sample_rate,
                                  output=True)
        self.lock = threading.Lock()
        self.note_queue = []  # list of (start_time, midi_note, duration)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def sine_wave(self, freq, duration):
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        return np.sin(2 * np.pi * freq * t).astype(np.float32)

    def adsr_envelope(self, length, attack=0.155, decay=0.385, sustain_level=0.17, release=1.13):
        attack_samples = int(self.sample_rate * attack)
        decay_samples = int(self.sample_rate * decay)
        release_samples = int(self.sample_rate * release)

        sustain_samples = length - attack_samples - decay_samples - release_samples
        if sustain_samples < 0:
            sustain_samples = 0

        # Sum up total samples to check if it matches length
        total_samples = attack_samples + decay_samples + sustain_samples + release_samples

        # Fix total_samples to exactly match length by adjusting sustain_samples
        diff = length - total_samples

        sustain_samples += diff
        if sustain_samples < 0:
            # If sustain is negative, reduce decay_samples instead (or release if needed)
            decay_samples += sustain_samples  # sustain_samples is negative here
            sustain_samples = 0
            if decay_samples < 0:
                release_samples += decay_samples  # decay_samples negative
                decay_samples = 0
                if release_samples < 0:
                    release_samples = 0


        envelope = np.concatenate([
            np.linspace(0, 1, attack_samples),           # Attack with endpoint=True (default)
            np.linspace(1, sustain_level, decay_samples), # Decay with endpoint=True
            np.full(sustain_samples, sustain_level),
            np.linspace(sustain_level, 0, release_samples)  # Release with endpoint=True
        ])

        return envelope

    def fade_edges(self, wave, fade_time=0.02):
        fade_samples = int(self.sample_rate * fade_time)
        if fade_samples * 2 > len(wave):
            fade_samples = len(wave) // 2  # avoid overrun

        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        wave[:fade_samples] *= fade_in
        wave[-fade_samples:] *= fade_out

        return wave




    def play_note(self, midi_note, duration):
        freq = freq_from_midi(midi_note)
        wave = self.sine_wave(freq, duration)
        env = self.adsr_envelope(len(wave))
        wave *= env
        wave = self.fade_edges(wave)  # <-- Add this line here

        with slider_val_lock:
            slider = slider_val
        total_gain_db = base_gain_db \
            + slider_to_global_gain_db(slider) \
            + slider_to_global_highshelf_db(slider) \
            + slider_to_lowmid_db(slider)

        volume = 10 ** (total_gain_db / 20)
        volume = max(0.02, min(volume, 0.3))
        wave *= volume

        print(f"wave[0]: {wave[0]}, wave[-1]: {wave[-1]}")


        self.stream.write(wave.tobytes())

    def add_note_to_queue(self, start_time, midi_note, duration):
        with self.lock:
            self.note_queue.append((start_time, midi_note, duration))

    def run(self):
        while True:
            now = time.time()
            with self.lock:
                to_play = [note for note in self.note_queue if note[0] <= now]
                self.note_queue = [note for note in self.note_queue if note[0] > now]
            for start_time, midi_note, duration in to_play:
                self.play_note(midi_note, duration)
            time.sleep(0.001)


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
