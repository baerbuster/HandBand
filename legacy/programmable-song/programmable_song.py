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

# Define measure and file groups
measure1_list = [f"measure1.{i+1}" for i in range(8)]
measure2_list = [f"measure2.{i+1}" for i in range(8)]
measure3_list = [f"measure3.{i+1}" for i in range(4)]
loop1file_list = [f"ProgrammableLoop1.{i+1}.wav" for i in range(8)]
loop2file_list = [f"ProgrammableLoop2.{i+1}.wav" for i in range(8)]
loop3file_list = [f"ProgrammableLoop3.{i+1}.wav" for i in range(4)]

measure_groups = [measure1_list, measure2_list, measure3_list]
file_groups = [loop1file_list, loop2file_list, loop3file_list]
num_groups = len(measure_groups)

slider_value = 0.0  # Shared var for slider state

# === Load Audio ===
def load_audio():
    global buffers, sample_rate
    for group, files in zip(measure_groups, file_groups):
        for measure, filename in zip(group, files):
            data, sample_rate = sf.read(filename, dtype='float32')
            if data.ndim == 2:
                data = np.mean(data, axis=1)
            buffers[measure] = data

# === Audio Callback ===
def audio_callback(outdata, frames, time_info, status):
    global sample_position, current_measure, next_measure, measure_index
    global is_stopping, stop_sample_position, stop_complete

    with lock:
        val = slider_value

    group_index = int(val * (num_groups - 1))
    current_group = measure_groups[group_index]

    buffer = buffers[current_measure]
    out = np.zeros(frames, dtype='float32')
    length = len(buffer)

    for i in range(frames):
        if sample_position >= length:
            sample_position = 0
            measure_index = (measure_index + 1) % len(current_group)
            next_measure = current_group[measure_index]
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
    global stream, sample_position, measure_index, stop_complete, current_measure
    sample_position = 0
    measure_index = 0
    stop_complete = False
    current_measure = measure_groups[0][0]
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

# Create a frame for the slider and custom labels
slider_frame = tk.Frame(root)
slider_frame.pack(pady=40)

# Slider setup (no number shown)
slider = tk.Scale(slider_frame, from_=0, to=1, resolution=0.5,
                  orient=tk.HORIZONTAL, showvalue=0, length=300, command=update_measure)
slider.grid(row=1, column=0)

# Labels above the slider
label_canvas = tk.Canvas(slider_frame, width=300, height=20, highlightthickness=0)
label_canvas.grid(row=0, column=0)

# Positions for labels
label_canvas.create_text(0, 10, text="Sad", anchor='w')
label_canvas.create_text(150, 10, text="|", anchor='center')
label_canvas.create_text(300, 10, text="Happy", anchor='e')

# Play button
play_button = tk.Button(root, text="Play", command=start_audio)
play_button.pack(padx=20, pady=10)

# Stop button
stop_button = tk.Button(root, text="Stop", command=stop_audio)
stop_button.pack(padx=20, pady=10)

root.mainloop()
