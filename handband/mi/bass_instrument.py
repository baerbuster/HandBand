"""
Bass Instrument

The band's low, single-note voice. Where the chord instrument sounds a
whole chord per strike, the bass plays ONE note at a time and moves it
around melodically. This module is built up one small piece at a time,
bottom to top, matching the bass spec.

Tier 1 — the simple scalar decisions (this file, so far):

  1. Bass Octave — take the chord's root note and drop it down a fixed
     number of octaves, so the bass sits below everything else.
  2. Rhythm Coupling — one 0-1 number for how strongly the bass copies
     the chord instrument's rhythm, driven by arousal: calm locks to the
     chords, energized breaks away and does its own thing.
  3. Chord-Tone Probability — how often a bass note lands on an actual
     chord tone vs. a passing note between them. A weighted pick among a
     few probability levels, biased by arousal (energized = more passing
     notes = more restless).
  4. Pattern Endpoint — which chord tone a phrase ENDS on (root, 3rd, or
     5th), biased by arousal: calm lands on the root (restful), energized
     lands on the 3rd/5th (left hanging).

Tier 2 — the two generators:

  5. Bassline Contour — a Fourier curve, in SCALE DEGREES, that the line
     rides: valence tilts it up or down, arousal makes it wiggle. One cell
     long, and it repeats.
  6. Bass Rhythmic Cell — the H/C/X rhythm for one cell, tiled across the
     song, coupled to the chord instrument's hits.

Tier 3 — the integrator:

  7. Relative Pattern Construction — fold the rhythm and the contour into
     one cell of actual bass line, in symbolic scale degrees. RELATIVE
     because the degrees are still measured against the key, not against
     the chord sounding over them; pointing them at each chord is a
     separate step that comes later.
"""

import math
import random

from handband.mi.instrument import Instrument
from handband.mi.pattern_primitives import weighted_choice, archetype_placer
from handband.mi.chord_library import chord_root_offset, clamp_to_register
from handband.mi.chord_instrument import active_chords
from handband.mi.bass_modes import mode_for_chord, degree_to_semitone, modal_degree_label
from handband.mi.global_parameters import CURRENT_KEY

SLOTS_PER_MEASURE = 16

BASS_OCTAVE_DROP = 2      # how many octaves below the chord root the bass sits

# Contour (Tier 2): the curve the bass rides, measured in SCALE DEGREES,
# not semitones. The vertical axis counts steps of the scale, so a whole
# octave is 7 steps (degree 1 up to degree 8) rather than 12 semitones,
# and the curve is centered on degree 1 — the tonic — rather than on 0.
# Working in degrees means the curve is already diatonic: every value it
# passes through is a note in the key, with no chromatic notes to filter
# out later.
DEGREES_PER_OCTAVE = 7    # 1 -> 8 is an octave: seven steps
CONTOUR_CENTER = 1        # the curve sits on degree 1, the tonic

CONTOUR_MAX_TILT = DEGREES_PER_OCTAVE     # valence drift across the cell
CONTOUR_MAX_WIGGLE = DEGREES_PER_OCTAVE   # wiggle swing off the tilt

# The chord-tone probability levels the bass draws from. Higher = sticks
# to chord tones; lower = wanders onto passing notes. Ordered high->low so
# arousal ramps the draw from the first toward the last.
CHORD_TONE_LEVELS = [0.8, 0.6, 0.4]
CHORD_TONE_WEIGHT_FLOOR = 0.1   # keeps every level reachable

# A phrase's landing note is drawn from this many of the chord's lowest
# tones: the root, 3rd, and 5th. (Fewer if the chord has fewer tones.)
ENDPOINT_TONE_COUNT = 3
ENDPOINT_WEIGHT_FLOOR = 0.1     # keeps the 3rd/5th reachable even when calm

# Rhythm cell (Tier 2). How hard a slot the chord instrument hits gets
# favored when coupling is high: weight is multiplied by
# (1 + coupling * COUPLING_BOOST) on those slots.
COUPLING_BOOST = 1.0

# How hard arousal plants a note on the downbeat. Each measure's "1" has
# its weight multiplied by (1 + arousal * DOWNBEAT_BOOST), so a calm bass
# treats the 1 like any other slot and an energized one nearly always
# lands it.
DOWNBEAT_BOOST = 20.0

# Fill: how much of the gap after each hit is held (C) rather than
# silent (X). Driven by VALENCE, not arousal — this is the third density,
# independent of how many notes there are. Sad/dark = long held notes,
# bright = short detached ones.
FILL_AT_MIN_VALENCE = 1.0       # valence -1 -> gaps fully sustained (legato)
FILL_AT_MAX_VALENCE = 0.0       # valence +1 -> gaps fully silent (staccato)

