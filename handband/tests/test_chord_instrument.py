"""
Chord Instrument Test

Test suite for mi/chord_instrument.py, in the same style as the engine
suites. The module has four testable layers:

READING THE PROGRESSION — active_chords carries each onset forward and
backfills a progression that opens on a continuation; chord_change_slots
reports where the sounding chord actually changes.

CELL AND PLACEMENT — cell_length_calculator stays inside its options and
divides the song; place_hit_cell respects the density the instrument
asked for and never places a hit twice.

THE PART (create_chord_instrument_part) — the rules the two-pass design
promises: the alphabet is H/C/R, a Continue only ever follows a Hit or a
Continue, a sustain NEVER rings across a chord change, every H and C
names the chord actually sounding at that slot, no measure comes out as
pure silence, and the hit rhythm repeats with the cell.

REALIZATION (realize_chord_notes) — the per-slot dicts the sequencer
reads: only hits carry data, the notes are the chord's own spelling in
the key, accent is this instrument's accent_follow applied to the shared
map, and timing is the one-measure groove vector tiled.
"""

import random
import sys

from handband.mi.chord_instrument import (
    CELL_OPTIONS,
    SLOTS_PER_MEASURE,
    _archetype_weights,
    active_chords,
    cell_length_calculator,
    chord_change_slots,
    create_chord_instrument_part,
    default_chord_instrument,
    place_hit_cell,
    realize_chord_notes,
)
from handband.mi.chord_library import chord_intervals, chord_root_offset
from handband.mi.chord_progression_engine import (create_chord_progression,
                                                  create_song_form)
from handband.mi.global_parameters import CURRENT_KEY
from handband.mi.instrument import MAX_ACCENT_DB


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


def prog(chords, measures_each=1):
    """A synthetic progression: one chord per `measures_each` measures."""
    out = []
    for chord in chords:
        out.append(chord)
        out += ["C"] * (measures_each * SLOTS_PER_MEASURE - 1)
    return out

# A handful of (valence, arousal) points spanning the emotional range,
# used wherever a property has to hold everywhere rather than at one spot.
CORNERS = [(-1.0, 0.0), (-0.5, 0.2), (0.0, 0.5), (0.5, 0.8), (1.0, 1.0)]

def songs(n=3):
    """Real generated songs, so the properties are tested on real input."""
    for valence, arousal in CORNERS:
        for _ in range(n):
            form = create_song_form(valence, arousal)
            progression = create_chord_progression(valence, arousal, form)
            yield valence, arousal, form, progression


def test_active_carries_forward():
    p = prog(["I", "V"], measures_each=1)
    active = active_chords(p)
    assert active[:16] == ["I"] * 16, "first chord did not carry forward"
    assert active[16:] == ["V"] * 16, "second chord did not carry forward"

def test_active_backfills_leading_continuations():
    p = ["C"] * 8 + ["V"] + ["C"] * 7
    active = active_chords(p)
    assert active[:8] == ["V"] * 8, \
        f"leading continuations were not backfilled: {active[:8]}"

def test_active_never_none():
    for _valence, _arousal, _form, p in songs(1):
        assert all(c is not None for c in active_chords(p)), \
            "a slot had no sounding chord"

def test_active_length():
    for _valence, _arousal, _form, p in songs(1):
        assert len(active_chords(p)) == len(p)

def test_active_only_real_chords():
    for _valence, _arousal, _form, p in songs(1):
        assert "C" not in active_chords(p), \
            "a continuation marker leaked into the sounding chords"

def test_change_slots_found():
    p = prog(["I", "V", "V", "vi"])
    changes = chord_change_slots(active_chords(p))
    # I->V at 16, V->V is not a change, V->vi at 48
    assert changes == {16, 48}, f"unexpected change slots: {sorted(changes)}"

def test_change_slots_exclude_zero():
    for _valence, _arousal, _form, p in songs(1):
        assert 0 not in chord_change_slots(active_chords(p)), \
            "slot 0 cannot be a change — nothing precedes it"

def test_change_slots_agree_with_active():
    for _valence, _arousal, _form, p in songs(1):
        active = active_chords(p)
        changes = chord_change_slots(active)
        for i in range(1, len(active)):
            assert (i in changes) == (active[i] != active[i - 1]), \
                f"slot {i} disagrees with the sounding chord"

