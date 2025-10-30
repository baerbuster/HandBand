//------------------------------------------------------------------------------//
//                  IMPORT HEADERS                                             //
//----------------------------------------------------------------------------//

// Standard C++ headers
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <queue>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <unordered_map>
#include <memory>

// Third-party headers
#include <portaudio.h>
#include <sndfile.h>

//------------------------------------------------------------------------------//
//                  CORE DECLARATIONS AND DATA STRUCTURES                      //
//----------------------------------------------------------------------------//

// Waveform IDs (keep these numeric values stable with Python side)
enum WaveType {
    WAVE_SINE     = 0,
    WAVE_SQUARE   = 1,
    WAVE_TRIANGLE = 2,
    WAVE_SAW      = 3,
    WAVE_SAMPLE   = 4
};

// Constants
constexpr double PI = 3.14159265358979323846;
// Filter range constants (needed by filter/comb calculations in other TU's)
constexpr double MIN_CUTOFF_HZ = 20.0;      // Lowest possible filter cutoff in Hz
constexpr double MAX_CUTOFF_HZ = 20000.0;   // Highest possible filter cutoff in Hz
constexpr double MIN_RESO_Q    = 0.1;       // Lowest resonance (Q) value
constexpr double MAX_RESO_Q    = 40.0;      // Highest resonance (Q) value
constexpr int MAX_OSC = 8;

// Enums
enum EnvelopeState {
    ATTACK, DECAY, SUSTAIN, HOLD_BEFORE_RELEASE, RELEASE, IDLE
};

const char* envelopeStateToStr(EnvelopeState state);

// -------------------------------------------------------------------------- //
//  Inline helper converting envelope enum → string (for debug / logging)    //
// -------------------------------------------------------------------------- //
inline const char* envelopeStateToStr(EnvelopeState state) {
    switch (state) {
        case ATTACK:              return "ATTACK";
        case DECAY:               return "DECAY";
        case SUSTAIN:             return "SUSTAIN";
        case HOLD_BEFORE_RELEASE: return "HOLD_BEFORE_RELEASE";
        case RELEASE:             return "RELEASE";
        case IDLE:                return "IDLE";
        default:                  return "UNKNOWN";
    }
}

// Forward declarations
class Synthesizer;
class SynthManager;

// Synthesizer class - replaces SineData struct
class Synthesizer {
public:
    Synthesizer(int id);
    ~Synthesizer();
    
    // Unique identifier for this synthesizer instance
    int synthId;

    // ====================================================================== //
    // 1.  CORE STATE AND SYNCHRONISATION DECLARATION                         //
    // ====================================================================== //

    std::mutex mutex;
    // Note timing tracking
    bool isFirstSampleOfNote = false;
    bool hasFirstSampleBeenSent = false;
    double phase = 0.0;
    double frequency = 440.0;
    double phaseIncrement = 2 * PI * frequency / 44100.0;
    double sampleBaseFreq = 440;
    double basePhaseIncrement = 2 * PI * sampleBaseFreq / 44100.0;
    double timeScalingFactor = 1.0;
    unsigned long sampleCount = 0;
    // Add this in the Synthesizer class declaration
    double noteVolumeNormalizationFactor = 1.0;
    double targetNoteVolumeNormalizationFactor = 1.0;
    double prevNoteVolumeNormalizationFactor = 1.0;

    // ====================================================================== //
    // 2.  ADSR ENVELOPE PARAMETERS & STATE                                   //
    // ====================================================================== //

    double attackTime = 0.001; // Attack Time in ms
    unsigned long attackSamples = static_cast<unsigned long>(44100.0/1000 * attackTime);
    double decayTime = 3158; // Decay Time in ms
    unsigned long decaySamples = static_cast<unsigned long>(44100.0/1000 * decayTime);
    double releaseTime = 330; // Release Time in ms
    unsigned long releaseSamples = static_cast<unsigned long>(44100.0/1000 * releaseTime);

    // Target ADSR Parameter Declarations
    double targetAttackTime = 0.001;
    double targetDecayTime = 3158;
    double targetReleaseTime = 330;
    double targetSustainLevel = -50.0;

    // Current smoothed ADSR Parameter Declarations
    double currentAttackTime = 0.001;
    double currentDecayTime = 3158;
    double currentReleaseTime = 330;
    double currentSustainLevel = -50.0;

    double amplitude = 0.5;
    double sustainLevel = -50.0; // in dB
    double sustainCalc = std::pow(10.0, currentSustainLevel / 20.0);

    std::atomic<bool> noteOn{false};
    unsigned long releaseStartSample = 0;
    unsigned long releaseHoldSamples = 0;
    double currentAmplitude = 0.0;
    double releaseStartLevel = 0.0;
    unsigned long releaseHoldCounter = 0;
    EnvelopeState envelopeState = IDLE;

    EnvelopeState prevEnvelopeState = IDLE;
    double prevAmplitude = 0.0;
    unsigned long samplesSinceStateChange = 256; // fade_samples

    // ====================================================================== //
    // 3.  OSCILLATOR SETTINGS & MIXING DECLARATIONS                          //
    // ====================================================================== //

    // Waveform selection (per-oscillator)
    enum WaveformType { WAVE_SINE = 0, WAVE_SQUARE = 1, WAVE_TRIANGLE = 2, WAVE_SAW = 3, WAVE_SAMPLE = 4 };
    int osc1Waveform = WAVE_SINE;    // default: sine
    int osc2Waveform = WAVE_SAMPLE;  // default: sample (preserves current behaviour)

    int    oscCount = 0;                         // 0 => use legacy 2-osc path
    int    oscWaveform[MAX_OSC] = {0};           // 0..4
    double targetOscGain[MAX_OSC] = {0.0};
    double currentOscGain[MAX_OSC] = {0.0};

    double prevOutputSample = 0.0;
    double prevRawSine = 0.0;

    double sineGain = 1.0;
    double sampleGain = 1.0;

    double targetSineGain = 1.0;
    double targetSampleGain = 1.0;

    double currentSineGain = 1.0;
    double currentSampleGain = 1.0;

    double gainSmoothingTimeSeconds = 0.5;
    unsigned long gainSmoothingSamples = static_cast<unsigned long>(44100.0 * gainSmoothingTimeSeconds);

    double fmDepth = 0.0; // in radians (modulation amplitude)

    // ====================================================================== //
    // 4.  FILTER 1 PARAMETER DECLARATIONS                                    //
    // ====================================================================== //

    // ---------------------------------- MASTER VOLUME --------------------- //

    double masterVolume = 0.1;

    // ------------------------------- FILTER 1------------------------------ //

    double targetFilterCutoff = 20000.0;  // Hz
    double targetFilterResonance = 0.7071;   // Q
    double targetFilterDrive = 0.0;      // %
    double targetFilterKeyTrack = 0.0;      // %
    double targetFilterEnvMod = 0.0;      // %

    double currentFilterCutoff = 20000.0;
    double currentFilterResonance = 0.7071;
    double currentFilterDrive = 0.0;
    double currentFilterKeyTrack = 0.0;
    double currentFilterEnvMod = 0.0;

    // bi-quad coefficients (a0 assumed 1) //
    double b0 = 1.0, b1 = 0.0, b2 = 0.0, a1 = 0.0, a2 = 0.0;
    // filter memory (DF-II T) //
    double z1 = 0.0, z2 = 0.0;

    // Moog ladder filter variables (alongside biquad)
    double stage1 = 0.0, stage2 = 0.0, stage3 = 0.0, stage4 = 0.0;
    double ladder_feedback = 0.0;
    double ladder_cutoff = 0.0;

    // TPT state variables (z values for each stage)
    double z1_tpt = 0.0, z2_tpt = 0.0, z3_tpt = 0.0, z4_tpt = 0.0;


    // ====================================================================== //
    // 5.  COMB FILTER PARAMETER DECLARATIONS                                 //
    // ====================================================================== //

    // ------------------------------- COMB FILTER -------------------------- //

    double targetCombCutoff = 20000.0;  // Hz (controls delay time)
    double targetCombResonance = 0.7071;   // Controls feedback
    double targetCombDrive = 0.0;      // % (pre-comb gain)
    double targetCombKeyTrack = 0.0;      // % (delay time adjustment)
    double targetCombEnvMod = 0.0;      // %

    double currentCombCutoff = 20000.0;
    double currentCombResonance = 0.7071;
    double currentCombDrive = 0.0;
    double currentCombKeyTrack = 0.0;
    double currentCombEnvMod = 0.0;

    // comb filter state //
    int MAX_DELAY_SAMPLES;
    std::vector<double> combDelayLine;
    int combWritePos = 0;
    int combDelayInSamples = 100; // Will be calculated based on cutoff
    double combFeedback = 0.5;    // Will be calculated based on resonance

    // ====================================================================== //
    // 6.  FILTER ENVELOPE PARAMETER DECLARATIONS                             //
    // ====================================================================== //

    // ---------------------------- FILTER ENVELOPE ------------------------- //

    double targetFilterEnvAttack = 0.001;   // seconds
    double targetFilterEnvDecay = 0.50;    // seconds
    double targetFilterEnvSustain = -20.0;   // dB
    double targetFilterEnvRelease = 0.50;    // seconds

    double currentFilterEnvAttack = 0.001;
    double currentFilterEnvDecay = 0.50;
    double currentFilterEnvSustain = -20.0;
    double currentFilterEnvRelease = 0.50;

    // Envelope runtime bookkeeping //
    EnvelopeState filterEnvState = IDLE;
    unsigned long filterEnvSampleCount = 0;
    unsigned long filterEnvAttackSamples = static_cast<unsigned long>(44100.0 * 0.001);
    unsigned long filterEnvDecaySamples = static_cast<unsigned long>(44100.0 * 0.50);
    unsigned long filterEnvReleaseSamples = static_cast<unsigned long>(44100.0 * 0.50);
    double filterEnvSustainCalc = std::pow(10.0, currentFilterEnvSustain / 20.0);
    unsigned long filterEnvReleaseStartSample = 0;
    double filterEnvReleaseStartLvl = 0.0;
    double currentFilterEnvLevel = 0.0;

    // Add these processing method declarations
    double processFilter(double inSample);
    double processCombFilter(double inSample);
    double processTubeDriver(double inSample);
    double processBitcrusher(double inSample);
    double calculateEffectiveCutoff();
    double calculateEffectiveResonance();
    double calculateCombEffectiveCutoff();
    double calculateCombEffectiveResonance();
    void calculateBiquadCoefficients(double cutoffHz, double resonanceQ);
    void calculateLadderCoefficients(double cutoffHz, double resonanceQ);
    void calculateCombDelayAndFeedback(double cutoffHz, double resonanceQ);

    // ====================================================================== //
    // 7.  GLOBAL CONTROLS DECLARATIONS                                       //
    // ====================================================================== //

    double targetGlobalCutoff = 632.456;   // start at log-mid ≈ sqrt(20*20000)
    double targetGlobalResonance = 3.16228;   // log-mid of 0.25 and 40

    double currentGlobalCutoff = 632.456;
    double currentGlobalResonance = 3.16228;

    // ====================================================================== //
    // 8.  LFO PARAMETER DECLARATIONS                                         //
    // ====================================================================== //

    double targetLfoRate = 1.0;      // Hz
    double targetLfoDepth = 0.0;      // % (0-100)
    double targetLfoLevel = 100.0;    // % (0-100 overall modulation level)

    double currentLfoRate = 1.0;
    double currentLfoDepth = 0.0;
    double currentLfoLevel = 100.0;

    double lfoPhase = 0.0;                     // 0-2π
    double lfoPhaseIncrement = 2 * PI * currentLfoRate / 44100.0;

    // ====================================================================== //
    // 9.  EFFECT PROCESSOR DECLARATIONS                                      //
    // ====================================================================== //

    // ---------------------------------- TUBE DRIVER ----------------------- //
 
    double targetTubeAmount = 0.0;      // % (0-100)
    double targetTubeMinMix = 0.0;      // % (0-100)
    double targetTubeMaxMix = 100.0;    // % (0-100)

    double currentTubeAmount = 0.0;
    double currentTubeMinMix = 0.0;
    double currentTubeMaxMix = 100.0;

    // ---------------------------------- BITCRUSHER ------------------------ //

    double targetBitDepth = 16.0;     // bits (1.0-16.0)
    double targetBitMix = 0.0;      // % (0-100)

    double currentBitDepth = 16.0;
    double currentBitMix = 0.0;
    
    // ====================================================================== //
    // 10. INSTANCE-SPECIFIC CONFIGURATION                                    //
    // ====================================================================== //
    
    // Global Parameters – Sample / Loop
    double sample_rate = 44100.0;
    double fade_samples = 256;
    unsigned int loop_fade_samples = 256;
    unsigned int fadeInTime = 10; // ms
    double sampleLoopStartPercentage = 0.01;
    double sampleLoopEndPercentage = 1.0;

    // Global Parameters – Gain & Normalization
    double gain_normalization_cap = 3.0;

    // Global Parameters – Filter
    double filter_drive_scaling = 4.0;
    double filter_env_mod_scaling = 1.5;

    // Global Parameters – Comb Filter
    double comb_filter_drive_scaling = 4.0;
    double comb_limiter_strength = 0.8;
    double comb_feedback_limiter = 0.95;
    double comb_min_delay_ms = 1.0;   // ms
    double comb_max_delay_ms = 50.0;  // ms
    double comb_feedback_max = 0.95;
    double comb_feedback_scaling = 15.0;
    double comb_env_mod_scaling = 1.5;   // octaves
    double comb_min_resonance = 0.1;

    // Global Parameters – Tube Saturation
    double tube_bypass_threshold = 0.01;
    double tube_drive_scaling = 3.0;
    double tube_cubic_coeff = 0.33;
    double tube_quintic_coeff = 0.05;
    double tube_intensity_scaling = 2.0;

    // Global Parameters – Bitcrusher
    double bitcrusher_bypass_threshold = 0.01;
    double bitcrusher_max_depth = 16.0;
    double bitcrusher_min_depth = 1.0;
    double bitcrusher_dither_threshold = 8.0;
    double bitcrusher_mix_scale_threshold = 4.0;

