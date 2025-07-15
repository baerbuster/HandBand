#!/usr/bin/env python3
"""
Multi-Synth Demo

This script demonstrates how to use multiple synth instances simultaneously,
each with different parameters and playing different patterns.
"""

import time
import threading
import math
import tkinter as tk
from typing import Dict, List, Any, Union, Optional, Callable

# Import our synth modules
from synth_class import Synth
from synth_config import (
    get_preset_config, 
    PATTERN_LABELS, 
    BASS_PATTERNS, 
    INTERVAL_TO_SEMITONE,
    DEFAULT_BPM,
    STEPS_PER_MEASURE,
    BASE_MIDI_NOTE,
    MASTER_VOLUME
)

class SynthSequencer:
    """
    A sequencer for controlling multiple synth instances with different patterns.
    """
    def __init__(self):
        self.synths: Dict[str, Synth] = {}
        self.patterns: Dict[str, List[List[Union[str, int]]]] = {}
        self.current_steps: Dict[str, int] = {}
        self.playing: bool = False
        self.bpm: float = DEFAULT_BPM
        self.stop_event = threading.Event()
        self.sequencer_thread = None
        
    def add_synth(self, name: str, preset: str = 'bass', config_overrides: Optional[Dict[str, Any]] = None):
        """
        Add a synth instance to the sequencer.
        
        Args:
            name: Name to identify this synth instance
            preset: Preset configuration to use ('bass', 'lead', 'pad')
            config_overrides: Optional dictionary of parameters to override in the preset
        """
        # Get the preset configuration
        config = get_preset_config(preset)
        
        # Apply any overrides
        if config_overrides:
            config.update(config_overrides)
        
        # Create the synth instance
        self.synths[name] = Synth(config)
        
        # Initialize pattern tracking
        self.patterns[name] = []
        self.current_steps[name] = 0
        
        # Start the synth
        self.synths[name].start_synth()
        
        print(f"Added synth '{name}' with preset '{preset}'")
        return self.synths[name]
    
    def set_pattern(self, synth_name: str, pattern: List[List[Union[str, int]]]):
        """
        Set a pattern for a specific synth.
        
        Args:
            synth_name: Name of the synth to set the pattern for
            pattern: List of pattern steps (each step is a list of notes or 0 for silence)
        """
        if synth_name in self.synths:
            self.patterns[synth_name] = pattern
            self.current_steps[synth_name] = 0
            print(f"Set pattern for synth '{synth_name}'")
        else:
            print(f"Synth '{synth_name}' not found")
    
    def start(self):
        """Start the sequencer."""
        if not self.playing:
            self.playing = True
            self.stop_event.clear()
            self.sequencer_thread = threading.Thread(
                target=self._sequencer_loop,
                daemon=True
            )
            self.sequencer_thread.start()
            print("Sequencer started")
    
    def stop(self):
        """Stop the sequencer."""
        if self.playing:
            self.playing = False
            self.stop_event.set()
            if self.sequencer_thread:
                self.sequencer_thread.join(timeout=1.0)
            
            # Stop all notes
            for name, synth in self.synths.items():
                synth.note_off()
            
            print("Sequencer stopped")
    
    def set_bpm(self, bpm: float):
        """Set the sequencer tempo in beats per minute."""
        self.bpm = max(40.0, min(300.0, bpm))
        print(f"BPM set to {self.bpm}")
    
    def _sequencer_loop(self):
        """Main sequencer loop - runs in a separate thread."""
        seconds_per_beat = 60.0 / self.bpm
        seconds_per_step = seconds_per_beat / 4  # 16th notes
        
        note_playing = {name: False for name in self.synths}
        
        while not self.stop_event.is_set():
            start_time = time.time()
            
            # Process each synth
            for name, synth in self.synths.items():
                if not self.patterns[name]:
                    continue
                
                pattern = self.patterns[name]
                step_index = self.current_steps[name]
                pattern_index = step_index % len(pattern)
                
                # Get the current step
                current_step = pattern[pattern_index]
                
                # Process the step
                if current_step == 0:  # Rest
                    if note_playing[name]:
                        synth.note_off()
                        note_playing[name] = False
                elif current_step == 'c':  # Continue
                    pass  # Keep the current note
                else:  # New note
                    if note_playing[name]:
                        synth.note_off()
                    
                    # Convert interval to MIDI note if it's a string
                    if isinstance(current_step, str) and current_step in INTERVAL_TO_SEMITONE:
                        midi_note = BASE_MIDI_NOTE + INTERVAL_TO_SEMITONE[current_step]
                        freq = 440.0 * 2 ** ((midi_note - 69) / 12)
                        synth.set_frequency(freq)
                        synth.note_on()
                        note_playing[name] = True
                
                # Move to next step
                self.current_steps[name] = (step_index + 1) % (len(pattern) * 2)  # Double pattern length for variation
            
            # Calculate sleep time for next step
            elapsed = time.time() - start_time
            sleep_time = max(0.001, seconds_per_step - elapsed)
            time.sleep(sleep_time)
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        for name, synth in self.synths.items():
            try:
                synth.stop_synth()
            except:
                pass
        print("All synths stopped and cleaned up")


