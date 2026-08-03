"""
Instrument

The first object in HandBand's Musical Intelligence layer. Everything
upstream (chord progression, accent map, groove vector, and the raw
valence/arousal signals) is floating data produced by stateless
engines. An Instrument is a thing with identity and behavior that READS
that shared data and decides how it, personally, responds to it.

This is a plain concrete class — deliberately NO abstract methods, so
nothing is forced on any particular instrument (drums may later want
funky per-piece placement, etc.). Each real instrument (chord, bass,
drums, ...) is an INSTANCE constructed with its own personal parameters.

It defines five shared functions, each of the same shape:
a shared emotion-driven input + a per-instrument parameter.

  1. Accent Following   — a 0-1 scalar → a max dB volume boost applied
                          uniformly to every accented slot.
  2. Groove Following   — a 0-1 scalar → a multiplier on the groove
                          vector's already-computed displacement.
  3. Note Density       — the shared activity signal (arousal) mapped
                          through the instrument's max articulation rate
                          into a per-measure hit count.
  4. Syncopation        — the shared syncopation signal ((valence+1)/2)
                          scaled by a per-instrument responsiveness,
                          reweighting placement toward weak metric slots.
  5. Voicing            — a soft arousal-biased draw for how far to
                          rotate a chord OFF its voice-leading baseline
                          (harmony only). Just the emotional DECISION —
                          an index; the voice-leading baseline and the
                          concrete rotation are applied downstream, at
                          render time, not here.

NOT in this class (each instrument handles these itself):
  - Pitch resolution (Roman/scale-degree → concrete notes) and the
    voice-leading baseline + rotation that realize the voicing index.
  - Placement (where notes land in time) and duration.

The numeric constants here (MAX_ACCENT_DB, the metric hierarchy) are
first-pass values meant to be tuned later; the structure is the point.
"""

from MI_Pattern_Primitives import weighted_choice

SLOTS_PER_MEASURE = 16
MAX_ACCENT_DB = 6.0          # loudest boost a fully accent-following instrument adds
VOICING_WEIGHT_FLOOR = 0.1   # keeps every rotation index reachable (never forbidden)
MIN_OCTAVE_RANGE = 1         # every instrument's register is at least one octave tall

# Metric hierarchy for one measure of 16th-note slots. Higher = stronger
# metric position. Beat 1 is strongest, the other three beats are strong,
# the 8th-note offbeats are medium, the in-between 16ths are weakest.
METRIC_STRENGTH = [
    4, 1, 2, 1,   # beat 1 . e . a
    3, 1, 2, 1,   # beat 2 . e . a
    4, 1, 2, 1,   # beat 3 . e . a   (bar midpoint, nearly as strong as 1)
    3, 1, 2, 1,   # beat 4 . e . a
]


