"""
Views Test

Smoke suite for the five Tk views in handband/gui/. These are drawing
code — hundreds of canvas calls reading the song bundle — so what can go
wrong is a crash on real data: an index off the end of a stream, a None
where a label was expected, a lookup on a symbol the drawer doesn't know.
That is exactly what a smoke test catches, and it needs no eyeballs.

Each view is built on a real (hidden) Tk root and driven through the
emotional corners, plus the two structural extremes the drawers have to
survive: the shortest song (one measure) and the longest (eight).
poll_live_input is called directly rather than through mainloop, so the
redraw path runs without the test ever entering an event loop.

The suite skips itself when tkinter can't open a display — a headless CI
runner — since that is a property of the machine, not of the code.
"""

import sys

try:
    import tkinter as tk
    from handband.gui import (bass_contour, bass_pattern, chord_instrument,
                              chord_progression, emote as emote_view, score)
    from handband.mi.song_source import SongSource
    IMPORTED = True
    IMPORT_ERROR = None
except ImportError as exc:          # no tkinter in this interpreter
    IMPORTED = False
    IMPORT_ERROR = str(exc)


# ============================================================
# TEST INFRASTRUCTURE
# ============================================================

passed = 0
failed = 0
skipped = 0
errors = []

_root = None            # one hidden Tk root, shared by every test
_display = None         # None = not yet probed, False = unavailable

def display_available():
    """Whether a Tk root can actually be opened here. Probed once."""
    global _root, _display
    if _display is None:
        if not IMPORTED:
            _display = False
        else:
            try:
                _root = tk.Tk()
                _root.withdraw()          # never show a window during tests
                _display = True
            except Exception:             # TclError, and anything else Tk raises
                _display = False
    return _display


def run_test(name, fn):
    global passed, failed, skipped
    if not display_available():
        skipped += 1
        print(f"  – {name} (skipped: no display)")
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
        errors.append((name, f"CRASH: {type(e).__name__}: {e}"))
        print(f"  ✗ {name} — CRASH: {type(e).__name__}: {e}")


# The corners of the emotional space, plus the two inputs that produce
# the shortest and longest songs (progression length is valence-driven).
INPUTS = [(-1.0, 0.0), (-1.0, 1.0), (0.0, 0.5), (1.0, 0.0), (1.0, 1.0),
          (0.6, 0.35), (-0.4, 0.85)]


class Live:
    """A settable valence/arousal provider, as the real input would be."""

    def __init__(self, valence=0.0, arousal=0.5):
        self.valence = valence
        self.arousal = arousal

    def __call__(self):
        return {"valence": self.valence, "arousal": self.arousal}


def window():
    """A fresh hidden window for one view."""
    top = tk.Toplevel(_root)
    top.withdraw()
    return top


def drive(module, attribute):
    """
    Build one view and run it through every input, so both the redraw
    path (the song changed) and the skip path (it didn't) execute.
    """
    live = Live()
    source = SongSource(live)
    view = getattr(module, attribute)(window(), source)
    for valence, arousal in INPUTS:
        live.valence, live.arousal = valence, arousal
        view.poll_live_input()            # song changed -> redraws
        view.poll_live_input()            # unchanged -> takes the skip path
    return view


def test_chord_progression_view():
    view = drive(chord_progression, "ChordProgressionView")
    assert view.last_key is not None, "the view never drew a song"

def test_chord_instrument_view():
    view = drive(chord_instrument, "ChordInstrumentView")
    assert view.last_key is not None, "the view never drew a song"

def test_bass_contour_view():
    view = drive(bass_contour, "BassContourView")
    assert view.last_key is not None, "the view never drew a song"

def test_bass_pattern_view():
    view = drive(bass_pattern, "BassPatternView")
    assert view.last_key is not None, "the view never drew a song"

def test_score_view():
    view = drive(score, "ScoreView")
    assert view.last_key is not None, "the view never drew a song"

def test_emote_view():
    # the emote view reads the raw valence/arousal state, not a song
    live = Live()
    view = emote_view.EmoteView(window(), live)
    for valence, arousal in INPUTS:
        live.valence, live.arousal = valence, arousal
        view.poll()
        view.poll()