def test_cell_length_in_options():
    for valence in (-1.0, -0.3, 0.0, 0.6, 1.0):
        for measures in (1, 2, 4, 8):
            for _ in range(100):
                cell = cell_length_calculator(valence, measures)
                assert cell in CELL_OPTIONS, f"cell {cell} not an option"
                assert cell <= measures, \
                    f"cell {cell} longer than the {measures}-measure song"

def test_cell_length_divides_the_song():
    for measures in (1, 2, 4, 8):
        for _ in range(200):
            cell = cell_length_calculator(random.uniform(-1, 1), measures)
            assert measures % cell == 0, \
                f"cell {cell} does not tile a {measures}-measure song"

def test_cell_length_one_measure_song():
    for _ in range(50):
        assert cell_length_calculator(1.0, 1) == 1, \
            "a one-measure song can only have a one-measure cell"

def test_cell_length_valence_bias():
    # positive valence leans long, negative leans short
    happy = [cell_length_calculator(1.0, 4) for _ in range(2000)]
    sad = [cell_length_calculator(-1.0, 4) for _ in range(2000)]
    assert happy.count(2) > sad.count(2), \
        f"happy did not lean longer: happy={happy.count(2)} sad={sad.count(2)}"

def test_archetype_weights_length_and_sign():
    for n in (16, 32):
        for _ in range(200):
            w = _archetype_weights(n)
            assert len(w) == n, f"expected {n} weights, got {len(w)}"
            assert all(x > 0 for x in w), f"a weight was not positive: {w}"

def test_place_hit_cell_in_range():
    inst = default_chord_instrument()
    for valence, arousal in CORNERS:
        for cell_measures in CELL_OPTIONS:
            for _ in range(30):
                cell = place_hit_cell(inst, valence, arousal, cell_measures)
                slots = cell_measures * SLOTS_PER_MEASURE
                assert all(0 <= s < slots for s in cell), \
                    f"a hit landed outside the cell: {cell}"

def test_place_hit_cell_sorted_unique():
    inst = default_chord_instrument()
    for valence, arousal in CORNERS:
        for _ in range(30):
            cell = place_hit_cell(inst, valence, arousal, 2)
            assert cell == sorted(cell), f"cell not sorted: {cell}"
            assert len(cell) == len(set(cell)), f"a slot was hit twice: {cell}"

def test_place_hit_cell_respects_density():
    inst = default_chord_instrument()
    for valence, arousal in CORNERS:
        wanted = inst.density_per_measure(arousal)
        for cell_measures in CELL_OPTIONS:
            for _ in range(30):
                cell = place_hit_cell(inst, valence, arousal, cell_measures)
                assert len(cell) <= wanted * cell_measures, \
                    f"placed {len(cell)} hits, density allows {wanted * cell_measures}"

def test_place_hit_cell_always_places_something():
    inst = default_chord_instrument()
    for valence, arousal in CORNERS:
        for _ in range(30):
            assert place_hit_cell(inst, valence, arousal, 1), \
                "an empty cell would leave the instrument silent"

def test_part_length():
    for valence, arousal, _form, p in songs(1):
        part = create_chord_instrument_part(valence, arousal, p)
        assert len(part) == len(p), \
            f"part is {len(part)} slots for a {len(p)}-slot progression"

def test_part_alphabet():
    for valence, arousal, _form, p in songs(1):
        for sym, chord in create_chord_instrument_part(valence, arousal, p):
            assert sym in ("H", "C", "R"), f"unknown symbol {sym!r}"
            assert (chord is None) == (sym == "R"), \
                f"{sym} carried chord {chord!r}"

def test_part_continue_only_after_sound():
    # a Continue means "still ringing", so it is only legal after a Hit or
    # another Continue
    for valence, arousal, _form, p in songs(2):
        part = create_chord_instrument_part(valence, arousal, p)
        for i, (sym, _chord) in enumerate(part):
            if sym == "C":
                assert i > 0, "the song opened on a Continue"
                assert part[i - 1][0] in ("H", "C"), \
                    f"Continue at slot {i} follows a {part[i - 1][0]}"

