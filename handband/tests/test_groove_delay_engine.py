"""
Groove/Delay Engine Test

Comprehensive test suite for MI_Groove_Delay_Engine, modeled on the
Accent Pattern Engine test suite. Runs up to 10,000 trials per
statistical test to verify distributions, invariants, and the
valence/arousal roles behave as designed.

The groove engine is deliberately simpler than the accent engine:
there is no form (no repetition pattern, no sections, no tiling) —
just ONE 16-slot measure of timing feel. So the tests focus on:

- groove_density_calculator: int, floor of 0 (empty at center),
  arousal=0 → 0, arousal=1 → b, monotonic, known values
- groove_archetype_calculator: valid outputs, uniform distribution
- choose_groove_archetype: triple, weight length, capacity shapes
- displacement_value: sign follows valence, magnitude follows
  arousal, zero at either center, exact known values
- apply_groove_archetype: length 16, exact displaced count, one
  uniform signed offset, direction, even spacing, capacity clamp,
  n<=0 → all grid
- create_groove_pattern: full pipeline, center is empty, count and
  magnitude grow with arousal, direction tracks valence, boundaries
- Edge case gauntlet + cross-function integration

Distribution reports print inline so biases can be eyeballed.
Tests marked "(visual)" pass as long as they don't crash.
"""

import math
import random
from collections import Counter
from handband.mi.groove_delay_engine import (
    groove_density_calculator,
    groove_archetype_calculator,
    choose_groove_archetype,
    displacement_value,
    apply_groove_archetype,
    create_groove_pattern,
    SLOTS_PER_MEASURE,
    MAX_DELAYS_PER_MEASURE,
    MAX_DELAY,
)


# ============================================================
# TEST INFRASTRUCTURE
# ============================================================

TRIALS = 10000
passed = 0
failed = 0
errors = []

def run_test(name, fn):
    """Run a single test, track pass/fail, print result."""
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

def distribution_report(name, counter, total):
    """Print a horizontal bar chart of a Counter's distribution."""
    print(f"    [{name}] n={total}")
    for key in sorted(counter.keys(), key=lambda x: str(x)):
        pct = counter[key] / total * 100
        bar = "█" * int(pct / 2)
        print(f"      {str(key):>12}: {pct:5.1f}%  {bar}")

VALID_ARCHETYPES = {"front", "back", "center", "alternating", "even", "random"}


# ============================================================
# GROOVE_DENSITY_CALCULATOR TESTS
# ============================================================

print("\n" + "=" * 60)
print("GROOVE_DENSITY_CALCULATOR")
print("=" * 60)

def test_gdc_returns_int():
    result = groove_density_calculator(0.5)
    assert isinstance(result, int), f"Expected int, got {type(result)}"

run_test("returns integer", test_gdc_returns_int)

def test_gdc_arousal_zero_gives_zero():
    # The center of the emotion space is calm: no groove at all.
    result = groove_density_calculator(0.0)
    assert result == 0, f"arousal=0 should give 0 (empty groove), got {result}"

run_test("arousal=0 gives an empty groove (density 0)", test_gdc_arousal_zero_gives_zero)

def test_gdc_arousal_one_gives_b():
    result = groove_density_calculator(1.0)
    assert result == MAX_DELAYS_PER_MEASURE, \
        f"arousal=1 should give b={MAX_DELAYS_PER_MEASURE}, got {result}"

run_test("arousal=1 gives the full b displaced slots", test_gdc_arousal_one_gives_b)

def test_gdc_never_negative():
    for _ in range(500):
        result = groove_density_calculator(random.random())
        assert result >= 0, f"Got {result}, expected >= 0"

run_test("never returns a negative density", test_gdc_never_negative)

def test_gdc_bounded_by_slots():
    for _ in range(500):
        result = groove_density_calculator(random.random())
        assert result <= SLOTS_PER_MEASURE, \
            f"density {result} exceeds the 16-slot measure"

run_test("density never exceeds the 16 slots in a measure", test_gdc_bounded_by_slots)

