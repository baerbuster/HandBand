"""
Score View Test

Test suite for the parts of gui/score.py that are pure computation: the
note speller, the groove readout, and the two functions that turn a song
bundle into draw records. Everything else in the GUI layer is Tk widget
work that needs a display, so it is deliberately out of scope here — but
these three are where a wrong answer would be silently WRONG on screen
rather than obviously broken, which is exactly what deserves a test.

- _note_name: MIDI number to the name a musician reads, including the
  octave numbering (60 = C4) and the accidental spelling
- _groove_feel: the one-word read of an instrument's timing — on grid,
  pushed (ahead), or laid back (behind) — plus its peak displacement
- _lane_records: one record per slot for both lanes, hits carrying the
  chord symbol / the mode-aware degree label and its note name, and
  everything else blank
- _drum_streams: the kit ordered cymbals-above-snare-above-kick, with
  unknown elements appended rather than dropped

The two record builders are called unbound, with no widget, because
neither touches the view — which is itself worth pinning down.
"""

import sys

try:
    from handband.gui.score import (DRUM_DISPLAY_ORDER, NOTE_NAMES, ScoreView,
                                    _groove_feel, _note_name)
    from handband.mi.song_source import SongSource
    TKINTER = True
except ImportError as exc:          # no tkinter in this interpreter
    TKINTER = False
    REASON = str(exc)


# ============================================================
# TEST INFRASTRUCTURE
# ============================================================

passed = 0
failed = 0
skipped = 0
errors = []

def run_test(name, fn):
    global passed, failed, skipped
    if not TKINTER:
        skipped += 1
        print(f"  – {name} (skipped: no tkinter)")
        return
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


def song_bundle(valence=0.3, arousal=0.6):
    return SongSource(lambda: {"valence": valence, "arousal": arousal}).poll()


def test_note_name_middle_c():
    assert _note_name(60) == "C4", "60 should be C4"

def test_note_name_octaves():
    for octave in range(-1, 9):
        midi = 12 * (octave + 1)
        assert _note_name(midi) == f"C{octave}", \
            f"MIDI {midi} should be C{octave}"

def test_note_name_accidentals():
    assert _note_name(61) == "C#4"
    assert _note_name(70) == "A#4"
    assert _note_name(71) == "B4"

