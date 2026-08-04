"""
Bass Modes

The bass line is generated in SYMBOLIC SCALE DEGREES that are key-relative
(degree 1 = the tonic of the key). To turn a degree into a concrete note
UNDER A CHORD, two things are needed: the chord's root, and the church
MODE the chord implies — the mode is what spaces the degrees, so the same
symbolic degree becomes a different chromatic note depending on which
chord is sounding (degree 3 is a natural 3rd over I, but a flat 3rd over
ii or vi).

This module holds the mode data and the lookup, ported straight from the
legacy engine (ProgrammableSong3.1.py: interval_to_semitone ~1752,
SCALES ~1804, CHORD_TO_SCALE ~1829, get_bass_note's degree math ~2306).
Scope here is DIATONIC only — the seven church modes, one per diatonic
chord — because the progression engine currently emits only
I, ii, iii, IV, V, vi, vii° and their 7th/9th extensions. When
non-diatonic chords arrive, mode_for_chord grows a contextual branch
(the legacy get_scale_for_chord, ~1841) for the borrowed/altered cases.
"""

# Interval name -> semitone offset from the chord root. A degree string
# like "b3" is 3 semitones, "5" is 7, "8" the octave. Negative names are
# the same degree an octave down (unused by the diatonic mode lookup, but
# kept whole since it's small and matches the legacy table).
interval_to_semitone = {
    # Below-tonic (negative) degrees
    "-1": -12, "-b2": -11, "-2": -10, "-b3": -9, "-3": -8, "-4": -7,
    "-#4": -6, "-b5": -6, "-5": -5, "-b6": -4, "-6": -3, "-b7": -2,
    "-7": -1,
    # Tonic and above
    "1": 0, "#1": 1, "b2": 1, "2": 2, "#2": 3, "b3": 3, "3": 4, "#3": 4,
    "b4": 4, "4": 5, "#4": 6, "b5": 6, "5": 7, "#5": 8, "b6": 8, "6": 9,
    "#6": 10, "b7": 10, "7": 11, "#7": 12, "8": 12,
}

# Each scale as its degrees, 1 through 8 (the 8 is the octave). Only the
# seven church modes are needed for the current diatonic vocabulary; the
# minor variants are kept as cheap, named building blocks for the future
# non-diatonic branch.
SCALES = {
    "ionian":         ["1", "2", "3", "4", "5", "6", "7", "8"],
    "dorian":         ["1", "2", "b3", "4", "5", "6", "b7", "8"],
    "phrygian":       ["1", "b2", "b3", "4", "5", "b6", "b7", "8"],
    "lydian":         ["1", "2", "3", "#4", "5", "6", "7", "8"],
    "mixolydian":     ["1", "2", "3", "4", "5", "6", "b7", "8"],
    "aeolian":        ["1", "2", "b3", "4", "5", "b6", "b7", "8"],
    "locrian":        ["1", "b2", "b3", "4", "b5", "b6", "b7", "8"],
    "natural_minor":  ["1", "2", "b3", "4", "5", "b6", "b7", "8"],
    "harmonic_minor": ["1", "2", "b3", "4", "5", "b6", "7", "8"],
    "melodic_minor":  ["1", "2", "b3", "4", "5", "6", "7", "8"],
}

# Which mode each diatonic chord implies — the modes of the major scale in
# order. Keyed to HandBand's OWN chord symbols: the degree sign here is
# U+00B0 ("°"), exactly what the progression engine emits ("vii°",
# "vii°ø7"), NOT the legacy engine's U+00BA ("º").
CHORD_TO_SCALE = {
    "I": "ionian",
    "ii": "dorian",
    "iii": "phrygian",
    "IV": "lydian",
    "V": "mixolydian",
    "vi": "aeolian",
    "vii°": "locrian",
}


def _base_chord(symbol):
    """
    Reduce a full chord symbol to its diatonic base — the accidental +
    Roman numeral, plus a trailing "°" if the chord is diminished. This is
    the CHORD_TO_SCALE key; extensions (7, 9, maj7, ø, ...) drop off because
    the base triad's mode already covers them.

    e.g. "V7" -> "V",  "ii9" -> "ii",  "vii°ø7" -> "vii°",  "Imaj9" -> "I".
    """
    i = 0
    base = ""
    if i < len(symbol) and symbol[i] in "b#":
        base += symbol[i]
        i += 1
    while i < len(symbol) and symbol[i] in "iIvV":
        base += symbol[i]
        i += 1
    if "°" in symbol:
        base += "°"
    return base


def mode_for_chord(symbol):
    """
    The church mode a chord implies, as a list of degree strings (see
    SCALES). Diatonic lookup via CHORD_TO_SCALE, defaulting to ionian for
    anything unrecognized so the bass never crashes on an unexpected symbol.
    """
    scale_name = CHORD_TO_SCALE.get(_base_chord(symbol), "ionian")
    return SCALES[scale_name]


def degree_to_semitone(mode, degree):
    """
    Turn a symbolic scale degree into a semitone offset from the chord root,
    spaced by `mode`. `degree` is HandBand's symbolic numbering: 1..8 above
    the root, and negative 1..7 for the same degree an octave BELOW (the
    magnitude is the degree, the sign marks the lower octave).

        pos = abs(degree) - 1  ->  mode[pos]  ->  interval_to_semitone
        degree < 0  ->  drop an octave (-12)

    e.g. over dorian, degree 3 -> "b3" -> 3;  over ionian, degree 3 -> 4.
    """
    pos = abs(degree) - 1
    semi = interval_to_semitone[mode[pos]]
    if degree < 0:
        semi -= 12
    return semi


def modal_degree_label(degree, chord):
    """
    Spell a symbolic scale degree the way the chord's MODE hears it — the
    label a musician would read. Under the chord's mode, degree `d` becomes
    the mode's `d`-th step, accidental and all; the octave-below region
    (negative degrees) is prefixed with "-".

        over I (ionian):  degree 3 -> "3"      degree -7 -> "-7"
        over ii (dorian): degree 3 -> "b3"     degree 7  -> "b7"

    This is purely for display (e.g. the score view); the note math itself
    goes through degree_to_semitone.
    """
    label = mode_for_chord(chord)[abs(degree) - 1]
    return label if degree >= 1 else "-" + label


if __name__ == "__main__":
    # Mode selection strips extensions down to the base triad's mode.
    assert mode_for_chord("V7") is SCALES["mixolydian"]
    assert mode_for_chord("ii9") is SCALES["dorian"]
    assert mode_for_chord("vii°ø7") is SCALES["locrian"]
    assert mode_for_chord("Imaj9") is SCALES["ionian"]

    # The same degree is a different chromatic note under a different mode.
    assert degree_to_semitone(SCALES["ionian"], 3) == 4    # natural 3rd
    assert degree_to_semitone(SCALES["dorian"], 3) == 3    # flat 3rd
    assert degree_to_semitone(SCALES["ionian"], 8) == 12   # octave
    assert degree_to_semitone(SCALES["ionian"], -1) == -12  # tonic, octave down
    print("bass_modes: all sanity checks passed")

    for sym in ("I", "ii", "iii", "IV", "V7", "vi9", "vii°ø7"):
        mode = mode_for_chord(sym)
        degrees = [degree_to_semitone(mode, d) for d in range(1, 9)]
        print(f"  {sym:8s} -> {mode}  semitones {degrees}")
