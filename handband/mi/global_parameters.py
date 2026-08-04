"""
Global Parameters

Tier 1 of Musical Intelligence. No dependencies on
any downstream engine — just takes valence straight
from EMOTE and produces the system-wide tempo, and
holds the key.

BPM uses a logarithmic mapping so that perceptual
change feels even across the slider. Moving from 80
to 100 feels about the same as moving from 140 to 180.
The equation is just a * (b/a)^v, where v is valence
normalized to 0-1.

Min/max BPM are configurable at the caller level, not
hardcoded.

(Register width is NOT global — each instrument owns its
own arousal-driven register height via
Instrument.register_octaves.)
"""

# The song's key, as the tonic's pitch class (0 = C). Fixed at C for now;
# everything downstream reads this rather than assuming a key.
CURRENT_KEY = 0   # C


def calculate_global_parameters(valence, min_bpm, max_bpm):
    """
    Turn valence into the system-wide BPM (sad = slow, happy = fast).

    Valence comes in as -1 to +1 from EMOTE, gets
    remapped to 0-1 internally for the log curve.
    """
    v = (valence + 1) / 2
    return min_bpm * (max_bpm / min_bpm) ** v