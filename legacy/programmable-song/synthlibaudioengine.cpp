
//------------------------------------------------------------------------------//
//                  CENTRAL STRUCTURE- STATES AND PROCESSING ENGINE            //
//----------------------------------------------------------------------------//

struct SineData {
    // ====================================================================== //
    // 1.  CORE STATE AND SYNCHRONISATION DECLARATION                         //
    // ====================================================================== //

    std::mutex mutex;
    double phase = 0.0;
    double frequency = 440.0;
    double phaseIncrement = 2 * PI * frequency / sample_rate;
    double sampleBaseFreq = 440;
    double basePhaseIncrement = 2 * PI * sampleBaseFreq / sample_rate;
    double timeScalingFactor = 1.0;
    unsigned long sampleCount = 0;

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

    double masterVolume         = 0.1;

    // ------------------------------- FILTER 1------------------------------ //

    double targetFilterCutoff    = 20000.0;  // Hz
    double targetFilterResonance = 0.7071;   // Q
    double targetFilterDrive     = 0.0;      // %
    double targetFilterKeyTrack  = 0.0;      // %
    double targetFilterEnvMod    = 0.0;      // %

    double currentFilterCutoff    = 20000.0;
    double currentFilterResonance = 0.7071;
    double currentFilterDrive     = 0.0;
    double currentFilterKeyTrack  = 0.0;
    double currentFilterEnvMod    = 0.0;

    // bi-quad coefficients (a0 assumed 1) //
    double b0 = 1.0, b1 = 0.0, b2 = 0.0, a1 = 0.0, a2 = 0.0;
    // filter memory (DF-II T) //
    double z1 = 0.0, z2 = 0.0;

    // ====================================================================== //
    // 5.  COMB FILTER PARAMETER DECLARATIONS                                 //
    // ====================================================================== //

    // ------------------------------- COMB FILTER -------------------------- //

    double targetCombCutoff    = 20000.0;  // Hz (controls delay time)
    double targetCombResonance = 0.7071;   // Controls feedback
    double targetCombDrive     = 0.0;      // % (pre-comb gain)
    double targetCombKeyTrack  = 0.0;      // % (delay time adjustment)
    double targetCombEnvMod    = 0.0;      // %

    double currentCombCutoff    = 20000.0;
    double currentCombResonance = 0.7071;
    double currentCombDrive     = 0.0;
    double currentCombKeyTrack  = 0.0;
    double currentCombEnvMod    = 0.0;

    // comb filter state //
    static int MAX_DELAY_SAMPLES;
    std::vector<double> combDelayLine = std::vector<double>(MAX_DELAY_SAMPLES, 0.0);
    int combWritePos = 0;
    int combDelayInSamples = 100; // Will be calculated based on cutoff
    double combFeedback = 0.5;    // Will be calculated based on resonance

    // ====================================================================== //
    // 6.  FILTER ENVELOPE PARAMETER DECLARATIONS                             //
    // ====================================================================== //

    // ---------------------------- FILTER ENVELOPE ------------------------- //

    double targetFilterEnvAttack  = 0.001;   // seconds
    double targetFilterEnvDecay   = 0.50;    // seconds
    double targetFilterEnvSustain = -20.0;   // dB
    double targetFilterEnvRelease = 0.50;    // seconds

    double currentFilterEnvAttack  = 0.001;
    double currentFilterEnvDecay   = 0.50;
    double currentFilterEnvSustain = -20.0;
    double currentFilterEnvRelease = 0.50;

    // Envelope runtime bookkeeping //
    EnvelopeState filterEnvState           = IDLE;
    unsigned long filterEnvSampleCount     = 0;
    unsigned long filterEnvAttackSamples   = static_cast<unsigned long>(sample_rate * 0.001);
    unsigned long filterEnvDecaySamples    = static_cast<unsigned long>(sample_rate* 0.50);
    unsigned long filterEnvReleaseSamples  = static_cast<unsigned long>(sample_rate * 0.50);
    double        filterEnvSustainCalc     = std::pow(10.0, currentFilterEnvSustain / 20.0);
    unsigned long filterEnvReleaseStartSample = 0;
    double        filterEnvReleaseStartLvl = 0.0;
    double        currentFilterEnvLevel    = 0.0;

    // ====================================================================== //
    // 7.  GLOBAL CONTROLS DECLARATIONS                                       //
    // ====================================================================== //

    double targetGlobalCutoff    = 632.456;   // start at log-mid ≈ sqrt(20*20000)
    double targetGlobalResonance = 3.16228;   // log-mid of 0.25 and 40

    double currentGlobalCutoff    = 632.456;
    double currentGlobalResonance = 3.16228;