class Instrument:
    """
    One instrument's personal response to the shared musical data.

    The fixed personal parameters are set at construction; the live song
    data (accent map, groove vector, arousal, valence) is passed into the
    methods, since it changes every time a song is generated.
    """

    def __init__(self, name, octave, max_octave_range,
                 accent_follow=0.5,
                 groove_follow=0.5,
                 max_density_rate=8,
                 syncopation_follow=0.5):
        """
        name               : label for this instrument (e.g. "bass").
        octave             : bottom of this instrument's register, as an
                             octave number. The register anchors where its
                             notes sit (MIDI: the key's tonic at this
                             octave = 12 * (octave + 1) + key).
        max_octave_range   : tallest this instrument's register gets, in
                             octaves (at full arousal). Arousal scales the
                             live height from MIN_OCTAVE_RANGE up to this
                             (see register_octaves); voicings are clamped to
                             fit. So the emotional input widens the
                             instrument, per-instrument.
        accent_follow      : 0-1. How strongly it emphasizes accented
                             slots; scaled by MAX_ACCENT_DB. 0 = ignores
                             accents entirely.
        groove_follow      : 0-1. Multiplier on the groove displacement it
                             applies. 0 = plays on the grid.
        max_density_rate   : max hits per measure at full activity
                             (e.g. 16 = can hit every 16th, 8 = up to
                             eighth notes).
        syncopation_follow : 0-1. How hard it chases the syncopation
                             weighting. 0 = ignores it (pure metric feel).
        """
        self.name = name
        self.octave = octave
        self.max_octave_range = max_octave_range
        self.accent_follow = accent_follow
        self.groove_follow = groove_follow
        self.max_density_rate = max_density_rate
        self.syncopation_follow = syncopation_follow

    # ------------------------------------------------------------------
    # 1. Accent Following
    # ------------------------------------------------------------------
    def accent_volume(self, accent_map):
        """
        Turn the shared binary accent map into this instrument's per-slot
        volume boost (in dB). Every accented slot gets the SAME boost —
        accent_follow * MAX_ACCENT_DB — and every other slot gets 0.
        """
        boost = self.accent_follow * MAX_ACCENT_DB
        return [boost if slot else 0.0 for slot in accent_map]

    # ------------------------------------------------------------------
    # 2. Groove / Delay Following
    # ------------------------------------------------------------------
    def groove_offsets(self, groove_vector):
        """
        Scale the shared groove displacement vector by how much this
        instrument leans into the groove. The groove vector already
        carries signed magnitude per slot; this just multiplies it, so
        0 = dead on the grid, 1 = the full groove feel.
        """
        return [offset * self.groove_follow for offset in groove_vector]

    # ------------------------------------------------------------------
    # 3. Note Density
    # ------------------------------------------------------------------
    def density_per_measure(self, arousal):
        """
        Map the shared activity signal (arousal, 0-1) through this
        instrument's max articulation rate into a hit count for one
        measure. Floored at 1 so every measure plays at least once.
        """
        return max(1, round(arousal * self.max_density_rate))

    # ------------------------------------------------------------------
    # 3b. Register Height
    # ------------------------------------------------------------------
    def register_octaves(self, arousal):
        """
        Map the shared activity signal (arousal, 0-1) into this
        instrument's live register height, in octaves: MIN_OCTAVE_RANGE at
        arousal 0, up to max_octave_range at arousal 1. This is what lets
        the emotional input widen (or tighten) each instrument's spread.
        """
        return MIN_OCTAVE_RANGE + (self.max_octave_range - MIN_OCTAVE_RANGE) * arousal

    # ------------------------------------------------------------------
    # 4. Syncopation
    # ------------------------------------------------------------------
    def syncopation_weights(self, valence):
        """
        Produce a per-slot placement weight vector for one measure,
        reweighted toward the weak metric slots by this instrument's
        effective syncopation strength.

            signal = (valence + 1) / 2          # shared, 0-1
            s      = signal * syncopation_follow # this instrument's pull

        The weights interpolate between the plain metric hierarchy (s=0,
        favor the beat) and its inverse (s=1, favor the offbeats). At s=1
        strong slots keep the low end of the range — unlikely, never
        forbidden. s=0.5 is flat (no metric preference).
        """
        signal = (valence + 1) / 2
        s = signal * self.syncopation_follow

        hi = max(METRIC_STRENGTH)
        lo = min(METRIC_STRENGTH)
        # inverted strength: strongest metric slot becomes weakest weight
        inverted = [(hi + lo) - strength for strength in METRIC_STRENGTH]

        return [(1 - s) * strength + s * inv
                for strength, inv in zip(METRIC_STRENGTH, inverted)]

    # ------------------------------------------------------------------
    # 5. Voicing
    # ------------------------------------------------------------------
    def voicing_index(self, arousal, chord_size):
        """
        Choose how far to rotate a chord OFF its voice-leading baseline.

        Returns an index in 0..chord_size-1. Index 0 is the voice-led
        baseline (the smoothest connection to the previous chord); higher
        indices rotate the voicing further off it (more disjunct). This is
        a soft weighted draw biased by arousal — the weights interpolate
        between a reverse ramp (favors index 0) at arousal 0 and a forward
        ramp (favors the top index) at arousal 1, flat at 0.5. A weight
        floor keeps every index reachable, so nothing is ever forbidden.

        Only meaningful for harmony (chord_size >= 2); a single note has
        one voicing and returns 0.
        """
        if chord_size <= 1:
            return 0
        indices = list(range(chord_size))
        weights = [(1 - arousal) * (chord_size - 1 - i)
                   + arousal * i
                   + VOICING_WEIGHT_FLOOR
                   for i in indices]
        return weighted_choice(indices, weights)


if __name__ == "__main__":
    # Two contrasting instruments reading the same shared data.
    chords = Instrument("chords", 4, 3, accent_follow=0.3, groove_follow=0.2,
                        max_density_rate=8, syncopation_follow=0.2)
    bass = Instrument("bass", 2, 2, accent_follow=0.8, groove_follow=1.0,
                      max_density_rate=16, syncopation_follow=0.7)

    accent_map = [1 if i in (0, 4, 10) else 0 for i in range(SLOTS_PER_MEASURE)]
    groove_vector = [0.0, 0.0, 0.15, 0.0] * 4

    for inst in (chords, bass):
        print(f"[{inst.name}]")
        print("  accent volume :", inst.accent_volume(accent_map))
        print("  groove offsets:", [round(o, 3) for o in inst.groove_offsets(groove_vector)])
        print("  density/meas  : arousal 0.2 ->", inst.density_per_measure(0.2),
              " arousal 0.9 ->", inst.density_per_measure(0.9))
        sad = [round(w, 2) for w in inst.syncopation_weights(-0.8)]
        happy = [round(w, 2) for w in inst.syncopation_weights(0.8)]
        print("  sync weights (sad valence)  :", sad)
        print("  sync weights (happy valence):", happy)
        print()