def test_attach_to_opens_a_window():
    # every view module exposes the same attach_to(parent, source) hook,
    # which is what main.py wires the toggles to
    live = Live()
    source = SongSource(live)
    for module in (chord_progression, chord_instrument, bass_contour,
                   bass_pattern, score):
        view = module.attach_to(_root, source)
        assert view is not None, f"{module.__name__}.attach_to returned nothing"
        view.master.withdraw()
    view = emote_view.attach_to(_root, live)
    assert view is not None, "gui.emote.attach_to returned nothing"

def test_views_share_one_song():
    # the reason SongSource exists: two views on one source draw the
    # same generated song, not two rolls of the dice
    live = Live(0.4, 0.6)
    source = SongSource(live)
    a = chord_instrument.ChordInstrumentView(window(), source)
    b = score.ScoreView(window(), source)
    assert a.last_key == b.last_key, \
        f"two views drew different songs: {a.last_key} vs {b.last_key}"

def song_of_length(slots, valence, step):
    """A source whose current song is exactly `slots` long. The length is
    a weighted draw, so the input is nudged until it comes up."""
    live = Live(valence, 0.5)
    source = SongSource(live)
    for _ in range(500):
        if len(source.poll()["progression"]) == slots:
            return source
        live.valence += step
    raise AssertionError(f"never drew a {slots}-slot song in 500 tries")


def test_one_measure_song_draws():
    # the shortest possible song exercises every drawer's row/column math
    # at its lower bound
    source = song_of_length(16, 1.0, -0.001)
    for module, attribute in ((chord_progression, "ChordProgressionView"),
                              (chord_instrument, "ChordInstrumentView"),
                              (bass_contour, "BassContourView"),
                              (bass_pattern, "BassPatternView"),
                              (score, "ScoreView")):
        getattr(module, attribute)(window(), source)

def test_eight_measure_song_draws():
    # and the longest, which is where a row overflow would show up
    source = song_of_length(128, -1.0, 0.001)
    for module, attribute in ((chord_progression, "ChordProgressionView"),
                              (chord_instrument, "ChordInstrumentView"),
                              (bass_contour, "BassContourView"),
                              (bass_pattern, "BassPatternView"),
                              (score, "ScoreView")):
        getattr(module, attribute)(window(), source)


def main():
    if not IMPORTED:
        print(f"\ntkinter is unavailable ({IMPORT_ERROR}) — the views cannot "
              f"be imported, so this suite is skipped.")
    elif not display_available():
        print("\nNo display available — Tk cannot open a window here, so this "
              "suite is skipped.")

    # ============================================================
    # THE VIEWS
    # ============================================================

    print("\n" + "=" * 60)
    print("THE VIEWS")
    print("=" * 60)

    run_test("the chord progression view draws at every input", test_chord_progression_view)

    run_test("the chord instrument view draws at every input", test_chord_instrument_view)

    run_test("the bass contour view draws at every input", test_bass_contour_view)

    run_test("the bass pattern view draws at every input", test_bass_pattern_view)

    run_test("the score view draws at every input", test_score_view)

    run_test("the emote view draws at every input", test_emote_view)


    # ============================================================
    # WIRING
    # ============================================================

    print("\n" + "=" * 60)
    print("WIRING")
    print("=" * 60)

    run_test("every module's attach_to opens a view", test_attach_to_opens_a_window)

    run_test("two views on one source draw the same song", test_views_share_one_song)


    # ============================================================
    # STRUCTURAL EXTREMES
    # ============================================================

    print("\n" + "=" * 60)
    print("STRUCTURAL EXTREMES")
    print("=" * 60)

    run_test("a one-measure song draws in every view", test_one_measure_song_draws)

    run_test("an eight-measure song draws in every view", test_eight_measure_song_draws)


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
        print("\nSkipped — no display available here.")
    else:
        print("\nAll tests passed.")

    if _root is not None:
        _root.destroy()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