# Relative pattern construction (Tier 3). The bass is allowed a two-octave span,
# expressed as raw step counts: 8 is the octave above the tonic, -6 the
# octave below. This is exactly the range the symbolic degree numbering
# covers (see to_symbolic_degree), and it matches the default bass's
# max_octave_range of 2.
DEGREE_STEP_MAX = 8
DEGREE_STEP_MIN = -6

# Which scale degrees count as chord tones for the snap. For now this is
# the tonic triad — root, 3rd, 5th — because relative pattern construction is still
# key-relative and has no chord under it yet. When the pattern is made
# relative to the chord root, this becomes the current chord's own tones.
CHORD_TONE_DEGREES = (1, 3, 5)


def default_bass_instrument():
    """A reasonable first-pass electric-bass voice."""
    return Instrument("bass",
                      octave=2,               # register bottom, two octaves under the chords
                      max_octave_range=2,     # bass stays fairly narrow
                      accent_follow=0.6,
                      groove_follow=0.8,      # bass leans hard into the groove
                      max_density_rate=16,    # can move as fast as 16th notes
                      syncopation_follow=0.6)


# ----------------------------------------------------------------------
# 1. Bass Octave
# ----------------------------------------------------------------------
def bass_root(root_note, octave_drop=BASS_OCTAVE_DROP):
    """
    Drop a chord's root note down `octave_drop` octaves to get the bass's
    root, e.g. root_note=60 (C4), octave_drop=2 -> 36 (C2). One octave is
    12 semitones. This is the low anchor the rest of the bass line is
    built around.
    """
    return root_note - octave_drop * 12


# ----------------------------------------------------------------------
# 2. Rhythm Coupling Probability
# ----------------------------------------------------------------------
def rhythm_coupling(arousal):
    """
    How strongly the bass's rhythm favors MATCHING the chord instrument's
    rhythm, as a 0-1 probability. Inverse of arousal: at arousal 0 the
    bass fully locks to the chords (1.0), at arousal 1 it goes fully its
    own way (0.0). Used later to bias the bass rhythm-cell choice.
    """
    return 1 - arousal


# ----------------------------------------------------------------------
# 3. Chord-Tone Probability
# ----------------------------------------------------------------------
def chord_tone_probability(arousal):
    """
    Draw the probability that a sampled bass note snaps to an actual chord
    tone (vs. staying a passing note between chord tones). A soft weighted
    pick among CHORD_TONE_LEVELS, biased by arousal: at arousal 0 the draw
    favors the high level (mostly chord tones, settled); at arousal 1 it
    favors the low level (more passing notes, restless); flat at 0.5. A
    weight floor keeps every level reachable, so nothing is ever forbidden.
    """
    n = len(CHORD_TONE_LEVELS)
    weights = [(1 - arousal) * (n - 1 - i)
               + arousal * i
               + CHORD_TONE_WEIGHT_FLOOR
               for i in range(n)]
    return weighted_choice(CHORD_TONE_LEVELS, weights)


# ----------------------------------------------------------------------
# 4. Pattern Endpoint
# ----------------------------------------------------------------------
def pattern_endpoint(arousal, chord_tones):
    """
    Choose which chord tone a phrase lands on: its root, 3rd, or 5th (the
    chord's lowest ENDPOINT_TONE_COUNT tones). A soft weighted draw biased
    by arousal: at arousal 0 it favors the root (a resolved, restful
    landing); at arousal 1 it favors the higher tones (3rd/5th, left
    hanging); flat at 0.5. A weight floor keeps every option reachable.

    chord_tones is the current chord's notes low-to-high (intervals or
    concrete MIDI, whichever the caller is working in). Returns the chosen
    tone in that same form.
    """
    options = chord_tones[:ENDPOINT_TONE_COUNT]
    n = len(options)
    if n <= 1:
        return options[0]
    weights = [(1 - arousal) * (n - 1 - i)
               + arousal * i
               + ENDPOINT_WEIGHT_FLOOR
               for i in range(n)]
    return weighted_choice(options, weights)


