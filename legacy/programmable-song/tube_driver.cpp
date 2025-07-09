// Tube driver addition for synthlib.cpp
// Add these components to the appropriate sections of synthlib.cpp

// 1. Add these struct members inside SineData
/* -------------------------- TUBE DRIVER PARAMETERS ----------------------- */
/* target values set by UI */
double targetTubeAmount     = 0.0;   // % (0-100)
double targetTubePreGain    = 1.0;   // (0.1-10.0)
double targetTubePostGain   = 1.0;   // (0.1-10.0)
double targetTubeAsymmetry  = 0.5;   // (0.0-1.0)

/* smoothed / realtime values */
double currentTubeAmount    = 0.0;
double currentTubePreGain   = 1.0;
double currentTubePostGain  = 1.0;
double currentTubeAsymmetry = 0.5;

// 2. Add this tube driver processing function inside SineData
/* ------------------------------------------------------------------ */
/*  Tube driver processing (warm distortion)                          */
/* ------------------------------------------------------------------ */
inline double processTubeDriver(double inSample) {
    // Early return if tube amount is zero (bypass)
    if (currentTubeAmount <= 0.001) return inSample;
    
    // Apply tube amount (mix control between 0-100%)
    const double mix = currentTubeAmount / 100.0;
    
    // Apply pre-gain (input drive)
    double x = inSample * currentTubePreGain;
    
    // Apply asymmetric soft clipping that emulates tube behavior
    // Positive side of the waveform clips differently than negative
    double y;
    if (x > 0.0) {
        y = 1.0 - std::exp(-x);  // Softer positive clipping
    } else {
        // Adjustable asymmetry for the negative portion
        double clipFactor = 1.0 + currentTubeAsymmetry * 3.0;
        y = -1.0 + std::exp(x * clipFactor);  // Harder negative clipping
    }
    
    // Apply post-gain (output level)
    y *= currentTubePostGain;
    
    // Mix dry/wet
    return (1.0 - mix) * inSample + mix * y;
}

// 3. Add these API functions at the end of the file with other extern "C" functions
// Tube-driver setters
extern "C" void set_tube_amount(double v)              { std::lock_guard<std::mutex> l(data.mutex); data.targetTubeAmount     = v; }
extern "C" void set_tube_pre_gain(double v)            { std::lock_guard<std::mutex> l(data.mutex); data.targetTubePreGain    = v; }
extern "C" void set_tube_post_gain(double v)           { std::lock_guard<std::mutex> l(data.mutex); data.targetTubePostGain   = v; }
extern "C" void set_tube_asymmetry(double v)           { std::lock_guard<std::mutex> l(data.mutex); data.targetTubeAsymmetry = std::clamp(v, 0.0, 1.0); }

// 4. Add this initialization code in start_synth() function
// Initialize tube driver parameters
data.currentTubeAmount = data.targetTubeAmount;
data.currentTubePreGain = data.targetTubePreGain;
data.currentTubePostGain = data.targetTubePostGain;
data.currentTubeAsymmetry = data.targetTubeAsymmetry;

// 5. Add this parameter smoothing code in the audio callback where other parameters are smoothed
// -------------------- Tube Driver Parameter Smoothing --------------------
bool tubeParamsChanged = false;

// Tube amount (linear smoothing)
if (std::abs(d->currentTubeAmount - d->targetTubeAmount) > 0.01) {
    if (d->currentTubeAmount < d->targetTubeAmount) {
        d->currentTubeAmount += smoothingStep * (d->targetTubeAmount - d->currentTubeAmount);
        if (d->currentTubeAmount > d->targetTubeAmount)
            d->currentTubeAmount = d->targetTubeAmount;
    } else {
        d->currentTubeAmount -= smoothingStep * (d->currentTubeAmount - d->targetTubeAmount);
        if (d->currentTubeAmount < d->targetTubeAmount)
            d->currentTubeAmount = d->targetTubeAmount;
    }
    tubeParamsChanged = true;
}

// Tube pre-gain (logarithmic smoothing)
if (std::abs(d->currentTubePreGain - d->targetTubePreGain) > 0.01) {
    if (d->currentTubePreGain < d->targetTubePreGain) {
        d->currentTubePreGain *= 1.0 + smoothingStep * 5.0;
        if (d->currentTubePreGain > d->targetTubePreGain)
            d->currentTubePreGain = d->targetTubePreGain;
    } else {
        d->currentTubePreGain *= 1.0 - smoothingStep * 5.0;
        if (d->currentTubePreGain < d->targetTubePreGain)
            d->currentTubePreGain = d->targetTubePreGain;
    }
    tubeParamsChanged = true;
}

// Tube post-gain (logarithmic smoothing)
if (std::abs(d->currentTubePostGain - d->targetTubePostGain) > 0.01) {
    if (d->currentTubePostGain < d->targetTubePostGain) {
        d->currentTubePostGain *= 1.0 + smoothingStep * 5.0;
        if (d->currentTubePostGain > d->targetTubePostGain)
            d->currentTubePostGain = d->targetTubePostGain;
    } else {
        d->currentTubePostGain *= 1.0 - smoothingStep * 5.0;
        if (d->currentTubePostGain < d->targetTubePostGain)
            d->currentTubePostGain = d->targetTubePostGain;
    }
    tubeParamsChanged = true;
}

// Tube asymmetry (linear smoothing)
if (std::abs(d->currentTubeAsymmetry - d->targetTubeAsymmetry) > 0.01) {
    if (d->currentTubeAsymmetry < d->targetTubeAsymmetry) {
        d->currentTubeAsymmetry += smoothingStep * (d->targetTubeAsymmetry - d->currentTubeAsymmetry);
        if (d->currentTubeAsymmetry > d->targetTubeAsymmetry)
            d->currentTubeAsymmetry = d->targetTubeAsymmetry;
    } else {
        d->currentTubeAsymmetry -= smoothingStep * (d->currentTubeAsymmetry - d->targetTubeAsymmetry);
        if (d->currentTubeAsymmetry < d->targetTubeAsymmetry)
            d->currentTubeAsymmetry = d->targetTubeAsymmetry;
    }
    tubeParamsChanged = true;
}

// 6. Add this processing code in the audio signal path after the comb filter processing
// Apply tube driver for warmth
double tubeInput = combined;
double tubeOutput = d->processTubeDriver(tubeInput);
combined = tubeOutput;