    // Per-oscillator sample data (for variable-osc path)
    std::vector<float> sampleBuffers[MAX_OSC];
    float               samplePosFloatArr[MAX_OSC] = {0};
    unsigned int        sampleLoopStartArr[MAX_OSC] = {0};
    unsigned int        sampleLoopEndArr[MAX_OSC] = {0};
    double sampleLoopStartPercentageArr[MAX_OSC] = {0.0};
    double sampleLoopEndPercentageArr[MAX_OSC] = {1.0};
    double sampleBaseFreqArr[MAX_OSC] = {440.0};
    double timeScalingFactorArr[MAX_OSC] = {1.0};
    bool                loopActiveArr[MAX_OSC] = {false};
    std::string         samplePathArr[MAX_OSC];

    // High-pass filter settings per oscillator
    double highpassCutoffArr[MAX_OSC] = {0.0};
    bool   highpassEnabledArr[MAX_OSC] = {false};

    // High-pass filter state per oscillator (for real-time processing)
    double highpassPrevInput[MAX_OSC] = {0.0};
    double highpassPrevOutput[MAX_OSC] = {0.0};
    
    // Sample data
    std::vector<float> sampleBuffer;
    float samplePosFloat = 0;
    unsigned int sampleLoopStart = 0;
    unsigned int sampleLoopEnd = 0;
    bool loopActive = false;
    std::string samplePath;
    float applyHighpassFilter(float input, int oscIndex, double cutoffHz, double sampleRate);
    
    // Load sample function (moved from global scope to class method)
    bool loadSample(const char* filename);

    bool loadSampleAt(int index, const char* filename);
    
    // Helper methods
    void updatePhaseIncrement();
    void update_adsr();
    void update_filter_env();
    void updateFilterCoeffs();
    void updateCombParams();
    void reset();

    void calculate_highshelf_coefficients(double freq_hz, double gain_db, double fs);
    void calculate_peaking_eq_coefficients(double freq_hz, double gain_db, double Q, double fs);
    void calculate_lowshelf_coefficients(double freq_hz, double gain_db, double fs);

};

// SynthManager class - manages multiple synthesizer instances
class SynthManager {
public:
    SynthManager();
    ~SynthManager();
    
    // Create a new synthesizer instance and return its ID
    int createSynthesizer();
    
    // Get a synthesizer by ID
    Synthesizer* getSynthesizer(int id);
    
    // Delete a synthesizer by ID
    bool deleteSynthesizer(int id);
    
    // Get all active synthesizers
    std::vector<Synthesizer*> getActiveSynthesizers();
    
    // Check if a synthesizer ID exists
    bool hasSynthesizer(int id);
    
    // Initialize PortAudio
    bool initialize();
    
    // Start audio processing
    bool start();
    
    // Stop audio processing
    void stop();
    
    // Get the PortAudio stream
    PaStream* getStream() { return stream; }
    
private:
    std::unordered_map<int, std::unique_ptr<Synthesizer>> synthesizers;
    int nextSynthId = 0;
    PaStream* stream = nullptr;
    std::mutex mutex;
};

// Global instance of the SynthManager
extern SynthManager synthManager;

// PortAudio stream pointer shared across translation units
extern PaStream* stream;

//------------------------------------------------------------------------------//
//                  CENTRAL STRUCTURE- STATES AND PROCESSING ENGINE            //
//----------------------------------------------------------------------------//

// Instantiate the global SynthManager
SynthManager synthManager;

// PortAudio stream pointer shared across translation units
PaStream* stream = nullptr;

// Synthesizer constructor
Synthesizer::Synthesizer(int id) : synthId(id) {
    // Initialize comb filter delay line with a safe default first
    MAX_DELAY_SAMPLES = static_cast<int>(44100 / 20); // Safe default based on 44.1kHz
    // Then if sample_rate is valid, recalculate
    if (sample_rate > 0) {
        MAX_DELAY_SAMPLES = static_cast<int>(sample_rate / 20);
    }
    combDelayLine.resize(MAX_DELAY_SAMPLES, 0.0);
}

// Synthesizer destructor
Synthesizer::~Synthesizer() {
    // Nothing special to clean up
}

bool Synthesizer::loadSample(const char* filename) {
    SF_INFO sfinfo;
    SNDFILE* file = sf_open(filename, SFM_READ, &sfinfo);
    if (!file) return false;
    
    sampleBuffer.resize(sfinfo.frames);
    sf_readf_float(file, sampleBuffer.data(), sfinfo.frames);
    sf_close(file);
    samplePosFloat = 0;

    // Apply fade-in to first samples
    unsigned int fadeInSamples = sample_rate / fadeInTime;
    if (fadeInSamples > sampleBuffer.size()) fadeInSamples = static_cast<unsigned int>(sampleBuffer.size());
    for (unsigned int i = 0; i < fadeInSamples; ++i) {
        float fadeFactor = static_cast<float>(i) / fadeInSamples;
        sampleBuffer[i] *= fadeFactor;
    }
    
    // Update loop points based on percentages
    sampleLoopStart = static_cast<unsigned int>(sampleLoopStartPercentage * sampleBuffer.size());
    sampleLoopEnd = static_cast<unsigned int>(sampleLoopEndPercentage * sampleBuffer.size());
    return true;
}

// High-pass filter implementation (OUTSIDE the loadSample function)
float Synthesizer::applyHighpassFilter(float input, int oscIndex, double cutoffHz, double sampleRate) {
    if (!highpassEnabledArr[oscIndex] || cutoffHz <= 0.0) {
        return input;
    }
    
    // Calculate filter coefficient
    double rc = 1.0 / (2.0 * PI * cutoffHz);
    double dt = 1.0 / sampleRate;
    double alpha = rc / (rc + dt);
    
    // Apply high-pass filter: y[n] = alpha * (y[n-1] + x[n] - x[n-1])
    double output = alpha * (highpassPrevOutput[oscIndex] + input - highpassPrevInput[oscIndex]);
    
    // Update filter state
    highpassPrevInput[oscIndex] = input;
    highpassPrevOutput[oscIndex] = output;
    
    return static_cast<float>(output);
}



bool Synthesizer::loadSampleAt(int index, const char* filename) {
    if (index < 0 || index >= MAX_OSC) return false;

    SF_INFO sfinfo{};
    SNDFILE* file = sf_open(filename, SFM_READ, &sfinfo);
    if (!file) return false;

    sampleBuffers[index].resize(sfinfo.frames);
    sf_readf_float(file, sampleBuffers[index].data(), sfinfo.frames);
    sf_close(file);

    samplePosFloatArr[index] = 0.0f;
    
    // Fade-in to avoid clicks
    unsigned int fadeInSamples = static_cast<unsigned int>(sample_rate / fadeInTime);
    if (fadeInSamples > sampleBuffers[index].size())
        fadeInSamples = static_cast<unsigned int>(sampleBuffers[index].size());
    for (unsigned int i = 0; i < fadeInSamples; ++i) {
        float fadeFactor = static_cast<float>(i) / fadeInSamples;
        sampleBuffers[index][i] *= fadeFactor;
    }
    
    // Apply high-pass filter if enabled for this oscillator
    if (highpassEnabledArr[index] && highpassCutoffArr[index] > 0.0) {
        // Reset filter state for this oscillator
        highpassPrevInput[index] = 0.0;
        highpassPrevOutput[index] = 0.0;
        
        // Apply high-pass filter to entire sample
        for (size_t i = 0; i < sampleBuffers[index].size(); ++i) {
            sampleBuffers[index][i] = applyHighpassFilter(
                sampleBuffers[index][i], 
                index, 
                highpassCutoffArr[index], 
                sfinfo.samplerate
            );
        }
    }
    // Normalize sample to prevent explosions
    float peakValue = 0.0f;
    for (size_t i = 0; i < sampleBuffers[index].size(); ++i) {
        float absValue = std::abs(sampleBuffers[index][i]);
        if (absValue > peakValue) {
            peakValue = absValue;
        }
    }

    // If peak exceeds 1.0, normalize the entire sample
    if (peakValue > 0.5f) {
        float normalizationFactor = 1.0f / peakValue;
        for (size_t i = 0; i < sampleBuffers[index].size(); ++i) {
            sampleBuffers[index][i] *= normalizationFactor;
        }
        std::cout << "Normalized sample " << index << " - Peak was " << peakValue << ", factor=" << normalizationFactor << std::endl;
    }
    // Compute loop points from per-oscillator percentages
    sampleLoopStartArr[index] = static_cast<unsigned int>(sampleLoopStartPercentageArr[index] * sampleBuffers[index].size());
    sampleLoopEndArr[index]   = static_cast<unsigned int>(sampleLoopEndPercentageArr[index] * sampleBuffers[index].size());
    // Enable looping for this oscillator
    loopActiveArr[index] = true;
    return true;
}

// Update phase increment based on frequency
void Synthesizer::updatePhaseIncrement() {
    phaseIncrement = 2 * PI * frequency / sample_rate;
    timeScalingFactor = phaseIncrement / basePhaseIncrement;
}

// Update ADSR envelope parameters
void Synthesizer::update_adsr() {
    attackSamples = static_cast<unsigned long>(sample_rate * currentAttackTime);
    decaySamples = static_cast<unsigned long>(sample_rate * currentDecayTime);
    releaseSamples = static_cast<unsigned long>(sample_rate * currentReleaseTime);
    sustainCalc = std::pow(10.0, currentSustainLevel / 20.0);
}

// Update filter envelope parameters
void Synthesizer::update_filter_env() {
    filterEnvAttackSamples = static_cast<unsigned long>(sample_rate * currentFilterEnvAttack);
    filterEnvDecaySamples = static_cast<unsigned long>(sample_rate * currentFilterEnvDecay);
    filterEnvReleaseSamples = static_cast<unsigned long>(sample_rate * currentFilterEnvRelease);
    filterEnvSustainCalc = std::pow(10.0, currentFilterEnvSustain / 20.0);
}

// Reset synthesizer state
void Synthesizer::reset() {
    std::lock_guard<std::mutex> lock(mutex);
    
    noteOn = true;
    sampleCount = 0;
    releaseStartSample = 0;
    releaseHoldCounter = 0;
    envelopeState = ATTACK;
    samplesSinceStateChange = fade_samples;
    updatePhaseIncrement();
}

// ------------------------------------------------------------------ //
//  Filter sample processing  (includes drive)                        //
// ------------------------------------------------------------------ //
inline double Synthesizer::processFilter(double inSample)
{
    const double drvAmt = currentFilterDrive / 100.0;   // 0-1
    const double drvGain = 1.0 + drvAmt * filter_drive_scaling;
    double x = std::tanh(inSample * drvGain);

    // Direct-Form-II Transposed bi-quad //
    double y = b0 * x + z1;

    z1 = b1 * x - a1 * y + z2;
    z2 = b2 * x - a2 * y;
    return y;
}




// ------------------------------------------------------------------ //
//  Comb filter processing (includes drive)                           //
// ------------------------------------------------------------------ //
inline double Synthesizer::processCombFilter(double inSample)
{
    // --------------------------------------------------------------
    // 1.  Pre-drive saturation
    // --------------------------------------------------------------
    const double drvAmt = currentCombDrive / 100.0;              // 0-1
    const double drvGain = 1.0 + drvAmt * comb_filter_drive_scaling; // up to 5×
    double x = std::tanh(inSample * drvGain);

    // --------------------------------------------------------------
    // 2.  Read delayed sample
    // --------------------------------------------------------------
    int readPos = combWritePos - combDelayInSamples;
    if (readPos < 0) readPos += MAX_DELAY_SAMPLES;
    double delayedSample = combDelayLine[readPos];

    // --------------------------------------------------------------
    // 3.  Improved feedback limiter
    // --------------------------------------------------------------
    double fbGain = combFeedback;
    double absDelayed = std::abs(delayedSample);
    if (absDelayed > comb_feedback_limiter && comb_feedback_limiter > 0.0) {
        double excess = absDelayed / comb_feedback_limiter; // >1.0
        fbGain /= excess;                                   // reduce feedback
    }

    // --------------------------------------------------------------
    // 4.  Combine input + (limited) feedback
    // --------------------------------------------------------------
    double output = x + fbGain * delayedSample;

    // --------------------------------------------------------------
    // 5.  Final soft-clip limiter
    // --------------------------------------------------------------
    output = std::tanh(output * comb_limiter_strength) / comb_limiter_strength;

    // --------------------------------------------------------------
    // 6.  Write to delay line & advance pointer
    // --------------------------------------------------------------
    combDelayLine[combWritePos] = output;
    combWritePos = (combWritePos + 1) % MAX_DELAY_SAMPLES;

    return output;
}

// ------------------------------------------------------------------ //
//  Tube driver processing (emulates tube saturation)                 //
// ------------------------------------------------------------------ //
inline double Synthesizer::processTubeDriver(double inSample)
{
    // Skip if amount is ~zero to avoid needless math                  
    if (currentTubeAmount < tube_bypass_threshold)
        return inSample;

    // Drive amount normalised 0-1                                     
    const double driveAmount = currentTubeAmount / 100.0;
    // Input gain scales with drive to push signal into saturation     
    double x = inSample * (1.0 + driveAmount * tube_drive_scaling);

    // Odd-order polynomial for tube-like asymmetrical saturation      
    // y = x − a·x³ + b·x⁵,   a = 0.33·drive,  b = 0.05·drive²       
    double tubeDist = x
                    - tube_cubic_coeff * driveAmount * x * x * x
                    + tube_quintic_coeff * driveAmount * driveAmount
                                * x * x * x * x * x;

    // Soft-clip output to keep it civil                             
    tubeDist = std::tanh(tubeDist);

    // Dry/wet mix interpolates between min & max mix settings based   
    // on instantaneous input amplitude (acts like "sag")             
    const double inputIntensity = std::min(1.0, std::abs(inSample) * tube_intensity_scaling);
    const double mixRatio = (currentTubeMinMix / 100.0)
                          + ((currentTubeMaxMix - currentTubeMinMix) / 100.0)
                            * inputIntensity;

    return inSample * (1.0 - mixRatio) + tubeDist * mixRatio;
}

