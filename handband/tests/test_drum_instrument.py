"""
Drum Instrument Test

Test suite for MI_Drum_Instrument, in the same style as the other
suites. Covers the spec's required list:

- output contract: package shape, slot shape, no "C", fundamental,
  key set with variants off
- generation scale: cell length inherited from the bass, exact tiling
- density: monotonic in arousal, bounded (cell-scale floor), scales
  with max_density_rate
- capacity clamp: min(n, capacity) at every archetype, arousal 1.0
- coupling: monotonic in c, non-uniform mask, P = Q round-trip,
  never forbids a slot, c out of range raises
- weighting: syncopation strictly positive; alternating capacity
- emote extremes: no raise across the corners and both progression
  length extremes
- variant engine: partition, disjoint, off-states, axis modality,
  reachability, unknown axis raises
- input contract: dangling reference / name collision / cycle raise
"""

import random

from handband.mi.drum_instrument import (
    DrumElement,
    DrumsInstrument,
    default_drum_instrument,
    create_drum_part,
    reference_mask,
    drum_archetype_weights,
    build_element_cell,
    select_variant,
    realize_drum_element,
    DRUM_ARCHETYPES,
    KICK_OCTAVE,
    SNARE_OCTAVE,
    HAT_OCTAVE,
    SLOTS_PER_MEASURE,
)
from handband.mi.bass_instrument import bass_cell_measures
from handband.mi.global_parameters import CURRENT_KEY


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


def element(**kw):
    """Build a DrumElement with defaults overridable per test."""
    params = dict(name="test", octave=3, accent_follow=0.5,
                  groove_follow=0.5, max_density_rate=8,
                  syncopation_follow=0.5)
    params.update(kw)
    return DrumElement(**params)


def make_progression(measures):
    """A one-chord-per-measure progression, `measures` measures long."""
    prog = []
    for m in range(measures):
        prog.append("I" if m % 2 == 0 else "V")
        prog.extend(["C"] * (SLOTS_PER_MEASURE - 1))
    return prog


def make_song(measures):
    """Progression + accent map + groove vector + a bass reference, all
    handmade so lengths are exact and the reference is non-trivial."""
    prog = make_progression(measures)
    total = len(prog)
    accents = [1 if i % 4 == 0 else 0 for i in range(total)]
    groove = [0.0, 0.0, 0.15, 0.0] * 4
    bass = ["H" if i % SLOTS_PER_MEASURE in (0, 3, 7, 10) else
            ("C" if i % SLOTS_PER_MEASURE in (1, 4, 8) else "X")
            for i in range(total)]
    return prog, accents, groove, {"bass": bass}


def generate(measures=4, valence=0.0, arousal=0.5, instrument=None):
    prog, accents, groove, refs = make_song(measures)
    return prog, create_drum_part(valence, arousal, prog, accents, groove,
                                  refs, instrument)


# ============================================================
# OUTPUT CONTRACT
# ============================================================

print("\n" + "=" * 60)
print("OUTPUT CONTRACT")
print("=" * 60)

def test_oc_package_shape():
    prog, drums = generate()
    assert isinstance(drums, dict), "package must be a dict"
    for name, stream in drums.items():
        assert isinstance(stream, list), f"stream '{name}' is not a list"
        assert len(stream) == len(prog), \
            f"stream '{name}' length {len(stream)} != {len(prog)}"

run_test("package is a dict of song-length lists", test_oc_package_shape)

def test_oc_slot_shape():
    _prog, drums = generate()
    for name, stream in drums.items():
        for i, slot in enumerate(stream):
            if slot["type"] == "R":
                assert set(slot) == {"type"}, \
                    f"'{name}'[{i}] rest carries extra keys: {slot}"
            else:
                assert set(slot) == {"type", "notes", "accent", "timing"}, \
                    f"'{name}'[{i}] hit keys wrong: {sorted(slot)}"

run_test("every slot is a bare R or a full hit record", test_oc_slot_shape)

def test_oc_no_c():
    _prog, drums = generate(valence=-0.8, arousal=0.1)
    for name, stream in drums.items():
        assert all(s["type"] != "C" for s in stream), \
            f"'{name}' emitted a C — percussion never sustains"

run_test('"C" never appears in any drum stream', test_oc_no_c)

