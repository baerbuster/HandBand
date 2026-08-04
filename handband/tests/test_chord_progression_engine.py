"""
Chord Progression Engine Test

Comprehensive test suite for mi/chord_progression_engine.py.
Runs 10,000 trials per statistical test to verify that
distributions, invariants, and directional biases all
behave as designed.

Structure:
- calculate_prog_length_weights: exponential shape,
  valence direction, boundary values
- prog_length_calculator: valid outputs, valence bias,
  distribution shape
- chord_density_calculator: monotonicity, known values,
  floor enforcement
- calculate_cadence_weights: floor enforcement, directional
  biases, boundary values
- cadence_type_calculator: valid outputs, valence/arousal
  directional biases
- chord_duration_archetype_calculator: valid outputs,
  uniform distribution
- repetition_pattern_calculator: valid structure, length
  bounds, arousal/valence bias
- calculate_extension_weights: threshold behavior,
  seventh never decreases, ninth zero below midpoint
- apply_extensions: below-threshold no-op, valid extensions,
  strictly diatonic, statistical distribution
- build_starting_section_chords: correct length, valid
  chords, valence affinity direction, novelty pressure
- apply_cadence_type: length preserved, cadence formulas
  enforced, valence/arousal bias direction
- apply_duration_archetype: correct output length,
  exact chord count, valid entries, archetype shapes
- roman_numeral_chord_progression_calculator: correct
  total length, valid entries, repetition pattern tiling
- create_chord_progression: full pipeline smoke test,
  output structure, emote boundary values
- Edge case gauntlet: single-chord sections, arousal
  at threshold, extreme emote corners
- Cross-function integration: full pipeline invariants

Distribution reports print inline so you can eyeball
whether biases and curves are working as intended.
Tests marked "(visual)" pass as long as they don't crash.
"""