// ------------------------------------------------------------------ //
//  Bitcrusher processing (reduces bit depth for digital distortion)  //
// ------------------------------------------------------------------ //
inline double Synthesizer::processBitcrusher(double inSample)
{
    // Bypass if mix ≈ 0 % or depth ≈ 16-bit (full quality)            
    if (currentBitMix < bitcrusher_bypass_threshold || currentBitDepth >= bitcrusher_max_depth)
        return inSample;

    // ------------------------------------------------------------------
    //  Safety clamp: keep sample in −1 … 1 to avoid NAN / inf later
    // ------------------------------------------------------------------
    inSample = std::max(-1.0, std::min(1.0, inSample));

    // Constrain depth to sane 1-16 bit range and compute steps        
    const double depth = std::max(bitcrusher_min_depth, std::min(bitcrusher_max_depth, currentBitDepth));
    const double bitSteps = std::pow(2.0, depth);

    // Scale  −1..1  →  0..bitSteps, quantise, clamp                   
    double scaled = (inSample + 1.0) * 0.5 * bitSteps;
    double quantised = std::floor(scaled);
    quantised = std::max(0.0, std::min(bitSteps - 1.0, quantised));

    // Map back to −1..1                                              
    double crushed = (quantised / bitSteps) * 2.0 - 1.0;

    // Optional dithering for very low bit depths (<8-bit)            
    if (depth < bitcrusher_dither_threshold) {
        const double dither =
            (static_cast<double>(std::rand()) / RAND_MAX - 0.5) * (1.0 / bitSteps);
        crushed += dither;
    }

    // Final clamp after dithering                                     
    crushed = std::max(-1.0, std::min(1.0, crushed));

    // Adaptive mix: reduce wet level for extreme crushing (<4-bit)    
    double mixRatio = currentBitMix / 100.0;
    if (depth < bitcrusher_mix_scale_threshold)
        mixRatio *= (depth / bitcrusher_mix_scale_threshold);   // linearly scale 0–4 bit range

    return std::max(-1.0, std::min(1.0,
                inSample * (1.0 - mixRatio) + crushed * mixRatio));
}

// Calculate final cutoff after global / key-track / envelope influence
inline double Synthesizer::calculateEffectiveCutoff() {
    // Mid-point for the perceptual scaling
    const double MID_CUTOFF_HZ = (MIN_CUTOFF_HZ + MAX_CUTOFF_HZ) * 0.5;

    // --- Global cutoff scaling --------------------------------------
    double cutoff = 0.0;
    if (currentGlobalCutoff <= MID_CUTOFF_HZ) {
        const double scale = currentGlobalCutoff / MID_CUTOFF_HZ;
        cutoff = MIN_CUTOFF_HZ + scale * (currentFilterCutoff - MIN_CUTOFF_HZ);
    } else {
        const double scale = (currentGlobalCutoff - MID_CUTOFF_HZ) /
                             (MAX_CUTOFF_HZ - MID_CUTOFF_HZ);
        cutoff = currentFilterCutoff + scale * (MAX_CUTOFF_HZ - currentFilterCutoff);
    }

    // --- Key tracking -----------------------------------------------
    if (currentFilterKeyTrack > 0.0) {
        const double keyRatio = frequency / 440.0;        // A4 reference
        cutoff *= std::pow(keyRatio, currentFilterKeyTrack / 100.0);
    }

    // --- Envelope modulation ----------------------------------------
    if (currentFilterEnvMod > 0.0 && filterEnvState != IDLE) {
        const double scaledLvl = currentFilterEnvLevel * (currentFilterEnvMod / 100.0);
        const double envFactor = std::pow(10.0, scaledLvl * filter_env_mod_scaling);
        cutoff *= envFactor;
    }

    // --- Clamp to (20 Hz, Nyquist) ----------------------------------
    const double nyquist = sample_rate * 0.5 - 1.0;
    return std::clamp(cutoff, MIN_CUTOFF_HZ, nyquist);
}

// Calculate final resonance (Q) after global scaling
inline double Synthesizer::calculateEffectiveResonance() {
    const double MID_RESO_Q = (MIN_RESO_Q + MAX_RESO_Q) * 0.5;

    double reso = 0.0;
    if (currentGlobalResonance <= MID_RESO_Q) {
        const double scale = currentGlobalResonance / MID_RESO_Q;
        reso = MIN_RESO_Q + scale * (currentFilterResonance - MIN_RESO_Q);
    } else {
        const double scale = (currentGlobalResonance - MID_RESO_Q) /
                             (MAX_RESO_Q - MID_RESO_Q);
        reso = currentFilterResonance + scale * (MAX_RESO_Q - currentFilterResonance);
    }

    // Guarantee a sensible lower bound
    return std::max(0.1, reso);
}

// Populate bi-quad coefficients b0-b2 / a1-a2 for a LPF
inline void Synthesizer::calculateBiquadCoefficients(double cutoffHz, double resonanceQ) {
    const double omega = 2.0 * PI * cutoffHz / sample_rate;
    const double sinO = std::sin(omega);
    const double cosO = std::cos(omega);
    const double alpha = sinO / (2.0 * resonanceQ);

    const double b0u = (1.0 - cosO) * 0.5;
    const double b1u = 1.0 - cosO;
    const double b2u = (1.0 - cosO) * 0.5;
    const double a0u = 1.0 + alpha;
    const double a1u = -2.0 * cosO;
    const double a2u = 1.0 - alpha;

    b0 = b0u / a0u;
    b1 = b1u / a0u;
    b2 = b2u / a0u;
    a1 = a1u / a0u;
    a2 = a2u / a0u;
}

void Synthesizer::calculate_highshelf_coefficients(double freq_hz, double gain_db, double fs) {
    // Skip calculation if gain is essentially zero
    if (std::abs(gain_db) < 1e-3) {
        b0 = 1.0; b1 = 0.0; b2 = 0.0;
        a1 = 0.0; a2 = 0.0;
        return;
    }

    double A = std::pow(10.0, gain_db / 40.0);  // √(linear gain)
    double w0 = 2.0 * PI * freq_hz / fs;
    double cos_w0 = std::cos(w0);
    double sin_w0 = std::sin(w0);
    double Q = 0.707;  // gentle slope
    double alpha = sin_w0 / (2.0 * Q) * std::sqrt((A + 1.0/A) * (1.0/Q - 1.0) + 2.0);

    // Calculate coefficients
    double b0_temp = A*((A+1.0) + (A-1.0)*cos_w0 + 2.0*std::sqrt(A)*alpha);
    double b1_temp = -2.0*A*((A-1.0) + (A+1.0)*cos_w0);
    double b2_temp = A*((A+1.0) + (A-1.0)*cos_w0 - 2.0*std::sqrt(A)*alpha);
    double a0_temp = (A+1.0) - (A-1.0)*cos_w0 + 2.0*std::sqrt(A)*alpha;
    double a1_temp = 2.0*((A-1.0) - (A+1.0)*cos_w0);
    double a2_temp = (A+1.0) - (A-1.0)*cos_w0 - 2.0*std::sqrt(A)*alpha;

    // Normalize by a0
    b0 = b0_temp / a0_temp;
    b1 = b1_temp / a0_temp;
    b2 = b2_temp / a0_temp;
    a1 = a1_temp / a0_temp;
    a2 = a2_temp / a0_temp;
}

void Synthesizer::calculate_peaking_eq_coefficients(double freq_hz, double gain_db, double Q, double fs) {
    // Skip calculation if gain is essentially zero
    if (std::abs(gain_db) < 1e-3) {
        b0 = 1.0; b1 = 0.0; b2 = 0.0;
        a1 = 0.0; a2 = 0.0;
        return;
    }

    double A = std::pow(10.0, gain_db / 40.0);  // √(linear gain)
    double w0 = 2.0 * PI * freq_hz / fs;
    double cos_w0 = std::cos(w0);
    double sin_w0 = std::sin(w0);
    double alpha = sin_w0 / (2.0 * Q);

    // Calculate coefficients
    double b0_temp = 1.0 + alpha * A;
    double b1_temp = -2.0 * cos_w0;
    double b2_temp = 1.0 - alpha * A;
    double a0_temp = 1.0 + alpha / A;
    double a1_temp = -2.0 * cos_w0;
    double a2_temp = 1.0 - alpha / A;

    // Normalize by a0
    b0 = b0_temp / a0_temp;
    b1 = b1_temp / a0_temp;
    b2 = b2_temp / a0_temp;
    a1 = a1_temp / a0_temp;
    a2 = a2_temp / a0_temp;
}

void Synthesizer::calculate_lowshelf_coefficients(double freq_hz, double gain_db, double fs) {
    // Skip calculation if gain is essentially zero
    if (std::abs(gain_db) < 1e-3) {
        b0 = 1.0; b1 = 0.0; b2 = 0.0;
        a1 = 0.0; a2 = 0.0;
        return;
    }

    double A = std::pow(10.0, gain_db / 40.0);  // √(linear gain)
    double w0 = 2.0 * PI * freq_hz / fs;
    double cos_w0 = std::cos(w0);
    double sin_w0 = std::sin(w0);
    double Q = 0.707;  // gentle slope
    double alpha = sin_w0 / (2.0 * Q) * std::sqrt((A + 1.0/A) * (1.0/Q - 1.0) + 2.0);

    // Calculate coefficients
    double b0_temp = A*((A+1.0) - (A-1.0)*cos_w0 + 2.0*std::sqrt(A)*alpha);
    double b1_temp = 2.0*A*((A-1.0) - (A+1.0)*cos_w0);
    double b2_temp = A*((A+1.0) - (A-1.0)*cos_w0 - 2.0*std::sqrt(A)*alpha);
    double a0_temp = (A+1.0) + (A-1.0)*cos_w0 + 2.0*std::sqrt(A)*alpha;
    double a1_temp = -2.0*((A-1.0) + (A+1.0)*cos_w0);
    double a2_temp = (A+1.0) + (A-1.0)*cos_w0 - 2.0*std::sqrt(A)*alpha;

    // Normalize by a0
    b0 = b0_temp / a0_temp;
    b1 = b1_temp / a0_temp;
    b2 = b2_temp / a0_temp;
    a1 = a1_temp / a0_temp;
    a2 = a2_temp / a0_temp;
}


// Recompute LPF coefficients – public entry
void Synthesizer::updateFilterCoeffs() {
    const double cutoffHz = calculateEffectiveCutoff();
    const double resonanceQ = calculateEffectiveResonance();
    calculateBiquadCoefficients(cutoffHz, resonanceQ);
}

// Calculate effective comb-filter cutoff (Hz) after all modifiers
inline double Synthesizer::calculateCombEffectiveCutoff() {
    const double MID_CUTOFF_HZ = (MIN_CUTOFF_HZ + MAX_CUTOFF_HZ) * 0.5;

    double cutoff = 0.0;
    if (currentGlobalCutoff <= MID_CUTOFF_HZ) {
        const double scale = currentGlobalCutoff / MID_CUTOFF_HZ;
        cutoff = MIN_CUTOFF_HZ + scale * (currentCombCutoff - MIN_CUTOFF_HZ);
    } else {
        const double scale = (currentGlobalCutoff - MID_CUTOFF_HZ) /
                             (MAX_CUTOFF_HZ - MID_CUTOFF_HZ);
        cutoff = currentCombCutoff + scale * (MAX_CUTOFF_HZ - currentCombCutoff);
    }

    // Key tracking
    if (currentCombKeyTrack > 0.0) {
        const double keyRatio = frequency / 440.0; // A4
        cutoff *= std::pow(keyRatio, currentCombKeyTrack / 100.0);
    }

    // Envelope modulation
    if (currentCombEnvMod > 0.0 && filterEnvState != IDLE) {
        const double scaledLvl = currentFilterEnvLevel * (currentCombEnvMod / 100.0);
        const double envFactor = std::pow(10.0, scaledLvl * comb_env_mod_scaling);
        cutoff *= envFactor;
    }

    // Clamp to audio range
    const double nyquist = sample_rate * 0.5 - 1.0;
    return std::clamp(cutoff, MIN_CUTOFF_HZ, nyquist);
}

// Calculate effective resonance (Q) for comb filter
inline double Synthesizer::calculateCombEffectiveResonance() {
    const double MID_RESO_Q = (MIN_RESO_Q + MAX_RESO_Q) * 0.5;

    double reso = 0.0;
    if (currentGlobalResonance <= MID_RESO_Q) {
        const double scale = currentGlobalResonance / MID_RESO_Q;
        reso = MIN_RESO_Q + scale * (currentCombResonance - MIN_RESO_Q);
    } else {
        const double scale = (currentGlobalResonance - MID_RESO_Q) /
                             (MAX_RESO_Q - MID_RESO_Q);
        reso = currentCombResonance + scale * (MAX_RESO_Q - currentCombResonance);
    }

    return std::max(comb_min_resonance, reso);
}

// Derive delay-line length and feedback from cutoff/resonance
inline void Synthesizer::calculateCombDelayAndFeedback(double cutoffHz, double resonanceQ) {
    const double nyquist = sample_rate * 0.5;
    const double normCutoff = cutoffHz / nyquist;

    // Delay time in ms (inverse of freq)
    const double delayMs = comb_min_delay_ms +
                           (comb_max_delay_ms - comb_min_delay_ms) * (1.0 - normCutoff);
    combDelayInSamples = static_cast<int>(sample_rate * delayMs / 1000.0);
    combDelayInSamples = std::clamp(combDelayInSamples, 1, MAX_DELAY_SAMPLES - 1);

    // Feedback from resonance
    combFeedback = std::min(comb_feedback_max, resonanceQ / comb_feedback_scaling);
}

// Update comb filter parameters (call under mutex!)
void Synthesizer::updateCombParams() {
    const double cutoffHz = calculateCombEffectiveCutoff();
    const double resonanceQ = calculateCombEffectiveResonance();
    calculateCombDelayAndFeedback(cutoffHz, resonanceQ);
}

// SynthManager implementation
SynthManager::SynthManager() {
    // Initialize is called separately
}

SynthManager::~SynthManager() {
    stop();
}

int SynthManager::createSynthesizer() {
    std::lock_guard<std::mutex> lock(mutex);
    int id = nextSynthId++;
    synthesizers[id] = std::make_unique<Synthesizer>(id);
    return id;
}

Synthesizer* SynthManager::getSynthesizer(int id) {
    std::lock_guard<std::mutex> lock(mutex);
    auto it = synthesizers.find(id);
    if (it != synthesizers.end()) {
        return it->second.get();
    }
    return nullptr;
}

