#pragma once

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

// Third-party headers
#include <portaudio.h>
#include <sndfile.h>

// Constants
constexpr double PI = 3.14159265358979323846;

// Envelope state enum
enum EnvelopeState {
    ATTACK, DECAY, SUSTAIN, HOLD_BEFORE_RELEASE, RELEASE, IDLE
};

const char* envelopeStateToStr(EnvelopeState state);

class Synthesizer {
public:
    // Constructor and destructor
    Synthesizer(int id);
    ~Synthesizer();

    // Unique identifier for this synthesizer instance
    int synthId;

    // ====================================================================== //
    // 1.  CORE STATE AND SYNCHRONISATION DECLARATION                         //
    // ====================================================================== //

    std::mutex mutex;
    double phase = 0.0;
    double frequency = 440.0;
    double phaseIncrement = 2 * PI * frequency / 44100.0;
    double sampleBaseFreq = 440.0;
    double basePhaseIncrement = 2 * PI * sampleBaseFreq / 44100.0;
    double timeScalingFactor = 1.0;
    unsigned long sampleCount = 0;

    // Sample-related state (previously global)
    std::vector<float> squareSample;
    float samplePosFloat = 0;
    unsigned int sampleLoopStart = 0;
    unsigned int sampleLoopEnd = 0;
    bool loopActive = false;
    std::string samplePath;

    // Global parameters (previously global variables)
    double sample_rate = 44100.0;
    double fade_samples = 256.0;
    unsigned int loop_fade_samples = 256;
    unsigned int fadeInTime = 10; // ms
    double sampleLoopStartPercentage = 0.01;
    double sampleLoopEndPercentage = 1.0;
    double gain_normalization_cap = 3.0;
    double filter_drive_scaling = 4.0;
    double filter_env_mod_scaling = 1.5;
    double comb_filter_drive_scaling = 4.0;
    double comb_limiter_strength = 0.8;
    double comb_feedback_limiter = 0.95;
    double comb_min_delay_ms = 1.0;
    double comb_max_delay_ms = 50.0;
    double comb_feedback_max = 0.95;
    double comb_feedback_scaling = 15.0;
    double comb_env_mod_scaling = 1.5;
    double comb_min_resonance = 0.1;
    double tube_bypass_threshold = 0.01;
    double tube_drive_scaling = 3.0;
    double tube_cubic_coeff = 0.33;
    double tube_quintic_coeff = 0.05;
    double tube_intensity_scaling = 2.0;
    double bitcrusher_bypass_threshold = 0.01;
    double bitcrusher_max_depth = 16.0;
    double bitcrusher_min_depth = 1.0;
    double bitcrusher_dither_threshold = 8.0;
    double bitcrusher_mix_scale_threshold = 4.0;

    // ====================================================================== //
    // 2.  ADSR ENVELOPE PARAMETERS & STATE                                   //
    // ====================================================================== //

    double attackTime = 0.001; // Attack Time in ms
    unsigned long attackSamples = static_cast<unsigned long>(sample_rate/1000 * attackTime);
    double decayTime = 3158; // Decay Time in ms
    unsigned long decaySamples = static_cast<unsigned long>(sample_rate/1000 * decayTime);
    double releaseTime = 330; // Release Time in ms
    unsigned long releaseSamples = static_cast<unsigned long>(sample_rate/1000 * releaseTime);

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
    unsigned long samplesSinceStateChange = fade_samples;

    // ====================================================================== //
    // 3.  OSCILLATOR SETTINGS & MIXING DECLARATIONS                          //
    // ====================================================================== //

    double prevOutputSample = 0.0;
    double prevRawSine = 0.0;

    double sineGain = 1.0;
    double squareGain = 1.0;

    double targetSineGain = 1.0;
    double targetSquareGain = 1.0;

    double currentSineGain = 1.0;
    double currentSquareGain = 1.0;

    double gainSmoothingTimeSeconds = 0.5;
    unsigned long gainSmoothingSamples = static_cast<unsigned long>(sample_rate * gainSmoothingTimeSeconds);

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
    int MAX_DELAY_SAMPLES = static_cast<int>(sample_rate / 20);
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
    unsigned long filterEnvAttackSamples = static_cast<unsigned long>(sample_rate * 0.001);
    unsigned long filterEnvDecaySamples = static_cast<unsigned long>(sample_rate * 0.50);
    unsigned long filterEnvReleaseSamples = static_cast<unsigned long>(sample_rate * 0.50);
    double filterEnvSustainCalc = std::pow(10.0, currentFilterEnvSustain / 20.0);
    unsigned long filterEnvReleaseStartSample = 0;
    double filterEnvReleaseStartLvl = 0.0;
    double currentFilterEnvLevel = 0.0;

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
    double lfoPhaseIncrement = 2 * PI * currentLfoRate / sample_rate;

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
    // 10. PUBLIC METHODS                                                     //
    // ====================================================================== //

