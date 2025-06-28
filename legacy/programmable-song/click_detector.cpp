#include <iostream>
#include <cmath>
#include <atomic>
#include <portaudio.h>
#include <thread>
#include <mutex>
#include <chrono>
#include <fstream>
#include <vector>
#include <iomanip>

constexpr double PI = 3.14159265358979323846;
constexpr int SAMPLE_RATE = 44100;

// Click detection settings
constexpr double CLICK_THRESHOLD = 0.05;  // Amplitude jump that constitutes a click
constexpr int PRE_CLICK_SAMPLES = 50;     // Samples to record before a click
constexpr int POST_CLICK_SAMPLES = 50;    // Samples to record after a click
constexpr int MAX_CLICKS_TO_LOG = 20;     // Maximum number of clicks to log in detail

// Log file setup
std::ofstream logFile("click_detector.log", std::ios::out | std::ios::trunc);
std::ofstream csvFile("sample_data.csv", std::ios::out | std::ios::trunc);

// Click detection state
struct ClickEvent {
    unsigned long sampleIndex;
    double amplitudeJump;
    double phase;
    double frequency;
    bool noteOnState;
    unsigned long samplesSinceNoteOn;
    unsigned long samplesSinceNoteOff;
    double envelopeValue;
    std::vector<std::pair<double, double>> surroundingSamples; // (time, amplitude) pairs
};

std::vector<ClickEvent> detectedClicks;
bool recordingClick = false;
int clickRecordCountdown = 0;
std::vector<std::pair<double, double>> clickBuffer;

struct SineData {
    std::mutex mutex;
    double phase = 0.0;
    double frequency = 440.0;
    double phaseIncrement = 2 * PI * frequency / SAMPLE_RATE;
    unsigned long sampleCount = 0;

    unsigned long attackSamples = static_cast<unsigned long>(SAMPLE_RATE * 0.3);
    unsigned long decaySamples = static_cast<unsigned long>(SAMPLE_RATE * 0.2);
    unsigned long releaseSamples = static_cast<unsigned long>(SAMPLE_RATE * 0.5);

    double sustainLevel = 0.5;
    double amplitude = 0.5;

    std::atomic<bool> noteOn{false};
    unsigned long releaseStartSample = 0;
    unsigned long noteOnStartSample = 0;
    
    // Previous sample values for click detection
    double prevSineValue = 0.0;
    double prevAmplitude = 0.0;
    double prevEnvelopeValue = 0.0;
    
    // Detailed state tracking
    std::atomic<int> envelopeState{0}; // 0=off, 1=attack, 2=decay, 3=sustain, 4=release
    std::atomic<bool> justTriggeredNoteOn{false};
    std::atomic<bool> justTriggeredNoteOff{false};
    
    // BPM-related info for diagnostics
    double currentBPM = 120.0;
    double noteDurationSec = 0.125; // 16th note at 120 BPM

    void reset() {
        std::lock_guard<std::mutex> lock(mutex);
        phase = 0.0;
        sampleCount = 0;
        noteOn = true;
        justTriggeredNoteOn = true;
        justTriggeredNoteOff = false;
        envelopeState = 1; // Attack
        noteOnStartSample = sampleCount;
        releaseStartSample = 0;
        updatePhaseIncrement();
        
        logFile << "NOTE_ON: Reset phase to 0, sampleCount to 0, entering ATTACK phase" << std::endl;
    }

    void updatePhaseIncrement() {
        phaseIncrement = 2 * PI * frequency / SAMPLE_RATE;
    }

    void setFrequency(double freq) {
        std::lock_guard<std::mutex> lock(mutex);
        frequency = freq;
        updatePhaseIncrement();
        logFile << "Frequency set to " << freq << " Hz" << std::endl;
    }
    
    void setBPM(double bpm) {
        std::lock_guard<std::mutex> lock(mutex);
        currentBPM = bpm;
        noteDurationSec = 60.0 / (bpm * 4.0); // Duration of a 16th note
        logFile << "BPM set to " << bpm << ", 16th note duration = " << noteDurationSec << " sec" << std::endl;
    }
};

static SineData data;
static PaStream* stream = nullptr;

