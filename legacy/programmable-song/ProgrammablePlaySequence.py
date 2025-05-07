import soundfile as sf
import sounddevice as sd
import numpy as np

def load_seq(file):
    data, sample_rate = sf.read(file, dtype = 'float32')
    if data.ndim == 2:
        data = np.mean(data, axis=1)  # convert to mono
    return data, sample_rate

def ProgrammablePlaySequence(measure="measure1"):
    if measure == 'measure1':
        data, sample_rate = load_seq('ProgrammableLoop.wav')
        
    elif measure == 'measure2':
        data, sample_rate = load_seq('ProgrammableLoop2.wav')
    else:
        return

    # Loop it
    data_all = np.concatenate([data])
    #data_all = np.tile(data_all, 2)

    # Play
    sd.play(data_all, samplerate=sample_rate)
    ProgrammablePlaySequence()
    sd.wait()

if __name__ == "__main__":
    ProgrammablePlaySequence()