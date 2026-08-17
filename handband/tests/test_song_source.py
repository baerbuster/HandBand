"""
Song Source Test

Test suite for mi/song_source.py, in the same style as the engine
suites. SongSource generates no music of its own — it exists so that
every view sees the SAME stochastic song — so the suite is about the
two things it actually promises:

CACHING — one generation per input change. Two polls at the same input
return the identical bundle object (not merely an equal one, which is
what a view comparing 'key' relies on), a change smaller than the key's
rounding does not regenerate, a real change does, and the instruments
are persistent so the rhythm and the realized notes keep coming from the
same players.

CONSISTENCY — the bundle is one coherent song. Every per-slot stream is
the song's length and lines up slot for slot: the chord part with its
realized sequence, the bass degrees with the realized bass, every drum
element with both, and the cell-length pieces (contour, degree cell)
with the declared cell length.
"""

import random
import sys

from handband.mi.bass_instrument import bass_cell_measures
from handband.mi.chord_instrument import SLOTS_PER_MEASURE
from handband.mi.song_source import SongSource


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


BUNDLE_KEYS = {
    "key", "valence", "arousal", "form", "progression", "accents", "groove",
    "chord_part", "chord_sequence", "bass_cell_measures", "bass_rhythm",
    "bass_contour", "bass_cell", "bass_sequence", "bass_degrees",
    "drum_sequence",
}

CORNERS = [(-1.0, 1.0), (-0.5, 0.25), (0.0, 0.0), (0.5, 0.25), (1.0, 1.0)]


class Provider:
    """A settable valence/arousal source, standing in for the live input."""

    def __init__(self, valence=0.0, arousal=0.5):
        self.valence = valence
        self.arousal = arousal
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return {"valence": self.valence, "arousal": self.arousal}


def source(valence=0.0, arousal=0.5):
    provider = Provider(valence, arousal)
    return SongSource(provider), provider


def test_bundle_has_every_key():
    src, _p = source()
    bundle = src.poll()
    assert set(bundle) == BUNDLE_KEYS, \
        f"missing {BUNDLE_KEYS - set(bundle)}, extra {set(bundle) - BUNDLE_KEYS}"

def test_bundle_reports_its_input():
    for valence, arousal in CORNERS:
        src, _p = source(valence, arousal)
        bundle = src.poll()
        assert bundle["valence"] == valence and bundle["arousal"] == arousal, \
            "the bundle does not carry the input it was generated from"

def test_key_is_the_rounded_input():
    src, _p = source(0.123456, 0.654321)
    assert src.poll()["key"] == (0.123, 0.654), \
        "the key should be the input rounded to three places"

def test_poll_reads_the_provider_every_time():
    src, provider = source()
    for i in range(1, 6):
        src.poll()
        assert provider.calls == i, "poll did not read the live input"

def test_same_input_returns_the_identical_bundle():
    # identity, not equality: views compare 'key' and expect one song
    src, _p = source(0.4, 0.6)
    first = src.poll()
    for _ in range(10):
        assert src.poll() is first, "the song was regenerated for free"

def test_sub_rounding_change_does_not_regenerate():
    src, provider = source(0.400, 0.600)
    first = src.poll()
    provider.valence = 0.4001
    provider.arousal = 0.6002
    assert src.poll() is first, \
        "a change below the key's resolution regenerated the song"

def test_real_change_regenerates():
    src, provider = source(0.0, 0.5)
    first = src.poll()
    provider.valence = 0.9
    second = src.poll()
    assert second is not first, "a real input change did not regenerate"
    assert second["key"] != first["key"], "the key did not move with the input"
    assert second["valence"] == 0.9

def test_returning_to_an_old_input_still_regenerates():
    # there is no history — the cache is one deep, by design
    src, provider = source(0.0, 0.5)
    first = src.poll()
    provider.valence = 0.9
    src.poll()
    provider.valence = 0.0
    assert src.poll() is not first, "an unexpected second cache slot exists"

