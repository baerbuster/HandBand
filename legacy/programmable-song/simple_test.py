#!/usr/bin/env python3
# simple_test.py - Simple test program to diagnose synthesizer clicks
# g++ -std=c++17 -fPIC -shared click_detector.cpp -o libclick.so -I/opt/homebrew/opt/portaudio/include -L/opt/homebrew/opt/portaudio/lib -lportaudio -pthread

import ctypes
import time
import threading
import os
import sys

# Constants
MIN_BPM = 80
MAX_BPM = 180
DEFAULT_BPM = 120
STEPS_PER_MEASURE = 16

# Test patterns
TEST_PATTERNS = {
    "single": ['1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    "alternating": ['1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c'],
    "two_steps": ['1', '1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    "long_note": ['1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', 'c'],
}

class ClickDetector:
    def __init__(self):
        self.current_bpm = DEFAULT_BPM
        self.pattern = TEST_PATTERNS["alternating"]
        self.attack_time = 0.3
        self.decay_time = 0.2
        self.sustain_level = 0.5
        self.release_time = 0.5
        self.stop_event = threading.Event()
        
        # Check if libclick.so exists, if not compile it
        if not os.path.exists("libclick.so"):
            print("Compiling click detector...")
            os.system("g++ -std=c++17 -fPIC -shared click_detector.cpp -o libclick.so -I/opt/homebrew/opt/portaudio/include -L/opt/homebrew/opt/portaudio/lib -lportaudio -pthread")
        
        # Load the click detector library
        try:
            self.synth = ctypes.CDLL('./libclick.so')
            print("Loaded click detector library")
            self.setup_synth_functions()
        except Exception as e:
            print(f"Failed to load click detector: {e}")
            sys.exit(1)
        
        # Start synth
        self.synth.start_synth()
        self.synth.set_bpm(ctypes.c_double(self.current_bpm))
        
        # Set initial envelope
        self.set_attack(self.attack_time)
        self.set_decay(self.decay_time)
        self.set_sustain(self.sustain_level)
        self.set_release(self.release_time)
    
    def setup_synth_functions(self):
        """Set up function signatures for the synth library"""
        self.synth.start_synth.restype = None
        self.synth.note_on.restype = None
        self.synth.note_off.restype = None
        self.synth.stop_synth.restype = None
        
        self.synth.set_frequency.restype = None
        self.synth.set_frequency.argtypes = [ctypes.c_double]
        
        self.synth.set_attack.restype = None
        self.synth.set_attack.argtypes = [ctypes.c_double]
        
        self.synth.set_decay.restype = None
        self.synth.set_decay.argtypes = [ctypes.c_double]
        
        self.synth.set_sustain_level.restype = None
        self.synth.set_sustain_level.argtypes = [ctypes.c_double]
        
        self.synth.set_release.restype = None
        self.synth.set_release.argtypes = [ctypes.c_double]
        
        self.synth.set_amplitude.restype = None
        self.synth.set_amplitude.argtypes = [ctypes.c_double]
        
        self.synth.set_bpm.restype = None
        self.synth.set_bpm.argtypes = [ctypes.c_double]
    
    def set_bpm(self, bpm):
        """Set the BPM"""
        self.current_bpm = bpm
        self.synth.set_bpm(ctypes.c_double(bpm))
        print(f"BPM set to {bpm}")
    
    def set_pattern(self, pattern_name):
        """Set the pattern"""
        if pattern_name in TEST_PATTERNS:
            self.pattern = TEST_PATTERNS[pattern_name]
            print(f"Pattern set to {pattern_name}")
        else:
            print(f"Unknown pattern: {pattern_name}")
    
    def set_attack(self, value):
        """Set attack time"""
        self.attack_time = value
        self.synth.set_attack(ctypes.c_double(value))
        print(f"Attack set to {value:.2f}s")
    
    def set_decay(self, value):
        """Set decay time"""
        self.decay_time = value
        self.synth.set_decay(ctypes.c_double(value))
        print(f"Decay set to {value:.2f}s")
    
    def set_sustain(self, value):
        """Set sustain level"""
        self.sustain_level = value
        self.synth.set_sustain_level(ctypes.c_double(value))
        print(f"Sustain set to {value:.2f}")
    
    def set_release(self, value):
        """Set release time"""
        self.release_time = value
        self.synth.set_release(ctypes.c_double(value))
        print(f"Release set to {value:.2f}s")
    
    def run_sequencer(self, duration_sec=10):
        """Run the sequencer for a specified duration"""
        self.stop_event.clear()
        
        print(f"Running sequencer with pattern for {duration_sec} seconds at {self.current_bpm} BPM")
        print(f"ADSR: A={self.attack_time}s, D={self.decay_time}s, S={self.sustain_level}, R={self.release_time}s")
        
        # Start sequencer in a thread
        thread = threading.Thread(target=self._sequencer_thread, args=(duration_sec,))
        thread.start()
        
        # Wait for sequencer to finish
        thread.join()
        
        # Check for clicks
        self.check_for_clicks()
    
    def _sequencer_thread(self, duration_sec):
        """Sequencer thread function"""
        step = 0
        note_is_on = False
        next_trigger = time.time()
        measure_count = 0
        start_time = time.time()
        
        while not self.stop_event.is_set() and (time.time() - start_time) < duration_sec:
            # Calculate timing based on BPM
            seconds_per_beat = 60 / self.current_bpm
            seconds_per_16th = seconds_per_beat / 4
            
            now = time.time()
            if now >= next_trigger:
                val = self.pattern[step]
                
                # Debug info
                step_info = f"Step {step}, Measure {measure_count}, BPM {self.current_bpm:.2f}, Value {val}"
                
                if val == 'c':
                    # If we are in a rest but a note is currently on, turn it off
                    if note_is_on:
                        self.synth.note_off()
                        note_is_on = False
                        print(f"{step_info}: note_off")
                    else:
                        print(f"{step_info}: no action (rest)")
                else:
                    is_on = (val == 1 or val == '1')
                    if is_on and not note_is_on:
                        self.synth.note_on()
                        note_is_on = True
                        print(f"{step_info}: note_on")
                    elif not is_on and note_is_on:
                        self.synth.note_off()
                        note_is_on = False
                        print(f"{step_info}: note_off")
                
                step = (step + 1) % STEPS_PER_MEASURE
                if step == 0:
                    measure_count += 1
                
                next_trigger += seconds_per_16th
            else:
                # Sleep until next step
                sleep_time = max(0, min(0.01, next_trigger - now))
                time.sleep(sleep_time)
        
        # Make sure note is off at the end
        if note_is_on:
            self.synth.note_off()
            print("Turning off note at end of sequence")
    
    def run_single_note_test(self, duration_sec=1.0):
        """Run a single note test"""
        print(f"Running single note test for {duration_sec} seconds at {self.current_bpm} BPM")
        print(f"ADSR: A={self.attack_time}s, D={self.decay_time}s, S={self.sustain_level}, R={self.release_time}s")
        
        # Turn on a note for the specified duration
        self.synth.note_on()
        time.sleep(duration_sec)
        self.synth.note_off()
        
        # Wait for release to complete
        time.sleep(self.release_time + 0.1)
        
        # Check for clicks
        self.check_for_clicks()
    
    def run_bpm_sweep_test(self):
        """Run a BPM sweep test"""
        print("Running BPM sweep test...")
        
        # Test different BPMs
        for bpm in [80, 100, 120, 140, 160, 180]:
            self.set_bpm(bpm)
            
            # Play a few notes
            print(f"\nTesting BPM: {bpm}")
            for i in range(3):
                print(f"  Note {i+1}/3")
                self.synth.note_on()
                time.sleep(60 / bpm / 4)  # Duration of a 16th note
                self.synth.note_off()
                time.sleep(60 / bpm / 4)  # Rest for a 16th note
            
            # Check for clicks
            self.check_for_clicks()
    
    def check_for_clicks(self):
        """Check for clicks in the log file"""
        if os.path.exists("click_detector.log"):
            try:
                with open("click_detector.log", "r") as f:
                    content = f.read()
                    click_count = content.count("CLICK DETECTED")
                    
                    print(f"\nFound {click_count} clicks in the log")
                    
                    # Extract and print details about the last few clicks
                    click_sections = content.split("===== CLICK DETECTED")
                    if len(click_sections) > 1:
                        last_clicks = click_sections[-3:] if len(click_sections) >= 3 else click_sections[1:]
                        print("\nDetails of the most recent clicks:")
                        for i, click in enumerate(last_clicks):
                            lines = click.strip().split("\n")
                            print(f"\nClick {i+1}:")
                            for line in lines[:10]:  # Print first 10 lines of each click
                                if line and not line.startswith("Sample values"):
                                    print(f"  {line}")
            except Exception as e:
                print(f"Error reading log file: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_event.set()
        self.synth.stop_synth()
        print("Synth stopped")

def print_menu():
    """Print the menu"""
    print("\n=== CLICK DETECTOR MENU ===")
    print("1. Run alternating pattern test")
    print("2. Run single note test")
    print("3. Run BPM sweep test")
    print("4. Change BPM")
    print("5. Change pattern")
    print("6. Change envelope (ADSR)")
    print("7. View log file")
    print("8. Exit")
    print("==========================")

def main():
    """Main function"""
    print("=== CLICK DETECTOR TEST ===")
    print("This program will help diagnose clicks in the synthesizer")
    
    detector = ClickDetector()
    
    while True:
        print_menu()
        choice = input("Enter your choice (1-8): ")
        
        if choice == '1':
            duration = float(input("Enter duration in seconds (default: 10): ") or "10")
            detector.run_sequencer(duration)
        elif choice == '2':
            duration = float(input("Enter note duration in seconds (default: 1): ") or "1")
            detector.run_single_note_test(duration)
        elif choice == '3':
            detector.run_bpm_sweep_test()
        elif choice == '4':
            bpm = float(input(f"Enter BPM ({MIN_BPM}-{MAX_BPM}, default: {detector.current_bpm}): ") or str(detector.current_bpm))
            detector.set_bpm(bpm)
        elif choice == '5':
            print("Available patterns:")
            for i, (name, _) in enumerate(TEST_PATTERNS.items()):
                print(f"  {i+1}. {name}")
            pattern_choice = input("Enter pattern name: ")
            detector.set_pattern(pattern_choice)
        elif choice == '6':
            print("\nCurrent envelope settings:")
            print(f"Attack: {detector.attack_time}s")
            print(f"Decay: {detector.decay_time}s")
            print(f"Sustain: {detector.sustain_level}")
            print(f"Release: {detector.release_time}s")
            
            setting = input("\nEnter setting to change (a/d/s/r): ").lower()
            if setting == 'a':
                value = float(input(f"Enter attack time in seconds (current: {detector.attack_time}): ") or str(detector.attack_time))
                detector.set_attack(value)
            elif setting == 'd':
                value = float(input(f"Enter decay time in seconds (current: {detector.decay_time}): ") or str(detector.decay_time))
                detector.set_decay(value)
            elif setting == 's':
                value = float(input(f"Enter sustain level 0-1 (current: {detector.sustain_level}): ") or str(detector.sustain_level))
                detector.set_sustain(value)
            elif setting == 'r':
                value = float(input(f"Enter release time in seconds (current: {detector.release_time}): ") or str(detector.release_time))
                detector.set_release(value)
            else:
                print("Invalid setting")
        elif choice == '7':
            if os.path.exists("click_detector.log"):
                print("\n=== LOG FILE CONTENTS ===")
                with open("click_detector.log", "r") as f:
                    # Print the last 20 lines
                    lines = f.readlines()
                    for line in lines[-20:]:
                        print(line.strip())
                print("=========================")
            else:
                print("Log file not found")
        elif choice == '8':
            detector.cleanup()
            print("Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