def test_note_name_wraps_at_the_octave():
    for midi in range(0, 128):
        name = _note_name(midi)
        pitch = NOTE_NAMES[midi % 12]
        assert name.startswith(pitch), \
            f"{midi} spelled {name}, expected the pitch class {pitch}"
        assert name[len(pitch):] == str(midi // 12 - 1), \
            f"{midi} spelled {name}, expected octave {midi // 12 - 1}"

def test_groove_feel_on_grid():
    assert _groove_feel([]) == "on grid"
    assert _groove_feel([0.0, 0.0, 0.0]) == "on grid"

def test_groove_feel_pushed():
    out = _groove_feel([-0.12, 0.0, -0.05])
    assert out.startswith("pushed"), f"negative offsets should push: {out}"

def test_groove_feel_laid_back():
    out = _groove_feel([0.12, 0.0, 0.05])
    assert out.startswith("laid back"), f"positive offsets should lay back: {out}"

def test_groove_feel_reports_the_peak():
    assert _groove_feel([0.05, 0.12, 0.0]) == "laid back ≤0.12"
    assert _groove_feel([-0.05, -0.12]) == "pushed ≤0.12"

def test_lane_records_one_per_slot():
    song = song_bundle()
    chord, bass = ScoreView._lane_records(None, song)
    total = len(song["progression"])
    assert len(chord) == total and len(bass) == total, \
        "the lanes are not the song's length"

def test_lane_records_track_the_streams():
    song = song_bundle()
    chord, bass = ScoreView._lane_records(None, song)
    for i in range(len(chord)):
        assert chord[i]["type"] == song["chord_part"][i][0], \
            f"chord lane slot {i} disagrees with the part"
        assert bass[i]["type"] == song["bass_sequence"][i]["type"], \
            f"bass lane slot {i} disagrees with the played bass"

def test_lane_records_only_hits_are_labelled():
    song = song_bundle()
    for lane in ScoreView._lane_records(None, song):
        for i, rec in enumerate(lane):
            if rec["type"] == "H":
                assert rec["main"] is not None, f"slot {i} is an unlabelled hit"
            else:
                assert rec["main"] is None and rec["sub"] is None, \
                    f"slot {i} is a {rec['type']} but carries a label"
                assert rec["accent"] == 0.0 and rec["timing"] == 0.0, \
                    f"slot {i} is a {rec['type']} but carries performance data"

def test_lane_records_chord_labels_are_the_chords():
    song = song_bundle()
    chord, _bass = ScoreView._lane_records(None, song)
    for i, rec in enumerate(chord):
        if rec["type"] == "H":
            assert rec["main"] == song["chord_part"][i][1], \
                f"slot {i} labelled the wrong chord"

def test_lane_records_bass_labels_carry_degree_and_note():
    song = song_bundle()
    _chord, bass = ScoreView._lane_records(None, song)
    for i, rec in enumerate(bass):
        if rec["type"] == "H":
            assert isinstance(rec["main"], str) and rec["main"], \
                f"slot {i} has no degree label"
            assert rec["sub"] == _note_name(song["bass_sequence"][i]["notes"][0]), \
                f"slot {i} names the wrong note"

def test_lane_records_copy_the_performance_data():
    song = song_bundle()
    chord, bass = ScoreView._lane_records(None, song)
    for i, rec in enumerate(chord):
        if rec["type"] == "H":
            assert rec["accent"] == song["chord_sequence"][i]["accent"]
            assert rec["timing"] == song["chord_sequence"][i]["timing"]
    for i, rec in enumerate(bass):
        if rec["type"] == "H":
            assert rec["accent"] == song["bass_sequence"][i]["accent"]
            assert rec["timing"] == song["bass_sequence"][i]["timing"]

def test_drum_streams_keep_every_element():
    song = song_bundle()
    ordered = ScoreView._drum_streams(None, song)
    assert {k for k, _s in ordered} == set(song["drum_sequence"]), \
        "an element was dropped or invented"
    assert len(ordered) == len(song["drum_sequence"]), "an element was duplicated"

def test_drum_streams_are_ordered_top_down():
    song = song_bundle()
    ordered = [k for k, _s in ScoreView._drum_streams(None, song)]
    known = [k for k in ordered if k in DRUM_DISPLAY_ORDER]
    expected = [k for k in DRUM_DISPLAY_ORDER if k in known]
    assert known == expected, \
        f"the kit is out of order: {known}, expected {expected}"

def test_drum_streams_append_unknown_elements():
    song = dict(song_bundle())
    song["drum_sequence"] = dict(song["drum_sequence"])
    song["drum_sequence"]["cowbell"] = [{"type": "R"}] * len(song["progression"])
    ordered = [k for k, _s in ScoreView._drum_streams(None, song)]
    assert ordered[-1] == "cowbell", \
        f"an unrecognized element should be appended, got {ordered}"

def test_drum_streams_pass_the_streams_through():
    song = song_bundle()
    for element, stream in ScoreView._drum_streams(None, song):
        assert stream is song["drum_sequence"][element], \
            f"the {element} stream was copied or altered"


def main():
    if not TKINTER:
        print(f"\ntkinter is unavailable ({REASON}) — the score view's helpers "
              f"cannot be imported, so this suite is skipped.")

    # ============================================================
    # NOTE NAMES
    # ============================================================

    print("\n" + "=" * 60)
    print("NOTE NAMES")
    print("=" * 60)

    run_test("60 is middle C", test_note_name_middle_c)

    run_test("every C names its own octave", test_note_name_octaves)

    run_test("accidentals are spelled sharp", test_note_name_accidentals)

    run_test("the spelling follows the pitch class", test_note_name_wraps_at_the_octave)


    # ============================================================
    # GROOVE READOUT
    # ============================================================

    print("\n" + "=" * 60)
    print("GROOVE READOUT")
    print("=" * 60)

    run_test("no displacement reads 'on grid'", test_groove_feel_on_grid)

    run_test("negative offsets read as pushed", test_groove_feel_pushed)

    run_test("positive offsets read as laid back", test_groove_feel_laid_back)

    run_test("the peak displacement is reported", test_groove_feel_reports_the_peak)


    # ============================================================
    # LANE RECORDS
    # ============================================================

    print("\n" + "=" * 60)
    print("LANE RECORDS")
    print("=" * 60)

    run_test("one record per slot in both lanes", test_lane_records_one_per_slot)

    run_test("each lane tracks its own stream", test_lane_records_track_the_streams)

    run_test("only hits are labelled or carry performance data", test_lane_records_only_hits_are_labelled)

    run_test("the chord lane labels the chord that was struck", test_lane_records_chord_labels_are_the_chords)

    run_test("the bass lane carries a degree label and a note name", test_lane_records_bass_labels_carry_degree_and_note)

    run_test("accent and timing are copied from the played streams", test_lane_records_copy_the_performance_data)


    # ============================================================
    # DRUM LANE
    # ============================================================

    print("\n" + "=" * 60)
    print("DRUM LANE")
    print("=" * 60)

    run_test("every element in the package gets a row", test_drum_streams_keep_every_element)

    run_test("cymbals sit above snare above kick", test_drum_streams_are_ordered_top_down)

    run_test("an unrecognized element is appended, not dropped", test_drum_streams_append_unknown_elements)

    run_test("the streams themselves are passed through untouched", test_drum_streams_pass_the_streams_through)


    # ============================================================
    # SUMMARY
    # ============================================================

    print("\n" + "=" * 60)
    total = passed + failed + skipped
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped out of {total} tests")
    print("=" * 60)

    if errors:
        print("\nFAILURES:")
        for name, msg in errors:
            print(f"  ✗ {name}: {msg}")
    elif skipped:
        print("\nSkipped — tkinter is not available here.")
    else:
        print("\nAll tests passed.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
