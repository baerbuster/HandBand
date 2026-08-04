"""
Instrument Test

Test suite for MI_Instrument, in the same style as the engine suites.
Covers the four shared functions plus the constructor:

- construction: stores personal parameters
- accent_volume: length, uniform boost on accented slots, 0 elsewhere,
  follow=0 silences, follow=1 hits MAX_ACCENT_DB
- groove_offsets: length, scales by groove_follow, sign preserved,
  follow=0 flattens, follow=1 passes through
- density_per_measure: int, floor of 1, hits max at arousal 1,
  monotonic in arousal, known values
- syncopation_weights: length 16, follow=0 gives the plain hierarchy,
  s=0.5 is flat, happy favors offbeats, sad favors the beat, strong
  slots stay positive (never forbidden), monotonic in valence
"""

import random
from MI_Instrument import (
    Instrument,
    MAX_ACCENT_DB,
    METRIC_STRENGTH,
    SLOTS_PER_MEASURE,
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


def inst(**kw):
    """Build an Instrument with defaults overridable per test."""
    params = dict(name="test", octave=4, max_octave_range=2, accent_follow=0.5,
                  groove_follow=0.5, max_density_rate=8, syncopation_follow=0.5)
    params.update(kw)
    return Instrument(**params)


# ============================================================
# CONSTRUCTION
# ============================================================

print("\n" + "=" * 60)
print("CONSTRUCTION")
print("=" * 60)

def test_stores_params():
    i = Instrument("bass", 2, 3, accent_follow=0.8, groove_follow=1.0,
                   max_density_rate=16, syncopation_follow=0.7)
    assert i.name == "bass"
    assert i.octave == 2
    assert i.max_octave_range == 3
    assert i.accent_follow == 0.8
    assert i.groove_follow == 1.0
    assert i.max_density_rate == 16
    assert i.syncopation_follow == 0.7

run_test("constructor stores personal parameters", test_stores_params)

def test_defaults():
    i = Instrument("x", 4, 2)
    assert i.accent_follow == 0.5 and i.groove_follow == 0.5
    assert i.max_density_rate == 8 and i.syncopation_follow == 0.5

run_test("constructor supplies sensible defaults", test_defaults)


# ============================================================
# ACCENT_VOLUME
# ============================================================

print("\n" + "=" * 60)
print("ACCENT_VOLUME")
print("=" * 60)

ACCENT_MAP = [1 if i in (0, 4, 10) else 0 for i in range(SLOTS_PER_MEASURE)]

def test_av_length():
    for _ in range(200):
        n = random.choice([16, 32, 64])
        m = [random.randint(0, 1) for _ in range(n)]
        assert len(inst().accent_volume(m)) == n

run_test("output length matches the accent map", test_av_length)

def test_av_boost_on_accented_only():
    i = inst(accent_follow=0.5)
    out = i.accent_volume(ACCENT_MAP)
    expected = 0.5 * MAX_ACCENT_DB
    for slot, v in zip(ACCENT_MAP, out):
        if slot:
            assert abs(v - expected) < 1e-9, f"accented slot got {v}, expected {expected}"
        else:
            assert v == 0.0, f"unaccented slot got {v}, expected 0"

run_test("accented slots boosted, others zero", test_av_boost_on_accented_only)

def test_av_uniform():
    out = inst(accent_follow=0.7).accent_volume(ACCENT_MAP)
    boosts = [v for slot, v in zip(ACCENT_MAP, out) if slot]
    assert len(set(boosts)) == 1, f"boosts not uniform: {boosts}"

run_test("every accented slot gets the SAME boost", test_av_uniform)

def test_av_follow_zero_silent():
    out = inst(accent_follow=0.0).accent_volume(ACCENT_MAP)
    assert all(v == 0.0 for v in out), "accent_follow=0 should add nothing"

run_test("accent_follow=0 adds no boost anywhere", test_av_follow_zero_silent)

def test_av_follow_one_maxes():
    out = inst(accent_follow=1.0).accent_volume(ACCENT_MAP)
    for slot, v in zip(ACCENT_MAP, out):
        if slot:
            assert abs(v - MAX_ACCENT_DB) < 1e-9

run_test("accent_follow=1 boosts accented slots by MAX_ACCENT_DB", test_av_follow_one_maxes)


# ============================================================
# GROOVE_OFFSETS
# ============================================================

print("\n" + "=" * 60)
print("GROOVE_OFFSETS")
print("=" * 60)

GROOVE = [0.0, 0.0, 0.15, 0.0, -0.1, 0.0, 0.15, 0.0,
          0.0, 0.0, 0.15, 0.0, -0.1, 0.0, 0.15, 0.0]

def test_go_length():
    assert len(inst().groove_offsets(GROOVE)) == len(GROOVE)

run_test("output length matches the groove vector", test_go_length)

def test_go_scales():
    for f in (0.0, 0.25, 0.5, 1.0):
        out = inst(groove_follow=f).groove_offsets(GROOVE)
        for g, o in zip(GROOVE, out):
            assert abs(o - g * f) < 1e-9, f"follow={f}: {g}->{o}, expected {g*f}"

run_test("each offset scaled by groove_follow", test_go_scales)

def test_go_follow_zero_flat():
    out = inst(groove_follow=0.0).groove_offsets(GROOVE)
    assert all(o == 0.0 for o in out), "groove_follow=0 should sit on the grid"

run_test("groove_follow=0 flattens to on-grid", test_go_follow_zero_flat)

def test_go_follow_one_passthrough():
    out = inst(groove_follow=1.0).groove_offsets(GROOVE)
    assert out == GROOVE, "groove_follow=1 should pass the vector through"

run_test("groove_follow=1 passes the vector through unchanged", test_go_follow_one_passthrough)

def test_go_sign_preserved():
    out = inst(groove_follow=0.5).groove_offsets(GROOVE)
    for g, o in zip(GROOVE, out):
        assert (g > 0) == (o > 0) and (g < 0) == (o < 0), "sign flipped"

run_test("push/pull sign is preserved", test_go_sign_preserved)


# ============================================================
# DENSITY_PER_MEASURE
# ============================================================

print("\n" + "=" * 60)
print("DENSITY_PER_MEASURE")
print("=" * 60)

def test_dpm_int():
    assert isinstance(inst().density_per_measure(0.5), int)

run_test("returns an int", test_dpm_int)

def test_dpm_floor_one():
    for rate in (1, 8, 16):
        assert inst(max_density_rate=rate).density_per_measure(0.0) == 1, \
            "arousal 0 must still give 1 hit/measure"

run_test("floored at 1 hit per measure (arousal 0)", test_dpm_floor_one)

def test_dpm_max_at_arousal_one():
    for rate in (4, 8, 16):
        assert inst(max_density_rate=rate).density_per_measure(1.0) == rate

run_test("arousal 1 reaches max_density_rate", test_dpm_max_at_arousal_one)

def test_dpm_monotonic():
    i = inst(max_density_rate=16)
    prev = 0
    for step in range(21):
        a = step / 20
        d = i.density_per_measure(a)
        assert d >= prev, f"density dropped at arousal {a}: {d} < {prev}"
        prev = d

run_test("non-decreasing in arousal", test_dpm_monotonic)

def test_dpm_known_values():
    i = inst(max_density_rate=8)
    assert i.density_per_measure(0.25) == 2   # round(2.0)
    assert i.density_per_measure(0.5) == 4    # round(4.0)
    assert i.density_per_measure(0.9) == 7    # round(7.2)

run_test("known values (rate 8)", test_dpm_known_values)


# ============================================================
# SYNCOPATION_WEIGHTS
# ============================================================

print("\n" + "=" * 60)
print("SYNCOPATION_WEIGHTS")
print("=" * 60)

def test_sw_length():
    assert len(inst().syncopation_weights(0.3)) == SLOTS_PER_MEASURE

run_test("returns 16 weights", test_sw_length)

def test_sw_follow_zero_is_hierarchy():
    # follow=0 -> s=0 for any valence -> plain metric hierarchy
    for v in (-1.0, 0.0, 1.0):
        out = inst(syncopation_follow=0.0).syncopation_weights(v)
        assert out == [float(x) for x in METRIC_STRENGTH] or \
               all(abs(o - s) < 1e-9 for o, s in zip(out, METRIC_STRENGTH)), \
               f"follow=0 should equal the hierarchy, got {out}"

run_test("syncopation_follow=0 yields the plain metric hierarchy", test_sw_follow_zero_is_hierarchy)

def test_sw_flat_at_half():
    # valence 0 -> signal 0.5; follow 1.0 -> s=0.5 -> flat weights
    out = inst(syncopation_follow=1.0).syncopation_weights(0.0)
    assert max(out) - min(out) < 1e-9, f"s=0.5 should be flat, got {out}"

run_test("s=0.5 gives flat (no metric preference)", test_sw_flat_at_half)

def test_sw_happy_favors_offbeats():
    # high s -> weak slot (1) should outrank strong slot (0)
    out = inst(syncopation_follow=1.0).syncopation_weights(0.9)
    assert out[1] > out[0], f"happy+following should favor offbeat: w0={out[0]} w1={out[1]}"

run_test("happy valence + following favors offbeats over the downbeat", test_sw_happy_favors_offbeats)

def test_sw_sad_favors_beat():
    # low s -> strong slot (0) outranks weak slot (1)
    out = inst(syncopation_follow=1.0).syncopation_weights(-0.9)
    assert out[0] > out[1], f"sad should favor the beat: w0={out[0]} w1={out[1]}"

run_test("sad valence favors the downbeat over offbeats", test_sw_sad_favors_beat)

def test_sw_never_forbidden():
    # strong slots must stay strictly positive across the whole range
    for _ in range(2000):
        v = random.uniform(-1, 1)
        f = random.random()
        out = inst(syncopation_follow=f).syncopation_weights(v)
        assert all(w > 0 for w in out), f"a weight hit 0 (forbidden): {out}"

run_test("no slot ever reaches zero weight (never forbidden)", test_sw_never_forbidden)

def test_sw_downbeat_monotonic_in_valence():
    # for a following instrument, the downbeat weight should fall as
    # valence (and thus syncopation) rises
    i = inst(syncopation_follow=1.0)
    prev = float("inf")
    for step in range(21):
        v = -1 + step * 0.1
        w0 = i.syncopation_weights(v)[0]
        assert w0 <= prev + 1e-9, f"downbeat weight rose at valence {v}"
        prev = w0

run_test("downbeat weight decreases as valence rises", test_sw_downbeat_monotonic_in_valence)


# ============================================================
# VOICING_INDEX
# ============================================================

print("\n" + "=" * 60)
print("VOICING_INDEX")
print("=" * 60)

def test_vi_in_range():
    # every draw lands in 0..chord_size-1 for a range of sizes/arousal
    for size in (2, 3, 4, 5):
        for _ in range(500):
            a = random.random()
            idx = inst().voicing_index(a, size)
            assert 0 <= idx < size, f"index {idx} out of range for size {size}"

run_test("index always lands in 0..chord_size-1", test_vi_in_range)

def test_vi_single_note_is_zero():
    # a single note (or fewer) has one voicing -> always index 0
    for size in (0, 1):
        for a in (0.0, 0.5, 1.0):
            assert inst().voicing_index(a, size) == 0, \
                f"chord_size {size} should always voice to 0"

run_test("single note always returns index 0", test_vi_single_note_is_zero)

def test_vi_low_arousal_favors_baseline():
    # arousal 0 should draw index 0 (the voice-led baseline) most often
    c = [0, 0, 0]
    for _ in range(6000):
        c[inst().voicing_index(0.0, 3)] += 1
    assert c[0] > c[1] > c[2], f"low arousal should favor baseline, got {c}"

run_test("low arousal favors the voice-led baseline (index 0)", test_vi_low_arousal_favors_baseline)

def test_vi_high_arousal_favors_top():
    # arousal 1 should mirror: the top index drawn most often
    c = [0, 0, 0]
    for _ in range(6000):
        c[inst().voicing_index(1.0, 3)] += 1
    assert c[2] > c[1] > c[0], f"high arousal should favor the top voicing, got {c}"

run_test("high arousal favors the most-rotated voicing (top index)", test_vi_high_arousal_favors_top)

def test_vi_never_forbidden():
    # even at the extremes every index must remain reachable
    for a in (0.0, 1.0):
        seen = set(inst().voicing_index(a, 4) for _ in range(8000))
        assert seen == {0, 1, 2, 3}, f"an index was unreachable at arousal {a}: {seen}"

run_test("every index stays reachable at the extremes (never forbidden)", test_vi_never_forbidden)


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
