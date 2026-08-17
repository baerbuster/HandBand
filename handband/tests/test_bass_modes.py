"""
Bass Modes Test

Test suite for mi/bass_modes.py, in the same style as the engine suites.
The module is a lookup table plus three small functions, so most of the
risk is in the DATA being internally consistent and in the symbol parser
handling every symbol the progression engine can emit.

- tables: every scale is 8 degrees, every degree name is in the semitone
  table, every mode ascends from the root to the octave, and every
  CHORD_TO_SCALE value names a real scale
- _base_chord: strips extensions, keeps the accidental, keeps the "°"
- mode_for_chord: the seven diatonic chords map to the seven church
  modes in order, extensions don't change the mode, and anything
  unrecognized falls back to ionian instead of crashing
- degree_to_semitone: agrees with the interval table for every mode and
  degree, and a negative degree is the same note an octave down
- modal_degree_label: spells the degree the way the chord's mode hears
  it, with "-" marking the lower octave, and agrees with the semitone
  math it's the display twin of
"""

import random
import sys

from handband.mi.bass_modes import (
    CHORD_TO_SCALE,
    SCALES,
    _base_chord,
    degree_to_semitone,
    interval_to_semitone,
    modal_degree_label,
    mode_for_chord,
)


# ============================================================
# TEST INFRASTRUCTURE
# ============================================================

passed = 0
failed = 0
errors = []

def run_test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  ✓ {name}")
    except AssertionError as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  ✗ {name} — {e}")
    except Exception as e:
        failed += 1
        errors.append((name, f"CRASH: {e}"))
        print(f"  ✗ {name} — CRASH: {e}")


# The seven diatonic chords, in degree order, and the mode each implies.
DIATONIC = [("I", "ionian"), ("ii", "dorian"), ("iii", "phrygian"),
            ("IV", "lydian"), ("V", "mixolydian"), ("vi", "aeolian"),
            ("vii°", "locrian")]

# Extension tokens the progression engine appends to a base chord.
EXTENSIONS = ["", "7", "9", "maj7", "maj9", "add9", "11", "13"]


def test_scales_are_eight_degrees():
    for name, scale in SCALES.items():
        assert len(scale) == 8, f"{name} has {len(scale)} degrees, expected 8"

def test_scale_degrees_are_known_intervals():
    for name, scale in SCALES.items():
        for degree in scale:
            assert degree in interval_to_semitone, \
                f"{name} uses unknown degree name {degree!r}"

def test_scales_span_an_octave():
    for name, scale in SCALES.items():
        semis = [interval_to_semitone[d] for d in scale]
        assert semis[0] == 0, f"{name} does not start on the root"
        assert semis[-1] == 12, f"{name} does not end on the octave"

def test_scales_ascend():
    for name, scale in SCALES.items():
        semis = [interval_to_semitone[d] for d in scale]
        for a, b in zip(semis, semis[1:]):
            assert b > a, f"{name} does not ascend: {semis}"

def test_chord_to_scale_values_exist():
    for chord, scale_name in CHORD_TO_SCALE.items():
        assert scale_name in SCALES, \
            f"{chord} maps to unknown scale {scale_name!r}"

def test_chord_to_scale_covers_the_diatonic_set():
    assert set(CHORD_TO_SCALE) == {c for c, _mode in DIATONIC}, \
        f"unexpected diatonic key set: {sorted(CHORD_TO_SCALE)}"

def test_negative_names_mirror_positive():
    # the below-tonic half of the interval table is the same degree, an
    # octave down
    for name, semi in interval_to_semitone.items():
        if name.startswith("-"):
            twin = name[1:]
            assert twin in interval_to_semitone, f"{name} has no positive twin"
            assert semi == interval_to_semitone[twin] - 12, \
                f"{name} is {semi}, expected {interval_to_semitone[twin] - 12}"

def test_base_chord_plain():
    for chord, _mode in DIATONIC:
        assert _base_chord(chord) == chord, f"{chord} was altered"

def test_base_chord_strips_extensions():
    assert _base_chord("V7") == "V"
    assert _base_chord("ii9") == "ii"
    assert _base_chord("Imaj9") == "I"
    assert _base_chord("IVadd9") == "IV"
    assert _base_chord("vi11") == "vi"

