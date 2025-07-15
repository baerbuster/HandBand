

// Undo Flag



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

// Third-party headers
#include <portaudio.h>
#include <sndfile.h>


//------------------------------------------------------------------------------//
//                  CORE DECLARATIONS AND DATA STRUCTURES                      //
//----------------------------------------------------------------------------//

// Constants
constexpr double PI = 3.14159265358979323846;

// Global Parameters – Sample / Loop
double sample_rate                = 44100;
double fade_samples              = 256;
unsigned int loop_fade_samples   = 256;
unsigned int fadeInTime          = 10; // ms
double sampleLoopStartPercentage = 0.01;
double sampleLoopEndPercentage   = 1.0;

// Global Parameters – Gain & Normalization
double gain_normalization_cap = 3.0;

// Global Parameters – Filter
double filter_drive_scaling   = 4.0;
double filter_env_mod_scaling = 1.5;

// Global Parameters – Comb Filter
double comb_filter_drive_scaling = 4.0;
double comb_limiter_strength     = 0.8;
double comb_feedback_limiter     = 0.95;
double comb_min_delay_ms         = 1.0;   // ms
double comb_max_delay_ms         = 50.0;  // ms
double comb_feedback_max         = 0.95;
double comb_feedback_scaling     = 15.0;
double comb_env_mod_scaling      = 1.5;   // octaves
double comb_min_resonance        = 0.1;

// Global Parameters – Tube Saturation
double tube_bypass_threshold   = 0.01;
double tube_drive_scaling     = 3.0;
double tube_cubic_coeff       = 0.33;
double tube_quintic_coeff     = 0.05;
double tube_intensity_scaling = 2.0;

// Global Parameters – Bitcrusher
double bitcrusher_bypass_threshold     = 0.01;
double bitcrusher_max_depth            = 16.0;
double bitcrusher_min_depth            = 1.0;
double bitcrusher_dither_threshold     = 8.0;
double bitcrusher_mix_scale_threshold  = 4.0;

// Sample Path
std::string samplePath =
    "/Users/busterbaer/Desktop/Programmable Song/ProgrammableLoop2/ProgrammableLoop2BassSynthOscillatorSample.wav";

// Enums and Structs
enum EnvelopeState {
    ATTACK, DECAY, SUSTAIN, HOLD_BEFORE_RELEASE, RELEASE, IDLE
};

const char* envelopeStateToStr(EnvelopeState state);

struct SineData;


//------------------------------------------------------------------------------//
//                               AUDIO UTILITIES                               //
//----------------------------------------------------------------------------//

// Declare array to hold sample data
std::vector<float> squareSample;
// Track playback position
float samplePosFloat = 0;

// Load in sample
bool loadSquareSample(const char* filename) {
    SF_INFO sfinfo; // Declare space for metadata about sample
    SNDFILE* file = sf_open(filename, SFM_READ, &sfinfo); // Open sample file
    if (!file) return false; // Check if succesful
    
    squareSample.resize(sfinfo.frames); // Correct size of array
    sf_readf_float(file, squareSample.data(), sfinfo.frames); // Read file into squareSample
    sf_close(file); // Close file
    samplePosFloat = 0; // Playback position to the beginning

    // Apply fade-in to first 256 samples (or fewer if sample is short)
    unsigned int fadeInSamples = sample_rate / fadeInTime;
    if (fadeInSamples > squareSample.size()) fadeInSamples = static_cast<unsigned int>(squareSample.size());
    for (unsigned int i = 0; i < fadeInSamples; ++i) {
        float fadeFactor = static_cast<float>(i) / fadeInSamples;
        squareSample[i] *= fadeFactor;
    }
    
    return true;
}

unsigned int sampleLoopStart = sampleLoopStartPercentage * squareSample.size();
unsigned int sampleLoopEnd = sampleLoopEndPercentage * squareSample.size();
bool loopActive = false;