def test_oc_fundamental():
    _prog, drums = generate()
    octaves = {"kick": KICK_OCTAVE, "snare": SNARE_OCTAVE, "hat": HAT_OCTAVE}
    for name, stream in drums.items():
        expected = 12 * (octaves[name] + 1) + CURRENT_KEY
        for slot in stream:
            if slot["type"] == "H":
                assert slot["notes"] == [expected], \
                    f"'{name}' notes {slot['notes']}, expected [{expected}]"

run_test("notes = [12*(octave+1) + CURRENT_KEY] per element", test_oc_fundamental)

def test_oc_key_set():
    _prog, drums = generate()
    assert set(drums) == {"kick", "snare", "hat"}, \
        f"variants off: keys must be the element names, got {sorted(drums)}"

run_test("with variants off, key set is exactly the element names", test_oc_key_set)


# ============================================================
# GENERATION SCALE
# ============================================================

print("\n" + "=" * 60)
print("GENERATION SCALE")
print("=" * 60)

def test_gs_cell_from_bass():
    for measures in (1, 2, 4, 8):
        prog, drums = generate(measures=measures)
        cell_slots = bass_cell_measures(prog) * SLOTS_PER_MEASURE
        for name, stream in drums.items():
            for i in range(len(stream) - cell_slots):
                assert stream[i]["type"] == stream[i + cell_slots]["type"], \
                    (f"'{name}' not periodic at the bass cell "
                     f"({cell_slots} slots) at slot {i}")

run_test("stream is periodic at bass_cell_measures exactly (tiled cell)",
         test_gs_cell_from_bass)


# ============================================================
# DENSITY
# ============================================================

print("\n" + "=" * 60)
print("DENSITY")
print("=" * 60)

def _mean_cell_hits(el, valence, arousal, cell_measures, runs=300):
    total = 0
    for _ in range(runs):
        cell = build_element_cell(el, valence, arousal, cell_measures, {})
        total += sum(cell)
    return total / runs

def test_d_monotonic_arousal():
    el = element(max_density_rate=16)
    means = [_mean_cell_hits(el, 0.0, a, 1) for a in (0.1, 0.5, 0.9)]
    assert means[0] < means[1] < means[2], \
        f"hits not monotonic in arousal: {means}"

run_test("hits per cell monotonic in arousal (statistical)", test_d_monotonic_arousal)

def test_d_bounds():
    for cell_measures in (1, 2):
        cell_slots = cell_measures * SLOTS_PER_MEASURE
        for a in (0.0, 0.3, 1.0):
            for _ in range(200):
                cell = build_element_cell(element(max_density_rate=16),
                                          0.0, a, cell_measures, {})
                hits = sum(cell)
                # Floor at CELL scale — drums omit the silent-measure
                # repair, so per-measure assertions would be wrong here.
                assert hits >= cell_measures, \
                    f"hits {hits} below cell floor {cell_measures}"
                assert hits <= cell_slots, f"hits {hits} exceed {cell_slots}"

run_test("cell floor <= hits <= cell slots, at all arousal", test_d_bounds)

def test_d_rate_scales():
    lo = _mean_cell_hits(element(max_density_rate=4), 0.0, 0.6, 1)
    hi = _mean_cell_hits(element(max_density_rate=16), 0.0, 0.6, 1)
    assert hi > lo, f"max_density_rate had no effect: {lo} vs {hi}"

run_test("higher max_density_rate yields more hits at equal arousal",
         test_d_rate_scales)

def test_d_min_rate_floor():
    # The per-element floor: at arousal 0 the element plays exactly
    # min_density_rate hits per measure (capacity never bites — even
    # alternating offers 8 per measure).
    for cell_measures in (1, 2):
        el = element(min_density_rate=4, max_density_rate=16)
        assert el.density_per_measure(0.0) == 4
        for _ in range(100):
            cell = build_element_cell(el, 0.0, 0.0, cell_measures, {})
            assert sum(cell) == 4 * cell_measures, \
                f"expected {4 * cell_measures} hits, got {sum(cell)}"

run_test("min_density_rate is the floor at arousal 0", test_d_min_rate_floor)