def test_gdc_known_values():
    # round(b * arousal)
    assert groove_density_calculator(0.5) == round(MAX_DELAYS_PER_MEASURE * 0.5)
    assert groove_density_calculator(0.25) == round(MAX_DELAYS_PER_MEASURE * 0.25)
    assert groove_density_calculator(1.0) == round(MAX_DELAYS_PER_MEASURE * 1.0)

run_test("matches round(b * arousal) for known inputs", test_gdc_known_values)

def test_gdc_monotonic_in_arousal():
    prev = groove_density_calculator(0.0)
    for a in [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
        curr = groove_density_calculator(a)
        assert curr >= prev, f"density not monotonic at arousal={a}: {curr} < {prev}"
        prev = curr

run_test("monotonically increases with arousal", test_gdc_monotonic_in_arousal)


# ============================================================
# GROOVE_ARCHETYPE_CALCULATOR TESTS
# ============================================================

print("\n" + "=" * 60)
print("GROOVE_ARCHETYPE_CALCULATOR")
print("=" * 60)

def test_gac_valid_outputs():
    for _ in range(TRIALS):
        result = groove_archetype_calculator()
        assert result in VALID_ARCHETYPES, f"Got invalid archetype: '{result}'"

run_test("always returns a valid archetype", test_gac_valid_outputs)

def test_gac_roughly_uniform():
    counts = Counter()
    for _ in range(TRIALS):
        counts[groove_archetype_calculator()] += 1
    for archetype in VALID_ARCHETYPES:
        ratio = counts[archetype] / TRIALS
        assert 0.10 < ratio < 0.25, \
            f"'{archetype}' at {ratio*100:.1f}%, expected ~16.7%"
    distribution_report("all archetypes", counts, TRIALS)

run_test("roughly uniform distribution over 6 archetypes", test_gac_roughly_uniform)


# ============================================================
# CHOOSE_GROOVE_ARCHETYPE TESTS
# ============================================================

print("\n" + "=" * 60)
print("CHOOSE_GROOVE_ARCHETYPE")
print("=" * 60)

def test_cga_returns_triple():
    result = choose_groove_archetype(16)
    assert len(result) == 3, f"Expected (archetype, weights, capacity), got {result}"
    archetype, weights, capacity = result
    assert archetype in VALID_ARCHETYPES

run_test("returns (archetype, weights, capacity)", test_cga_returns_triple)

def test_cga_weights_length_matches_slots():
    for slots in [16, 32, 64]:
        for _ in range(50):
            _, weights, _ = choose_groove_archetype(slots)
            assert len(weights) == slots, f"slots={slots}: got {len(weights)} weights"

run_test("weight vector length always equals slots", test_cga_weights_length_matches_slots)

def test_cga_capacity_bounds():
    for _ in range(1000):
        slots = random.choice([16, 32, 64])
        _, weights, capacity = choose_groove_archetype(slots)
        assert capacity == sum(1 for w in weights if w > 0), \
            "capacity must equal count of positive weights"
        assert 1 <= capacity <= slots, f"capacity {capacity} out of [1, {slots}]"

run_test("capacity equals positive-weight count and is within [1, slots]", test_cga_capacity_bounds)

def test_cga_weights_nonnegative():
    for _ in range(1000):
        _, weights, _ = choose_groove_archetype(random.choice([16, 32, 64]))
        assert all(w >= 0 for w in weights), "weights must be non-negative"

run_test("all weights are non-negative", test_cga_weights_nonnegative)

def test_cga_even_and_random_full_capacity():
    for archetype_target in ("even", "random"):
        found = False
        for _ in range(2000):
            archetype, weights, capacity = choose_groove_archetype(16)
            if archetype == archetype_target:
                found = True
                assert capacity == 16, \
                    f"'{archetype_target}' should offer full capacity, got {capacity}"
        assert found, f"'{archetype_target}' never chosen in 2000 draws"

run_test("'even' and 'random' offer full capacity", test_cga_even_and_random_full_capacity)

def test_cga_alternating_half_capacity():
    for _ in range(2000):
        archetype, weights, capacity = choose_groove_archetype(16)
        if archetype == "alternating":
            assert capacity == 8, \
                f"'alternating' over 16 slots should have capacity 8, got {capacity}"

run_test("'alternating' leaves half the slots empty", test_cga_alternating_half_capacity)


# ============================================================
# DISPLACEMENT_VALUE TESTS
# ============================================================

print("\n" + "=" * 60)
print("DISPLACEMENT_VALUE")
print("=" * 60)

def test_dv_zero_at_valence_zero():
    for a in [0.0, 0.3, 0.7, 1.0]:
        assert displacement_value(0.0, a) == 0.0, \
            f"valence=0 must give 0 offset regardless of arousal={a}"

run_test("valence=0 gives zero offset (no direction)", test_dv_zero_at_valence_zero)

def test_dv_zero_at_arousal_zero():
    for v in [-1.0, -0.5, 0.5, 1.0]:
        assert displacement_value(v, 0.0) == 0.0, \
            f"arousal=0 must give 0 offset regardless of valence={v}"

run_test("arousal=0 gives zero offset (no intensity)", test_dv_zero_at_arousal_zero)

def test_dv_positive_valence_pulls():
    # Positive valence -> positive offset (laid back / behind the beat).
    for _ in range(500):
        v = random.uniform(0.01, 1.0)
        a = random.uniform(0.01, 1.0)
        assert displacement_value(v, a) > 0, \
            f"positive valence should pull (positive offset): v={v}, a={a}"

run_test("positive valence produces a positive (behind-the-beat) offset", test_dv_positive_valence_pulls)

def test_dv_negative_valence_pushes():
    # Negative valence -> negative offset (on top / ahead of the beat).
    for _ in range(500):
        v = random.uniform(-1.0, -0.01)
        a = random.uniform(0.01, 1.0)
        assert displacement_value(v, a) < 0, \
            f"negative valence should push (negative offset): v={v}, a={a}"

run_test("negative valence produces a negative (on-top) offset", test_dv_negative_valence_pushes)

def test_dv_known_magnitude():
    # |offset| = arousal * MAX_DELAY, sign from valence
    assert math.isclose(displacement_value(1.0, 1.0), MAX_DELAY)
    assert math.isclose(displacement_value(-1.0, 1.0), -MAX_DELAY)
    assert math.isclose(displacement_value(0.5, 0.5), 0.5 * MAX_DELAY)
    assert math.isclose(displacement_value(-0.2, 0.25), -0.25 * MAX_DELAY)

run_test("magnitude is arousal * MAX_DELAY with valence's sign", test_dv_known_magnitude)

def test_dv_magnitude_independent_of_valence_size():
    # Only the SIGN of valence matters; its magnitude does not scale the offset.
    a = 0.7
    assert math.isclose(displacement_value(0.1, a), displacement_value(0.9, a)), \
        "offset should depend on valence sign only, not its magnitude"
    assert math.isclose(displacement_value(-0.1, a), displacement_value(-0.9, a)), \
        "offset should depend on valence sign only, not its magnitude"

run_test("only valence's sign matters, not its size", test_dv_magnitude_independent_of_valence_size)

def test_dv_magnitude_capped():
    for _ in range(1000):
        v = random.uniform(-1, 1)
        a = random.random()
        assert abs(displacement_value(v, a)) <= MAX_DELAY + 1e-9, \
            "offset magnitude must never exceed MAX_DELAY"

run_test("offset magnitude never exceeds MAX_DELAY", test_dv_magnitude_capped)


# ============================================================
# APPLY_GROOVE_ARCHETYPE TESTS
# ============================================================

print("\n" + "=" * 60)
print("APPLY_GROOVE_ARCHETYPE")
print("=" * 60)

# Mirrors real caller usage: choose the shape, clamp the count to the
# layout's capacity, then place. Returns the displacement vector + count.
def placed_groove(slots, density, valence, arousal):
    archetype, weights, capacity = choose_groove_archetype(slots)
    n = min(density, capacity)
    return apply_groove_archetype(slots, n, archetype, weights, valence, arousal), n

def test_aga_output_length():
    for slots in [16, 32, 64]:
        for density in range(1, 6):
            vec, _ = placed_groove(slots, density, 0.8, 0.8)
            assert len(vec) == slots, f"slots={slots}: got {len(vec)}"

run_test("output length always equals slots", test_aga_output_length)

def test_aga_zero_count_all_grid():
    for slots in [16, 32]:
        archetype, weights, _ = choose_groove_archetype(slots)
        for n in (0, -1):
            vec = apply_groove_archetype(slots, n, archetype, weights, 0.9, 0.9)
            assert vec == [0.0] * slots, f"n={n} should leave every hit on the grid"

run_test("n<=0 leaves the whole measure on the grid", test_aga_zero_count_all_grid)

def test_aga_exact_displaced_count():
    # With nonzero valence AND arousal, every placed slot is a nonzero offset.
    for _ in range(1000):
        slots = random.choice([16, 32])
        vec, n = placed_groove(slots, random.randint(1, 12), 0.8, 0.8)
        moved = sum(1 for v in vec if v != 0.0)
        assert moved == n, f"Expected {n} displaced slots, got {moved}"

run_test("number of displaced slots equals the (clamped) count", test_aga_exact_displaced_count)

def test_aga_uniform_offset():
    # All displaced slots share exactly one offset value.
    for _ in range(1000):
        slots = 16
        vec, n = placed_groove(slots, random.randint(1, 8), 0.6, 0.6)
        nonzero = [v for v in vec if v != 0.0]
        assert len(set(nonzero)) <= 1, \
            f"displaced slots must share one uniform offset, got {set(nonzero)}"

run_test("all displaced slots carry one uniform offset", test_aga_uniform_offset)

def test_aga_offset_matches_displacement_value():
    for _ in range(500):
        v = random.uniform(0.01, 1.0)
        a = random.uniform(0.01, 1.0)
        archetype, weights, capacity = choose_groove_archetype(16)
        n = min(4, capacity)
        vec = apply_groove_archetype(16, n, archetype, weights, v, a)
        expected = displacement_value(v, a)
        for slot in vec:
            if slot != 0.0:
                assert math.isclose(slot, expected), \
                    f"slot offset {slot} != displacement_value {expected}"

run_test("displaced offset equals displacement_value(valence, arousal)", test_aga_offset_matches_displacement_value)

def test_aga_direction_tracks_valence():
    for _ in range(500):
        a = random.uniform(0.2, 1.0)
        # positive valence -> all offsets >= 0
        vec_pos, _ = placed_groove(16, 4, 0.7, a)
        assert all(v >= 0 for v in vec_pos), "positive valence produced a push offset"
        # negative valence -> all offsets <= 0
        vec_neg, _ = placed_groove(16, 4, -0.7, a)
        assert all(v <= 0 for v in vec_neg), "negative valence produced a pull offset"

run_test("offset direction tracks valence sign across the measure", test_aga_direction_tracks_valence)

def test_aga_clamp_never_crashes():
    # Short measure + high density + a capacity-limited shape (alternating).
    for _ in range(3000):
        slots = random.choice([16, 32])
        density = slots  # deliberately ask for the whole measure
        vec, n = placed_groove(slots, density, 0.9, 0.9)
        moved = sum(1 for v in vec if v != 0.0)
        assert moved == n, "Clamp failed: displaced a different count than asked"
        assert len(vec) == slots

run_test("density exceeding capacity clamps instead of crashing", test_aga_clamp_never_crashes)

def test_aga_even_hits_downbeat_and_spaces_evenly():
    _, weights, _ = choose_groove_archetype(16)  # weights unused by 'even'
    for n in [1, 2, 4, 8]:
        vec = apply_groove_archetype(16, n, "even", weights, 0.8, 0.8)
        moved = sum(1 for v in vec if v != 0.0)
        assert moved == n
        assert vec[0] != 0.0, f"'even' should displace the downbeat, n={n}: {vec}"
        positions = [i for i, v in enumerate(vec) if v != 0.0]
        expected = [int(i * 16 / n) for i in range(n)]
        assert positions == expected, \
            f"'even' spacing off for n={n}: {positions} != {expected}"

run_test("'even' displaces the downbeat and spaces hits regularly", test_aga_even_hits_downbeat_and_spaces_evenly)


# ============================================================
# CREATE_GROOVE_PATTERN TESTS
# ============================================================

print("\n" + "=" * 60)
print("CREATE_GROOVE_PATTERN")
print("=" * 60)

def test_cgp_returns_list():
    result = create_groove_pattern(0.5, 0.5)
    assert isinstance(result, list), f"Expected list, got {type(result)}"

run_test("returns a list", test_cgp_returns_list)

def test_cgp_length_is_16():
    for _ in range(300):
        result = create_groove_pattern(random.uniform(-1, 1), random.random())
        assert len(result) == SLOTS_PER_MEASURE, \
            f"groove must be one 16-slot measure, got {len(result)}"

run_test("length is always exactly 16 (one measure)", test_cgp_length_is_16)

def test_cgp_entries_are_offset_or_zero():
    for _ in range(500):
        v = random.uniform(-1, 1)
        a = random.random()
        result = create_groove_pattern(v, a)
        offset = displacement_value(v, a)
        for slot in result:
            assert slot == 0.0 or math.isclose(slot, offset), \
                f"slot {slot} is neither 0 nor the offset {offset}"

run_test("every entry is either 0 or the one groove offset", test_cgp_entries_are_offset_or_zero)

def test_cgp_center_is_empty():
    # input 0 -> valence 0, arousal 0 -> everything on the grid.
    for _ in range(200):
        result = create_groove_pattern(0.0, 0.0)
        assert all(v == 0.0 for v in result), \
            f"the neutral center must produce a flat, on-grid groove: {result}"

run_test("neutral center (0,0) produces an empty groove", test_cgp_center_is_empty)

def test_cgp_displaced_count_grows_with_arousal():
    low = sum(1 for _ in range(2000) for v in create_groove_pattern(0.6, 0.2) if v != 0.0)
    high = sum(1 for _ in range(2000) for v in create_groove_pattern(0.6, 0.9) if v != 0.0)
    print(f"    total displaced slots (valence=0.6): arousal=0.2 → {low}, arousal=0.9 → {high}")
    assert high > low, f"displaced slots should grow with arousal: low={low}, high={high}"

run_test("displaced-slot count grows with arousal", test_cgp_displaced_count_grows_with_arousal)

def test_cgp_magnitude_grows_with_arousal():
    lo = abs(displacement_value(0.6, 0.2))
    hi = abs(displacement_value(0.6, 0.9))
    print(f"    offset magnitude (valence=0.6): arousal=0.2 → {lo:.3f}, arousal=0.9 → {hi:.3f}")
    assert hi > lo, "offset magnitude should grow with arousal"

run_test("offset magnitude grows with arousal", test_cgp_magnitude_grows_with_arousal)

def test_cgp_direction_tracks_valence():
    for _ in range(500):
        a = random.uniform(0.3, 1.0)
        pos = create_groove_pattern(0.8, a)
        neg = create_groove_pattern(-0.8, a)
        assert all(v >= 0 for v in pos), "positive valence should never push"
        assert all(v <= 0 for v in neg), "negative valence should never pull"

run_test("groove direction tracks valence sign", test_cgp_direction_tracks_valence)

def test_cgp_boundary_corners():
    for v in (-1.0, 0.0, 1.0):
        for a in (0.0, 1.0):
            result = create_groove_pattern(v, a)
            assert len(result) == SLOTS_PER_MEASURE
            offset = displacement_value(v, a)
            assert all(s == 0.0 or math.isclose(s, offset) for s in result)

run_test("valence/arousal boundary corners don't crash and stay valid", test_cgp_boundary_corners)

def test_cgp_sample_outputs():
    print("    Sample groove measures (fraction of a slot per hit):")
    for inp in [0.3, -0.5, 0.8, -1.0]:
        v = inp
        a = abs(inp) ** 2.0
        groove = create_groove_pattern(v, a)
        cells = " ".join(f"{x:+.2f}" if x else "  .  " for x in groove)
        moved = sum(1 for x in groove if x)
        print(f"      input={inp:+.1f} v={v:+.2f} a={a:.2f} moved={moved}")
        print(f"        {cells}")

run_test("sample groove measures (visual)", test_cgp_sample_outputs)


# ============================================================
# EDGE CASE GAUNTLET
# ============================================================

print("\n" + "=" * 60)
print("EDGE CASE GAUNTLET")
print("=" * 60)

def test_edge_full_grid_no_crash():
    count = 0
    for vstep in range(-10, 11):
        v = vstep / 10
        for astep in range(21):
            a = astep / 20
            for _ in range(10):
                result = create_groove_pattern(v, a)
                assert len(result) == SLOTS_PER_MEASURE
                offset = displacement_value(v, a)
                assert all(s == 0.0 or math.isclose(s, offset) for s in result)
                count += 1
    print(f"    swept {count} (valence × arousal × trials) cases with no crash")

run_test("full valence × arousal grid produces valid output", test_edge_full_grid_no_crash)

def test_edge_zero_valence_nonzero_arousal_is_empty():
    # valence exactly 0 means no direction -> offset 0 even if arousal is high,
    # so the groove reads as empty (every slot on the grid).
    for _ in range(200):
        result = create_groove_pattern(0.0, random.random())
        assert all(v == 0.0 for v in result), \
            "zero valence must yield an on-grid groove regardless of arousal"

run_test("zero valence yields an empty groove at any arousal", test_edge_zero_valence_nonzero_arousal_is_empty)

def test_edge_max_arousal_fills_up_to_capacity():
    # arousal 1.0 asks for b=8 displaced slots; capacity-limited shapes clamp.
    for _ in range(500):
        result = create_groove_pattern(1.0, 1.0)
        moved = sum(1 for v in result if v != 0.0)
        assert 1 <= moved <= MAX_DELAYS_PER_MEASURE, \
            f"arousal=1 displaced {moved}, expected 1..{MAX_DELAYS_PER_MEASURE}"

run_test("arousal=1 displaces up to b slots, clamped by archetype", test_edge_max_arousal_fills_up_to_capacity)


# ============================================================
# CROSS-FUNCTION INTEGRATION
# ============================================================

print("\n" + "=" * 60)
print("CROSS-FUNCTION INTEGRATION")
print("=" * 60)

def test_int_full_pipeline_many_runs():
    for _ in range(1000):
        v = random.uniform(-1, 1)
        a = random.random()
        result = create_groove_pattern(v, a)
        assert isinstance(result, list)
        assert len(result) == SLOTS_PER_MEASURE
        offset = displacement_value(v, a)
        assert all(s == 0.0 or math.isclose(s, offset) for s in result)

run_test("full pipeline: 1000 random runs all produce valid output", test_int_full_pipeline_many_runs)

def test_int_emote_coupled_sweep():
    # Drive the engine the way EMOTE actually does: one input slider,
    # valence = input, arousal = input^2. Verify the emergent behavior —
    # groove intensifies away from center, direction flips at 0.
    for inp in [-1.0, -0.5, -0.1, 0.1, 0.5, 1.0]:
        v = inp
        a = abs(inp) ** 2.0
        result = create_groove_pattern(v, a)
        offset = displacement_value(v, a)
        assert all(s == 0.0 or math.isclose(s, offset) for s in result)
        nonzero = [s for s in result if s != 0.0]
        if nonzero:
            if inp > 0:
                assert all(s > 0 for s in nonzero), "positive input should pull"
            else:
                assert all(s < 0 for s in nonzero), "negative input should push"

run_test("EMOTE-coupled input sweep behaves coherently", test_int_emote_coupled_sweep)


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
