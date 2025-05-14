import soundfile as sf
import sounddevice as sd
import numpy as np
import tkinter as tk
import threading
import time
import librosa
from scipy.signal import firwin2, lfilter

# === Variables ===
buffers = {}
sample_rate = 44100
sample_position = 0
current_measure = None
measure_index = 0
lock = threading.Lock()
stream = None

fade_out_duration = 2  # seconds
durations = {'fade_out': fade_out_duration}
fade_out_samples = int(fade_out_duration * sample_rate)
is_stopping = False
stop_sample_position = 0
stop_complete = False

slider_value = 0.5  # default center

measure1_list = [f"measure1.{i+1}" for i in range(8)]
measure2_list = [f"measure2.{i+1}" for i in range(8)]
measure3_list = [f"measure3.{i+1}" for i in range(4)]
loop1file_list = [f"ProgrammableLoop1.{i+1}.wav" for i in range(8)]
loop2file_list = [f"ProgrammableLoop2.{i+1}.wav" for i in range(8)]
loop3file_list = [f"ProgrammableLoop3.{i+1}.wav" for i in range(4)]

measure_groups = [measure1_list, measure2_list, measure3_list]
file_groups = [loop1file_list, loop2file_list, loop3file_list]
num_groups = len(measure_groups)

# === Load Audio ===
def load_audio():
    global buffers, sample_rate
    for group_idx, (group, files) in enumerate(zip(measure_groups, file_groups)):
        tempo_shift = 1 + (group_idx / (num_groups - 1) - 0.5) * 0.10  # ±5%
        for measure, filename in zip(group, files):
            data, sr = sf.read(filename, dtype='float32')
            if data.ndim == 2:
                data = np.mean(data, axis=1)
            data = librosa.effects.time_stretch(data, rate=tempo_shift)

            nyq = 0.5 * sr

            # === High-end EQ: drop left, boost right ===
            gain_db_high = (group_idx / (num_groups - 1) - 0.5) * 4.0  # -2dB to +2dB
            gain_linear_high = 10**(gain_db_high / 20)
            freqs_high = [0, 2000, 20000, nyq]
            gains_high = [1.0, 1.0, gain_linear_high, gain_linear_high]
            freq_norm_high = [f / nyq for f in freqs_high]
            taps_high = firwin2(513, freq_norm_high, gains_high)
            data = lfilter(taps_high, 1.0, data)

            # === Low-mid EQ: boost left, cut right (gradual slope) ===
            gain_db_mid = (1 - 2 * (group_idx / (num_groups - 1))) * 1.0  # +1dB to -1dB
            gain_linear_mid = 10**(gain_db_mid / 20)
            freqs_mid = [0, 100, 200, 400, 800, nyq]
            gains_mid = [1.0, gain_linear_mid, gain_linear_mid, 1.0, 1.0, 1.0]
            freq_norm_mid = [f / nyq for f in freqs_mid]
            taps_mid = firwin2(513, freq_norm_mid, gains_mid)
            data = lfilter(taps_mid, 1.0, data)

            buffers[measure] = data
            sample_rate = sr

# === Audio Callback ===
def audio_callback(outdata, frames, time_info, status):
    global sample_position, current_measure, measure_index
    global is_stopping, stop_sample_position, stop_complete

    with lock:
        val = slider_value
    gain_db = (val - 0.5) * 2.0  # ±1 dB
    amp = 10 ** (gain_db / 20.0)

    group_index = int(val * (num_groups - 1))
    current_group = measure_groups[group_index]

    if current_measure is None or current_measure not in buffers:
        return

    buf = buffers[current_measure]
    length = len(buf)
    out = np.zeros(frames, dtype='float32')

    end_pos = sample_position + frames
    if end_pos <= length:
        chunk = buf[sample_position:end_pos]
    else:
        first = buf[sample_position:]
        remaining = end_pos - length
        measure_index = (measure_index + 1) % len(current_group)
        current_measure = current_group[measure_index]
        buf2 = buffers[current_measure]
        chunk = np.concatenate((first, buf2[:remaining]))
    sample_position = end_pos % length

    if is_stopping:
        start = stop_sample_position
        stop = min(stop_sample_position + frames, fade_out_samples)
        env = np.linspace(1, 0, fade_out_samples)[start:stop]
        if len(env) < frames:
            env = np.pad(env, (0, frames - len(env)), 'constant', constant_values=(0,))
        out[:] = chunk * env * amp
        stop_sample_position = stop
        if stop_sample_position >= fade_out_samples:
            stop_complete = True
    else:
        out[:] = chunk * amp

    outdata[:] = out.reshape(-1, 1)

# === Start/Stop Audio ===
def start_audio():
    global stream, sample_position, measure_index, stop_complete, current_measure
    with lock:
        val = slider_value
    group_index = int(val * (num_groups - 1))
    current_measure = measure_groups[group_index][0]
    sample_position = 0
    measure_index = 0
    stop_complete = False
    stream = sd.OutputStream(callback=audio_callback,
                             samplerate=sample_rate,
                             channels=1,
                             dtype='float32')
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
root.title("Measure Switcher with EQ & Tempo Shift")
root.geometry('500x300')

slider_frame = tk.Frame(root)
slider_frame.pack(pady=40)
slider = tk.Scale(slider_frame,
                  from_=0, to=1,
                  resolution=0.5,
                  orient=tk.HORIZONTAL,
                  showvalue=0,
                  length=300,
                  command=update_measure)
slider.set(slider_value)
slider.grid(row=1, column=0)

label_canvas = tk.Canvas(slider_frame, width=300, height=20, highlightthickness=0)
label_canvas.grid(row=0, column=0)
label_canvas.create_text(0, 10, text="Sad", anchor='w')
label_canvas.create_text(150, 10, text="|", anchor='center')
label_canvas.create_text(300, 10, text="Happy", anchor='e')

play_button = tk.Button(root, text="Play", command=start_audio)
play_button.pack(padx=20, pady=10)
stop_button = tk.Button(root, text="Stop", command=stop_audio)
stop_button.pack(padx=20, pady=10)

root.mainloop()