# ----------------------------------------------------------------------
# 5. Bassline Contour (Tier 2 — the Fourier pitch curve)
# ----------------------------------------------------------------------
def bass_contour(valence, arousal, cell_measures):
    """
    The curve the bass line rides, as a list of SCALE DEGREES, one value
    per 16th-note slot in ONE CELL.

    The vertical axis is scale degrees, NOT semitones: 1 is the tonic, 8 is
    the octave above it, -6 the octave below, and one octave is therefore 7
    steps. Because the axis is the scale itself, every value the curve
    passes through is already a note in the key — there are no chromatic
    in-between notes to filter out downstream. Values are continuous
    (e.g. 3.4); rounding a sample to a whole degree is the caller's job.

    The curve is one cell long and REPEATS with the rhythm cell, re-anchored
    each repetition to whatever chord is sounding there. That makes the bass
    a riff — the same melodic shape restated over moving harmony — rather
    than a line that wanders off across the song. There is deliberately no
    long-range drift; both layers below live entirely inside the cell.

    Two layers add together:

      tilt(t)  = valence * CONTOUR_MAX_TILT * (t/T)
                 A straight climb or fall across the cell, starting at the
                 tonic and reaching up to a full octave — 7 degrees, up if
                 happy, down if sad — by the cell's end, then restarting
                 from the next chord's root.

      wiggle(t) = a sum of harmonics 1..n_max, each an equal-weight sine/
                 cosine with a random amplitude and phase, scaled so its
                 peak swing is arousal * CONTOUR_MAX_WIGGLE degrees.
                 n_max = 1 + (N/2 - 1) * arousal   (N = cell slots)
                 so calm = one slow bump (n=1), full arousal = motion up to
                 the Nyquist harmonic (flipping every 16th note). Equal
                 weight is required: a rolloff would suppress the fast
                 harmonics and the cutoff would stop meaning anything.

    The whole curve is shifted so slot 0 reads exactly CONTOUR_CENTER — the
    cell opens on the tonic, and everything after it is measured against
    that in scale steps.
    """
    n_slots = cell_measures * SLOTS_PER_MEASURE
    if n_slots == 0:
        return []
    T = n_slots
    nyquist = n_slots // 2
    n_max = max(1, round(1 + (nyquist - 1) * arousal))

    # Equal-weight harmonics, random amplitude + phase, so every generated
    # line is a different curve of the same character.
    coeffs = [(random.uniform(-1, 1), random.uniform(-1, 1))
              for _ in range(n_max + 1)]   # index 0 unused

    tilt = []
    wiggle = []
    for t in range(n_slots):
        tilt.append(valence * CONTOUR_MAX_TILT * (t / T))
        w = sum(a * math.sin(n * 2 * math.pi * t / T)
                + b * math.cos(n * 2 * math.pi * t / T)
                for n, (a, b) in enumerate(coeffs) if n >= 1)
        wiggle.append(w)

    # Scale the wiggle so its peak swing is exactly arousal * one octave.
    peak = max((abs(w) for w in wiggle), default=0.0)
    scale = (arousal * CONTOUR_MAX_WIGGLE / peak) if peak else 0.0
    curve = [tilt[t] + wiggle[t] * scale for t in range(n_slots)]

    # Anchor the cell to the tonic: slot 0 reads degree 1, and every other
    # slot is that many scale steps above or below it.
    start = curve[0]
    return [c - start + CONTOUR_CENTER for c in curve]


# ----------------------------------------------------------------------
# 6. Bass Rhythmic Cell (Tier 2 — the H/C/X rhythm)
# ----------------------------------------------------------------------
def chord_onsets(progression):
    """
    The slots where a new chord is struck, read straight off the
    progression: every slot that isn't a "C" continuation IS an onset.

    Deliberately NOT derived from active_chords/chord_change_slots — those
    answer the chord instrument's question ("which chord is sounding
    here"), and both lose onsets. active_chords backfills leading
    continuations with the first chord, hiding its true onset; and
    comparing sounding chords misses a repeated numeral (V -> V is a new
    strike, not a change). Harmonic rhythm has to come from the
    progression itself.
    """
    return [i for i, slot in enumerate(progression) if slot != "C"]


