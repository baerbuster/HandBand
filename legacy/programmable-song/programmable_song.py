#Imports
import soundfile as sf
import sounddevice as sd
import numpy as np
import tkinter as tk
import threading
import time

#Some variable declarations
buffers = {}
sample_rate = 44100
sample_position = 0
current_measure = "measure1"
next_measure = "measure1"
lock = threading.Lock()
stream = None
fade_out_duration = 2  # seconds for fade-out effect
fade_out_samples = int(fade_out_duration * sample_rate)
is_stopping = False  # Flag to indicate if we're stopping
stop_sample_position = 0  # Track where we are in the fade-out
stop_complete = False  # Flag to track if stop has finished

#Load and Prep Audio Here
def load_audio():
    global buffers, sample_rate
    buffers['measure1'], sample_rate = sf.read('ProgrammableLoop.wav', dtype='float32')
    buffers['measure2'], _ = sf.read('ProgrammableLoop2.wav', dtype='float32')
    #Check for Stereo and convert to mono
    for key in buffers:
        if buffers[key].ndim == 2:
            buffers[key] = np.mean(buffers[key], axis=1)

#Realtime Processing
def audio_callback(outdata, frames, time_info, status):
    global sample_position, current_measure, next_measure, is_stopping, stop_sample_position, stop_complete
    #Lock "current measure" and copy it to "buffer"
    with lock:
        buffer = buffers[current_measure]
    #Initialize final output buffer
    out = np.zeros(frames, dtype='float32')
    length = len(buffer)

    #Check for stop fade out, otherwise copy current sample under "buffer" and paste it to final output buffer
    for i in range(frames):
        if is_stopping:
            # Apply fade-out
            fade_factor = 1 - (stop_sample_position / fade_out_samples)
            if stop_sample_position < fade_out_samples:
                out[i] = buffer[sample_position] * fade_factor
                stop_sample_position += 1
            else:
                out[i] = 0  # Ensure silence after fade-out
                stop_complete = True  # Mark stop as complete
        else:
            out[i] = buffer[sample_position]
        
        #Progress samples, if end is reached, lock and reestablish next loop
        sample_position += 1
        if sample_position >= length:
            sample_position = 0
            with lock:
                current_measure = next_measure
                buffer = buffers[current_measure]
                length = len(buffer)

    #Reshape data for output, mono stylin'
    outdata[:] = out.reshape(-1, 1)

def start_audio():
    global stream
    stream = sd.OutputStream(callback=audio_callback, samplerate=sample_rate, channels=1, dtype='float32')
    stream.start()

def stop_audio():
    global stream, is_stopping, stop_sample_position, stop_complete
    if stream:
        is_stopping = True  # Set flag to initiate fade-out
        stop_sample_position = 0  # Reset stop sample_position to begin fade-out from the start

        # Allow the callback to finish fading out
        while not stop_complete:
            time.sleep(0.01)  # Wait for fade-out to complete

        # After fade-out completes, stop the audio
        stream.stop()  
        stream.close()  
        is_stopping = False  # Reset flag after stopping

def update_measure(val):
    global next_measure
    with lock:
        next_measure = 'measure1' if float(val) == 0 else 'measure2'

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
