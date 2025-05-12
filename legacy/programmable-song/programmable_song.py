import soundfile as sf
import sounddevice as sd
import numpy as np
import tkinter as tk
import threading
import time

# === Variables ===
buffers = {}
sample_rate = 44100
sample_position = 0
current_measure = "measure1.1"
next_measure = "measure1.2"
measure_index = 0
lock = threading.Lock()
stream = None

fade_out_duration = 2
fade_out_samples = int(fade_out_duration * sample_rate)
is_stopping = False
stop_sample_position = 0
stop_complete = False

measure1_list = ["measure1.1", "measure1.2", "measure1.3", "measure1.4", "measure1.5", "measure1.6", "measure1.7", "measure1.8"]
measure2_list = ["measure2.1", "measure2.2", "measure2.3", "measure2.4", "measure2.5", "measure2.6", "measure2.7", "measure2.8"]
loop1file_list = ["ProgrammableLoop1.1.wav", "ProgrammableLoop1.2.wav", "ProgrammableLoop1.3.wav", "ProgrammableLoop1.4.wav", "ProgrammableLoop1.5.wav", "ProgrammableLoop1.6.wav", "ProgrammableLoop1.7.wav", "ProgrammableLoop1.8.wav"]
loop2file_list = ["ProgrammableLoop2.1.wav", "ProgrammableLoop2.2.wav", "ProgrammableLoop2.3.wav", "ProgrammableLoop2.4.wav", "ProgrammableLoop2.5.wav", "ProgrammableLoop2.6.wav", "ProgrammableLoop2.7.wav", "ProgrammableLoop2.8.wav"]

slider_value = 0.0  # Shared var for slider state

# === Load Audio ===
def load_audio():
    global buffers, sample_rate
    for measures, loop1file in zip(measure1_list, loop1file_list):
        buffers[measures], sample_rate = sf.read(loop1file, dtype='float32')
    for measures, loop2file in zip(measure2_list, loop2file_list):
        buffers[measures], sample_rate = sf.read(loop2file, dtype='float32')
    for key in buffers:
        if buffers[key].ndim == 2:
            buffers[key] = np.mean(buffers[key], axis=1)

# === Audio Callback ===
def audio_callback(outdata, frames, time_info, status):
    global sample_position, current_measure, next_measure, measure_index
    global is_stopping, stop_sample_position, stop_complete

    with lock:
        buffer = buffers[current_measure]
        val = slider_value

    out = np.zeros(frames, dtype='float32')
    length = len(buffer)

    for i in range(frames):
        if sample_position >= length:
            sample_position = 0

            # Advance measure_index safely
            measure_index = (measure_index + 1) % len(measure1_list)

            # Choose next measure list
            if current_measure in measure1_list:
                next_measure = measure2_list[measure_index] if val == 1.0 else measure1_list[measure_index]
            else:
                next_measure = measure1_list[measure_index] if val == 0.0 else measure2_list[measure_index]

            current_measure = next_measure
            buffer = buffers[current_measure]
            length = len(buffer)

        if is_stopping:
            if stop_sample_position < fade_out_samples:
                fade_factor = 1 - (stop_sample_position / fade_out_samples)
                out[i] = buffer[sample_position] * fade_factor
                stop_sample_position += 1
            else:
                out[i] = 0
                stop_complete = True
        else:
            out[i] = buffer[sample_position]

        sample_position += 1

    outdata[:] = out.reshape(-1, 1)

# === Start/Stop Audio ===
def start_audio():
    global stream, sample_position, measure_index, stop_complete
    sample_position = 0
    measure_index = 0
    stop_complete = False
    stream = sd.OutputStream(callback=audio_callback, samplerate=sample_rate, channels=1, dtype='float32')
    stream.start()

def stop_audio():
    global stream, is_stopping, stop_sample_position, stop_complete
    if stream:
        is_stopping = True
        stop_sample_position = 0
        stop_complete = False

        while not stop_complete:
            time.sleep(0.01)

        stream.stop()
        stream.close()
        is_stopping = False

# === Slider Callback ===
def update_measure(val):
    global slider_value
    with lock:
        slider_value = float(val)

# === GUI ===
load_audio()
root = tk.Tk()
root.title("Measure Switcher")
root.geometry('500x300')

slider = tk.Scale(root, from_=0, to=1, orient=tk.HORIZONTAL, label="Select Measure", command=update_measure)
slider.pack(padx=20, pady=20)

play_button = tk.Button(root, text="Play", command=start_audio)
play_button.pack(padx=20, pady=10)

stop_button = tk.Button(root, text="Stop", command=stop_audio)
stop_button.pack(padx=20, pady=10)

root.mainloop()