def bass_cell_measures(progression):
    """
    How long the bass's repeating rhythmic cell is, in measures: the
    SHORTEST chord duration in the progression, floored to whole measures
    and never less than one. The idea is that the cell should fit inside
    the fastest harmonic rhythm, so the pattern reads as a groove against
    the chords rather than fighting them.

    The result is then walked down to a divisor of the song length, so
    tiling the cell always comes out even.
    """
    measures = len(progression) // SLOTS_PER_MEASURE
    boundaries = chord_onsets(progression) + [len(progression)]
    shortest = min(boundaries[i + 1] - boundaries[i]
                   for i in range(len(boundaries) - 1))

    cell = max(1, min(shortest // SLOTS_PER_MEASURE, measures))
    while measures % cell:
        cell -= 1
    return cell


def bass_fill(valence):
    """
    The fraction of each post-hit gap that stays sounding (C) instead of
    going silent (X) — the bass's THIRD density, alongside how many notes
    there are and how much silence there is.

    A held whole note and eight staccato eighths are both "dense" bass,
    in different ways, so this is deliberately a separate axis from
    density_per_measure: that one sets how many notes, this one sets how
    long they last. Driven by valence so the two don't move together —
    dark and heavy holds notes, bright and bouncy clips them.
    """
    t = (valence + 1) / 2       # -1..1 -> 0..1
    return FILL_AT_MIN_VALENCE + (FILL_AT_MAX_VALENCE - FILL_AT_MIN_VALENCE) * t


def _bass_archetype_weights(n_slots):
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


def chord_hit_mask(chord_part, cell_slots):
    """
    Fold the chord instrument's hits down onto one cell's worth of slots:
    1 where the chords strike, 0 elsewhere. Since the bass cell tiles, a
    cell slot counts as a chord-hit slot if the chords strike there in
    ANY repetition. This is what the bass couples its rhythm TO.
    """
    mask = [0] * cell_slots
    for i, (sym, _chord) in enumerate(chord_part):
        if sym == "H":
            mask[i % cell_slots] = 1
    return mask


def place_bass_cell(instrument, valence, arousal, cell_measures, mask):
    """
    Choose the hit slots for one bass cell.

    Four placement forces multiply into one weight list:
      - the instrument's syncopation weighting, tiled per measure
      - an archetype shape over the whole cell
      - the coupling term, which boosts slots the chords hit by
        (1 + coupling * COUPLING_BOOST)
      - the downbeat term, which boosts every measure's "1" by
        (1 + arousal * DOWNBEAT_BOOST)

    Coupling comes from arousal (see rhythm_coupling): calm locks the
    bass onto the chord hits, energized lets it wander onto its own slots.
    The downbeat term pulls the other way: the more energized the bass
    gets, the harder it plants a note on the 1, so a busy line still lands
    the bar rather than floating. It also counteracts the syncopation
    weighting, which inverts at high valence and would otherwise make the
    downbeat the LEAST likely slot exactly when the line is busiest.

    No boost ever forbids anything — an unboosted slot keeps its full
    syncopation/archetype weight, it just competes against boosted ones.
    """
    cell_slots = cell_measures * SLOTS_PER_MEASURE
    coupling = rhythm_coupling(arousal)
    sync = instrument.syncopation_weights(valence) * cell_measures   # tiled
    arch = _bass_archetype_weights(cell_slots)
    downbeat = [1 + arousal * DOWNBEAT_BOOST if i % SLOTS_PER_MEASURE == 0 else 1
                for i in range(cell_slots)]
    weights = [s * a * (1 + coupling * COUPLING_BOOST * m) * d
               for s, a, m, d in zip(sync, arch, mask, downbeat)]

    n = min(instrument.density_per_measure(arousal) * cell_measures, cell_slots)
    positions = archetype_placer(n, weights, list(range(cell_slots)))
    return sorted(set(positions))


def create_bass_rhythm_part(valence, arousal, progression, chord_part,
                            instrument=None):
    """
    Build the bass's rhythm for the whole song: a flat list, one symbol
    per 16th-note slot.

        "H"  strike a new note here
        "C"  the note is still sounding (held)
        "X"  silence

    Pass 1 places the cell's hits (see place_bass_cell) and tiles them
    across the song. Pass 2 fills each gap: hold for bass_fill(valence)
    of it, then rest.

    Unlike the chord instrument, this generator does NOT cut a sustain at
    a chord change — the H/C/X cell is placed and tiled without regard to
    the harmony. What happens to a hold that spans a chord change is decided
    later, at note realization (see realize_bass_notes): the note is
    RE-STRUCK on the new chord's harmonic degree and held out to its
    original end. That retrigger is a realization detail; the cell itself
    stays a plain repeating rhythm.

    No pitch is decided at this stage — that is relative pattern
    construction's job, sampling the contour at the "H" positions.
    """
    if instrument is None:
        instrument = default_bass_instrument()

    total = len(progression)
    measures = total // SLOTS_PER_MEASURE
    cell_measures = bass_cell_measures(progression)
    cell_slots = cell_measures * SLOTS_PER_MEASURE

    mask = chord_hit_mask(chord_part, cell_slots)
    cell = place_bass_cell(instrument, valence, arousal, cell_measures, mask)
    hits = sorted(offset + s
                  for offset in range(0, total, cell_slots)
                  for s in cell)

    part = ["X"] * total
    fill = bass_fill(valence)

    for i, h in enumerate(hits):
        part[h] = "H"
        next_hit = hits[i + 1] if i + 1 < len(hits) else total
        max_sustain = next_hit - h - 1
        for j in range(h + 1, h + 1 + round(fill * max_sustain)):
            part[j] = "C"

    # Repair: no measure may be pure silence. A measure carried by a note
    # ringing in from an earlier hit is fine; only one that came out
    # entirely "X" gets a fresh hit on its downbeat.
    for m in range(measures):
        start = m * SLOTS_PER_MEASURE
        if all(sym == "X" for sym in part[start:start + SLOTS_PER_MEASURE]):
            part[start] = "H"

    return part


# ----------------------------------------------------------------------
# 7. Relative Pattern Construction (Tier 3 — the integrator)
# ----------------------------------------------------------------------
def to_symbolic_degree(step):
    """
    Convert a raw step count into the symbolic degree numbering.

    The contour counts scale STEPS from the tonic: 1 is the tonic, 8 the
    octave above, and it keeps going down through 0 to -6, the octave
    below. That's easy arithmetic but not how degrees are named — there is
    no "degree 0", and the note under degree 1 is the 7th of the octave
    below.

    So the region below the tonic gets renamed. Descending in pitch, the
    numbering reads:

        8  7  6  5  4  3  2  1  -7  -6  -5  -4  -3  -2  -1

    A negative number names the same degree an octave down: -7 is the 7th
    below the tonic (the note immediately under degree 1) and -1 is the
    tonic itself, one octave lower. Note that inside the negative region a
    LARGER magnitude is a HIGHER pitch — the sign marks the lower octave,
    it isn't a direction along the axis.

    This numbering spans exactly two octaves, which is the bass's range.
    """
    if step >= CONTOUR_CENTER:
        return step
    return -(step + DEGREES_PER_OCTAVE)


def from_symbolic_degree(degree):
    """Inverse of to_symbolic_degree: symbolic numbering back to raw steps."""
    if degree >= CONTOUR_CENTER:
        return degree
    return -degree - DEGREES_PER_OCTAVE


def _chord_tone_candidates(chord_tone_degrees, lo, hi):
    """
    Every chord tone in raw-step space between lo and hi. Chord tones
    repeat once per octave, so each degree is stamped out at every octave
    offset that lands inside the range.
    """
    candidates = []
    octave_lo = (lo - max(chord_tone_degrees)) // DEGREES_PER_OCTAVE
    octave_hi = (hi - min(chord_tone_degrees)) // DEGREES_PER_OCTAVE + 1
    for octave in range(octave_lo, octave_hi + 1):
        for degree in chord_tone_degrees:
            step = degree + DEGREES_PER_OCTAVE * octave
            if lo <= step <= hi:
                candidates.append(step)
    return sorted(set(candidates))


def create_bass_degree_cell(rhythm_cell, contour, arousal,
                            chord_tone_degrees=CHORD_TONE_DEGREES):
    """
    Relative pattern construction: fold the rhythm cell and the contour
    into ONE cell of the bass line, expressed in symbolic scale degrees.

    Returns a list the same length as the cell, one entry per 16th-note
    slot, mirroring the chord instrument's part format:

        ("H", degree)   strike this scale degree
        ("C", None)     the previous degree is still sounding
        ("X", None)     silence

    The degrees are KEY-relative, not chord-relative: degree 1 means the
    tonic of the key, full stop. Re-pointing them at whatever chord is
    sounding is a later step, deliberately not done here.

    What actually happens per slot:

      - "H": read the contour at that slot and round it to a whole degree.
        The contour axis IS the scale, so the rounded value is already a
        diatonic note — no chromatic filtering needed.
      - chord-tone snap: with probability chord_tone_probability(arousal),
        that degree is pulled to the nearest chord tone; otherwise it stays
        where the curve put it, as a passing note. One draw per cell, so a
        cell is consistently settled or consistently restless rather than
        flickering between the two note to note.
      - the last "H" of the cell is overridden by pattern_endpoint, so the
        cell lands on a chosen chord tone instead of wherever the curve
        happened to end.
      - "C"/"X" carry no degree: a hold re-sounds nothing, and a rest is
        silence. What a "C" is holding is simply the last "H" before it.

    Everything is computed in raw step counts and converted to the
    symbolic numbering on the way out (see to_symbolic_degree).
    """
    snap_probability = chord_tone_probability(arousal)
    candidates = _chord_tone_candidates(chord_tone_degrees,
                                        DEGREE_STEP_MIN, DEGREE_STEP_MAX)

    hit_slots = [i for i, sym in enumerate(rhythm_cell) if sym == "H"]
    last_hit = hit_slots[-1] if hit_slots else None

    cell = []
    for slot, sym in enumerate(rhythm_cell):
        if sym != "H":
            cell.append((sym, None))
            continue

        step = round(contour[slot % len(contour)])
        if random.random() < snap_probability and candidates:
            step = min(candidates, key=lambda c: (abs(c - step), c))
        if slot == last_hit:
            # The landing note is chosen among the chord's own root/3rd/5th
            # in the tonic octave, NOT among every chord tone in range —
            # pattern_endpoint reads its options as "root, 3rd, 5th" in
            # order, which only holds for one octave's worth.
            step = pattern_endpoint(arousal, list(chord_tone_degrees))

        step = max(DEGREE_STEP_MIN, min(DEGREE_STEP_MAX, step))
        cell.append(("H", to_symbolic_degree(step)))
    return cell


def create_bass_pattern_cell(valence, arousal, progression, chord_part,
                             instrument=None):
    """
    The whole Tier 3 pipeline in one call. Returns the three pieces
    together, all from the SAME generation:

        (rhythm_part, contour, cell)

      rhythm_part  the H/C/X rhythm for the whole song
      contour      the scale-degree curve, one cell long
      cell         one cell of bass line in symbolic scale degrees

    All three come back from one call on purpose. Both the rhythm and the
    contour are stochastic, so generating them separately — once here and
    once for a view to draw — would produce a picture that doesn't match
    the line. Anything that needs to display or play the bass takes all
    three from here.

    The rhythm part is generated for the full song and then sliced to its
    first cell. The cell is what actually repeats — the song-length part is
    that same cell tiled — so its first cell_slots entries ARE the cell.
    """
    if instrument is None:
        instrument = default_bass_instrument()

    cell_measures = bass_cell_measures(progression)
    cell_slots = cell_measures * SLOTS_PER_MEASURE

    rhythm_part = create_bass_rhythm_part(valence, arousal, progression,
                                          chord_part, instrument)
    contour = bass_contour(valence, arousal, cell_measures)
    cell = create_bass_degree_cell(rhythm_part[:cell_slots], contour, arousal)
    return rhythm_part, contour, cell


# ----------------------------------------------------------------------
# 8. Note Realization (Tier 4 — chord-relative, concrete MIDI)
# ----------------------------------------------------------------------
def bass_degree_stream(bass_rhythm, bass_cell, progression):
    """
    Which symbolic scale degree sounds at each slot of the whole song, as a
    per-slot list of (type, degree):

        ("H", d)      strike degree d here
        ("C", None)   the previous degree is still sounding (hold)
        ("R", None)   silence

    This is the single source of truth for the bass's degree-per-slot AND
    its retrigger rule, shared by realize_bass_notes (which turns each degree
    into MIDI) and any view that wants to LABEL the line. The key-relative
    degree cell (bass_cell) is tiled across the song; a "repaired" hit with
    no cell degree defaults to 1 (the root); and a hold whose sounding chord
    differs from the chord the note was struck under is RE-STRUCK — emitted
    as a fresh "H" on the same degree (see realize_bass_notes for why).

    Silence is reported as "R" to match the chord stream, even though the
    bass's own rhythm alphabet upstream calls a rest "X".
    """
    active = active_chords(progression)
    cell_slots = len(bass_cell)

    stream = []
    held_degree = None      # symbolic degree of the note currently sounding
    held_chord = None       # chord it was (re)struck under
    for i, sym in enumerate(bass_rhythm):
        if sym == "X":
            stream.append(("R", None))
            held_degree = held_chord = None
            continue

        chord = active[i]
        if sym == "H":
            _csym, degree = bass_cell[i % cell_slots]
            if degree is None:
                degree = 1
            held_degree, held_chord = degree, chord
            stream.append(("H", degree))
        else:   # "C"
            if held_degree is not None and chord != held_chord:
                held_chord = chord      # retrigger on the new chord
                stream.append(("H", held_degree))
            else:
                stream.append(("C", None))
    return stream


def realize_bass_notes(bass_rhythm, bass_cell, progression, arousal,
                       instrument, accent_map, groove_vector):
    """
    Turn the KEY-relative degree cell into the whole song's concrete bass
    line, re-anchored to whatever chord is sounding at each slot. This is
    the step that finally points the degrees at the harmony: the repeating
    cell is tiled over the progression and each degree is read against the
    CURRENT chord's root and mode.

    Returns ONE per-slot list the sequencer reads directly, in EXACTLY the
    same shape realize_chord_notes emits — the two are interchangeable:

        {"type": "H", "notes": [...], "accent": <dB>, "timing": <offset>}
        {"type": "C"}     still sounding (hold)
        {"type": "R"}     silence

    "notes" is a list even though the bass is monophonic (one entry), so a
    consumer iterates it identically for both instruments. accent/timing are
    this instrument's personal response to the shared accent map and groove
    vector (accent_follow * dB on accented slots; groove displacement scaled
    by groove_follow, the vector being one measure tiled) — same two calls
    the chord instrument makes. Only strikes carry data; C/R are bare.

    (Silence is emitted as "R" to match the chord stream, even though the
    bass's own rhythm alphabet upstream calls a rest "X".)

    Per struck degree d, under the sounding chord:
        note = bass_root_midi + chord_root_offset(chord)
               + degree_to_semitone(mode_for_chord(chord), d)
    then octave-clamped into the instrument's live register
    [bass_root_midi, bass_root_midi + register_octaves(arousal)*12).

    Chord change under a held note: the H/C/X skeleton (bass_rhythm) is left
    alone, but a "C" whose sounding chord differs from the chord the note
    was struck under is RE-STRUCK — emitted as a fresh "H" on the SAME
    symbolic degree, re-mapped to the new chord, then held out. So the
    realized stream carries slightly MORE attacks than bass_rhythm: one
    extra wherever a hold crosses a chord boundary. No legato / no pitch
    slide — every pitch change is a real attack.

    A "repaired" hit (a dead-air measure given a downbeat strike by
    create_bass_rhythm_part) lands where the cell has no degree; it defaults
    to degree 1, the root.
    """
    active = active_chords(progression)
    root_midi = 12 * (instrument.octave + 1) + CURRENT_KEY   # bass tonic anchor
    range_span = instrument.register_octaves(arousal) * 12

    accent_boosts = instrument.accent_volume(accent_map)   # per-slot dB, whole song
    groove = instrument.groove_offsets(groove_vector)      # 16 values, per measure

    sequence = []
    for i, (sym, degree) in enumerate(bass_degree_stream(bass_rhythm, bass_cell,
                                                         progression)):
        if sym != "H":
            sequence.append({"type": sym})
            continue
        chord = active[i]
        semi = degree_to_semitone(mode_for_chord(chord), degree)
        note = root_midi + chord_root_offset(chord) + semi
        sequence.append({
            "type": "H",
            "notes": clamp_to_register([note], root_midi, range_span),
            "accent": accent_boosts[i],
            "timing": groove[i % SLOTS_PER_MEASURE],
        })
    return sequence


if __name__ == "__main__":
    for note in (60, 62, 67):   # C4, D4, G4
        print(f"chord root {note} -> bass root {bass_root(note)}")
    print()
    for a in (0.0, 0.3, 0.7, 1.0):
        print(f"arousal {a} -> rhythm coupling {rhythm_coupling(a):.2f}")
    print()
    # Chord-tone prob is a random draw, so show the average over many draws
    # to make the arousal bias visible.
    for a in (0.0, 0.5, 1.0):
        draws = [chord_tone_probability(a) for _ in range(2000)]
        print(f"arousal {a} -> avg chord-tone prob {sum(draws) / len(draws):.2f}")
    print()
    # Pattern endpoint over a C major triad (root 0, 3rd 4, 5th 7): show how
    # often each tone is chosen as the landing note across many phrases.
    triad = [0, 4, 7]
    for a in (0.0, 0.5, 1.0):
        draws = [pattern_endpoint(a, triad) for _ in range(3000)]
        counts = {t: draws.count(t) / len(draws) for t in triad}
        print(f"arousal {a} -> endpoint mix root={counts[0]:.2f} "
              f"3rd={counts[4]:.2f} 5th={counts[7]:.2f}")

    # Contour: draw it as an ASCII plot over a 2-measure cell so the tilt
    # (valence) and bumpiness (arousal) are both visible. Each row is one
    # 16th-note slot; the marker's horizontal position is the scale degree.
    print()
    random.seed(1)

    def plot(curve, width=41):
        span = max(1.0, max(abs(c - CONTOUR_CENTER) for c in curve))
        mid = width // 2
        lines = []
        for c in curve:
            pos = mid + round((c - CONTOUR_CENTER) / span * mid)
            pos = max(0, min(width - 1, pos))
            row = [" "] * width
            row[mid] = "|"       # the tonic line (degree 1)
            row[pos] = "*"
            lines.append("".join(row))
        return lines

    for valence, arousal, label in [(0.0, 0.15, "calm, neutral"),
                                    (0.9, 0.5, "happy, medium"),
                                    (-0.8, 0.95, "sad, frantic")]:
        curve = bass_contour(valence, arousal, cell_measures=2)
        print(f"[{label}]  v={valence} a={arousal}   "
              f"(| = tonic/degree 1, * = degree, left=low right=high)")
        for row in plot(curve):
            print("   ", row)
        print(f"    range: degree {min(curve):+.1f} to {max(curve):+.1f}")
        print()

    # Rhythm cell: show the bass part against the chord part it couples to.
    from MI_Chord_Progression_Engine import create_song_form, create_chord_progression
    from MI_Chord_Instrument import (default_chord_instrument,
                                     create_chord_instrument_part)
    from MI_Accent_Pattern_Engine import create_accent_pattern
    from MI_Groove_Delay_Engine import create_groove_pattern

    def rows(symbols, glyphs):
        return ["".join(glyphs[s] for s in symbols[i:i + SLOTS_PER_MEASURE])
                for i in range(0, len(symbols), SLOTS_PER_MEASURE)]

    print("=" * 60)
    for valence, arousal in [(-0.7, 0.2), (0.0, 0.5), (0.8, 0.9)]:
        form = create_song_form(valence, arousal)
        length, _density, rep = form
        prog = create_chord_progression(valence, arousal, form)
        chord_part = create_chord_instrument_part(valence, arousal, prog,
                                                  default_chord_instrument())
        accents = create_accent_pattern(length, arousal, rep)
        groove = create_groove_pattern(valence, arousal)
        bass = default_bass_instrument()
        # One call, so the rhythm printed below and the degrees printed
        # under it are the same generated line.
        part, _curve, pattern = create_bass_pattern_cell(
            valence, arousal, prog, chord_part, bass)

        cell = bass_cell_measures(prog)
        print(f"valence={valence} arousal={arousal}  measures={len(prog) // 16}  "
              f"cell={cell}m  coupling={rhythm_coupling(arousal):.2f}  "
              f"fill={bass_fill(valence):.2f}")
        print(f"   hits={part.count('H')} held={part.count('C')} "
              f"silent={part.count('X')}")
        chord_rows = rows([sym for sym, _ in chord_part],
                          {"H": "|", "C": "=", "R": "."})
        bass_rows = rows(part, {"H": "|", "C": "=", "X": "."})
        print("   chords / bass   (|=hit  ==held  .=silent)")
        for c, b in zip(chord_rows, bass_rows):
            print(f"    C {c}")
            print(f"    B {b}")

        # Relative pattern construction: the one repeating cell, in degrees.
        print("   pattern cell (symbolic degrees, . = hold or rest)")
        print("     ", " ".join(f"{d:>3}" if d is not None else "  ."
                                for _sym, d in pattern))
        print("     ", " ".join(f"{sym:>3}" for sym, _d in pattern))

        # Note realization (Tier 4): the cell pointed at the sounding chords,
        # as concrete MIDI, with accent/groove folded in exactly as the chord
        # instrument does — the emitted dicts are the same shape. Extra "H"s
        # vs. the rhythm above are retriggers where a hold crossed a change.
        sequence = realize_bass_notes(part, pattern, prog, arousal, bass,
                                      accents, groove)
        names = ["C", "C#", "D", "D#", "E", "F",
                 "F#", "G", "G#", "A", "A#", "B"]
        def name(m):
            return f"{names[m % 12]}{m // 12 - 1}"
        root_midi = 12 * (bass.octave + 1) + CURRENT_KEY
        span = bass.register_octaves(arousal) * 12
        notes = [s["notes"][0] for s in sequence if s["type"] == "H"]
        in_range = all(root_midi <= n < root_midi + span for n in notes)
        attacks = sum(1 for s in sequence if s["type"] == "H")
        retriggers = attacks - part.count("H")
        print(f"   realized: {attacks} attacks "
              f"({retriggers} retrigger(s) at chord changes)  "
              f"range {min(notes)}-{max(notes)} all-in-window={in_range}")
        active = active_chords(prog)
        first_hits = [(i, s) for i, s in enumerate(sequence)
                      if s["type"] == "H"][:8]
        print("   realized bass notes (first 8 attacks: chord -> note, accent, timing):")
        for i, s in first_hits:
            print(f"     slot {i:>3}: {active[i]:<6} -> {s['notes'][0]:>3} "
                  f"({name(s['notes'][0])})  accent={s['accent']:.1f}dB "
                  f"timing={s['timing']:+.2f}")
        print()
