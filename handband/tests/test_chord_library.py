"""
Chord Library Test

Test suite for mi/chord_library.py, in the same style as the engine
suites. Two halves:

SPELLING — chord_intervals / chord_root_offset. Every quality, every
extension, every color the module documents, plus the invariants that
hold for all of them (sorted, unique, rooted at 0) and the errors that
should be raised for a symbol it can't parse.

PLACEMENT — the four functions that move an already-spelled chord
around: notes_from_root / chord_to_midi (pure offsets), voice_lead (the
nearest inversion to the last chord), rotate_voicing (rotation off that
baseline), clamp_to_register (whole-octave shift into a window). These
are tested by their invariants — pitch classes survive, shifts are whole
octaves, the chosen candidate really is the best one in the search space
— rather than by hardcoded voicings, since that's what downstream code
actually depends on.
"""

import random
import sys

from handband.mi.chord_library import (
    DEGREE_OFFSET,
    chord_intervals,
    chord_root_offset,
    chord_to_midi,
    clamp_to_register,
    notes_from_root,
    rotate_voicing,
    voice_lead,
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


# Everything the progression engine emits, plus the wishlist chords the
# module's own demo block lists.
VOCABULARY = [
    "I", "ii", "iii", "IV", "V", "vi", "vii°",
    "Imaj7", "Imaj9", "V7", "V9", "ii7", "ii9", "vi7", "IV9",
    "vii°ø7", "vii°ø9", "vii°7",
    "VI#9", "bviihalfdim#9", "Vsus4", "iisus2", "IV°7", "bVIIadd9",
]


def test_major_triad():
    assert chord_intervals("I") == [0, 4, 7]

def test_minor_triad():
    assert chord_intervals("ii") == [0, 3, 7]

def test_diminished_triad():
    assert chord_intervals("vii°") == [0, 3, 6]
    assert chord_intervals("Idim") == [0, 3, 6]

def test_augmented_triad():
    assert chord_intervals("I+") == [0, 4, 8]
    assert chord_intervals("Iaug") == [0, 4, 8]

def test_dominant_and_minor_sevenths():
    assert chord_intervals("V7") == [0, 4, 7, 10]
    assert chord_intervals("ii7") == [0, 3, 7, 10]

def test_major_seventh():
    assert chord_intervals("Imaj7") == [0, 4, 7, 11]

def test_fully_diminished_seventh():
    assert chord_intervals("vii°7") == [0, 3, 6, 9]

def test_half_diminished_seventh():
    # ø flattens the fifth like ° but takes a MAJOR third on top: b7, not bb7
    assert chord_intervals("vii°ø7") == [0, 3, 6, 10]
    assert chord_intervals("bviihalfdim") == [0, 3, 6, 10]

def test_ninths():
    assert chord_intervals("I9") == [0, 4, 7, 10, 14]
    assert chord_intervals("Imaj9") == [0, 4, 7, 11, 14]

def test_elevenths_and_thirteenths():
    assert chord_intervals("I11") == [0, 4, 7, 10, 14, 17]
    assert chord_intervals("I13") == [0, 4, 7, 10, 14, 17, 21]

def test_extensions_stack_upward():
    # each rung adds exactly the next scale tone above the one below it
    assert chord_intervals("I9")[:4] == chord_intervals("I7")
    assert chord_intervals("I11")[:5] == chord_intervals("I9")
    assert chord_intervals("I13")[:6] == chord_intervals("I11")

def test_colors_sit_high():
    # a color is placed at a fixed distance from the ROOT, so a #9 stays
    # 15 rather than collapsing onto the b3
    assert chord_intervals("Iadd9") == [0, 4, 7, 14]
    assert chord_intervals("Ib9") == [0, 4, 7, 13]
    assert chord_intervals("I#9") == [0, 4, 7, 15]
    assert chord_intervals("I#11") == [0, 4, 7, 18]
    assert chord_intervals("Ib13") == [0, 4, 7, 20]

def test_color_is_root_and_quality_agnostic():
    # the same #9 under a different root and a different quality
    for symbol in ("I#9", "VI#9", "bviihalfdim#9"):
        assert 15 in chord_intervals(symbol), f"{symbol} lost its #9"

def test_sus_replaces_the_third():
    assert chord_intervals("Isus4") == [0, 5, 7]
    assert chord_intervals("Isus2") == [0, 2, 7]
    assert 4 not in chord_intervals("Vsus4"), "sus4 left the third in place"

def test_altered_fifth():
    assert chord_intervals("Ib5") == [0, 4, 6]
    assert chord_intervals("I#5") == [0, 4, 8]

def test_intervals_sorted_unique_rooted():
    for symbol in VOCABULARY:
        iv = chord_intervals(symbol)
        assert iv == sorted(iv), f"{symbol} came back unsorted: {iv}"
        assert len(iv) == len(set(iv)), f"{symbol} has a duplicate note: {iv}"
        assert iv[0] == 0, f"{symbol} is not rooted at 0: {iv}"

def test_intervals_are_a_triad_at_minimum():
    for symbol in VOCABULARY:
        assert len(chord_intervals(symbol)) >= 3, \
            f"{symbol} produced fewer than three notes"

def test_root_offsets():
    assert chord_root_offset("I") == 0
    assert chord_root_offset("ii") == 2
    assert chord_root_offset("iii") == 4
    assert chord_root_offset("IV") == 5
    assert chord_root_offset("V") == 7
    assert chord_root_offset("vi") == 9
    assert chord_root_offset("vii°") == 11

def test_root_offset_accidentals():
    assert chord_root_offset("bVII") == 10
    assert chord_root_offset("#IV") == 6
    assert chord_root_offset("bII") == 1

def test_root_offset_ignores_extensions():
    for base in ("I", "ii", "V", "vii°"):
        plain = chord_root_offset(base)
        for ext in ("7", "9", "maj7", "add9", "sus4"):
            assert chord_root_offset(base + ext) == plain, \
                f"{base + ext} moved its root"

def test_case_does_not_move_the_root():
    for upper, lower in (("I", "i"), ("IV", "iv"), ("VII", "vii")):
        assert chord_root_offset(upper) == chord_root_offset(lower), \
            f"{upper}/{lower} disagree on the root"

def test_unknown_numeral_raises():
    for symbol in ("H", "", "7", "bH7"):
        try:
            chord_intervals(symbol)
        except ValueError:
            continue
        raise AssertionError(f"{symbol!r} should have raised ValueError")

def test_unknown_modifier_raises():
    for symbol in ("I%", "Vfoo", "iizz7"):
        try:
            chord_intervals(symbol)
        except ValueError:
            continue
        raise AssertionError(f"{symbol!r} should have raised ValueError")

def test_every_numeral_is_reachable():
    for numeral in DEGREE_OFFSET:
        assert chord_root_offset(numeral) == DEGREE_OFFSET[numeral]
        assert chord_intervals(numeral)[0] == 0

def test_notes_from_root_is_a_shift():
    for root in (-5, 0, 3, 60):
        iv = chord_intervals("V7")
        assert notes_from_root(root, iv) == [root + n for n in iv]

def test_chord_to_midi_is_a_shift():
    notes = [2, 5, 9]
    assert chord_to_midi(60, notes) == [62, 65, 69]
    assert chord_to_midi(0, notes) == notes

def test_placement_composes():
    # the two shifts used together are just one sum, which is what the
    # instruments rely on
    iv = chord_intervals("ii9")
    placed = notes_from_root(chord_root_offset("ii9"), iv)
    assert chord_to_midi(60, placed) == [60 + 2 + n for n in iv]

def test_voice_lead_no_previous_is_sorted():
    chord = [67, 60, 64]
    assert voice_lead(chord, None) == [60, 64, 67]
    assert voice_lead(chord, []) == [60, 64, 67]

def test_voice_lead_preserves_pitch_classes():
    for _ in range(300):
        chord = sorted(random.sample(range(48, 84), 4))
        last = sorted(random.sample(range(48, 84), 4))
        led = voice_lead(chord, last)
        assert sorted(n % 12 for n in led) == sorted(n % 12 for n in chord), \
            f"voice_lead changed the harmony: {chord} -> {led}"

def test_voice_lead_preserves_size():
    for _ in range(300):
        chord = sorted(random.sample(range(48, 84), random.randint(3, 5)))
        last = sorted(random.sample(range(48, 84), 4))
        assert len(voice_lead(chord, last)) == len(chord)

def test_voice_lead_is_sorted():
    for _ in range(200):
        chord = sorted(random.sample(range(48, 84), 4))
        last = sorted(random.sample(range(48, 84), 4))
        led = voice_lead(chord, last)
        assert led == sorted(led), f"voice_lead returned unsorted: {led}"

def _distance(voicing, last):
    return sum(min(abs(n - p) for p in last) for n in voicing)

def test_voice_lead_beats_the_naive_chord():
    # the un-led chord is itself a candidate, so the result can never be
    # worse than just playing it where it sits
    for _ in range(300):
        chord = sorted(random.sample(range(48, 84), 4))
        last = sorted(random.sample(range(48, 84), 4))
        led = voice_lead(chord, last)
        assert _distance(led, last) <= _distance(chord, last), \
            f"voice_lead moved further away: {chord} -> {led} against {last}"

def test_voice_lead_beats_random_alternatives():
    # and it beats any other inversion/octave placement drawn at random
    for _ in range(300):
        chord = sorted(random.sample(range(48, 84), 4))
        last = sorted(random.sample(range(48, 84), 4))
        led = voice_lead(chord, last)
        i = random.randrange(len(chord))
        k = random.randint(-4, 4)
        rival = sorted(n + 12 * k
                       for n in chord[i:] + [c + 12 for c in chord[:i]])
        assert _distance(led, last) <= _distance(rival, last), \
            f"a rival voicing beat voice_lead: {led} vs {rival} against {last}"

def test_voice_lead_is_optimal_over_its_search_space():
    # the strong form: no inversion at any octave placement connects to the
    # previous chord more smoothly than the one that came back
    for _ in range(60):
        chord = sorted(random.sample(range(48, 84), 4))
        last = sorted(random.sample(range(48, 84), 4))
        led = voice_lead(chord, last)
        best = min(_distance(sorted(n + 12 * k
                                    for n in chord[i:] + [c + 12 for c in chord[:i]]),
                             last)
                   for i in range(len(chord))
                   for k in range(-5, 6))
        assert _distance(led, last) == best, \
            f"a smoother voicing existed: {_distance(led, last)} vs {best}"

def test_rotate_zero_is_identity():
    for _ in range(100):
        voicing = sorted(random.sample(range(48, 84), 4))
        assert rotate_voicing(voicing, 0) == voicing

def test_rotate_sorts_its_input():
    assert rotate_voicing([67, 60, 64], 0) == [60, 64, 67]

def test_rotate_preserves_pitch_classes():
    for index in range(5):
        voicing = [60, 64, 67, 70]
        rotated = rotate_voicing(voicing, index)
        assert sorted(n % 12 for n in rotated) == sorted(n % 12 for n in voicing), \
            f"rotation {index} changed the harmony: {rotated}"

def test_rotate_lifts_one_octave_per_index():
    voicing = [60, 64, 67, 70]
    for index in range(6):
        rotated = rotate_voicing(voicing, index)
        assert sum(rotated) == sum(voicing) + 12 * index, \
            f"rotation {index} did not lift exactly {index} note(s) an octave"

def test_rotate_full_turn_is_an_octave_up():
    voicing = [60, 64, 67]
    assert rotate_voicing(voicing, len(voicing)) == [n + 12 for n in voicing]

def test_rotate_keeps_size_and_order():
    for index in range(5):
        rotated = rotate_voicing([60, 64, 67, 70], index)
        assert len(rotated) == 4
        assert rotated == sorted(rotated)

def test_clamp_shifts_by_whole_octaves():
    for _ in range(300):
        voicing = sorted(random.sample(range(20, 100), 4))
        out = clamp_to_register(voicing, 60, 24)
        shifts = {o - n for o, n in zip(out, voicing)}
        assert len(shifts) == 1, f"clamp broke the voicing's shape: {shifts}"
        assert shifts.pop() % 12 == 0, "clamp shifted by less than an octave"

def test_clamp_maximizes_notes_in_range():
    for _ in range(300):
        voicing = sorted(random.sample(range(20, 100), 4))
        bottom, span = 48, 24
        out = clamp_to_register(voicing, bottom, span)
        got = sum(bottom <= n < bottom + span for n in out)
        best = max(sum(bottom <= n + 12 * k < bottom + span for n in voicing)
                   for k in range(-6, 7))
        assert got == best, \
            f"clamp landed {got} notes in range, {best} were possible: {voicing} -> {out}"

def test_clamp_ties_keep_the_lower_placement():
    # [60, 72] fits one note either way; the lower placement wins
    assert clamp_to_register([60, 72], 60, 12) == [48, 60]

def test_clamp_leaves_an_already_fitting_voicing_alone():
    voicing = [60, 64, 67]
    assert clamp_to_register(voicing, 60, 24) == voicing

def test_clamp_preserves_size():
    for _ in range(200):
        voicing = sorted(random.sample(range(20, 100), random.randint(1, 5)))
        assert len(clamp_to_register(voicing, 36, 12)) == len(voicing)

def test_full_chain_stays_diatonic_to_the_chord():
    # spelling -> placement -> voice-leading -> rotation -> clamp must
    # never change WHICH notes are sounding, only where they sit
    for symbol in VOCABULARY:
        placed = notes_from_root(chord_root_offset(symbol),
                                 chord_intervals(symbol))
        midi = chord_to_midi(60, placed)
        led = voice_lead(midi, [58, 62, 65])
        rotated = rotate_voicing(led, 2)
        final = clamp_to_register(rotated, 48, 24)
        assert sorted(n % 12 for n in final) == sorted(n % 12 for n in midi), \
            f"{symbol} changed harmony through the chain: {midi} -> {final}"


def main():
    # ============================================================
    # TRIAD QUALITY
    # ============================================================

    print("\n" + "=" * 60)
    print("TRIAD QUALITY")
    print("=" * 60)

    run_test("uppercase numeral builds a major triad", test_major_triad)

    run_test("lowercase numeral builds a minor triad", test_minor_triad)

    run_test("° / dim builds a diminished triad", test_diminished_triad)

    run_test("+ / aug builds an augmented triad", test_augmented_triad)


    # ============================================================
    # SEVENTHS AND EXTENSIONS
    # ============================================================

    print("\n" + "=" * 60)
    print("SEVENTHS AND EXTENSIONS")
    print("=" * 60)

    run_test("dominant and minor sevenths take a minor third on top", test_dominant_and_minor_sevenths)

    run_test("maj7 takes a major third on top", test_major_seventh)

    run_test("°7 stacks a diminished seventh", test_fully_diminished_seventh)

    run_test("ø keeps the flat fifth but takes a minor seventh", test_half_diminished_seventh)

    run_test("9ths add the natural ninth", test_ninths)

    run_test("11ths and 13ths keep stacking", test_elevenths_and_thirteenths)

    run_test("each extension contains the one below it", test_extensions_stack_upward)


    # ============================================================
    # COLORS AND ALTERATIONS
    # ============================================================

    print("\n" + "=" * 60)
    print("COLORS AND ALTERATIONS")
    print("=" * 60)

    run_test("colors sit at a fixed distance above the root", test_colors_sit_high)

    run_test("a color behaves the same under any root and quality", test_color_is_root_and_quality_agnostic)

    run_test("sus2/sus4 replace the third", test_sus_replaces_the_third)

    run_test("b5/#5 move the fifth in place", test_altered_fifth)


    # ============================================================
    # SPELLING INVARIANTS
    # ============================================================

    print("\n" + "=" * 60)
    print("SPELLING INVARIANTS")
    print("=" * 60)

    run_test("intervals come back sorted, unique, and rooted at 0", test_intervals_sorted_unique_rooted)

    run_test("every chord has at least three notes", test_intervals_are_a_triad_at_minimum)

    run_test("every numeral in the table spells and roots", test_every_numeral_is_reachable)


    # ============================================================
    # ROOT OFFSETS
    # ============================================================

    print("\n" + "=" * 60)
    print("ROOT OFFSETS")
    print("=" * 60)

    run_test("the seven diatonic roots", test_root_offsets)

    run_test("b/# shifts the root by a semitone", test_root_offset_accidentals)

    run_test("extensions never move the root", test_root_offset_ignores_extensions)

    run_test("case sets quality, not root", test_case_does_not_move_the_root)


    # ============================================================
    # PARSE ERRORS
    # ============================================================

    print("\n" + "=" * 60)
    print("PARSE ERRORS")
    print("=" * 60)

    run_test("an unknown Roman numeral raises ValueError", test_unknown_numeral_raises)

    run_test("an unknown modifier raises ValueError", test_unknown_modifier_raises)


    # ============================================================
    # PLACEMENT (notes_from_root / chord_to_midi)
    # ============================================================

    print("\n" + "=" * 60)
    print("PLACEMENT")
    print("=" * 60)

    run_test("notes_from_root is a plain shift", test_notes_from_root_is_a_shift)

    run_test("chord_to_midi is a plain shift", test_chord_to_midi_is_a_shift)

    run_test("the two shifts compose into one sum", test_placement_composes)


    # ============================================================
    # VOICE LEADING
    # ============================================================

    print("\n" + "=" * 60)
    print("VOICE LEADING")
    print("=" * 60)

    run_test("no previous chord returns it sorted, unchanged", test_voice_lead_no_previous_is_sorted)

    run_test("the harmony is never altered (pitch classes survive)", test_voice_lead_preserves_pitch_classes)

    run_test("the chord keeps its number of notes", test_voice_lead_preserves_size)

    run_test("output is sorted", test_voice_lead_is_sorted)

    run_test("never worse than the un-led chord", test_voice_lead_beats_the_naive_chord)

    run_test("beats random rival inversions and octave placements", test_voice_lead_beats_random_alternatives)

    run_test("no inversion at any octave connects more smoothly", test_voice_lead_is_optimal_over_its_search_space)


    # ============================================================
    # ROTATION
    # ============================================================

    print("\n" + "=" * 60)
    print("ROTATION")
    print("=" * 60)

    run_test("index 0 leaves the baseline untouched", test_rotate_zero_is_identity)

    run_test("input is sorted first", test_rotate_sorts_its_input)

    run_test("rotation never alters the harmony", test_rotate_preserves_pitch_classes)

    run_test("each index lifts exactly one more note an octave", test_rotate_lifts_one_octave_per_index)

    run_test("a full turn is the whole voicing an octave up", test_rotate_full_turn_is_an_octave_up)

    run_test("size and ordering survive", test_rotate_keeps_size_and_order)


    # ============================================================
    # REGISTER CLAMP
    # ============================================================

    print("\n" + "=" * 60)
    print("REGISTER CLAMP")
    print("=" * 60)

    run_test("the whole voicing shifts by whole octaves", test_clamp_shifts_by_whole_octaves)

    run_test("as many notes as possible land in the window", test_clamp_maximizes_notes_in_range)

    run_test("a tie keeps the lower placement", test_clamp_ties_keep_the_lower_placement)

    run_test("a voicing already in range is left alone", test_clamp_leaves_an_already_fitting_voicing_alone)

    run_test("size survives", test_clamp_preserves_size)


    # ============================================================
    # THE WHOLE CHAIN
    # ============================================================

    print("\n" + "=" * 60)
    print("THE WHOLE CHAIN")
    print("=" * 60)

    run_test("spell → place → lead → rotate → clamp never changes the harmony", test_full_chain_stays_diatonic_to_the_chord)


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