def test_two_views_see_one_song():
    # the module's entire reason to exist
    src, _p = source(0.3, 0.7)
    view_a = src.poll()
    view_b = src.poll()
    assert view_a is view_b, "two views polled and got different songs"
    assert view_a["progression"] is view_b["progression"]

def test_instruments_persist_across_generations():
    src, provider = source(0.0, 0.5)
    chords = src.chord_instrument
    bass = src.bass_instrument
    drums = src.drum_instrument
    for valence in (0.2, -0.6, 0.9):
        provider.valence = valence
        src.poll()
    assert src.chord_instrument is chords, "the chord player was replaced"
    assert src.bass_instrument is bass, "the bass player was replaced"
    assert src.drum_instrument is drums, "the drummer was replaced"


def bundles():
    """One bundle per emotional corner, plus a few random inputs."""
    points = list(CORNERS) + [(random.uniform(-1, 1), random.random())
                              for _ in range(5)]
    for valence, arousal in points:
        src, _p = source(valence, arousal)
        yield src.poll()


def test_song_length_is_whole_measures():
    for bundle in bundles():
        total = len(bundle["progression"])
        assert total % SLOTS_PER_MEASURE == 0, \
            f"a {total}-slot song is not whole measures"
        assert total == bundle["form"][0] * SLOTS_PER_MEASURE, \
            "the progression's length disagrees with the song form"

def test_per_slot_streams_are_song_length():
    for bundle in bundles():
        total = len(bundle["progression"])
        for name in ("accents", "chord_part", "chord_sequence", "bass_rhythm",
                     "bass_sequence", "bass_degrees"):
            assert len(bundle[name]) == total, \
                f"{name} is {len(bundle[name])} slots, song is {total}"

def test_groove_is_one_measure():
    for bundle in bundles():
        assert len(bundle["groove"]) == SLOTS_PER_MEASURE, \
            "the groove vector should be exactly one measure"

def test_cell_pieces_are_one_cell_long():
    for bundle in bundles():
        cell_measures = bundle["bass_cell_measures"]
        assert cell_measures == bass_cell_measures(bundle["progression"]), \
            "the declared cell length disagrees with the progression"
        cell_slots = cell_measures * SLOTS_PER_MEASURE
        assert len(bundle["bass_contour"]) == cell_slots, \
            "the contour is not one cell long"
        assert len(bundle["bass_cell"]) == cell_slots, \
            "the degree cell is not one cell long"

def test_chord_part_and_sequence_align():
    for bundle in bundles():
        for i, ((sym, _chord), slot) in enumerate(zip(bundle["chord_part"],
                                                      bundle["chord_sequence"])):
            assert slot["type"] == sym, \
                f"slot {i}: the realized chord stream says {slot['type']}, part says {sym}"

def test_bass_degrees_align_with_the_bass_sequence():
    for bundle in bundles():
        for i, ((sym, _degree), slot) in enumerate(zip(bundle["bass_degrees"],
                                                       bundle["bass_sequence"])):
            assert slot["type"] == sym, \
                f"slot {i}: the bass label stream and the played stream disagree"

def test_bass_degrees_label_every_strike():
    for bundle in bundles():
        for i, (sym, degree) in enumerate(bundle["bass_degrees"]):
            if sym == "H":
                assert degree is not None, f"slot {i} plays an unlabelled note"
            else:
                assert degree is None, f"slot {i} labels a {sym}"

def test_drum_streams_are_a_package():
    for bundle in bundles():
        drums = bundle["drum_sequence"]
        assert isinstance(drums, dict) and drums, "the kit came back empty"
        total = len(bundle["progression"])
        for element, stream in drums.items():
            assert isinstance(element, str), f"element key {element!r} is not a name"
            assert len(stream) == total, \
                f"the {element} stream is {len(stream)} slots, song is {total}"

