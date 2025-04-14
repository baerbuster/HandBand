import wave
import array
import math

# Parameters for the "four on the floor" bass drum sound
rate = 44100  # Samples per second
duration = 0.5  # Duration of each drum hit in seconds
frequency = 60  # Frequency of bass drum sound in Hz
amplitude = 16000  # Amplitude of the sound (volume)

# Function to generate a sine wave tone
def generate_sine_wave(frequency, duration, rate, amplitude):
    num_samples = int(duration * rate)
    samples = array.array("h", [int(amplitude * math.sin(2 * math.pi * frequency * t / rate)) for t in range(num_samples)])
    return samples

# Create the "four on the floor" beat
def create_four_on_the_floor(rate, duration, frequency, amplitude, num_beats):
    sound = array.array("h")
    for i in range(num_beats):
        # Append the bass drum sound at regular intervals
        sound.extend(generate_sine_wave(frequency, duration, rate, amplitude))
        # Add a silence between the beats
        sound.extend([0] * int(rate * 0.2))  # 0.2 seconds of silence
    return sound

# Create a 4-on-the-floor rhythm for 4 beats (2 seconds total)
sound_data = create_four_on_the_floor(rate, duration, frequency, amplitude, 4)

# Save the sound to a .wav file
with wave.open("four_on_the_floor.wav", "w") as file:
    file.setnchannels(1)  # Mono sound
    file.setsampwidth(2)  # 2 bytes per sample
    file.setframerate(rate)
    file.writeframes(sound_data.tobytes())

print("four_on_the_floor.wav created!")

