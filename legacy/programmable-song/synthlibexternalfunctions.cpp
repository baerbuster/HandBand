

//------------------------------------------------------------------------------//
//                  External Call Functions                                    //
//----------------------------------------------------------------------------//

// SYNTH LIFECYCLE

extern "C" void start_synth() {
    Pa_Initialize();
    Pa_OpenDefaultStream(&stream, 0, 1, paFloat32, sample_rate, 256, paCallback, &data);
    /* Load the currently configured sample path */
    loadSquareSample(samplePath.c_str());
    {
        std::lock_guard<std::mutex> lock(data.mutex);
        data.currentSineGain = data.targetSineGain;
        data.currentSquareGain = data.targetSquareGain;
        data.prevOutputSample = 0.0;
        data.prevRawSine = 0.0;
        data.phase = 0.0;
        data.sampleCount = 0;
        
        // Initialize filter parameters
        data.currentFilterCutoff = data.targetFilterCutoff;
        data.currentFilterResonance = data.targetFilterResonance;
        data.currentFilterDrive = data.targetFilterDrive;
        data.currentFilterKeyTrack = data.targetFilterKeyTrack;
        data.currentFilterEnvMod = data.targetFilterEnvMod;
        
        // Initialize filter coefficients
        data.updateFilterCoeffs();
        
        // Initialize comb filter parameters
        data.currentCombCutoff = data.targetCombCutoff;
        data.currentCombResonance = data.targetCombResonance;
        data.currentCombDrive = data.targetCombDrive;
        data.currentCombKeyTrack = data.targetCombKeyTrack;
        data.currentCombEnvMod = data.targetCombEnvMod;
        
        // Initialize global filter parameters
        data.currentGlobalCutoff = data.targetGlobalCutoff;
        data.currentGlobalResonance = data.targetGlobalResonance;
        
        // Initialize filter envelope parameters
        data.currentFilterEnvAttack  = data.targetFilterEnvAttack;
        data.currentFilterEnvDecay   = data.targetFilterEnvDecay;
        data.currentFilterEnvSustain = data.targetFilterEnvSustain;
        data.currentFilterEnvRelease = data.targetFilterEnvRelease;
        data.update_filter_env();
        
        // Initialize comb filter parameters
        data.updateCombParams();
        /* -------------------------- LFO initialisation -------------------------- */
        data.currentLfoRate    = data.targetLfoRate;
        data.currentLfoDepth   = data.targetLfoDepth;
        data.currentLfoLevel   = data.targetLfoLevel;
        data.lfoPhase          = 0.0;
        data.lfoPhaseIncrement = 2 * PI * data.currentLfoRate / sample_rate;

        // Initialize tube driver parameters
        data.currentTubeAmount = data.targetTubeAmount;
        data.currentTubeMinMix = data.targetTubeMinMix;
        data.currentTubeMaxMix = data.targetTubeMaxMix;

        // Initialize bitcrusher parameters
        data.currentBitDepth = data.targetBitDepth;
        data.currentBitMix   = data.targetBitMix;

        // Initialize delay line buffer
        data.combDelayLine.assign(data.MAX_DELAY_SAMPLES, 0.0);
        data.combWritePos = 0;
    }

    {
        std::lock_guard<std::mutex> lock(data.mutex);
        data.update_adsr();
    }
    Pa_StartStream(stream);
}

extern "C" void note_on() {
    {
        std::lock_guard<std::mutex> lock(data.mutex);
        samplePosFloat = 0;  // Reset sample playback
    }
    data.reset();
}

extern "C" void note_off();

extern "C" void note_off() {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.noteOn = false;
    data.releaseHoldCounter = 0;
    data.envelopeState = HOLD_BEFORE_RELEASE;
    data.releaseStartLevel = data.currentAmplitude;
}

extern "C" void stop_synth() {
    note_off();
    constexpr unsigned int maxWaitMs = 2000;
    constexpr unsigned int sleepStepMs = 50;
    unsigned int waitedMs = 0;
    while ((data.envelopeState != IDLE) && waitedMs < maxWaitMs) {
        std::this_thread::sleep_for(std::chrono::milliseconds(sleepStepMs));
        waitedMs += sleepStepMs;
    }
    if (stream) {
        Pa_StopStream(stream);
        Pa_CloseStream(stream);
        Pa_Terminate();
        stream = nullptr;
    }
}

// CORE AUDIO PARAMETERS

extern "C" void set_sample_rate(double SAMPLE_RATE) {
    data.setSampleRate(SAMPLE_RATE);
}

extern "C" void set_frequency(double freq) {
    data.setFrequency(freq);
}

extern "C" void set_amplitude(double amplitude) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.amplitude = amplitude;
}

extern "C" void set_gain_smoothing_time_seconds(double GAIN_SMOOTHING_TIME_SECONDS) {
    data.setGainSmoothingTimeSeconds(GAIN_SMOOTHING_TIME_SECONDS);
}

