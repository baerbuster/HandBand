import soundfile as sf
import sounddevice as sd
import numpy as np
import threading
import time

current_measure = "measure1"
next_measure = "measure1"
stop_pending = False
measure_ended = False
lock = threading.Lock()
position = 0
buffers = {}
sample_rate = 44100

def load_seq(file):
    data, sr = sf.read(file, dtype='float32')
    if data.ndim == 2:
        data = np.mean(data, axis=1)
    return data, sr

def audio_callback(outdata, frames, time_info, status):
    global position, current_measure, next_measure, stop_pending, measure_ended
    with lock:
        buffer = buffers[current_measure]
    length = len(buffer)
    out = np.empty(frames, dtype='float32')

    for i in range(frames):
        out[i] = buffer[position]
        position += 1
        if position >= length:
            position = 0
            with lock:
                if stop_pending:
                    measure_ended = True
                current_measure = next_measure
                buffer = buffers[current_measure]
                length = len(buffer)

    outdata[:] = out.reshape(-1, 1)

def user_input():
    global next_measure, stop_pending
    while True:
        cmd = input("Enter measure1 / measure2 / stop: ").strip()
        if cmd in buffers:
            with lock:
                next_measure = cmd
        elif cmd == 'stop':
            with lock:
                stop_pending = True
            break

if __name__ == "__main__":
    buffers['measure1'], sample_rate = load_seq('ProgrammableLoop.wav')
    buffers['measure2'], _ = load_seq('ProgrammableLoop2.wav')

    stream = sd.OutputStream(callback=audio_callback, samplerate=sample_rate, channels=1, dtype='float32')
    stream.start()
    user_thread = threading.Thread(target=user_input)
    user_thread.start()

    while True:
        with lock:
            if measure_ended:
                break
        time.sleep(0.05)

    stream.stop()
    stream.close()
