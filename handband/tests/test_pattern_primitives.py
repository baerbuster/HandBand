"""
Pattern Primitives Test

Comprehensive test suite for the five pattern primitive
functions. Runs 10,000 trials per statistical test to
verify distributions actually behave as designed.

Structure:
- weighted_choice: basic selection, weight dominance,
  edge cases with tiny/zero weights
- density_calculator: monotonicity, abs symmetry,
  known value spot checks
- selected_patterns: divisor validity, arousal bias
  direction, k sensitivity, maximum filtering
- generate_variation: length correctness, alphabet
  validity, arousal→repetition, valence→returns,
  novelty mechanism
- archetype_placer: sorting, no duplicates, weight
  bias, input immutability
- Cross-function integration: chained pipelines
  mimicking real engine usage
- Edge case gauntlet: huge partitions, highly
  composite numbers, boundary values

Distribution reports print inline so you can eyeball
whether the Gaussian curves and weight biases look
right. Tests that say "(visual)" are for your eyes —
they pass as long as they don't crash.
"""

import random
import math
from collections import Counter
from handband.mi.pattern_primitives import weighted_choice, density_calculator, selected_patterns, generate_variation, archetype_placer


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
        print(f"      {str(key):>8}: {pct:5.1f}%  {bar}")


# ============================================================
# WEIGHTED_CHOICE TESTS
# ============================================================

print("\n" + "=" * 60)
print("WEIGHTED_CHOICE")
print("=" * 60)

def test_wc_returns_from_options():
    options = ['a', 'b', 'c']
    weights = [1, 1, 1]
    for _ in range(1000):
        result = weighted_choice(options, weights)
        assert result in options, f"Got {result}, not in {options}"

run_test("always returns element from options list", test_wc_returns_from_options)

def test_wc_single_option():
    for _ in range(100):
        result = weighted_choice(['only'], [1])
        assert result == 'only'

run_test("single option always returns that option", test_wc_single_option)

def test_wc_zero_weight_never_chosen():
    counts = Counter()
    for _ in range(TRIALS):
        result = weighted_choice(['a', 'b', 'c'], [0, 1, 0])
        counts[result] += 1
    assert counts['a'] == 0, f"'a' chosen {counts['a']} times with weight 0"
    assert counts['c'] == 0, f"'c' chosen {counts['c']} times with weight 0"
    assert counts['b'] == TRIALS

run_test("zero-weight options never chosen", test_wc_zero_weight_never_chosen)

def test_wc_dominant_weight():
    counts = Counter()
    for _ in range(TRIALS):
        result = weighted_choice(['a', 'b', 'c'], [1000, 1, 1])
        counts[result] += 1
    ratio = counts['a'] / TRIALS
    assert ratio > 0.95, f"Dominant weight only chosen {ratio*100:.1f}% of time"
    distribution_report("dominant weight [1000,1,1]", counts, TRIALS)

run_test("dominant weight wins overwhelmingly", test_wc_dominant_weight)

def test_wc_equal_weights_roughly_uniform():
    counts = Counter()
    for _ in range(TRIALS):
        result = weighted_choice(['a', 'b', 'c', 'd'], [1, 1, 1, 1])
        counts[result] += 1
    for key in ['a', 'b', 'c', 'd']:
        ratio = counts[key] / TRIALS
        assert 0.15 < ratio < 0.35, f"'{key}' at {ratio*100:.1f}%, expected ~25%"
    distribution_report("equal weights", counts, TRIALS)

run_test("equal weights produce roughly uniform distribution", test_wc_equal_weights_roughly_uniform)

def test_wc_works_with_integers():
    result = weighted_choice([1, 2, 3], [1, 1, 1])
    assert isinstance(result, int)

run_test("works with integer options", test_wc_works_with_integers)

def test_wc_works_with_floats_weights():
    counts = Counter()
    for _ in range(TRIALS):
        result = weighted_choice(['a', 'b'], [0.9, 0.1])
        counts[result] += 1
    ratio = counts['a'] / TRIALS
    assert ratio > 0.8, f"'a' with weight 0.9 only chosen {ratio*100:.1f}%"

run_test("works with float weights", test_wc_works_with_floats_weights)

