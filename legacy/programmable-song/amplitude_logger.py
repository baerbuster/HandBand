#!/usr/bin/env python3
# amplitude_logger.py - Logs amplitude values during a sustained note

import ctypes
import time
import numpy as np
import matplotlib.pyplot as plt
import pyaudio
import threading
import wave
import struct
import os

# Constants from ProgrammableSong2.14.py
SAMPLE_RATE = 44100
FADE_SAMPLES = 256
FADE_IN_TIME = 10
SAMPLE_LOOP_START_PERCENTAGE = 0.26
SAMPLE_LOOP_END_PERCENTAGE = 1.0
SAMPLE_BASE_FREQUENCY = 32.703
GAIN_SMOOTHING_TIME_SECONDS = 0.5
FILTER_DRIVE_SCALING = 4.0
COMB_FILTER_DRIVE_SCALING = 4.0
COMB_LIMITER_STRENGTH = 0.8
TUBE_BYPASS_THRESHOLD = 0.01
TUBE_DRIVE_SCALING = 3.0
TUBE_CUBIC_COEFF = 0.33
TUBE_QUINTIC_COEFF = 0.05
TUBE_INTENSITY_SCALING = 2.0
BITCRUSHER_BYPASS_THRESHOLD = 0.01
BITCRUSHER_MAX_DEPTH = 16.0
BITCRUSHER_MIN_DEPTH = 1.0
BITCRUSHER_DITHER_THRESHOLD = 8.0
BITCRUSHER_MIX_SCALE_THRESHOLD = 4.0
FILTER_ENV_MOD_SCALING = 1.5
GAIN_NORMALIZATION_CAP = 3.0
LOOP_FADE_SAMPLES = 256
COMB_MIN_DELAY_MS = 1.0
COMB_MAX_DELAY_MS = 50.0
COMB_FEEDBACK_MAX = 0.95
COMB_FEEDBACK_SCALING = 15.0
COMB_ENV_MOD_SCALING = 1.5
COMB_MIN_RESONANCE = 0.1
MASTER_VOLUME = 5.0

# ADSR bounds for slider at 0.0
MIN_ATTACK = 0.155
MIN_DECAY = 0.385
MIN_RELEASE = 1.130
MIN_SUSTAIN_DB = -15.65

# Load the synth library
synth = ctypes.CDLL('./libsynth.so')

# Set up function prototypes
synth.set_frequency.argtypes = [ctypes.c_double]
synth.set_frequency.restype = None
synth.set_attack.argtypes = [ctypes.c_double]
synth.set_attack.restype = None
synth.set_decay.argtypes = [ctypes.c_double]
synth.set_decay.restype = None
synth.set_release.argtypes = [ctypes.c_double]
synth.set_release.restype = None
synth.set_sustain_level.argtypes = [ctypes.c_double]
synth.set_sustain_level.restype = None
synth.set_sample_rate.argtypes = [ctypes.c_double]
synth.set_sample_rate.restype = None
synth.set_master_volume.argtypes = [ctypes.c_double]
synth.set_master_volume.restype = None
synth.start_synth.restype = None
synth.note_on.restype = None
synth.note_off.restype = None
synth.stop_synth.restype = None

# Initialize all the parameters that would be set when slider is at 0.0
def initialize_synth_for_slider_zero():
    print("Initializing synth with slider at 0.0 settings...")
    synth.set_sample_rate(SAMPLE_RATE)
    synth.set_fade_samples(FADE_SAMPLES)
    synth.set_fade_in_time(FADE_IN_TIME)
    synth.set_sample_loop_start_percentage(SAMPLE_LOOP_START_PERCENTAGE)
    synth.set_sample_loop_end_percentage(SAMPLE_LOOP_END_PERCENTAGE)
    synth.set_sample_base_frequency(SAMPLE_BASE_FREQUENCY)
    synth.set_gain_smoothing_time_seconds(GAIN_SMOOTHING_TIME_SECONDS)
    synth.set_filter_drive_scaling(FILTER_DRIVE_SCALING)
    synth.set_comb_filter_drive_scaling(COMB_FILTER_DRIVE_SCALING)
    synth.set_comb_limiter_strength(COMB_LIMITER_STRENGTH)
    synth.set_tube_bypass_threshold(TUBE_BYPASS_THRESHOLD)
    synth.set_tube_drive_scaling(TUBE_DRIVE_SCALING)
    synth.set_tube_cubic_coeff(TUBE_CUBIC_COEFF)
    synth.set_tube_quintic_coeff(TUBE_QUINTIC_COEFF)
    synth.set_tube_intensity_scaling(TUBE_INTENSITY_SCALING)
    synth.set_bitcrusher_bypass_threshold(BITCRUSHER_BYPASS_THRESHOLD)
    synth.set_bitcrusher_max_depth(BITCRUSHER_MAX_DEPTH)
    synth.set_bitcrusher_min_depth(BITCRUSHER_MIN_DEPTH)
    synth.set_bitcrusher_dither_threshold(BITCRUSHER_DITHER_THRESHOLD)
    synth.set_bitcrusher_mix_scale_threshold(BITCRUSHER_MIX_SCALE_THRESHOLD)
    synth.set_filter_env_mod_scaling(FILTER_ENV_MOD_SCALING)
    synth.set_comb_min_delay_ms(COMB_MIN_DELAY_MS)
    synth.set_comb_max_delay_ms(COMB_MAX_DELAY_MS)
    synth.set_comb_feedback_max(COMB_FEEDBACK_MAX)
    synth.set_comb_feedback_scaling(COMB_FEEDBACK_SCALING)
    synth.set_comb_env_mod_scaling(COMB_ENV_MOD_SCALING)
    synth.set_comb_min_resonance(COMB_MIN_RESONANCE)
    synth.set_gain_normalization_cap(GAIN_NORMALIZATION_CAP)
    synth.set_loop_fade_samples(LOOP_FADE_SAMPLES)
    
    # Set ADSR parameters for slider at 0.0
    synth.set_attack(MIN_ATTACK)
    synth.set_decay(MIN_DECAY)
    synth.set_release(MIN_RELEASE)
    synth.set_sustain_level(MIN_SUSTAIN_DB)
    
    # Set master volume
    synth.set_master_volume(MASTER_VOLUME)
    
    # Start the synth
    synth.start_synth()
    print("Synth initialized.")

