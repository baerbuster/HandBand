import numpy as np
import pyaudio
import time


# === Synth Settings ===
SAMPLE_RATE = 44100
VOLUME = 1.0  # Max volume
NOTE_DURATION = 0.3  # seconds
REST_DURATION = 0.2  # between notes

def freq_from_midi(midi_note):
    return 440.0 * (2 ** ((midi_note - 69) / 12.0))

def sine_wave(frequency, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return VOLUME * np.sin(2 * np.pi * frequency * t).astype(np.float32)

# === Audio Stream Setup ===
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=SAMPLE_RATE,
                output=True)

print("Synth running. Press Ctrl+C to stop.")
try:
    while True:
        wave = sine_wave(freq_from_midi(60), NOTE_DURATION)
        stream.write(wave)
        time.sleep(REST_DURATION)
except KeyboardInterrupt:
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Exited.")