bool SynthManager::deleteSynthesizer(int id) {
    std::lock_guard<std::mutex> lock(mutex);
    return synthesizers.erase(id) > 0;
}

std::vector<Synthesizer*> SynthManager::getActiveSynthesizers() {
    std::lock_guard<std::mutex> lock(mutex);
    std::vector<Synthesizer*> result;
    result.reserve(synthesizers.size());
    for (auto& pair : synthesizers) {
        result.push_back(pair.second.get());
    }
    return result;
}

bool SynthManager::hasSynthesizer(int id) {
    std::lock_guard<std::mutex> lock(mutex);
    return synthesizers.find(id) != synthesizers.end();
}

bool SynthManager::initialize() {
    PaError err = Pa_Initialize();
    return err == paNoError;
}

bool SynthManager::start() {
    stop(); // Stop any existing stream
    return true; // Actual stream creation happens in external functions
}

void SynthManager::stop() {
    if (stream) {
        Pa_StopStream(stream);
        Pa_CloseStream(stream);
        Pa_Terminate();
        stream = nullptr;
    }
}

//------------------------------------------------------------------------------//
//                      AUDIO CALLBACK AND PROCESSING                          //
//----------------------------------------------------------------------------//

// ---------------------- Sample Path Setter ----------------------------------                                                      
extern "C" void set_sample_path(const char* path, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (synth && path && *path) {
        synth->samplePath = path;
    }
}

extern "C" void set_sample_path_at(const char* path, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    if (!path || !*path) return;
    if (index < 0 || index >= MAX_OSC) return;
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->samplePathArr[index] = path;
    synth->loadSampleAt(index, path);  // Load the sample immediately
}