def test_wc_very_small_weights():
    counts = Counter()
    for _ in range(TRIALS):
        result = weighted_choice(['a', 'b'], [0.0001, 0.0001])
        counts[result] += 1
    ratio = counts['a'] / TRIALS
    assert 0.35 < ratio < 0.65, f"Tiny equal weights not uniform: {ratio*100:.1f}%"

run_test("very small but equal weights still uniform", test_wc_very_small_weights)


# ============================================================
# DENSITY_CALCULATOR TESTS
# ============================================================

print("\n" + "=" * 60)
print("DENSITY_CALCULATOR")
print("=" * 60)

def test_dc_returns_int():
    result = density_calculator(16, 0.5, 0.7)
    assert isinstance(result, int), f"Got {type(result)}, expected int"

run_test("always returns integer", test_dc_returns_int)

def test_dc_zero_emote():
    result = density_calculator(16, 0.5, 0.0)
    assert result == 1, f"emote=0 should give minimum, got {result}"

run_test("zero emote value returns minimum", test_dc_zero_emote)

def test_dc_zero_scalar():
    result = density_calculator(16, 0.0, 0.8)
    assert result == 1, f"scalar=0 should give minimum, got {result}"

run_test("zero scalar returns minimum", test_dc_zero_scalar)

def test_dc_negative_emote():
    pos = density_calculator(16, 0.5, 0.7)
    neg = density_calculator(16, 0.5, -0.7)
    assert pos == neg, f"abs not working: pos={pos}, neg={neg}"

run_test("negative emote same as positive (abs)", test_dc_negative_emote)

def test_dc_monotonic_in_emote():
    prev = density_calculator(16, 0.5, 0.0)
    for e in [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]:
        curr = density_calculator(16, 0.5, e)
        assert curr >= prev, f"Not monotonic: emote {e} gave {curr} < {prev}"
        prev = curr

run_test("monotonically increases with emote value", test_dc_monotonic_in_emote)

def test_dc_monotonic_in_length():
    prev = density_calculator(0, 0.5, 0.7)
    for L in [4, 8, 12, 16, 24, 32]:
        curr = density_calculator(L, 0.5, 0.7)
        assert curr >= prev, f"Not monotonic: length {L} gave {curr} < {prev}"
        prev = curr

run_test("monotonically increases with length", test_dc_monotonic_in_length)

def test_dc_known_values():
    assert density_calculator(16, 0.5, 0.7) == 6   # 16 * 0.5 * 0.7 = 5.6 → 6
    assert density_calculator(8, 1.0, 1.0) == 8     # 8 * 1.0 * 1.0 = 8
    assert density_calculator(12, 0.25, 0.4) == 1   # 12 * 0.25 * 0.4 = 1.2 → 1

run_test("known value spot checks", test_dc_known_values)

def test_dc_large_values():
    result = density_calculator(1024, 1.0, 1.0)
    assert result == 1024

run_test("handles large length", test_dc_large_values)


# ============================================================
# SELECTED_PATTERNS TESTS
# ============================================================

print("\n" + "=" * 60)
print("SELECTED_PATTERNS")
print("=" * 60)

def test_sp_always_returns_divisor():
    test_lengths = [4, 6, 8, 12, 16, 24, 32]
    for L in test_lengths:
        for _ in range(500):
            arousal = random.random()
            result = selected_patterns(L, arousal, k=2)
            assert L % result == 0, f"L={L}, got {result} which is not a divisor"

run_test("always returns a divisor of length", test_sp_always_returns_divisor)

def test_sp_returns_int():
    result = selected_patterns(16, 0.5, k=2)
    assert isinstance(result, int)

run_test("returns integer", test_sp_returns_int)

def test_sp_length_1():
    for _ in range(100):
        result = selected_patterns(1, random.random(), k=2)
        assert result == 1, f"Length 1 should always return 1, got {result}"

run_test("length=1 always returns 1", test_sp_length_1)

def test_sp_prime_length():
    for _ in range(500):
        result = selected_patterns(7, random.random(), k=2)
        assert result in [1, 7], f"Prime 7: got {result}, expected 1 or 7"

run_test("prime length only returns 1 or itself", test_sp_prime_length)

