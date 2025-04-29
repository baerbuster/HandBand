import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
import sounddevice as sd

def main():
    #Load The Wav File
    sample_rate, data = wav.read("ProgrammableLoop.wav")

    #Get Wav Info
    print(sample_rate)
    print(data.shape)
    print(data.dtype)



import os
print("Current working directory:", os.getcwd())