// The global `stream` pointer is declared/defined in the audio-engine TU.
static int paCallback(const void*, void* outputBuffer,
                      unsigned long framesPerBuffer,
                      const PaStreamCallbackTimeInfo*,
                      PaStreamCallbackFlags,
                      void* userData) {
    float* out = static_cast<float*>(outputBuffer);
    SynthManager* manager = static_cast<SynthManager*>(userData);
    
    // Get all active synthesizers
    std::vector<Synthesizer*> activeSynths = manager->getActiveSynthesizers();
    
    // If no active synthesizers, output silence
    if (activeSynths.empty()) {
        for (unsigned long i = 0; i < framesPerBuffer; i++) {
            out[i] = 0.0f;
        }
        return paContinue;
    }
    
    // Process each frame
    for (unsigned long i = 0; i < framesPerBuffer; i++) {
        float mixedOutput = 0.0f; // Initialize mixed output for this frame
        
        // Process each synthesizer and mix outputs
        for (Synthesizer* synth : activeSynths) {
            double amplitudeMultiplier = 0.0;
            EnvelopeState currentState;
            double currentAmp;
            double prevAmp;
            unsigned long fadeCounter;
            bool isStateTransition = false;
            unsigned long currentSampleCount;

            {
                std::lock_guard<std::mutex> lock(synth->mutex);
                currentState = synth->envelopeState;
                currentSampleCount = synth->sampleCount;

                // Reset variables per envelope
                if (currentState != synth->prevEnvelopeState) {
                    synth->prevEnvelopeState = currentState;
                    synth->samplesSinceStateChange = 0;
                    synth->prevAmplitude = synth->currentAmplitude;
                    isStateTransition = true;
                    // Update per-oscillator time scaling factors for sample playback
                    for (int oi = 0; oi < synth->oscCount; ++oi) {
                        if (synth->oscWaveform[oi] == WAVE_SAMPLE) {
                            synth->timeScalingFactorArr[oi] = synth->frequency / synth->sampleBaseFreqArr[oi];
                        }
                    }
                }

                switch (currentState) {
                    case ATTACK:
                        if ((synth->sampleCount < synth->attackSamples) && (synth->prevEnvelopeState == IDLE)) {
                            amplitudeMultiplier = static_cast<double>(synth->sampleCount) / synth->attackSamples;
                        } else if ((synth->sampleCount < synth->attackSamples) && (synth->prevEnvelopeState == RELEASE)) {
                            amplitudeMultiplier = static_cast<double>(synth->sampleCount) / synth->attackSamples;
                        } else {
                            synth->envelopeState = DECAY;
                            amplitudeMultiplier = 1.0;
                            synth->samplesSinceStateChange = 0;
                            isStateTransition = true;

                            // Calculate volume impact factors from all parameters
                            double oscGainFactor = std::sqrt(synth->currentSineGain * synth->currentSineGain + 
                                                            synth->currentSampleGain * synth->currentSampleGain);

                            // Filter drive increases volume
                            double filterFactor = 1.0 + (synth->currentFilterDrive / 100.0) * 0.5;

                            // Comb filter resonance and drive affect volume
                            double combFactor = 1.0 + (synth->currentCombDrive / 100.0) * 0.3 + 
                                            (synth->currentCombResonance / 10.0) * 0.2;

                            // Tube amount increases perceived volume
                            double tubeFactor = 1.0 + (synth->currentTubeAmount / 100.0) * 0.4;

                            // Combined impact on volume
                            double totalVolumeFactor = oscGainFactor * filterFactor * combFactor * tubeFactor;

                            // Store current normalization factor as previous value
                            synth->prevNoteVolumeNormalizationFactor = synth->noteVolumeNormalizationFactor;

                            // Calculate target normalization factor (inverse of the volume impact)
                            // Cap the normalization to avoid extreme values
                            synth->targetNoteVolumeNormalizationFactor = std::clamp(
                                1.0 / std::max(0.5, std::min(2.0, totalVolumeFactor)), 
                                0.5, 2.0
                            );
                            
                        }
                        break;
                    case DECAY: {
                        unsigned long decayPos = synth->sampleCount - synth->attackSamples;
                        if (decayPos < synth->decaySamples) {
                            double decayProgress = static_cast<double>(decayPos) / synth->decaySamples;
                            amplitudeMultiplier = 1.0 + decayProgress * (synth->sustainCalc - 1.0);
                        } else {
                            synth->envelopeState = SUSTAIN;
                            amplitudeMultiplier = synth->sustainCalc;
                            synth->samplesSinceStateChange = 0;
                            isStateTransition = true;
                        }
                        break;
                    }
                    case SUSTAIN:
                        amplitudeMultiplier = synth->sustainCalc;
                        break;
                    case HOLD_BEFORE_RELEASE:
                        amplitudeMultiplier = synth->releaseStartLevel;
                        if (++synth->releaseHoldCounter >= synth->releaseHoldSamples) {
                            synth->envelopeState = RELEASE;
                            synth->releaseStartSample = synth->sampleCount;
                            synth->samplesSinceStateChange = 0;
                            isStateTransition = true;
                        }
                        break;
                    case RELEASE: {
                        unsigned long releasePos = synth->sampleCount - synth->releaseStartSample;
                        if (releasePos >= synth->releaseSamples) {
                            amplitudeMultiplier = 0.0;
                            synth->envelopeState = IDLE;
                            synth->samplesSinceStateChange = 0;
                            synth->prevAmplitude = 0;
                            isStateTransition = true;
                        } else {
                            double releaseProgress = static_cast<double>(releasePos) / synth->releaseSamples;
                            amplitudeMultiplier = synth->releaseStartLevel * (1.0 - releaseProgress);
                        }
                        break;
                    }
                    case IDLE:
                    default: {
                        // Keep generating samples until we hit a zero-crossing
                        double rawSine = sin(synth->phase);
                        
                        // If we're near a zero crossing, truly silence
                        if (std::abs(rawSine) < 1e-4) {
                            amplitudeMultiplier = 0.0;
                        } else {
                            amplitudeMultiplier = 0.0;  // keep amplitude at 0
                        }
                        break;
                    }
                }

                fadeCounter = synth->samplesSinceStateChange;
                prevAmp = synth->prevAmplitude;
                currentAmp = amplitudeMultiplier;

                if (fadeCounter < synth->fade_samples) {
                    double alpha = static_cast<double>(fadeCounter) / synth->fade_samples;
                    amplitudeMultiplier = (1.0 - alpha) * prevAmp + alpha * currentAmp;
                } else {
                    amplitudeMultiplier = currentAmp;
                }

                synth->samplesSinceStateChange++;
                synth->currentAmplitude = amplitudeMultiplier;
            }

            // Get phase and calculate raw sine value
            double phaseCopy;
            {
                std::lock_guard<std::mutex> lock(synth->mutex);
                phaseCopy = synth->phase;
            }

            float sampleValue = 0.0f;
            if (!synth->sampleBuffer.empty()) {
                int indexA = static_cast<int>(floor(synth->samplePosFloat));
                int indexB = indexA + 1;
                if (indexB >= synth->sampleBuffer.size()) indexB = indexA;

                float frac = static_cast<float>(synth->samplePosFloat - indexA);

                sampleValue = synth->sampleBuffer[indexA] * (1.0f - frac) + synth->sampleBuffer[indexB] * frac;

                if (synth->loopActive && synth->envelopeState != RELEASE && synth->envelopeState != IDLE) {
                    // Calculate fade out factor near loop end
                    float fadeOutFactor = 1.0f;
                    if (synth->samplePosFloat >= synth->sampleLoopEnd - synth->loop_fade_samples) {
                        unsigned int fadePos = synth->samplePosFloat - (synth->sampleLoopEnd - synth->loop_fade_samples);
                        fadeOutFactor = 1.0f - static_cast<float>(fadePos) / synth->loop_fade_samples;
                    }

                    // Calculate fade in factor near loop start
                    float fadeInFactor = 1.0f;
                    if (synth->samplePosFloat < synth->sampleLoopStart + synth->loop_fade_samples) {
                        unsigned int fadePos = synth->samplePosFloat - synth->sampleLoopStart;
                        fadeInFactor = static_cast<float>(fadePos) / synth->loop_fade_samples;
                    }

                    // Combine fade factors (multiplying them gives a crossfade effect)
                    float loopFadeFactor = fadeOutFactor * fadeInFactor;

                    sampleValue *= loopFadeFactor;

                    synth->samplePosFloat += synth->timeScalingFactor;
                    if (synth->samplePosFloat >= synth->sampleLoopEnd || synth->samplePosFloat >= synth->sampleBuffer.size()) {
                        synth->samplePosFloat = synth->sampleLoopStart;
                    }
                } else {
                    synth->samplePosFloat += synth->timeScalingFactor;
                    if (synth->samplePosFloat >= synth->sampleBuffer.size()) 
                        synth->samplePosFloat = synth->sampleBuffer.size() - 1; // hold last sample
                }
            }

            double modulator = sin(phaseCopy);  // same freq
            double modulatedPhase = phaseCopy + synth->fmDepth * modulator;
            double rawSine = sin(modulatedPhase);

            double rawSquare = (rawSine >= 0.0 ? 1.0 : -1.0);

            // Triangle via asin(sin) scaled to [-1,1]
            double rawTriangle = (2.0 / PI) * std::asin(rawSine);

            // Saw: normalised phase → [-1,1]
            double phaseNorm = phaseCopy / (2.0 * PI);
            phaseNorm -= std::floor(phaseNorm);
            double rawSaw = 2.0 * phaseNorm - 1.0;
            
            // Pre-compute per-oscillator sample values for WAVE_SAMPLE when in variable-osc mode
            double oscSampleVals[MAX_OSC] = {0.0};
            if (synth->oscCount > 0) {
                for (int oi = 0; oi < synth->oscCount; ++oi) {
                    if (synth->oscWaveform[oi] == WAVE_SAMPLE && !synth->sampleBuffers[oi].empty()) {
                        int indexA = static_cast<int>(floor(synth->samplePosFloatArr[oi]));
                        int indexB = indexA + 1;
                        if (indexB >= static_cast<int>(synth->sampleBuffers[oi].size())) indexB = indexA;

                        float frac = static_cast<float>(synth->samplePosFloatArr[oi] - indexA);
                        float sa = synth->sampleBuffers[oi][indexA];
                        float sb = synth->sampleBuffers[oi][indexB];
                        float val = sa * (1.0f - frac) + sb * frac;
                        // DEBUG: Check sample interpolation inputs with cooldown
                        static auto last_debug_log_time = std::chrono::high_resolution_clock::now();
                        static bool debug_printed = false;
                        auto current_debug_time = std::chrono::high_resolution_clock::now();
                        auto time_since_last_debug_log = std::chrono::duration_cast<std::chrono::milliseconds>(current_debug_time - last_debug_log_time).count();

                        if (std::abs(val) > 0.05f && time_since_last_debug_log > 500) {
                            std::cout << "SAMPLE DEBUG - Osc[" << oi << "] val=" << val << " sa=" << sa << " sb=" << sb << " frac=" << frac 
                                    << " indexA=" << indexA << " indexB=" << indexB << " samplePos=" << synth->samplePosFloatArr[oi] 
                                    << " bufferSize=" << synth->sampleBuffers[oi].size() << std::endl;
                            last_debug_log_time = current_debug_time;
                        }
                        // Crossfade around loop boundaries if looping
                        if (synth->loopActiveArr[oi]) {
                            float fadeOutFactor = 1.0f;
                            float fadeInFactor  = 1.0f;

                            if (synth->samplePosFloatArr[oi] >= synth->sampleLoopEndArr[oi] - synth->loop_fade_samples) {
                                unsigned int fadePos = static_cast<unsigned int>(
                                    synth->samplePosFloatArr[oi] - (synth->sampleLoopEndArr[oi] - synth->loop_fade_samples));
                                fadeOutFactor = 1.0f - static_cast<float>(fadePos) / synth->loop_fade_samples;
                            }
                            if (synth->samplePosFloatArr[oi] >= synth->sampleLoopStartArr[oi] && synth->samplePosFloatArr[oi] < synth->sampleLoopStartArr[oi] + synth->loop_fade_samples) {
                                int raw = static_cast<int>(synth->samplePosFloatArr[oi] - synth->sampleLoopStartArr[oi]);
                                if (raw < 0) {
                                    std::cout << "NEGATIVE RAW - Osc[" << oi << "] pos=" << synth->samplePosFloatArr[oi] 
                                            << " loopStart=" << synth->sampleLoopStartArr[oi] << " raw=" << raw << std::endl;
                                }
                                unsigned int fadePos = raw < 0 ? 0u : static_cast<unsigned int>(raw);
                                if (fadePos > synth->loop_fade_samples) fadePos = synth->loop_fade_samples;
                                fadeInFactor = static_cast<float>(fadePos) / synth->loop_fade_samples;
                            }
                            val *= (fadeOutFactor * fadeInFactor);
                            if (std::abs(val) > 0.05f && (fadeOutFactor < 1.0f || fadeInFactor < 1.0f)) {
                                std::cout << "CROSSFADE EXPLOSION - Osc[" << oi << "] val=" << val << " fadeOut=" << fadeOutFactor << " fadeIn=" << fadeInFactor << " before=" << (sa * (1.0f - frac) + sb * frac) << std::endl;
                            }
                        }
                        
                        
                        oscSampleVals[oi] = static_cast<double>(val);

                        
                        // Advance and wrap/hold
                        synth->samplePosFloatArr[oi] += synth->timeScalingFactorArr[oi];
                        if (synth->loopActiveArr[oi]) {
                            if (synth->samplePosFloatArr[oi] >= synth->sampleLoopEndArr[oi] ||
                                synth->samplePosFloatArr[oi] >= synth->sampleBuffers[oi].size()) {
                                synth->samplePosFloatArr[oi] = static_cast<float>(synth->sampleLoopStartArr[oi]);
                            }
                        } else {
                            if (synth->samplePosFloatArr[oi] >= synth->sampleBuffers[oi].size()) {
                                synth->samplePosFloatArr[oi] = static_cast<float>(synth->sampleBuffers[oi].size() - 1);
                            }
                        }
                    }
                    // OSC SAMPLE EXPLOSION DETECTOR: Check per-oscillator sample values
                    static float last_sample_vals[MAX_OSC] = {0.0f};
                    static auto last_sample_log_time = std::chrono::high_resolution_clock::now();
                    auto current_sample_time = std::chrono::high_resolution_clock::now();
                    auto time_since_last_sample_log = std::chrono::duration_cast<std::chrono::milliseconds>(current_sample_time - last_sample_log_time).count();

                    if (time_since_last_sample_log > 500) {
                        for (int oi = 0; oi < synth->oscCount; ++oi) {
                            if (std::abs(oscSampleVals[oi]) > 0.05f) {
                                std::cout << "SAMPLE EXPLOSION DETECTED - Osc[" << oi << "]: " << oscSampleVals[oi] << " (Previous: " << last_sample_vals[oi] << ")" << std::endl;
                                last_sample_log_time = current_sample_time;
                                break;
                            }
                        }
                    }

                    // Update previous values
                    for (int oi = 0; oi < synth->oscCount; ++oi) {
                        last_sample_vals[oi] = static_cast<float>(oscSampleVals[oi]);
                    }
                }
            }

            // Smooth gain values towards targets sample by sample
            bool filterParamsChanged = false;
            bool combParamsChanged = false;
            {
                std::lock_guard<std::mutex> lock(synth->mutex);
                double smoothingStep = 1.0 / static_cast<double>(synth->gainSmoothingSamples);

                // Smooth attackTime
                if (synth->currentAttackTime < synth->targetAttackTime) {
                    synth->currentAttackTime += smoothingStep * (synth->targetAttackTime - synth->currentAttackTime);
                    if (std::abs(synth->currentAttackTime - synth->targetAttackTime) < 1e-6)
                        synth->currentAttackTime = synth->targetAttackTime;
                } else if (synth->currentAttackTime > synth->targetAttackTime) {
                    synth->currentAttackTime -= smoothingStep * (synth->currentAttackTime - synth->targetAttackTime);
                    if (std::abs(synth->currentAttackTime - synth->targetAttackTime) < 1e-6)
                        synth->currentAttackTime = synth->targetAttackTime;
                }

                // Smooth decayTime
                if (synth->currentDecayTime < synth->targetDecayTime) {
                    synth->currentDecayTime += smoothingStep * (synth->targetDecayTime - synth->currentDecayTime);
                    if (std::abs(synth->currentDecayTime - synth->targetDecayTime) < 1e-6)
                        synth->currentDecayTime = synth->targetDecayTime;
                } else if (synth->currentDecayTime > synth->targetDecayTime) {
                    synth->currentDecayTime -= smoothingStep * (synth->currentDecayTime - synth->targetDecayTime);
                    if (std::abs(synth->currentDecayTime - synth->targetDecayTime) < 1e-6)
                        synth->currentDecayTime = synth->targetDecayTime;
                }

                // Smooth releaseTime
                if (synth->currentReleaseTime < synth->targetReleaseTime) {
                    synth->currentReleaseTime += smoothingStep * (synth->targetReleaseTime - synth->currentReleaseTime);
                    if (std::abs(synth->currentReleaseTime - synth->targetReleaseTime) < 1e-6)
                        synth->currentReleaseTime = synth->targetReleaseTime;
                } else if (synth->currentReleaseTime > synth->targetReleaseTime) {
                    synth->currentReleaseTime -= smoothingStep * (synth->currentReleaseTime - synth->targetReleaseTime);
                    if (std::abs(synth->currentReleaseTime - synth->targetReleaseTime) < 1e-6)
                        synth->currentReleaseTime = synth->targetReleaseTime;
                }

                // Smooth sustainLevel
                if (synth->currentSustainLevel < synth->targetSustainLevel) {
                    synth->currentSustainLevel += smoothingStep * (synth->targetSustainLevel - synth->currentSustainLevel);
                    if (std::abs(synth->currentSustainLevel - synth->targetSustainLevel) < 1e-6)
                        synth->currentSustainLevel = synth->targetSustainLevel;
                } else if (synth->currentSustainLevel > synth->targetSustainLevel) {
                    synth->currentSustainLevel -= smoothingStep * (synth->currentSustainLevel - synth->targetSustainLevel);
                    if (std::abs(synth->currentSustainLevel - synth->targetSustainLevel) < 1e-6)
                        synth->currentSustainLevel = synth->targetSustainLevel;
                }

                // Update ADSR samples and sustainCalc based on smoothed values
                synth->update_adsr();
            
                // Smooth oscillator gains
                if (synth->oscCount > 0) {
                    for (int i = 0; i < synth->oscCount; ++i) {
                        if (synth->currentOscGain[i] < synth->targetOscGain[i]) {
                            synth->currentOscGain[i] += smoothingStep;
                            if (synth->currentOscGain[i] > synth->targetOscGain[i])
                                synth->currentOscGain[i] = synth->targetOscGain[i];
                        } else if (synth->currentOscGain[i] > synth->targetOscGain[i]) {
                            synth->currentOscGain[i] -= smoothingStep;
                            if (synth->currentOscGain[i] < synth->targetOscGain[i])
                                synth->currentOscGain[i] = synth->targetOscGain[i];
                        }
                    }
                } else {
                    if (synth->currentSineGain < synth->targetSineGain) {
                        synth->currentSineGain += smoothingStep;
                        if (synth->currentSineGain > synth->targetSineGain)
                            synth->currentSineGain = synth->targetSineGain;
                    } else if (synth->currentSineGain > synth->targetSineGain) {
                        synth->currentSineGain -= smoothingStep;
                        if (synth->currentSineGain < synth->targetSineGain)
                            synth->currentSineGain = synth->targetSineGain;
                    }

                    if (synth->currentSampleGain < synth->targetSampleGain) {
                        synth->currentSampleGain += smoothingStep;
                        if (synth->currentSampleGain > synth->targetSampleGain)
                            synth->currentSampleGain = synth->targetSampleGain;
                    } else if (synth->currentSampleGain > synth->targetSampleGain) {
                        synth->currentSampleGain -= smoothingStep;
                        if (synth->currentSampleGain < synth->targetSampleGain)
                            synth->currentSampleGain = synth->targetSampleGain;
                    }
                }

                /* ---------- LFO parameter smoothing ---------- */

                /* Rate : logarithmic smoothing for perceptual naturalness
                 * (reduced aggression to minimise clicks)                  */
                if (std::abs(synth->currentLfoRate - synth->targetLfoRate) > 0.01) {
                    if (synth->currentLfoRate < synth->targetLfoRate) {
                        synth->currentLfoRate *= 1.0 + smoothingStep * 2.0; // was 5.0
                        if (synth->currentLfoRate > synth->targetLfoRate)
                            synth->currentLfoRate = synth->targetLfoRate;
                    } else {
                        synth->currentLfoRate *= 1.0 - smoothingStep * 2.0; // was 5.0
                        if (synth->currentLfoRate < synth->targetLfoRate)
                            synth->currentLfoRate = synth->targetLfoRate;
                    }
                    /* update phase-increment gradually to avoid clicks     */
                    double newIncrement = 2 * PI * synth->currentLfoRate / synth->sample_rate;
                    synth->lfoPhaseIncrement = synth->lfoPhaseIncrement * 0.9 + newIncrement * 0.1;
                }

                /* Depth : linear smoothing */
                if (std::abs(synth->currentLfoDepth - synth->targetLfoDepth) > 0.01) {
                    if (synth->currentLfoDepth < synth->targetLfoDepth) {
                        synth->currentLfoDepth += smoothingStep * (synth->targetLfoDepth - synth->currentLfoDepth);
                        if (synth->currentLfoDepth > synth->targetLfoDepth)
                            synth->currentLfoDepth = synth->targetLfoDepth;
                    } else {
                        synth->currentLfoDepth -= smoothingStep * (synth->currentLfoDepth - synth->targetLfoDepth);
                        if (synth->currentLfoDepth < synth->targetLfoDepth)
                            synth->currentLfoDepth = synth->targetLfoDepth;
                    }
                }

                /* Level : linear smoothing */
                if (std::abs(synth->currentLfoLevel - synth->targetLfoLevel) > 0.01) {
                    if (synth->currentLfoLevel < synth->targetLfoLevel) {
                        synth->currentLfoLevel += smoothingStep * (synth->targetLfoLevel - synth->currentLfoLevel);
                        if (synth->currentLfoLevel > synth->targetLfoLevel)
                            synth->currentLfoLevel = synth->targetLfoLevel;
                    } else {
                        synth->currentLfoLevel -= smoothingStep * (synth->currentLfoLevel - synth->targetLfoLevel);
                        if (synth->currentLfoLevel < synth->targetLfoLevel)
                            synth->currentLfoLevel = synth->targetLfoLevel;
                    }
                }

                /* ---------- Tube driver parameter smoothing ---------- */

                /* Amount: linear smoothing */
                if (std::abs(synth->currentTubeAmount - synth->targetTubeAmount) > 0.01) {
                    if (synth->currentTubeAmount < synth->targetTubeAmount) {
                        synth->currentTubeAmount += smoothingStep * (synth->targetTubeAmount - synth->currentTubeAmount);
                        if (synth->currentTubeAmount > synth->targetTubeAmount)
                            synth->currentTubeAmount = synth->targetTubeAmount;
                    } else {
                        synth->currentTubeAmount -= smoothingStep * (synth->currentTubeAmount - synth->targetTubeAmount);
                        if (synth->currentTubeAmount < synth->targetTubeAmount)
                            synth->currentTubeAmount = synth->targetTubeAmount;
                    }
                }

                /* Min Mix: linear smoothing */
                if (std::abs(synth->currentTubeMinMix - synth->targetTubeMinMix) > 0.01) {
                    if (synth->currentTubeMinMix < synth->targetTubeMinMix) {
                        synth->currentTubeMinMix += smoothingStep * (synth->targetTubeMinMix - synth->currentTubeMinMix);
                        if (synth->currentTubeMinMix > synth->targetTubeMinMix)
                            synth->currentTubeMinMix = synth->targetTubeMinMix;
                    } else {
                        synth->currentTubeMinMix -= smoothingStep * (synth->currentTubeMinMix - synth->targetTubeMinMix);
                        if (synth->currentTubeMinMix < synth->targetTubeMinMix)
                            synth->currentTubeMinMix = synth->targetTubeMinMix;
                    }
                }

                /* Max Mix: linear smoothing */
                if (std::abs(synth->currentTubeMaxMix - synth->targetTubeMaxMix) > 0.01) {
                    if (synth->currentTubeMaxMix < synth->targetTubeMaxMix) {
                        synth->currentTubeMaxMix += smoothingStep * (synth->targetTubeMaxMix - synth->currentTubeMaxMix);
                        if (synth->currentTubeMaxMix > synth->targetTubeMaxMix)
                            synth->currentTubeMaxMix = synth->targetTubeMaxMix;
                    } else {
                        synth->currentTubeMaxMix -= smoothingStep * (synth->currentTubeMaxMix - synth->targetTubeMaxMix);
                        if (synth->currentTubeMaxMix < synth->targetTubeMaxMix)
                            synth->currentTubeMaxMix = synth->targetTubeMaxMix;
                    }
                }

                /* ---------- Bitcrusher parameter smoothing ---------- */

                /* Bit Depth: linear smoothing */
                if (std::abs(synth->currentBitDepth - synth->targetBitDepth) > 0.01) {
                    if (synth->currentBitDepth < synth->targetBitDepth) {
                        synth->currentBitDepth += smoothingStep * (synth->targetBitDepth - synth->currentBitDepth);
                        if (synth->currentBitDepth > synth->targetBitDepth)
                            synth->currentBitDepth = synth->targetBitDepth;
                    } else {
                        synth->currentBitDepth -= smoothingStep * (synth->currentBitDepth - synth->targetBitDepth);
                        if (synth->currentBitDepth < synth->targetBitDepth)
                            synth->currentBitDepth = synth->targetBitDepth;
                    }
                }

                /* Mix: linear smoothing */
                if (std::abs(synth->currentBitMix - synth->targetBitMix) > 0.01) {
                    if (synth->currentBitMix < synth->targetBitMix) {
                        synth->currentBitMix += smoothingStep * (synth->targetBitMix - synth->currentBitMix);
                        if (synth->currentBitMix > synth->targetBitMix)
                            synth->currentBitMix = synth->targetBitMix;
                    } else {
                        synth->currentBitMix -= smoothingStep * (synth->currentBitMix - synth->targetBitMix);
                        if (synth->currentBitMix < synth->targetBitMix)
                            synth->currentBitMix = synth->targetBitMix;
                    }
                }

                // -------------------- Global Filter Parameter Smoothing --------------------
                // Global cutoff offset (linear smoothing)
                if (std::abs(synth->currentGlobalCutoff - synth->targetGlobalCutoff) > 0.01) {
                    if (synth->currentGlobalCutoff < synth->targetGlobalCutoff) {
                        synth->currentGlobalCutoff += smoothingStep * (synth->targetGlobalCutoff - synth->currentGlobalCutoff);
                        if (synth->currentGlobalCutoff > synth->targetGlobalCutoff)
                            synth->currentGlobalCutoff = synth->targetGlobalCutoff;
                    } else {
                        synth->currentGlobalCutoff -= smoothingStep * (synth->currentGlobalCutoff - synth->targetGlobalCutoff);
                        if (synth->currentGlobalCutoff < synth->targetGlobalCutoff)
                            synth->currentGlobalCutoff = synth->targetGlobalCutoff;
                    }
                    filterParamsChanged = true;
                    combParamsChanged = true;  // Global params affect both filters
                }

                // Global resonance offset (linear smoothing)
                if (std::abs(synth->currentGlobalResonance - synth->targetGlobalResonance) > 0.01) {
                    if (synth->currentGlobalResonance < synth->targetGlobalResonance) {
                        synth->currentGlobalResonance += smoothingStep * (synth->targetGlobalResonance - synth->currentGlobalResonance);
                        if (synth->currentGlobalResonance > synth->targetGlobalResonance)
                            synth->currentGlobalResonance = synth->targetGlobalResonance;
                    } else {
                        synth->currentGlobalResonance -= smoothingStep * (synth->currentGlobalResonance - synth->targetGlobalResonance);
                        if (synth->currentGlobalResonance < synth->targetGlobalResonance)
                            synth->currentGlobalResonance = synth->targetGlobalResonance;
                    }
                    filterParamsChanged = true;
                    combParamsChanged = true;  // Global params affect both filters
                }

                // Smooth filter parameters (logarithmic for cutoff, linear for others)
                // Cutoff frequency (logarithmic smoothing for more natural frequency changes)
                if (std::abs(synth->currentFilterCutoff - synth->targetFilterCutoff) > 0.01) {
                    if (synth->currentFilterCutoff < synth->targetFilterCutoff) {
                        synth->currentFilterCutoff *= 1.0 + smoothingStep * 10.0;
                        if (synth->currentFilterCutoff > synth->targetFilterCutoff)
                            synth->currentFilterCutoff = synth->targetFilterCutoff;
                    } else {
                        synth->currentFilterCutoff *= 1.0 - smoothingStep * 10.0;
                        if (synth->currentFilterCutoff < synth->targetFilterCutoff)
                            synth->currentFilterCutoff = synth->targetFilterCutoff;
                    }
                    filterParamsChanged = true;
                }

                // Resonance (linear smoothing)
                if (std::abs(synth->currentFilterResonance - synth->targetFilterResonance) > 0.01) {
                    if (synth->currentFilterResonance < synth->targetFilterResonance) {
                        synth->currentFilterResonance += smoothingStep * (synth->targetFilterResonance - synth->currentFilterResonance);
                        if (synth->currentFilterResonance > synth->targetFilterResonance)
                            synth->currentFilterResonance = synth->targetFilterResonance;
                    } else {
                        synth->currentFilterResonance -= smoothingStep * (synth->currentFilterResonance - synth->targetFilterResonance);
                        if (synth->currentFilterResonance < synth->targetFilterResonance)
                            synth->currentFilterResonance = synth->targetFilterResonance;
                    }
                    filterParamsChanged = true;
                }

                // Drive (linear smoothing)
                if (std::abs(synth->currentFilterDrive - synth->targetFilterDrive) > 0.01) {
                    if (synth->currentFilterDrive < synth->targetFilterDrive) {
                        synth->currentFilterDrive += smoothingStep * (synth->targetFilterDrive - synth->currentFilterDrive);
                        if (synth->currentFilterDrive > synth->targetFilterDrive)
                            synth->currentFilterDrive = synth->targetFilterDrive;
                    } else {
                        synth->currentFilterDrive -= smoothingStep * (synth->currentFilterDrive - synth->targetFilterDrive);
                        if (synth->currentFilterDrive < synth->targetFilterDrive)
                            synth->currentFilterDrive = synth->targetFilterDrive;
                    }
                    filterParamsChanged = true;
                }

                // Key tracking (linear smoothing)
                if (std::abs(synth->currentFilterKeyTrack - synth->targetFilterKeyTrack) > 0.01) {
                    if (synth->currentFilterKeyTrack < synth->targetFilterKeyTrack) {
                        synth->currentFilterKeyTrack += smoothingStep * (synth->targetFilterKeyTrack - synth->currentFilterKeyTrack);
                        if (synth->currentFilterKeyTrack > synth->targetFilterKeyTrack)
                            synth->currentFilterKeyTrack = synth->targetFilterKeyTrack;
                    } else {
                        synth->currentFilterKeyTrack -= smoothingStep * (synth->currentFilterKeyTrack - synth->targetFilterKeyTrack);
                        if (synth->currentFilterKeyTrack < synth->targetFilterKeyTrack)
                            synth->currentFilterKeyTrack = synth->targetFilterKeyTrack;
                    }
                    filterParamsChanged = true;
                }

                // Env mod (linear smoothing) - currently unused but included for completeness
                if (std::abs(synth->currentFilterEnvMod - synth->targetFilterEnvMod) > 0.01) {
                    if (synth->currentFilterEnvMod < synth->targetFilterEnvMod) {
                        synth->currentFilterEnvMod += smoothingStep * (synth->targetFilterEnvMod - synth->currentFilterEnvMod);
                        if (synth->currentFilterEnvMod > synth->targetFilterEnvMod)
                            synth->currentFilterEnvMod = synth->targetFilterEnvMod;
                    } else {
                        synth->currentFilterEnvMod -= smoothingStep * (synth->currentFilterEnvMod - synth->targetFilterEnvMod);
                        if (synth->currentFilterEnvMod < synth->targetFilterEnvMod)
                            synth->currentFilterEnvMod = synth->targetFilterEnvMod;
                    }
                    filterParamsChanged = true;
                }

                /* ---------------- Filter-Envelope Parameter Smoothing ---------------- */
                bool filterEnvParamsChanged = false;

                auto smoothLinear = [&](double &cur, double tgt, double tol = 0.0001) {
                    if (std::abs(cur - tgt) > tol) {
                        if (cur < tgt) {
                            cur += smoothingStep * (tgt - cur);
                            if (cur > tgt) cur = tgt;
                        } else {
                            cur -= smoothingStep * (cur - tgt);
                            if (cur < tgt) cur = tgt;
                        }
                        filterEnvParamsChanged = true;
                    }
                };

                // Attack/Decay/Release logarithmic-ish smoothing by scaling
                auto smoothLog = [&](double &cur, double tgt) {
                    if (std::abs(cur - tgt) > 1e-6) {
                        if (cur < tgt) {
                            cur *= 1.0 + smoothingStep * 5.0;
                            if (cur > tgt) cur = tgt;
                        } else {
                            cur *= 1.0 - smoothingStep * 5.0;
                            if (cur < tgt) cur = tgt;
                        }
                        filterEnvParamsChanged = true;
                    }
                };

                smoothLog(synth->currentFilterEnvAttack, synth->targetFilterEnvAttack);
                smoothLinear(synth->currentFilterEnvDecay, synth->targetFilterEnvDecay, 0.0001);
                smoothLinear(synth->currentFilterEnvSustain, synth->targetFilterEnvSustain, 0.05);
                smoothLinear(synth->currentFilterEnvRelease, synth->targetFilterEnvRelease, 0.0001);

                if (filterEnvParamsChanged) {
                    synth->update_filter_env();
                }

                // Update filter coefficients if parameters changed
                if (filterParamsChanged) {
                    synth->updateFilterCoeffs();
                }
                
                // -------------------- Comb Filter Parameter Smoothing --------------------
                // Cutoff (logarithmic smoothing)
                if (std::abs(synth->currentCombCutoff - synth->targetCombCutoff) > 0.01) {
                    if (synth->currentCombCutoff < synth->targetCombCutoff) {
                        synth->currentCombCutoff *= 1.0 + smoothingStep * 10.0;
                        if (synth->currentCombCutoff > synth->targetCombCutoff)
                            synth->currentCombCutoff = synth->targetCombCutoff;
                    } else {
                        synth->currentCombCutoff *= 1.0 - smoothingStep * 10.0;
                        if (synth->currentCombCutoff < synth->targetCombCutoff)
                            synth->currentCombCutoff = synth->targetCombCutoff;
                    }
                    combParamsChanged = true;
                }
                
                // Resonance (linear smoothing)
                if (std::abs(synth->currentCombResonance - synth->targetCombResonance) > 0.01) {
                    if (synth->currentCombResonance < synth->targetCombResonance) {
                        synth->currentCombResonance += smoothingStep * (synth->targetCombResonance - synth->currentCombResonance);
                        if (synth->currentCombResonance > synth->targetCombResonance)
                            synth->currentCombResonance = synth->targetCombResonance;
                    } else {
                        synth->currentCombResonance -= smoothingStep * (synth->currentCombResonance - synth->targetCombResonance);
                        if (synth->currentCombResonance < synth->targetCombResonance)
                            synth->currentCombResonance = synth->targetCombResonance;
                    }
                    combParamsChanged = true;
                }
                
                // Drive (linear smoothing)
                if (std::abs(synth->currentCombDrive - synth->targetCombDrive) > 0.01) {
                    if (synth->currentCombDrive < synth->targetCombDrive) {
                        synth->currentCombDrive += smoothingStep * (synth->targetCombDrive - synth->currentCombDrive);
                        if (synth->currentCombDrive > synth->targetCombDrive)
                            synth->currentCombDrive = synth->targetCombDrive;
                    } else {
                        synth->currentCombDrive -= smoothingStep * (synth->currentCombDrive - synth->targetCombDrive);
                        if (synth->currentCombDrive < synth->targetCombDrive)
                            synth->currentCombDrive = synth->targetCombDrive;
                    }
                    combParamsChanged = true;
                }
                
                // Key tracking (linear smoothing)
                if (std::abs(synth->currentCombKeyTrack - synth->targetCombKeyTrack) > 0.01) {
                    if (synth->currentCombKeyTrack < synth->targetCombKeyTrack) {
                        synth->currentCombKeyTrack += smoothingStep * (synth->targetCombKeyTrack - synth->currentCombKeyTrack);
                        if (synth->currentCombKeyTrack > synth->targetCombKeyTrack)
                            synth->currentCombKeyTrack = synth->targetCombKeyTrack;
                    } else {
                        synth->currentCombKeyTrack -= smoothingStep * (synth->currentCombKeyTrack - synth->targetCombKeyTrack);
                        if (synth->currentCombKeyTrack < synth->targetCombKeyTrack)
                            synth->currentCombKeyTrack = synth->targetCombKeyTrack;
                    }
                    combParamsChanged = true;
                }
                
                // Env mod (linear smoothing) - currently unused
                if (std::abs(synth->currentCombEnvMod - synth->targetCombEnvMod) > 0.01) {
                    if (synth->currentCombEnvMod < synth->targetCombEnvMod) {
                        synth->currentCombEnvMod += smoothingStep * (synth->targetCombEnvMod - synth->currentCombEnvMod);
                        if (synth->currentCombEnvMod > synth->targetCombEnvMod)
                            synth->currentCombEnvMod = synth->targetCombEnvMod;
                    } else {
                        synth->currentCombEnvMod -= smoothingStep * (synth->currentCombEnvMod - synth->targetCombEnvMod);
                        if (synth->currentCombEnvMod < synth->targetCombEnvMod)
                            synth->currentCombEnvMod = synth->targetCombEnvMod;
                    }
                    combParamsChanged = true;
                }
                
                // Update comb filter parameters if changed
                if (combParamsChanged) {
                    synth->updateCombParams();
                }
            }
            
            // Mix oscillators and apply *pre-envelope* normalisation
            // ------------------------------------------------------------------
            double combined = 0.0;

            if (synth->oscCount > 0) {
                double gainPower = 0.0;
                for (int i = 0; i < synth->oscCount; ++i) {
                    double s = 0.0;
                    switch (synth->oscWaveform[i]) {
                        case 0: s = rawSine;               break; // WAVE_SINE
                        case 1: s = rawSquare;             break; // WAVE_SQUARE
                        case 2: s = rawTriangle;           break; // WAVE_TRIANGLE
                        case 3: s = rawSaw;                break; // WAVE_SAW
                        case 4: s = oscSampleVals[i];      break; // WAVE_SAMPLE (per-osc value)
                        default: s = rawSine;              break;
                    }
                    combined += synth->currentOscGain[i] * s;
                    gainPower += synth->currentOscGain[i] * synth->currentOscGain[i];
                }
                double normalizer = 1.0;
                if (gainPower > 0.0001 && gainPower < 1.0) {
                    normalizer = std::min(synth->gain_normalization_cap, 1.0 / std::sqrt(gainPower));
                }
                combined *= normalizer;
                
            } else {
                double osc1Sample = 0.0;
                switch (synth->osc1Waveform) {
                    case 0: osc1Sample = rawSine;     break;
                    case 1: osc1Sample = rawSquare;   break;
                    case 2: osc1Sample = rawTriangle; break;
                    case 3: osc1Sample = rawSaw;      break;
                    case 4: osc1Sample = sampleValue; break;
                    default: osc1Sample = rawSine;    break;
                }
                
                double osc2Sample = 0.0;
                switch (synth->osc2Waveform) {
                    case 0: osc2Sample = rawSine;     break;
                    case 1: osc2Sample = rawSquare;   break;
                    case 2: osc2Sample = rawTriangle; break;
                    case 3: osc2Sample = rawSaw;      break;
                    case 4: osc2Sample = sampleValue; break;
                    default: osc2Sample = rawSine;    break;
                }

                combined = synth->currentSineGain * osc1Sample
                        + synth->currentSampleGain * osc2Sample;

                double gainPower = synth->currentSineGain * synth->currentSineGain +
                                synth->currentSampleGain * synth->currentSampleGain;
                double normalizer = 1.0;
                if (gainPower > 0.0001 && gainPower < 1.0) {
                    normalizer = std::min(synth->gain_normalization_cap,
                                        1.0 / std::sqrt(gainPower));
                }
                combined *= normalizer;
            }

            // Apply filter to the combined signal and track inputs/outputs for debugging
            double filterInput = combined;
            double filterOutput = synth->processFilter(filterInput);

            combined = filterOutput;

            // Apply comb filter after the lowpass filter
            double combInput = combined;
            double combOutput = synth->processCombFilter(combInput);
            combined = combOutput;

            // Apply tube driver after filters
            double tubeInput = combined;
            double tubeOutput = synth->processTubeDriver(tubeInput);
            combined = tubeOutput;

            // Apply bitcrusher after tube driver
            double bitInput = combined;
            double bitOutput = synth->processBitcrusher(bitInput);
            combined = bitOutput;

            // Smooth normalization factor transition to avoid clicks
            if (synth->noteVolumeNormalizationFactor != synth->targetNoteVolumeNormalizationFactor) {
                // Use a simple linear interpolation for smoothing
                // Adjust the 0.001 value to control smoothing speed (smaller = slower, larger = faster)
                synth->noteVolumeNormalizationFactor += 0.001 * (synth->targetNoteVolumeNormalizationFactor - synth->noteVolumeNormalizationFactor);
                
                // If we're very close to the target, snap to it
                if (std::abs(synth->noteVolumeNormalizationFactor - synth->targetNoteVolumeNormalizationFactor) < 0.001) {
                    synth->noteVolumeNormalizationFactor = synth->targetNoteVolumeNormalizationFactor;
                }
            }

            /* Apply global master volume at the last moment so it scales      *
             * every component (oscillators, filters, effects, etc.).          */
            double outputSample = synth->amplitude * amplitudeMultiplier * combined * 
                     synth->masterVolume * synth->noteVolumeNormalizationFactor;

            // Add this synth's output to the mixed output
            mixedOutput += static_cast<float>(outputSample);

            // Calculate differential from previous sample
            double sampleDiff = outputSample - synth->prevOutputSample;
            double rawDiff = rawSine - synth->prevRawSine;
            
            // Update previous values for next iteration
            synth->prevOutputSample = outputSample;
            synth->prevRawSine = rawSine;

            // ------------------------------------------------------------------
            // Update filter-envelope state so it follows the amplitude envelope
            // ------------------------------------------------------------------
            {
                std::lock_guard<std::mutex> lock(synth->mutex);

                /* --- State-transition logic mirrors amplitude envelope -------- */
                if (synth->envelopeState != synth->filterEnvState) {
                    if (synth->envelopeState == ATTACK && synth->filterEnvState != ATTACK) {
                        synth->filterEnvState = ATTACK;
                        synth->filterEnvSampleCount = 0;
                    } else if (synth->envelopeState == DECAY && synth->filterEnvState != DECAY) {
                        synth->filterEnvState = DECAY;
                        synth->filterEnvSampleCount = synth->filterEnvAttackSamples;
                    } else if (synth->envelopeState == SUSTAIN && synth->filterEnvState != SUSTAIN) {
                        synth->filterEnvState = SUSTAIN;
                    } else if ((synth->envelopeState == HOLD_BEFORE_RELEASE ||
                                synth->envelopeState == RELEASE) &&
                              synth->filterEnvState != RELEASE) {
                        synth->filterEnvState = RELEASE;
                        synth->filterEnvReleaseStartSample = synth->sampleCount;
                        synth->filterEnvReleaseStartLvl = synth->currentFilterEnvLevel;
                    } else if (synth->envelopeState == IDLE && synth->filterEnvState != IDLE) {
                        synth->filterEnvState = IDLE;
                        synth->currentFilterEnvLevel = 0.0;
                    }
                }

                /* --- Per-sample envelope progression -------------------------- */
                switch (synth->filterEnvState) {
                    case ATTACK:
                        if (synth->filterEnvSampleCount < synth->filterEnvAttackSamples) {
                            synth->currentFilterEnvLevel =
                                static_cast<double>(synth->filterEnvSampleCount) /
                                synth->filterEnvAttackSamples;
                            synth->filterEnvSampleCount++;
                        } else {
                            synth->filterEnvState = DECAY;
                            synth->filterEnvSampleCount = synth->filterEnvAttackSamples;
                            synth->currentFilterEnvLevel = 1.0;
                        }
                        break;

                    case DECAY: {
                        unsigned long decayPos =
                            synth->filterEnvSampleCount - synth->filterEnvAttackSamples;
                        if (decayPos < synth->filterEnvDecaySamples) {
                            double decayProgress =
                                static_cast<double>(decayPos) /
                                synth->filterEnvDecaySamples;
                            synth->currentFilterEnvLevel =
                                1.0 +
                                decayProgress * (synth->filterEnvSustainCalc - 1.0);
                            synth->filterEnvSampleCount++;
                        } else {
                            synth->filterEnvState = SUSTAIN;
                            synth->currentFilterEnvLevel = synth->filterEnvSustainCalc;
                        }
                        break;
                    }

                    case SUSTAIN:
                        synth->currentFilterEnvLevel = synth->filterEnvSustainCalc;
                        break;

                    case RELEASE: {
                        unsigned long relPos =
                            synth->sampleCount - synth->filterEnvReleaseStartSample;
                        if (relPos >= synth->filterEnvReleaseSamples) {
                            synth->currentFilterEnvLevel = 0.0;
                            synth->filterEnvState = IDLE;
                        } else {
                            double relProg =
                                static_cast<double>(relPos) /
                                synth->filterEnvReleaseSamples;
                            synth->currentFilterEnvLevel =
                                synth->filterEnvReleaseStartLvl * (1.0 - relProg);
                        }
                        break;
                    }

                    case IDLE:
                    case HOLD_BEFORE_RELEASE:
                    default:
                        synth->currentFilterEnvLevel = 0.0;
                        break;
                }
            }

            // ------------------------------------------------------------------
            // Update LFO & main oscillator phase for next sample
            // ------------------------------------------------------------------
            {
                std::lock_guard<std::mutex> lock(synth->mutex);

                /* ----------- LFO pitch-modulation (DISABLED for diagnosis) ----------- */
                /* Advance LFO phase so it keeps running silently               */
                synth->lfoPhase += synth->lfoPhaseIncrement;
                if (synth->lfoPhase >= 2 * PI) synth->lfoPhase -= 2 * PI;

                /* Skip using LFO value – keep oscillator at base frequency     */
                synth->phaseIncrement = 2 * PI * synth->frequency / synth->sample_rate;

                /* Advance main oscillator phase                                */
                synth->phase += synth->phaseIncrement;
                if (synth->phase >= 2 * PI) synth->phase -= 2 * PI;

                synth->sampleCount++;
            }
        }
        
        // Store the mixed output in the output buffer
        // Apply a simple limiter to prevent clipping if too many synths are active
        if (mixedOutput > 1.0f) mixedOutput = 1.0f;
        if (mixedOutput < -1.0f) mixedOutput = -1.0f;
                // EXPLOSION DETECTOR: Only log when audio jumps above 0.05 (explosive events)
        static float last_output = 0.0f;
        static auto last_log_time = std::chrono::high_resolution_clock::now();
        auto current_time = std::chrono::high_resolution_clock::now();
        auto time_since_last_log = std::chrono::duration_cast<std::chrono::milliseconds>(current_time - last_log_time).count();
        
        // Detect explosive volume increases
        if (mixedOutput > 0.05f && time_since_last_log > 500) {  // Louder than 0.05 and at least 500ms since last log
            std::cout << "EXPLOSION DETECTED - Output: " << mixedOutput << " (Previous: " << last_output << ")" << std::endl;
            last_log_time = current_time;
        }
        
        last_output = mixedOutput;
        
        out[i] = mixedOutput;



        
        
    }

    return paContinue;
}

