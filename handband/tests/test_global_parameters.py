"""
Global Parameters Test

Test suite for mi/global_parameters.py, in the same style as the engine
suites. The module is one equation and one constant, and the equation's
whole point is the CURVE, so that's what's tested:

- endpoints: valence -1 gives exactly min_bpm, +1 exactly max_bpm
- the log curve: valence 0 lands on the GEOMETRIC mean of the window,
  not the arithmetic one — the property that makes 80→100 feel like
  140→180 — and equal steps of valence multiply rather than add
- monotonic and bounded everywhere in between
- the window is the caller's: nothing is hardcoded, and a degenerate
  window (min == max) still behaves
- the key is a pitch class

It also still prints the EMOTE → BPM sweep the old smoke test printed,
so the numbers stay eyeballable.
"""

import math
import random
import sys

from handband.emote import EMOTE
from handband.mi.global_parameters import CURRENT_KEY, calculate_global_parameters

MIN_BPM = 80
MAX_BPM = 180


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


def bpm(valence, lo=MIN_BPM, hi=MAX_BPM):
    return calculate_global_parameters(valence, lo, hi)


def test_min_at_lowest_valence():
    assert abs(bpm(-1.0) - MIN_BPM) < 1e-9, "valence -1 should be the slowest tempo"

def test_max_at_highest_valence():
    assert abs(bpm(1.0) - MAX_BPM) < 1e-9, "valence +1 should be the fastest tempo"

def test_neutral_is_the_geometric_mean():
    # the whole reason for the log curve: the middle of the slider is the
    # geometric mean of the window, NOT the arithmetic mean
    middle = bpm(0.0)
    geometric = math.sqrt(MIN_BPM * MAX_BPM)
    arithmetic = (MIN_BPM + MAX_BPM) / 2
    assert abs(middle - geometric) < 1e-9, \
        f"neutral gave {middle:.2f}, expected the geometric mean {geometric:.2f}"
    assert abs(middle - arithmetic) > 1.0, \
        "neutral landed on the arithmetic mean — the curve is linear"

def test_bounded_everywhere():
    for step in range(201):
        v = -1 + step / 100
        b = bpm(v)
        assert MIN_BPM - 1e-9 <= b <= MAX_BPM + 1e-9, \
            f"valence {v} gave {b}, outside [{MIN_BPM}, {MAX_BPM}]"

def test_monotonic_in_valence():
    prev = 0.0
    for step in range(201):
        b = bpm(-1 + step / 100)
        assert b >= prev - 1e-9, "BPM fell as valence rose"
        prev = b

def test_strictly_increasing():
    for _ in range(500):
        a, b = sorted(random.uniform(-1, 1) for _ in range(2))
        if b - a > 1e-6:
            assert bpm(b) > bpm(a), f"BPM did not rise from valence {a} to {b}"

def test_equal_steps_multiply():
    # a log curve means equal valence steps are equal RATIOS, which is what
    # makes the change feel even across the slider
    ratios = []
    for step in range(10):
        a = -1 + step * 0.2
        ratios.append(bpm(a + 0.2) / bpm(a))
    for r in ratios[1:]:
        assert abs(r - ratios[0]) < 1e-9, \
            f"steps are not equal ratios: {ratios}"

def test_window_is_the_callers():
    # nothing is hardcoded: any window is honoured at both ends
    for lo, hi in ((60, 180), (100, 120), (40, 300)):
        assert abs(bpm(-1.0, lo, hi) - lo) < 1e-9, f"window [{lo},{hi}] bottom"
        assert abs(bpm(1.0, lo, hi) - hi) < 1e-9, f"window [{lo},{hi}] top"
        assert abs(bpm(0.0, lo, hi) - math.sqrt(lo * hi)) < 1e-9, \
            f"window [{lo},{hi}] middle"

def test_degenerate_window():
    for v in (-1.0, 0.0, 1.0):
        assert abs(bpm(v, 120, 120) - 120) < 1e-9, \
            "a zero-width window should give that one tempo"

def test_key_is_a_pitch_class():
    assert isinstance(CURRENT_KEY, int), "the key should be a pitch class integer"
    assert 0 <= CURRENT_KEY < 12, f"{CURRENT_KEY} is not a pitch class"

def test_emote_pipeline():
    # the real path: raw input -> EMOTE -> BPM, end to end
    emote = EMOTE()
    for input_val in (-1.0, -0.5, 0.0, 0.5, 1.0):
        result = emote.transform(input_val)
        b = bpm(result['valence'])
        assert MIN_BPM - 1e-9 <= b <= MAX_BPM + 1e-9, \
            f"input {input_val} produced {b} BPM"
    assert bpm(emote.transform(1.0)['valence']) > bpm(emote.transform(-1.0)['valence']), \
        "happy should be faster than sad through the full pipeline"


def main():
    # ============================================================
    # THE BPM CURVE
    # ============================================================

    print("\n" + "=" * 60)
    print("THE BPM CURVE")
    print("=" * 60)

    run_test("valence -1 gives the minimum BPM", test_min_at_lowest_valence)

    run_test("valence +1 gives the maximum BPM", test_max_at_highest_valence)

    run_test("neutral lands on the geometric mean, not the arithmetic one", test_neutral_is_the_geometric_mean)

    run_test("BPM stays inside the window everywhere", test_bounded_everywhere)

    run_test("BPM never falls as valence rises", test_monotonic_in_valence)

    run_test("BPM strictly rises with valence", test_strictly_increasing)

    run_test("equal valence steps are equal tempo ratios", test_equal_steps_multiply)


    # ============================================================
    # CONFIGURATION
    # ============================================================

    print("\n" + "=" * 60)
    print("CONFIGURATION")
    print("=" * 60)

    run_test("the BPM window belongs to the caller", test_window_is_the_callers)

    run_test("a zero-width window still works", test_degenerate_window)

    run_test("the key is a pitch class", test_key_is_a_pitch_class)


    # ============================================================
    # END TO END
    # ============================================================

    print("\n" + "=" * 60)
    print("END TO END")
    print("=" * 60)

    run_test("input → EMOTE → BPM stays in range and tracks valence", test_emote_pipeline)


    # ============================================================
    # EYEBALL SWEEP
    # ============================================================

    print("\n" + "=" * 60)
    print("EYEBALL SWEEP (input → valence/arousal → BPM)")
    print("=" * 60)

    emote = EMOTE()
    for input_val in (-1.0, -0.5, 0.0, 0.5, 1.0):
        result = emote.transform(input_val)
        print(f"  Input: {input_val:+.1f} → V: {result['valence']:+.2f}, "
              f"A: {result['arousal']:.2f} → BPM: {bpm(result['valence']):.1f}")


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
