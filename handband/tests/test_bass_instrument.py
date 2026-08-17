"""
Bass Instrument Test

Test suite for mi/bass_instrument.py, in the same style as the engine
suites, walking the module's own four tiers:

TIER 1 — the scalar decisions. bass_root drops whole octaves;
rhythm_coupling inverts arousal; chord_tone_probability and
pattern_endpoint are weighted draws, so they're tested by the SHAPE of
their distribution (bias in the documented direction, nothing ever
forbidden) rather than by a single value.

TIER 2 — the two generators. The contour is checked against its own
definition: it opens on the tonic, at arousal 0 it is exactly the
valence tilt, the wiggle stays inside its stated bound, and more arousal
means more motion. The rhythm cell is checked for the alphabet, the
"C only after a note" rule, no silent measure, correct tiling, and the
valence-driven fill at both extremes.

TIER 3 — the integrator. The symbolic degree numbering round-trips, the
chord-tone candidates really are chord tones, and a generated cell keeps
its rhythm, stays inside the bass's two-octave span, and lands its last
note on a chosen chord tone.

TIER 4 — realization. The emitted stream is the SAME per-slot shape the
chord instrument emits, the notes are the struck degree read against the
sounding chord, a hold crossing a chord change becomes a real retrigger,
and every note lands inside the instrument's live register.
"""

import random
import sys

from handband.mi.bass_instrument import (
    BASS_OCTAVE_DROP,
    CHORD_TONE_DEGREES,
    CHORD_TONE_LEVELS,
    CONTOUR_CENTER,
    CONTOUR_MAX_TILT,
    CONTOUR_MAX_WIGGLE,
    DEGREE_STEP_MAX,
    DEGREE_STEP_MIN,
    DEGREES_PER_OCTAVE,
    ENDPOINT_TONE_COUNT,
    FILL_AT_MAX_VALENCE,
    FILL_AT_MIN_VALENCE,
    SLOTS_PER_MEASURE,
    _bass_archetype_weights,
    _chord_tone_candidates,
    bass_cell_measures,
    bass_contour,
    bass_degree_stream,
    bass_fill,
    bass_root,
    chord_hit_mask,
    chord_onsets,
    chord_tone_probability,
    create_bass_degree_cell,
    create_bass_pattern_cell,
    create_bass_rhythm_part,
    default_bass_instrument,
    from_symbolic_degree,
    pattern_endpoint,
    place_bass_cell,
    realize_bass_notes,
    rhythm_coupling,
    to_symbolic_degree,
)
from handband.mi.bass_modes import degree_to_semitone, mode_for_chord
from handband.mi.chord_instrument import (active_chords,
                                          create_chord_instrument_part,
                                          default_chord_instrument)
from handband.mi.chord_library import chord_root_offset
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


CORNERS = [(-1.0, 0.0), (-0.5, 0.2), (0.0, 0.5), (0.5, 0.8), (1.0, 1.0)]


def prog(chords, measures_each=1):
    """A synthetic progression: one chord per `measures_each` measures."""
    out = []
    for chord in chords:
        out.append(chord)
        out += ["C"] * (measures_each * SLOTS_PER_MEASURE - 1)
    return out


def song(valence, arousal):
    """A generated progression plus the chord part the bass couples to."""
    form = create_song_form(valence, arousal)
    progression = create_chord_progression(valence, arousal, form)
    chord_part = create_chord_instrument_part(valence, arousal, progression,
                                              default_chord_instrument())
    return form, progression, chord_part


# ----------------------------------------------------------------------
# Tier 1
# ----------------------------------------------------------------------
def test_bass_root_drops_octaves():
    assert bass_root(60) == 60 - 12 * BASS_OCTAVE_DROP
    assert bass_root(60, 0) == 60
    assert bass_root(60, 1) == 48
    assert bass_root(67, 3) == 31

def test_bass_root_keeps_pitch_class():
    for note in range(36, 96):
        for drop in range(4):
            assert bass_root(note, drop) % 12 == note % 12, \
                "dropping octaves changed the note"

def test_rhythm_coupling_inverts_arousal():
    assert rhythm_coupling(0.0) == 1.0
    assert rhythm_coupling(1.0) == 0.0
    for step in range(101):
        a = step / 100
        assert abs(rhythm_coupling(a) - (1 - a)) < 1e-12

def test_rhythm_coupling_monotonic():
    prev = 2.0
    for step in range(101):
        c = rhythm_coupling(step / 100)
        assert c <= prev, "coupling rose with arousal"
        prev = c

def test_chord_tone_probability_in_levels():
    for a in (0.0, 0.25, 0.5, 0.75, 1.0):
        for _ in range(500):
            assert chord_tone_probability(a) in CHORD_TONE_LEVELS

def test_chord_tone_probability_arousal_bias():
    # calm sticks to chord tones, energized wanders
    calm = [chord_tone_probability(0.0) for _ in range(4000)]
    busy = [chord_tone_probability(1.0) for _ in range(4000)]
    assert sum(calm) / len(calm) > sum(busy) / len(busy), \
        "energized should use passing notes more often"