def test_d_default_kit_density_windows():
    # The authored windows: hat 4..16, kick and snare 2..12.
    kit = {el.name: el for el in default_drum_instrument().elements}
    expected = {"kick": (2, 12), "snare": (2, 12), "hat": (4, 16)}
    for name, (lo, hi) in expected.items():
        assert kit[name].density_per_measure(0.0) == lo, \
            f"{name} floor {kit[name].density_per_measure(0.0)}, expected {lo}"
        assert kit[name].density_per_measure(1.0) == hi, \
            f"{name} ceiling {kit[name].density_per_measure(1.0)}, expected {hi}"

run_test("default kit density windows: hat 4-16, kick/snare 2-12",
         test_d_default_kit_density_windows)

def test_d_min_rate_invalid_raises():
    # Zero hits stays illegal, and a floor above the ceiling is a
    # config error — both raise rather than silently clamping.
    for bad_min, mx in ((0, 8), (-2, 8), (9, 8)):
        try:
            element(min_density_rate=bad_min, max_density_rate=mx)
            assert False, f"min={bad_min}, max={mx} did not raise"
        except ValueError:
            pass

run_test("min_density_rate outside [1, max_density_rate] raises",
         test_d_min_rate_invalid_raises)


# ============================================================
# CAPACITY CLAMP
# ============================================================

print("\n" + "=" * 60)
print("CAPACITY CLAMP")
print("=" * 60)

def test_cc_capacities():
    for archetype in DRUM_ARCHETYPES:
        for _ in range(50):
            weights, capacity = drum_archetype_weights(archetype, 16, 16)
            assert capacity == sum(1 for w in weights if w > 0)
            if archetype == "alternating":
                assert capacity == 8, \
                    f"alternating capacity {capacity}, expected 8 over 16"
            else:
                assert capacity == 16, \
                    f"{archetype} capacity {capacity}, expected 16"

run_test("capacity = nonzero weights; only alternating restricts it",
         test_cc_capacities)

def test_cc_clamped_at_full_arousal():
    # rate 16 at arousal 1.0 demands 16 hits; alternating only offers 8.
    # Placement must never be handed more hits than nonzero weights —
    # the bug class that crashed the chord progression engine.
    seen = set()
    for _ in range(400):
        cell = build_element_cell(element(max_density_rate=16),
                                  0.0, 1.0, 1, {})
        hits = sum(cell)
        assert hits in (8, 16), f"unexpected hit count {hits}"
        seen.add(hits)
    assert seen == {8, 16}, \
        f"expected both full (16) and alternating-clamped (8) cells: {seen}"

run_test("density clamped to min(n, capacity) at every archetype, arousal 1",
         test_cc_clamped_at_full_arousal)


# ============================================================
# COUPLING
# ============================================================

print("\n" + "=" * 60)
print("COUPLING")
print("=" * 60)

# A deliberately non-uniform mask: strong on the beats, silent elsewhere.
COUPLING_MASK = [1.0 if i % 4 == 0 else 0.0 for i in range(16)]

def _mean_overlap(c, runs=500):
    el = element(max_density_rate=8, coupling={"ref": c})
    total = 0.0
    for _ in range(runs):
        cell = build_element_cell(el, 0.0, 0.5, 1, {"ref": COUPLING_MASK})
        hits = sum(cell)
        total += sum(m for q, m in enumerate(COUPLING_MASK) if cell[q]) / hits
    return total / runs

def test_cp_mask_not_uniform():
    assert len(set(COUPLING_MASK)) > 1, \
        "test mask is uniform — a uniform bias is no bias at all"

run_test("the reference mask used by these tests is not uniform",
         test_cp_mask_not_uniform)

def test_cp_monotonic_in_c():
    overlaps = [_mean_overlap(c) for c in (-1.0, 0.0, 1.0)]
    assert overlaps[0] < overlaps[1] < overlaps[2], \
        f"overlap not monotonic in c: {overlaps}"

run_test("overlap with the reference is monotonic in c (-1, 0, +1)",
         test_cp_monotonic_in_c)

def test_cp_round_trip():
    # A pattern already periodic at the cell length folds back to
    # exactly its own cell.
    cell = ["H" if i in (0, 3, 7, 10) else "X" for i in range(16)]
    mask = reference_mask(cell * 4, 16)
    expected = [1.0 if s == "H" else 0.0 for s in cell]
    assert mask == expected, f"P = Q fold changed the cell: {mask}"

run_test("a P = Q reference round-trips to its own cell", test_cp_round_trip)

