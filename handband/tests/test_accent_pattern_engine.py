"""
Accent Pattern Engine Test

Comprehensive test suite for MI_Accent_Pattern_Engine, modeled on the
Chord Progression Engine test suite. Runs up to 10,000 trials per
statistical test to verify distributions, invariants, and directional
biases behave as designed.

Structure:
- accent_density_calculator: int, floor, monotonic in arousal and
  measures, known values, arousal=0 floor
- accent_archetype_calculator: valid outputs, uniform distribution
- choose_accent_archetype: weight-vector length, capacity bounds,
  per-archetype capacity shapes
- apply_accent_archetype: binary output, exact accent count, length,
  even-spacing behavior, capacity clamp never crashes
- accent_pattern_calculator: total length, binary, repeated sections
  identical, different letters can differ, at least one accent
- create_accent_pattern: full pipeline smoke test, output structure,
  arousal/measure trends, emote boundary values
- Edge case gauntlet: arousal at extremes, single measure, full grid
- Cross-function integration: pipeline invariants

Distribution reports print inline so biases and curves can be eyeballed.
Tests marked "(visual)" pass as long as they don't crash.
"""

import random
from collections import Counter
from handband.mi.accent_pattern_engine import (
    accent_density_calculator,
    accent_archetype_calculator,
    choose_accent_archetype,
    apply_accent_archetype,
    accent_pattern_calculator,
    create_accent_pattern,
    SLOTS_PER_MEASURE,
    MAX_ACCENTS_PER_MEASURE,
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
PROG_LENGTHS = [1, 2, 4, 8]


def a_pattern(measures):
    """
    Test scaffolding: build a valid shared repetition pattern whose
    length divides `measures`, so it tiles the accent grid cleanly.

    The engine no longer derives its own repetition pattern — it
    receives the harmonic engine's form — so the tests supply one here
    to exercise create_accent_pattern the way the real pipeline feeds it.
    """
    divisors = [d for d in range(1, measures + 1) if measures % d == 0]
    n = random.choice(divisors)
    letters = [chr(65 + i) for i in range(n)]
    return ['A'] + [random.choice(letters) for _ in range(n - 1)]


# ============================================================
# ACCENT_DENSITY_CALCULATOR TESTS
# ============================================================

print("\n" + "=" * 60)
print("ACCENT_DENSITY_CALCULATOR")
print("=" * 60)

def test_adc_returns_int():
    result = accent_density_calculator(2, 0.5)
    assert isinstance(result, int), f"Expected int, got {type(result)}"

run_test("returns integer", test_adc_returns_int)

def test_adc_minimum_is_one():
    for _ in range(500):
        result = accent_density_calculator(random.choice(PROG_LENGTHS), random.random())
        assert result >= 1, f"Got {result}, expected >= 1"

run_test("never returns less than 1", test_adc_minimum_is_one)

def test_adc_arousal_zero_gives_one():
    for m in PROG_LENGTHS:
        result = accent_density_calculator(m, 0.0)
        assert result == 1, f"arousal=0 should give 1, got {result} for measures={m}"

run_test("arousal=0 always gives minimum density of 1", test_adc_arousal_zero_gives_one)

def test_adc_known_values():
    # p * b * x with b = MAX_ACCENTS_PER_MEASURE
    assert accent_density_calculator(1, 1.0) == MAX_ACCENTS_PER_MEASURE, \
        f"1 measure at arousal 1.0 should be {MAX_ACCENTS_PER_MEASURE}"
    assert accent_density_calculator(2, 0.5) == round(2 * MAX_ACCENTS_PER_MEASURE * 0.5)
    assert accent_density_calculator(4, 1.0) == round(4 * MAX_ACCENTS_PER_MEASURE * 1.0)

run_test("matches p*b*x for known inputs", test_adc_known_values)

def test_adc_monotonic_in_arousal():
    for m in PROG_LENGTHS:
        prev = accent_density_calculator(m, 0.0)
        for a in [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
            curr = accent_density_calculator(m, a)
            assert curr >= prev, \
                f"measures={m}: density not monotonic at arousal={a}: {curr} < {prev}"
            prev = curr

run_test("monotonically increases with arousal", test_adc_monotonic_in_arousal)

def test_adc_monotonic_in_measures():
    prev = accent_density_calculator(1, 0.7)
    for m in [2, 4, 8]:
        curr = accent_density_calculator(m, 0.7)
        assert curr >= prev, f"Density not monotonic: measures={m} gave {curr} < {prev}"
        prev = curr

run_test("monotonically increases with section measures", test_adc_monotonic_in_measures)


# ============================================================
# ACCENT_ARCHETYPE_CALCULATOR TESTS
# ============================================================

print("\n" + "=" * 60)
print("ACCENT_ARCHETYPE_CALCULATOR")
print("=" * 60)

def test_aac_valid_outputs():
    for _ in range(TRIALS):
        result = accent_archetype_calculator()
        assert result in VALID_ARCHETYPES, f"Got invalid archetype: '{result}'"

run_test("always returns a valid archetype", test_aac_valid_outputs)

def test_aac_roughly_uniform():
    counts = Counter()
    for _ in range(TRIALS):
        counts[accent_archetype_calculator()] += 1
    for archetype in VALID_ARCHETYPES:
        ratio = counts[archetype] / TRIALS
        assert 0.10 < ratio < 0.25, \
            f"'{archetype}' at {ratio*100:.1f}%, expected ~16.7%"
    distribution_report("all archetypes", counts, TRIALS)

run_test("roughly uniform distribution over 6 archetypes", test_aac_roughly_uniform)


# ============================================================
# CHOOSE_ACCENT_ARCHETYPE TESTS
# ============================================================

print("\n" + "=" * 60)
print("CHOOSE_ACCENT_ARCHETYPE")
print("=" * 60)

def test_caa_returns_triple():
    result = choose_accent_archetype(16)
    assert len(result) == 3, f"Expected (archetype, weights, capacity), got {result}"
    archetype, weights, capacity = result
    assert archetype in VALID_ARCHETYPES

run_test("returns (archetype, weights, capacity)", test_caa_returns_triple)

def test_caa_weights_length_matches_slots():
    for section_slots in [16, 32, 64, 128]:
        for _ in range(50):
            _, weights, _ = choose_accent_archetype(section_slots)
            assert len(weights) == section_slots, \
                f"section_slots={section_slots}: got {len(weights)} weights"

run_test("weight vector length always equals section_slots", test_caa_weights_length_matches_slots)

def test_caa_capacity_bounds():
    for _ in range(1000):
        section_slots = random.choice([16, 32, 64, 128])
        _, weights, capacity = choose_accent_archetype(section_slots)
        assert capacity == sum(1 for w in weights if w > 0), \
            "capacity must equal count of positive weights"
        assert 1 <= capacity <= section_slots, \
            f"capacity {capacity} out of [1, {section_slots}]"

run_test("capacity equals positive-weight count and is within [1, slots]", test_caa_capacity_bounds)

def test_caa_weights_nonnegative():
    for _ in range(1000):
        _, weights, _ = choose_accent_archetype(random.choice([16, 32, 64]))
        assert all(w >= 0 for w in weights), "weights must be non-negative"

run_test("all weights are non-negative", test_caa_weights_nonnegative)

def test_caa_even_and_random_full_capacity():
    # Force the two full-capacity archetypes and check their capacity.
    for archetype_target in ("even", "random"):
        found = False
        for _ in range(2000):
            archetype, weights, capacity = choose_accent_archetype(16)
            if archetype == archetype_target:
                found = True
                assert capacity == 16, \
                    f"'{archetype_target}' should offer full capacity, got {capacity}"
        assert found, f"'{archetype_target}' never chosen in 2000 draws"

run_test("'even' and 'random' offer full section capacity", test_caa_even_and_random_full_capacity)

def test_caa_alternating_half_capacity():
    for _ in range(2000):
        archetype, weights, capacity = choose_accent_archetype(16)
        if archetype == "alternating":
            assert capacity == 8, \
                f"'alternating' over 16 slots should have capacity 8, got {capacity}"

run_test("'alternating' leaves half the slots empty", test_caa_alternating_half_capacity)


# ============================================================
# APPLY_ACCENT_ARCHETYPE TESTS
# ============================================================

print("\n" + "=" * 60)
print("APPLY_ACCENT_ARCHETYPE")
print("=" * 60)

# Mirrors real caller usage: choose the shape, clamp accent count to the
# layout's capacity, then place. Returns the binary pattern and count.
def placed_accents(section_slots, density):
    archetype, weights, capacity = choose_accent_archetype(section_slots)
    n = max(1, min(density, capacity))
    return apply_accent_archetype(section_slots, n, archetype, weights), n

def test_aaa_output_length():
    for section_slots in [16, 32, 64]:
        for density in range(1, 6):
            pattern, _ = placed_accents(section_slots, density)
            assert len(pattern) == section_slots, \
                f"section_slots={section_slots}: got {len(pattern)}"

run_test("output length always equals section_slots", test_aaa_output_length)

def test_aaa_binary_output():
    for _ in range(1000):
        section_slots = random.choice([16, 32, 64])
        pattern, _ = placed_accents(section_slots, random.randint(1, 8))
        assert all(v in (0, 1) for v in pattern), "pattern must be binary"

run_test("all entries are 0 or 1", test_aaa_binary_output)

def test_aaa_exact_accent_count():
    for _ in range(1000):
        section_slots = random.choice([16, 32, 64])
        pattern, n = placed_accents(section_slots, random.randint(1, 12))
        assert sum(pattern) == n, \
            f"Expected {n} accents placed, got {sum(pattern)}"

run_test("number of lit slots equals the (clamped) accent count", test_aaa_exact_accent_count)

def test_aaa_clamp_never_crashes():
    # The chord-engine crash analog: short section + high density + a
    # capacity-limited shape (alternating). Clamp must hold.
    for _ in range(3000):
        section_slots = random.choice([16, 32])
        density = section_slots  # deliberately ask for the whole section
        pattern, n = placed_accents(section_slots, density)
        assert sum(pattern) == n, "Clamp failed: placed a different count than asked"
        assert sum(pattern) >= 1, "Should always place at least one accent"

run_test("density exceeding capacity clamps instead of crashing", test_aaa_clamp_never_crashes)

def test_aaa_density_one_single_accent():
    for _ in range(500):
        archetype, weights, capacity = choose_accent_archetype(16)
        pattern = apply_accent_archetype(16, 1, archetype, weights)
        assert sum(pattern) == 1, f"density=1 should place exactly one accent, got {sum(pattern)}"

run_test("density=1 places exactly one accent", test_aaa_density_one_single_accent)

def test_aaa_even_hits_downbeat_and_spaces_evenly():
    # 'even' places the first accent on slot 0 and spreads regularly.
    _, weights, _ = choose_accent_archetype(16)  # weights unused by 'even'
    for n in [1, 2, 4, 8]:
        pattern = apply_accent_archetype(16, n, "even", weights)
        assert sum(pattern) == n
        assert pattern[0] == 1, f"'even' should hit the downbeat, n={n}: {pattern}"
        positions = [i for i, v in enumerate(pattern) if v == 1]
        expected = [int(i * 16 / n) for i in range(n)]
        assert positions == expected, \
            f"'even' spacing off for n={n}: {positions} != {expected}"

run_test("'even' hits the downbeat and spaces accents regularly", test_aaa_even_hits_downbeat_and_spaces_evenly)


# ============================================================
# ACCENT_PATTERN_CALCULATOR TESTS
# ============================================================

print("\n" + "=" * 60)
print("ACCENT_PATTERN_CALCULATOR")
print("=" * 60)

def test_apc_correct_total_length():
    for measures in PROG_LENGTHS:
        for pattern in (["A"], ["A", "B"]):
            if measures % len(pattern) != 0:
                continue
            result = accent_pattern_calculator(measures, 0.5, pattern)
            assert len(result) == measures * SLOTS_PER_MEASURE, \
                f"measures={measures}, pattern={pattern}: got {len(result)}"

run_test("output length equals measures * 16", test_apc_correct_total_length)

def test_apc_binary_and_nonempty():
    for _ in range(500):
        measures = random.choice(PROG_LENGTHS)
        pattern = a_pattern(measures)
        result = accent_pattern_calculator(measures, random.random(), pattern)
        assert all(v in (0, 1) for v in result), "matrix must be binary"
        assert sum(result) >= 1, "matrix must contain at least one accent"

run_test("matrix is binary and has at least one accent", test_apc_binary_and_nonempty)

def test_apc_repeated_sections_identical():
    for _ in range(300):
        a = random.random()
        pattern = ["A", "A", "B", "A"]
        result = accent_pattern_calculator(4, a, pattern)
        section_len = len(result) // 4
        sec_a0 = result[0:section_len]
        sec_a1 = result[section_len:section_len * 2]
        sec_a3 = result[section_len * 3:section_len * 4]
        assert sec_a0 == sec_a1, "Section A[0] and A[1] differ"
        assert sec_a0 == sec_a3, "Section A[0] and A[3] differ"

run_test("repeated sections (AABA) are byte-for-byte identical", test_apc_repeated_sections_identical)

def test_apc_different_sections_can_differ():
    differences = 0
    for _ in range(300):
        result = accent_pattern_calculator(2, random.random(), ["A", "B"])
        section_len = len(result) // 2
        if result[:section_len] != result[section_len:]:
            differences += 1
    assert differences > 0, "A and B accent sections were always identical"

run_test("different section letters can produce different accents", test_apc_different_sections_can_differ)


# ============================================================
# CREATE_ACCENT_PATTERN TESTS
# ============================================================

print("\n" + "=" * 60)
print("CREATE_ACCENT_PATTERN")
print("=" * 60)

def test_cap_returns_list():
    result = create_accent_pattern(4, 0.5, a_pattern(4))
    assert isinstance(result, list), f"Expected list, got {type(result)}"

run_test("returns a list", test_cap_returns_list)

def test_cap_length_is_measures_times_16():
    for _ in range(300):
        measures = random.choice(PROG_LENGTHS)
        result = create_accent_pattern(measures, random.random(), a_pattern(measures))
        assert len(result) == measures * SLOTS_PER_MEASURE, \
            f"measures={measures}: got {len(result)}"

run_test("length always equals measures * 16", test_cap_length_is_measures_times_16)

def test_cap_length_in_valid_set():
    for _ in range(300):
        measures = random.choice(PROG_LENGTHS)
        result = create_accent_pattern(measures, random.random(), a_pattern(measures))
        assert len(result) in {16, 32, 64, 128}, f"Length {len(result)} unexpected"

run_test("length is 16, 32, 64, or 128", test_cap_length_in_valid_set)

def test_cap_binary():
    for _ in range(300):
        measures = random.choice(PROG_LENGTHS)
        result = create_accent_pattern(measures, random.random(), a_pattern(measures))
        assert all(v in (0, 1) for v in result), "matrix must be binary"

run_test("all entries are 0 or 1", test_cap_binary)

def test_cap_at_least_one_accent():
    for _ in range(500):
        measures = random.choice(PROG_LENGTHS)
        result = create_accent_pattern(measures, random.random(), a_pattern(measures))
        assert sum(result) >= 1, "Accent pattern has no accents at all"

run_test("always contains at least one accent", test_cap_at_least_one_accent)

def test_cap_accent_count_grows_with_arousal():
    low = sum(sum(create_accent_pattern(4, 0.2, a_pattern(4))) for _ in range(2000))
    high = sum(sum(create_accent_pattern(4, 0.9, a_pattern(4))) for _ in range(2000))
    print(f"    total accents (4 measures): arousal=0.2 → {low}, arousal=0.9 → {high}")
    assert high > low, f"Accents should grow with arousal: low={low}, high={high}"

run_test("accent count grows with arousal", test_cap_accent_count_grows_with_arousal)

def test_cap_accent_count_grows_with_measures():
    short = sum(sum(create_accent_pattern(2, 0.7, a_pattern(2))) for _ in range(2000))
    long = sum(sum(create_accent_pattern(8, 0.7, a_pattern(8))) for _ in range(2000))
    print(f"    total accents (arousal=0.7): 2 measures → {short}, 8 measures → {long}")
    assert long > short, f"Accents should grow with length: short={short}, long={long}"

run_test("accent count grows with progression length", test_cap_accent_count_grows_with_measures)

def test_cap_boundary_corners():
    for measures in PROG_LENGTHS:
        for a in (0.0, 1.0):
            result = create_accent_pattern(measures, a, a_pattern(measures))
            assert len(result) == measures * SLOTS_PER_MEASURE
            assert all(v in (0, 1) for v in result)
            assert sum(result) >= 1

run_test("arousal boundary corners don't crash and stay valid", test_cap_boundary_corners)

def test_cap_sample_outputs():
    print("    Sample accent matrices (rows = measures):")
    for measures, a in [(1, 0.3), (2, 0.6), (4, 0.9)]:
        matrix = create_accent_pattern(measures, a, a_pattern(measures))
        rows = ["".join("X" if s else "." for s in matrix[i:i + SLOTS_PER_MEASURE])
                for i in range(0, len(matrix), SLOTS_PER_MEASURE)]
        print(f"      measures={measures} arousal={a} accents={sum(matrix)}")
        for r in rows:
            print(f"        {r}")

run_test("sample accent matrices (visual)", test_cap_sample_outputs)


# ============================================================
# EDGE CASE GAUNTLET
# ============================================================

print("\n" + "=" * 60)
print("EDGE CASE GAUNTLET")
print("=" * 60)

def test_edge_arousal_zero_still_has_accent():
    for measures in PROG_LENGTHS:
        for _ in range(100):
            result = create_accent_pattern(measures, 0.0, a_pattern(measures))
            assert sum(result) >= 1, f"arousal=0, measures={measures}: no accent placed"

run_test("arousal=0 still places at least one accent per section", test_edge_arousal_zero_still_has_accent)

def test_edge_max_arousal_max_length():
    for _ in range(100):
        result = create_accent_pattern(8, 1.0, a_pattern(8))
        assert len(result) == 128
        assert all(v in (0, 1) for v in result)

run_test("8 measures at arousal=1.0 doesn't crash", test_edge_max_arousal_max_length)

def test_edge_single_measure_max_arousal():
    for _ in range(200):
        result = create_accent_pattern(1, 1.0, a_pattern(1))
        assert len(result) == 16
        # 1 measure at arousal 1.0 -> density 8, capacity-dependent
        assert 1 <= sum(result) <= 16

run_test("single measure at arousal=1.0 stays within slot bounds", test_edge_single_measure_max_arousal)

def test_edge_full_grid_no_crash():
    count = 0
    for measures in PROG_LENGTHS:
        for step in range(21):
            a = step / 20
            for _ in range(20):
                result = create_accent_pattern(measures, a, a_pattern(measures))
                assert len(result) == measures * 16
                assert all(v in (0, 1) for v in result)
                assert sum(result) >= 1
                count += 1
    print(f"    swept {count} (measures × arousal × trials) cases with no crash")

run_test("full measures × arousal grid produces valid output", test_edge_full_grid_no_crash)


# ============================================================
# CROSS-FUNCTION INTEGRATION
# ============================================================

print("\n" + "=" * 60)
print("CROSS-FUNCTION INTEGRATION")
print("=" * 60)

def test_int_pattern_tiles_evenly():
    for _ in range(500):
        measures = random.choice(PROG_LENGTHS)
        a = random.random()
        pattern = a_pattern(measures)
        total_slots = measures * SLOTS_PER_MEASURE
        assert total_slots % len(pattern) == 0, \
            f"pattern length {len(pattern)} doesn't tile {total_slots} slots evenly"

run_test("repetition pattern always tiles the slot grid evenly", test_int_pattern_tiles_evenly)

def test_int_density_within_section_capacity():
    # Each unique section's placed accent count must never exceed its slots.
    for _ in range(500):
        measures = random.choice(PROG_LENGTHS)
        a = random.random()
        pattern = a_pattern(measures)
        section_slots = (measures * SLOTS_PER_MEASURE) // len(pattern)
        matrix = accent_pattern_calculator(measures, a, pattern)
        # inspect the first section's accent count
        first_section = matrix[:section_slots]
        assert sum(first_section) <= section_slots, "section over-filled"
        assert sum(first_section) >= 1, "section under-filled"

run_test("per-section accent count stays within section capacity", test_int_density_within_section_capacity)

def test_int_full_pipeline_many_runs():
    for _ in range(500):
        measures = random.choice(PROG_LENGTHS)
        result = create_accent_pattern(measures, random.random(), a_pattern(measures))
        assert isinstance(result, list)
        assert len(result) == measures * 16
        assert all(v in (0, 1) for v in result)
        assert sum(result) >= 1

run_test("full pipeline: 500 random runs all produce valid output", test_int_full_pipeline_many_runs)


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
