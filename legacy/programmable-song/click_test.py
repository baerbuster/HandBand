#!/usr/bin/env python3
# click_test.py - Test program to evaluate clicks in various situations
# g++ -std=c++17 -fPIC -shared click_detector.cpp -o libclick.so -I/opt/homebrew/opt/portaudio/include -L/opt/homebrew/opt/portaudio/lib -lportaudio -pthread

import ctypes
import time
import threading
import tkinter as tk
from tkinter import ttk
import math
import os
import subprocess
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import numpy as np

# Constants
MIN_BPM = 80
MAX_BPM = 180
DEFAULT_BPM = 120
STEPS_PER_MEASURE = 16

# Test patterns
TEST_PATTERNS = {
    "Single Step": ['1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    "Two Steps": ['1', '1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    "Four Steps": ['1', '1', '1', '1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    "Eight Steps": ['1', '1', '1', '1', '1', '1', '1', '1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    "Alternating": ['1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c', '1', 'c'],
    "Sustain Test": ['1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', 'c'],
    "Release Test": ['1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', '1', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
}

class ClickTest:
    def __init__(self, root):
        self.root = root
        self.root.title("Click Detector Test")
        self.root.geometry("900x700")
        
        # Set up variables
        self.current_bpm = DEFAULT_BPM
        self.pattern = TEST_PATTERNS["Alternating"]
        self.pattern_name = tk.StringVar(value="Alternating")
        self.attack_time = tk.DoubleVar(value=0.3)
        self.decay_time = tk.DoubleVar(value=0.2)
        self.sustain_level = tk.DoubleVar(value=0.5)
        self.release_time = tk.DoubleVar(value=0.5)
        self.is_running = False
        self.stop_event = threading.Event()
        self.slider_val_lock = threading.Lock()
        self.slider_val = 0.5
        self.click_count = 0
        
        # Compile the click detector if needed
        if not os.path.exists("libclick.so"):
            self.compile_click_detector()
        
        # Load the click detector library
        try:
            self.synth = ctypes.CDLL('./libclick.so')
            print("Loaded click detector library")
            self.setup_synth_functions()
        except Exception as e:
            print(f"Failed to load click detector: {e}")
            self.show_error(f"Failed to load click detector: {e}")
            return
        
        # Create UI
        self.create_ui()
        
        # Start synth
        self.synth.start_synth()
        self.synth.set_bpm(ctypes.c_double(self.current_bpm))
        
        # Start sequencer thread
        self.sequencer_thread = threading.Thread(
            target=self.run_sequencer,
            daemon=True)
        self.sequencer_thread.start()
        
        # Set up close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def compile_click_detector(self):
        """Compile the click detector library"""
        try:
            cmd = [
                "g++", "-std=c++17", "-fPIC", "-shared", 
                "click_detector.cpp", "-o", "libclick.so",
                "-I/opt/homebrew/opt/portaudio/include",
                "-L/opt/homebrew/opt/portaudio/lib",
                "-lportaudio", "-pthread"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Compilation error: {result.stderr}")
                self.show_error(f"Failed to compile click detector: {result.stderr}")
            else:
                print("Successfully compiled click detector")
        except Exception as e:
            print(f"Compilation error: {e}")
            self.show_error(f"Failed to compile click detector: {e}")
    
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
    
    def create_ui(self):
        """Create the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Test Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=5)
        
        # BPM slider
        bpm_frame = ttk.Frame(control_frame)
        bpm_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(bpm_frame, text="BPM:").pack(side=tk.LEFT)
        self.bpm_label = ttk.Label(bpm_frame, text=f"{DEFAULT_BPM:.1f}")
        self.bpm_label.pack(side=tk.LEFT, padx=5)
        
        self.bpm_slider = ttk.Scale(
            bpm_frame, 
            from_=0, 
            to=1, 
            orient=tk.HORIZONTAL,
            command=self.on_bpm_change
        )
        self.bpm_slider.set(self.slider_to_bpm_pos(DEFAULT_BPM))
        self.bpm_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Pattern selection
        pattern_frame = ttk.LabelFrame(control_frame, text="Test Patterns", padding=10)
        pattern_frame.pack(fill=tk.X, pady=5)
        
        for i, (name, _) in enumerate(TEST_PATTERNS.items()):
            ttk.Radiobutton(
                pattern_frame, 
                text=name, 
                variable=self.pattern_name, 
                value=name,
                command=lambda n=name: self.on_pattern_select(n)
            ).grid(row=i//3, column=i%3, sticky=tk.W, padx=10, pady=2)
        
        # ADSR controls
        adsr_frame = ttk.LabelFrame(control_frame, text="Envelope Settings", padding=10)
        adsr_frame.pack(fill=tk.X, pady=5)
        
        # Attack
        ttk.Label(adsr_frame, text="Attack (s):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        attack_scale = ttk.Scale(
            adsr_frame, 
            from_=0.01, 
            to=1.0, 
            variable=self.attack_time,
            orient=tk.HORIZONTAL
        )
        attack_scale.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(
            adsr_frame, 
            text="Set", 
            command=lambda: self.set_attack(self.attack_time.get())
        ).grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(adsr_frame, textvariable=self.attack_time).grid(row=0, column=3, padx=5, pady=2)
        
        # Decay
        ttk.Label(adsr_frame, text="Decay (s):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        decay_scale = ttk.Scale(
            adsr_frame, 
            from_=0.01, 
            to=1.0, 
            variable=self.decay_time,
            orient=tk.HORIZONTAL
        )
        decay_scale.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(
            adsr_frame, 
            text="Set", 
            command=lambda: self.set_decay(self.decay_time.get())
        ).grid(row=1, column=2, padx=5, pady=2)
        ttk.Label(adsr_frame, textvariable=self.decay_time).grid(row=1, column=3, padx=5, pady=2)
        
        # Sustain
        ttk.Label(adsr_frame, text="Sustain:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        sustain_scale = ttk.Scale(
            adsr_frame, 
            from_=0.0, 
            to=1.0, 
            variable=self.sustain_level,
            orient=tk.HORIZONTAL
        )
        sustain_scale.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(
            adsr_frame, 
            text="Set", 
            command=lambda: self.set_sustain(self.sustain_level.get())
        ).grid(row=2, column=2, padx=5, pady=2)
        ttk.Label(adsr_frame, textvariable=self.sustain_level).grid(row=2, column=3, padx=5, pady=2)
        
        # Release
        ttk.Label(adsr_frame, text="Release (s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        release_scale = ttk.Scale(
            adsr_frame, 
            from_=0.01, 
            to=2.0, 
            variable=self.release_time,
            orient=tk.HORIZONTAL
        )
        release_scale.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(
            adsr_frame, 
            text="Set", 
            command=lambda: self.set_release(self.release_time.get())
        ).grid(row=3, column=2, padx=5, pady=2)
        ttk.Label(adsr_frame, textvariable=self.release_time).grid(row=3, column=3, padx=5, pady=2)
        
        adsr_frame.columnconfigure(1, weight=1)
        
        # Test buttons
        test_frame = ttk.Frame(control_frame)
        test_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            test_frame, 
            text="Single Note Test", 
            command=self.run_single_note_test
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            test_frame, 
            text="BPM Sweep Test", 
            command=self.run_bpm_sweep_test
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            test_frame, 
            text="Analyze Results", 
            command=self.analyze_results
        ).pack(side=tk.LEFT, padx=5)
        
        # Status and visualization area
        status_frame = ttk.LabelFrame(main_frame, text="Status and Results", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Status text
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("TkDefaultFont", 12))
        status_label.pack(fill=tk.X, pady=5)
        
        # Click counter
        self.click_count_var = tk.StringVar(value="Clicks detected: 0")
        click_count_label = ttk.Label(status_frame, textvariable=self.click_count_var, font=("TkDefaultFont", 12))
        click_count_label.pack(fill=tk.X, pady=5)
        
        # Visualization area
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=status_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial plot setup
        self.ax.set_title("Amplitude over time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True)
        self.canvas.draw()
    
    def slider_to_bpm_pos(self, bpm):
        """Convert BPM to slider position (0-1)"""
        log_min = math.log(MIN_BPM)
        log_max = math.log(MAX_BPM)
        return (math.log(bpm) - log_min) / (log_max - log_min)
    
    def bpm_pos_to_slider(self, pos):
        """Convert slider position (0-1) to BPM"""
        log_min = math.log(MIN_BPM)
        log_max = math.log(MAX_BPM)
        return math.exp(log_min + pos * (log_max - log_min))
    
    def on_bpm_change(self, val):
        """Handle BPM slider change"""
        with self.slider_val_lock:
            self.slider_val = float(val)
        
        bpm = self.bpm_pos_to_slider(float(val))
        self.current_bpm = bpm
        self.bpm_label.config(text=f"{bpm:.1f}")
        self.synth.set_bpm(ctypes.c_double(bpm))
    
    def on_pattern_select(self, name):
        """Handle pattern selection"""
        self.pattern = TEST_PATTERNS[name]
        self.status_var.set(f"Pattern: {name}")
    
    def set_attack(self, value):
        """Set attack time"""
        self.synth.set_attack(ctypes.c_double(value))
        self.status_var.set(f"Attack set to {value:.2f}s")
    
    def set_decay(self, value):
        """Set decay time"""
        self.synth.set_decay(ctypes.c_double(value))
        self.status_var.set(f"Decay set to {value:.2f}s")
    
    def set_sustain(self, value):
        """Set sustain level"""
        self.synth.set_sustain_level(ctypes.c_double(value))
        self.status_var.set(f"Sustain set to {value:.2f}")
    
    def set_release(self, value):
        """Set release time"""
        self.synth.set_release(ctypes.c_double(value))
        self.status_var.set(f"Release set to {value:.2f}s")
    
    def run_sequencer(self):
        """Run the sequencer thread"""
        step = 0
        note_is_on = False
        next_trigger = time.time()
        measure_count = 0
        
        while not self.stop_event.is_set():
            with self.slider_val_lock:
                current_slider_val = self.slider_val
            
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
            
            # Check for clicks
            if os.path.exists("click_detector.log"):
                try:
                    with open("click_detector.log", "r") as f:
                        content = f.read()
                        click_count = content.count("CLICK DETECTED")
                        if click_count != self.click_count:
                            self.click_count = click_count
                            self.click_count_var.set(f"Clicks detected: {click_count}")
                            self.update_visualization()
                except:
                    pass
    
    def run_single_note_test(self):
        """Run a single note test"""
        self.status_var.set("Running single note test...")
        
        # Turn on a note for 1 second
        self.synth.note_on()
        time.sleep(1.0)
        self.synth.note_off()
        
        self.status_var.set("Single note test complete")
        self.update_visualization()
    
    def run_bpm_sweep_test(self):
        """Run a BPM sweep test"""
        self.status_var.set("Running BPM sweep test...")
        
        # Save original BPM
        original_bpm = self.current_bpm
        
        # Test different BPMs
        for bpm in [80, 100, 120, 140, 160, 180]:
            self.current_bpm = bpm
            self.bpm_label.config(text=f"{bpm:.1f}")
            self.bpm_slider.set(self.slider_to_bpm_pos(bpm))
            self.synth.set_bpm(ctypes.c_double(bpm))
            
            self.status_var.set(f"Testing BPM: {bpm}")
            self.root.update()
            
            # Play a few notes
            for _ in range(3):
                self.synth.note_on()
                time.sleep(60 / bpm / 4)  # Duration of a 16th note
                self.synth.note_off()
                time.sleep(60 / bpm / 4)  # Rest for a 16th note
        
        # Restore original BPM
        self.current_bpm = original_bpm
        self.bpm_label.config(text=f"{original_bpm:.1f}")
        self.bpm_slider.set(self.slider_to_bpm_pos(original_bpm))
        self.synth.set_bpm(ctypes.c_double(original_bpm))
        
        self.status_var.set("BPM sweep test complete")
        self.update_visualization()
    
    def analyze_results(self):
        """Analyze the test results"""
        self.status_var.set("Analyzing results...")
        
        # Check if CSV file exists
        if not os.path.exists("sample_data.csv"):
            self.status_var.set("No sample data available. Run a test first.")
            return
        
        # Read the CSV file
        times = []
        amplitudes = []
        envelope_values = []
        note_states = []
        envelope_phases = []
        
        try:
            with open("sample_data.csv", "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    times.append(float(row["Time"]))
                    amplitudes.append(float(row["OutputAmplitude"]))
                    envelope_values.append(float(row["EnvelopeValue"]))
                    note_states.append(row["NoteState"])
                    envelope_phases.append(row["EnvelopePhase"])
        except Exception as e:
            self.status_var.set(f"Error reading sample data: {e}")
            return
        
        # Clear the plot
        self.ax.clear()
        
        # Plot the amplitude
        self.ax.plot(times, amplitudes, label="Output Amplitude")
        
        # Plot the envelope
        self.ax.plot(times, envelope_values, label="Envelope Value", linestyle="--")
        
        # Mark note on/off transitions
        note_on_times = []
        note_off_times = []
        prev_state = None
        
        for i, state in enumerate(note_states):
            if prev_state != state:
                if state == "ON":
                    note_on_times.append(times[i])
                elif state == "OFF":
                    note_off_times.append(times[i])
                prev_state = state
        
        for t in note_on_times:
            self.ax.axvline(x=t, color='g', linestyle='-', alpha=0.5, label="Note On" if t == note_on_times[0] else "")
        
        for t in note_off_times:
            self.ax.axvline(x=t, color='r', linestyle='-', alpha=0.5, label="Note Off" if t == note_off_times[0] else "")
        
        # Mark detected clicks
        click_times = []
        try:
            with open("click_detector.log", "r") as f:
                content = f.read()
                for line in content.split("\n"):
                    if "CLICK DETECTED at sample" in line:
                        parts = line.split("sample")[1].strip().split(" ")
                        sample_index = int(parts[0])
                        click_time = sample_index / 44100  # Convert sample index to time
                        click_times.append(click_time)
        except:
            pass
        
        for t in click_times:
            self.ax.axvline(x=t, color='m', linestyle='-', linewidth=2, alpha=0.7, label="Click" if t == click_times[0] else "")
        
        # Set plot properties
        self.ax.set_title(f"Amplitude over time (BPM: {self.current_bpm:.1f})")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True)
        self.ax.legend()
        
        # Update the canvas
        self.canvas.draw()
        
        self.status_var.set(f"Analysis complete. Found {len(click_times)} clicks.")
    
    def update_visualization(self):
        """Update the visualization with the latest data"""
        self.analyze_results()
    
    def show_error(self, message):
        """Show an error message"""
        error_window = tk.Toplevel(self.root)
        error_window.title("Error")
        error_window.geometry("400x200")
        
        ttk.Label(
            error_window, 
            text=message, 
            wraplength=380,
            justify=tk.CENTER,
            font=("TkDefaultFont", 12)
        ).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Button(
            error_window, 
            text="OK", 
            command=error_window.destroy
        ).pack(pady=10)
    
    def on_close(self):
        """Handle window close"""
        self.stop_event.set()
        if hasattr(self, 'sequencer_thread'):
            self.sequencer_thread.join(timeout=1.0)
        if hasattr(self, 'synth'):
            self.synth.stop_synth()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClickTest(root)
    root.mainloop()
