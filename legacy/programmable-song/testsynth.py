import ctypes
import time

# Load the shared library
synth = ctypes.CDLL("./libsynth.dylib")

# Set the function prototypes
synth.start_synth.restype = None
synth.stop_synth.restype = None
synth.set_frequency.argtypes = [ctypes.c_double]
synth.set_frequency.restype = None

# Play a note
synth.set_frequency(440.0)  # A4
synth.start_synth()
time.sleep(2)               # sustain for 2 seconds
synth.stop_synth()