def test_base_chord_keeps_diminished_mark():
    assert _base_chord("vii°") == "vii°"
    assert _base_chord("vii°7") == "vii°"
    assert _base_chord("vii°ø7") == "vii°"

def test_base_chord_keeps_accidental():
    assert _base_chord("bVII") == "bVII"
    assert _base_chord("#IV°7") == "#IV°"

def test_mode_for_each_diatonic_chord():
    for chord, mode_name in DIATONIC:
        assert mode_for_chord(chord) is SCALES[mode_name], \
            f"{chord} should imply {mode_name}"

def test_mode_ignores_extensions():
    for chord, mode_name in DIATONIC:
        for ext in EXTENSIONS:
            symbol = chord + ext
            assert mode_for_chord(symbol) is SCALES[mode_name], \
                f"{symbol} should still imply {mode_name}"

def test_half_diminished_still_locrian():
    for symbol in ("vii°ø7", "vii°ø9", "vii°7"):
        assert mode_for_chord(symbol) is SCALES["locrian"], \
            f"{symbol} should stay locrian"

def test_unknown_symbol_falls_back_to_ionian():
    for symbol in ("bVII", "#IV", "N6", "", "???", "bviihalfdim#9"):
        assert mode_for_chord(symbol) is SCALES["ionian"], \
            f"{symbol!r} should fall back to ionian"

def test_mode_never_crashes():
    alphabet = "iIvVb#°ø7913majdusn "
    for _ in range(2000):
        symbol = "".join(random.choice(alphabet)
                         for _ in range(random.randint(0, 8)))
        mode = mode_for_chord(symbol)
        assert len(mode) == 8, f"{symbol!r} produced a malformed mode"

def test_degree_matches_interval_table():
    for name, scale in SCALES.items():
        for degree in range(1, 9):
            expected = interval_to_semitone[scale[degree - 1]]
            got = degree_to_semitone(scale, degree)
            assert got == expected, \
                f"{name} degree {degree}: {got} != {expected}"

def test_negative_degree_drops_an_octave():
    for name, scale in SCALES.items():
        for degree in range(1, 8):
            up = degree_to_semitone(scale, degree)
            down = degree_to_semitone(scale, -degree)
            assert down == up - 12, \
                f"{name} degree -{degree}: {down} != {up - 12}"

def test_degree_known_values():
    assert degree_to_semitone(SCALES["ionian"], 3) == 4      # natural 3rd
    assert degree_to_semitone(SCALES["dorian"], 3) == 3      # flat 3rd
    assert degree_to_semitone(SCALES["locrian"], 5) == 6     # flat 5th
    assert degree_to_semitone(SCALES["mixolydian"], 7) == 10  # flat 7th
    assert degree_to_semitone(SCALES["ionian"], 8) == 12     # the octave
    assert degree_to_semitone(SCALES["ionian"], -1) == -12   # tonic, octave down

def test_degree_the_same_degree_differs_by_mode():
    # the whole point of the module: one symbolic degree, different notes
    thirds = {name: degree_to_semitone(scale, 3) for name, scale in SCALES.items()}
    assert len(set(thirds.values())) > 1, \
        f"degree 3 is identical under every mode: {thirds}"

def test_degree_ascends_within_a_mode():
    for name, scale in SCALES.items():
        semis = [degree_to_semitone(scale, d) for d in range(1, 9)]
        for a, b in zip(semis, semis[1:]):
            assert b > a, f"{name} degrees do not ascend: {semis}"

def test_label_positive_is_the_mode_step():
    for chord, mode_name in DIATONIC:
        for degree in range(1, 9):
            expected = SCALES[mode_name][degree - 1]
            got = modal_degree_label(degree, chord)
            assert got == expected, \
                f"{chord} degree {degree}: {got!r} != {expected!r}"

def test_label_negative_is_prefixed():
    for chord, mode_name in DIATONIC:
        for degree in range(1, 8):
            expected = "-" + SCALES[mode_name][degree - 1]
            got = modal_degree_label(-degree, chord)
            assert got == expected, \
                f"{chord} degree -{degree}: {got!r} != {expected!r}"