def test_chord_tone_probability_never_forbidden():
    for a in (0.0, 1.0):
        seen = {chord_tone_probability(a) for _ in range(6000)}
        assert seen == set(CHORD_TONE_LEVELS), \
            f"a level was unreachable at arousal {a}: {seen}"

def test_pattern_endpoint_in_options():
    tones = [0, 4, 7, 11, 14]
    for a in (0.0, 0.5, 1.0):
        for _ in range(500):
            assert pattern_endpoint(a, tones) in tones[:ENDPOINT_TONE_COUNT], \
                "endpoint landed outside the root/3rd/5th"

def test_pattern_endpoint_single_tone():
    assert pattern_endpoint(0.0, [7]) == 7
    assert pattern_endpoint(1.0, [7]) == 7

def test_pattern_endpoint_arousal_bias():
    triad = [0, 4, 7]
    calm = [pattern_endpoint(0.0, triad) for _ in range(4000)]
    busy = [pattern_endpoint(1.0, triad) for _ in range(4000)]
    assert calm.count(0) > busy.count(0), "calm should land on the root"
    assert busy.count(7) > calm.count(7), "energized should land higher"

def test_pattern_endpoint_never_forbidden():
    triad = [0, 4, 7]
    for a in (0.0, 1.0):
        seen = {pattern_endpoint(a, triad) for _ in range(6000)}
        assert seen == set(triad), f"a landing tone was unreachable at {a}: {seen}"


# ----------------------------------------------------------------------
# Tier 2 — contour
# ----------------------------------------------------------------------
def test_contour_length():
    for cell in (1, 2, 4):
        assert len(bass_contour(0.3, 0.5, cell)) == cell * SLOTS_PER_MEASURE

def test_contour_empty_cell():
    assert bass_contour(0.3, 0.5, 0) == []

def test_contour_opens_on_the_tonic():
    for valence, arousal in CORNERS:
        for _ in range(20):
            curve = bass_contour(valence, arousal, 2)
            assert abs(curve[0] - CONTOUR_CENTER) < 1e-12, \
                f"the cell opened on degree {curve[0]}, not the tonic"

def test_contour_at_zero_arousal_is_pure_tilt():
    for valence in (-1.0, -0.4, 0.0, 0.7, 1.0):
        curve = bass_contour(valence, 0.0, 2)
        T = len(curve)
        for t, c in enumerate(curve):
            expected = valence * CONTOUR_MAX_TILT * (t / T) + CONTOUR_CENTER
            assert abs(c - expected) < 1e-9, \
                f"valence {valence} slot {t}: {c} != {expected}"

def test_contour_flat_when_neutral_and_calm():
    curve = bass_contour(0.0, 0.0, 2)
    assert all(abs(c - CONTOUR_CENTER) < 1e-12 for c in curve), \
        "a neutral, calm bass should sit still on the tonic"

def test_contour_tilt_follows_valence():
    for _ in range(20):
        up = bass_contour(1.0, 0.0, 2)
        down = bass_contour(-1.0, 0.0, 2)
        assert up[-1] > up[0], "happy should climb"
        assert down[-1] < down[0], "sad should fall"

def test_contour_tilt_reaches_an_octave():
    # at full valence the tilt spans (almost) a full octave across the cell
    curve = bass_contour(1.0, 0.0, 1)
    T = len(curve)
    span = curve[-1] - curve[0]
    assert abs(span - CONTOUR_MAX_TILT * (T - 1) / T) < 1e-9, \
        f"full-valence tilt spanned {span} degrees"

def test_contour_stays_inside_its_bound():
    # the tilt reaches at most one octave and the wiggle's peak swing is
    # arousal * one octave; anchoring to slot 0 can cost one more wiggle
    for valence, arousal in CORNERS:
        for _ in range(50):
            curve = bass_contour(valence, arousal, 2)
            bound = (abs(valence) * CONTOUR_MAX_TILT
                     + 2 * arousal * CONTOUR_MAX_WIGGLE + 1e-9)
            worst = max(abs(c - CONTOUR_CENTER) for c in curve)
            assert worst <= bound, \
                f"curve reached {worst:.2f} degrees off the tonic, bound {bound:.2f}"

def test_contour_arousal_adds_motion():
    def motion(arousal):
        total = 0.0
        for _ in range(60):
            curve = bass_contour(0.0, arousal, 2)
            total += sum(abs(b - a) for a, b in zip(curve, curve[1:]))
        return total
    assert motion(0.9) > motion(0.1), "more arousal should mean more wiggle"

def test_contour_is_stochastic():
    # two draws at the same input are different curves of the same character
    a = bass_contour(0.2, 0.6, 2)
    b = bass_contour(0.2, 0.6, 2)
    assert a != b, "the contour should not be deterministic"


# ----------------------------------------------------------------------
# Tier 2 — rhythm cell
# ----------------------------------------------------------------------
def test_chord_onsets_reads_the_progression():
    p = prog(["I", "V", "V", "vi"])
    assert chord_onsets(p) == [0, 16, 32, 48]