class MultiSynthApp:
    """
    GUI application for controlling multiple synths.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Synth Demo")
        self.root.geometry("800x600")
        
        # Create sequencer
        self.sequencer = SynthSequencer()
        
        # Set up UI
        self._create_ui()
        
        # Set up synths with different configurations
        self._setup_synths()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_ui(self):
        """Create the user interface."""
        # Main frame
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="Multi-Synth Demo", 
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # BPM control
        bpm_frame = tk.Frame(main_frame)
        bpm_frame.pack(fill=tk.X, pady=10)
        
        bpm_label = tk.Label(bpm_frame, text="BPM:", width=10)
        bpm_label.pack(side=tk.LEFT)
        
        self.bpm_var = tk.StringVar(value=str(DEFAULT_BPM))
        bpm_entry = tk.Entry(bpm_frame, textvariable=self.bpm_var, width=6)
        bpm_entry.pack(side=tk.LEFT, padx=5)
        
        bpm_slider = tk.Scale(
            bpm_frame, 
            from_=60, 
            to=200, 
            orient=tk.HORIZONTAL, 
            length=300,
            command=self._on_bpm_change
        )
        bpm_slider.set(DEFAULT_BPM)
        bpm_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # Control buttons
        control_frame = tk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        start_button = tk.Button(
            control_frame, 
            text="Start", 
            command=self._start_sequencer,
            width=10,
            height=2
        )
        start_button.pack(side=tk.LEFT, padx=5)
        
        stop_button = tk.Button(
            control_frame, 
            text="Stop", 
            command=self._stop_sequencer,
            width=10,
            height=2
        )
        stop_button.pack(side=tk.LEFT, padx=5)
        
        # Synth controls frame
        synths_frame = tk.LabelFrame(main_frame, text="Synth Controls", padx=10, pady=10)
        synths_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # We'll add synth-specific controls in _setup_synths
        self.synth_frames = {}
    
    def _setup_synths(self):
        """Set up multiple synth instances with different configurations."""
        # Bass synth
        bass_synth = self.sequencer.add_synth(
            "bass", 
            "bass", 
            {
                'master_volume': 0.6,
                'filter_cutoff': 300.0,
                'filter_resonance': 2.0,
                'filter_env_mod': 40.0,
            }
        )
        self.sequencer.set_pattern("bass", BASS_PATTERNS[8])  # Neutral pattern
        
        # Lead synth
        lead_synth = self.sequencer.add_synth(
            "lead", 
            "lead", 
            {
                'master_volume': 0.4,
                'attack': 0.05,
                'release': 0.3,
                'filter_cutoff': 1500.0,
                'filter_resonance': 4.0,
                'lfo_rate': 5.0,
                'lfo_depth': 10.0,
            }
        )
        # Create a simple lead pattern (one octave up from bass)
        lead_pattern = [
            ['8', 0, 0, 0, '5', 0, 0, 0, '6', 0, '5', 0, '3', 0, 0, 0],
            [0, 0, '5', 0, 0, 0, '3', 0, '5', 0, 0, 0, '8', 0, '5', 0],
        ]
        self.sequencer.set_pattern("lead", lead_pattern)
        
        # Pad synth
        pad_synth = self.sequencer.add_synth(
            "pad", 
            "pad", 
            {
                'master_volume': 0.3,
                'attack': 1.0,
                'release': 2.0,
                'filter_cutoff': 600.0,
                'filter_resonance': 0.7,
                'lfo_rate': 0.3,
                'lfo_depth': 15.0,
            }
        )
        # Create a simple pad pattern (whole notes)
        pad_pattern = [
            ['1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
            ['5', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
            ['b3', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
        ]
        self.sequencer.set_pattern("pad", pad_pattern)
        
        # Create UI controls for each synth
        self._create_synth_controls()
    
    def _create_synth_controls(self):
        """Create UI controls for each synth."""
        # Get the synths frame
        synths_frame = self.root.winfo_children()[0].winfo_children()[-1]
        
        # Create a frame for each synth
        for i, (name, synth) in enumerate(self.sequencer.synths.items()):
            frame = tk.LabelFrame(synths_frame, text=f"{name.capitalize()} Synth", padx=5, pady=5)
            frame.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
            
            # Volume control
            volume_label = tk.Label(frame, text="Volume:")
            volume_label.grid(row=0, column=0, sticky="w")
            
            volume_slider = tk.Scale(
                frame, 
                from_=0, 
                to=1.0, 
                resolution=0.01,
                orient=tk.HORIZONTAL, 
                length=150,
                command=lambda v, n=name: self._set_synth_volume(n, float(v))
            )
            volume_slider.set(0.5)
            volume_slider.grid(row=0, column=1, sticky="ew")
            
            # Enable/disable checkbox
            enabled_var = tk.BooleanVar(value=True)
            enabled_check = tk.Checkbutton(
                frame, 
                text="Enabled", 
                variable=enabled_var,
                command=lambda n=name, v=enabled_var: self._toggle_synth(n, v.get())
            )
            enabled_check.grid(row=1, column=0, sticky="w")
            
            # Pattern selector (for bass only)
            if name == "bass":
                pattern_label = tk.Label(frame, text="Pattern:")
                pattern_label.grid(row=2, column=0, sticky="w")
                
                pattern_var = tk.StringVar(value="Neutral")
                pattern_menu = tk.OptionMenu(
                    frame, 
                    pattern_var, 
                    *PATTERN_LABELS,
                    command=lambda v, n=name: self._set_pattern(n, v)
                )
                pattern_menu.grid(row=2, column=1, sticky="ew")
            
            # Store the frame reference
            self.synth_frames[name] = frame
        
        # Configure grid weights
        rows, cols = (2, 2)
        for i in range(rows):
            synths_frame.grid_rowconfigure(i, weight=1)
        for i in range(cols):
            synths_frame.grid_columnconfigure(i, weight=1)
    
    def _set_synth_volume(self, synth_name: str, volume: float):
        """Set the volume for a specific synth."""
        if synth_name in self.sequencer.synths:
            self.sequencer.synths[synth_name].set_master_volume(volume)
    
    def _toggle_synth(self, synth_name: str, enabled: bool):
        """Enable or disable a specific synth."""
        if synth_name in self.sequencer.synths:
            if not enabled:
                self.sequencer.synths[synth_name].note_off()
                # Clear the pattern temporarily
                self.sequencer.patterns[synth_name + "_backup"] = self.sequencer.patterns[synth_name]
                self.sequencer.patterns[synth_name] = []
            else:
                # Restore the pattern
                if synth_name + "_backup" in self.sequencer.patterns:
                    self.sequencer.patterns[synth_name] = self.sequencer.patterns[synth_name + "_backup"]
                    del self.sequencer.patterns[synth_name + "_backup"]
    
    def _set_pattern(self, synth_name: str, pattern_name: str):
        """Set the pattern for a specific synth."""
        if synth_name in self.sequencer.synths:
            pattern_index = PATTERN_LABELS.index(pattern_name)
            if pattern_index < len(BASS_PATTERNS):
                self.sequencer.set_pattern(synth_name, BASS_PATTERNS[pattern_index])
    
    def _on_bpm_change(self, value):
        """Handle BPM slider change."""
        bpm = float(value)
        self.bpm_var.set(str(int(bpm)))
        self.sequencer.set_bpm(bpm)
    
    def _start_sequencer(self):
        """Start the sequencer."""
        self.sequencer.start()
    
    def _stop_sequencer(self):
        """Stop the sequencer."""
        self.sequencer.stop()
    
    def _on_close(self):
        """Handle window close event."""
        self.sequencer.cleanup()
        self.root.destroy()


def run_headless_demo():
    """Run a headless demo without GUI."""
    print("Starting headless multi-synth demo...")
    
    # Create sequencer
    sequencer = SynthSequencer()
    
    # Set up synths
    bass = sequencer.add_synth("bass", "bass")
    lead = sequencer.add_synth("lead", "lead")
    pad = sequencer.add_synth("pad", "pad")
    
    # Set patterns
    sequencer.set_pattern("bass", BASS_PATTERNS[8])  # Neutral pattern
    
    # Lead pattern (one octave up)
    lead_pattern = [
        ['8', 0, 0, 0, '5', 0, 0, 0, '6', 0, '5', 0, '3', 0, 0, 0],
        [0, 0, '5', 0, 0, 0, '3', 0, '5', 0, 0, 0, '8', 0, '5', 0],
    ]
    sequencer.set_pattern("lead", lead_pattern)
    
    # Pad pattern (whole notes)
    pad_pattern = [
        ['1', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
        ['5', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    ]
    sequencer.set_pattern("pad", pad_pattern)
    
    # Set BPM
    sequencer.set_bpm(120)
    
    # Start sequencer
    sequencer.start()
    
    print("Playing for 30 seconds...")
    try:
        # Play for 30 seconds
        time.sleep(10)
        
        # Change patterns
        print("Changing patterns...")
        sequencer.set_pattern("bass", BASS_PATTERNS[12])  # HappyLevel4
        
        time.sleep(10)
        
        # Change BPM
        print("Increasing tempo...")
        sequencer.set_bpm(140)
        
        time.sleep(10)
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        sequencer.cleanup()
        print("Demo finished")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        # Run headless demo
        run_headless_demo()
    else:
        # Run GUI demo
        root = tk.Tk()
        app = MultiSynthApp(root)
        root.mainloop()
