#!/usr/bin/env python3
"""
PythonExample.py - Demonstrates using multiple synthesizers with the refactored API
"""

import ctypes
import time
import threading
import math

# Load the shared library
synth = ctypes.CDLL('./libsynth.so')

# Define function return types and argument types
synth.create_synth.restype = ctypes.c_int
synth.delete_synth.argtypes = [ctypes.c_int]
synth.delete_synth.restype = ctypes.c_bool
synth.has_synth.argtypes = [ctypes.c_int]
synth.has_synth.restype = ctypes.c_bool

synth.initialize_synth_system.restype = None
synth.shutdown_synth_system.restype = None

synth.start_synth.argtypes = [ctypes.c_int]
synth.start_synth.restype = None
synth.note_on.argtypes = [ctypes.c_int]
synth.note_on.restype = None
synth.note_off.argtypes = [ctypes.c_int]
synth.note_off.restype = None
synth.stop_synth.argtypes = [ctypes.c_int]
synth.stop_synth.restype = None

# Parameter setters with synth ID
synth.set_frequency.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_amplitude.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_master_volume.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_attack.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_decay.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sustain_level.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_release.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sine_gain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_square_gain.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_cutoff.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_filter_resonance.argtypes = [ctypes.c_double, ctypes.c_int]
synth.set_sample_path.argtypes = [ctypes.c_char_p, ctypes.c_int]

def freq_from_midi(midi_note):
    """Convert MIDI note number to frequency in Hz"""
    return 440.0 * 2 ** ((midi_note - 69) / 12)

def play_chord(synth_ids, midi_notes, duration=1.0):
    """Play a chord using multiple synthesizers"""
    if len(synth_ids) != len(midi_notes):
        raise ValueError("Number of synths must match number of notes")
    
    # Set frequencies and play notes
    for i, (synth_id, midi_note) in enumerate(zip(synth_ids, midi_notes)):
        freq = freq_from_midi(midi_note)
        synth.set_frequency(freq, synth_id)
        synth.note_on(synth_id)
    
    # Wait for the specified duration
    time.sleep(duration)
    
    # Release all notes
    for synth_id in synth_ids:
        synth.note_off(synth_id)

def play_arpeggio(synth_id, midi_notes, duration=0.2):
    """Play an arpeggio using a single synthesizer"""
    for midi_note in midi_notes:
        freq = freq_from_midi(midi_note)
        synth.set_frequency(freq, synth_id)
        synth.note_on(synth_id)
        time.sleep(duration)
        synth.note_off(synth_id)
        time.sleep(0.05)  # Small gap between notes

def main():
    # Initialize the synthesizer system
    synth.initialize_synth_system()
    
    try:
        # Create 3 synthesizer instances
        bass_synth = synth.create_synth()
        lead_synth = synth.create_synth()
        pad_synth = synth.create_synth()
        
        print(f"Created synthesizers with IDs: {bass_synth}, {lead_synth}, {pad_synth}")
        
        # Configure bass synth - deep, resonant sound
        synth.start_synth(bass_synth)
        synth.set_master_volume(0.5, bass_synth)
        synth.set_sine_gain(0.3, bass_synth)
        synth.set_square_gain(0.7, bass_synth)
        synth.set_attack(0.01, bass_synth)
        synth.set_decay(0.2, bass_synth)
        synth.set_sustain_level(-6.0, bass_synth)
        synth.set_release(0.5, bass_synth)
        synth.set_filter_cutoff(500.0, bass_synth)
        synth.set_filter_resonance(4.0, bass_synth)
        
        # Configure lead synth - bright, cutting sound
        synth.start_synth(lead_synth)
        synth.set_master_volume(0.4, lead_synth)
        synth.set_sine_gain(0.8, lead_synth)
        synth.set_square_gain(0.2, lead_synth)
        synth.set_attack(0.005, lead_synth)
        synth.set_decay(0.1, lead_synth)
        synth.set_sustain_level(-3.0, lead_synth)
        synth.set_release(0.2, lead_synth)
        synth.set_filter_cutoff(5000.0, lead_synth)
        synth.set_filter_resonance(2.0, lead_synth)
        
        # Configure pad synth - soft, atmospheric sound
        synth.start_synth(pad_synth)
        synth.set_master_volume(0.3, pad_synth)
        synth.set_sine_gain(0.9, pad_synth)
        synth.set_square_gain(0.1, pad_synth)
        synth.set_attack(1.0, pad_synth)
        synth.set_decay(2.0, pad_synth)
        synth.set_sustain_level(-10.0, pad_synth)
        synth.set_release(3.0, pad_synth)
        synth.set_filter_cutoff(2000.0, pad_synth)
        synth.set_filter_resonance(0.7, pad_synth)
        
        # Play a pad chord
        print("Playing pad chord...")
        play_chord([pad_synth], [60], 2.0)  # C major chord on pad
        
        # Play a bass line while the pad is still ringing
        print("Playing bass line...")
        bass_notes = [36, 43, 41, 38]  # C, G, F, D
        for note in bass_notes:
            synth.set_frequency(freq_from_midi(note), bass_synth)
            synth.note_on(bass_synth)
            time.sleep(0.5)
            synth.note_off(bass_synth)
            time.sleep(0.1)
        
        # Play a lead melody
        print("Playing lead melody...")
        lead_notes = [72, 74, 76, 77, 76, 74, 72, 69]  # C, D, E, F, E, D, C, A
        play_arpeggio(lead_synth, lead_notes, 0.2)
        
        # Play a final chord with all three synths
        print("Playing final chord with all synths...")
        play_chord([bass_synth, lead_synth, pad_synth], [48, 64, 72], 3.0)
        
        # Wait for release tails to finish
        time.sleep(3.0)
        
    finally:
        # Clean up
        print("Cleaning up...")
        synth.stop_synth(bass_synth)
        synth.stop_synth(lead_synth)
        synth.stop_synth(pad_synth)
        
        synth.delete_synth(bass_synth)
        synth.delete_synth(lead_synth)
        synth.delete_synth(pad_synth)
        
        synth.shutdown_synth_system()

if __name__ == "__main__":
    main()
    print("Example completed successfully!")