def test_sp_high_arousal_favors_large_divisors():
    counts = Counter()
    L = 16
    for _ in range(TRIALS):
        result = selected_patterns(L, arousal=0.95, k=2)
        counts[result] += 1
    large_ratio = (counts.get(16, 0) + counts.get(8, 0)) / TRIALS
    small_ratio = (counts.get(1, 0) + counts.get(2, 0)) / TRIALS
    assert large_ratio > small_ratio, f"High arousal: large={large_ratio:.2f}, small={small_ratio:.2f}"
    distribution_report("arousal=0.95, L=16", counts, TRIALS)

run_test("high arousal favors large divisors", test_sp_high_arousal_favors_large_divisors)

def test_sp_low_arousal_favors_small_divisors():
    counts = Counter()
    L = 16
    for _ in range(TRIALS):
        result = selected_patterns(L, arousal=0.05, k=2)
        counts[result] += 1
    small_ratio = (counts.get(1, 0) + counts.get(2, 0)) / TRIALS
    large_ratio = (counts.get(16, 0) + counts.get(8, 0)) / TRIALS
    assert small_ratio > large_ratio, f"Low arousal: small={small_ratio:.2f}, large={large_ratio:.2f}"
    distribution_report("arousal=0.05, L=16", counts, TRIALS)

run_test("low arousal favors small divisors", test_sp_low_arousal_favors_small_divisors)

def test_sp_mid_arousal_distribution():
    counts = Counter()
    L = 16
    for _ in range(TRIALS):
        result = selected_patterns(L, arousal=0.5, k=2)
        counts[result] += 1
    distribution_report("arousal=0.5, L=16", counts, TRIALS)

run_test("mid arousal distribution (visual)", test_sp_mid_arousal_distribution)

def test_sp_k_sensitivity():
    counts_tight = Counter()
    counts_wide = Counter()
    L = 24
    for _ in range(TRIALS):
        counts_tight[selected_patterns(L, 0.5, k=1)] += 1
        counts_wide[selected_patterns(L, 0.5, k=8)] += 1
    print(f"    k=1 (tight):")
    distribution_report("k=1", counts_tight, TRIALS)
    print(f"    k=8 (wide):")
    distribution_report("k=8", counts_wide, TRIALS)

run_test("k parameter controls spread (visual)", test_sp_k_sensitivity)

def test_sp_arousal_zero():
    counts = Counter()
    L = 12
    for _ in range(TRIALS):
        counts[selected_patterns(L, 0.0, k=2)] += 1
    assert counts[1] / TRIALS > 0.25, f"arousal=0 should favor 1, got {counts[1]/TRIALS:.2f}"
    distribution_report("arousal=0, L=12", counts, TRIALS)

run_test("arousal=0 strongly favors 1", test_sp_arousal_zero)

def test_sp_arousal_one():
    counts = Counter()
    L = 12
    for _ in range(TRIALS):
        counts[selected_patterns(L, 1.0, k=2)] += 1
    assert counts[12] / TRIALS > 0.3, f"arousal=1 should favor L, got {counts[12]/TRIALS:.2f}"
    distribution_report("arousal=1, L=12", counts, TRIALS)

run_test("arousal=1 strongly favors length itself", test_sp_arousal_one)

def test_sp_max_filters_divisors():
    for _ in range(1000):
        result = selected_patterns(16, random.random(), k=2, maximum=8)
        assert result <= 8, f"Got {result} with maximum=8"

run_test("maximum filters out divisors above it", test_sp_max_filters_divisors)

def test_sp_max_none_unchanged():
    random.seed(42)
    a = [selected_patterns(16, 0.5, k=2) for _ in range(100)]
    random.seed(42)
    b = [selected_patterns(16, 0.5, k=2, maximum=None) for _ in range(100)]
    assert a == b

run_test("maximum=None changes nothing", test_sp_max_none_unchanged)

def test_sp_max_redistributes_center():
    counts = Counter()
    for _ in range(TRIALS):
        result = selected_patterns(16, arousal=0.95, k=2, maximum=8)
        counts[result] += 1
    assert counts[8] / TRIALS > 0.5, f"Expected 8 to dominate, got {counts[8]/TRIALS:.2f}"
    distribution_report("arousal=0.95, max=8", counts, TRIALS)