def test_part_sustain_names_its_own_chord():
    for valence, arousal, _form, p in songs(2):
        part = create_chord_instrument_part(valence, arousal, p)
        sounding = None
        for i, (sym, chord) in enumerate(part):
            if sym == "H":
                sounding = chord
            elif sym == "C":
                assert chord == sounding, \
                    f"slot {i} sustains {chord!r} but {sounding!r} was struck"

def test_part_never_holds_across_a_chord_change():
    # the rule the two-pass design exists to guarantee: an old chord is
    # never left ringing over new harmony
    for valence, arousal, _form, p in songs(3):
        part = create_chord_instrument_part(valence, arousal, p)
        active = active_chords(p)
        for i, (sym, chord) in enumerate(part):
            if sym in ("H", "C"):
                assert chord == active[i], \
                    f"slot {i} sounds {chord!r} while {active[i]!r} is the harmony"

def test_part_hits_the_sounding_chord():
    for valence, arousal, _form, p in songs(2):
        part = create_chord_instrument_part(valence, arousal, p)
        active = active_chords(p)
        for i, (sym, chord) in enumerate(part):
            if sym == "H":
                assert chord == active[i], f"slot {i} struck the wrong chord"

def test_part_no_silent_measure():
    for valence, arousal, _form, p in songs(3):
        part = create_chord_instrument_part(valence, arousal, p)
        for m in range(len(part) // SLOTS_PER_MEASURE):
            measure = part[m * SLOTS_PER_MEASURE:(m + 1) * SLOTS_PER_MEASURE]
            assert not all(sym == "R" for sym, _c in measure), \
                f"measure {m} came out as pure silence"

def test_part_rhythm_repeats_with_the_cell():
    # the cell is tiled, so a hit anywhere in the song recurs at the same
    # position in every repetition. The cell length is drawn per song, so
    # the test asks only that SOME option tiles; measure downbeats are
    # exempt, since the dead-air repair adds those outside the cell.
    for valence, arousal, _form, p in songs(3):
        part = create_chord_instrument_part(valence, arousal, p)
        hits = {i for i, (sym, _c) in enumerate(part) if sym == "H"}
        total = len(part)
        offbeats = {h for h in hits if h % SLOTS_PER_MEASURE}
        periodic = False
        for cell_measures in CELL_OPTIONS:
            cell_slots = cell_measures * SLOTS_PER_MEASURE
            if total % cell_slots:
                continue
            if all(offset + h % cell_slots in hits
                   for offset in range(0, total, cell_slots)
                   for h in offbeats):
                periodic = True
                break
        assert periodic, f"the hit rhythm does not tile: {sorted(hits)}"

def test_part_arousal_shortens_sustains():
    # high arousal = staccato: fewer slots left ringing
    calm = busy = 0
    for _ in range(30):
        form = create_song_form(0.0, 0.5)
        p = create_chord_progression(0.0, 0.5, form)
        calm += sum(1 for sym, _c in create_chord_instrument_part(0.0, 0.05, p)
                    if sym == "C")
        busy += sum(1 for sym, _c in create_chord_instrument_part(0.0, 0.95, p)
                    if sym == "C")
    assert calm > busy, \
        f"calm should sustain more than energized: calm={calm} busy={busy}"

def test_part_accepts_a_supplied_instrument():
    form = create_song_form(0.2, 0.5)
    p = create_chord_progression(0.2, 0.5, form)
    inst = default_chord_instrument()
    part = create_chord_instrument_part(0.2, 0.5, p, inst)
    assert len(part) == len(p)


def realized(valence, arousal, accent_map=None, groove=None):
    """One realized chord stream plus everything it was built from."""
    form = create_song_form(valence, arousal)
    p = create_chord_progression(valence, arousal, form)
    inst = default_chord_instrument()
    part = create_chord_instrument_part(valence, arousal, p, inst)
    if accent_map is None:
        accent_map = [random.randint(0, 1) for _ in range(len(p))]
    if groove is None:
        groove = [random.uniform(-0.2, 0.2) for _ in range(SLOTS_PER_MEASURE)]
    seq = realize_chord_notes(part, arousal, inst, accent_map, groove)
    return seq, part, p, inst, accent_map, groove

def test_realize_length_and_types():
    for valence, arousal in CORNERS:
        seq, part, _p, _i, _a, _g = realized(valence, arousal)
        assert len(seq) == len(part), "realization changed the song's length"
        for slot, (sym, _chord) in zip(seq, part):
            assert slot["type"] == sym, \
                f"realization changed {sym} into {slot['type']}"

def test_realize_only_hits_carry_data():
    for valence, arousal in CORNERS:
        seq, _part, _p, _i, _a, _g = realized(valence, arousal)
        for slot in seq:
            if slot["type"] == "H":
                assert set(slot) == {"type", "notes", "accent", "timing"}, \
                    f"hit carries unexpected keys: {sorted(slot)}"
            else:
                assert set(slot) == {"type"}, \
                    f"a {slot['type']} carries data: {sorted(slot)}"

def test_realize_notes_are_sorted_ints():
    for valence, arousal in CORNERS:
        seq, _part, _p, _i, _a, _g = realized(valence, arousal)
        for slot in seq:
            if slot["type"] == "H":
                notes = slot["notes"]
                assert notes, "a hit sounded no notes"
                assert all(isinstance(n, int) for n in notes), \
                    f"non-integer MIDI note: {notes}"
                assert notes == sorted(notes), f"notes unsorted: {notes}"

def test_realize_notes_spell_the_sounding_chord():
    # the pitch chain may move notes by octaves, never change which notes
    for valence, arousal in CORNERS:
        seq, part, _p, _i, _a, _g = realized(valence, arousal)
        for slot, (sym, chord) in zip(seq, part):
            if sym != "H":
                continue
            root = chord_root_offset(chord)
            want = sorted((CURRENT_KEY + root + iv) % 12
                          for iv in chord_intervals(chord))
            got = sorted(n % 12 for n in slot["notes"])
            assert got == want, \
                f"{chord} realized as pitch classes {got}, expected {want}"

def test_realize_accent_follows_the_map():
    for valence, arousal in CORNERS:
        seq, _part, _p, inst, accent_map, _g = realized(valence, arousal)
        boost = inst.accent_follow * MAX_ACCENT_DB
        for i, slot in enumerate(seq):
            if slot["type"] == "H":
                expected = boost if accent_map[i] else 0.0
                assert abs(slot["accent"] - expected) < 1e-9, \
                    f"slot {i}: accent {slot['accent']} != {expected}"

def test_realize_timing_tiles_the_groove():
    for valence, arousal in CORNERS:
        seq, _part, _p, inst, _a, groove = realized(valence, arousal)
        for i, slot in enumerate(seq):
            if slot["type"] == "H":
                expected = groove[i % SLOTS_PER_MEASURE] * inst.groove_follow
                assert abs(slot["timing"] - expected) < 1e-9, \
                    f"slot {i}: timing {slot['timing']} != {expected}"

def test_realize_stays_near_the_register():
    # the clamp can't always fit a wide chord in a narrow window, but it
    # must never leave the voicing octaves adrift from the register
    for valence, arousal in CORNERS:
        seq, _part, _p, inst, _a, _g = realized(valence, arousal)
        bottom = 12 * (inst.octave + 1) + CURRENT_KEY
        top = bottom + inst.register_octaves(arousal) * 12
        for slot in seq:
            if slot["type"] == "H":
                assert min(slot["notes"]) >= bottom - 12, \
                    f"voicing sank below the register: {slot['notes']}"
                assert max(slot["notes"]) < top + 24, \
                    f"voicing floated above the register: {slot['notes']}"

def test_realize_voice_leads_between_hits():
    # consecutive strikes should stay in the same neighbourhood rather than
    # leaping registers. A single leap is legal (the clamp can force one),
    # so the claim is about the typical move, not the worst one.
    jumps = []
    for _ in range(10):
        seq, _part, _p, _i, _a, _g = realized(0.0, 0.3)
        centres = [sum(s["notes"]) / len(s["notes"])
                   for s in seq if s["type"] == "H"]
        jumps += [abs(b - a) for a, b in zip(centres, centres[1:])]
    average = sum(jumps) / len(jumps)
    assert average <= 6, \
        f"strikes move an average of {average:.1f} semitones — not voice-led"

def test_realize_zero_accent_instrument():
    # an instrument that ignores accents gets a flat 0 everywhere
    from handband.mi.instrument import Instrument
    form = create_song_form(0.0, 0.5)
    p = create_chord_progression(0.0, 0.5, form)
    inst = Instrument("flat", 4, 2, accent_follow=0.0, groove_follow=0.0)
    part = create_chord_instrument_part(0.0, 0.5, p, inst)
    seq = realize_chord_notes(part, 0.5, inst, [1] * len(p),
                              [0.2] * SLOTS_PER_MEASURE)
    for slot in seq:
        if slot["type"] == "H":
            assert slot["accent"] == 0.0, "accent_follow=0 still boosted"
            assert slot["timing"] == 0.0, "groove_follow=0 still displaced"


def main():
    # ============================================================
    # READING THE PROGRESSION
    # ============================================================

    print("\n" + "=" * 60)
    print("READING THE PROGRESSION")
    print("=" * 60)

    run_test("each onset carries forward over its continuations", test_active_carries_forward)

    run_test("leading continuations are backfilled", test_active_backfills_leading_continuations)

    run_test("every slot has a sounding chord", test_active_never_none)

    run_test("one sounding chord per slot", test_active_length)

    run_test("no continuation marker survives as a chord", test_active_only_real_chords)

    run_test("change slots are found, repeats are not changes", test_change_slots_found)

    run_test("slot 0 is never a change", test_change_slots_exclude_zero)

    run_test("change slots agree with the sounding chords", test_change_slots_agree_with_active)


    # ============================================================
    # CELL LENGTH
    # ============================================================

    print("\n" + "=" * 60)
    print("CELL LENGTH")
    print("=" * 60)

    run_test("the cell is one of the options and fits the song", test_cell_length_in_options)

    run_test("the cell always divides the song", test_cell_length_divides_the_song)

    run_test("a one-measure song gets a one-measure cell", test_cell_length_one_measure_song)

    run_test("positive valence leans toward the longer cell", test_cell_length_valence_bias)


    # ============================================================
    # HIT PLACEMENT
    # ============================================================

    print("\n" + "=" * 60)
    print("HIT PLACEMENT")
    print("=" * 60)

    run_test("archetype weights are the right length and strictly positive", test_archetype_weights_length_and_sign)

    run_test("hits land inside the cell", test_place_hit_cell_in_range)

    run_test("hits come back sorted, with no slot hit twice", test_place_hit_cell_sorted_unique)

    run_test("hit count never exceeds the instrument's density", test_place_hit_cell_respects_density)

    run_test("a cell is never empty", test_place_hit_cell_always_places_something)


    # ============================================================
    # THE PART
    # ============================================================

    print("\n" + "=" * 60)
    print("THE PART")
    print("=" * 60)

    run_test("one entry per progression slot", test_part_length)

    run_test("symbols are H/C/R, and only R has no chord", test_part_alphabet)

    run_test("a Continue only ever follows a Hit or a Continue", test_part_continue_only_after_sound)

    run_test("a sustain names the chord that was struck", test_part_sustain_names_its_own_chord)

    run_test("no sustain ever rings across a chord change", test_part_never_holds_across_a_chord_change)

    run_test("every strike plays the chord sounding there", test_part_hits_the_sounding_chord)

    run_test("no measure comes out as pure silence", test_part_no_silent_measure)

    run_test("the hit rhythm tiles with the cell", test_part_rhythm_repeats_with_the_cell)

    run_test("high arousal shortens sustains (staccato)", test_part_arousal_shortens_sustains)

    run_test("a caller-supplied instrument is used", test_part_accepts_a_supplied_instrument)


    # ============================================================
    # NOTE REALIZATION
    # ============================================================

    print("\n" + "=" * 60)
    print("NOTE REALIZATION")
    print("=" * 60)

    run_test("one slot per part entry, symbols unchanged", test_realize_length_and_types)

    run_test("only hits carry notes/accent/timing", test_realize_only_hits_carry_data)

    run_test("notes are sorted integer MIDI", test_realize_notes_are_sorted_ints)

    run_test("the realized notes spell the sounding chord", test_realize_notes_spell_the_sounding_chord)

    run_test("accent is accent_follow applied to the shared map", test_realize_accent_follows_the_map)

    run_test("timing is the one-measure groove vector, tiled", test_realize_timing_tiles_the_groove)

    run_test("voicings stay in the instrument's register neighbourhood", test_realize_stays_near_the_register)

    run_test("consecutive strikes stay voice-led", test_realize_voice_leads_between_hits)

    run_test("an instrument that follows nothing gets flat accent and timing", test_realize_zero_accent_instrument)


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
