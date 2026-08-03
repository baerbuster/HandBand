"""
EMOTE (Emotional Mathematical Optimization
Translation Engine)
EMOTE is HandBand's core intelligence layer that
transforms a single emotional state value (-1 to +1)
into multiple abstract dimensions grounded in
affective science. Its foundation rests on Russell's
Circumplex Model of Affect, the most empirically
validated framework in emotion research, which
demonstrates that emotional experience can be
reliably captured through two independent
orthogonal dimensions: valence (pleasure-displeasure)
and arousal (activation-deactivation).
Scientific Foundation
The Circumplex Model, validated across thousands
of empirical studies since 1980, shows that all
emotional states occupy positions within a
two-dimensional space. Valence represents the
hedonic quality of experience (positive to negative),
while arousal represents physiological and
psychological activation (energized to calm). These
dimensions are mathematically independent - you can
experience any combination of valence and arousal,
from high-arousal positive states (excitement,
elation) to low-arousal negative states (depression,
fatigue).
EMOTE's transformation functions are informed by
psychophysical principles, particularly Stevens'
Power Law, which demonstrates that human perception
often scales as a power function of stimulus
intensity. While Stevens' research focused on
sensory perception (light, sound, touch), the
underlying principle - that perceptual experience
follows nonlinear transformations of input - applies
to emotional state mapping as well.
Implementation
EMOTE takes HandBand's single input value and
performs two simultaneous transformations:
Valence maps linearly to the input - it
represents the most fundamental, directly
proportional relationship between input and
emotional quality. As input moves from -1
(negative/dysregulated) through 0 (neutral) to +1
(positive/regulated), valence changes at a constant
rate.
Arousal follows a power law transformation,
mapping the absolute value of input raised to a
configurable exponent. This creates the
characteristic U-shaped curve where emotional
extremes (both negative and positive) produce high
physiological activation, while the neutral center
represents calm, low-arousal states. The specific
exponent is configurable, allowing the system to be
tuned through experimentation and eventual
biosensor feedback.
Architectural Role
EMOTE contains pure mathematical transformation
functions but makes no domain-specific decisions
about notes, sounds, or musical implementation. It
outputs abstract numerical values (valence and
arousal) that Musical Domain and Sonic Domain
interpret according to their own specialized logic.
This separation of concerns ensures EMOTE remains a
clean mathematical layer - transforming emotional
state into scientifically grounded dimensions
without prescribing how those dimensions should
manifest as music.
Evolution Path
The system begins with these foundational
transformations based on established affective
science, but its long-term design embraces learned
optimization. As the biosensor feedback loop closes,
EMOTE will discover which transformation curves and
dimensional profiles actually succeed at moving
users between emotional states. It will learn
personal calibration - that for a specific user,
moving from anxiety to focus might require a
particular arousal exponent or valence offset that
differs from another user's optimal profile.
Eventually, integration with Northstar will provide
historical context, allowing EMOTE to understand not
just "input is at -0.3" but "user wants to reach
their recorded 'deep focus' state and has been
trending toward scattered attention for the past
hour." The system discovers its own optimal pathways
while maintaining the scientific framework of
valence-arousal space as its foundation.
"""

#===================#
#===Configurables===#
#===================#

arousal_exp = 2.0

class EMOTE:
    def __init__(self):
        """
        Initialize EMOTE transformation engine.
        """
        self.arousal_exp = arousal_exp
    
    def transform(self, input_val):
        """
        Transform single emotional state input into 
        valence-arousal dimensions.
        
        Args:
            input_value (float): Emotional state 
                ranging from -1 (negative/dysregulated) 
                through 0 (neutral) to +1 
                (positive/regulated)
        
        Returns:
            dict: {
                'valence': float [-1, 1],
                'arousal': float [0, 1]
            }
        """
        valence = input_val
        arousal = abs(input_val) ** self.arousal_exp
        return {'valence': valence, 'arousal': arousal}