//------------------------------------------------------------------------------//
//                  External Call Functions                                    //
//----------------------------------------------------------------------------//

// SYNTH MANAGEMENT

// Create a new synthesizer instance and return its ID
extern "C" int create_synth() {
    return synthManager.createSynthesizer();
}

// Delete a synthesizer instance by ID
extern "C" bool delete_synth(int synthId) {
    return synthManager.deleteSynthesizer(synthId);
}

// Check if a synthesizer ID exists
extern "C" bool has_synth(int synthId) {
    return synthManager.hasSynthesizer(synthId);
}

// SYNTH LIFECYCLE

extern "C" void initialize_synth_system() {
    synthManager.initialize();
}

extern "C" void start_synth(int synthId) {
    std::cout << "STREAM RESTART - start_synth called for synthId: " << synthId << std::endl;
    
    // Always stop and restart the stream when adding a new synth
    if (stream) {
        std::cout << "STREAM STOP - Stopping existing PortAudio stream" << std::endl;
        Pa_StopStream(stream);
        std::cout << "STREAM CLOSE - Closing existing PortAudio stream" << std::endl;
        Pa_CloseStream(stream);
        stream = nullptr;
    }
    
    // Now initialize PortAudio again for ALL synths
    std::cout << "STREAM INIT - Reinitializing PortAudio" << std::endl;
    Pa_Initialize();
    std::cout << "STREAM OPEN - Opening new PortAudio stream" << std::endl;
    Pa_OpenDefaultStream(&stream, 0, 1, paFloat32, 44100, 256, paCallback, &synthManager);
    std::cout << "STREAM START - Starting new PortAudio stream" << std::endl;
    Pa_StartStream(stream);
    
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    /* Load the currently configured sample path */
    if (!synth->samplePath.empty()) {
        synth->loadSample(synth->samplePath.c_str());
    }

    // Load per-oscillator sample paths (variable-osc path)
    if (synth->oscCount > 0) {
        for (int i = 0; i < synth->oscCount; ++i) {
            if (!synth->samplePathArr[i].empty()) {
                synth->loadSampleAt(i, synth->samplePathArr[i].c_str());
            }
        }
    }
    
    {
        std::lock_guard<std::mutex> lock(synth->mutex);
        synth->currentSineGain = synth->targetSineGain;
        synth->currentSampleGain = synth->targetSampleGain;
        synth->prevOutputSample = 0.0;
        synth->prevRawSine = 0.0;
        synth->phase = 0.0;
        synth->sampleCount = 0;
        
        // Initialize filter parameters
        synth->currentFilterCutoff = synth->targetFilterCutoff;
        synth->currentFilterResonance = synth->targetFilterResonance;
        synth->currentFilterDrive = synth->targetFilterDrive;
        synth->currentFilterKeyTrack = synth->targetFilterKeyTrack;
        synth->currentFilterEnvMod = synth->targetFilterEnvMod;
        
        // Initialize filter coefficients
        synth->updateFilterCoeffs();
        
        // Initialize comb filter parameters
        synth->currentCombCutoff = synth->targetCombCutoff;
        synth->currentCombResonance = synth->targetCombResonance;
        synth->currentCombDrive = synth->targetCombDrive;
        synth->currentCombKeyTrack = synth->targetCombKeyTrack;
        synth->currentCombEnvMod = synth->targetCombEnvMod;
        
        // Initialize global filter parameters
        synth->currentGlobalCutoff = synth->targetGlobalCutoff;
        synth->currentGlobalResonance = synth->targetGlobalResonance;
        
        // Initialize filter envelope parameters
        synth->currentFilterEnvAttack = synth->targetFilterEnvAttack;
        synth->currentFilterEnvDecay = synth->targetFilterEnvDecay;
        synth->currentFilterEnvSustain = synth->targetFilterEnvSustain;
        synth->currentFilterEnvRelease = synth->targetFilterEnvRelease;
        synth->update_filter_env();
        
        // Initialize comb filter parameters
        synth->updateCombParams();
        
        /* -------------------------- LFO initialisation -------------------------- */
        synth->currentLfoRate = synth->targetLfoRate;
        synth->currentLfoDepth = synth->targetLfoDepth;
        synth->currentLfoLevel = synth->targetLfoLevel;
        synth->lfoPhase = 0.0;
        synth->lfoPhaseIncrement = 2 * PI * synth->currentLfoRate / synth->sample_rate;

        // Initialize tube driver parameters
        synth->currentTubeAmount = synth->targetTubeAmount;
        synth->currentTubeMinMix = synth->targetTubeMinMix;
        synth->currentTubeMaxMix = synth->targetTubeMaxMix;

        // Initialize bitcrusher parameters
        synth->currentBitDepth = synth->targetBitDepth;
        synth->currentBitMix = synth->targetBitMix;

        // Initialize delay line buffer
        synth->combDelayLine.assign(synth->MAX_DELAY_SAMPLES, 0.0);
        synth->combWritePos = 0;
    }

    {
        std::lock_guard<std::mutex> lock(synth->mutex);
        synth->update_adsr();
    }
}
extern "C" void note_on(int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    {
        std::lock_guard<std::mutex> lock(synth->mutex);
        synth->samplePosFloat = 0;  // Reset sample playback
        for (int oi = 0; oi < synth->oscCount; ++oi) {
            synth->samplePosFloatArr[oi] = 0.0f;
        }
        synth->isFirstSampleOfNote = true;
        synth->hasFirstSampleBeenSent = false;
    }
    synth->reset();
}