    // Core lifecycle methods
    bool initialize();
    void start();
    void stop();
    void reset();
    
    // Sample loading
    bool loadSample(const char* filename);
    
    // Note control
    void noteOn();
    void noteOff();
    
    // Parameter setters
    void setFrequency(double freq);
    void setSampleRate(double sampleRate);
    void setAmplitude(double amplitude);
    void setMasterVolume(double volume);
    
    // ADSR settings
    void setAttack(double attackSeconds);
    void setDecay(double decaySeconds);
    void setRelease(double releaseSeconds);
    void setSustainLevel(double levelDb);
    
    // Sample settings
    void setSampleBaseFrequency(double frequency);
    void setSampleLoop(unsigned int start, unsigned int end);
    void setSampleLoopStartPercentage(double percentage);
    void setSampleLoopEndPercentage(double percentage);
    
    // Oscillator settings
    void setSineGain(double gain);
    void setSquareGain(double gain);
    void setFmDepth(double depth);
    
    // Filter settings
    void setFilterCutoff(double cutoff);
    void setFilterResonance(double resonance);
    void setFilterEnvMod(double envMod);
    void setFilterDrive(double drive);
    void setFilterKeyTracking(double tracking);
    
    // Comb filter settings
    void setCombCutoff(double cutoff);
    void setCombResonance(double resonance);
    void setCombEnvMod(double envMod);
    void setCombDrive(double drive);
    void setCombKeyTracking(double tracking);
    
    // Global filter settings
    void setGlobalCutoff(double cutoffHz);
    void setGlobalResonance(double resonanceQ);
    
    // Filter envelope settings
    void setFilterEnvAttack(double attackSec);
    void setFilterEnvDecay(double decaySec);
    void setFilterEnvSustain(double sustainDb);
    void setFilterEnvRelease(double releaseSec);
    
    // LFO settings
    void setLfoRate(double rate);
    void setLfoDepth(double depth);
    void setLfoLevel(double level);
    
    // Bitcrusher settings
    void setBitDepth(double depthBits);
    void setBitMix(double mixPercent);
    
    // Tube driver settings
    void setTubeAmount(double amount);
    void setTubeMinMix(double minMix);
    void setTubeMaxMix(double maxMix);
    
    // Configuration settings
    void setGainSmoothingTimeSeconds(double seconds);
    void setGainNormalizationCap(double cap);
    void setFadeSamples(double samples);
    void setFadeInTime(double ms);
    void setLoopFadeSamples(unsigned int samples);
    void setFilterDriveScaling(double scaling);
    void setFilterEnvModScaling(double scaling);
    void setCombLimiterStrength(double strength);
    void setCombMinDelayMs(double ms);
    void setCombMaxDelayMs(double ms);
    void setCombFeedbackMax(double max);
    void setCombFeedbackScaling(double scaling);
    void setCombFeedbackLimiter(double limiter);
    void setCombMinResonance(double resonance);
    void setCombEnvModScaling(double scaling);
    void setCombFilterDriveScaling(double scaling);
    void setBitcrusherMinDepth(double depth);
    void setBitcrusherMaxDepth(double depth);
    void setBitcrusherBypassThreshold(double threshold);
    void setBitcrusherMixScaleThreshold(double threshold);
    void setBitcrusherDitherThreshold(double threshold);
    void setTubeDriveScaling(double scaling);
    void setTubeIntensityScaling(double scaling);
    void setTubeQuinticCoeff(double coeff);
    void setTubeCubicCoeff(double coeff);
    void setTubeBypassThreshold(double threshold);

    // ====================================================================== //
    // 11. SIGNAL PROCESSING METHODS                                          //
    // ====================================================================== //
    
    // Process a single sample through the synthesizer
    float processSample();
    
    // Update phase increment based on frequency
    void updatePhaseIncrement();
    
    // Update ADSR envelope parameters
    void update_adsr();
    
    // Update filter envelope parameters
    void update_filter_env();
    
    // Update filter coefficients
    void updateFilterCoeffs();
    
    // Update comb filter parameters
    void updateCombParams();
    
    // Filter processing methods
    inline double processFilter(double inSample);
    inline double processCombFilter(double inSample);
    inline double processTubeDriver(double inSample);
    inline double processBitcrusher(double inSample);
    
    // Filter calculation utilities
    inline double calculateEffectiveCutoff();
    inline double calculateEffectiveResonance();
    inline void calculateBiquadCoefficients(double cutoffHz, double resonanceQ);
    inline double calculateCombEffectiveCutoff();
    inline double calculateCombEffectiveResonance();
    inline void calculateCombDelayAndFeedback(double cutoffHz, double resonanceQ);

    // Named constants (avoid magic numbers)
    static constexpr double MIN_CUTOFF_HZ = 20.0;
    static constexpr double MAX_CUTOFF_HZ = 20000.0;
    static constexpr double MIN_RESO_Q = 0.25;
    static constexpr double MAX_RESO_Q = 40.0;
};