    // ====================================================================== //
    // 8.  LFO PARAMETER DECLARATIONS                                         //
    // ====================================================================== //

    double targetLfoRate        = 1.0;      // Hz
    double targetLfoDepth       = 0.0;      // % (0-100)
    double targetLfoLevel       = 100.0;    // % (0-100 overall modulation level)

    double currentLfoRate       = 1.0;
    double currentLfoDepth      = 0.0;
    double currentLfoLevel      = 100.0;

    double lfoPhase             = 0.0;                     // 0-2π
    double lfoPhaseIncrement    = 2 * PI * currentLfoRate / sample_rate;

    // ====================================================================== //
    // 9.  EFFECT PROCESSOR DECLARATIONS                                      //
    // ====================================================================== //

    // ---------------------------------- TUBE DRIVER ----------------------- //
 
    double targetTubeAmount      = 0.0;      // % (0-100)
    double targetTubeMinMix      = 0.0;      // % (0-100)
    double targetTubeMaxMix      = 100.0;    // % (0-100)

    double currentTubeAmount     = 0.0;
    double currentTubeMinMix     = 0.0;
    double currentTubeMaxMix     = 100.0;

    // ---------------------------------- BITCRUSHER ------------------------ //

    double targetBitDepth       = 16.0;     // bits (1.0-16.0)
    double targetBitMix         = 0.0;      // % (0-100)

    double currentBitDepth      = 16.0;
    double currentBitMix        = 0.0;

