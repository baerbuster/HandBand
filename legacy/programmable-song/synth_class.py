"""
Synth Class - Python wrapper for the SynthLib C++ library

This module provides a class-based interface to the SynthLib audio engine,
allowing multiple synth instances to be created and controlled independently.
"""

import ctypes
import atexit
import time
import os
import platform

class Synth:
    """
    A class representing a synthesizer instance.
    
    This class wraps the C API of the SynthLib audio engine, allowing for
    multiple synth instances to be created and controlled independently.
    """
    
    # Keep track of all instances to ensure proper cleanup
    _instances = {}
    _lib = None
    
    @classmethod
    def _load_library(cls):
        """Load the synth library and set up function prototypes."""
        if cls._lib is not None:
            return
            
        # Determine the correct library extension based on platform
        if platform.system() == "Windows":
            lib_name = "synthlib.dll"
        elif platform.system() == "Darwin":  # macOS
            lib_name = "synthlib.so"
        else:  # Linux and others
            lib_name = "synthlib.so"
            
        # Try to load from current directory first
        try:
            cls._lib = ctypes.CDLL(f"./{lib_name}")
        except OSError:
            # Try to load using absolute path if relative path fails
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cls._lib = ctypes.CDLL(os.path.join(script_dir, lib_name))
        
        # Set up function prototypes for the C API
        
        # Instance management
        cls._lib.create_synth.argtypes = []
        cls._lib.create_synth.restype = ctypes.c_int
        cls._lib.delete_synth.argtypes = [ctypes.c_int]
        cls._lib.delete_synth.restype = None
        
        # Initialization/Shutdown
        cls._lib.initialize_synth_system.argtypes = []
        cls._lib.initialize_synth_system.restype = None
        cls._lib.shutdown_synth_system.argtypes = []
        cls._lib.shutdown_synth_system.restype = None

        # Initialize the synth system
        cls._lib.initialize_synth_system()
        
        # Core functions
        cls._lib.start_synth.argtypes = [ctypes.c_int]
        cls._lib.start_synth.restype = None
        cls._lib.note_on.argtypes = [ctypes.c_int]
        cls._lib.note_on.restype = None
        cls._lib.note_off.argtypes = [ctypes.c_int]
        cls._lib.note_off.restype = None
        cls._lib.stop_synth.argtypes = [ctypes.c_int]
        cls._lib.stop_synth.restype = None
        
        # Parameter setters
        cls._lib.set_frequency.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_frequency.restype = None
        cls._lib.set_sample_rate.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_sample_rate.restype = None
        cls._lib.set_master_volume.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_master_volume.restype = None
        
        # ADSR envelope
        cls._lib.set_attack.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_attack.restype = None
        cls._lib.set_decay.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_decay.restype = None
        cls._lib.set_sustain_level.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_sustain_level.restype = None
        cls._lib.set_release.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_release.restype = None
        
        # Oscillator settings
        cls._lib.set_sine_gain.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_sine_gain.restype = None
        cls._lib.set_square_gain.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_square_gain.restype = None
        cls._lib.set_fm_depth.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_fm_depth.restype = None
        
        # Sample settings
        cls._lib.set_sample_path.argtypes = [ctypes.c_int, ctypes.c_char_p]
        cls._lib.set_sample_path.restype = None
        cls._lib.set_sample_base_frequency.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_sample_base_frequency.restype = None
        cls._lib.set_sample_loop_start_percentage.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_sample_loop_start_percentage.restype = None
        cls._lib.set_sample_loop_end_percentage.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_sample_loop_end_percentage.restype = None
        
        # Fade and smoothing settings
        cls._lib.set_fade_samples.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_fade_samples.restype = None
        cls._lib.set_fade_in_time.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_fade_in_time.restype = None
        cls._lib.set_loop_fade_samples.argtypes = [ctypes.c_int, ctypes.c_uint]
        cls._lib.set_loop_fade_samples.restype = None
        cls._lib.set_gain_smoothing_time_seconds.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_gain_smoothing_time_seconds.restype = None
        cls._lib.set_gain_normalization_cap.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_gain_normalization_cap.restype = None
        
        # Filter settings
        cls._lib.set_filter_cutoff.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_cutoff.restype = None
        cls._lib.set_filter_resonance.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_resonance.restype = None
        cls._lib.set_filter_drive.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_drive.restype = None
        cls._lib.set_filter_key_tracking.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_key_tracking.restype = None
        cls._lib.set_filter_env_mod.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_env_mod.restype = None
        cls._lib.set_filter_drive_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_drive_scaling.restype = None
        cls._lib.set_filter_env_mod_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_env_mod_scaling.restype = None
        
        # Comb filter settings
        cls._lib.set_comb_cutoff.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_cutoff.restype = None
        cls._lib.set_comb_resonance.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_resonance.restype = None
        cls._lib.set_comb_drive.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_drive.restype = None
        cls._lib.set_comb_key_tracking.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_key_tracking.restype = None
        cls._lib.set_comb_env_mod.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_env_mod.restype = None
        cls._lib.set_comb_min_delay_ms.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_min_delay_ms.restype = None
        cls._lib.set_comb_max_delay_ms.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_max_delay_ms.restype = None
        cls._lib.set_comb_feedback_max.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_feedback_max.restype = None
        cls._lib.set_comb_feedback_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_feedback_scaling.restype = None
        cls._lib.set_comb_feedback_limiter.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_feedback_limiter.restype = None
        cls._lib.set_comb_env_mod_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_env_mod_scaling.restype = None
        cls._lib.set_comb_min_resonance.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_min_resonance.restype = None
        cls._lib.set_comb_limiter_strength.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_limiter_strength.restype = None
        cls._lib.set_comb_filter_drive_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_comb_filter_drive_scaling.restype = None
        
        # Global filter settings
        cls._lib.set_global_cutoff.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_global_cutoff.restype = None
        cls._lib.set_global_resonance.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_global_resonance.restype = None
        
        # Filter envelope settings
        cls._lib.set_filter_env_attack.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_env_attack.restype = None
        cls._lib.set_filter_env_decay.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_env_decay.restype = None
        cls._lib.set_filter_env_sustain.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_env_sustain.restype = None
        cls._lib.set_filter_env_release.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_filter_env_release.restype = None
        
        # LFO settings
        cls._lib.set_lfo_rate.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_lfo_rate.restype = None
        cls._lib.set_lfo_depth.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_lfo_depth.restype = None
        cls._lib.set_lfo_level.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_lfo_level.restype = None
        
        # Tube driver settings
        cls._lib.set_tube_amount.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_amount.restype = None
        cls._lib.set_tube_min_mix.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_min_mix.restype = None
        cls._lib.set_tube_max_mix.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_max_mix.restype = None
        cls._lib.set_tube_drive_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_drive_scaling.restype = None
        cls._lib.set_tube_intensity_scaling.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_intensity_scaling.restype = None
        cls._lib.set_tube_quintic_coeff.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_quintic_coeff.restype = None
        cls._lib.set_tube_cubic_coeff.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_cubic_coeff.restype = None
        cls._lib.set_tube_bypass_threshold.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_tube_bypass_threshold.restype = None
        
        # Bitcrusher settings
        cls._lib.set_bit_depth.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bit_depth.restype = None
        cls._lib.set_bit_mix.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bit_mix.restype = None
        cls._lib.set_bitcrusher_min_depth.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bitcrusher_min_depth.restype = None
        cls._lib.set_bitcrusher_max_depth.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bitcrusher_max_depth.restype = None
        cls._lib.set_bitcrusher_bypass_threshold.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bitcrusher_bypass_threshold.restype = None
        cls._lib.set_bitcrusher_mix_scale_threshold.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bitcrusher_mix_scale_threshold.restype = None
        cls._lib.set_bitcrusher_dither_threshold.argtypes = [ctypes.c_int, ctypes.c_double]
        cls._lib.set_bitcrusher_dither_threshold.restype = None
    
    @classmethod
    def _cleanup_all(cls):
        """Clean up all synth instances at program exit."""
        for synth_id in list(cls._instances.keys()):
            try:
                cls._lib.delete_synth(synth_id)
            except:
                pass
        cls._instances.clear()
        
        # Shutdown the synth system
        try:
            cls._lib.shutdown_synth_system()
        except:
            pass
    
    def __init__(self, config=None):
        """
        Initialize a new synth instance.
        
        Args:
            config (dict, optional): Configuration dictionary with initial settings.
        """
        # Load the library if not already loaded
        self.__class__._load_library()
        
        # Create a new synth instance
        self.synth_id = self.__class__._lib.create_synth()
        self.__class__._instances[self.synth_id] = self
        
        # Apply default configuration
        self.set_default_config()
        
        # Apply custom configuration if provided
        if config:
            self.apply_config(config)
        
        # Register cleanup handler if not already registered
        if not hasattr(self.__class__, "_cleanup_registered"):
            atexit.register(self.__class__._cleanup_all)
            self.__class__._cleanup_registered = True
    
    def __del__(self):
        """Clean up the synth instance when the Python object is deleted."""
        if hasattr(self, "synth_id") and self.synth_id in self.__class__._instances:
            try:
                self.__class__._lib.delete_synth(self.synth_id)
                del self.__class__._instances[self.synth_id]
            except:
                pass
    
    def set_default_config(self):
        """Apply sensible default configuration to the synth."""
        # Sample rate and basic settings
        self.set_sample_rate(44100)
        self.set_master_volume(0.1)
        
        # ADSR defaults
        self.set_attack(0.001)
        self.set_decay(0.5)
        self.set_sustain_level(-6.0)
        self.set_release(0.5)
        
        # Oscillator defaults
        self.set_sine_gain(1.0)
        self.set_square_gain(0.0)
        self.set_fm_depth(0.0)
        
        # Filter defaults
        self.set_filter_cutoff(20000.0)
        self.set_filter_resonance(0.7071)
        self.set_filter_drive(0.0)
        self.set_filter_key_tracking(0.0)
        self.set_filter_env_mod(0.0)
        
        # Comb filter defaults
        self.set_comb_cutoff(20000.0)
        self.set_comb_resonance(0.7071)
        self.set_comb_drive(0.0)
        self.set_comb_key_tracking(0.0)
        self.set_comb_env_mod(0.0)
        
        # Global filter defaults
        self.set_global_cutoff(632.456)
        self.set_global_resonance(3.16228)
        
        # Filter envelope defaults
        self.set_filter_env_attack(0.001)
        self.set_filter_env_decay(0.5)
        self.set_filter_env_sustain(-20.0)
        self.set_filter_env_release(0.5)
        
        # LFO defaults
        self.set_lfo_rate(1.0)
        self.set_lfo_depth(0.0)
        self.set_lfo_level(100.0)
        
        # Tube driver defaults
        self.set_tube_amount(0.0)
        self.set_tube_min_mix(0.0)
        self.set_tube_max_mix(100.0)
        
        # Bitcrusher defaults
        self.set_bit_depth(16.0)
        self.set_bit_mix(0.0)
    
    def apply_config(self, config):
        """
        Apply a configuration dictionary to the synth.
        
        Args:
            config (dict): Dictionary with parameter names and values.
        """
        # Map config keys to setter methods
        setters = {
            'sample_rate': self.set_sample_rate,
            'master_volume': self.set_master_volume,
            'attack': self.set_attack,
            'decay': self.set_decay,
            'sustain': self.set_sustain_level,
            'release': self.set_release,
            'sine_gain': self.set_sine_gain,
            'square_gain': self.set_square_gain,
            'fm_depth': self.set_fm_depth,
            'filter_cutoff': self.set_filter_cutoff,
            'filter_resonance': self.set_filter_resonance,
            'filter_drive': self.set_filter_drive,
            'filter_key_tracking': self.set_filter_key_tracking,
            'filter_env_mod': self.set_filter_env_mod,
            'comb_cutoff': self.set_comb_cutoff,
            'comb_resonance': self.set_comb_resonance,
            'comb_drive': self.set_comb_drive,
            'comb_key_tracking': self.set_comb_key_tracking,
            'comb_env_mod': self.set_comb_env_mod,
            'global_cutoff': self.set_global_cutoff,
            'global_resonance': self.set_global_resonance,
            'filter_env_attack': self.set_filter_env_attack,
            'filter_env_decay': self.set_filter_env_decay,
            'filter_env_sustain': self.set_filter_env_sustain,
            'filter_env_release': self.set_filter_env_release,
            'lfo_rate': self.set_lfo_rate,
            'lfo_depth': self.set_lfo_depth,
            'lfo_level': self.set_lfo_level,
            'tube_amount': self.set_tube_amount,
            'tube_min_mix': self.set_tube_min_mix,
            'tube_max_mix': self.set_tube_max_mix,
            'bit_depth': self.set_bit_depth,
            'bit_mix': self.set_bit_mix,
            'sample_path': self.set_sample_path,
            'sample_base_frequency': self.set_sample_base_frequency,
            'sample_loop_start_percentage': self.set_sample_loop_start_percentage,
            'sample_loop_end_percentage': self.set_sample_loop_end_percentage,
        }
        
        # Apply each setting
        for key, value in config.items():
            if key in setters:
                setters[key](value)
    
    # Core synth control methods
    
    def start_synth(self):
        """Start the synth and initialize audio processing."""
        self.__class__._lib.start_synth(self.synth_id)
    
    def note_on(self):
        """Trigger a note-on event (start playing a note)."""
        self.__class__._lib.note_on(self.synth_id)
    
    def note_off(self):
        """Trigger a note-off event (stop playing a note)."""
        self.__class__._lib.note_off(self.synth_id)
    
    def stop_synth(self):
        """Stop the synth and clean up audio resources."""
        self.__class__._lib.stop_synth(self.synth_id)
    
    # Parameter setter methods
    
    def set_frequency(self, freq):
        """Set the oscillator frequency in Hz."""
        self.__class__._lib.set_frequency(self.synth_id, ctypes.c_double(freq))
    
    def set_sample_rate(self, rate):
        """Set the audio sample rate in Hz."""
        self.__class__._lib.set_sample_rate(self.synth_id, ctypes.c_double(rate))
    
    def set_master_volume(self, volume):
        """Set the master volume (0.0 to 1.0 and beyond)."""
        self.__class__._lib.set_master_volume(self.synth_id, ctypes.c_double(volume))
    
    # ADSR envelope methods
    
    def set_attack(self, attack_seconds):
        """Set the attack time in seconds."""
        self.__class__._lib.set_attack(self.synth_id, ctypes.c_double(attack_seconds))
    
    def set_decay(self, decay_seconds):
        """Set the decay time in seconds."""
        self.__class__._lib.set_decay(self.synth_id, ctypes.c_double(decay_seconds))
    
    def set_sustain_level(self, level_db):
        """Set the sustain level in dB."""
        self.__class__._lib.set_sustain_level(self.synth_id, ctypes.c_double(level_db))
    
    def set_release(self, release_seconds):
        """Set the release time in seconds."""
        self.__class__._lib.set_release(self.synth_id, ctypes.c_double(release_seconds))
    
    # Oscillator methods
    
    def set_sine_gain(self, gain):
        """Set the sine oscillator gain (0.0 to 1.0)."""
        self.__class__._lib.set_sine_gain(self.synth_id, ctypes.c_double(gain))
    
    def set_square_gain(self, gain):
        """Set the square oscillator gain (0.0 to 1.0)."""
        self.__class__._lib.set_square_gain(self.synth_id, ctypes.c_double(gain))
    
    def set_fm_depth(self, depth):
        """Set the FM synthesis depth (0.0 to 1.0)."""
        self.__class__._lib.set_fm_depth(self.synth_id, ctypes.c_double(depth))
    
    # Sample methods
    
    def set_sample_path(self, path):
        """Set the path to the sample file."""
        self.__class__._lib.set_sample_path(self.synth_id, ctypes.c_char_p(path.encode('utf-8')))
    
    def set_sample_base_frequency(self, freq):
        """Set the base frequency of the sample in Hz."""
        self.__class__._lib.set_sample_base_frequency(self.synth_id, ctypes.c_double(freq))
    
    def set_sample_loop_start_percentage(self, percentage):
        """Set the loop start point as a percentage (0.0 to 1.0)."""
        self.__class__._lib.set_sample_loop_start_percentage(self.synth_id, ctypes.c_double(percentage))
    
    def set_sample_loop_end_percentage(self, percentage):
        """Set the loop end point as a percentage (0.0 to 1.0)."""
        self.__class__._lib.set_sample_loop_end_percentage(self.synth_id, ctypes.c_double(percentage))
    
    # Fade and smoothing methods
    
    def set_fade_samples(self, samples):
        """Set the number of samples for fade transitions."""
        self.__class__._lib.set_fade_samples(self.synth_id, ctypes.c_double(samples))
    
    def set_fade_in_time(self, time_ms):
        """Set the fade-in time in milliseconds."""
        self.__class__._lib.set_fade_in_time(self.synth_id, ctypes.c_double(time_ms))
    
    def set_loop_fade_samples(self, samples):
        """Set the number of samples for loop point crossfading."""
        self.__class__._lib.set_loop_fade_samples(self.synth_id, ctypes.c_uint(samples))
    
    def set_gain_smoothing_time_seconds(self, seconds):
        """Set the time for gain parameter smoothing in seconds."""
        self.__class__._lib.set_gain_smoothing_time_seconds(self.synth_id, ctypes.c_double(seconds))
    
    def set_gain_normalization_cap(self, cap):
        """Set the maximum gain normalization factor."""
        self.__class__._lib.set_gain_normalization_cap(self.synth_id, ctypes.c_double(cap))
    
    # Filter methods
    
    def set_filter_cutoff(self, cutoff_hz):
        """Set the filter cutoff frequency in Hz."""
        self.__class__._lib.set_filter_cutoff(self.synth_id, ctypes.c_double(cutoff_hz))
    
    def set_filter_resonance(self, resonance_q):
        """Set the filter resonance (Q factor)."""
        self.__class__._lib.set_filter_resonance(self.synth_id, ctypes.c_double(resonance_q))
    
    def set_filter_drive(self, drive_percent):
        """Set the filter drive amount as a percentage (0-100)."""
        self.__class__._lib.set_filter_drive(self.synth_id, ctypes.c_double(drive_percent))
    
    def set_filter_key_tracking(self, tracking_percent):
        """Set the filter key tracking as a percentage (0-100)."""
        self.__class__._lib.set_filter_key_tracking(self.synth_id, ctypes.c_double(tracking_percent))
    
    def set_filter_env_mod(self, mod_percent):
        """Set the filter envelope modulation as a percentage (0-100)."""
        self.__class__._lib.set_filter_env_mod(self.synth_id, ctypes.c_double(mod_percent))
    
    def set_filter_drive_scaling(self, scaling):
        """Set the filter drive scaling factor."""
        self.__class__._lib.set_filter_drive_scaling(self.synth_id, ctypes.c_double(scaling))
    
    def set_filter_env_mod_scaling(self, scaling):
        """Set the filter envelope modulation scaling factor."""
        self.__class__._lib.set_filter_env_mod_scaling(self.synth_id, ctypes.c_double(scaling))
    
    # Comb filter methods
    
    def set_comb_cutoff(self, cutoff_hz):
        """Set the comb filter cutoff frequency in Hz."""
        self.__class__._lib.set_comb_cutoff(self.synth_id, ctypes.c_double(cutoff_hz))
    
    def set_comb_resonance(self, resonance_q):
        """Set the comb filter resonance (Q factor)."""
        self.__class__._lib.set_comb_resonance(self.synth_id, ctypes.c_double(resonance_q))
    
    def set_comb_drive(self, drive_percent):
        """Set the comb filter drive amount as a percentage (0-100)."""
        self.__class__._lib.set_comb_drive(self.synth_id, ctypes.c_double(drive_percent))
    
    def set_comb_key_tracking(self, tracking_percent):
        """Set the comb filter key tracking as a percentage (0-100)."""
        self.__class__._lib.set_comb_key_tracking(self.synth_id, ctypes.c_double(tracking_percent))
    
    def set_comb_env_mod(self, mod_percent):
        """Set the comb filter envelope modulation as a percentage (0-100)."""
        self.__class__._lib.set_comb_env_mod(self.synth_id, ctypes.c_double(mod_percent))
    
    def set_comb_min_delay_ms(self, delay_ms):
        """Set the minimum delay time for the comb filter in milliseconds."""
        self.__class__._lib.set_comb_min_delay_ms(self.synth_id, ctypes.c_double(delay_ms))
    
    def set_comb_max_delay_ms(self, delay_ms):
        """Set the maximum delay time for the comb filter in milliseconds."""
        self.__class__._lib.set_comb_max_delay_ms(self.synth_id, ctypes.c_double(delay_ms))
    
    def set_comb_feedback_max(self, feedback):
        """Set the maximum feedback amount for the comb filter (0.0 to 1.0)."""
        self.__class__._lib.set_comb_feedback_max(self.synth_id, ctypes.c_double(feedback))
    
    def set_comb_feedback_scaling(self, scaling):
        """Set the feedback scaling factor for the comb filter."""
        self.__class__._lib.set_comb_feedback_scaling(self.synth_id, ctypes.c_double(scaling))
    
    def set_comb_feedback_limiter(self, limit):
        """Set the feedback limiter threshold for the comb filter."""
        self.__class__._lib.set_comb_feedback_limiter(self.synth_id, ctypes.c_double(limit))
    
    def set_comb_env_mod_scaling(self, scaling):
        """Set the envelope modulation scaling factor for the comb filter."""
        self.__class__._lib.set_comb_env_mod_scaling(self.synth_id, ctypes.c_double(scaling))
    
    def set_comb_min_resonance(self, resonance):
        """Set the minimum resonance for the comb filter."""
        self.__class__._lib.set_comb_min_resonance(self.synth_id, ctypes.c_double(resonance))
    
    def set_comb_limiter_strength(self, strength):
        """Set the limiter strength for the comb filter."""
        self.__class__._lib.set_comb_limiter_strength(self.synth_id, ctypes.c_double(strength))
    
    def set_comb_filter_drive_scaling(self, scaling):
        """Set the drive scaling factor for the comb filter."""
        self.__class__._lib.set_comb_filter_drive_scaling(self.synth_id, ctypes.c_double(scaling))
    
    # Global filter methods
    
    def set_global_cutoff(self, cutoff_hz):
        """Set the global cutoff frequency in Hz."""
        self.__class__._lib.set_global_cutoff(self.synth_id, ctypes.c_double(cutoff_hz))
    
    def set_global_resonance(self, resonance_q):
        """Set the global resonance (Q factor)."""
        self.__class__._lib.set_global_resonance(self.synth_id, ctypes.c_double(resonance_q))
    
    # Filter envelope methods
    
    def set_filter_env_attack(self, attack_seconds):
        """Set the filter envelope attack time in seconds."""
        self.__class__._lib.set_filter_env_attack(self.synth_id, ctypes.c_double(attack_seconds))
    
    def set_filter_env_decay(self, decay_seconds):
        """Set the filter envelope decay time in seconds."""
        self.__class__._lib.set_filter_env_decay(self.synth_id, ctypes.c_double(decay_seconds))
    
    def set_filter_env_sustain(self, level_db):
        """Set the filter envelope sustain level in dB."""
        self.__class__._lib.set_filter_env_sustain(self.synth_id, ctypes.c_double(level_db))
    
    def set_filter_env_release(self, release_seconds):
        """Set the filter envelope release time in seconds."""
        self.__class__._lib.set_filter_env_release(self.synth_id, ctypes.c_double(release_seconds))
    
    # LFO methods
    
    def set_lfo_rate(self, rate_hz):
        """Set the LFO rate in Hz."""
        self.__class__._lib.set_lfo_rate(self.synth_id, ctypes.c_double(rate_hz))
    
    def set_lfo_depth(self, depth_percent):
        """Set the LFO depth as a percentage (0-100)."""
        self.__class__._lib.set_lfo_depth(self.synth_id, ctypes.c_double(depth_percent))
    
    def set_lfo_level(self, level_percent):
        """Set the LFO level as a percentage (0-100)."""
        self.__class__._lib.set_lfo_level(self.synth_id, ctypes.c_double(level_percent))
    
    # Tube driver methods
    
    def set_tube_amount(self, amount_percent):
        """Set the tube driver amount as a percentage (0-100)."""
        self.__class__._lib.set_tube_amount(self.synth_id, ctypes.c_double(amount_percent))
    
    def set_tube_min_mix(self, mix_percent):
        """Set the tube driver minimum mix as a percentage (0-100)."""
        self.__class__._lib.set_tube_min_mix(self.synth_id, ctypes.c_double(mix_percent))
    
    def set_tube_max_mix(self, mix_percent):
        """Set the tube driver maximum mix as a percentage (0-100)."""
        self.__class__._lib.set_tube_max_mix(self.synth_id, ctypes.c_double(mix_percent))
    
    def set_tube_drive_scaling(self, scaling):
        """Set the tube driver drive scaling factor."""
        self.__class__._lib.set_tube_drive_scaling(self.synth_id, ctypes.c_double(scaling))
    
    def set_tube_intensity_scaling(self, scaling):
        """Set the tube driver intensity scaling factor."""
        self.__class__._lib.set_tube_intensity_scaling(self.synth_id, ctypes.c_double(scaling))
    
    def set_tube_quintic_coeff(self, coeff):
        """Set the tube driver quintic coefficient."""
        self.__class__._lib.set_tube_quintic_coeff(self.synth_id, ctypes.c_double(coeff))
    
    def set_tube_cubic_coeff(self, coeff):
        """Set the tube driver cubic coefficient."""
        self.__class__._lib.set_tube_cubic_coeff(self.synth_id, ctypes.c_double(coeff))
    
    def set_tube_bypass_threshold(self, threshold):
        """Set the tube driver bypass threshold."""
        self.__class__._lib.set_tube_bypass_threshold(self.synth_id, ctypes.c_double(threshold))
    
    # Bitcrusher methods
    
    def set_bit_depth(self, depth_bits):
        """Set the bitcrusher bit depth (1.0 to 16.0)."""
        self.__class__._lib.set_bit_depth(self.synth_id, ctypes.c_double(depth_bits))
    
    def set_bit_mix(self, mix_percent):
        """Set the bitcrusher mix as a percentage (0-100)."""
        self.__class__._lib.set_bit_mix(self.synth_id, ctypes.c_double(mix_percent))
    
    def set_bitcrusher_min_depth(self, depth):
        """Set the minimum bit depth for the bitcrusher."""
        self.__class__._lib.set_bitcrusher_min_depth(self.synth_id, ctypes.c_double(depth))
    
    def set_bitcrusher_max_depth(self, depth):
        """Set the maximum bit depth for the bitcrusher."""
        self.__class__._lib.set_bitcrusher_max_depth(self.synth_id, ctypes.c_double(depth))
    
    def set_bitcrusher_bypass_threshold(self, threshold):
        """Set the bitcrusher bypass threshold."""
        self.__class__._lib.set_bitcrusher_bypass_threshold(self.synth_id, ctypes.c_double(threshold))
    
    def set_bitcrusher_mix_scale_threshold(self, threshold):
        """Set the bitcrusher mix scale threshold."""
        self.__class__._lib.set_bitcrusher_mix_scale_threshold(self.synth_id, ctypes.c_double(threshold))
    
    def set_bitcrusher_dither_threshold(self, threshold):
        """Set the bitcrusher dither threshold."""
        self.__class__._lib.set_bitcrusher_dither_threshold(self.synth_id, ctypes.c_double(threshold))