def test_chord_onsets_keeps_repeated_numerals():
    # V -> V is a new strike even though the sounding chord is unchanged
    p = prog(["V", "V"])
    assert chord_onsets(p) == [0, 16], \
        "a repeated numeral lost its onset"

def test_chord_onsets_handles_a_leading_continuation():
    p = ["C"] * 8 + ["V"] + ["C"] * 7
    assert chord_onsets(p) == [8], "the true onset was lost"

def test_cell_measures_matches_the_fastest_harmony():
    assert bass_cell_measures(prog(["I", "V", "vi", "IV"])) == 1
    assert bass_cell_measures(prog(["I", "V"], measures_each=2)) == 2
    assert bass_cell_measures(prog(["I", "V", "vi", "IV"], measures_each=2)) == 2

def test_cell_measures_divides_the_song():
    for valence, arousal in CORNERS:
        for _ in range(20):
            _form, p, _part = song(valence, arousal)
            measures = len(p) // SLOTS_PER_MEASURE
            cell = bass_cell_measures(p)
            assert 1 <= cell <= measures, f"cell {cell} for {measures} measures"
            assert measures % cell == 0, f"cell {cell} does not tile {measures}"

def test_cell_measures_floors_at_one():
    # chords changing faster than a measure still give a one-measure cell
    p = ["I"] + ["C"] * 7 + ["V"] + ["C"] * 7
    assert bass_cell_measures(p) == 1

def test_fill_endpoints():
    assert abs(bass_fill(-1.0) - FILL_AT_MIN_VALENCE) < 1e-12
    assert abs(bass_fill(1.0) - FILL_AT_MAX_VALENCE) < 1e-12

def test_fill_is_linear_and_bounded():
    prev = None
    for step in range(101):
        v = -1 + step / 50
        f = bass_fill(v)
        assert 0.0 <= f <= 1.0, f"fill {f} out of range at valence {v}"
        if prev is not None:
            assert f <= prev + 1e-12, "fill rose with valence"
        prev = f

def test_bass_archetype_weights():
    for n in (16, 32):
        for _ in range(200):
            w = _bass_archetype_weights(n)
            assert len(w) == n and all(x > 0 for x in w), f"bad weights: {w}"

def test_chord_hit_mask_folds_onto_the_cell():
    part = [("H", "I")] + [("R", None)] * 15 + [("R", None)] * 8 + [("H", "V")] + [("R", None)] * 7
    mask = chord_hit_mask(part, 16)
    assert len(mask) == 16
    assert mask[0] == 1 and mask[8] == 1, "a chord hit was lost"
    assert sum(mask) == 2, f"unexpected extra hits: {mask}"

def test_chord_hit_mask_is_binary():
    _form, p, part = song(0.0, 0.6)
    mask = chord_hit_mask(part, 32)
    assert set(mask) <= {0, 1}, f"mask is not binary: {set(mask)}"

def test_place_bass_cell_in_range():
    inst = default_bass_instrument()
    for valence, arousal in CORNERS:
        for cell_measures in (1, 2):
            slots = cell_measures * SLOTS_PER_MEASURE
            mask = [random.randint(0, 1) for _ in range(slots)]
            for _ in range(20):
                cell = place_bass_cell(inst, valence, arousal, cell_measures, mask)
                assert all(0 <= s < slots for s in cell), f"out of cell: {cell}"
                assert cell == sorted(cell), f"unsorted: {cell}"
                assert len(cell) == len(set(cell)), f"slot hit twice: {cell}"
                assert cell, "an empty bass cell would leave it silent"

def test_place_bass_cell_respects_density():
    inst = default_bass_instrument()
    for valence, arousal in CORNERS:
        wanted = inst.density_per_measure(arousal)
        for cell_measures in (1, 2):
            slots = cell_measures * SLOTS_PER_MEASURE
            mask = [0] * slots
            for _ in range(20):
                cell = place_bass_cell(inst, valence, arousal, cell_measures, mask)
                assert len(cell) <= wanted * cell_measures, \
                    f"{len(cell)} hits exceeds density {wanted * cell_measures}"

def test_place_bass_cell_arousal_plants_the_downbeat():
    inst = default_bass_instrument()
    slots = SLOTS_PER_MEASURE
    mask = [0] * slots
    calm = sum(0 in place_bass_cell(inst, 0.0, 0.05, 1, mask) for _ in range(400))
    busy = sum(0 in place_bass_cell(inst, 0.0, 0.95, 1, mask) for _ in range(400))
    assert busy > calm, \
        f"an energized bass should land the 1 more often: calm={calm} busy={busy}"

def test_rhythm_part_length_and_alphabet():
    for valence, arousal in CORNERS:
        _form, p, part = song(valence, arousal)
        rhythm = create_bass_rhythm_part(valence, arousal, p, part)
        assert len(rhythm) == len(p), "rhythm is not the song's length"
        assert set(rhythm) <= {"H", "C", "X"}, f"unknown symbol: {set(rhythm)}"