    // ====================================================================== //
    // 10.  SIGNAL-PROCESSING METHODS                                         //
    //       (processFilter, processCombFilter, etc.)                         //
    // ====================================================================== //

    
    // ------------------------------------------------------------------ //
    //  Filter sample processing  (includes drive)                        //
    // ------------------------------------------------------------------ //
    inline double processFilter(double inSample)
    {
        const double drvAmt  = currentFilterDrive / 100.0;   // 0-1
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
    inline double processCombFilter(double inSample)
    {
        // --------------------------------------------------------------
        // 1.  Pre-drive saturation
        // --------------------------------------------------------------
        const double drvAmt  = currentCombDrive / 100.0;              // 0-1
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
    inline double processTubeDriver(double inSample)
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
                        + tube_quintic_coeff  * driveAmount * driveAmount
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
    inline double processBitcrusher(double inSample)
    {
        // Bypass if mix ≈ 0 % or depth ≈ 16-bit (full quality)            
        if (currentBitMix < bitcrusher_bypass_threshold || currentBitDepth >= bitcrusher_max_depth)
            return inSample;

        // ------------------------------------------------------------------
        //  Safety clamp: keep sample in −1 … 1 to avoid NAN / inf later
        // ------------------------------------------------------------------
        inSample = std::max(-1.0, std::min( 1.0, inSample));

        // Constrain depth to sane 1-16 bit range and compute steps        
        const double depth    = std::max(bitcrusher_min_depth, std::min(bitcrusher_max_depth, currentBitDepth));
        const double bitSteps = std::pow(2.0, depth);

        // Scale  −1..1  →  0..bitSteps, quantise, clamp                   
        double scaled    = (inSample + 1.0) * 0.5 * bitSteps;
        double quantised = std::floor(scaled);
        quantised        = std::max(0.0, std::min(bitSteps - 1.0, quantised));

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

    // ------------------------------------------------------------------ //
    //  Helper utilities for filter-coefficient update                    //
    // ------------------------------------------------------------------ //

    // Named constants (avoid magic numbers)
    static constexpr double MIN_CUTOFF_HZ   = 20.0;
    static constexpr double MAX_CUTOFF_HZ   = 20000.0;
    static constexpr double MIN_RESO_Q      = 0.25;
    static constexpr double MAX_RESO_Q      = 40.0;

    // Calculate final cutoff after global / key-track / envelope influence
    inline double calculateEffectiveCutoff() {
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
    inline double calculateEffectiveResonance() {
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
    inline void calculateBiquadCoefficients(double cutoffHz, double resonanceQ) {
        const double omega = 2.0 * PI * cutoffHz / sample_rate;
        const double sinO  = std::sin(omega);
        const double cosO  = std::cos(omega);
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

    // -------------------------------------------------------------- //
    //  Recompute LPF coefficients – public entry                     //
    // -------------------------------------------------------------- //
    void updateFilterCoeffs() {
        const double cutoffHz   = calculateEffectiveCutoff();
        const double resonanceQ = calculateEffectiveResonance();
        calculateBiquadCoefficients(cutoffHz, resonanceQ);
    }

    // ------------------------------------------------------------------ //
    //  Helper utilities for COMB-filter parameter update                 //
    // ------------------------------------------------------------------ //

    // Calculate effective comb-filter cutoff (Hz) after all modifiers
    inline double calculateCombEffectiveCutoff() {
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
    inline double calculateCombEffectiveResonance() {
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
    inline void calculateCombDelayAndFeedback(double cutoffHz, double resonanceQ) {
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

    // update comb filter parameters (call under mutex!)
    void updateCombParams() {
        const double cutoffHz   = calculateCombEffectiveCutoff();
        const double resonanceQ = calculateCombEffectiveResonance();
        calculateCombDelayAndFeedback(cutoffHz, resonanceQ);
    }

    // ====================================================================== 
    // 11.  PARAMETER-UPDATE / HELPER METHODS                                 
    // ====================================================================== 

    // UTILITIES

    void reset() {
        std::lock_guard<std::mutex> lock(mutex);
        noteOn = true;
        sampleCount = 0;
        releaseStartSample = 0;
        releaseHoldCounter = 0;
        envelopeState = ATTACK;
        samplesSinceStateChange = fade_samples;
        updatePhaseIncrement();
    }
    
    void updatePhaseIncrement() {
        phaseIncrement = 2 * PI * frequency / sample_rate;
        timeScalingFactor = phaseIncrement / basePhaseIncrement;

    }

    void setFrequency(double freq) {
        std::lock_guard<std::mutex> lock(mutex);
        frequency = freq;
        updatePhaseIncrement();
    }

    void setSampleRate(double SAMPLE_RATE) {
        std::lock_guard<std::mutex> lock(mutex);
        sample_rate = SAMPLE_RATE;
    }

    void setGainNormalizationCap(double GAIN_NORM_CAP) {
        std::lock_guard<std::mutex> lock(mutex);
        gain_normalization_cap = GAIN_NORM_CAP;
    }

    void setGainSmoothingTimeSeconds(double GAIN_SMOOTHING_TIME_SECONDS) {
        std::lock_guard<std::mutex> lock(mutex);
        gainSmoothingTimeSeconds = GAIN_SMOOTHING_TIME_SECONDS;
    }

    void setFadeSamples(double FADE_SAMPLES) {
        std::lock_guard<std::mutex> lock(mutex);
        fade_samples = FADE_SAMPLES;
    }

    void setFadeInTime(double FADE_IN_TIME) {
        std::lock_guard<std::mutex> lock(mutex);
        fadeInTime = FADE_IN_TIME;
    }

    /* Loop-fade length (samples) setter */
    void setLoopFadeSamples(unsigned int LOOP_FADE_SAMPLES) {
        std::lock_guard<std::mutex> lock(mutex);
        loop_fade_samples = LOOP_FADE_SAMPLES;
    }

    void setSampleLoopStartPercentage(double SAMPLE_LOOP_START_PERCENTAGE) {
        std::lock_guard<std::mutex> lock(mutex);
        sampleLoopStartPercentage = SAMPLE_LOOP_START_PERCENTAGE;
        // Add this line to update the actual loop start point:
        if (!squareSample.empty()) {
            sampleLoopStart = static_cast<unsigned int>(sampleLoopStartPercentage * squareSample.size());
        }
    }

    void setSampleLoopEndPercentage(double SAMPLE_LOOP_END_PERCENTAGE) {
        std::lock_guard<std::mutex> lock(mutex);
        sampleLoopEndPercentage = SAMPLE_LOOP_END_PERCENTAGE;
        // Add this line to update the actual loop start point:
        if (!squareSample.empty()) {
            sampleLoopEnd = static_cast<unsigned int>(sampleLoopEndPercentage * squareSample.size());
        }
    }

    void setSampleBaseFrequency(double SAMPLE_BASE_FREQUENCY) {
        std::lock_guard<std::mutex> lock(mutex);
        sampleBaseFreq = SAMPLE_BASE_FREQUENCY;
        basePhaseIncrement = 2 * PI * sampleBaseFreq / sample_rate;
        updatePhaseIncrement(); // This updates timeScalingFactor based on the new basePhaseIncrement
    }

    // ADSR
    
    void update_adsr() {
        attackSamples = static_cast<unsigned long>(sample_rate * currentAttackTime);
        decaySamples = static_cast<unsigned long>(sample_rate * currentDecayTime);
        releaseSamples = static_cast<unsigned long>(sample_rate * currentReleaseTime);
        sustainCalc = std::pow(10.0, currentSustainLevel / 20.0);
    }

    // FILTERS

    void setFilterDriveScaling(double FILTER_DRIVE_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        filter_drive_scaling = FILTER_DRIVE_SCALING;
    }

    void setCombLimiterStrength(double COMB_LIMITER_STRENGTH) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_limiter_strength = COMB_LIMITER_STRENGTH;
    }

    void setCombMinDelayMs(double COMB_MIN_DELAY_MS) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_min_delay_ms = COMB_MIN_DELAY_MS;
    }

    void setCombMaxDelayMs(double COMB_MAX_DELAY_MS) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_max_delay_ms = COMB_MAX_DELAY_MS;
    }

    void setCombFeedbackMax(double COMB_FEEDBACK_MAX) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_feedback_max = COMB_FEEDBACK_MAX;
    }

    void setCombFeedbackScaling(double COMB_FEEDBACK_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_feedback_scaling = COMB_FEEDBACK_SCALING;
    }

    void setCombFeedbackLimiter(double COMB_FEEDBACK_LIMITER) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_feedback_limiter = COMB_FEEDBACK_LIMITER;
    }

    void setCombMinResonance(double COMB_MIN_RESONANCE) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_min_resonance = COMB_MIN_RESONANCE;
    }

    void setCombEnvModScaling(double COMB_ENV_MOD_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_env_mod_scaling = COMB_ENV_MOD_SCALING;
    }

    void setCombFilterDriveScaling(double COMB_FILTER_DRIVE_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        comb_filter_drive_scaling = COMB_FILTER_DRIVE_SCALING;
    }

    // FILTER ENVELOPE

    void update_filter_env() {
        filterEnvAttackSamples  = static_cast<unsigned long>(sample_rate * currentFilterEnvAttack);
        filterEnvDecaySamples   = static_cast<unsigned long>(sample_rate * currentFilterEnvDecay);
        filterEnvReleaseSamples = static_cast<unsigned long>(sample_rate * currentFilterEnvRelease);
        filterEnvSustainCalc    = std::pow(10.0, currentFilterEnvSustain / 20.0);
    }

    void setFilterEnvModScaling(double FILTER_ENV_MOD_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        filter_env_mod_scaling = FILTER_ENV_MOD_SCALING;
    }

    // BITCRUSHER

    void setBitcrusherMixScaleThreshold(double BITCRUSHER_MIX_SCALE_THRESHOLD) {
        std::lock_guard<std::mutex> lock(mutex);
        bitcrusher_mix_scale_threshold = BITCRUSHER_MIX_SCALE_THRESHOLD;
    }

    void setBitcrusherDitherThreshold(double BITCRUSHER_DITHER_THRESHOLD) {
        std::lock_guard<std::mutex> lock(mutex);
        bitcrusher_dither_threshold = BITCRUSHER_DITHER_THRESHOLD;
    }

    void setBitcrusherMaxDepth(double BITCRUSHER_MAX_DEPTH) {
        std::lock_guard<std::mutex> lock(mutex);
        bitcrusher_max_depth = BITCRUSHER_MAX_DEPTH;
    }

    void setBitcrusherMinDepth(double BITCRUSHER_MIN_DEPTH) {
        std::lock_guard<std::mutex> lock(mutex);
        bitcrusher_min_depth = BITCRUSHER_MIN_DEPTH;
    }

    void setBitcrusherBypassThreshold(double BITCRUSHER_BYPASS_THRESHOLD) {
        std::lock_guard<std::mutex> lock(mutex);
        bitcrusher_bypass_threshold = BITCRUSHER_BYPASS_THRESHOLD;
    }

    // TUBE-DRIVER
    
    void setTubeQuinticCoeff(double TUBE_QUINTIC_COEFF) {
        std::lock_guard<std::mutex> lock(mutex);
        tube_quintic_coeff = TUBE_QUINTIC_COEFF;
    }

    void setTubeCubicCoeff(double TUBE_CUBIC_COEFF) {
        std::lock_guard<std::mutex> lock(mutex);
        tube_cubic_coeff = TUBE_CUBIC_COEFF;
    }

    void setTubeBypassThreshold(double TUBE_BYPASS_THRESHOLD) {
        std::lock_guard<std::mutex> lock(mutex);
        tube_bypass_threshold = TUBE_BYPASS_THRESHOLD;
    }

    void setTubeIntensityScaling(double TUBE_INTENSITY_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        tube_intensity_scaling = TUBE_INTENSITY_SCALING;
    }

    void setTubeDriveScaling(double TUBE_DRIVE_SCALING) {
        std::lock_guard<std::mutex> lock(mutex);
        tube_drive_scaling = TUBE_DRIVE_SCALING;
    }
};
int SineData::MAX_DELAY_SAMPLES = sample_rate / 20; //Random Parameter needs global declaration
static SineData data; // Actual instantiation of SineData called "data"


