"""
Chord Library

Turns a Roman-numeral chord symbol into its raw notes. NO register, NO
voicing, NO MIDI — just "which notes are in this chord." The octave
clamp, voice-leading, and rotation all happen downstream in the resolver.

HOW CHORDS ARE BUILT: stack thirds. Start on the root (0) and stack
thirds, where each third is either minor (3 semitones) or major (4).

  - The TRIAD is the first two thirds:
        uppercase (major):  +4 then +3   -> 0, 4, 7
        lowercase (minor):  +3 then +4   -> 0, 3, 7
        °  diminished:      +3 then +3   -> 0, 3, 6
        +  augmented:       +4 then +4   -> 0, 4, 8

  - The 7th is just the NEXT third: +3 by default (dominant/minor 7th),
    +4 for a major 7th (maj7) or a half-diminished chord (ø).
        V7    -> 0,4,7,10      Imaj7 -> 0,4,7,11
        vii°7 -> 0,3,6,9       vii°ø7 -> 0,3,6,10

  - 9ths / 11ths / 13ths keep stacking to their natural scale tones.

Everything above is a stacked third. On TOP of the stack sit chromatic
COLORS — #9, b9, #11, b13, add9 — each one note added at a fixed
distance from the root, and b5/#5/sus which nudge a note already there.
A color is one entry that behaves the same under every root and quality,
so `VI#9` and `bviihalfdim#9` reuse the exact same #9.

Output:
  chord_intervals(symbol) -> sorted semitones above the ROOT (a #9 stays
                             15, not 3, so the resolver can place it high).
"""

# Where each Roman numeral's root sits, in semitones above the key tonic.
# A b/# prefix shifts it by ∓1.
DEGREE_OFFSET = {
    "I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11,
}

# How high a seventh/extension token stacks.
EXTENSION_REACH = {
    "7": 7, "maj7": 7, "°7": 7, "dim7": 7,
    "9": 9, "maj9": 9,
    "11": 11, "13": 13,
}

# Chromatic colors that ADD one note at a fixed distance above the root.
COLOR_ADD = {"add9": 14, "b9": 13, "#9": 15, "#11": 18, "b13": 20}

# Modifier tokens, longest first so multi-char tokens win while scanning.
MODIFIER_ORDER = [
    "maj9", "maj7", "halfdim", "dim7", "sus2", "sus4", "add9",
    "dim", "aug", "#11", "b13", "#9", "b9", "b5", "#5",
    "°7", "°", "ø", "+", "13", "11", "9", "7",
]


def _parse(symbol):
    """Split a symbol into (root_offset, is_major, [modifier tokens])."""
    i = 0
    accidental = 0
    if i < len(symbol) and symbol[i] in "b#":
        accidental = -1 if symbol[i] == "b" else 1
        i += 1

    roman = ""
    while i < len(symbol) and symbol[i] in "iIvV":
        roman += symbol[i]
        i += 1
    if roman.upper() not in DEGREE_OFFSET:
        raise ValueError(f"Unknown Roman numeral in chord symbol: {symbol!r}")

    rest = symbol[i:]
    tokens = []
    while rest:
        for tok in MODIFIER_ORDER:
            if rest.startswith(tok):
                tokens.append(tok)
                rest = rest[len(tok):]
                break
        else:
            raise ValueError(f"Unknown modifier {rest!r} in chord symbol: {symbol!r}")

    return DEGREE_OFFSET[roman.upper()] + accidental, roman.isupper(), tokens