import random
import sys
import math
from collections import Counter
from handband.mi.chord_progression_engine import (
    calculate_prog_length_weights,
    prog_length_calculator,
    chord_density_calculator,
    calculate_cadence_weights,
    cadence_type_calculator,
    chord_duration_archetype_calculator,
    repetition_pattern_calculator,
    calculate_extension_weights,
    apply_extensions,
    build_starting_section_chords,
    apply_cadence_type,
    choose_duration_archetype,
    apply_duration_archetype,
    roman_numeral_chord_progression_calculator,
    create_chord_progression,
    DIATONIC_POOL,
    DIATONIC_EXTENSIONS,
    EXTENSION_AROUSAL_THRESHOLD,
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

VALID_CHORD_ROOTS = set(DIATONIC_POOL)
VALID_EXTENSIONS = set()
for root, (seventh, ninth) in DIATONIC_EXTENSIONS.items():
    VALID_EXTENSIONS.add(seventh)
    VALID_EXTENSIONS.add(ninth)
VALID_CHORD_NAMES = VALID_CHORD_ROOTS | VALID_EXTENSIONS | {"C"}

def test_plw_returns_four_weights():
    w = calculate_prog_length_weights(0.5)
    assert len(w) == 4, f"Expected 4 weights, got {len(w)}"

def test_plw_all_positive():
    for v in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        w = calculate_prog_length_weights(v)
        for i, weight in enumerate(w):
            assert weight > 0, f"valence={v}, weight[{i}]={weight} is not positive"

def test_plw_negative_valence_back_heavy():
    w = calculate_prog_length_weights(-1.0)
    assert w[3] > w[0], f"Negative valence should favor long: w[3]={w[3]}, w[0]={w[0]}"

def test_plw_positive_valence_front_heavy():
    w = calculate_prog_length_weights(1.0)
    assert w[0] > w[3], f"Positive valence should favor short: w[0]={w[0]}, w[3]={w[3]}"

def test_plw_zero_valence_uniform():
    w = calculate_prog_length_weights(0.0)
    assert all(wt == 1.0 for wt in w), f"Zero valence should give all 1s, got {w}"

def test_plw_exponential_shape():
    w_pos = calculate_prog_length_weights(1.0)
    # With valence=1, weights are 2^(0*(3-i)) = 2^(3-i): [8, 4, 2, 1]
    assert w_pos[0] > w_pos[1] > w_pos[2] > w_pos[3], \
        f"Expected descending for valence=1, got {w_pos}"

def test_plc_valid_outputs():
    valid = {1, 2, 4, 8}
    for _ in range(TRIALS):
        result = prog_length_calculator(random.uniform(-1, 1))
        assert result in valid, f"Got {result}, not in {valid}"

def test_plc_negative_valence_favors_long():
    counts = Counter()
    for _ in range(TRIALS):
        counts[prog_length_calculator(-1.0)] += 1
    long_ratio = (counts[4] + counts[8]) / TRIALS
    short_ratio = (counts[1] + counts[2]) / TRIALS
    assert long_ratio > short_ratio, \
        f"Negative valence: long={long_ratio:.2f}, short={short_ratio:.2f}"
    distribution_report("valence=-1.0", counts, TRIALS)

def test_plc_positive_valence_favors_short():
    counts = Counter()
    for _ in range(TRIALS):
        counts[prog_length_calculator(1.0)] += 1
    short_ratio = (counts[1] + counts[2]) / TRIALS
    long_ratio = (counts[4] + counts[8]) / TRIALS
    assert short_ratio > long_ratio, \
        f"Positive valence: short={short_ratio:.2f}, long={long_ratio:.2f}"
    distribution_report("valence=1.0", counts, TRIALS)

def test_plc_mid_valence_distribution():
    counts = Counter()
    for _ in range(TRIALS):
        counts[prog_length_calculator(0.0)] += 1
    distribution_report("valence=0.0", counts, TRIALS)

def test_cdc_returns_int():
    result = chord_density_calculator(4, 0.5)
    assert isinstance(result, int), f"Expected int, got {type(result)}"

def test_cdc_minimum_is_one():
    for _ in range(500):
        result = chord_density_calculator(random.choice([1, 2, 4, 8]), random.random())
        assert result >= 1, f"Got {result}, expected >= 1"

def test_cdc_monotonic_in_arousal():
    for length in [1, 2, 4, 8]:
        prev = chord_density_calculator(length, 0.0)
        for a in [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
            curr = chord_density_calculator(length, a)
            assert curr >= prev, \
                f"length={length}: density not monotonic at arousal={a}: {curr} < {prev}"
            prev = curr

def test_cdc_monotonic_in_length():
    prev = chord_density_calculator(1, 0.7)
    for L in [2, 4, 8]:
        curr = chord_density_calculator(L, 0.7)
        assert curr >= prev, \
            f"Density not monotonic: length={L} gave {curr} < {prev}"
        prev = curr

def test_cdc_arousal_zero_gives_minimum():
    for L in [1, 2, 4, 8]:
        result = chord_density_calculator(L, 0.0)
        assert result == 1, f"arousal=0 should give 1, got {result} for L={L}"

def test_cdc_density_distribution():
    counts = Counter()
    for _ in range(TRIALS):
        a = random.random()
        result = chord_density_calculator(4, a)
        counts[result] += 1
    distribution_report("L=4, arousal uniform", counts, TRIALS)

def test_ccw_returns_four_weights():
    w = calculate_cadence_weights(0.5, 0.5)
    assert len(w) == 4, f"Expected 4 weights, got {len(w)}"

def test_ccw_all_at_least_one():
    for _ in range(1000):
        v = random.uniform(-1, 1)
        a = random.random()
        w = calculate_cadence_weights(v, a)
        for i, weight in enumerate(w):
            assert weight >= 1, \
                f"v={v:.2f}, a={a:.2f}: weight[{i}]={weight} < 1"

def test_ccw_high_valence_boosts_authentic():
    w_high = calculate_cadence_weights(1.0, 0.5)
    w_low  = calculate_cadence_weights(-1.0, 0.5)
    assert w_high[0] > w_low[0], \
        f"Authentic weight: high_v={w_high[0]}, low_v={w_low[0]}"

def test_ccw_low_valence_boosts_deceptive():
    w_neg = calculate_cadence_weights(-1.0, 0.5)
    w_pos = calculate_cadence_weights(1.0, 0.5)
    assert w_neg[3] > w_pos[3], \
        f"Deceptive weight: neg_v={w_neg[3]}, pos_v={w_pos[3]}"

def test_ccw_high_arousal_boosts_half():
    w_high = calculate_cadence_weights(0.0, 1.0)
    w_low  = calculate_cadence_weights(0.0, 0.0)
    assert w_high[2] > w_low[2], \
        f"Half weight: high_a={w_high[2]}, low_a={w_low[2]}"

def test_ccw_low_arousal_boosts_plagal():
    w_low  = calculate_cadence_weights(0.0, 0.0)
    w_high = calculate_cadence_weights(0.0, 1.0)
    assert w_low[1] > w_high[1], \
        f"Plagal weight: low_a={w_low[1]}, high_a={w_high[1]}"

VALID_CADENCES = {"authentic", "plagal", "half", "deceptive"}

def test_ctc_valid_outputs():
    for _ in range(TRIALS):
        result = cadence_type_calculator(random.uniform(-1, 1), random.random())
        assert result in VALID_CADENCES, f"Got invalid cadence: '{result}'"

def test_ctc_high_valence_favors_authentic():
    counts = Counter()
    for _ in range(TRIALS):
        counts[cadence_type_calculator(1.0, 0.5)] += 1
    assert counts["authentic"] > counts["deceptive"], \
        f"High valence: authentic={counts['authentic']}, deceptive={counts['deceptive']}"
    distribution_report("valence=1.0, arousal=0.5", counts, TRIALS)

def test_ctc_low_valence_favors_deceptive():
    counts = Counter()
    for _ in range(TRIALS):
        counts[cadence_type_calculator(-1.0, 0.5)] += 1
    assert counts["deceptive"] > counts["authentic"], \
        f"Low valence: deceptive={counts['deceptive']}, authentic={counts['authentic']}"
    distribution_report("valence=-1.0, arousal=0.5", counts, TRIALS)

def test_ctc_high_arousal_favors_half():
    counts = Counter()
    for _ in range(TRIALS):
        counts[cadence_type_calculator(0.0, 1.0)] += 1
    assert counts["half"] > counts["plagal"], \
        f"High arousal: half={counts['half']}, plagal={counts['plagal']}"
    distribution_report("valence=0.0, arousal=1.0", counts, TRIALS)

def test_ctc_low_arousal_favors_plagal():
    counts = Counter()
    for _ in range(TRIALS):
        counts[cadence_type_calculator(0.0, 0.0)] += 1
    assert counts["plagal"] > counts["half"], \
        f"Low arousal: plagal={counts['plagal']}, half={counts['half']}"
    distribution_report("valence=0.0, arousal=0.0", counts, TRIALS)

VALID_ARCHETYPES = {"front", "back", "center", "alternating", "symmetrical", "random"}

def test_cdac_valid_outputs():
    for _ in range(TRIALS):
        result = chord_duration_archetype_calculator()
        assert result in VALID_ARCHETYPES, f"Got invalid archetype: '{result}'"

def test_cdac_roughly_uniform():
    counts = Counter()
    for _ in range(TRIALS):
        counts[chord_duration_archetype_calculator()] += 1
    for archetype in VALID_ARCHETYPES:
        ratio = counts[archetype] / TRIALS
        assert 0.10 < ratio < 0.25, \
            f"'{archetype}' at {ratio*100:.1f}%, expected ~16.7%"
    distribution_report("all archetypes", counts, TRIALS)

def test_rpc_returns_list():
    result = repetition_pattern_calculator(0.5, 0.5, 8)
    assert isinstance(result, list), f"Expected list, got {type(result)}"

def test_rpc_length_divides_density():
    for _ in range(500):
        density = random.choice([2, 4, 6, 8, 12, 16])
        v = random.uniform(-1, 1)
        a = random.random()
        result = repetition_pattern_calculator(v, a, density)
        assert density % len(result) == 0, \
            f"density={density}, pattern length={len(result)} — doesn't divide evenly"

def test_rpc_length_bounded():
    for _ in range(500):
        density = random.choice([2, 4, 6, 8, 16])
        result = repetition_pattern_calculator(random.uniform(-1, 1), random.random(), density)
        assert 1 <= len(result) <= 8, \
            f"Pattern length {len(result)} out of bounds [1, 8]"

def test_rpc_starts_with_A():
    for _ in range(500):
        result = repetition_pattern_calculator(0.5, 0.5, 8)
        assert result[0] == 'A', f"Pattern doesn't start with 'A': {result}"

def test_rpc_density_1_returns_single():
    for _ in range(100):
        result = repetition_pattern_calculator(0.5, 0.5, 1)
        assert result == ['A'], f"density=1 should give ['A'], got {result}"

def test_rpc_sample_outputs():
    print("    Sample patterns at different emote values:")
    for a, v in [(0.1, 0.1), (0.5, 0.5), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9)]:
        samples = [repetition_pattern_calculator(v, a, 8) for _ in range(5)]
        print(f"      a={a}, v={v}: {[''.join(s) for s in samples]}")

def test_cew_returns_three_weights():
    w = calculate_extension_weights(EXTENSION_AROUSAL_THRESHOLD)
    assert len(w) == 3, f"Expected 3 weights, got {len(w)}"

def test_cew_at_threshold_only_triads():
    w = calculate_extension_weights(EXTENSION_AROUSAL_THRESHOLD)
    triad_w, seventh_w, ninth_w = w
    assert triad_w == 1, f"triad_w at threshold should be 1, got {triad_w}"
    assert seventh_w == 0, f"seventh_w at threshold should be 0, got {seventh_w}"
    assert ninth_w == 0, f"ninth_w at threshold should be 0, got {ninth_w}"

def test_cew_at_midpoint_no_ninths():
    # t=0.5 means arousal = 0.85 + 0.5 * 0.15 = 0.925
    mid_arousal = EXTENSION_AROUSAL_THRESHOLD + 0.5 * (1 - EXTENSION_AROUSAL_THRESHOLD)
    w = calculate_extension_weights(mid_arousal)
    triad_w, seventh_w, ninth_w = w
    assert triad_w == 1, f"triad_w at midpoint should be 1, got {triad_w}"
    assert seventh_w == 1, f"seventh_w at midpoint should be 1, got {seventh_w}"
    assert abs(ninth_w) < 1e-10, f"ninth_w at midpoint should be 0, got {ninth_w}"

def test_cew_at_maximum_all_equal():
    w = calculate_extension_weights(1.0)
    triad_w, seventh_w, ninth_w = w
    assert triad_w == 1, f"triad_w at max should be 1, got {triad_w}"
    assert seventh_w == 1, f"seventh_w at max should be 1, got {seventh_w}"
    assert ninth_w == 1, f"ninth_w at max should be 1, got {ninth_w}"

def test_cew_triad_always_one():
    for a in [EXTENSION_AROUSAL_THRESHOLD, 0.875, 0.9, 0.95, 1.0]:
        w = calculate_extension_weights(a)
        assert w[0] == 1, f"triad_w should always be 1, got {w[0]} at arousal={a}"

def test_cew_seventh_never_decreases():
    prev_seventh = 0
    for a in [EXTENSION_AROUSAL_THRESHOLD + i * 0.01 for i in range(16)]:
        w = calculate_extension_weights(min(a, 1.0))
        assert w[1] >= prev_seventh - 1e-9, \
            f"seventh_w decreased at arousal={a:.3f}: {w[1]} < {prev_seventh}"
        prev_seventh = w[1]

def test_cew_ninth_zero_in_lower_half():
    for a in [EXTENSION_AROUSAL_THRESHOLD + i * 0.007 for i in range(8)]:
        w = calculate_extension_weights(min(a, 1.0))
        t = (min(a, 1.0) - EXTENSION_AROUSAL_THRESHOLD) / (1 - EXTENSION_AROUSAL_THRESHOLD)
        if t < 0.5 - 1e-9:
            assert w[2] == 0, \
                f"ninth_w should be 0 for t<0.5 (arousal={a:.3f}), got {w[2]}"

def test_cew_ninth_monotonic_in_upper_half():
    prev = 0
    for a in [0.926 + i * 0.007 for i in range(11)]:
        a = min(a, 1.0)
        w = calculate_extension_weights(a)
        assert w[2] >= prev - 1e-9, \
            f"ninth_w not monotonic at arousal={a:.3f}: {w[2]} < {prev}"
        prev = w[2]

def test_cew_print_curve():
    print("    Extension weight curve:")
    for a in [0.85, 0.875, 0.90, 0.925, 0.95, 0.975, 1.0]:
        w = calculate_extension_weights(a)
        t = (a - EXTENSION_AROUSAL_THRESHOLD) / (1 - EXTENSION_AROUSAL_THRESHOLD)
        print(f"      a={a:.3f} t={t:.2f}  triad={w[0]:.2f}  7th={w[1]:.2f}  9th={w[2]:.2f}")

def test_ae_below_threshold_no_change():
    chords = ["I", "IV", "V", "I"]
    for a in [0.0, 0.5, 0.84, EXTENSION_AROUSAL_THRESHOLD - 0.001]:
        result = apply_extensions(chords, a)
        assert result == chords, \
            f"arousal={a}: expected no change, got {result}"

def test_ae_output_length_unchanged():
    for n in range(1, 8):
        chords = random.choices(DIATONIC_POOL, k=n)
        result = apply_extensions(chords, 1.0)
        assert len(result) == n, \
            f"Length changed: input={n}, output={len(result)}"

def test_ae_all_outputs_diatonic():
    for _ in range(1000):
        chords = random.choices(DIATONIC_POOL, k=random.randint(1, 7))
        a = random.uniform(EXTENSION_AROUSAL_THRESHOLD, 1.0)
        result = apply_extensions(chords, a)
        for r, original in zip(result, chords):
            seventh, ninth = DIATONIC_EXTENSIONS[original]
            valid = {original, seventh, ninth}
            assert r in valid, \
                f"'{r}' is not a valid extension of '{original}'"

def test_ae_at_threshold_only_triads():
    chords = DIATONIC_POOL.copy()
    for _ in range(TRIALS):
        result = apply_extensions(chords, EXTENSION_AROUSAL_THRESHOLD)
        assert result == chords, \
            f"At threshold, triads should dominate. Got: {result}"

def test_ae_high_arousal_produces_extensions():
    counts = Counter()
    chord = "I"
    for _ in range(TRIALS):
        result = apply_extensions([chord], 1.0)
        counts[result[0]] += 1
    assert counts["I"] < TRIALS * 0.6, \
        f"At arousal=1.0, plain triad should not dominate: {counts['I']/TRIALS:.2f}"
    assert counts["Imaj7"] > 0, "Imaj7 never appeared at arousal=1.0"
    assert counts["Imaj9"] > 0, "Imaj9 never appeared at arousal=1.0"
    distribution_report("I chord, arousal=1.0", counts, TRIALS)

def test_ae_mid_arousal_no_ninths():
    # At t=0.5 (arousal≈0.925), ninths should have weight 0
    mid_arousal = EXTENSION_AROUSAL_THRESHOLD + 0.5 * (1 - EXTENSION_AROUSAL_THRESHOLD)
    ninth_count = 0
    for _ in range(TRIALS):
        result = apply_extensions(DIATONIC_POOL.copy(), mid_arousal)
        for r in result:
            if r in VALID_EXTENSIONS and r.endswith("9"):
                ninth_count += 1
    assert ninth_count == 0, \
        f"At t=0.5, 9ths should be impossible — got {ninth_count}"

def test_ae_all_roots_extendable():
    for chord in DIATONIC_POOL:
        result = apply_extensions([chord], 1.0)
        assert len(result) == 1
        seventh, ninth = DIATONIC_EXTENSIONS[chord]
        assert result[0] in {chord, seventh, ninth}, \
            f"'{result[0]}' not a valid extension of '{chord}'"

def test_bssc_correct_length():
    for n in range(1, 8):
        result = build_starting_section_chords(0.5, 0.5, n)
        assert len(result) == n, f"Expected {n} chords, got {len(result)}"

def test_bssc_all_diatonic():
    for _ in range(500):
        v = random.uniform(-1, 1)
        a = random.random()
        n = random.randint(1, 7)
        result = build_starting_section_chords(v, a, n)
        for chord in result:
            assert chord in VALID_CHORD_ROOTS, \
                f"'{chord}' is not in DIATONIC_POOL"

def test_bssc_length_one():
    for _ in range(200):
        result = build_starting_section_chords(random.uniform(-1,1), random.random(), 1)
        assert len(result) == 1
        assert result[0] in VALID_CHORD_ROOTS

def test_bssc_high_valence_favors_bright():
    bright = {"I", "IV", "V"}
    dark = {"vi", "vii°"}
    bright_count = 0
    dark_count = 0
    for _ in range(TRIALS):
        result = build_starting_section_chords(1.0, 0.5, 4)
        for chord in result:
            if chord in bright:
                bright_count += 1
            elif chord in dark:
                dark_count += 1
    assert bright_count > dark_count, \
        f"High valence: bright={bright_count}, dark={dark_count}"

def test_bssc_low_valence_more_dark_than_high_valence():
    dark = {"vi", "vii°", "iii"}
    dark_low = 0
    dark_high = 0
    for _ in range(TRIALS):
        for chord in build_starting_section_chords(-1.0, 0.5, 4):
            if chord in dark:
                dark_low += 1
        for chord in build_starting_section_chords(1.0, 0.5, 4):
            if chord in dark:
                dark_high += 1
    assert dark_low > dark_high, \
        f"Dark chords more common at low valence: low={dark_low}, high={dark_high}"

def test_bssc_chord_distribution():
    counts = Counter()
    for _ in range(TRIALS):
        result = build_starting_section_chords(0.0, 0.5, 4)
        for chord in result:
            counts[chord] += 1
    distribution_report("valence=0, arousal=0.5, density=4", counts, TRIALS * 4)

def test_bssc_novelty_all_seven_appear():
    seen = set()
    for _ in range(500):
        result = build_starting_section_chords(0.0, 0.5, 7)
        seen.update(result)
        if len(seen) == 7:
            break
    assert len(seen) == 7, \
        f"Not all diatonic chords appeared in 500 runs. Missing: {VALID_CHORD_ROOTS - seen}"

CADENCE_ENDINGS = {
    "authentic": ("V", "I"),
    "plagal":    ("IV", "I"),
    "deceptive": ("V", "vi"),
    "half":      ("V",),
}

def test_act_length_unchanged():
    for n in range(1, 8):
        chords = random.choices(DIATONIC_POOL, k=n)
        result = apply_cadence_type(0.5, 0.5, chords)
        assert len(result) == n, \
            f"Length changed: input={n}, output={len(result)}"

def test_act_high_valence_authentic_ending():
    two_chord_correct = 0
    for _ in range(TRIALS):
        chords = ["I", "IV", "ii", "V"]
        result = apply_cadence_type(1.0, 0.1, chords)
        if result[-2] == "V" and result[-1] == "I":
            two_chord_correct += 1
    ratio = two_chord_correct / TRIALS
    assert ratio > 0.35, \
        f"High valence, low arousal should often give authentic: only {ratio:.2f}"

def test_act_low_valence_deceptive_ending():
    deceptive_count = 0
    for _ in range(TRIALS):
        chords = ["I", "IV", "ii", "V"]
        result = apply_cadence_type(-1.0, 0.5, chords)
        if result[-2] == "V" and result[-1] == "vi":
            deceptive_count += 1
    ratio = deceptive_count / TRIALS
    assert ratio > 0.3, \
        f"Low valence should produce many deceptive cadences: only {ratio:.2f}"

def test_act_high_arousal_half_ending():
    half_count = 0
    for _ in range(TRIALS):
        chords = ["I", "IV", "ii", "V"]
        result = apply_cadence_type(0.0, 1.0, chords)
        if result[-1] == "V":
            half_count += 1
    ratio = half_count / TRIALS
    assert ratio > 0.3, \
        f"High arousal should produce many half cadences: only {ratio:.2f}"

def test_act_single_chord_section():
    counts = Counter()
    for _ in range(TRIALS):
        result = apply_cadence_type(0.5, 0.5, ["I"])
        assert len(result) == 1
        counts[result[0]] += 1
    distribution_report("single-chord cadence endings", counts, TRIALS)

def test_act_two_chord_section():
    for _ in range(500):
        chords = random.choices(DIATONIC_POOL, k=2)
        result = apply_cadence_type(random.uniform(-1,1), random.random(), chords)
        assert len(result) == 2
        assert all(c in VALID_CHORD_ROOTS for c in result)

# Mirrors real caller usage: choose the shape, clamp the chord count to
# the layout's capacity, then place. Returns the placed section.
def placed_section(section_length, density):
    weights, capacity = choose_duration_archetype(section_length)
    n = max(1, min(density, capacity))
    chords = random.choices(DIATONIC_POOL, k=n)
    return apply_duration_archetype(section_length, chords, weights), chords

def test_ada_correct_output_length():
    for section_length in [4, 8, 16, 32]:
        for density in range(1, min(section_length, 5)):
            result, _ = placed_section(section_length, density)
            assert len(result) == section_length, \
                f"section_length={section_length}, density={density}: " \
                f"got {len(result)} elements"

def test_ada_exact_chord_count():
    for _ in range(500):
        section_length = random.choice([8, 16, 32])
        density = random.randint(1, section_length // 2)
        result, chords = placed_section(section_length, density)
        non_c = [x for x in result if x != "C"]
        assert len(non_c) == len(chords), \
            f"Expected {len(chords)} chord hits, got {len(non_c)}"

def test_ada_never_crashes_when_density_exceeds_capacity():
    # The old crash: short section + high density + alternating shape.
    for _ in range(2000):
        section_length = random.choice([2, 4, 8])
        density = section_length  # deliberately ask for the whole section
        result, chords = placed_section(section_length, density)
        non_c = [x for x in result if x != "C"]
        assert len(non_c) == len(chords), \
            "Clamp failed: placed a different number of chords than generated"
        assert len(non_c) >= 1, "Should always place at least one chord"

def test_ada_all_entries_valid():
    for _ in range(500):
        result, _ = placed_section(16, random.randint(1, 4))
        for entry in result:
            assert entry in VALID_CHORD_ROOTS or entry == "C", \
                f"Invalid entry '{entry}' in output"

def test_ada_chord_values_preserved():
    for _ in range(500):
        weights, capacity = choose_duration_archetype(16)
        n = max(1, min(3, capacity))
        chords = random.choices(DIATONIC_POOL, k=n)
        result = apply_duration_archetype(16, chords, weights)
        non_c = [x for x in result if x != "C"]
        assert sorted(non_c) == sorted(chords), \
            f"Chord values changed: expected {chords}, got {non_c}"

def test_ada_density_one_exactly_one_hit():
    for _ in range(500):
        weights, _ = choose_duration_archetype(16)
        result = apply_duration_archetype(16, ["I"], weights)
        non_c = [x for x in result if x != "C"]
        assert non_c == ["I"], f"Expected exactly one 'I', got {non_c}"

def test_rncp_correct_total_length():
    for prog_length in [1, 2, 4, 8]:
        # pattern length must divide density and each section must get >= 1 chord
        for density in [2, 4, 6]:
            pattern = ["A", "B"]  # length 2 divides all densities above
            result = roman_numeral_chord_progression_calculator(
                0.5, 0.5, prog_length, pattern, density
            )
            expected = prog_length * 16
            assert len(result) == expected, \
                f"prog_length={prog_length}: expected {expected} slots, got {len(result)}"

def test_rncp_all_entries_valid():
    for _ in range(200):
        v = random.uniform(-1, 1)
        a = random.random()
        L = random.choice([1, 2, 4])
        pattern = random.choices(["A", "B"], k=2)
        density = len(pattern) * random.randint(1, 4)  # always >= 1 per section
        result = roman_numeral_chord_progression_calculator(v, a, L, pattern, density)
        for entry in result:
            assert entry in VALID_CHORD_NAMES, \
                f"Invalid entry '{entry}' in progression"

def test_rncp_repeated_sections_are_identical():
    for _ in range(200):
        v = random.uniform(-1, 1)
        a = random.random()
        pattern = ["A", "A", "B", "A"]
        result = roman_numeral_chord_progression_calculator(v, a, 4, pattern, 4)
        section_len = len(result) // 4
        sec_a0 = result[0:section_len]
        sec_a1 = result[section_len:section_len*2]
        sec_a3 = result[section_len*3:section_len*4]
        assert sec_a0 == sec_a1, \
            f"Section A[0] and A[1] differ:\n  {sec_a0}\n  {sec_a1}"
        assert sec_a0 == sec_a3, \
            f"Section A[0] and A[3] differ:\n  {sec_a0}\n  {sec_a3}"

def test_rncp_different_sections_can_differ():
    differences_found = 0
    for _ in range(200):
        v = random.uniform(-1, 1)
        a = random.random()
        pattern = ["A", "B"]
        result = roman_numeral_chord_progression_calculator(v, a, 2, pattern, 2)
        section_len = len(result) // 2
        sec_a = result[:section_len]
        sec_b = result[section_len:]
        if sec_a != sec_b:
            differences_found += 1
    assert differences_found > 0, "A and B sections were always identical — unique section logic may be broken"

def test_rncp_single_section_pattern():
    for _ in range(100):
        result = roman_numeral_chord_progression_calculator(0.5, 0.5, 1, ["A"], 1)
        assert len(result) == 16
        assert all(e in VALID_CHORD_NAMES for e in result)

def test_ccp_returns_list():
    result = create_chord_progression(0.0, 0.5)
    assert isinstance(result, list), f"Expected list, got {type(result)}"

def test_ccp_all_entries_valid():
    for _ in range(200):
        result = create_chord_progression(random.uniform(-1, 1), random.random())
        for entry in result:
            assert entry in VALID_CHORD_NAMES, \
                f"Invalid entry '{entry}' in progression"

def test_ccp_length_is_multiple_of_16():
    for _ in range(200):
        result = create_chord_progression(random.uniform(-1, 1), random.random())
        assert len(result) % 16 == 0, \
            f"Length {len(result)} is not a multiple of 16"

def test_ccp_length_in_valid_range():
    for _ in range(200):
        result = create_chord_progression(random.uniform(-1, 1), random.random())
        assert len(result) in {16, 32, 64, 128}, \
            f"Length {len(result)} not in {{16, 32, 64, 128}}"

def test_ccp_has_at_least_one_chord():
    for _ in range(500):
        result = create_chord_progression(random.uniform(-1, 1), random.random())
        non_c = [x for x in result if x != "C"]
        assert len(non_c) >= 1, "Progression has no chord onsets at all"

def test_ccp_boundary_corners():
    corners = [(-1.0, 0.0), (-1.0, 1.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0), (0.0, 1.0)]
    for v, a in corners:
        result = create_chord_progression(v, a)
        assert isinstance(result, list)
        assert len(result) % 16 == 0
        for entry in result:
            assert entry in VALID_CHORD_NAMES, \
                f"v={v}, a={a}: invalid entry '{entry}'"

def test_ccp_high_arousal_produces_extensions():
    extension_count = 0
    total = 0
    for _ in range(200):
        result = create_chord_progression(0.0, 1.0)
        for entry in result:
            if entry != "C":
                total += 1
                if entry in VALID_EXTENSIONS:
                    extension_count += 1
    assert total > 0
    ratio = extension_count / total
    assert ratio > 0.0, "High arousal never produced any extensions"
    print(f"    Extension rate at arousal=1.0: {ratio*100:.1f}%")

def test_ccp_low_arousal_no_extensions():
    for _ in range(200):
        result = create_chord_progression(0.0, 0.0)
        for entry in result:
            assert entry not in VALID_EXTENSIONS, \
                f"Low arousal should never produce extensions, got '{entry}'"

def test_ccp_sample_outputs():
    print("    Sample progressions at different emote values:")
    for v, a in [(-1.0, 0.0), (0.0, 0.5), (1.0, 1.0), (-1.0, 1.0), (1.0, 0.0)]:
        result = create_chord_progression(v, a)
        onsets = [x for x in result if x != "C"]
        print(f"      v={v:+.1f}, a={a:.1f}  len={len(result)}  chords={onsets}")

def test_edge_arousal_exactly_at_threshold():
    for _ in range(200):
        result = create_chord_progression(0.0, EXTENSION_AROUSAL_THRESHOLD)
        for entry in result:
            assert entry in VALID_CHORD_NAMES
            assert entry not in VALID_EXTENSIONS, \
                f"At exact threshold, no extensions expected, got '{entry}'"

def test_edge_arousal_just_above_threshold():
    for _ in range(200):
        result = create_chord_progression(0.0, EXTENSION_AROUSAL_THRESHOLD + 0.001)
        for entry in result:
            assert entry in VALID_CHORD_NAMES

def test_edge_all_chord_roots_survive_full_pipeline():
    # Confirm every chord root appears and can be cadenced, extended, placed
    seen_roots = set()
    for _ in range(2000):
        result = create_chord_progression(random.uniform(-1, 1), random.random())
        for entry in result:
            if entry in VALID_CHORD_ROOTS:
                seen_roots.add(entry)
        if seen_roots == VALID_CHORD_ROOTS:
            break
    assert seen_roots == VALID_CHORD_ROOTS, \
        f"These roots never appeared: {VALID_CHORD_ROOTS - seen_roots}"

def test_edge_single_measure_high_density():
    for _ in range(100):
        result = create_chord_progression(1.0, 1.0)
        assert isinstance(result, list)
        assert len(result) % 16 == 0

def test_edge_maximum_length_progression():
    result = create_chord_progression(1.0, 0.01)
    assert len(result) in {16, 32, 64, 128}

def test_edge_extensions_cover_all_roots():
    # At high arousal, confirm extended forms of all 7 roots can appear
    seen_extensions = set()
    for _ in range(5000):
        result = create_chord_progression(0.0, 1.0)
        for entry in result:
            if entry in VALID_EXTENSIONS:
                seen_extensions.add(entry)
    all_sevenths = {v[0] for v in DIATONIC_EXTENSIONS.values()}
    missing_sevenths = all_sevenths - seen_extensions
    print(f"    Seen extensions: {sorted(seen_extensions)}")
    if missing_sevenths:
        print(f"    Never saw these 7ths: {sorted(missing_sevenths)}")

def test_int_density_feeds_build():
    for _ in range(200):
        v = random.uniform(-1, 1)
        a = random.random()
        prog_len = 1
        density = chord_density_calculator(prog_len, a)
        pattern = ["A"]
        section_density = density // len(pattern)
        chords = build_starting_section_chords(v, a, max(1, section_density))
        assert all(c in VALID_CHORD_ROOTS for c in chords)

def test_int_build_feeds_cadence_feeds_extensions():
    for _ in range(500):
        v = random.uniform(-1, 1)
        a = random.random()
        chords = build_starting_section_chords(v, a, random.randint(1, 6))
        chords = apply_cadence_type(v, a, chords)
        chords = apply_extensions(chords, a)
        for chord in chords:
            assert chord in VALID_CHORD_NAMES, \
                f"Invalid chord after full section pipeline: '{chord}'"

def test_int_full_pipeline_many_runs():
    for _ in range(500):
        result = create_chord_progression(
            random.uniform(-1, 1),
            random.random()
        )
        assert isinstance(result, list)
        assert len(result) % 16 == 0
        assert all(e in VALID_CHORD_NAMES for e in result)
        assert any(e != "C" for e in result)

def test_int_progression_length_reflects_valence_trend():
    neg_lengths = []
    pos_lengths = []
    for _ in range(500):
        neg_lengths.append(len(create_chord_progression(-1.0, 0.5)))
        pos_lengths.append(len(create_chord_progression(1.0, 0.5)))
    avg_neg = sum(neg_lengths) / len(neg_lengths)
    avg_pos = sum(pos_lengths) / len(pos_lengths)
    print(f"    Avg length: valence=-1.0 → {avg_neg:.1f}, valence=1.0 → {avg_pos:.1f}")
    assert avg_neg >= avg_pos, \
        f"Negative valence should produce longer progressions on average"


def main():
    # ============================================================
    # CALCULATE_PROG_LENGTH_WEIGHTS TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CALCULATE_PROG_LENGTH_WEIGHTS")
    print("=" * 60)

    run_test("returns exactly 4 weights", test_plw_returns_four_weights)

    run_test("all weights are positive for all valence values", test_plw_all_positive)

    run_test("negative valence weights favor long progressions", test_plw_negative_valence_back_heavy)

    run_test("positive valence weights favor short progressions", test_plw_positive_valence_front_heavy)

    run_test("zero valence gives uniform weights [1,1,1,1]", test_plw_zero_valence_uniform)

    run_test("valence=1.0 produces strictly monotonic weights", test_plw_exponential_shape)


    # ============================================================
    # PROG_LENGTH_CALCULATOR TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("PROG_LENGTH_CALCULATOR")
    print("=" * 60)

    run_test("always returns 1, 2, 4, or 8", test_plc_valid_outputs)

    run_test("negative valence produces longer progressions", test_plc_negative_valence_favors_long)

    run_test("positive valence produces shorter progressions", test_plc_positive_valence_favors_short)

    run_test("mid valence distribution (visual)", test_plc_mid_valence_distribution)


    # ============================================================
    # CHORD_DENSITY_CALCULATOR TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CHORD_DENSITY_CALCULATOR")
    print("=" * 60)

    run_test("returns integer", test_cdc_returns_int)

    run_test("never returns less than 1", test_cdc_minimum_is_one)

    run_test("monotonically increases with arousal", test_cdc_monotonic_in_arousal)

    run_test("monotonically increases with prog_measure_length", test_cdc_monotonic_in_length)

    run_test("arousal=0 always gives minimum density of 1", test_cdc_arousal_zero_gives_minimum)

    run_test("density distribution over L=4 (visual)", test_cdc_density_distribution)


    # ============================================================
    # CALCULATE_CADENCE_WEIGHTS TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CALCULATE_CADENCE_WEIGHTS")
    print("=" * 60)

    run_test("returns exactly 4 weights", test_ccw_returns_four_weights)

    run_test("all weights are always >= 1 (floor enforced)", test_ccw_all_at_least_one)

    run_test("high valence boosts authentic weight", test_ccw_high_valence_boosts_authentic)

    run_test("negative valence boosts deceptive weight", test_ccw_low_valence_boosts_deceptive)

    run_test("high arousal boosts half cadence weight", test_ccw_high_arousal_boosts_half)

    run_test("low arousal boosts plagal weight", test_ccw_low_arousal_boosts_plagal)


    # ============================================================
    # CADENCE_TYPE_CALCULATOR TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CADENCE_TYPE_CALCULATOR")
    print("=" * 60)

    run_test("always returns a valid cadence type", test_ctc_valid_outputs)

    run_test("high valence favors authentic cadence", test_ctc_high_valence_favors_authentic)

    run_test("negative valence favors deceptive cadence", test_ctc_low_valence_favors_deceptive)

    run_test("high arousal favors half cadence", test_ctc_high_arousal_favors_half)

    run_test("low arousal favors plagal cadence", test_ctc_low_arousal_favors_plagal)


    # ============================================================
    # CHORD_DURATION_ARCHETYPE_CALCULATOR TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CHORD_DURATION_ARCHETYPE_CALCULATOR")
    print("=" * 60)

    run_test("always returns a valid archetype", test_cdac_valid_outputs)

    run_test("roughly uniform distribution over 6 archetypes", test_cdac_roughly_uniform)


    # ============================================================
    # REPETITION_PATTERN_CALCULATOR TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("REPETITION_PATTERN_CALCULATOR")
    print("=" * 60)

    run_test("returns a list", test_rpc_returns_list)

    run_test("pattern length always divides chord_density evenly", test_rpc_length_divides_density)

    run_test("pattern length stays within [1, 8]", test_rpc_length_bounded)

    run_test("always starts with 'A'", test_rpc_starts_with_A)

    run_test("density=1 always returns ['A']", test_rpc_density_1_returns_single)

    run_test("sample pattern outputs (visual)", test_rpc_sample_outputs)


    # ============================================================
    # CALCULATE_EXTENSION_WEIGHTS TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CALCULATE_EXTENSION_WEIGHTS")
    print("=" * 60)

    run_test("returns exactly 3 weights", test_cew_returns_three_weights)

    run_test("at threshold: only triads possible [1, 0, 0]", test_cew_at_threshold_only_triads)

    run_test("at t=0.5: triads and 7ths equal, no 9ths [1, 1, 0]", test_cew_at_midpoint_no_ninths)

    run_test("at arousal=1.0: all three equal [1, 1, 1]", test_cew_at_maximum_all_equal)

    run_test("triad weight is always 1 throughout the range", test_cew_triad_always_one)

    run_test("seventh weight never decreases as arousal rises", test_cew_seventh_never_decreases)

    run_test("ninth weight is zero for all arousal below t=0.5", test_cew_ninth_zero_in_lower_half)

    run_test("ninth weight monotonically increases in upper half", test_cew_ninth_monotonic_in_upper_half)

    run_test("extension weight curve printout (visual)", test_cew_print_curve)


    # ============================================================
    # APPLY_EXTENSIONS TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("APPLY_EXTENSIONS")
    print("=" * 60)

    run_test("below threshold returns chords unchanged", test_ae_below_threshold_no_change)

    run_test("output length always matches input length", test_ae_output_length_unchanged)

    run_test("all outputs are valid diatonic extensions of their input chord", test_ae_all_outputs_diatonic)

    run_test("at exact threshold only triads returned", test_ae_at_threshold_only_triads)

    run_test("high arousal produces 7ths and 9ths", test_ae_high_arousal_produces_extensions)

    run_test("no 9ths appear at t=0.5 (arousal=0.925)", test_ae_mid_arousal_no_ninths)

    run_test("every diatonic chord root can be extended", test_ae_all_roots_extendable)


    # ============================================================
    # BUILD_STARTING_SECTION_CHORDS TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("BUILD_STARTING_SECTION_CHORDS")
    print("=" * 60)

    run_test("returns exactly section_chord_density chords", test_bssc_correct_length)

    run_test("all chords are diatonic Roman numerals", test_bssc_all_diatonic)

    run_test("handles single-chord section", test_bssc_length_one)

    run_test("high valence favors bright chords (I, IV, V)", test_bssc_high_valence_favors_bright)

    run_test("negative valence produces more dark chords than positive valence", test_bssc_low_valence_more_dark_than_high_valence)

    run_test("chord distribution at neutral emote (visual)", test_bssc_chord_distribution)

    run_test("novelty pressure ensures all 7 diatonic chords can appear", test_bssc_novelty_all_seven_appear)


    # ============================================================
    # APPLY_CADENCE_TYPE TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("APPLY_CADENCE_TYPE")
    print("=" * 60)

    run_test("length is always preserved", test_act_length_unchanged)

    run_test("high valence, low arousal mostly gives authentic ending", test_act_high_valence_authentic_ending)

    run_test("negative valence produces deceptive cadences", test_act_low_valence_deceptive_ending)

    run_test("high arousal produces half cadences", test_act_high_arousal_half_ending)

    run_test("handles single-chord section without crash (visual)", test_act_single_chord_section)

    run_test("handles two-chord section correctly", test_act_two_chord_section)


    # ============================================================
    # APPLY_DURATION_ARCHETYPE TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("APPLY_DURATION_ARCHETYPE")
    print("=" * 60)

    run_test("output length always equals section_length", test_ada_correct_output_length)

    run_test("non-C entries equal the (clamped) chord count", test_ada_exact_chord_count)

    run_test("density exceeding capacity clamps instead of crashing", test_ada_never_crashes_when_density_exceeds_capacity)

    run_test("all entries are valid chord names or 'C'", test_ada_all_entries_valid)

    run_test("chord identities are preserved (just reordered into slots)", test_ada_chord_values_preserved)

    run_test("density=1 places exactly one chord", test_ada_density_one_exactly_one_hit)


    # ============================================================
    # ROMAN_NUMERAL_CHORD_PROGRESSION_CALCULATOR TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("ROMAN_NUMERAL_CHORD_PROGRESSION_CALCULATOR")
    print("=" * 60)

    run_test("output length always equals prog_measure_length * 16", test_rncp_correct_total_length)

    run_test("all entries are valid chord names or 'C'", test_rncp_all_entries_valid)

    run_test("repeated sections (AABA) are byte-for-byte identical", test_rncp_repeated_sections_are_identical)

    run_test("different section letters (A vs B) can produce different content", test_rncp_different_sections_can_differ)

    run_test("single-section pattern ['A'] works correctly", test_rncp_single_section_pattern)


    # ============================================================
    # CREATE_CHORD_PROGRESSION TESTS
    # ============================================================

    print("\n" + "=" * 60)
    print("CREATE_CHORD_PROGRESSION")
    print("=" * 60)

    run_test("returns a list", test_ccp_returns_list)

    run_test("all entries are valid chord names or 'C'", test_ccp_all_entries_valid)

    run_test("output length is always a multiple of 16", test_ccp_length_is_multiple_of_16)

    run_test("output length is 16, 32, 64, or 128", test_ccp_length_in_valid_range)

    run_test("always contains at least one chord onset", test_ccp_has_at_least_one_chord)

    run_test("all emote boundary corners don't crash and produce valid output", test_ccp_boundary_corners)

    run_test("high arousal produces some extended chords", test_ccp_high_arousal_produces_extensions)

    run_test("low arousal never produces extended chords", test_ccp_low_arousal_no_extensions)

    run_test("sample progressions at various emote values (visual)", test_ccp_sample_outputs)


    # ============================================================
    # EDGE CASE GAUNTLET
    # ============================================================

    print("\n" + "=" * 60)
    print("EDGE CASE GAUNTLET")
    print("=" * 60)

    run_test("arousal exactly at threshold produces no extensions", test_edge_arousal_exactly_at_threshold)

    run_test("arousal just above threshold doesn't crash", test_edge_arousal_just_above_threshold)

    run_test("all 7 diatonic roots appear somewhere across 2000 runs", test_edge_all_chord_roots_survive_full_pipeline)

    run_test("single-measure high-density progression (v=1, a=1) doesn't crash", test_edge_single_measure_high_density)

    run_test("maximum length progression (v=1, a=0) doesn't crash", test_edge_maximum_length_progression)

    run_test("extended chord forms appear across 5000 high-arousal runs (visual)", test_edge_extensions_cover_all_roots)


    # ============================================================
    # CROSS-FUNCTION INTEGRATION
    # ============================================================

    print("\n" + "=" * 60)
    print("CROSS-FUNCTION INTEGRATION")
    print("=" * 60)

    run_test("chord_density_calculator → build_starting_section_chords pipeline", test_int_density_feeds_build)

    run_test("build → cadence → extensions pipeline produces valid chords", test_int_build_feeds_cadence_feeds_extensions)

    run_test("full pipeline: 500 random emote values all produce valid output", test_int_full_pipeline_many_runs)

    run_test("negative valence produces longer progressions on average", test_int_progression_length_reflects_valence_trend)


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

    # Exit non-zero on failure, so a script or CI job running this
    # standalone actually fails instead of printing "1 failed" and
    # reporting success.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
