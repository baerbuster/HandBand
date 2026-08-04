"""
Chord Progression Engine

Phase 3 of Musical Intelligence. Takes valence and
arousal from EMOTE and produces a full Roman-numeral
chord progression as a flat list of 16th-note slots.

The pipeline:
  1. prog_length — how many measures (valence-driven)
  2. chord_density — how many chord changes (arousal-driven)
  3. repetition_pattern — section structure: AABA, ABCAB, etc.
  4. For each unique section:
       a. build_starting_section_chords — Markov selection
          from the diatonic pool using valence affinities,
          harmonic transition weights, and novelty pressure
       b. apply_cadence_type — force a cadential ending
       c. apply_extensions — optionally color chords with
          diatonic 7ths and 9ths when arousal is high
       d. apply_duration_archetype — spread chords across
          the section's 16th-note slots
  5. Tile repeated sections from the repetition pattern.

Output: flat list of Roman numeral strings (or "C" for
continuation slots), one entry per 16th-note position.
"""

from MI_Pattern_Primitives import weighted_choice, selected_patterns, generate_variation, archetype_placer
import random

STATIC_DENSITY_SCALAR = 4
GAUSSIAN_SHARPNESS_REPETITION_PATTERN = 2
RESOLUTION_MULT = 6
NOVELTY_FACTOR_BASE_CHORDS = 0.08
DIATONIC_POOL = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
DIATONIC_EXTENSIONS = {
    "I":    ("Imaj7",  "Imaj9"),
    "ii":   ("ii7",    "ii9"),
    "iii":  ("iii7",   "iii9"),
    "IV":   ("IVmaj7", "IVmaj9"),
    "V":    ("V7",     "V9"),
    "vi":   ("vi7",    "vi9"),
    "vii°": ("vii°ø7", "vii°ø9"),
}
EXTENSION_AROUSAL_THRESHOLD = 0.85
CHORD_VALENCE_AFFINITIES = {
    "I": 1.0, "IV": 0.5, "V": 0.3,
    "vi": -0.3, "ii": -0.2, "iii": -0.4, "vii°": -1.0
}
TRANSITIONS = {
    "I":    {"IV": 2, "V": 2, "vi": 1},
    "ii":   {"V": 3, "IV": 1},
    "iii":  {"vi": 2, "IV": 1},
    "IV":   {"I": 2, "V": 3, "ii": 1},
    "V":    {"I": 4, "vi": 2},
    "vi":   {"ii": 2, "IV": 2, "V": 1},
    "vii°": {"I": 4},
}


def calculate_prog_length_weights(valence):
    """Exponential weights over [1, 2, 4, 8] measures. Negative valence favors short; positive favors long."""
    return [2 ** (max(0, -valence) * i + max(0, valence) * (3 - i)) for i in range(4)]


def prog_length_calculator(valence):
    """Pick a progression length in measures: 1, 2, 4, or 8."""
    weights = calculate_prog_length_weights(valence)
    return weighted_choice([1, 2, 4, 8], weights)


def chord_density_calculator(prog_measure_length, arousal):
    """How many chord changes fit in the progression. Scales with arousal."""
    return max(1, round(prog_measure_length * (arousal ** 0.9) * STATIC_DENSITY_SCALAR))


def calculate_cadence_weights(valence, arousal):
    """
    Linear weights for the four cadence types.
    Valence drives authentic vs deceptive; arousal drives half vs plagal.
    """
    authentic_weight = max(1, valence * 4)
    plagal_weight    = max(1, 4 * (1 - arousal))
    half_weight      = max(1, 4 * arousal)
    deceptive_weight = max(1, -4 * valence)
    return [authentic_weight, plagal_weight, half_weight, deceptive_weight]


def cadence_type_calculator(valence, arousal):
    """Pick a cadence type: authentic, plagal, half, or deceptive."""
    cadence_weights = calculate_cadence_weights(valence, arousal)
    return weighted_choice(["authentic", "plagal", "half", "deceptive"], cadence_weights)


def chord_duration_archetype_calculator():
    """Pick a duration shape for spreading chords across a section."""
    return weighted_choice(["front", "back", "center", "alternating", "symmetrical", "random"], [1,1,1,1,1,1])