// Function to log a detected click
void logClickEvent(const ClickEvent& click) {
    logFile << "===== CLICK DETECTED at sample " << click.sampleIndex << " =====" << std::endl;
    logFile << "Amplitude jump: " << click.amplitudeJump << std::endl;
    logFile << "Phase at click: " << click.phase << " (" << (click.phase * 180.0 / PI) << " degrees)" << std::endl;
    logFile << "Frequency: " << click.frequency << " Hz" << std::endl;
    logFile << "Note state: " << (click.noteOnState ? "ON" : "OFF") << std::endl;
    
    if (click.noteOnState) {
        logFile << "Time since note_on: " << static_cast<double>(click.samplesSinceNoteOn) / SAMPLE_RATE 
                << " sec (" << click.samplesSinceNoteOn << " samples)" << std::endl;
        
        double attackTime = static_cast<double>(data.attackSamples) / SAMPLE_RATE;
        double decayTime = static_cast<double>(data.decaySamples) / SAMPLE_RATE;
        
        logFile << "Envelope phase: ";
        if (click.samplesSinceNoteOn < data.attackSamples) {
            double attackProgress = static_cast<double>(click.samplesSinceNoteOn) / data.attackSamples * 100.0;
            logFile << "ATTACK at " << attackProgress << "% (" 
                    << static_cast<double>(click.samplesSinceNoteOn) / SAMPLE_RATE << " sec of " 
                    << attackTime << " sec attack time)" << std::endl;
        } else if (click.samplesSinceNoteOn < data.attackSamples + data.decaySamples) {
            unsigned long decayPos = click.samplesSinceNoteOn - data.attackSamples;
            double decayProgress = static_cast<double>(decayPos) / data.decaySamples * 100.0;
            logFile << "DECAY at " << decayProgress << "% (" 
                    << static_cast<double>(decayPos) / SAMPLE_RATE << " sec of " 
                    << decayTime << " sec decay time)" << std::endl;
        } else {
            logFile << "SUSTAIN" << std::endl;
        }
    } else {
        logFile << "Time since note_off: " << static_cast<double>(click.samplesSinceNoteOff) / SAMPLE_RATE 
                << " sec (" << click.samplesSinceNoteOff << " samples)" << std::endl;
        
        double releaseTime = static_cast<double>(data.releaseSamples) / SAMPLE_RATE;
        double releaseProgress = static_cast<double>(click.samplesSinceNoteOff) / data.releaseSamples * 100.0;
        
        logFile << "Envelope phase: RELEASE at " << releaseProgress << "% (" 
                << static_cast<double>(click.samplesSinceNoteOff) / SAMPLE_RATE << " sec of " 
                << releaseTime << " sec release time)" << std::endl;
    }
    
    logFile << "Envelope value at click: " << click.envelopeValue << std::endl;
    logFile << "BPM at click: " << data.currentBPM << std::endl;
    logFile << "16th note duration: " << data.noteDurationSec << " sec" << std::endl;
    
    // Log surrounding samples to show the discontinuity
    logFile << "\nSample values around click (time in sec, amplitude):" << std::endl;
    for (const auto& sample : click.surroundingSamples) {
        logFile << sample.first << ", " << sample.second << std::endl;
    }
    logFile << "=========================================" << std::endl << std::endl;
}