# Audio recording setup
def record_audio(duration, filename="output.wav"):
    print(f"Recording audio for {duration} seconds...")
    
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=1024)
    
    frames = []
    
    # Record audio
    for i in range(0, int(SAMPLE_RATE / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the recorded audio to a WAV file
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paFloat32))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"Audio saved to {filename}")
    return frames

# Analyze amplitude from recorded frames
def analyze_amplitude(frames, interval_ms=100):
    print("Analyzing amplitude...")
    samples_per_interval = int(SAMPLE_RATE * interval_ms / 1000)
    
    amplitudes = []
    timestamps = []
    
    # Convert byte data to float32 samples
    all_samples = []
    for frame in frames:
        samples = struct.unpack(f'{len(frame)//4}f', frame)
        all_samples.extend(samples)
    
    # Calculate RMS amplitude for each interval
    for i in range(0, len(all_samples), samples_per_interval):
        interval_samples = all_samples[i:i+samples_per_interval]
        if interval_samples:
            rms = np.sqrt(np.mean(np.array(interval_samples)**2))
            amplitudes.append(rms)
            timestamps.append(i / SAMPLE_RATE)
    
    return timestamps, amplitudes

# Real-time amplitude monitoring
def monitor_amplitude_realtime(duration=10, interval_ms=100):
    print(f"Monitoring amplitude in real-time for {duration} seconds...")
    
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=1024)
    
    amplitudes = []
    timestamps = []
    
    samples_per_interval = int(SAMPLE_RATE * interval_ms / 1000)
    buffer = []
    
    start_time = time.time()
    while time.time() - start_time < duration:
        data = stream.read(1024)
        samples = struct.unpack(f'{len(data)//4}f', data)
        buffer.extend(samples)
        
        if len(buffer) >= samples_per_interval:
            rms = np.sqrt(np.mean(np.array(buffer[:samples_per_interval])**2))
            current_time = time.time() - start_time
            
            print(f"Time: {current_time:.2f}s, Amplitude: {rms:.6f}")
            
            amplitudes.append(rms)
            timestamps.append(current_time)
            
            buffer = buffer[samples_per_interval:]
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    return timestamps, amplitudes

# Plot amplitude over time
def plot_amplitude(timestamps, amplitudes):
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, amplitudes)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Amplitude (RMS)')
    plt.title('Amplitude Over Time During Sustained Note')
    plt.grid(True)
    
    # Add trendline
    z = np.polyfit(timestamps, amplitudes, 1)
    p = np.poly1d(z)
    plt.plot(timestamps, p(timestamps), "r--", label=f"Trend: {z[0]:.6f}x + {z[1]:.6f}")
    
    plt.legend()
    plt.savefig('amplitude_over_time.png')
    plt.show()

def main():
    # Initialize the synth with slider at 0.0 settings
    initialize_synth_for_slider_zero()
    
    # Play a note (A4 = 440Hz)
    synth.set_frequency(440.0)
    
    print("Playing note and monitoring amplitude...")
    synth.note_on()
    
    try:
        # Option 1: Record audio and analyze later
        # frames = record_audio(10, "sustained_note.wav")
        # timestamps, amplitudes = analyze_amplitude(frames)
        
        # Option 2: Monitor amplitude in real-time
        timestamps, amplitudes = monitor_amplitude_realtime(duration=10, interval_ms=100)
        
        # Stop the note
        synth.note_off()
        time.sleep(1)  # Let the release finish
        
        # Plot the results
        plot_amplitude(timestamps, amplitudes)
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        if synth:
            synth.note_off()
            time.sleep(1)
            synth.stop_synth()
    
    print("Done.")

if __name__ == "__main__":
    main()