def repetition_pattern_calculator(valence, arousal, chord_density):
    """
    Build a section repetition pattern (e.g. AABA, ABCAB).
    Arousal drives how many unique sections; valence drives
    how much earlier material returns.
    """
    partition_number = selected_patterns(chord_density, arousal, GAUSSIAN_SHARPNESS_REPETITION_PATTERN, maximum=8)
    return generate_variation(partition_number, arousal, valence, repeat_mult=10, return_mult=5, chunk_mult=8, novelty_factor=0.1)


def calculate_extension_weights(arousal):
    """
    Weights for [triad, 7th, 9th] given arousal above the threshold.
    t=0 (arousal=0.85): triads only.
    t=0.5 (arousal=0.925): triads and 7ths equally, no 9ths yet.
    t=1.0 (arousal=1.0): all three equally likely.
    """
    t = (arousal - EXTENSION_AROUSAL_THRESHOLD) / (1 - EXTENSION_AROUSAL_THRESHOLD)
    triad_w   = 1
    seventh_w = min(1, 2 * t)
    ninth_w   = max(0, 2 * t - 1)
    return [triad_w, seventh_w, ninth_w]


def apply_extensions(chords, arousal):
    """
    Optionally color each chord with a diatonic 7th or 9th.
    Only runs when arousal crosses EXTENSION_AROUSAL_THRESHOLD.
    Extensions are always diatonic — fixed by chord function.
    """
    if arousal < EXTENSION_AROUSAL_THRESHOLD:
        return chords
    result = []
    for chord in chords:
        seventh, ninth = DIATONIC_EXTENSIONS[chord]
        ext_weights = calculate_extension_weights(arousal)
        result.append(weighted_choice([chord, seventh, ninth], ext_weights))
    return result


def build_starting_section_chords(valence, arousal, section_chord_density):
    """
    Select a sequence of Roman numeral chords for one section.

    Each slot is chosen via weighted draw that combines three forces:
    - Valence affinity: how well each chord matches the emotional tone
    - Harmonic transitions: resolution gravity from the previous chord
    - Novelty pressure: small boost for chords not yet used in this section
    """
    resolution_strength = (1 - arousal) * RESOLUTION_MULT
    chords = []
    used = set()
    for slot in range(section_chord_density):
        weights = {chord: max(0.5, 1 + CHORD_VALENCE_AFFINITIES[chord] * valence)
                   for chord in DIATONIC_POOL}
        if chords:
            for target, boost in TRANSITIONS.get(chords[-1], {}).items():
                weights[target] += boost * resolution_strength
        novelty_boost = sum(weights.values()) * NOVELTY_FACTOR_BASE_CHORDS
        for chord in DIATONIC_POOL:
            if chord not in used:
                weights[chord] += novelty_boost
        chosen = weighted_choice(list(weights.keys()), list(weights.values()))
        chords.append(chosen)
        used.add(chosen)
    return chords


def apply_cadence_type(valence, arousal, section_chords):
    """
    Force a cadential ending onto the section by overwriting
    the last one or two chords with the chosen cadence formula.
    """
    cadence_type = cadence_type_calculator(valence, arousal)
    if cadence_type == "authentic":
        cadence = ["V", "I"]
    elif cadence_type == "plagal":
        cadence = ["IV", "I"]
    elif cadence_type == "deceptive":
        cadence = ["V", "vi"]
    elif cadence_type == "half":
        cadence = ["V"]
    # Trim cadence if the section is shorter than the cadence formula
    cadence = cadence[-len(section_chords):]
    for i, chord in enumerate(reversed(cadence)):
        section_chords[-(i+1)] = chord
    return section_chords


def choose_duration_archetype(section_length):
    """
    Pick a duration shape and build its slot-weight layout.

    Returns the weight vector plus its capacity: the number of
    slots that are actually open for a chord to land (non-zero
    weight). Some archetypes (e.g. alternating) deliberately
    leave slots empty, so capacity can be less than section_length.
    The caller must clamp its chord count to this capacity before
    generating chords, so nothing overflows the layout.
    """
    duration_archetype = chord_duration_archetype_calculator()
    if duration_archetype == "front":
        weights = [section_length - i for i in range(section_length)]
    elif duration_archetype == "back":
        weights = [section_length + i for i in range(section_length)]
    elif duration_archetype == "center":
        mid = section_length / 2
        weights = [mid - abs(i - mid) for i in range(section_length)]
    elif duration_archetype == "alternating":
        start = random.randint(0, 1)
        weights = [1 if i % 2 == start else 0 for i in range(section_length)]
    elif duration_archetype == "random":
        weights = [1 for i in range(section_length)]
    elif duration_archetype == "symmetrical":
        mid = section_length // 2
        if mid == 0:
            weights = [1]
        else:
            offset = weighted_choice(list(range(mid)), [mid - i for i in range(mid)])
            first_half = [max(0, mid - abs(i - offset)) for i in range(mid)]
            center = [first_half[-1]] if section_length % 2 == 1 else []
            weights = first_half + center + first_half[::-1]

    capacity = sum(1 for w in weights if w > 0)
    return weights, capacity


