// synthlib.cpp - C++ synth turned into a library for Python access

#include <iostream>
#include <cmath>
#include <atomic>
#include <portaudio.h>
#include <thread>
#include <mutex>

constexpr double PI = 3.14159265358979323846;
constexpr int SAMPLE_RATE = 44100;
constexpr double AMPLITUDE = 0.5;

// ADSR envelope times in seconds
constexpr double ATTACK = 0.3;
constexpr double DECAY = 0.2;
constexpr double SUSTAIN_LEVEL = 0.5;
constexpr double RELEASE = 0.5;

struct SineData {
    std::mutex mutex;
    double phase = 0.0;
    double frequency = 440.0;
    double phaseIncrement = 2 * PI * frequency / SAMPLE_RATE;
    unsigned long sampleCount = 0;

    unsigned long attackSamples = static_cast<unsigned long>(SAMPLE_RATE * ATTACK);
    unsigned long decaySamples = static_cast<unsigned long>(SAMPLE_RATE * DECAY);
    unsigned long releaseSamples = static_cast<unsigned long>(SAMPLE_RATE * RELEASE);

    std::atomic<bool> noteOn{false};
    unsigned long releaseStartSample = 0;

    void reset() {
        std::lock_guard<std::mutex> lock(mutex);
        phase = 0.0;
        sampleCount = 0;
        noteOn = true;
        releaseStartSample = 0;
        updatePhaseIncrement();
    }

    void updatePhaseIncrement() {
        phaseIncrement = 2 * PI * frequency / SAMPLE_RATE;
    }

    void setFrequency(double freq) {
        std::lock_guard<std::mutex> lock(mutex);
        frequency = freq;
        updatePhaseIncrement();
    }
};

static SineData data;
static PaStream* stream = nullptr;

static int paCallback(const void*, void* outputBuffer,
                      unsigned long framesPerBuffer,
                      const PaStreamCallbackTimeInfo*,
                      PaStreamCallbackFlags,
                      void* userData) {
    float* out = static_cast<float*>(outputBuffer);
    SineData* d = static_cast<SineData*>(userData);

    for (unsigned long i = 0; i < framesPerBuffer; i++) {
        double amplitudeMultiplier = 0.0;
        unsigned long t;
        {
            std::lock_guard<std::mutex> lock(d->mutex);
            t = d->sampleCount;
        }

        bool noteOn = d->noteOn.load();

        if (noteOn) {
            if (t < d->attackSamples) {
                amplitudeMultiplier = static_cast<double>(t) / d->attackSamples;
            } else if (t < d->attackSamples + d->decaySamples) {
                unsigned long decayPos = t - d->attackSamples;
                double decayProgress = static_cast<double>(decayPos) / d->decaySamples;
                amplitudeMultiplier = 1.0 + decayProgress * (SUSTAIN_LEVEL - 1.0);
            } else {
                amplitudeMultiplier = SUSTAIN_LEVEL;
            }
        } else {
            unsigned long releasePos = t - d->releaseStartSample;
            if (releasePos >= d->releaseSamples) {
                amplitudeMultiplier = 0.0;
            } else {
                double releaseProgress = static_cast<double>(releasePos) / d->releaseSamples;
                amplitudeMultiplier = SUSTAIN_LEVEL * (1.0 - releaseProgress);
            }
        }

        double phaseCopy;
        {
            std::lock_guard<std::mutex> lock(d->mutex);
            phaseCopy = d->phase;
        }

        *out++ = static_cast<float>(AMPLITUDE * amplitudeMultiplier * sin(phaseCopy));

        {
            std::lock_guard<std::mutex> lock(d->mutex);
            d->phase += d->phaseIncrement;
            if (d->phase >= 2 * PI) d->phase -= 2 * PI;
            d->sampleCount++;
        }
    }

    if (!d->noteOn && (d->sampleCount - d->releaseStartSample > d->releaseSamples)) {
        return paComplete;
    }

    return paContinue;
}

extern "C" void start_synth() {
    Pa_Initialize();
    Pa_OpenDefaultStream(&stream, 0, 1, paFloat32, SAMPLE_RATE, 256, paCallback, &data);
    data.reset();
    Pa_StartStream(stream);
}

extern "C" void stop_synth() {
    data.noteOn = false;
    {
        std::lock_guard<std::mutex> lock(data.mutex);
        data.releaseStartSample = data.sampleCount;
    }

    while (Pa_IsStreamActive(stream) == 1) {
        Pa_Sleep(50);
    }

    Pa_StopStream(stream);
    Pa_CloseStream(stream);
    Pa_Terminate();
}

extern "C" void set_frequency(double freq) {
    data.setFrequency(freq);
}
