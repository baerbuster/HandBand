# Legacy — Programmable Song (2025)

**Archived. Not maintained. Does not build. Superseded by the current system in `handband/`.**

This is the prototype HandBand grew out of, developed April–October 2025.
It is kept because the current system's ideas came from here, and because
the history is worth reading — but it is not part of the working product
and should not be judged as current code.

## What it was

A realtime generative song engine: a Python sequencer driving a C++
synthesis library through `ctypes`, with per-instrument sample playback,
a filter and effects chain, and drum/bass patterns that responded to a
"happy ↔ sad" control. It ran, it made music, and it got progressively
less maintainable as it grew — `programmable_song.py` ends at 199 KB in
a single file.

That ceiling is why the current system exists. The current system separates
emotional mapping (EMOTE) from musical decisions (the Musical Intelligence
instruments) from sound, which is precisely what this codebase could not
do.

## What carried forward

- **Valence-driven parameter mapping.** The happy/sad control scaling
  kick, snare, and bass selection is the direct ancestor of EMOTE's
  valence/arousal transformation.
- **Per-instrument pattern generation** became the `MI_*` instrument
  layer.
- **The symbolic/audio split.** Doing both in one file is what made this
  version collapse; the current architecture's hard boundary between
  "what to play" and "how it sounds" is the lesson.

## A note on the history

The commit history here was **reconstructed after the fact.** During 2025
this project was versioned the way a lot of people start out — by saving
numbered copies of the file (`ProgrammableSong1.2.py` through
`ProgrammableSong3.1.py`). Those 32 snapshots have been replayed into
git as one file with one commit each, stamped with each snapshot's real
modification time.

So: the code is original, the dates are real, and the diffs are genuine
diffs between files that actually existed. The *commits* did not exist at
the time. Nothing here was backdated to imply a working practice that
wasn't happening — the point was to recover a development record that was
sitting in the filesystem instead of in version control.

Dead-end experiments (`_debug`, `_smart`, `_backup`, `_improved`,
`_zero_crossing`, `_fixed_part*`, `*_new`) were left out. They never
rejoined the main line.

Two quirks preserved rather than cleaned up:

- `2.14` was saved on Jul 17 and `2.13` on Jul 19. The history is ordered
  by date, so 2.14 lands first.
- `3.0` (Aug 4) and `3.1` (Oct 30) each represent months of work in a
  single commit, because only the final state of each was saved. The
  history gets coarser toward the end.

## Running it

Don't. It needs `pyaudio`, `sounddevice`, `soundfile`, `librosa`,
`pedalboard`, and a compiled `libsynth.dylib` built from `synthlib.cpp`
with no build script. Several files still hold absolute
`/Users/busterbaer/...` sample paths. It was macOS-only and never ran
anywhere but the machine it was written on.

It is here to be read, not executed.