run_test("maximum redistributes center properly", test_sp_max_redistributes_center)


# ============================================================
# GENERATE_VARIATION TESTS
# ============================================================

print("\n" + "=" * 60)
print("GENERATE_VARIATION")
print("=" * 60)

def test_gv_returns_list():
    result = generate_variation(4, 0.5, 0.5)
    assert isinstance(result, list)

run_test("returns a list", test_gv_returns_list)

def test_gv_correct_length():
    for n in range(1, 15):
        result = generate_variation(n, 0.5, 0.5)
        assert len(result) == n, f"partition={n}, got length {len(result)}"

run_test("output length equals partition_number", test_gv_correct_length)

def test_gv_partition_1():
    result = generate_variation(1, 0.5, 0.5)
    assert result == ['A']

run_test("partition=1 returns ['A']", test_gv_partition_1)

def test_gv_starts_with_A():
    for _ in range(500):
        n = random.randint(2, 10)
        result = generate_variation(n, random.random(), random.random())
        assert result[0] == 'A', f"First element is {result[0]}, expected 'A'"

run_test("always starts with 'A'", test_gv_starts_with_A)

def test_gv_valid_alphabet():
    for _ in range(500):
        n = random.randint(2, 12)
        result = generate_variation(n, random.random(), random.random())
        valid = set(chr(65 + i) for i in range(n))
        for letter in result:
            assert letter in valid, f"'{letter}' not in valid set {valid} for n={n}"

run_test("all elements within valid alphabet", test_gv_valid_alphabet)

def test_gv_high_arousal_more_repetition():
    rep_counts_high = []
    rep_counts_low = []
    n = 8
    for _ in range(TRIALS):
        high = generate_variation(n, arousal=0.95, valence=0.5)
        low = generate_variation(n, arousal=0.05, valence=0.5)
        rep_high = sum(1 for i in range(len(high)-1) if high[i] == high[i+1])
        rep_low = sum(1 for i in range(len(low)-1) if low[i] == low[i+1])
        rep_counts_high.append(rep_high)
        rep_counts_low.append(rep_low)
    avg_high = sum(rep_counts_high) / len(rep_counts_high)
    avg_low = sum(rep_counts_low) / len(rep_counts_low)
    print(f"    Avg adjacent repeats: high_arousal={avg_high:.2f}, low_arousal={avg_low:.2f}")
    assert avg_high > avg_low, f"High arousal should repeat more: {avg_high:.2f} vs {avg_low:.2f}"

run_test("high arousal produces more adjacent repetition", test_gv_high_arousal_more_repetition)

def test_gv_high_valence_more_returns():
    return_counts_high = []
    return_counts_low = []
    n = 8
    for _ in range(TRIALS):
        high = generate_variation(n, arousal=0.5, valence=0.95)
        low = generate_variation(n, arousal=0.5, valence=0.05)
        def count_returns(pat):
            returns = 0
            for i in range(2, len(pat)):
                if pat[i] != pat[i-1] and pat[i] in pat[:i-1]:
                    returns += 1
            return returns
        return_counts_high.append(count_returns(high))
        return_counts_low.append(count_returns(low))
    avg_high = sum(return_counts_high) / len(return_counts_high)
    avg_low = sum(return_counts_low) / len(return_counts_low)
    print(f"    Avg returns: high_valence={avg_high:.2f}, low_valence={avg_low:.2f}")
    assert avg_high > avg_low, f"High valence should return more: {avg_high:.2f} vs {avg_low:.2f}"

run_test("high valence produces more returning patterns", test_gv_high_valence_more_returns)

def test_gv_unique_letters_used():
    n = 6
    all_used = 0
    for _ in range(TRIALS):
        result = generate_variation(n, 0.3, 0.3)
        if len(set(result)) == n:
            all_used += 1
    ratio = all_used / TRIALS
    print(f"    All {n} letters used: {ratio*100:.1f}% of trials")
    assert all_used > 0, "Never used all letters — novelty mechanism may be broken"

run_test("novelty mechanism eventually introduces all letters", test_gv_unique_letters_used)

def test_gv_extreme_partition():
    result = generate_variation(20, 0.5, 0.5)
    assert len(result) == 20
    valid = set(chr(65 + i) for i in range(20))
    for letter in result:
        assert letter in valid