def chord_intervals(symbol):
    """The chord's notes as sorted semitone offsets from its root."""
    _root, is_major, tokens = _parse(symbol)

    # The two triad thirds, overridden by an explicit quality. Diminished,
    # fully-diminished (°7), and half-diminished (ø) all flatten the fifth.
    thirds = [4, 3] if is_major else [3, 4]
    if any(t in ("°", "dim", "°7", "dim7", "halfdim", "ø") for t in tokens):
        thirds = [3, 3]
    elif any(t in ("+", "aug") for t in tokens):
        thirds = [4, 4]

    # Stack the triad.
    notes = [0]
    for third in thirds:
        notes.append(notes[-1] + third)

    # How far up do we stack? (° and ø both extend a triad to a 7th.)
    reach = max((EXTENSION_REACH[t] for t in tokens if t in EXTENSION_REACH),
                default=0)
    if any(t in ("halfdim", "ø") for t in tokens):
        reach = max(reach, 7)

    if reach >= 7:
        # The 7th is the next third: +4 for maj7 / half-diminished, else +3.
        seventh_third = 4 if any(t in ("maj7", "maj9", "halfdim", "ø")
                                 for t in tokens) else 3
        notes.append(notes[-1] + seventh_third)
    if reach >= 9:
        notes.append(14)    # natural 9th
    if reach >= 11:
        notes.append(17)    # natural 11th
    if reach >= 13:
        notes.append(21)    # natural 13th

    # Chromatic colors on top.
    if "sus2" in tokens:
        notes[1] = 2
    if "sus4" in tokens:
        notes[1] = 5
    if "b5" in tokens:
        notes[2] = 6
    if "#5" in tokens:
        notes[2] = 8
    for tok in tokens:
        if tok in COLOR_ADD:
            notes.append(COLOR_ADD[tok])

    return sorted(set(notes))


def chord_root_offset(symbol):
    """Semitones of the chord root above the key tonic (V -> 7, ii -> 2)."""
    root, _is_major, _tokens = _parse(symbol)
    return root


def notes_from_root(root_note, intervals):
    """
    Place a chord's root-relative intervals on a concrete root note.
    e.g. root_note=1, intervals=[0,3,7] -> [1,4,8].
    """
    return [root_note + iv for iv in intervals]


def chord_to_midi(instrument_root_midi, notes):
    """
    Shift a chord's notes onto the instrument's actual root MIDI note,
    giving concrete MIDI note numbers.
    e.g. instrument_root_midi=60 (C4), notes=[2,5,9] -> [62,65,69].
    """
    return [instrument_root_midi + n for n in notes]


def voice_lead(chord_notes, last_chord_notes):
    """
    Voice-lead a chord toward the previous one: return the inversion of
    chord_notes that sits closest to last_chord_notes, i.e. the smallest
    total semitone distance (each note measured to its nearest note in the
    last chord). Candidates are the chord's inversions, each octave-placed
    to sit nearest, so the chord shape is preserved.

    With no previous chord (None/empty), the chord is returned unchanged.
    """
    if not last_chord_notes:
        return sorted(chord_notes)

    def distance(voicing):
        return sum(min(abs(n - p) for p in last_chord_notes) for n in voicing)

    notes = sorted(chord_notes)
    best = None
    for i in range(len(notes)):                       # each inversion
        inversion = notes[i:] + [n + 12 for n in notes[:i]]
        for k in range(-5, 6):                         # octave-place it nearest
            candidate = [n + 12 * k for n in inversion]
            if best is None or distance(candidate) < distance(best):
                best = candidate
    return sorted(best)


def rotate_voicing(voicing, index):
    """
    Rotate a voicing off its baseline by `index` inversions: move the
    lowest note up an octave, repeated `index` times. index 0 leaves the
    baseline untouched; higher indices lift more notes over the top.
    (index comes from Instrument.voicing_index.)
    """
    notes = sorted(voicing)
    for _ in range(index):
        notes = notes[1:] + [notes[0] + 12]
    return sorted(notes)


def clamp_to_register(voicing, range_bottom, range_span):
    """
    Shift the whole voicing by whole octaves (no re-inversion) so that as
    many notes as possible land in the instrument's register
    [range_bottom, range_bottom + range_span). The bottom is the
    instrument's octave; range_span (in semitones) is the arousal-driven
    height (register_octaves * 12). Ties keep the lower placement, so a
    voicing left with a single note in range drops an octave to put the
    majority in range.
    """
    top = range_bottom + range_span
    best_shift, best_count = 0, -1
    for k in range(-6, 7):        # ascending so ties keep the lower placement
        shift = 12 * k
        count = sum(range_bottom <= n + shift < top for n in voicing)
        if count > best_count:
            best_count, best_shift = count, shift
    return [n + best_shift for n in voicing]


if __name__ == "__main__":
    # Everything the progression engine emits, plus the wishlist chords.
    demo = [
        "I", "ii", "vii°",
        "Imaj7", "Imaj9", "V7", "ii9", "vii°ø7", "vii°ø9",
        "VI#9", "bviihalfdim#9", "Vsus4", "iisus2", "IV°7", "bVIIadd9",
    ]
    for sym in demo:
        print(f"{sym:15s} intervals={chord_intervals(sym)}")
