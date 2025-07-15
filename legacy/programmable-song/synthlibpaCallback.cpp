//------------------------------------------------------------------------------//
//                      AUDIO CALLBACK AND PROCESSING                          //
//----------------------------------------------------------------------------//

// ---------------------- Sample Path Setter ----------------------------------                                                      
extern std::string samplePath;
extern "C" void set_sample_path(const char* path) {
    if (path && *path) {
        samplePath = path;
    }
}

// Set Up Stream
static PaStream* stream = nullptr;
static int paCallback(const void*, void* outputBuffer,
                      unsigned long framesPerBuffer,
                      const PaStreamCallbackTimeInfo*,
                      PaStreamCallbackFlags,
                      void* userData) {
    float* out = static_cast<float*>(outputBuffer);
    SineData* d = static_cast<SineData*>(userData);

    // Declare variables at beginning of loop
    for (unsigned long i = 0; i < framesPerBuffer; i++) {
        double amplitudeMultiplier = 0.0;
        EnvelopeState currentState;
        double currentAmp;
        double prevAmp;
        unsigned long fadeCounter;
        bool isStateTransition = false;
        unsigned long currentSampleCount;

        {
            std::lock_guard<std::mutex> lock(d->mutex);
            currentState = d->envelopeState;
            currentSampleCount = d->sampleCount;

            // Reset variables per envelope
            if (currentState != d->prevEnvelopeState) {
                d->prevEnvelopeState = currentState;
                d->samplesSinceStateChange = 0;
                d->prevAmplitude = d->currentAmplitude;
                isStateTransition = true;
            }

            switch (currentState) {
                case ATTACK:
                    if ((d->sampleCount < d->attackSamples) && (d->prevEnvelopeState == IDLE)) {
                        amplitudeMultiplier = static_cast<double>(d->sampleCount) / d->attackSamples;
                    } else if ((d->sampleCount < d->attackSamples) && (d->prevEnvelopeState == RELEASE)) {
                        amplitudeMultiplier = static_cast<double>(d->sampleCount) / d->attackSamples;
                    } else {
                        d->envelopeState = DECAY;
                        amplitudeMultiplier = 1.0;
                        d->samplesSinceStateChange = 0;
                        isStateTransition = true;
                    }
                    break;
                case DECAY: {
                    unsigned long decayPos = d->sampleCount - d->attackSamples;
                    if (decayPos < d->decaySamples) {
                        double decayProgress = static_cast<double>(decayPos) / d->decaySamples;
                        amplitudeMultiplier = 1.0 + decayProgress * (d->sustainCalc - 1.0);
                    } else {
                        d->envelopeState = SUSTAIN;
                        amplitudeMultiplier = d->sustainCalc;
                        d->samplesSinceStateChange = 0;
                        isStateTransition = true;
                    }
                    break;
                }
                case SUSTAIN:
                    amplitudeMultiplier = d->sustainCalc;
                    break;
                case HOLD_BEFORE_RELEASE:
                    amplitudeMultiplier = d->releaseStartLevel;
                    if (++d->releaseHoldCounter >= d->releaseHoldSamples) {
                        d->envelopeState = RELEASE;
                        d->releaseStartSample = d->sampleCount;
                        d->samplesSinceStateChange = 0;
                        isStateTransition = true;
                    }
                    break;
                case RELEASE: {
                    unsigned long releasePos = d->sampleCount - d->releaseStartSample;
                    if (releasePos >= d->releaseSamples) {
                        amplitudeMultiplier = 0.0;
                        d->envelopeState = IDLE;
                        d->samplesSinceStateChange = 0;
                        d->prevAmplitude = 0;
                        isStateTransition = true;
                    } else {
                        double releaseProgress = static_cast<double>(releasePos) / d->releaseSamples;
                        amplitudeMultiplier = d->releaseStartLevel * (1.0 - releaseProgress);
                    }
                    break;
                }
                case IDLE:
                default: {
                    // Keep generating samples until we hit a zero-crossing
                    double rawSine = sin(d->phase);
                    
                    // If we're near a zero crossing, truly silence
                    if (std::abs(rawSine) < 1e-4) {
                        amplitudeMultiplier = 0.0;
                    } else {
                        amplitudeMultiplier = 0.0;  // keep amplitude at 0
                    }
                    break;
                }

            }

            fadeCounter = d->samplesSinceStateChange;
            prevAmp = d->prevAmplitude;
            currentAmp = amplitudeMultiplier;


            if (fadeCounter < fade_samples) {
                double alpha = static_cast<double>(fadeCounter) / fade_samples;
                amplitudeMultiplier = (1.0 - alpha) * prevAmp + alpha * currentAmp;
            } else {
                amplitudeMultiplier = currentAmp;
            }

            d->samplesSinceStateChange++;
            d->currentAmplitude = amplitudeMultiplier;
        }

        // Get phase and calculate raw sine value
        double phaseCopy;
        {
            std::lock_guard<std::mutex> lock(d->mutex);
            phaseCopy = d->phase;
        }

        float sampleValue = 0.0f;
        if (!squareSample.empty()) {
            int indexA = static_cast<int>(floor(samplePosFloat));
            int indexB = indexA + 1;
            if (indexB >= squareSample.size()) indexB = indexA;

            float frac = static_cast<float>(samplePosFloat - indexA);

            sampleValue = squareSample[indexA] * (1.0f - frac) + squareSample[indexB] * frac;

            if (loopActive && data.envelopeState != RELEASE && data.envelopeState != IDLE) {
                // Calculate fade out factor near loop end
                float fadeOutFactor = 1.0f;
                if (samplePosFloat >= sampleLoopEnd - loop_fade_samples) {
                    unsigned int fadePos = samplePosFloat - (sampleLoopEnd - loop_fade_samples);
                    fadeOutFactor = 1.0f - static_cast<float>(fadePos) / loop_fade_samples;
                }

                // Calculate fade in factor near loop start
                float fadeInFactor = 1.0f;
                if (samplePosFloat < sampleLoopStart + loop_fade_samples) {
                    unsigned int fadePos = samplePosFloat - sampleLoopStart;
                    fadeInFactor = static_cast<float>(fadePos) / loop_fade_samples;
                }

                // Combine fade factors (multiplying them gives a crossfade effect)
                float loopFadeFactor = fadeOutFactor * fadeInFactor;

                sampleValue *= loopFadeFactor;

                samplePosFloat += d->timeScalingFactor;
                if (samplePosFloat >= sampleLoopEnd || samplePosFloat >= squareSample.size()) {
                    samplePosFloat = sampleLoopStart;
                }
            } else {
                samplePosFloat += d->timeScalingFactor;
                if (samplePosFloat >= squareSample.size()) samplePosFloat = squareSample.size() - 1; // hold last sample
            }
        }

        double modulator = sin(phaseCopy);  // same freq
        double modulatedPhase = phaseCopy + d->fmDepth * modulator;
        double rawSine = sin(modulatedPhase);

        double rawSquare = (rawSine >= 0.0 ? 1.0 : -1.0);
        // Smooth gain values towards targets sample by sample
        bool filterParamsChanged = false;
        bool combParamsChanged = false;
        {
            std::lock_guard<std::mutex> lock(d->mutex);
            double smoothingStep = 1.0 / static_cast<double>(d->gainSmoothingSamples);

            // Smooth attackTime
            if (d->currentAttackTime < d->targetAttackTime) {
                d->currentAttackTime += smoothingStep * (d->targetAttackTime - d->currentAttackTime);
                if (std::abs(d->currentAttackTime - d->targetAttackTime) < 1e-6)
                    d->currentAttackTime = d->targetAttackTime;
            } else if (d->currentAttackTime > d->targetAttackTime) {
                d->currentAttackTime -= smoothingStep * (d->currentAttackTime - d->targetAttackTime);
                if (std::abs(d->currentAttackTime - d->targetAttackTime) < 1e-6)
                    d->currentAttackTime = d->targetAttackTime;
            }

            // Smooth decayTime
            if (d->currentDecayTime < d->targetDecayTime) {
                d->currentDecayTime += smoothingStep * (d->targetDecayTime - d->currentDecayTime);
                if (std::abs(d->currentDecayTime - d->targetDecayTime) < 1e-6)
                    d->currentDecayTime = d->targetDecayTime;
            } else if (d->currentDecayTime > d->targetDecayTime) {
                d->currentDecayTime -= smoothingStep * (d->currentDecayTime - d->targetDecayTime);
                if (std::abs(d->currentDecayTime - d->targetDecayTime) < 1e-6)
                    d->currentDecayTime = d->targetDecayTime;
            }

            // Smooth releaseTime
            if (d->currentReleaseTime < d->targetReleaseTime) {
                d->currentReleaseTime += smoothingStep * (d->targetReleaseTime - d->currentReleaseTime);
                if (std::abs(d->currentReleaseTime - d->targetReleaseTime) < 1e-6)
                    d->currentReleaseTime = d->targetReleaseTime;
            } else if (d->currentReleaseTime > d->targetReleaseTime) {
                d->currentReleaseTime -= smoothingStep * (d->currentReleaseTime - d->targetReleaseTime);
                if (std::abs(d->currentReleaseTime - d->targetReleaseTime) < 1e-6)
                    d->currentReleaseTime = d->targetReleaseTime;
            }

            // Smooth sustainLevel
            if (d->currentSustainLevel < d->targetSustainLevel) {
                d->currentSustainLevel += smoothingStep * (d->targetSustainLevel - d->currentSustainLevel);
                if (std::abs(d->currentSustainLevel - d->targetSustainLevel) < 1e-6)
                    d->currentSustainLevel = d->targetSustainLevel;
            } else if (d->currentSustainLevel > d->targetSustainLevel) {
                d->currentSustainLevel -= smoothingStep * (d->currentSustainLevel - d->targetSustainLevel);
                if (std::abs(d->currentSustainLevel - d->targetSustainLevel) < 1e-6)
                    d->currentSustainLevel = d->targetSustainLevel;
            }

            // Update ADSR samples and sustainCalc based on smoothed values
            d->update_adsr();
        
            // Smooth oscillator gains
            if (d->currentSineGain < d->targetSineGain) {
                d->currentSineGain += smoothingStep;
                if (d->currentSineGain > d->targetSineGain)
                    d->currentSineGain = d->targetSineGain;
            } else if (d->currentSineGain > d->targetSineGain) {
                d->currentSineGain -= smoothingStep;
                if (d->currentSineGain < d->targetSineGain)
                    d->currentSineGain = d->targetSineGain;
            }

            if (d->currentSquareGain < d->targetSquareGain) {
                d->currentSquareGain += smoothingStep;
                if (d->currentSquareGain > d->targetSquareGain)
                    d->currentSquareGain = d->targetSquareGain;
            } else if (d->currentSquareGain > d->targetSquareGain) {
                d->currentSquareGain -= smoothingStep;
                if (d->currentSquareGain < d->targetSquareGain)
                    d->currentSquareGain = d->targetSquareGain;
            }

                /* ---------- LFO parameter smoothing ---------- */

                /* Rate : logarithmic smoothing for perceptual naturalness
                 * (reduced aggression to minimise clicks)                  */
                if (std::abs(d->currentLfoRate - d->targetLfoRate) > 0.01) {
                    if (d->currentLfoRate < d->targetLfoRate) {
                        d->currentLfoRate *= 1.0 + smoothingStep * 2.0; // was 5.0
                        if (d->currentLfoRate > d->targetLfoRate)
                            d->currentLfoRate = d->targetLfoRate;
                    } else {
                        d->currentLfoRate *= 1.0 - smoothingStep * 2.0; // was 5.0
                        if (d->currentLfoRate < d->targetLfoRate)
                            d->currentLfoRate = d->targetLfoRate;
                    }
                    /* update phase-increment gradually to avoid clicks     */
                    double newIncrement = 2 * PI * d->currentLfoRate / sample_rate;
                    d->lfoPhaseIncrement = d->lfoPhaseIncrement * 0.9 + newIncrement * 0.1;
                }

                /* Depth : linear smoothing */
                if (std::abs(d->currentLfoDepth - d->targetLfoDepth) > 0.01) {
                    if (d->currentLfoDepth < d->targetLfoDepth) {
                        d->currentLfoDepth += smoothingStep * (d->targetLfoDepth - d->currentLfoDepth);
                        if (d->currentLfoDepth > d->targetLfoDepth)
                            d->currentLfoDepth = d->targetLfoDepth;
                    } else {
                        d->currentLfoDepth -= smoothingStep * (d->currentLfoDepth - d->targetLfoDepth);
                        if (d->currentLfoDepth < d->targetLfoDepth)
                            d->currentLfoDepth = d->targetLfoDepth;
                    }
                }

                /* Level : linear smoothing */
                if (std::abs(d->currentLfoLevel - d->targetLfoLevel) > 0.01) {
                    if (d->currentLfoLevel < d->targetLfoLevel) {
                        d->currentLfoLevel += smoothingStep * (d->targetLfoLevel - d->currentLfoLevel);
                        if (d->currentLfoLevel > d->targetLfoLevel)
                            d->currentLfoLevel = d->targetLfoLevel;
                    } else {
                        d->currentLfoLevel -= smoothingStep * (d->currentLfoLevel - d->targetLfoLevel);
                        if (d->currentLfoLevel < d->targetLfoLevel)
                            d->currentLfoLevel = d->targetLfoLevel;
                    }
                }

                /* ---------- Tube driver parameter smoothing ---------- */

                /* Amount: linear smoothing */
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
                }

                /* Min Mix: linear smoothing */
                if (std::abs(d->currentTubeMinMix - d->targetTubeMinMix) > 0.01) {
                    if (d->currentTubeMinMix < d->targetTubeMinMix) {
                        d->currentTubeMinMix += smoothingStep * (d->targetTubeMinMix - d->currentTubeMinMix);
                        if (d->currentTubeMinMix > d->targetTubeMinMix)
                            d->currentTubeMinMix = d->targetTubeMinMix;
                    } else {
                        d->currentTubeMinMix -= smoothingStep * (d->currentTubeMinMix - d->targetTubeMinMix);
                        if (d->currentTubeMinMix < d->targetTubeMinMix)
                            d->currentTubeMinMix = d->targetTubeMinMix;
                    }
                }

                /* Max Mix: linear smoothing */
                if (std::abs(d->currentTubeMaxMix - d->targetTubeMaxMix) > 0.01) {
                    if (d->currentTubeMaxMix < d->targetTubeMaxMix) {
                        d->currentTubeMaxMix += smoothingStep * (d->targetTubeMaxMix - d->currentTubeMaxMix);
                        if (d->currentTubeMaxMix > d->targetTubeMaxMix)
                            d->currentTubeMaxMix = d->targetTubeMaxMix;
                    } else {
                        d->currentTubeMaxMix -= smoothingStep * (d->currentTubeMaxMix - d->targetTubeMaxMix);
                        if (d->currentTubeMaxMix < d->targetTubeMaxMix)
                            d->currentTubeMaxMix = d->targetTubeMaxMix;
                    }
                }

                /* ---------- Bitcrusher parameter smoothing ---------- */

                /* Bit Depth: linear smoothing */
                if (std::abs(d->currentBitDepth - d->targetBitDepth) > 0.01) {
                    if (d->currentBitDepth < d->targetBitDepth) {
                        d->currentBitDepth += smoothingStep * (d->targetBitDepth - d->currentBitDepth);
                        if (d->currentBitDepth > d->targetBitDepth)
                            d->currentBitDepth = d->targetBitDepth;
                    } else {
                        d->currentBitDepth -= smoothingStep * (d->currentBitDepth - d->targetBitDepth);
                        if (d->currentBitDepth < d->targetBitDepth)
                            d->currentBitDepth = d->targetBitDepth;
                    }
                }

                /* Mix: linear smoothing */
                if (std::abs(d->currentBitMix - d->targetBitMix) > 0.01) {
                    if (d->currentBitMix < d->targetBitMix) {
                        d->currentBitMix += smoothingStep * (d->targetBitMix - d->currentBitMix);
                        if (d->currentBitMix > d->targetBitMix)
                            d->currentBitMix = d->targetBitMix;
                    } else {
                        d->currentBitMix -= smoothingStep * (d->currentBitMix - d->targetBitMix);
                        if (d->currentBitMix < d->targetBitMix)
                            d->currentBitMix = d->targetBitMix;
                    }
                }

            // -------------------- Global Filter Parameter Smoothing --------------------
            // Global cutoff offset (linear smoothing)
            if (std::abs(d->currentGlobalCutoff - d->targetGlobalCutoff) > 0.01) {
                if (d->currentGlobalCutoff < d->targetGlobalCutoff) {
                    d->currentGlobalCutoff += smoothingStep * (d->targetGlobalCutoff - d->currentGlobalCutoff);
                    if (d->currentGlobalCutoff > d->targetGlobalCutoff)
                        d->currentGlobalCutoff = d->targetGlobalCutoff;
                } else {
                    d->currentGlobalCutoff -= smoothingStep * (d->currentGlobalCutoff - d->targetGlobalCutoff);
                    if (d->currentGlobalCutoff < d->targetGlobalCutoff)
                        d->currentGlobalCutoff = d->targetGlobalCutoff;
                }
                filterParamsChanged = true;
                combParamsChanged = true;  // Global params affect both filters
            }

            // Global resonance offset (linear smoothing)
            if (std::abs(d->currentGlobalResonance - d->targetGlobalResonance) > 0.01) {
                if (d->currentGlobalResonance < d->targetGlobalResonance) {
                    d->currentGlobalResonance += smoothingStep * (d->targetGlobalResonance - d->currentGlobalResonance);
                    if (d->currentGlobalResonance > d->targetGlobalResonance)
                        d->currentGlobalResonance = d->targetGlobalResonance;
                } else {
                    d->currentGlobalResonance -= smoothingStep * (d->currentGlobalResonance - d->targetGlobalResonance);
                    if (d->currentGlobalResonance < d->targetGlobalResonance)
                        d->currentGlobalResonance = d->targetGlobalResonance;
                }
                filterParamsChanged = true;
                combParamsChanged = true;  // Global params affect both filters
            }

            // Smooth filter parameters (logarithmic for cutoff, linear for others)
            // Cutoff frequency (logarithmic smoothing for more natural frequency changes)
            if (std::abs(d->currentFilterCutoff - d->targetFilterCutoff) > 0.01) {
                if (d->currentFilterCutoff < d->targetFilterCutoff) {
                    d->currentFilterCutoff *= 1.0 + smoothingStep * 10.0;
                    if (d->currentFilterCutoff > d->targetFilterCutoff)
                        d->currentFilterCutoff = d->targetFilterCutoff;
                } else {
                    d->currentFilterCutoff *= 1.0 - smoothingStep * 10.0;
                    if (d->currentFilterCutoff < d->targetFilterCutoff)
                        d->currentFilterCutoff = d->targetFilterCutoff;
                }
                filterParamsChanged = true;
            }

            // Resonance (linear smoothing)
            if (std::abs(d->currentFilterResonance - d->targetFilterResonance) > 0.01) {
                if (d->currentFilterResonance < d->targetFilterResonance) {
                    d->currentFilterResonance += smoothingStep * (d->targetFilterResonance - d->currentFilterResonance);
                    if (d->currentFilterResonance > d->targetFilterResonance)
                        d->currentFilterResonance = d->targetFilterResonance;
                } else {
                    d->currentFilterResonance -= smoothingStep * (d->currentFilterResonance - d->targetFilterResonance);
                    if (d->currentFilterResonance < d->targetFilterResonance)
                        d->currentFilterResonance = d->targetFilterResonance;
                }
                filterParamsChanged = true;
            }

            // Drive (linear smoothing)
            if (std::abs(d->currentFilterDrive - d->targetFilterDrive) > 0.01) {
                if (d->currentFilterDrive < d->targetFilterDrive) {
                    d->currentFilterDrive += smoothingStep * (d->targetFilterDrive - d->currentFilterDrive);
                    if (d->currentFilterDrive > d->targetFilterDrive)
                        d->currentFilterDrive = d->targetFilterDrive;
                } else {
                    d->currentFilterDrive -= smoothingStep * (d->currentFilterDrive - d->targetFilterDrive);
                    if (d->currentFilterDrive < d->targetFilterDrive)
                        d->currentFilterDrive = d->targetFilterDrive;
                }
                filterParamsChanged = true;
            }

            // Key tracking (linear smoothing)
            if (std::abs(d->currentFilterKeyTrack - d->targetFilterKeyTrack) > 0.01) {
                if (d->currentFilterKeyTrack < d->targetFilterKeyTrack) {
                    d->currentFilterKeyTrack += smoothingStep * (d->targetFilterKeyTrack - d->currentFilterKeyTrack);
                    if (d->currentFilterKeyTrack > d->targetFilterKeyTrack)
                        d->currentFilterKeyTrack = d->targetFilterKeyTrack;
                } else {
                    d->currentFilterKeyTrack -= smoothingStep * (d->currentFilterKeyTrack - d->targetFilterKeyTrack);
                    if (d->currentFilterKeyTrack < d->targetFilterKeyTrack)
                        d->currentFilterKeyTrack = d->targetFilterKeyTrack;
                }
                filterParamsChanged = true;
            }

            // Env mod (linear smoothing) - currently unused but included for completeness
            if (std::abs(d->currentFilterEnvMod - d->targetFilterEnvMod) > 0.01) {
                if (d->currentFilterEnvMod < d->targetFilterEnvMod) {
                    d->currentFilterEnvMod += smoothingStep * (d->targetFilterEnvMod - d->currentFilterEnvMod);
                    if (d->currentFilterEnvMod > d->targetFilterEnvMod)
                        d->currentFilterEnvMod = d->targetFilterEnvMod;
                } else {
                    d->currentFilterEnvMod -= smoothingStep * (d->currentFilterEnvMod - d->targetFilterEnvMod);
                    if (d->currentFilterEnvMod < d->targetFilterEnvMod)
                        d->currentFilterEnvMod = d->targetFilterEnvMod;
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

            smoothLog(d->currentFilterEnvAttack , d->targetFilterEnvAttack );
            smoothLinear(d->currentFilterEnvDecay  , d->targetFilterEnvDecay , 0.0001);
            smoothLinear(d->currentFilterEnvSustain, d->targetFilterEnvSustain, 0.05);
            smoothLinear(d->currentFilterEnvRelease, d->targetFilterEnvRelease, 0.0001);

            if (filterEnvParamsChanged) {
                d->update_filter_env();
            }

            // Update filter coefficients if parameters changed
            if (filterParamsChanged) {
                d->updateFilterCoeffs();
            }
            
            // -------------------- Comb Filter Parameter Smoothing --------------------
            // Cutoff (logarithmic smoothing)
            if (std::abs(d->currentCombCutoff - d->targetCombCutoff) > 0.01) {
                if (d->currentCombCutoff < d->targetCombCutoff) {
                    d->currentCombCutoff *= 1.0 + smoothingStep * 10.0;
                    if (d->currentCombCutoff > d->targetCombCutoff)
                        d->currentCombCutoff = d->targetCombCutoff;
                } else {
                    d->currentCombCutoff *= 1.0 - smoothingStep * 10.0;
                    if (d->currentCombCutoff < d->targetCombCutoff)
                        d->currentCombCutoff = d->targetCombCutoff;
                }
                combParamsChanged = true;
            }
            
            // Resonance (linear smoothing)
            if (std::abs(d->currentCombResonance - d->targetCombResonance) > 0.01) {
                if (d->currentCombResonance < d->targetCombResonance) {
                    d->currentCombResonance += smoothingStep * (d->targetCombResonance - d->currentCombResonance);
                    if (d->currentCombResonance > d->targetCombResonance)
                        d->currentCombResonance = d->targetCombResonance;
                } else {
                    d->currentCombResonance -= smoothingStep * (d->currentCombResonance - d->targetCombResonance);
                    if (d->currentCombResonance < d->targetCombResonance)
                        d->currentCombResonance = d->targetCombResonance;
                }
                combParamsChanged = true;
            }
            
            // Drive (linear smoothing)
            if (std::abs(d->currentCombDrive - d->targetCombDrive) > 0.01) {
                if (d->currentCombDrive < d->targetCombDrive) {
                    d->currentCombDrive += smoothingStep * (d->targetCombDrive - d->currentCombDrive);
                    if (d->currentCombDrive > d->targetCombDrive)
                        d->currentCombDrive = d->targetCombDrive;
                } else {
                    d->currentCombDrive -= smoothingStep * (d->currentCombDrive - d->targetCombDrive);
                    if (d->currentCombDrive < d->targetCombDrive)
                        d->currentCombDrive = d->targetCombDrive;
                }
                combParamsChanged = true;
            }
            
            // Key tracking (linear smoothing)
            if (std::abs(d->currentCombKeyTrack - d->targetCombKeyTrack) > 0.01) {
                if (d->currentCombKeyTrack < d->targetCombKeyTrack) {
                    d->currentCombKeyTrack += smoothingStep * (d->targetCombKeyTrack - d->currentCombKeyTrack);
                    if (d->currentCombKeyTrack > d->targetCombKeyTrack)
                        d->currentCombKeyTrack = d->targetCombKeyTrack;
                } else {
                    d->currentCombKeyTrack -= smoothingStep * (d->currentCombKeyTrack - d->targetCombKeyTrack);
                    if (d->currentCombKeyTrack < d->targetCombKeyTrack)
                        d->currentCombKeyTrack = d->targetCombKeyTrack;
                }
                combParamsChanged = true;
            }
            
            // Env mod (linear smoothing) - currently unused
            if (std::abs(d->currentCombEnvMod - d->targetCombEnvMod) > 0.01) {
                if (d->currentCombEnvMod < d->targetCombEnvMod) {
                    d->currentCombEnvMod += smoothingStep * (d->targetCombEnvMod - d->currentCombEnvMod);
                    if (d->currentCombEnvMod > d->targetCombEnvMod)
                        d->currentCombEnvMod = d->targetCombEnvMod;
                } else {
                    d->currentCombEnvMod -= smoothingStep * (d->currentCombEnvMod - d->targetCombEnvMod);
                    if (d->currentCombEnvMod < d->targetCombEnvMod)
                        d->currentCombEnvMod = d->targetCombEnvMod;
                }
                combParamsChanged = true;
            }
            
            // Update comb filter parameters if changed
            if (combParamsChanged) {
                d->updateCombParams();
            }
        }
        // Mix oscillators and apply *pre-envelope* normalisation
        // ------------------------------------------------------------------
        double combined = d->currentSineGain * rawSine + d->currentSquareGain * sampleValue;

        /* Normalise oscillator mix so overall power remains similar
         * irrespective of the gain settings. Done here (pre-processing)
         * so that ADSR / filter envelopes are not flattened by later
         * automatic gain compensation.                                     */
        {
            double gainPower = d->currentSineGain * d->currentSineGain +
                               d->currentSquareGain * d->currentSquareGain;
            double normalizer = 1.0;
            if (gainPower > 0.0001 && gainPower < 1.0) {
                normalizer = std::min(gain_normalization_cap,
                                      1.0 / std::sqrt(gainPower));
            }
            combined *= normalizer;
        }

        // Apply filter to the combined signal and track inputs/outputs for debugging
        double filterInput = combined;
        double filterOutput = d->processFilter(filterInput);
        combined = filterOutput;

        // Apply comb filter after the lowpass filter
        double combInput = combined;
        double combOutput = d->processCombFilter(combInput);
        combined = combOutput;

        // Apply tube driver after filters
        double tubeInput = combined;
        double tubeOutput = d->processTubeDriver(tubeInput);
        combined = tubeOutput;

        // Apply bitcrusher after tube driver
        double bitInput  = combined;
        double bitOutput = d->processBitcrusher(bitInput);
        combined = bitOutput;

        /* Apply global master volume at the last moment so it scales      *
         * every component (oscillators, filters, effects, etc.).          */
        double outputSample = d->amplitude * amplitudeMultiplier *
                              combined * d->masterVolume;

        // Store sample in output buffer
        *out++ = static_cast<float>(outputSample);
        

        // Calculate differential from previous sample
        double sampleDiff = outputSample - d->prevOutputSample;
        double rawDiff = rawSine - d->prevRawSine;

        
        // Update previous values for next iteration
        d->prevOutputSample = outputSample;
        d->prevRawSine = rawSine;

        // ------------------------------------------------------------------
        // Update filter-envelope state so it follows the amplitude envelope
        // ------------------------------------------------------------------
        {
            std::lock_guard<std::mutex> lock(d->mutex);

            /* --- State-transition logic mirrors amplitude envelope -------- */
            if (d->envelopeState != d->filterEnvState) {
                if (d->envelopeState == ATTACK && d->filterEnvState != ATTACK) {
                    d->filterEnvState      = ATTACK;
                    d->filterEnvSampleCount = 0;
                } else if (d->envelopeState == DECAY && d->filterEnvState != DECAY) {
                    d->filterEnvState       = DECAY;
                    d->filterEnvSampleCount = d->filterEnvAttackSamples;
                } else if (d->envelopeState == SUSTAIN && d->filterEnvState != SUSTAIN) {
                    d->filterEnvState = SUSTAIN;
                } else if ((d->envelopeState == HOLD_BEFORE_RELEASE ||
                            d->envelopeState == RELEASE) &&
                           d->filterEnvState != RELEASE) {
                    d->filterEnvState              = RELEASE;
                    d->filterEnvReleaseStartSample = d->sampleCount;
                    d->filterEnvReleaseStartLvl    = d->currentFilterEnvLevel;
                } else if (d->envelopeState == IDLE && d->filterEnvState != IDLE) {
                    d->filterEnvState        = IDLE;
                    d->currentFilterEnvLevel = 0.0;
                }
            }

            /* --- Per-sample envelope progression -------------------------- */
            switch (d->filterEnvState) {
                case ATTACK:
                    if (d->filterEnvSampleCount < d->filterEnvAttackSamples) {
                        d->currentFilterEnvLevel =
                            static_cast<double>(d->filterEnvSampleCount) /
                            d->filterEnvAttackSamples;
                        d->filterEnvSampleCount++;
                    } else {
                        d->filterEnvState       = DECAY;
                        d->filterEnvSampleCount = d->filterEnvAttackSamples;
                        d->currentFilterEnvLevel = 1.0;
                    }
                    break;

                case DECAY: {
                    unsigned long decayPos =
                        d->filterEnvSampleCount - d->filterEnvAttackSamples;
                    if (decayPos < d->filterEnvDecaySamples) {
                        double decayProgress =
                            static_cast<double>(decayPos) /
                            d->filterEnvDecaySamples;
                        d->currentFilterEnvLevel =
                            1.0 +
                            decayProgress * (d->filterEnvSustainCalc - 1.0);
                        d->filterEnvSampleCount++;
                    } else {
                        d->filterEnvState   = SUSTAIN;
                        d->currentFilterEnvLevel = d->filterEnvSustainCalc;
                    }
                    break;
                }

                case SUSTAIN:
                    d->currentFilterEnvLevel = d->filterEnvSustainCalc;
                    break;

                case RELEASE: {
                    unsigned long relPos =
                        d->sampleCount - d->filterEnvReleaseStartSample;
                    if (relPos >= d->filterEnvReleaseSamples) {
                        d->currentFilterEnvLevel = 0.0;
                        d->filterEnvState = IDLE;
                    } else {
                        double relProg =
                            static_cast<double>(relPos) /
                            d->filterEnvReleaseSamples;
                        d->currentFilterEnvLevel =
                            d->filterEnvReleaseStartLvl * (1.0 - relProg);
                    }
                    break;
                }

                case IDLE:
                case HOLD_BEFORE_RELEASE:
                default:
                    d->currentFilterEnvLevel = 0.0;
                    break;
            }
        }

        // ------------------------------------------------------------------
        // Update LFO & main oscillator phase for next sample
        // ------------------------------------------------------------------
        {
            std::lock_guard<std::mutex> lock(d->mutex);

            /* ----------- LFO pitch-modulation (DISABLED for diagnosis) ----------- */
            /* Advance LFO phase so it keeps running silently               */
            d->lfoPhase += d->lfoPhaseIncrement;
            if (d->lfoPhase >= 2 * PI) d->lfoPhase -= 2 * PI;

            /* Skip using LFO value – keep oscillator at base frequency     */
            d->phaseIncrement = 2 * PI * d->frequency / sample_rate;

            /* Advance main oscillator phase                                */
            d->phase += d->phaseIncrement;
            if (d->phase >= 2 * PI) d->phase -= 2 * PI;

            d->sampleCount++;
        }
    }

    return paContinue;
}