extern "C" void set_gain_normalization_cap(double GAIN_NORMALIZATION_CAP) {
    data.setGainNormalizationCap(GAIN_NORMALIZATION_CAP);
}

extern "C" void set_master_volume(double volume) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.masterVolume = volume;
}

// SAMPLE SETTINGS

extern "C" void set_sample_base_frequency( double SAMPLE_BASE_FREQUENCY) {
    data.setSampleBaseFrequency(SAMPLE_BASE_FREQUENCY);
}

extern "C" void set_sample_loop(unsigned int start, unsigned int end) {
    loopActive = true;
    sampleLoopStart = std::min(start, static_cast<unsigned int>(squareSample.size()));
    sampleLoopEnd = std::min(end, static_cast<unsigned int>(squareSample.size()));
    if (sampleLoopEnd <= sampleLoopStart) sampleLoopEnd = squareSample.size();
}

extern "C" void set_sample_loop_start_percentage(double SAMPLE_LOOP_START_PERCENTAGE) {
    data.setSampleLoopStartPercentage(SAMPLE_LOOP_START_PERCENTAGE);
}

extern "C" void set_sample_loop_end_percentage(double SAMPLE_LOOP_END_PERCENTAGE) {
    data.setSampleLoopEndPercentage(SAMPLE_LOOP_END_PERCENTAGE);
}

extern "C" void set_fade_samples(double FADE_SAMPLES) {
    data.setFadeSamples(FADE_SAMPLES);
}

extern "C" void set_fade_in_time(double FADE_IN_TIME) {
    data.setFadeInTime(FADE_IN_TIME);
}

extern "C" void set_loop_fade_samples(unsigned int LOOP_FADE_SAMPLES) {
    data.setLoopFadeSamples(LOOP_FADE_SAMPLES);
}

// OSCILLATOR SETTINGS

extern "C" void set_sine_gain(double gain) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetSineGain = gain;
}

extern "C" void set_square_gain(double gain) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetSquareGain = gain;
}

extern "C" void set_fm_depth(double depth) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.fmDepth = depth * PI;  // scale 0-1 input to 0 - π radians
}

// ADSR SETTINGS

extern "C" void set_attack(double attackSeconds) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetAttackTime = attackSeconds;
}

extern "C" void set_decay(double decaySeconds) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetDecayTime = decaySeconds;
}

extern "C" void set_release(double releaseSeconds) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetReleaseTime = releaseSeconds;
}

extern "C" void set_sustain_level(double levelDb) {
    std::lock_guard<std::mutex> lock(data.mutex);
    /* Keep smoothing intact – only set the target; smoothing engine
       will bring currentSustainLevel and sustainCalc to this target.   */
    data.targetSustainLevel = levelDb;
}

// FILTER 1 SETTINGS

extern "C" void set_filter_cutoff(double cutoff) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterCutoff = cutoff;
}

extern "C" void set_filter_resonance(double resonance) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterResonance = resonance;
}

extern "C" void set_filter_env_mod(double envMod) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterEnvMod = envMod;
}

extern "C" void set_filter_drive(double drive) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterDrive = drive;
}

extern "C" void set_filter_key_tracking(double tracking) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterKeyTrack = tracking;
}

extern "C" void set_filter_drive_scaling(double FILTER_DRIVE_SCALING) {
    data.setFilterDriveScaling(FILTER_DRIVE_SCALING);
}

extern "C" void set_filter_env_mod_scaling(double FILTER_ENV_MOD_SCALING) {
    data.setFilterEnvModScaling(FILTER_ENV_MOD_SCALING);
}

// Filter 2 Settings

extern "C" void set_comb_cutoff(double cutoff) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetCombCutoff = cutoff;
}

extern "C" void set_comb_resonance(double resonance) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetCombResonance = resonance;
}

extern "C" void set_comb_env_mod(double envMod) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetCombEnvMod = envMod;
}

extern "C" void set_comb_drive(double drive) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetCombDrive = drive;
}

extern "C" void set_comb_key_tracking(double tracking) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetCombKeyTrack = tracking;
}

// ACTUAL LIMITS
extern "C" void set_comb_min_delay_ms(double COMB_MIN_DELAY_MS) {
    data.setCombMinDelayMs(COMB_MIN_DELAY_MS);
}

extern "C" void set_comb_max_delay_ms(double COMB_MAX_DELAY_MS) {
    data.setCombMaxDelayMs(COMB_MAX_DELAY_MS);
}

extern "C" void set_comb_feedback_max(double COMB_FEEDBACK_MAX) {
    data.setCombFeedbackMax(COMB_FEEDBACK_MAX);
}

extern "C" void set_comb_min_resonance(double COMB_MIN_RESONANCE) {
    data.setCombMinResonance(COMB_MIN_RESONANCE);
}

