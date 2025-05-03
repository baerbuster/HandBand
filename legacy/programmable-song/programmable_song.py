
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
import sounddevice as sd

def main():
    #Load The Wav File
    sample_rate, data = wav.read("ProgrammableLoop.wav")

    if len(data.shape) == 2:
        data = np.mean(data, axis=1, dtype=data.dtype)


    #Get Wav Info
    print(sample_rate)
    print(data.shape)
    print(data.dtype)

    #Start/End Times
    start_time = 0
    end_time = len(data)

    #Star/End Times in samples
    start_sample = int(start_time*sample_rate)
    end_sample = int(end_time*sample_rate)

    #Trim The Audio To Start and End Time
    data = data[start_sample:end_sample]

    #Loop that bitch
    data= np.tile(data, 4)

    #Play The Sound
    sd.play(data, samplerate=sample_rate)
    sd.wait()

if __name__ == "__main__":
    main()