static int paCallback(const void*, void* outputBuffer,
                      unsigned long framesPerBuffer,
                      const PaStreamCallbackTimeInfo*,
                      PaStreamCallbackFlags,
                      void* userData) {
    float* out = static_cast<float*>(outputBuffer);
    SineData* d = static_cast<SineData*>(userData);
    
    // Write CSV header if this is the first buffer
    static bool firstBuffer = true;
    if (firstBuffer) {
        csvFile << "SampleIndex,Time,NoteState,EnvelopePhase,EnvelopeValue,SineValue,OutputAmplitude" << std::endl;
        firstBuffer = false;
    }

    for (unsigned long i = 0; i < framesPerBuffer; i++) {
        double amplitudeMultiplier = 0.0;
        unsigned long t;
        {
            std::lock_guard<std::mutex> lock(d->mutex);
            t = d->sampleCount;
        }

        bool noteOn = d->noteOn.load();
        bool justTriggeredNoteOn = d->justTriggeredNoteOn.load();
        bool justTriggeredNoteOff = d->justTriggeredNoteOff.load();
        
        // Reset trigger flags after one sample
        if (justTriggeredNoteOn) {
            d->justTriggeredNoteOn = false;
        }
        if (justTriggeredNoteOff) {
            d->justTriggeredNoteOff = false;
        }

        // Calculate time since note on/off for envelope tracking
        unsigned long samplesSinceNoteOn = t - d->noteOnStartSample;
        unsigned long samplesSinceNoteOff = t - d->releaseStartSample;

        // Track envelope state for diagnostics
        int envelopeState = 0;

        // Calculate the current envelope level
        if (noteOn) {
            if (t < d->noteOnStartSample + d->attackSamples) {
                amplitudeMultiplier = static_cast<double>(samplesSinceNoteOn) / d->attackSamples;
                envelopeState = 1; // Attack
            } else if (t < d->noteOnStartSample + d->attackSamples + d->decaySamples) {
                unsigned long decayPos = samplesSinceNoteOn - d->attackSamples;
                double decayProgress = static_cast<double>(decayPos) / d->decaySamples;
                amplitudeMultiplier = 1.0 + decayProgress * (d->sustainLevel - 1.0);
                envelopeState = 2; // Decay
            } else {
                amplitudeMultiplier = d->sustainLevel;
                envelopeState = 3; // Sustain
            }
        } else {
            if (samplesSinceNoteOff >= d->releaseSamples) {
                amplitudeMultiplier = 0.0;
                envelopeState = 0; // Off
            } else {
                double releaseProgress = static_cast<double>(samplesSinceNoteOff) / d->releaseSamples;
                amplitudeMultiplier = d->sustainLevel * (1.0 - releaseProgress);
                envelopeState = 4; // Release
            }
        }

        d->envelopeState.store(envelopeState);

        double phaseCopy;
        {
            std::lock_guard<std::mutex> lock(d->mutex);
            phaseCopy = d->phase;
        }

        // Calculate the sine value
        double sineValue = sin(phaseCopy);
        
        // Calculate final output amplitude
        double outputAmplitude = d->amplitude * amplitudeMultiplier * sineValue;
        
        // Check for amplitude jumps (potential clicks)
        double amplitudeDelta = std::abs(outputAmplitude - d->prevAmplitude);
        
        // Record sample data to CSV (not every sample to avoid huge files)
        if (t % 10 == 0 || amplitudeDelta > CLICK_THRESHOLD || recordingClick) {
            double timeInSec = static_cast<double>(t) / SAMPLE_RATE;
            std::string envelopePhase;
            switch(envelopeState) {
                case 0: envelopePhase = "OFF"; break;
                case 1: envelopePhase = "ATTACK"; break;
                case 2: envelopePhase = "DECAY"; break;
                case 3: envelopePhase = "SUSTAIN"; break;
                case 4: envelopePhase = "RELEASE"; break;
            }
            
            csvFile << t << "," 
                    << timeInSec << "," 
                    << (noteOn ? "ON" : "OFF") << "," 
                    << envelopePhase << "," 
                    << amplitudeMultiplier << "," 
                    << sineValue << "," 
                    << outputAmplitude << std::endl;
        }
        
        // Click detection logic
        if (amplitudeDelta > CLICK_THRESHOLD && !recordingClick && detectedClicks.size() < MAX_CLICKS_TO_LOG) {
            // Start recording a click event
            recordingClick = true;
            clickRecordCountdown = PRE_CLICK_SAMPLES + POST_CLICK_SAMPLES;
            clickBuffer.clear();
            
            // Add previous samples if available (pre-click buffer)
            for (int j = 0; j < PRE_CLICK_SAMPLES; j++) {
                double timeInSec = static_cast<double>(t - PRE_CLICK_SAMPLES + j) / SAMPLE_RATE;
                clickBuffer.push_back(std::make_pair(timeInSec, 0.0)); // Will be filled with actual values if available
            }
            
            // Create click event
            ClickEvent click;
            click.sampleIndex = t;
            click.amplitudeJump = amplitudeDelta;
            click.phase = phaseCopy;
            click.frequency = d->frequency;
            click.noteOnState = noteOn;
            click.samplesSinceNoteOn = samplesSinceNoteOn;
            click.samplesSinceNoteOff = samplesSinceNoteOff;
            click.envelopeValue = amplitudeMultiplier;
            
            detectedClicks.push_back(click);
            
            logFile << "Click detected at sample " << t << ", amplitude jump: " << amplitudeDelta 
                    << ", envelope state: " << envelopeState << std::endl;
        }
        
        // If we're recording a click, add this sample to the buffer
        if (recordingClick) {
            double timeInSec = static_cast<double>(t) / SAMPLE_RATE;
            clickBuffer.push_back(std::make_pair(timeInSec, outputAmplitude));
            clickRecordCountdown--;
            
            if (clickRecordCountdown <= 0) {
                recordingClick = false;
                
                // Store the surrounding samples in the last detected click
                if (!detectedClicks.empty()) {
                    detectedClicks.back().surroundingSamples = clickBuffer;
                    logClickEvent(detectedClicks.back());
                }
            }
        }
        
        // Store values for next iteration
        d->prevSineValue = sineValue;
        d->prevAmplitude = outputAmplitude;
        d->prevEnvelopeValue = amplitudeMultiplier;

        // Output the sample
        *out++ = static_cast<float>(outputAmplitude);

        {
            std::lock_guard<std::mutex> lock(d->mutex);
            d->phase += d->phaseIncrement;
            if (d->phase >= 2 * PI) d->phase -= 2 * PI;
            d->sampleCount++;
        }
    }

    return paContinue;
}

extern "C" void note_off();  // forward declaration

