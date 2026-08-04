"""
Accent Pattern Engine

Phase 4 of Musical Intelligence (Tier 3). Sits alongside the
Groove/Delay engine and, like it, depends only on the progression
LENGTH inherited from the Chord Progression Engine — never on the
chords themselves. Its job is purely rhythmic: decide which 16th-note
slots are accented, so the instruments in the shared layer have an
emphasis map to follow.

The pipeline mirrors the chord engine on purpose:
  1. For each unique section of the shared repetition pattern:
       a. accent_density — how many accents land in it (p * b * x)
       b. choose_accent_archetype — pick a placement shape and its
          slot capacity
       c. apply_accent_archetype — drop the accents into the section's
          16th-note slots as a binary 1/0 pattern
  2. Tile repeated sections across the full length.

This engine does NOT generate its own repetition pattern. It receives
the shared song form from the harmonic engine (create_song_form), so
accents phrase against the same structure as the chords. Accent
placement itself is still driven by arousal alone.

Output: a flat binary accent matrix, one entry per 16th-note slot
(1 = accented, 0 = not), the same length as the chord progression.
"""

from handband.mi.pattern_primitives import (
    weighted_choice, density_calculator, archetype_placer,
)
import random

SLOTS_PER_MEASURE = 16
MAX_ACCENTS_PER_MEASURE = 8          # b — density scalar


def accent_density_calculator(section_measures, arousal):
    """
    How many accents fall in one section: p * b * x, where p is the
    section's length in measures, b is the max accents per measure, and
    x is arousal. Never less than 1.
    """
    return density_calculator(section_measures, MAX_ACCENTS_PER_MEASURE,
                              arousal, minimum=1)


def accent_archetype_calculator():
    """Pick a placement shape for the accents in a section."""
    return weighted_choice(
        ["front", "back", "center", "alternating", "even", "random"],
        [1, 1, 1, 1, 1, 1],
    )


def choose_accent_archetype(section_slots):
    """
    Pick an accent placement shape and build its slot-weight layout.

    Returns the archetype name, its weight vector, and its capacity —
    the number of slots actually open for an accent (non-zero weight).
    Some archetypes (e.g. alternating) leave slots empty, so capacity
    can be less than section_slots. The caller clamps its accent count
    to this capacity before placing, so nothing overflows the layout.

    "even" is a special case: its accents are spread by regular spacing
    at placement time rather than by weighted draw, so every slot is
    nominally open (capacity = section_slots).
    """
    archetype = accent_archetype_calculator()
    if archetype == "front":
        weights = [section_slots - i for i in range(section_slots)]
    elif archetype == "back":
        weights = [section_slots + i for i in range(section_slots)]
    elif archetype == "center":
        mid = section_slots / 2
        weights = [mid - abs(i - mid) for i in range(section_slots)]
    elif archetype == "alternating":
        start = random.randint(0, 1)
        weights = [1 if i % 2 == start else 0 for i in range(section_slots)]
    elif archetype == "random":
        weights = [1 for i in range(section_slots)]
    elif archetype == "even":
        weights = [1 for i in range(section_slots)]

    capacity = sum(1 for w in weights if w > 0)
    return archetype, weights, capacity


def apply_accent_archetype(section_slots, n_accents, archetype, weights):
    """
    Place n_accents into the section's 16th-note slots and return a
    binary pattern (1 = accented, 0 = not).

    "even" spreads the accents at regular spacing (first hit on the
    section's downbeat). Every other archetype draws positions from its
    weight vector without replacement. The accent count is already
    clamped to the layout's capacity upstream.
    """
    if archetype == "even":
        positions = [int(i * section_slots / n_accents) for i in range(n_accents)]
    else:
        positions = archetype_placer(n_accents, weights, list(range(section_slots)))
    hits = set(positions)
    return [1 if i in hits else 0 for i in range(section_slots)]


def accent_pattern_calculator(prog_measure_length, arousal, repetition_pattern):
    """
    Build the full accent matrix and tile the repetition pattern across
    the progression length. Unique sections are built once, then their
    binary patterns are copied into every occurrence.
    """
    accent_matrix = [0] * prog_measure_length * SLOTS_PER_MEASURE
    section_slots = len(accent_matrix) // len(repetition_pattern)
    section_measures = section_slots // SLOTS_PER_MEASURE

    section_indices = {}
    for i, letter in enumerate(repetition_pattern):
        start = i * section_slots
        section_indices.setdefault(letter, []).append(
            list(range(start, start + section_slots))
        )

    section_patterns = {}
    for letter in section_indices:
        # Choose the placement shape first, then clamp the accent count
        # to the slots it actually offers, so placement can't overflow.
        archetype, weights, capacity = choose_accent_archetype(section_slots)
        density = accent_density_calculator(section_measures, arousal)
        n = max(1, min(density, capacity))
        section_patterns[letter] = apply_accent_archetype(
            section_slots, n, archetype, weights
        )

    for letter, pattern in section_patterns.items():
        for occurrence in section_indices[letter]:
            for local_i, global_i in enumerate(occurrence):
                accent_matrix[global_i] = pattern[local_i]

    return accent_matrix


def create_accent_pattern(prog_measure_length, arousal, repetition_pattern):
    """
    Main entry point. Takes the inherited progression length (in
    measures), arousal, and the shared repetition pattern (the song
    form from the harmonic engine). Returns a flat binary accent matrix
    at 16th-note resolution (1 = accented slot, 0 = not).
    """
    return accent_pattern_calculator(prog_measure_length, arousal, repetition_pattern)


if __name__ == "__main__":
    from MI_Chord_Progression_Engine import create_song_form

    for valence, arousal in [(-0.6, 0.2), (0.2, 0.6), (0.7, 0.9), (1.0, 1.0)]:
        prog_measure_length, _chord_density, repetition_pattern = create_song_form(valence, arousal)
        matrix = create_accent_pattern(prog_measure_length, arousal, repetition_pattern)
        rows = ["".join("X" if s else "." for s in matrix[i:i + SLOTS_PER_MEASURE])
                for i in range(0, len(matrix), SLOTS_PER_MEASURE)]
        print(f"valence={valence} arousal={arousal} measures={prog_measure_length} "
              f"form={''.join(repetition_pattern)} accents={sum(matrix)}")
        for r in rows:
            print("  ", r)
        print()