run_test("handles large partition (20)", test_gv_extreme_partition)

def test_gv_partition_2():
    counts = Counter()
    for _ in range(TRIALS):
        result = generate_variation(2, 0.5, 0.5)
        counts[tuple(result)] += 1
    distribution_report("partition=2 patterns", counts, TRIALS)

run_test("partition=2 distribution (visual)", test_gv_partition_2)

def test_gv_emote_extremes():
    for a, v in [(0.0, 0.0), (1.0, 1.0), (0.0, 1.0), (1.0, 0.0)]:
        result = generate_variation(6, a, v)
        assert len(result) == 6

run_test("all emote corners (0,0), (1,1), (0,1), (1,0) don't crash", test_gv_emote_extremes)

def test_gv_sample_outputs():
    print("    Sample patterns at different emote values:")
    for a, v in [(0.1, 0.1), (0.5, 0.5), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9)]:
        samples = [generate_variation(6, a, v) for _ in range(5)]
        print(f"      a={a}, v={v}: {[''.join(s) for s in samples]}")

run_test("sample outputs at various emote values (visual)", test_gv_sample_outputs)


# ============================================================
# ARCHETYPE_PLACER TESTS
# ============================================================

print("\n" + "=" * 60)
print("ARCHETYPE_PLACER")
print("=" * 60)

def test_ap_returns_list():
    result = archetype_placer(3, [1, 1, 1, 1, 1], [0, 1, 2, 3, 4])
    assert isinstance(result, list)

run_test("returns a list", test_ap_returns_list)

def test_ap_correct_length():
    result = archetype_placer(3, [1, 1, 1, 1, 1], [0, 1, 2, 3, 4])
    assert len(result) == 3, f"Expected 3, got {len(result)}"

run_test("output length equals N", test_ap_correct_length)

def test_ap_sorted():
    for _ in range(500):
        N = random.randint(1, 5)
        positions = list(range(8))
        weights = [1] * 8
        result = archetype_placer(N, weights, positions)
        assert result == sorted(result), f"Not sorted: {result}"

run_test("output is always sorted", test_ap_sorted)

def test_ap_no_duplicates():
    for _ in range(500):
        N = random.randint(1, 6)
        positions = list(range(8))
        weights = [1] * 8
        result = archetype_placer(N, weights, positions)
        assert len(result) == len(set(result)), f"Duplicates found: {result}"

run_test("no duplicate positions", test_ap_no_duplicates)

def test_ap_all_from_positions():
    positions = [0, 2, 4, 6, 8]
    for _ in range(500):
        result = archetype_placer(3, [1]*5, positions)
        for pos in result:
            assert pos in positions, f"{pos} not in valid positions {positions}"

run_test("all placements come from position list", test_ap_all_from_positions)

def test_ap_n_equals_positions():
    positions = [0, 1, 2, 3]
    result = archetype_placer(4, [1, 1, 1, 1], positions)
    assert result == [0, 1, 2, 3], f"Expected [0,1,2,3], got {result}"

run_test("N == len(positions) uses all positions", test_ap_n_equals_positions)

def test_ap_n_equals_1():
    counts = Counter()
    positions = [0, 1, 2, 3, 4]
    for _ in range(TRIALS):
        result = archetype_placer(1, [1]*5, positions)
        counts[result[0]] += 1
    distribution_report("N=1 uniform weights", counts, TRIALS)

run_test("N=1 placement distribution (visual)", test_ap_n_equals_1)

def test_ap_heavy_weight():
    counts = Counter()
    positions = [0, 1, 2, 3, 4]
    weights = [1, 1, 100, 1, 1]
    for _ in range(TRIALS):
        result = archetype_placer(1, weights, positions)
        counts[result[0]] += 1
    ratio = counts[2] / TRIALS
    assert ratio > 0.8, f"Heavy weight position only chosen {ratio*100:.1f}%"
    distribution_report("N=1 heavy weight on pos 2", counts, TRIALS)

run_test("heavy weight dominates placement", test_ap_heavy_weight)