extern "C" void start_synth() {
    // Initialize log files
    logFile << "=== CLICK DETECTOR STARTED ===" << std::endl;
    logFile << "Sample Rate: " << SAMPLE_RATE << " Hz" << std::endl;
    logFile << "Click detection threshold: " << CLICK_THRESHOLD << std::endl;
    logFile << "Attack time: " << static_cast<double>(data.attackSamples) / SAMPLE_RATE << " sec" << std::endl;
    logFile << "Decay time: " << static_cast<double>(data.decaySamples) / SAMPLE_RATE << " sec" << std::endl;
    logFile << "Release time: " << static_cast<double>(data.releaseSamples) / SAMPLE_RATE << " sec" << std::endl;
    logFile << "Sustain level: " << data.sustainLevel << std::endl;
    
    Pa_Initialize();
    Pa_OpenDefaultStream(&stream, 0, 1, paFloat32, SAMPLE_RATE, 256, paCallback, &data);
    Pa_StartStream(stream);
}

extern "C" void stop_synth() {
    note_off();

    // Wait up to 2 seconds max for release phase to finish
    constexpr unsigned int maxWaitMs = 2000;
    constexpr unsigned int sleepStepMs = 50;
    unsigned int waitedMs = 0;

    while ((data.noteOn.load() || (data.sampleCount - data.releaseStartSample <= data.releaseSamples))
           && waitedMs < maxWaitMs) {
        std::this_thread::sleep_for(std::chrono::milliseconds(sleepStepMs));
        waitedMs += sleepStepMs;
    }

    if (stream) {
        Pa_StopStream(stream);
        Pa_CloseStream(stream);
        Pa_Terminate();
        stream = nullptr;
    }
    
    // Log summary of detected clicks
    logFile << "\n=== CLICK DETECTOR SUMMARY ===" << std::endl;
    logFile << "Total clicks detected: " << detectedClicks.size() << std::endl;
    
    // Close log files
    logFile << "=== CLICK DETECTOR STOPPED ===" << std::endl;
    logFile.close();
    csvFile.close();
}

extern "C" void note_on() {
    logFile << "NOTE_ON called at sample " << data.sampleCount << std::endl;
    
    // Store the sample count when note_on was called
    data.noteOnStartSample = data.sampleCount;
    data.justTriggeredNoteOn = true;
    
    data.reset(); // resets phase/sampleCount and sets noteOn = true
}

extern "C" void note_off() {
    if (data.noteOn.load()) {
        logFile << "NOTE_OFF called at sample " << data.sampleCount << std::endl;
        
        unsigned long samplesSinceNoteOn = data.sampleCount - data.noteOnStartSample;
        double timeSinceNoteOn = static_cast<double>(samplesSinceNoteOn) / SAMPLE_RATE;
        
        logFile << "Note duration: " << timeSinceNoteOn << " sec (" << samplesSinceNoteOn << " samples)" << std::endl;
        
        // Log envelope state at note_off
        if (samplesSinceNoteOn < data.attackSamples) {
            double attackProgress = static_cast<double>(samplesSinceNoteOn) / data.attackSamples * 100.0;
            logFile << "NOTE_OFF during ATTACK phase: " << attackProgress << "% complete" << std::endl;
        } else if (samplesSinceNoteOn < data.attackSamples + data.decaySamples) {
            unsigned long decayPos = samplesSinceNoteOn - data.attackSamples;
            double decayProgress = static_cast<double>(decayPos) / data.decaySamples * 100.0;
            logFile << "NOTE_OFF during DECAY phase: " << decayProgress << "% complete" << std::endl;
        } else {
            logFile << "NOTE_OFF during SUSTAIN phase" << std::endl;
        }
        
        data.noteOn = false;
        data.justTriggeredNoteOff = true;
        
        {
            std::lock_guard<std::mutex> lock(data.mutex);
            data.releaseStartSample = data.sampleCount;
        }
    }
}

extern "C" void set_frequency(double freq) {
    data.setFrequency(freq);
}

extern "C" void set_attack(double attackSeconds) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.attackSamples = static_cast<unsigned long>(SAMPLE_RATE * attackSeconds);
    logFile << "Attack set to " << attackSeconds << " sec" << std::endl;
}

extern "C" void set_decay(double decaySeconds) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.decaySamples = static_cast<unsigned long>(SAMPLE_RATE * decaySeconds);
    logFile << "Decay set to " << decaySeconds << " sec" << std::endl;
}

extern "C" void set_sustain_level(double level) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.sustainLevel = level;
    logFile << "Sustain level set to " << level << std::endl;
}

extern "C" void set_release(double releaseSeconds) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.releaseSamples = static_cast<unsigned long>(SAMPLE_RATE * releaseSeconds);
    logFile << "Release set to " << releaseSeconds << " sec" << std::endl;
}

extern "C" void set_amplitude(double amplitude) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.amplitude = amplitude;
    logFile << "Amplitude set to " << amplitude << std::endl;
}

extern "C" void set_bpm(double bpm) {
    data.setBPM(bpm);
}