extern "C" void note_off(int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->noteOn = false;
    synth->releaseHoldCounter = 0;
    synth->envelopeState = HOLD_BEFORE_RELEASE;
    synth->releaseStartLevel = synth->currentAmplitude;
    synth->isFirstSampleOfNote = false;
    synth->hasFirstSampleBeenSent = false;
}

extern "C" void stop_synth(int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    note_off(synthId);
    constexpr unsigned int maxWaitMs = 2000;
    constexpr unsigned int sleepStepMs = 50;
    unsigned int waitedMs = 0;
    while ((synth->envelopeState != IDLE) && waitedMs < maxWaitMs) {
        std::this_thread::sleep_for(std::chrono::milliseconds(sleepStepMs));
        waitedMs += sleepStepMs;
    }
}

extern "C" void shutdown_synth_system() {
    if (stream) {
        Pa_StopStream(stream);
        Pa_CloseStream(stream);
        Pa_Terminate();
        stream = nullptr;
    }
}

// CORE AUDIO PARAMETERS

extern "C" void set_sample_rate(double SAMPLE_RATE, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sample_rate = SAMPLE_RATE;
}

extern "C" void set_frequency(double freq, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->frequency = freq;
    synth->updatePhaseIncrement();
}

extern "C" void set_amplitude(double amplitude, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->amplitude = amplitude;
}

