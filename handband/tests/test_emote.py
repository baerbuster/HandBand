"""
EMOTE Test

Test suite for emote.py, in the same style as the engine suites. EMOTE is
two equations, so the suite is about the SHAPE of those equations rather
than a handful of values:

- transform output: exactly the two documented keys, both floats
- valence: linear passthrough, identity at every input, unaffected by
  the arousal exponent
- arousal: the power law itself — symmetric about 0 (the U), 0 at the
  center, 1 at both extremes, never negative, never above 1 inside the
  documented input range, non-decreasing in |input|, and compressive in
  the middle (the point of an exponent above 1)
- configuration: the exponent is per-instance, defaults to the module
  value, and one instance's exponent doesn't leak into another's
"""

import random
import sys

import handband.emote as emote_module
from handband.emote import EMOTE


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


# A dense sweep of the documented input range, endpoints included.
SWEEP = [-1 + i / 50 for i in range(101)]


def test_output_keys():
    out = EMOTE().transform(0.3)
    assert isinstance(out, dict), f"expected a dict, got {type(out)}"
    assert set(out) == {"valence", "arousal"}, f"unexpected keys: {sorted(out)}"

def test_output_floats():
    for v in (-1, 0, 1, -0.5, 0.5):
        out = EMOTE().transform(v)
        assert isinstance(out["valence"], (int, float)), "valence not numeric"
        assert isinstance(out["arousal"], (int, float)), "arousal not numeric"

def test_valence_is_identity():
    e = EMOTE()
    for v in SWEEP:
        assert e.transform(v)["valence"] == v, \
            f"valence changed the input: {v} -> {e.transform(v)['valence']}"

def test_valence_ignores_exponent():
    # valence is documented as linear regardless of how arousal is tuned
    for exp in (0.5, 1.0, 2.0, 4.0):
        e = EMOTE()
        e.arousal_exp = exp
        for v in (-0.7, 0.0, 0.42, 1.0):
            assert e.transform(v)["valence"] == v, \
                f"exponent {exp} leaked into valence at {v}"

def test_arousal_matches_power_law():
    e = EMOTE()
    for v in SWEEP:
        expected = abs(v) ** e.arousal_exp
        got = e.transform(v)["arousal"]
        assert abs(got - expected) < 1e-12, f"arousal at {v}: {got} != {expected}"

def test_arousal_is_symmetric():
    # the U-shape: equal and opposite inputs are equally activating
    e = EMOTE()
    for v in SWEEP:
        assert abs(e.transform(v)["arousal"] - e.transform(-v)["arousal"]) < 1e-12, \
            f"arousal not symmetric at ±{v}"

def test_arousal_zero_at_center():
    assert EMOTE().transform(0.0)["arousal"] == 0.0, "neutral input should be calm"

def test_arousal_one_at_extremes():
    e = EMOTE()
    for v in (-1.0, 1.0):
        assert abs(e.transform(v)["arousal"] - 1.0) < 1e-12, \
            f"extreme input {v} should reach full arousal"

def test_arousal_in_unit_range():
    e = EMOTE()
    for v in SWEEP:
        a = e.transform(v)["arousal"]
        assert 0.0 <= a <= 1.0, f"arousal {a} out of [0,1] at input {v}"

def test_arousal_nondecreasing_in_magnitude():
    e = EMOTE()
    prev = -1.0
    for step in range(101):
        a = e.transform(step / 100)["arousal"]
        assert a >= prev - 1e-12, f"arousal dropped at input {step / 100}"
        prev = a

def test_arousal_compresses_the_middle():
    # an exponent above 1 must pull the midrange DOWN toward calm — that's
    # the whole reason it isn't linear
    e = EMOTE()
    assert e.arousal_exp > 1, "this test assumes a compressive exponent"
    for v in (0.2, 0.5, 0.8, -0.3):
        a = e.transform(v)["arousal"]
        assert a < abs(v), f"arousal {a} at {v} is not below the linear |v|"

