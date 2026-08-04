"""
Chord Instrument

The first real instance of the Instrument class (mi/instrument.py). It
takes the band-wide data — the chord progression, plus valence/arousal
(and later the accent map and groove vector) — and produces THIS
player's performance chart: a per-slot rhythm of when to strike the
current chord, how long to hold it, and when to rest.

Two-pass rhythm generation (the settled design):

  Cell length. First a rhythmic-cell length is chosen the same way the
  progression length is (valence-weighted), but the options are just
  1 or 2 measures. That cell is generated once and tiled across the
  whole progression, so the rhythm repeats.

  Pass 1 — HITS. All placement forces superimpose into one weight list
  over the cell's slots (here: the instrument's syncopation weighting,
  tiled per measure, times a chosen archetype shape). density_per_measure
  sets how many hits per measure; archetype_placer draws their positions.

  Pass 2 — GAPS. Every non-hit slot becomes a Continue (chord still
  ringing) or a Rest. Because a Continue is only legal after a Hit or a
  Continue, each gap is forced into "sustain k slots, then rest," so the
  whole pass reduces to choosing ONE sustain length per hit. That length
  is the staccato<->legato axis, driven by arousal (high arousal = short
  = staccato). A sustain is always capped so it never crosses a chord
  change (never hold an old chord over new harmony) — so a tiled cell can
  read slightly differently where a real chord change interrupts it.

Output (working format, not yet final): a flat list the same length as
the progression, each slot one of
    ("H", chord)   struck here, play this chord
    ("C", chord)   chord still sounding (sustain)
    ("R", None)    silence

Pitch/voicing is deferred — the chord is still just its Roman-numeral
string; a resolver turns it into notes later.
"""

from handband.mi.instrument import Instrument
from handband.mi.pattern_primitives import weighted_choice, archetype_placer
from handband.mi.chord_library import (chord_intervals, chord_root_offset,
                              notes_from_root, chord_to_midi, voice_lead,
                              rotate_voicing, clamp_to_register)
from handband.mi.global_parameters import CURRENT_KEY
import random

SLOTS_PER_MEASURE = 16
CELL_OPTIONS = [1, 2]        # a hit cell is 1 or 2 measures long


def default_chord_instrument():
    """A reasonable first-pass keyboard/guitar comping voice."""
    return Instrument("chords",
                      octave=4,               # register bottom -> root at C4
                      max_octave_range=3,     # widens from 1 octave (calm) to 3 (peak)
                      accent_follow=0.4,
                      groove_follow=0.3,
                      max_density_rate=8,     # up to eighth-note comping
                      syncopation_follow=0.4)


def cell_length_calculator(valence, prog_measure_length):
    """
    Choose the hit cell's length in measures (1 or 2), valence-weighted
    the same way progression length is — positive valence leans longer.
    Clamped so the cell never exceeds (and always divides) the song.
    """
    options = [c for c in CELL_OPTIONS if c <= prog_measure_length]
    # negative valence boosts the short option, positive boosts the long
    weights = [2 ** (max(0, -valence) * (len(options) - 1 - i)
                     + max(0, valence) * i)
               for i in range(len(options))]
    return weighted_choice(options, weights)


def active_chords(progression):
    """
    The chord sounding at each slot: carry each onset forward over its
    "C" continuation slots, and backfill any leading continuations into
    the first real chord so nothing opens on an undefined chord.
    """
    active = []
    current = None
    for slot in progression:
        if slot != "C":
            current = slot
        active.append(current)
    first = next((c for c in active if c is not None), None)
    for i in range(len(active)):
        if active[i] is None:
            active[i] = first
        else:
            break
    return active


def chord_change_slots(active):
    """Slots where the sounding chord differs from the previous slot."""
    return {i for i in range(1, len(active)) if active[i] != active[i - 1]}


def _archetype_weights(n_slots):
    """A strictly-positive placement shape over the cell's slots."""
    shape = weighted_choice(["front", "back", "center", "even", "random"],
                            [1, 1, 1, 1, 1])
    if shape == "front":
        return [n_slots - i for i in range(n_slots)]
    if shape == "back":
        return [1 + i for i in range(n_slots)]
    if shape == "center":
        mid = n_slots / 2
        return [mid - abs(i - mid) + 1 for i in range(n_slots)]
    if shape == "even":
        return [1] * n_slots
    return [random.random() + 0.1 for _ in range(n_slots)]   # random


def place_hit_cell(instrument, valence, arousal, cell_measures):
    """
    Pass 1: choose the hit slots for a cell of cell_measures measures.

    The per-measure syncopation weighting (tiled across the cell) and a
    chosen archetype shape multiply into one weight list; density is
    density_per_measure per measure, so cell_measures measures get that
    many times as many hits.
    """
    cell_slots = cell_measures * SLOTS_PER_MEASURE
    sync = instrument.syncopation_weights(valence) * cell_measures   # tiled
    arch = _archetype_weights(cell_slots)
    weights = [s * a for s, a in zip(sync, arch)]

    n = min(instrument.density_per_measure(arousal) * cell_measures, cell_slots)
    positions = archetype_placer(n, weights, list(range(cell_slots)))
    return sorted(set(positions))