extern "C" void set_gain_smoothing_time_seconds(double GAIN_SMOOTHING_TIME_SECONDS, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->gainSmoothingTimeSeconds = GAIN_SMOOTHING_TIME_SECONDS;
    synth->gainSmoothingSamples = static_cast<unsigned long>(synth->sample_rate * GAIN_SMOOTHING_TIME_SECONDS);
}

extern "C" void set_gain_normalization_cap(double GAIN_NORMALIZATION_CAP, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->gain_normalization_cap = GAIN_NORMALIZATION_CAP;
}

extern "C" void set_master_volume(double volume, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->masterVolume = volume;
}

// SAMPLE SETTINGS

extern "C" void set_sample_base_frequency(double SAMPLE_BASE_FREQUENCY, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sampleBaseFreq = SAMPLE_BASE_FREQUENCY;
    synth->basePhaseIncrement = 2 * PI * SAMPLE_BASE_FREQUENCY / synth->sample_rate;
    synth->updatePhaseIncrement();
}

extern "C" void set_sample_loop(unsigned int start, unsigned int end, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->loopActive = true;
    synth->sampleLoopStart = std::min(start, static_cast<unsigned int>(synth->sampleBuffer.size()));
    synth->sampleLoopEnd = std::min(end, static_cast<unsigned int>(synth->sampleBuffer.size()));
    if (synth->sampleLoopEnd <= synth->sampleLoopStart) synth->sampleLoopEnd = synth->sampleBuffer.size();
    // Mirror to per-osc buffers
    for (int i = 0; i < synth->oscCount; ++i) {
        if (!synth->sampleBuffers[i].empty()) {
            synth->sampleLoopStartArr[i] = std::min(start, static_cast<unsigned int>(synth->sampleBuffers[i].size()));
            unsigned int endClamped = std::min(end, static_cast<unsigned int>(synth->sampleBuffers[i].size()));
            synth->sampleLoopEndArr[i] = (endClamped <= synth->sampleLoopStartArr[i])
                ? static_cast<unsigned int>(synth->sampleBuffers[i].size())
                : endClamped;
        }
    }
}

extern "C" void set_sample_loop_start_percentage(double SAMPLE_LOOP_START_PERCENTAGE, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sampleLoopStartPercentage = SAMPLE_LOOP_START_PERCENTAGE;
    if (!synth->sampleBuffer.empty()) {
        synth->sampleLoopStart = static_cast<unsigned int>(SAMPLE_LOOP_START_PERCENTAGE * synth->sampleBuffer.size());
    }
}

extern "C" void set_sample_loop_end_percentage(double SAMPLE_LOOP_END_PERCENTAGE, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sampleLoopEndPercentage = SAMPLE_LOOP_END_PERCENTAGE;
    if (!synth->sampleBuffer.empty()) {
        synth->sampleLoopEnd = static_cast<unsigned int>(SAMPLE_LOOP_END_PERCENTAGE * synth->sampleBuffer.size());
    }
}

extern "C" void set_fade_samples(double FADE_SAMPLES, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->fade_samples = FADE_SAMPLES;
}

extern "C" void set_fade_in_time(double FADE_IN_TIME, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->fadeInTime = FADE_IN_TIME;
}

extern "C" void set_loop_fade_samples(unsigned int LOOP_FADE_SAMPLES, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->loop_fade_samples = LOOP_FADE_SAMPLES;
}

// OSCILLATOR SETTINGS

extern "C" void set_sine_gain(double gain, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetSineGain = gain;
}

extern "C" void set_sample_gain(double gain, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetSampleGain = gain;
}

extern "C" void set_osc1_waveform(int type, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    std::lock_guard<std::mutex> lock(synth->mutex);
    if (type < 0) type = 0;
    if (type > 4) type = 4;
    synth->osc1Waveform = type;
}

extern "C" void set_osc2_waveform(int type, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    std::lock_guard<std::mutex> lock(synth->mutex);
    if (type < 0) type = 0;
    if (type > 4) type = 4;
    synth->osc2Waveform = type;
}

extern "C" void set_osc_count(int count, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    std::lock_guard<std::mutex> lock(synth->mutex);
    if (count < 0) count = 0;
    if (count > MAX_OSC) count = MAX_OSC;
    synth->oscCount = count;
}

extern "C" void set_osc_waveform_at(int index, int type, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    std::lock_guard<std::mutex> lock(synth->mutex);
    if (index < 0 || index >= MAX_OSC) return;
    if (type < 0) type = 0;
    if (type > 4) type = 4;
    synth->oscWaveform[index] = type;
}

extern "C" void set_osc_gain_at(double gain, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    std::lock_guard<std::mutex> lock(synth->mutex);
    if (index < 0 || index >= MAX_OSC) return;
    synth->targetOscGain[index] = gain;
}

extern "C" void set_fm_depth(double depth, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->fmDepth = depth * PI;  // scale 0-1 input to 0 - π radians
}

// ADSR SETTINGS

extern "C" void set_attack(double attackSeconds, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetAttackTime = attackSeconds;
}

extern "C" void set_decay(double decaySeconds, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetDecayTime = decaySeconds;
}

extern "C" void set_release(double releaseSeconds, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetReleaseTime = releaseSeconds;
}

extern "C" void set_sustain_level(double levelDb, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    /* Keep smoothing intact – only set the target; smoothing engine
       will bring currentSustainLevel and sustainCalc to this target.   */
    synth->targetSustainLevel = levelDb;
}

// FILTER 1 SETTINGS

extern "C" void set_filter_cutoff(double cutoff, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterCutoff = cutoff;
}

extern "C" void set_filter_resonance(double resonance, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterResonance = resonance;
}

extern "C" void set_filter_env_mod(double envMod, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterEnvMod = envMod;
}

extern "C" void set_filter_drive(double drive, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterDrive = drive;
}

extern "C" void set_filter_key_tracking(double tracking, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterKeyTrack = tracking;
}

extern "C" void set_filter_drive_scaling(double FILTER_DRIVE_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->filter_drive_scaling = FILTER_DRIVE_SCALING;
}

extern "C" void set_filter_env_mod_scaling(double FILTER_ENV_MOD_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->filter_env_mod_scaling = FILTER_ENV_MOD_SCALING;
}

// Filter 2 Settings

extern "C" void set_comb_cutoff(double cutoff, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetCombCutoff = cutoff;
}

extern "C" void set_comb_resonance(double resonance, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetCombResonance = resonance;
}

extern "C" void set_comb_env_mod(double envMod, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetCombEnvMod = envMod;
}

extern "C" void set_comb_drive(double drive, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetCombDrive = drive;
}

extern "C" void set_comb_key_tracking(double tracking, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetCombKeyTrack = tracking;
}

// ACTUAL LIMITS
extern "C" void set_comb_min_delay_ms(double COMB_MIN_DELAY_MS, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_min_delay_ms = COMB_MIN_DELAY_MS;
}

extern "C" void set_comb_max_delay_ms(double COMB_MAX_DELAY_MS, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_max_delay_ms = COMB_MAX_DELAY_MS;
}

extern "C" void set_comb_feedback_max(double COMB_FEEDBACK_MAX, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_feedback_max = COMB_FEEDBACK_MAX;
}

extern "C" void set_comb_min_resonance(double COMB_MIN_RESONANCE, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_min_resonance = COMB_MIN_RESONANCE;
}

extern "C" void set_comb_feedback_limiter(double COMB_FEEDBACK_LIMITER, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_feedback_limiter = COMB_FEEDBACK_LIMITER;
}

// SCALING
extern "C" void set_comb_feedback_scaling(double COMB_FEEDBACK_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_feedback_scaling = COMB_FEEDBACK_SCALING;
}

extern "C" void set_comb_env_mod_scaling(double COMB_ENV_MOD_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_env_mod_scaling = COMB_ENV_MOD_SCALING;
}

extern "C" void set_comb_limiter_strength(double COMB_LIMITER_STRENGTH, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_limiter_strength = COMB_LIMITER_STRENGTH;
}

extern "C" void set_comb_filter_drive_scaling(double COMB_FILTER_DRIVE_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->comb_filter_drive_scaling = COMB_FILTER_DRIVE_SCALING;
}

// FILTER ENVELOPE SETTINGS

extern "C" void set_filter_env_attack(double attackSec, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterEnvAttack = std::max(0.0001, attackSec);
}

extern "C" void set_filter_env_decay(double decaySec, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterEnvDecay = std::max(0.0001, decaySec);
}

extern "C" void set_filter_env_sustain(double sustainDb, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterEnvSustain = sustainDb;
}

extern "C" void set_filter_env_release(double releaseSec, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetFilterEnvRelease = std::max(0.0001, releaseSec);
}

// GLOBAL FILTER SETTERS

extern "C" void set_global_cutoff(double cutoffHz, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetGlobalCutoff = cutoffHz;
}

extern "C" void set_global_resonance(double resonanceQ, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetGlobalResonance = resonanceQ;
}

// LFO SETTINGS

extern "C" void set_lfo_rate(double rate, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetLfoRate = rate;
}

extern "C" void set_lfo_depth(double depth, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetLfoDepth = depth;
}

extern "C" void set_lfo_level(double level, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetLfoLevel = level;
}

// BITCRUSHER SETTINGS

extern "C" void set_bit_depth(double depthBits, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    /* Clamp to 1-16 bits */
    synth->targetBitDepth = std::min(16.0, std::max(1.0, depthBits));
}

extern "C" void set_bit_mix(double mixPercent, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetBitMix = std::clamp(mixPercent, 0.0, 100.0);
}

// ACTUAL LIMITS
extern "C" void set_bitcrusher_min_depth(double BITCRUSHER_MIN_DEPTH, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->bitcrusher_min_depth = BITCRUSHER_MIN_DEPTH;
}

extern "C" void set_bitcrusher_max_depth(double BITCRUSHER_MAX_DEPTH, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->bitcrusher_max_depth = BITCRUSHER_MAX_DEPTH;
}

extern "C" void set_bitcrusher_bypass_threshold(double BITCRUSHER_BYPASS_THRESHOLD, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->bitcrusher_bypass_threshold = BITCRUSHER_BYPASS_THRESHOLD;
}

extern "C" void set_bitcrusher_mix_scale_threshold(double BITCRUSHER_MIX_SCALE_THRESHOLD, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->bitcrusher_mix_scale_threshold = BITCRUSHER_MIX_SCALE_THRESHOLD;
}

extern "C" void set_bitcrusher_dither_threshold(double BITCRUSHER_DITHER_THRESHOLD, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->bitcrusher_dither_threshold = BITCRUSHER_DITHER_THRESHOLD;
}

// TUBE DRIVER SETTINGS

extern "C" void set_tube_amount(double amount, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetTubeAmount = amount;
}

extern "C" void set_tube_min_mix(double minMix, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetTubeMinMix = minMix;
}

extern "C" void set_tube_max_mix(double maxMix, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->targetTubeMaxMix = maxMix;
}

extern "C" void set_tube_drive_scaling(double TUBE_DRIVE_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->tube_drive_scaling = TUBE_DRIVE_SCALING;
}

extern "C" void set_tube_intensity_scaling(double TUBE_INTENSITY_SCALING, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->tube_intensity_scaling = TUBE_INTENSITY_SCALING;
}

extern "C" void set_tube_quintic_coeff(double TUBE_QUINTIC_COEFF, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->tube_quintic_coeff = TUBE_QUINTIC_COEFF;
}

extern "C" void set_tube_cubic_coeff(double TUBE_CUBIC_COEFF, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->tube_cubic_coeff = TUBE_CUBIC_COEFF;
}

extern "C" void set_tube_bypass_threshold(double TUBE_BYPASS_THRESHOLD, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->tube_bypass_threshold = TUBE_BYPASS_THRESHOLD;
}

extern "C" double get_master_volume(int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return 0.0;
    
    return synth->masterVolume;
}

// EQ SETTINGS

extern "C" void set_highshelf_eq(double freq_hz, double gain_db, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->calculate_highshelf_coefficients(freq_hz, gain_db, synth->sample_rate);
}

extern "C" void set_peaking_eq(double freq_hz, double gain_db, double Q, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->calculate_peaking_eq_coefficients(freq_hz, gain_db, Q, synth->sample_rate);
}

extern "C" void set_lowshelf_eq(double freq_hz, double gain_db, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->calculate_lowshelf_coefficients(freq_hz, gain_db, synth->sample_rate);
}

// Add these new functions at the end of the file, after the last extern "C" function

extern "C" void set_sample_loop_start_percentage_at(double percentage, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    if (index < 0 || index >= MAX_OSC) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sampleLoopStartPercentageArr[index] = percentage;
    
    // Update loop points if sample buffer exists
    if (!synth->sampleBuffers[index].empty()) {
        synth->sampleLoopStartArr[index] = static_cast<unsigned int>(percentage * synth->sampleBuffers[index].size());
    }
}

extern "C" void set_sample_loop_end_percentage_at(double percentage, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    if (index < 0 || index >= MAX_OSC) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sampleLoopEndPercentageArr[index] = percentage;
    
    // Update loop points if sample buffer exists
    if (!synth->sampleBuffers[index].empty()) {
        synth->sampleLoopEndArr[index] = static_cast<unsigned int>(percentage * synth->sampleBuffers[index].size());
    }
}

extern "C" void set_sample_base_frequency_at(double frequency, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    if (index < 0 || index >= MAX_OSC) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->sampleBaseFreqArr[index] = frequency;
}

extern "C" void set_highpass_cutoff_at(double cutoff, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    if (index < 0 || index >= MAX_OSC) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->highpassCutoffArr[index] = cutoff;
}

extern "C" void set_highpass_enabled_at(bool enabled, int index, int synthId) {
    Synthesizer* synth = synthManager.getSynthesizer(synthId);
    if (!synth) return;
    if (index < 0 || index >= MAX_OSC) return;
    
    std::lock_guard<std::mutex> lock(synth->mutex);
    synth->highpassEnabledArr[index] = enabled;
}