def test_rhythm_hold_only_after_a_note():
    for valence, arousal in CORNERS:
        _form, p, part = song(valence, arousal)
        rhythm = create_bass_rhythm_part(valence, arousal, p, part)
        for i, sym in enumerate(rhythm):
            if sym == "C":
                assert i > 0 and rhythm[i - 1] in ("H", "C"), \
                    f"a hold at slot {i} follows {rhythm[i - 1] if i else 'nothing'}"

def test_rhythm_no_silent_measure():
    for valence, arousal in CORNERS:
        for _ in range(5):
            _form, p, part = song(valence, arousal)
            rhythm = create_bass_rhythm_part(valence, arousal, p, part)
            for m in range(len(rhythm) // SLOTS_PER_MEASURE):
                measure = rhythm[m * SLOTS_PER_MEASURE:(m + 1) * SLOTS_PER_MEASURE]
                assert not all(sym == "X" for sym in measure), \
                    f"measure {m} is pure silence"

def test_rhythm_tiles_with_the_cell():
    # the cell length is deterministic, so a hit anywhere in the song must
    # recur at the same position in every repetition. Measure downbeats are
    # exempt: the dead-air repair adds those outside the cell.
    for valence, arousal in CORNERS:
        for _ in range(5):
            _form, p, part = song(valence, arousal)
            rhythm = create_bass_rhythm_part(valence, arousal, p, part)
            cell_slots = bass_cell_measures(p) * SLOTS_PER_MEASURE
            hits = {i for i, sym in enumerate(rhythm) if sym == "H"}
            for h in hits:
                if h % SLOTS_PER_MEASURE == 0:
                    continue
                for offset in range(0, len(rhythm), cell_slots):
                    twin = offset + h % cell_slots
                    assert twin in hits, \
                        f"the cell's hit at {h} is missing at {twin}"

def test_rhythm_fill_at_min_valence_is_legato():
    # full fill sustains every gap, so once the line has started there is
    # no silence left in it (the slots before the first hit are untouched
    # by fill, since nothing is sounding yet)
    for _ in range(10):
        _form, p, part = song(-1.0, 0.5)
        rhythm = create_bass_rhythm_part(-1.0, 0.5, p, part)
        first = rhythm.index("H")
        assert "X" not in rhythm[first:], \
            "full fill (valence -1) should leave no silence after the first note"

def test_rhythm_fill_at_max_valence_is_staccato():
    _form, p, part = song(1.0, 0.5)
    rhythm = create_bass_rhythm_part(1.0, 0.5, p, part)
    assert "C" not in rhythm, \
        "zero fill (valence +1) should hold nothing"

def test_rhythm_ignores_chord_changes():
    # unlike the chord instrument, the bass cell is placed without regard
    # to harmony — the retrigger happens later, at realization
    p = prog(["I", "V"], measures_each=1)
    part = [("H", "I")] + [("R", None)] * 31
    rhythm = create_bass_rhythm_part(-1.0, 0.1, p, part)
    assert "C" in rhythm[16:], \
        "a hold should be allowed to run past a chord change"


# ----------------------------------------------------------------------
# Tier 3 — symbolic degrees and the pattern cell
# ----------------------------------------------------------------------
def test_symbolic_degree_known_values():
    assert to_symbolic_degree(1) == 1
    assert to_symbolic_degree(8) == 8
    assert to_symbolic_degree(0) == -7
    assert to_symbolic_degree(-6) == -1

def test_symbolic_degree_skips_zero():
    for step in range(DEGREE_STEP_MIN, DEGREE_STEP_MAX + 1):
        assert to_symbolic_degree(step) != 0, "there is no degree 0"

def test_symbolic_degree_round_trips():
    for step in range(DEGREE_STEP_MIN, DEGREE_STEP_MAX + 1):
        assert from_symbolic_degree(to_symbolic_degree(step)) == step

def test_symbolic_degree_spans_two_octaves():
    degrees = {to_symbolic_degree(s)
               for s in range(DEGREE_STEP_MIN, DEGREE_STEP_MAX + 1)}
    assert degrees == set(range(1, 9)) | set(range(-7, 0)), \
        f"unexpected degree span: {sorted(degrees)}"

def test_symbolic_degree_is_order_preserving_in_steps():
    # higher step = higher pitch, whatever the sign of the name
    steps = list(range(DEGREE_STEP_MIN, DEGREE_STEP_MAX + 1))
    back = [from_symbolic_degree(to_symbolic_degree(s)) for s in steps]
    assert back == steps, "the numbering reordered the pitches"

def test_chord_tone_candidates_are_chord_tones():
    cands = _chord_tone_candidates(CHORD_TONE_DEGREES, DEGREE_STEP_MIN,
                                   DEGREE_STEP_MAX)
    assert cands == sorted(set(cands)), f"unsorted or duplicated: {cands}"
    for c in cands:
        assert any((c - d) % DEGREES_PER_OCTAVE == 0 for d in CHORD_TONE_DEGREES), \
            f"{c} is not a chord tone in any octave"
        assert DEGREE_STEP_MIN <= c <= DEGREE_STEP_MAX, f"{c} out of range"

def test_chord_tone_candidates_include_the_base_degrees():
    cands = _chord_tone_candidates(CHORD_TONE_DEGREES, DEGREE_STEP_MIN,
                                   DEGREE_STEP_MAX)
    for d in CHORD_TONE_DEGREES:
        assert d in cands, f"the tonic-octave degree {d} is missing"

def test_chord_tone_candidates_cover_both_octaves():
    cands = _chord_tone_candidates(CHORD_TONE_DEGREES, DEGREE_STEP_MIN,
                                   DEGREE_STEP_MAX)
    assert any(c < CONTOUR_CENTER for c in cands), "no candidate below the tonic"
    assert any(c > DEGREES_PER_OCTAVE for c in cands), "no candidate above the octave"

def test_degree_cell_keeps_the_rhythm():
    rhythm = ["H", "C", "C", "X"] * 4
    contour = [1.0 + i * 0.3 for i in range(16)]
    cell = create_bass_degree_cell(rhythm, contour, 0.5)
    assert len(cell) == len(rhythm)
    assert [sym for sym, _d in cell] == rhythm, "the rhythm was altered"

def test_degree_cell_only_hits_carry_degrees():
    rhythm = ["H", "C", "C", "X"] * 4
    contour = [1.0 + i * 0.3 for i in range(16)]
    for _ in range(50):
        cell = create_bass_degree_cell(rhythm, contour, 0.5)
        for sym, degree in cell:
            if sym == "H":
                assert degree is not None, "a strike carried no degree"
            else:
                assert degree is None, f"a {sym} carried degree {degree}"

def test_degree_cell_stays_in_the_bass_span():
    contour = [-20.0 + i * 3 for i in range(32)]   # deliberately out of range
    rhythm = ["H"] * 32
    for _ in range(50):
        cell = create_bass_degree_cell(rhythm, contour, 0.5)
        for _sym, degree in cell:
            assert degree != 0, "degree 0 does not exist"
            assert -7 <= degree <= DEGREE_STEP_MAX, \
                f"degree {degree} is outside the bass's two octaves"

def test_degree_cell_lands_on_a_chord_tone():
    contour = [3.7] * 16
    rhythm = ["H", "X", "H", "X"] * 4
    for _ in range(100):
        cell = create_bass_degree_cell(rhythm, contour, 0.5)
        hits = [d for sym, d in cell if sym == "H"]
        assert hits[-1] in CHORD_TONE_DEGREES, \
            f"the cell landed on {hits[-1]}, not a chord tone"

def test_degree_cell_all_rests():
    cell = create_bass_degree_cell(["X"] * 16, [1.0] * 16, 0.5)
    assert cell == [("X", None)] * 16, "a silent cell should stay silent"

def test_degree_cell_snap_follows_arousal():
    # low arousal snaps to chord tones more often than high arousal does
    contour = [2.4] * 16     # sits between chord tones 1/3, rounds to 2
    rhythm = ["H"] * 15 + ["X"]
    def snapped(arousal):
        total = 0
        for _ in range(200):
            cell = create_bass_degree_cell(rhythm, contour, arousal)
            total += sum(1 for sym, d in cell
                         if sym == "H" and d in CHORD_TONE_DEGREES)
        return total
    assert snapped(0.0) > snapped(1.0), \
        "calm should land on chord tones more often than energized"

def test_pattern_cell_pieces_agree():
    for valence, arousal in CORNERS:
        _form, p, part = song(valence, arousal)
        rhythm, contour, cell = create_bass_pattern_cell(valence, arousal, p, part)
        cell_slots = bass_cell_measures(p) * SLOTS_PER_MEASURE
        assert len(rhythm) == len(p), "rhythm is not song-length"
        assert len(contour) == cell_slots, "contour is not one cell long"
        assert len(cell) == cell_slots, "degree cell is not one cell long"
        assert [sym for sym, _d in cell] == rhythm[:cell_slots], \
            "the degree cell and the rhythm disagree"

def test_pattern_cell_uses_a_supplied_instrument():
    _form, p, part = song(0.2, 0.5)
    inst = default_bass_instrument()
    rhythm, _contour, _cell = create_bass_pattern_cell(0.2, 0.5, p, part, inst)
    assert len(rhythm) == len(p)


# ----------------------------------------------------------------------
# Tier 4 — the degree stream and realization
# ----------------------------------------------------------------------
def test_stream_length_and_alphabet():
    for valence, arousal in CORNERS:
        _form, p, part = song(valence, arousal)
        rhythm, _c, cell = create_bass_pattern_cell(valence, arousal, p, part)
        stream = bass_degree_stream(rhythm, cell, p)
        assert len(stream) == len(rhythm)
        for sym, degree in stream:
            assert sym in ("H", "C", "R"), f"unknown symbol {sym!r}"
            assert (degree is None) == (sym != "H"), \
                f"{sym} carried degree {degree!r}"

def test_stream_rests_map_to_R():
    p = prog(["I"], measures_each=1)
    rhythm = ["H"] + ["X"] * 15
    cell = [("H", 5)] + [("X", None)] * 15
    stream = bass_degree_stream(rhythm, cell, p)
    assert stream[0] == ("H", 5)
    assert all(s == ("R", None) for s in stream[1:]), \
        "the bass's X should be reported as R"

def test_stream_retriggers_on_a_chord_change():
    p = prog(["I", "V"], measures_each=1)
    rhythm = ["H"] + ["C"] * 31
    cell = [("H", 5)] + [("C", None)] * 15
    stream = bass_degree_stream(rhythm, cell, p)
    assert stream[0] == ("H", 5), "the initial strike was lost"
    assert all(s == ("C", None) for s in stream[1:16]), \
        "the note should just be held under its own chord"
    assert stream[16] == ("H", 5), \
        "the hold should be re-struck on the new chord, on the same degree"
    assert all(s == ("C", None) for s in stream[17:]), \
        "only the change slot retriggers"

def test_stream_does_not_retrigger_a_repeated_chord():
    p = prog(["V", "V"], measures_each=1)
    rhythm = ["H"] + ["C"] * 31
    cell = [("H", 3)] + [("C", None)] * 15
    stream = bass_degree_stream(rhythm, cell, p)
    assert stream[16] == ("C", None), \
        "the sounding chord did not change, so nothing should retrigger"

def test_stream_repaired_hit_defaults_to_the_root():
    p = prog(["I"], measures_each=1)
    rhythm = ["X"] * 8 + ["H"] + ["X"] * 7
    cell = [("X", None)] * 16          # the cell has no degree at slot 8
    stream = bass_degree_stream(rhythm, cell, p)
    assert stream[8] == ("H", 1), \
        f"a repaired hit should default to degree 1, got {stream[8]}"

def test_stream_tiles_the_cell():
    p = prog(["I", "I"], measures_each=1)
    rhythm = (["H"] + ["X"] * 15) * 2
    cell = [("H", 4)] + [("X", None)] * 15
    stream = bass_degree_stream(rhythm, cell, p)
    assert stream[0] == ("H", 4) and stream[16] == ("H", 4), \
        "the degree cell did not tile across the song"

def test_stream_never_loses_an_attack():
    for valence, arousal in CORNERS:
        _form, p, part = song(valence, arousal)
        rhythm, _c, cell = create_bass_pattern_cell(valence, arousal, p, part)
        stream = bass_degree_stream(rhythm, cell, p)
        attacks = sum(1 for sym, _d in stream if sym == "H")
        assert attacks >= rhythm.count("H"), \
            "realization dropped an attack the rhythm asked for"


def realized(valence, arousal):
    """A realized bass stream plus everything it was built from."""
    _form, p, part = song(valence, arousal)
    inst = default_bass_instrument()
    rhythm, _contour, cell = create_bass_pattern_cell(valence, arousal, p,
                                                      part, inst)
    accent_map = [random.randint(0, 1) for _ in range(len(p))]
    groove = [random.uniform(-0.2, 0.2) for _ in range(SLOTS_PER_MEASURE)]
    seq = realize_bass_notes(rhythm, cell, p, arousal, inst, accent_map, groove)
    return seq, rhythm, cell, p, inst, accent_map, groove

def test_realize_shape_matches_the_chord_stream():
    for valence, arousal in CORNERS:
        seq, rhythm, _cell, _p, _i, _a, _g = realized(valence, arousal)
        assert len(seq) == len(rhythm), "realization changed the song's length"
        for slot in seq:
            assert slot["type"] in ("H", "C", "R"), f"unknown type {slot['type']}"
            if slot["type"] == "H":
                assert set(slot) == {"type", "notes", "accent", "timing"}, \
                    f"hit carries unexpected keys: {sorted(slot)}"
            else:
                assert set(slot) == {"type"}, \
                    f"a {slot['type']} carries data: {sorted(slot)}"

def test_realize_is_monophonic():
    for valence, arousal in CORNERS:
        seq, _r, _c, _p, _i, _a, _g = realized(valence, arousal)
        for slot in seq:
            if slot["type"] == "H":
                assert len(slot["notes"]) == 1, \
                    f"the bass sounded {len(slot['notes'])} notes at once"
                assert isinstance(slot["notes"][0], int), "non-integer MIDI note"

def test_realize_notes_read_against_the_sounding_chord():
    for valence, arousal in CORNERS:
        seq, rhythm, cell, p, inst, _a, _g = realized(valence, arousal)
        active = active_chords(p)
        stream = bass_degree_stream(rhythm, cell, p)
        root_midi = 12 * (inst.octave + 1) + CURRENT_KEY
        for i, slot in enumerate(seq):
            if slot["type"] != "H":
                continue
            chord = active[i]
            degree = stream[i][1]
            want = (root_midi + chord_root_offset(chord)
                    + degree_to_semitone(mode_for_chord(chord), degree))
            assert slot["notes"][0] % 12 == want % 12, \
                f"slot {i}: {slot['notes'][0]} is not degree {degree} over {chord}"

def test_realize_stays_in_the_register():
    # a single note always fits, so the clamp has no excuse here
    for valence, arousal in CORNERS:
        seq, _r, _c, _p, inst, _a, _g = realized(valence, arousal)
        bottom = 12 * (inst.octave + 1) + CURRENT_KEY
        top = bottom + inst.register_octaves(arousal) * 12
        for slot in seq:
            if slot["type"] == "H":
                note = slot["notes"][0]
                assert bottom <= note < top, \
                    f"note {note} outside the register [{bottom}, {top})"

def test_realize_accent_follows_the_map():
    for valence, arousal in CORNERS:
        seq, _r, _c, _p, inst, accent_map, _g = realized(valence, arousal)
        boost = inst.accent_follow * MAX_ACCENT_DB
        for i, slot in enumerate(seq):
            if slot["type"] == "H":
                expected = boost if accent_map[i] else 0.0
                assert abs(slot["accent"] - expected) < 1e-9, \
                    f"slot {i}: accent {slot['accent']} != {expected}"

def test_realize_timing_tiles_the_groove():
    for valence, arousal in CORNERS:
        seq, _r, _c, _p, inst, _a, groove = realized(valence, arousal)
        for i, slot in enumerate(seq):
            if slot["type"] == "H":
                expected = groove[i % SLOTS_PER_MEASURE] * inst.groove_follow
                assert abs(slot["timing"] - expected) < 1e-9, \
                    f"slot {i}: timing {slot['timing']} != {expected}"

def test_realize_agrees_with_the_degree_stream():
    for valence, arousal in CORNERS:
        seq, rhythm, cell, p, _i, _a, _g = realized(valence, arousal)
        stream = bass_degree_stream(rhythm, cell, p)
        assert [s["type"] for s in seq] == [sym for sym, _d in stream], \
            "the realized stream and the degree stream disagree slot by slot"

def test_realize_retrigger_changes_the_note():
    # the point of the retrigger: the same symbolic degree becomes a
    # different concrete note once the chord under it moves
    p = prog(["I", "V"], measures_each=1)
    rhythm = ["H"] + ["C"] * 31
    cell = [("H", 3)] + [("C", None)] * 15
    inst = default_bass_instrument()
    seq = realize_bass_notes(rhythm, cell, p, 0.5, inst, [0] * 32,
                             [0.0] * SLOTS_PER_MEASURE)
    assert seq[0]["type"] == "H" and seq[16]["type"] == "H", \
        "the chord change did not produce a retrigger"
    assert seq[0]["notes"] != seq[16]["notes"], \
        "the retriggered note should follow the new chord"


def main():
    # ============================================================
    # TIER 1 — SCALAR DECISIONS
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 1 — SCALAR DECISIONS")
    print("=" * 60)

    run_test("bass_root drops whole octaves", test_bass_root_drops_octaves)

    run_test("dropping octaves never changes the note", test_bass_root_keeps_pitch_class)

    run_test("rhythm coupling is the inverse of arousal", test_rhythm_coupling_inverts_arousal)

    run_test("rhythm coupling falls as arousal rises", test_rhythm_coupling_monotonic)

    run_test("chord-tone probability is always one of the levels", test_chord_tone_probability_in_levels)

    run_test("calm favors chord tones, energized favors passing notes", test_chord_tone_probability_arousal_bias)

    run_test("every chord-tone level stays reachable", test_chord_tone_probability_never_forbidden)

    run_test("the endpoint is one of the root/3rd/5th", test_pattern_endpoint_in_options)

    run_test("a one-tone chord returns that tone", test_pattern_endpoint_single_tone)

    run_test("calm lands on the root, energized lands higher", test_pattern_endpoint_arousal_bias)

    run_test("every landing tone stays reachable", test_pattern_endpoint_never_forbidden)


    # ============================================================
    # TIER 2 — CONTOUR
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 2 — CONTOUR")
    print("=" * 60)

    run_test("one value per slot in the cell", test_contour_length)

    run_test("a zero-length cell gives an empty curve", test_contour_empty_cell)

    run_test("the cell opens exactly on the tonic", test_contour_opens_on_the_tonic)

    run_test("at zero arousal the curve is exactly the valence tilt", test_contour_at_zero_arousal_is_pure_tilt)

    run_test("neutral and calm sits still on the tonic", test_contour_flat_when_neutral_and_calm)

    run_test("happy climbs, sad falls", test_contour_tilt_follows_valence)

    run_test("full valence tilts a full octave across the cell", test_contour_tilt_reaches_an_octave)

    run_test("the curve stays inside its tilt+wiggle bound", test_contour_stays_inside_its_bound)

    run_test("more arousal means more motion", test_contour_arousal_adds_motion)

    run_test("every curve is a fresh draw", test_contour_is_stochastic)


    # ============================================================
    # TIER 2 — RHYTHM CELL
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 2 — RHYTHM CELL")
    print("=" * 60)

    run_test("onsets are read straight off the progression", test_chord_onsets_reads_the_progression)

    run_test("a repeated numeral keeps its onset", test_chord_onsets_keeps_repeated_numerals)

    run_test("a leading continuation does not hide the onset", test_chord_onsets_handles_a_leading_continuation)

    run_test("the cell fits inside the fastest harmonic rhythm", test_cell_measures_matches_the_fastest_harmony)

    run_test("the cell always divides the song", test_cell_measures_divides_the_song)

    run_test("sub-measure harmony still gives a one-measure cell", test_cell_measures_floors_at_one)

    run_test("fill hits its endpoints at ±1 valence", test_fill_endpoints)

    run_test("fill is bounded and falls with valence", test_fill_is_linear_and_bounded)

    run_test("archetype weights are the right length and strictly positive", test_bass_archetype_weights)

    run_test("the chord hit mask folds onto one cell", test_chord_hit_mask_folds_onto_the_cell)

    run_test("the mask is binary", test_chord_hit_mask_is_binary)

    run_test("bass hits land inside the cell, sorted and unique", test_place_bass_cell_in_range)

    run_test("bass hit count never exceeds the density", test_place_bass_cell_respects_density)

    run_test("arousal plants the downbeat harder", test_place_bass_cell_arousal_plants_the_downbeat)

    run_test("the rhythm is song-length and uses H/C/X", test_rhythm_part_length_and_alphabet)

    run_test("a hold only ever follows a note", test_rhythm_hold_only_after_a_note)

    run_test("no measure comes out as pure silence", test_rhythm_no_silent_measure)

    run_test("the rhythm tiles with the cell", test_rhythm_tiles_with_the_cell)

    run_test("valence -1 fills every gap (legato)", test_rhythm_fill_at_min_valence_is_legato)

    run_test("valence +1 holds nothing (staccato)", test_rhythm_fill_at_max_valence_is_staccato)

    run_test("the rhythm is placed without regard to chord changes", test_rhythm_ignores_chord_changes)


    # ============================================================
    # TIER 3 — SYMBOLIC DEGREES
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 3 — SYMBOLIC DEGREES")
    print("=" * 60)

    run_test("known step → degree values", test_symbolic_degree_known_values)

    run_test("there is no degree 0", test_symbolic_degree_skips_zero)

    run_test("the numbering round-trips", test_symbolic_degree_round_trips)

    run_test("the numbering spans exactly two octaves", test_symbolic_degree_spans_two_octaves)

    run_test("the numbering never reorders pitches", test_symbolic_degree_is_order_preserving_in_steps)

    run_test("every candidate really is a chord tone in range", test_chord_tone_candidates_are_chord_tones)

    run_test("the tonic octave's own tones are candidates", test_chord_tone_candidates_include_the_base_degrees)

    run_test("candidates are stamped out in both octaves", test_chord_tone_candidates_cover_both_octaves)


    # ============================================================
    # TIER 3 — PATTERN CELL
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 3 — PATTERN CELL")
    print("=" * 60)

    run_test("the degree cell keeps the rhythm it was given", test_degree_cell_keeps_the_rhythm)

    run_test("only strikes carry a degree", test_degree_cell_only_hits_carry_degrees)

    run_test("degrees stay inside the bass's two octaves", test_degree_cell_stays_in_the_bass_span)

    run_test("the cell lands its last note on a chord tone", test_degree_cell_lands_on_a_chord_tone)

    run_test("a silent cell stays silent", test_degree_cell_all_rests)

    run_test("calm snaps to chord tones more often than energized", test_degree_cell_snap_follows_arousal)

    run_test("the three returned pieces agree with each other", test_pattern_cell_pieces_agree)

    run_test("a caller-supplied instrument is used", test_pattern_cell_uses_a_supplied_instrument)


    # ============================================================
    # TIER 4 — DEGREE STREAM
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 4 — DEGREE STREAM")
    print("=" * 60)

    run_test("the stream is song-length and uses H/C/R", test_stream_length_and_alphabet)

    run_test("the bass's X is reported as R", test_stream_rests_map_to_R)

    run_test("a hold across a chord change is re-struck", test_stream_retriggers_on_a_chord_change)

    run_test("a repeated chord does not retrigger", test_stream_does_not_retrigger_a_repeated_chord)

    run_test("a repaired hit defaults to the root", test_stream_repaired_hit_defaults_to_the_root)

    run_test("the degree cell tiles across the song", test_stream_tiles_the_cell)

    run_test("no attack the rhythm asked for is lost", test_stream_never_loses_an_attack)


    # ============================================================
    # TIER 4 — NOTE REALIZATION
    # ============================================================

    print("\n" + "=" * 60)
    print("TIER 4 — NOTE REALIZATION")
    print("=" * 60)

    run_test("the emitted shape matches the chord instrument's", test_realize_shape_matches_the_chord_stream)

    run_test("exactly one note per strike", test_realize_is_monophonic)

    run_test("each note is its degree read against the sounding chord", test_realize_notes_read_against_the_sounding_chord)

    run_test("every note lands inside the live register", test_realize_stays_in_the_register)

    run_test("accent is accent_follow applied to the shared map", test_realize_accent_follows_the_map)

    run_test("timing is the one-measure groove vector, tiled", test_realize_timing_tiles_the_groove)

    run_test("the realized stream tracks the degree stream slot for slot", test_realize_agrees_with_the_degree_stream)

    run_test("a retrigger really does move the note", test_realize_retrigger_changes_the_note)


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