def test_ap_doesnt_mutate_inputs():
    positions = [0, 1, 2, 3, 4]
    weights = [1, 2, 3, 4, 5]
    pos_copy = positions.copy()
    w_copy = weights.copy()
    archetype_placer(3, weights, positions)
    assert positions == pos_copy, f"Positions mutated: {positions} vs {pos_copy}"
    assert weights == w_copy, f"Weights mutated: {weights} vs {w_copy}"

run_test("does not mutate input lists", test_ap_doesnt_mutate_inputs)

def test_ap_placement_frequency():
    positions = [0, 1, 2, 3, 4, 5]
    weights = [5, 4, 3, 2, 1, 1]
    pos_counts = Counter()
    for _ in range(TRIALS):
        result = archetype_placer(3, weights, positions)
        for p in result:
            pos_counts[p] += 1
    distribution_report("N=3, descending weights", pos_counts, TRIALS * 3)

run_test("weighted positions appear proportionally (visual)", test_ap_placement_frequency)


# ============================================================
# CROSS-FUNCTION INTEGRATION TESTS
# ============================================================

print("\n" + "=" * 60)
print("CROSS-FUNCTION INTEGRATION")
print("=" * 60)

def test_integration_sp_into_gv():
    """selected_patterns feeds generate_variation — the core pipeline."""
    for _ in range(500):
        L = random.choice([4, 6, 8, 12, 16, 24])
        arousal = random.random()
        valence = random.random()
        partition = selected_patterns(L, arousal, k=2)
        pattern = generate_variation(partition, arousal, valence)
        assert len(pattern) == partition
        assert partition > 0

run_test("selected_patterns → generate_variation pipeline", test_integration_sp_into_gv)

def test_integration_dc_into_ap():
    """density_calculator determines how many items archetype_placer places."""
    for _ in range(500):
        L = 16
        emote = random.random()
        density = density_calculator(L, 0.3, emote)
        density = max(1, min(density, L))
        positions = list(range(L))
        weights = [1] * L
        result = archetype_placer(density, weights, positions)
        assert len(result) == density
        assert len(set(result)) == density

run_test("density_calculator → archetype_placer pipeline", test_integration_dc_into_ap)

def test_integration_full_chain():
    """Full primitive chain: partition → pattern → density → placement."""
    for _ in range(200):
        arousal = random.random()
        valence = random.random()
        L = random.choice([8, 12, 16, 24])
        
        partition = selected_patterns(L, arousal, k=2)
        pattern = generate_variation(partition, arousal, valence)
        density = density_calculator(partition, 0.5, arousal)
        density = max(1, min(density, partition))
        
        positions = list(range(partition))
        weights = [1] * partition
        placement = archetype_placer(density, weights, positions)
        
        assert len(pattern) == partition
        assert len(placement) == density
        assert all(0 <= p < partition for p in placement)

run_test("full EMOTE → partition → pattern → density → placement chain", test_integration_full_chain)


# ============================================================
# EDGE CASE GAUNTLET
# ============================================================

print("\n" + "=" * 60)
print("EDGE CASE GAUNTLET")
print("=" * 60)

def test_edge_sp_length_2():
    counts = Counter()
    for _ in range(TRIALS):
        counts[selected_patterns(2, 0.5, k=2)] += 1
    assert set(counts.keys()).issubset({1, 2})
    distribution_report("L=2, arousal=0.5", counts, TRIALS)

run_test("selected_patterns with length=2", test_edge_sp_length_2)

def test_edge_gv_partition_200():
    result = generate_variation(200, 0.001, 0.5)
    assert len(result) == 200
    valid = set(chr(65 + i) for i in range(200))
    for letter in result:
        assert letter in valid

run_test("generate_variation with partition=200 (full alphabet)", test_edge_gv_partition_200)

def test_edge_dc_max_emote():
    result = density_calculator(100, 1.0, 1.0)
    assert result == 100

run_test("density_calculator at max values", test_edge_dc_max_emote)

def test_edge_sp_highly_composite():
    counts = Counter()
    for _ in range(TRIALS):
        counts[selected_patterns(60, 0.5, k=5)] += 1
    distribution_report("L=60 (highly composite), arousal=0.5, k=5", counts, TRIALS)

run_test("selected_patterns with highly composite number (60)", test_edge_sp_highly_composite)


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