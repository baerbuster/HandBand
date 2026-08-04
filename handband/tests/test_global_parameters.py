"""
Global Parameters Test

Smoke test for the EMOTE → Global Parameters pipeline.
Feeds five points across the input range (-1 to +1)
through EMOTE, then into calculate_global_parameters,
and prints the results so you can eyeball whether
BPM is behaving.

What to look for:
- BPM tracks valence (-1 = min, +1 = max)
- The log curve on BPM means the middle value (0.0)
  should land around the geometric mean of min/max,
  not the arithmetic mean

(Register width is no longer global — it's per-instrument
via Instrument.register_octaves.)
"""

from emote import EMOTE
from MI_Global_Parameters import calculate_global_parameters

MIN_BPM = 80
MAX_BPM = 180

emote = EMOTE()

test_inputs = [-1.0, -0.5, 0.0, 0.5, 1.0]

for input_val in test_inputs:
    result = emote.transform(input_val)
    bpm = calculate_global_parameters(result['valence'], MIN_BPM, MAX_BPM)
    print(f"Input: {input_val:+.1f} → V: {result['valence']:+.2f}, A: {result['arousal']:.2f} → BPM: {bpm:.1f}")