def create_chord_instrument_part(valence, arousal, progression, instrument=None):
    """
    Build the chord instrument's performance chart for the whole song.

    Returns a flat list, one entry per slot: ("H", chord), ("C", chord),
    or ("R", None).
    """
    if instrument is None:
        instrument = default_chord_instrument()

    total = len(progression)
    measures = total // SLOTS_PER_MEASURE
    active = active_chords(progression)
    changes = chord_change_slots(active)

    # Cell length, then tile its hit positions across the whole song.
    cell_measures = cell_length_calculator(valence, measures)
    cell_slots = cell_measures * SLOTS_PER_MEASURE
    cell = place_hit_cell(instrument, valence, arousal, cell_measures)
    hits = sorted(offset + s
                  for offset in range(0, total, cell_slots)
                  for s in cell)

    part = [("R", None)] * total

    # Pass 2: per hit, a sustain length k, capped by the next hit and any
    # chord change, scaled by arousal (high arousal -> short -> staccato).
    for i, h in enumerate(hits):
        chord = active[h]
        part[h] = ("H", chord)

        next_hit = hits[i + 1] if i + 1 < len(hits) else total
        next_change = min((c for c in changes if c > h), default=total)
        gap_end = min(next_hit, next_change)

        max_sustain = gap_end - h - 1
        k = round((1 - arousal) * max_sustain)
        for j in range(h + 1, h + 1 + k):
            part[j] = ("C", chord)

    # Repair: no measure may be pure silence. A measure covered by its own
    # hit OR by a sustain ringing in from an earlier one is fine; only a
    # measure that came out entirely "R" gets a fresh hit on its downbeat,
    # playing whatever chord is active there. (Not a per-measure hit floor —
    # sustains are allowed to carry a measure; this only fills dead air.)
    for m in range(measures):
        start = m * SLOTS_PER_MEASURE
        measure = part[start:start + SLOTS_PER_MEASURE]
        if all(sym == "R" for sym, _ in measure):
            part[start] = ("H", active[start])

    return part


def realize_chord_notes(part, arousal, instrument, accent_map, groove_vector):
    """
    Fold notes, accent, and timing into the H/C/R part, returning ONE
    per-slot list the sequencer reads directly. Each slot is a dict:
        {"type": "H", "notes": [...], "accent": <dB>, "timing": <offset>}
        {"type": "C"}     still ringing (hold)
        {"type": "R"}     silence

    Only hits carry data — a strike is the only thing with notes to sound,
    an accent boost, and an onset to nudge. C/R stay bare markers so the
    sequencer still knows when to hold and release.

    notes run the full pitch chain (voice-led from the previous hit, then
    rotated by the voicing index and clamped to the register). accent is
    this instrument's dB boost at that slot (its accent_follow applied to
    the shared accent map); timing is its groove displacement at that
    slot's position in the measure (the groove vector is one measure, tiled).

    The register height is the instrument's live register_octaves(arousal),
    so higher arousal widens the register the voicings are clamped into.
    """
    root_midi = 12 * (instrument.octave + 1) + CURRENT_KEY   # C4 = 60
    range_span = instrument.register_octaves(arousal) * 12

    accent_boosts = instrument.accent_volume(accent_map)   # per-slot dB, whole song
    groove = instrument.groove_offsets(groove_vector)      # 16 values, per measure

    sequence = []
    last = None
    for step, (sym, chord) in enumerate(part):
        if sym != "H":
            sequence.append({"type": sym})
            continue
        placed = notes_from_root(chord_root_offset(chord), chord_intervals(chord))
        midi = chord_to_midi(root_midi, placed)
        led = voice_lead(midi, last)
        index = instrument.voicing_index(arousal, len(led))
        voiced = clamp_to_register(rotate_voicing(led, index), root_midi, range_span)
        sequence.append({
            "type": "H",
            "notes": voiced,
            "accent": accent_boosts[step],
            "timing": groove[step % SLOTS_PER_MEASURE],
        })
        last = voiced
    return sequence


if __name__ == "__main__":
    from handband.mi.chord_progression_engine import create_song_form, create_chord_progression
    from handband.mi.accent_pattern_engine import create_accent_pattern
    from handband.mi.groove_delay_engine import create_groove_pattern

    def render(sequence):
        rows = []
        for i in range(0, len(sequence), SLOTS_PER_MEASURE):
            rows.append("".join({"H": "|", "C": "=", "R": "."}[slot["type"]]
                                for slot in sequence[i:i + SLOTS_PER_MEASURE]))
        return rows

    for valence, arousal in [(-0.5, 0.15), (0.4, 0.5), (0.8, 0.9)]:
        form = create_song_form(valence, arousal)
        length, _density, rep = form
        prog = create_chord_progression(valence, arousal, form)
        instrument = default_chord_instrument()
        part = create_chord_instrument_part(valence, arousal, prog, instrument)
        accents = create_accent_pattern(length, arousal, rep)
        groove = create_groove_pattern(valence, arousal)
        sequence = realize_chord_notes(part, arousal, instrument, accents, groove)
        hits = sum(1 for slot in sequence if slot["type"] == "H")
        print(f"valence={valence} arousal={arousal}  measures={len(prog) // 16}  hits={hits}")
        print("   |=hit  ==sustain  .=rest")
        for r in render(sequence):
            print("   ", r)
        shown = 0
        for step, slot in enumerate(sequence):
            if slot["type"] == "H":
                print(f"    step {step:>3}: notes={slot['notes']} "
                      f"accent={slot['accent']:.1f}dB timing={slot['timing']:+.2f}")
                shown += 1
                if shown >= 5:
                    break
        print()