def test_arousal_never_negative_random():
    e = EMOTE()
    for _ in range(2000):
        v = random.uniform(-1, 1)
        assert e.transform(v)["arousal"] >= 0.0, f"negative arousal at {v}"

def test_default_exponent_from_module():
    assert EMOTE().arousal_exp == emote_module.arousal_exp, \
        "instance exponent should default to the module configurable"

def test_exponent_is_per_instance():
    a, b = EMOTE(), EMOTE()
    a.arousal_exp = 4.0
    assert b.arousal_exp == emote_module.arousal_exp, \
        "changing one instance's exponent changed another's"
    assert a.transform(0.5)["arousal"] != b.transform(0.5)["arousal"], \
        "the exponent had no effect on the transform"

def test_exponent_one_is_linear():
    e = EMOTE()
    e.arousal_exp = 1.0
    for v in SWEEP:
        assert abs(e.transform(v)["arousal"] - abs(v)) < 1e-12, \
            f"exponent 1 should give |v| exactly, failed at {v}"

def test_endpoints_fixed_under_any_exponent():
    # 0 -> 0 and ±1 -> 1 hold for every positive exponent, so tuning the
    # curve never moves the ends of the range
    for exp in (0.25, 0.5, 1.0, 2.0, 3.7):
        e = EMOTE()
        e.arousal_exp = exp
        assert e.transform(0.0)["arousal"] == 0.0, f"exp {exp} moved the center"
        assert abs(e.transform(1.0)["arousal"] - 1.0) < 1e-12, \
            f"exp {exp} moved the top end"
        assert abs(e.transform(-1.0)["arousal"] - 1.0) < 1e-12, \
            f"exp {exp} moved the bottom end"

def test_stateless_across_calls():
    # no history: the same input always gives the same output
    e = EMOTE()
    first = e.transform(0.37)
    for _ in range(50):
        e.transform(random.uniform(-1, 1))
    assert e.transform(0.37) == first, "EMOTE remembered something it shouldn't"


def main():
    # ============================================================
    # OUTPUT SHAPE
    # ============================================================

    print("\n" + "=" * 60)
    print("OUTPUT SHAPE")
    print("=" * 60)

    run_test("transform returns exactly valence and arousal", test_output_keys)

    run_test("both dimensions are numeric", test_output_floats)


    # ============================================================
    # VALENCE — LINEAR
    # ============================================================

    print("\n" + "=" * 60)
    print("VALENCE")
    print("=" * 60)

    run_test("valence passes the input through unchanged", test_valence_is_identity)

    run_test("the arousal exponent never touches valence", test_valence_ignores_exponent)


    # ============================================================
    # AROUSAL — THE POWER LAW
    # ============================================================

    print("\n" + "=" * 60)
    print("AROUSAL")
    print("=" * 60)

    run_test("arousal is |input| ** arousal_exp", test_arousal_matches_power_law)

    run_test("arousal is symmetric about 0 (the U-shape)", test_arousal_is_symmetric)

    run_test("neutral input gives zero arousal", test_arousal_zero_at_center)

    run_test("both extremes give full arousal", test_arousal_one_at_extremes)

    run_test("arousal stays inside [0, 1]", test_arousal_in_unit_range)

    run_test("arousal is non-decreasing in |input|", test_arousal_nondecreasing_in_magnitude)

    run_test("an exponent above 1 compresses the midrange", test_arousal_compresses_the_middle)

    run_test("arousal is never negative (random sweep)", test_arousal_never_negative_random)


    # ============================================================
    # CONFIGURATION
    # ============================================================

    print("\n" + "=" * 60)
    print("CONFIGURATION")
    print("=" * 60)

    run_test("the exponent defaults to the module configurable", test_default_exponent_from_module)

    run_test("the exponent is per-instance", test_exponent_is_per_instance)

    run_test("exponent 1 makes arousal exactly |input|", test_exponent_one_is_linear)

    run_test("0 and ±1 are fixed points under any exponent", test_endpoints_fixed_under_any_exponent)

    run_test("EMOTE is stateless across calls", test_stateless_across_calls)


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