def test_every_stream_shares_one_slot_format():
    # chords, bass and every drum element are read by the same sequencer,
    # so they must all emit the same per-slot shape
    for bundle in bundles():
        streams = [bundle["chord_sequence"], bundle["bass_sequence"]]
        streams += list(bundle["drum_sequence"].values())
        for stream in streams:
            for slot in stream:
                assert slot["type"] in ("H", "C", "R"), \
                    f"unknown slot type {slot['type']!r}"
                if slot["type"] == "H":
                    assert set(slot) == {"type", "notes", "accent", "timing"}, \
                        f"a strike carries {sorted(slot)}"
                    assert slot["notes"], "a strike sounded nothing"
                else:
                    assert set(slot) == {"type"}, \
                        f"a {slot['type']} carries {sorted(slot)}"

def test_accents_are_binary():
    for bundle in bundles():
        assert set(bundle["accents"]) <= {0, 1}, \
            f"the accent map is not binary: {set(bundle['accents'])}"

def test_bass_rhythm_uses_its_own_alphabet():
    for bundle in bundles():
        assert set(bundle["bass_rhythm"]) <= {"H", "C", "X"}, \
            "the bass rhythm skeleton should still use H/C/X"

def test_regeneration_stays_consistent():
    # every property above must hold again after an input change, not just
    # on the first generation
    src, provider = source(0.0, 0.5)
    src.poll()
    for valence, arousal in CORNERS:
        provider.valence, provider.arousal = valence, arousal
        bundle = src.poll()
        total = len(bundle["progression"])
        assert len(bundle["chord_sequence"]) == total
        assert len(bundle["bass_sequence"]) == total
        assert all(len(s) == total for s in bundle["drum_sequence"].values()), \
            "a drum stream came back the wrong length after regeneration"


def main():
    # ============================================================
    # THE BUNDLE
    # ============================================================

    print("\n" + "=" * 60)
    print("THE BUNDLE")
    print("=" * 60)

    run_test("every documented piece is present", test_bundle_has_every_key)

    run_test("the bundle carries the input it came from", test_bundle_reports_its_input)

    run_test("the key is the input rounded to three places", test_key_is_the_rounded_input)


    # ============================================================
    # CACHING
    # ============================================================

    print("\n" + "=" * 60)
    print("CACHING")
    print("=" * 60)

    run_test("poll reads the live input every time", test_poll_reads_the_provider_every_time)

    run_test("an unchanged input returns the identical bundle", test_same_input_returns_the_identical_bundle)

    run_test("a change below the key's resolution does not regenerate", test_sub_rounding_change_does_not_regenerate)

    run_test("a real change regenerates and moves the key", test_real_change_regenerates)

    run_test("the cache is one deep — no history", test_returning_to_an_old_input_still_regenerates)

    run_test("two views polling get one and the same song", test_two_views_see_one_song)

    run_test("the players persist across generations", test_instruments_persist_across_generations)


    # ============================================================
    # INTERNAL CONSISTENCY
    # ============================================================

    print("\n" + "=" * 60)
    print("INTERNAL CONSISTENCY")
    print("=" * 60)

    run_test("the song is whole measures, matching the form", test_song_length_is_whole_measures)

    run_test("every per-slot stream is the song's length", test_per_slot_streams_are_song_length)

    run_test("the groove vector is one measure", test_groove_is_one_measure)

    run_test("contour and degree cell are one cell long", test_cell_pieces_are_one_cell_long)

    run_test("the chord part and its realization align slot for slot", test_chord_part_and_sequence_align)

    run_test("the bass labels align with the played bass", test_bass_degrees_align_with_the_bass_sequence)

    run_test("every bass strike is labelled, and only strikes are", test_bass_degrees_label_every_strike)

    run_test("the kit is a named package of song-length streams", test_drum_streams_are_a_package)

    run_test("chords, bass and drums share one slot format", test_every_stream_shares_one_slot_format)

    run_test("the accent map is binary", test_accents_are_binary)

    run_test("the bass rhythm keeps its own H/C/X alphabet", test_bass_rhythm_uses_its_own_alphabet)

    run_test("consistency survives regeneration", test_regeneration_stays_consistent)


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
