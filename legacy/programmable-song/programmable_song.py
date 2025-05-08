# Imports
import soundfile as sf
import sounddevice as sd
import numpy as np
import tkinter as tk
import threading
import time

# Some variable declarations
buffers = {}
sample_rate = 44100
sample_position = 0
current_measure = "measure1.1"
next_measure = "measure1.2"
lock = threading.Lock()
stream = None
fade_out_duration = 2  # seconds for fade-out effect
fade_out_samples = int(fade_out_duration * sample_rate)
is_stopping = False  # Flag to indicate if we're stopping
stop_sample_position = 0  # Track where we are in the fade-out
stop_complete = False  # Flag to track if stop has finished
measure1_list = ["measure1.1", "measure1.2", "measure1.3", "measure1.4", "measure1.5", "measure1.6", "measure1.7", "measure1.8"]
measure2_list = ["measure2.1", "measure2.2", "measure2.3", "measure2.4", "measure2.5", "measure2.6", "measure2.7", "measure2.8"]
loop1file_list = ["ProgrammableLoop1.1.wav", "ProgrammableLoop1.2.wav", "ProgrammableLoop1.3.wav", "ProgrammableLoop1.4.wav", "ProgrammableLoop1.5.wav", "ProgrammableLoop1.6.wav", "ProgrammableLoop1.7.wav", "ProgrammableLoop1.8.wav"]
loop2file_list = ["ProgrammableLoop2.1.wav", "ProgrammableLoop2.2.wav", "ProgrammableLoop2.3.wav", "ProgrammableLoop2.4.wav", "ProgrammableLoop2.5.wav", "ProgrammableLoop2.6.wav", "ProgrammableLoop2.7.wav", "ProgrammableLoop2.8.wav"]
measure_index = 0

# Load and Prep Audio Here
def load_audio():
    global buffers, sample_rate
    for measures, loop1file in zip(measure1_list, loop1file_list):
        buffers[measures], sample_rate = sf.read(loop1file, dtype='float32')
    for measures, loop2file in zip(measure2_list, loop2file_list):
        buffers[measures], sample_rate = sf.read(loop2file, dtype='float32')
    # Check for Stereo and convert to mono
    for key in buffers:
        if buffers[key].ndim == 2:
            buffers[key] = np.mean(buffers[key], axis=1)

# Realtime Processing
def audio_callback(outdata, frames, time_info, status):
    global sample_position, current_measure, measure_index, next_measure, is_stopping, stop_sample_position, stop_complete
    with lock:
        buffer = buffers[current_measure]
    
    out = np.zeros(frames, dtype='float32')
    length = len(buffer)

    for i in range(frames):
        if is_stopping:
            fade_factor = 1 - (stop_sample_position / fade_out_samples)
            if stop_sample_position < fade_out_samples:
                out[i] = buffer[sample_position] * fade_factor
                stop_sample_position += 1
            else:
                out[i] = 0
                stop_complete = True
        else:
            out[i] = buffer[sample_position]

        sample_position += 1

        if sample_position >= length:
            sample_position = 0

            # Handle measure switching between measure1 and measure2
            if current_measure == "measure1.8":  # End of measure1 cycle
                if float(slider.get()) == 1.0:
                    next_measure = 'measure2.1'
                    measure_index = 0
                else:
                    measure_index = 0
                    next_measure = measure1_list[measure_index]

            elif current_measure == "measure2.8":  # End of measure2 cycle
                if float(slider.get()) == 0.0:
                    next_measure = 'measure1.1'
                    measure_index = 0
                else:
                    measure_index = 0
                    next_measure = measure2_list[measure_index]

            else:
                if current_measure in measure1_list:
                    measure_list = measure1_list
                else:
                    measure_list = measure2_list

                if current_measure == measure_list[-1]:
                    measure_index = 0
                else:
                    measure_index = (measure_index + 1) % len(measure_list)

                next_measure = measure_list[measure_index]

            current_measure = next_measure
            buffer = buffers[current_measure]
            length = len(buffer)
        else:
            next_measure = current_measure

    outdata[:] = out.reshape(-1, 1)

# Audio playback start
def start_audio():
    global stream
    stream = sd.OutputStream(callback=audio_callback, samplerate=sample_rate, channels=1, dtype='float32')
    stream.start()

# Audio stop
def stop_audio():
    global stream, is_stopping, stop_sample_position, stop_complete
    if stream:
        is_stopping = True  # Set flag to initiate fade-out
        stop_sample_position = 0  # Reset stop sample_position to begin fade-out from the start
        stop_complete = False  # Reset flag for stop completion

        # Allow the callback to finish fading out
        while not stop_complete:
            time.sleep(0.01)  # Wait for fade-out to complete

        # After fade-out completes, stop the audio
        stream.stop()
        stream.close()
        is_stopping = False  # Reset flag after stopping

# Measure switching
def update_measure(val):
    global next_measure
    if float(val) == 1.0:
        next_measure = 'measure2.1'

# GUI setup
load_audio()
root = tk.Tk()
root.title("Measure Switcher")

# Set window size
root.geometry('500x300')

slider = tk.Scale(root, from_=0, to=1, orient=tk.HORIZONTAL, label="Select Measure", command=update_measure)
slider.pack(padx=20, pady=20)

# Play and Stop buttons
play_button = tk.Button(root, text="Play", command=start_audio)
play_button.pack(padx=20, pady=10)

stop_button = tk.Button(root, text="Stop", command=stop_audio)
stop_button.pack(padx=20, pady=10)

root.mainloop()