def test_label_known_values():
    assert modal_degree_label(3, "I") == "3"
    assert modal_degree_label(3, "ii") == "b3"
    assert modal_degree_label(7, "V") == "b7"
    assert modal_degree_label(5, "vii°") == "b5"
    assert modal_degree_label(-7, "I") == "-7"

def test_label_agrees_with_semitones():
    # the display twin must never disagree with the note math
    for chord, _mode_name in DIATONIC:
        mode = mode_for_chord(chord)
        for degree in list(range(1, 9)) + list(range(-7, 0)):
            label = modal_degree_label(degree, chord)
            semi = degree_to_semitone(mode, degree)
            expected = interval_to_semitone[label.lstrip("-")]
            if label.startswith("-"):
                expected -= 12
            assert semi == expected, \
                f"{chord} degree {degree}: label {label!r} says {expected}, math says {semi}"


def main():
    # ============================================================
    # TABLE CONSISTENCY
    # ============================================================

    print("\n" + "=" * 60)
    print("TABLE CONSISTENCY")
    print("=" * 60)

    run_test("every scale has 8 degrees", test_scales_are_eight_degrees)

    run_test("every scale degree is a known interval name", test_scale_degrees_are_known_intervals)

    run_test("every scale runs root to octave", test_scales_span_an_octave)

    run_test("every scale ascends", test_scales_ascend)

    run_test("every CHORD_TO_SCALE value names a real scale", test_chord_to_scale_values_exist)

    run_test("CHORD_TO_SCALE covers exactly the diatonic chords", test_chord_to_scale_covers_the_diatonic_set)

    run_test("negative interval names are their positive twin, an octave down", test_negative_names_mirror_positive)


    # ============================================================
    # SYMBOL PARSING (_base_chord)
    # ============================================================

    print("\n" + "=" * 60)
    print("SYMBOL PARSING")
    print("=" * 60)

    run_test("a plain diatonic symbol is unchanged", test_base_chord_plain)

    run_test("extensions are stripped", test_base_chord_strips_extensions)

    run_test("the diminished mark survives", test_base_chord_keeps_diminished_mark)

    run_test("a b/# accidental survives", test_base_chord_keeps_accidental)


    # ============================================================
    # MODE_FOR_CHORD
    # ============================================================

    print("\n" + "=" * 60)
    print("MODE_FOR_CHORD")
    print("=" * 60)

    run_test("the seven diatonic chords give the seven church modes", test_mode_for_each_diatonic_chord)

    run_test("extensions never change the mode", test_mode_ignores_extensions)

    run_test("diminished and half-diminished stay locrian", test_half_diminished_still_locrian)

    run_test("an unrecognized symbol falls back to ionian", test_unknown_symbol_falls_back_to_ionian)

    run_test("random garbage never crashes the lookup", test_mode_never_crashes)


    # ============================================================
    # DEGREE_TO_SEMITONE
    # ============================================================

    print("\n" + "=" * 60)
    print("DEGREE_TO_SEMITONE")
    print("=" * 60)

    run_test("agrees with the interval table for every mode", test_degree_matches_interval_table)

    run_test("a negative degree is the same note an octave down", test_negative_degree_drops_an_octave)

    run_test("known values", test_degree_known_values)

    run_test("the same degree is a different note under a different mode", test_degree_the_same_degree_differs_by_mode)

    run_test("degrees ascend within a mode", test_degree_ascends_within_a_mode)


    # ============================================================
    # MODAL_DEGREE_LABEL
    # ============================================================

    print("\n" + "=" * 60)
    print("MODAL_DEGREE_LABEL")
    print("=" * 60)

    run_test("a positive degree spells the mode's step", test_label_positive_is_the_mode_step)

    run_test("a negative degree is the same label with a '-'", test_label_negative_is_prefixed)

    run_test("known values", test_label_known_values)

    run_test("the label always agrees with the semitone math", test_label_agrees_with_semitones)


    # ============================================================
    # SUMMARY
    # ============================================================

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 60)

    if errors:
        print("\nFAILURES:")
        for name, msg in errors:
            print(f"  ✗ {name}: {msg}")
    else:
        print("\nAll tests passed.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