def test_cp_fold_is_fractional():
    # P = 2Q: a slot hit in both halves is a stronger anchor (1.0) than
    # one hit in only one (0.5) — information boolean folding discards.
    part = (["H"] + ["X"] * 15) + (["H"] + ["X"] * 7 + ["H"] + ["X"] * 7)
    mask = reference_mask(part, 16)
    assert mask[0] == 1.0 and mask[8] == 0.5, \
        f"fold not fractional: mask[0]={mask[0]} mask[8]={mask[8]}"

run_test("folding is fractional, not boolean", test_cp_fold_is_fractional)

def test_cp_never_forbids():
    # Full avoid at a saturated mask slot: DRUM_COUPLING_FLOOR must keep
    # every slot reachable over many seeds.
    el = element(max_density_rate=8, coupling={"ref": -1.0})
    seen = set()
    for _ in range(800):
        cell = build_element_cell(el, 0.0, 0.5, 1, {"ref": COUPLING_MASK})
        seen.update(q for q in range(16) if cell[q])
    assert seen == set(range(16)), \
        f"slots never hit under c=-1: {sorted(set(range(16)) - seen)}"

run_test("coupling never forbids a slot (DRUM_COUPLING_FLOOR)",
         test_cp_never_forbids)

def test_cp_out_of_range_raises():
    for bad in (-1.5, 1.01, 7):
        try:
            element(coupling={"ref": bad})
            assert False, f"coupling c={bad} did not raise"
        except ValueError:
            pass

run_test("c outside [-1, 1] raises", test_cp_out_of_range_raises)


# ============================================================
# WEIGHTING
# ============================================================

print("\n" + "=" * 60)
print("WEIGHTING")
print("=" * 60)

def test_w_syncopation_positive():
    for _ in range(500):
        el = element(syncopation_follow=random.random())
        weights = el.syncopation_weights(random.uniform(-1, 1)) * 2
        assert all(w > 0 for w in weights), \
            f"syncopation weight hit zero: {weights}"

run_test("syncopation weights strictly positive over the whole cell",
         test_w_syncopation_positive)

def test_w_alternating_zeros_are_legal():
    # Archetype weights are NOT required positive — alternating's zeros
    # are its shape. The invariant that matters is the capacity clamp
    # (tested above): the placer is never handed more hits than nonzero
    # weights.
    weights, capacity = drum_archetype_weights("alternating", 16, 16)
    assert 0 in weights, "alternating should carry hard zeros"
    assert capacity == 8

run_test("alternating legitimately has zeros; capacity covers them",
         test_w_alternating_zeros_are_legal)


# ============================================================
# EMOTE EXTREMES
# ============================================================

print("\n" + "=" * 60)
print("EMOTE EXTREMES")
print("=" * 60)

def test_ee_corners():
    # All valence/arousal corners, at the shortest (1 measure) and
    # longest (8 measures) progression the form engine can produce.
    for measures in (1, 8):
        for v in (-1.0, 0.0, 1.0):
            for a in (0.0, 1.0):
                prog, drums = generate(measures=measures, valence=v,
                                       arousal=a)
                assert set(drums) == {"kick", "snare", "hat"}
                for stream in drums.values():
                    assert len(stream) == len(prog)

run_test("generates at every emote corner and both length extremes",
         test_ee_corners)


# ============================================================
# VARIANT ENGINE
# ============================================================

print("\n" + "=" * 60)
print("VARIANT ENGINE")
print("=" * 60)

VARIANTS = {"axis": "valence",
            "variants": [("ride", -0.75), ("hi-hat", 0.0), ("crash", 0.75)]}
EMOTE = {"valence": 0.0, "arousal": 0.5}

def _realized_variants(valence=0.0):
    el = element(variant_table=VARIANTS)
    cell = [1 if i % 2 == 0 else 0 for i in range(16)]   # 8 hits, known
    prog = make_progression(4)
    accents = [0] * len(prog)
    groove = [0.0] * 16
    streams = realize_drum_element(el, cell, prog, accents, groove,
                                   {"valence": valence, "arousal": 0.5})
    return cell, prog, streams