def apply_duration_archetype(section_length, section_chords, weights):
    """
    Drop the chords into the layout chosen earlier.

    Places one hit per chord into the reserved slots of the given
    weight vector; every other slot holds the previous chord ("C").
    The chord count is already clamped to the layout's capacity
    upstream, so this can never be asked for more slots than exist.
    """
    positions = list(range(section_length))
    chord_hits = archetype_placer(len(section_chords), weights, positions)
    section = []
    counter = 0
    for i in range(section_length):
        if i in chord_hits:
            section.append(section_chords[counter])
            counter += 1
        else:
            section.append("C")
    return section


def roman_numeral_chord_progression_calculator(valence, arousal, prog_measure_length, repetition_pattern, chord_density):
    """
    Build the full chord progression as a flat 16th-note slot list.
    Unique sections are constructed once, then tiled across the
    repetition pattern.
    """
    roman_numeral_chord_prog = ["C"] * prog_measure_length * 16
    section_length = len(roman_numeral_chord_prog) // len(repetition_pattern)
    section_chord_density = chord_density // len(repetition_pattern)

    section_indices = {}
    for i, letter in enumerate(repetition_pattern):
        start = i * section_length
        end = start + section_length
        if letter not in section_indices:
            section_indices[letter] = []
        section_indices[letter].append(list(range(start, end)))

    section_chords = {}
    section_weights = {}
    for letter in section_indices:
        # Choose the rhythmic shape first, then clamp the chord count to
        # the slots it actually offers, so generation and placement agree.
        weights, capacity = choose_duration_archetype(section_length)
        section_weights[letter] = weights
        n = max(1, min(section_chord_density, capacity))
        section_chords[letter] = build_starting_section_chords(valence, arousal, n)
        section_chords[letter] = apply_cadence_type(valence, arousal, section_chords[letter])
        section_chords[letter] = apply_extensions(section_chords[letter], arousal)

    for letter in section_chords:
        section_roman_numeral_prog = apply_duration_archetype(section_length, section_chords[letter], section_weights[letter])
        for occurrence in section_indices[letter]:
            for local_i, global_i in enumerate(occurrence):
                roman_numeral_chord_prog[global_i] = section_roman_numeral_prog[local_i]

    return roman_numeral_chord_prog


def create_song_form(valence, arousal):
    """
    Build the shared song form — the structural skeleton every
    downstream engine aligns to. Returns (prog_measure_length,
    chord_density, repetition_pattern).

    The repetition pattern is the canonical form of the whole piece:
    it is generated here, in the harmonic engine, because form emerges
    from the harmony. Other engines (e.g. the accent engine) receive
    this same form rather than inventing their own, so the arrangement
    shares one structure.
    """
    prog_measure_length = prog_length_calculator(valence)
    chord_density = chord_density_calculator(prog_measure_length, arousal)
    repetition_pattern = repetition_pattern_calculator(valence, arousal, chord_density)
    return prog_measure_length, chord_density, repetition_pattern


def create_chord_progression(valence, arousal, form=None):
    """
    Main entry point. Takes valence and arousal, returns a flat
    list of Roman numeral chord symbols at 16th-note resolution.

    If a precomputed song form (from create_song_form) is passed in,
    it is used directly so the chord progression and any other engine
    sharing that form stay structurally aligned; otherwise the form is
    generated internally.
    """
    if form is None:
        form = create_song_form(valence, arousal)
    prog_measure_length, chord_density, repetition_pattern = form
    return roman_numeral_chord_progression_calculator(valence, arousal, prog_measure_length, repetition_pattern, chord_density)