extern "C" void set_comb_feedback_limiter(double COMB_FEEDBACK_LIMITER) {
    data.setCombFeedbackLimiter(COMB_FEEDBACK_LIMITER);
}

// SCALING
extern "C" void set_comb_feedback_scaling(double COMB_FEEDBACK_SCALING) {
    data.setCombFeedbackScaling(COMB_FEEDBACK_SCALING);
}

extern "C" void set_comb_env_mod_scaling(double COMB_ENV_MOD_SCALING) {
    data.setCombEnvModScaling(COMB_ENV_MOD_SCALING);
}

extern "C" void set_comb_limiter_strength(double COMB_LIMITER_STRENGTH) {
    data.setCombLimiterStrength(COMB_LIMITER_STRENGTH);
}

extern "C" void set_comb_filter_drive_scaling(double COMB_FILTER_DRIVE_SCALING) {
    data.setCombFilterDriveScaling(COMB_FILTER_DRIVE_SCALING);
}

// FILTER ENVELOPE SETTINGS

extern "C" void set_filter_env_attack(double attackSec) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterEnvAttack = std::max(0.0001, attackSec);
}

extern "C" void set_filter_env_decay(double decaySec) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterEnvDecay = std::max(0.0001, decaySec);
}

extern "C" void set_filter_env_sustain(double sustainDb) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterEnvSustain = sustainDb;
}

extern "C" void set_filter_env_release(double releaseSec) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetFilterEnvRelease = std::max(0.0001, releaseSec);
}

// GLOBAL FILTER SETTERS

extern "C" void set_global_cutoff(double cutoffHz) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetGlobalCutoff = cutoffHz;
}

extern "C" void set_global_resonance(double resonanceQ) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetGlobalResonance = resonanceQ;
}

// LFO SETTINGS

extern "C" void set_lfo_rate(double rate) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetLfoRate = rate;
}

extern "C" void set_lfo_depth(double depth) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetLfoDepth = depth;
}

extern "C" void set_lfo_level(double level) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetLfoLevel = level;
}

// BITCRUSHER SETTINGS

extern "C" void set_bit_depth(double depthBits) {
    std::lock_guard<std::mutex> lock(data.mutex);
    /* Clamp to 1-16 bits */
    data.targetBitDepth = std::min(16.0, std::max(1.0, depthBits));
}

extern "C" void set_bit_mix(double mixPercent) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetBitMix = std::clamp(mixPercent, 0.0, 100.0);
}

// ACTUAL LIMITS
extern "C" void set_bitcrusher_min_depth(double BITCRUSHER_MIN_DEPTH) {
    data.setBitcrusherMinDepth(BITCRUSHER_MIN_DEPTH);
}

extern "C" void set_bitcrusher_max_depth(double BITCRUSHER_MAX_DEPTH) {
    data.setBitcrusherMaxDepth(BITCRUSHER_MAX_DEPTH);
}

extern "C" void set_bitcrusher_bypass_threshold(double BITCRUSHER_BYPASS_THRESHOLD) {
    data.setBitcrusherBypassThreshold(BITCRUSHER_BYPASS_THRESHOLD);
}

extern "C" void set_bitcrusher_mix_scale_threshold(double BITCRUSHER_MIX_SCALE_THRESHOLD) {
    data.setBitcrusherMixScaleThreshold(BITCRUSHER_MIX_SCALE_THRESHOLD);
}

extern "C" void set_bitcrusher_dither_threshold(double BITCRUSHER_DITHER_THRESHOLD) {
    data.setBitcrusherDitherThreshold(BITCRUSHER_DITHER_THRESHOLD);
}

// TUBE DRIVER SETTINGS

extern "C" void set_tube_amount(double amount) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetTubeAmount = amount;
}

extern "C" void set_tube_min_mix(double minMix) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetTubeMinMix = minMix;
}

extern "C" void set_tube_max_mix(double maxMix) {
    std::lock_guard<std::mutex> lock(data.mutex);
    data.targetTubeMaxMix = maxMix;
}

extern "C" void set_tube_drive_scaling(double TUBE_DRIVE_SCALING) {
    data.setTubeDriveScaling(TUBE_DRIVE_SCALING);
}

extern "C" void set_tube_intensity_scaling(double TUBE_INTENSITY_SCALING) {
    data.setTubeIntensityScaling(TUBE_INTENSITY_SCALING);
}

extern "C" void set_tube_quintic_coeff(double TUBE_QUINTIC_COEFF) {
    data.setTubeQuinticCoeff(TUBE_QUINTIC_COEFF);
}

extern "C" void set_tube_cubic_coeff(double TUBE_CUBIC_COEFF) {
    data.setTubeCubicCoeff(TUBE_CUBIC_COEFF);
}

extern "C" void set_tube_bypass_threshold(double TUBE_BYPASS_THRESHOLD) {
    data.setTubeBypassThreshold(TUBE_BYPASS_THRESHOLD);
}