def test_v_partition():
    cell, prog, streams = _realized_variants()
    expected = sum(cell) * (len(prog) // len(cell))
    total = sum(sum(1 for s in stream if s["type"] == "H")
                for stream in streams.values())
    assert total == expected, \
        f"hits lost/duplicated across variant streams: {total} != {expected}"

run_test("partition: summed H across variant streams = cell_hits x tiles",
         test_v_partition)

def test_v_disjoint():
    _cell, prog, streams = _realized_variants()
    for i in range(len(prog)):
        hs = [n for n, s in streams.items() if s[i]["type"] == "H"]
        assert len(hs) <= 1, f"slot {i} struck in two streams: {hs}"

run_test("disjoint: no slot carries H in two of an element's streams",
         test_v_disjoint)

def test_v_off_states():
    for table in (None, {"axis": "valence", "variants": []}):
        el = element(name="kick", variant_table=table)
        streams = realize_drum_element(el, [1] + [0] * 15,
                                       make_progression(1), [0] * 16,
                                       [0.0] * 16, EMOTE)
        assert set(streams) == {"kick"}, \
            f"empty table should key by ELEMENT name, got {sorted(streams)}"
    el = element(name="kick",
                 variant_table={"axis": "valence",
                                "variants": [("hi-hat", 0.0)]})
    streams = realize_drum_element(el, [1] + [0] * 15, make_progression(1),
                                   [0] * 16, [0.0] * 16, EMOTE)
    assert set(streams) == {"hi-hat"}, \
        f"single entry should key by ENTRY name, got {sorted(streams)}"

run_test("off: empty table -> element name; one entry -> entry name",
         test_v_off_states)

def test_v_axis_modal():
    for name, center in VARIANTS["variants"]:
        draws = [select_variant(VARIANTS, {"valence": center})
                 for _ in range(3000)]
        counts = {n: draws.count(n) for n, _ in VARIANTS["variants"]}
        assert max(counts, key=counts.get) == name, \
            f"at e={center} modal draw was not '{name}': {counts}"

run_test("at e = a variant's center, that variant is the modal draw",
         test_v_axis_modal)

def test_v_reachability():
    for e in (-1.0, 0.0, 1.0):
        seen = {select_variant(VARIANTS, {"valence": e})
                for _ in range(4000)}
        assert seen == {"ride", "hi-hat", "crash"}, \
            f"a variant was unreachable at e={e}: {seen}"

run_test("every variant reachable at any e (VARIANT_WEIGHT_FLOOR)",
         test_v_reachability)

def test_v_unknown_axis_raises():
    bad = {"axis": "tempo", "variants": [("a", 0.0), ("b", 1.0)]}
    try:
        select_variant(bad, EMOTE)
        assert False, "unknown axis did not raise"
    except ValueError:
        pass

run_test('an unknown "axis" raises', test_v_unknown_axis_raises)


# ============================================================
# INPUT CONTRACT
# ============================================================

print("\n" + "=" * 60)
print("INPUT CONTRACT")
print("=" * 60)

def test_ic_dangling_raises():
    kit = DrumsInstrument([element(name="kick",
                                   coupling={"ghost": 0.5})])
    prog, accents, groove, refs = make_song(2)
    try:
        kit.create_part(0.0, 0.5, prog, accents, groove, refs)
        assert False, "dangling reference did not raise"
    except ValueError as e:
        assert "ghost" in str(e), f"error does not name the offender: {e}"

run_test("a dangling coupling reference raises, naming the offender",
         test_ic_dangling_raises)

def test_ic_collision_raises():
    kit = default_drum_instrument()
    prog, accents, groove, refs = make_song(2)
    refs["kick"] = refs["bass"]   # collides with the kick element
    try:
        kit.create_part(0.0, 0.5, prog, accents, groove, refs)
        assert False, "kit/references name collision did not raise"
    except ValueError as e:
        assert "kick" in str(e)

run_test("a name colliding between kit and references raises",
         test_ic_collision_raises)

def test_ic_cycle_raises():
    kit = DrumsInstrument([
        element(name="kick", coupling={"snare": 0.5}),
        element(name="snare", coupling={"kick": 0.5}),
    ])
    prog, accents, groove, refs = make_song(2)
    try:
        kit.create_part(0.0, 0.5, prog, accents, groove, refs)
        assert False, "cyclic coupling graph did not raise"
    except ValueError as e:
        assert "cyclic" in str(e).lower()

run_test("a cyclic coupling graph raises rather than deadlocking",
         test_ic_cycle_raises)


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
