"""
Drum Instrument

The kit: kick, snare, hat — three DrumElements, each a full Instrument
in its own right, held by a thin DrumsInstrument container. First pass
per MI_Drum_Instrument_Spec.md: triggers only (no fills, no toms, no
synthesis), variant engine present but OFF.

Output: ONE package, a dict keyed by stream name, each value a full
song-length per-slot list in EXACTLY the format realize_chord_notes and
realize_bass_notes emit — so drums["kick"] is substitutable for
chord_sequence / bass_sequence anywhere a consumer reads the shared
shape. Percussion is one-shot, so the type alphabet is only H and R
("C" never appears). `notes` is the synthesis fundamental — the tonic
of the current key at the element's own octave — NOT a drum-map index;
element identity lives in the stream key.

Everything is generated at CELL level and tiled. The cell length is
inherited from the bass (bass_cell_measures), so the drum cell and the
bass cell repeat in lockstep and kick/bass coupling holds at every
repetition. Per element, one placement weight per slot is the product
of three factors — syncopation x archetype x coupling — and hits are
placed without replacement, then realized with the element's own
accent/groove response.

Departures from the spec's sources, recorded per its definition of done:

1. `even` rewritten as weights-based (strong periodic peaks, floored
   elsewhere) rather than the mask family's placement-time bypass — a
   bypass would discard the other weight factors (spec section 4).
   Consequence: the archetype weight builder takes the pre-clamped hit
   count as an input, since even spacing has no meaning without it —
   `even` is the only archetype that reads it.
2. `reference_mask` duplicates `chord_hit_mask`'s intent deliberately —
   fractional vs. boolean; `MI_Bass_Instrument.py` left untouched
   (spec section 1.5).
3. `DRUM_COUPLING_BOOST` is separate from the bass's `COUPLING_BOOST` —
   it multiplies a continuous mask where the bass's multiplies a boolean
   one; the two are expected to diverge under tuning (spec section 4).
4. Zero hits per cell is not legal — the limitation is deferred with
   fills, because an all-R stream forces a decision about the dynamic
   key set (spec section 4). Beyond the spec: the floor is no longer
   the base class's hardcoded 1 — DrumElement overrides
   density_per_measure with a per-element min_density_rate (hits per
   measure at arousal 0, validated >= 1 so zero stays illegal), because
   a drum keeps time even when the band is calm.
5. Drums omit the silent-measure repair that chord and bass apply — a
   silent measure in one kit element is ordinary drumming (spec
   section 4).
6. The spec's crash-on-downbeat example is unreachable without a metric
   term in variant selection; left out while the engine is off (spec
   section 5).
7. Bass defect at place_bass_cell:385 — a negative coupling coefficient
   can zero a slot there, violating never-forbids-a-slot. Noted, NOT
   fixed; out of scope (spec section 4).
"""

import random

from MI_Instrument import Instrument
from MI_Pattern_Primitives import weighted_choice, archetype_placer
from MI_Bass_Instrument import bass_cell_measures   # the ONLY bass import
from MI_Global_Parameters import CURRENT_KEY

SLOTS_PER_MEASURE = 16

# ----------------------------------------------------------------------
# Tunables. All named and centralized (see the parameter-neural-net goal);
# nothing below is magic-numbered inline.
# ----------------------------------------------------------------------

# Element fundamentals: each element sounds the tonic of the current key
# at its own octave (12 * (octave + 1) + CURRENT_KEY). Chosen against
# real drum acoustics — kick in the sub band, snare on shell-ring
# frequency, hat as the anchor for a metallic partial stack.
KICK_OCTAVE = 1
SNARE_OCTAVE = 3
HAT_OCTAVE = 5

# Coupling. The multiplier applied per slot is
#     max(DRUM_COUPLING_FLOOR, 1 + c * DRUM_COUPLING_BOOST * mask[q])
# c is authored per element (the personality); DRUM_COUPLING_BOOST is the
# global depth knob a tuning pass reaches for — a no-op at 1.0 on purpose.
# The floor clamps the MULTIPLIER, not c: full avoid leaves a slot ten
# times less likely than neutral, never impossible.
DRUM_COUPLING_BOOST = 1.0
DRUM_COUPLING_FLOOR = 0.1
KICK_BASS_COUPLING = 0.8     # kick attracts toward the bass's slots
SNARE_KICK_COUPLING = -0.8   # snare avoids the kick's slots

# Archetypes. Six names; equal static weights, learnable later.
DRUM_ARCHETYPES = ["front", "back", "center", "alternating", "even", "random"]
DRUM_ARCHETYPE_CHOICE_WEIGHTS = [1, 1, 1, 1, 1, 1]
EVEN_PEAK_WEIGHT = 10.0      # weight on the regular-spacing slots
EVEN_FLOOR_WEIGHT = 0.1      # everywhere else — even composes, never bypasses
RANDOM_WEIGHT_FLOOR = 0.1    # the jitter floor of the instrument-family random

# Variant Selection Engine (OFF in the first pass — every default element
# gets an empty table). A variant is a (stream_name, center) pair on an
# emote axis; selection is a per-hit soft draw with a floor.
VARIANT_AXIS_SPAN = 2.0      # the valence axis runs -1..1
VARIANT_WEIGHT_FLOOR = 0.1   # keeps every variant reachable at any e

# Hat's future variant table, one uncomment away. Centers at -0.75 / 0.0
# / +0.75 put the equal-weight crossovers at exactly +-0.375 — the
# original document's ride/crash thresholds, derived instead of magic.
# HAT_VARIANT_TABLE = {
#     "axis": "valence",
#     "variants": [("ride", -0.75), ("hi-hat", 0.0), ("crash", 0.75)],
# }

# Per-element personalities (first-pass values, tuned later). Drums lean
# much harder into accent than chords or bass — ghost notes and hat
# accents are most of what makes a part feel human. Density runs between
# the element's own MIN (its floor at arousal 0 — drums keep time even
# when the band is calm) and MAX (hits per measure at full arousal).
KICK_ACCENT_FOLLOW = 0.8
KICK_GROOVE_FOLLOW = 0.3
KICK_MIN_DENSITY_RATE = 2
KICK_MAX_DENSITY_RATE = 12
KICK_SYNCOPATION_FOLLOW = 0.3

SNARE_ACCENT_FOLLOW = 0.9
SNARE_GROOVE_FOLLOW = 0.6
SNARE_MIN_DENSITY_RATE = 2
SNARE_MAX_DENSITY_RATE = 12
SNARE_SYNCOPATION_FOLLOW = 0.5

HAT_ACCENT_FOLLOW = 0.7
HAT_GROOVE_FOLLOW = 0.9
HAT_MIN_DENSITY_RATE = 4     # the hat runs denser than kick and snare
HAT_MAX_DENSITY_RATE = 16
HAT_SYNCOPATION_FOLLOW = 0.4


# ----------------------------------------------------------------------
# The element
# ----------------------------------------------------------------------
class DrumElement(Instrument):
    """
    One piece of the kit. Keeps all Instrument behavior unchanged —
    accent_volume, groove_offsets, syncopation_weights — and ADDS the
    coupling table, the variant table, and a per-element density FLOOR:
    density_per_measure is overridden so the at-least-one floor becomes
    min_density_rate, this element's hits per measure at arousal 0.

    coupling         : {reference_name: coefficient}, coefficient in
                       [-1, 1]. Positive attracts this element toward the
                       reference's slots, negative avoids them. A name
                       resolves to another kit element's cell or a
                       caller-supplied reference pattern (see
                       DrumsInstrument.create_part).
    variant_table    : {"axis": <emote name>, "variants": [(name, center)]}
                       or None/empty for a single stream keyed by the
                       element's own name. OFF for every default element.
    min_density_rate : hits per measure at arousal 0 (the floor). At
                       least 1 — zero hits per cell stays not legal
                       (departure 4). Never above max_density_rate.

    max_octave_range is dead for drums (no register to widen) and pinned
    at the minimum.
    """

    def __init__(self, name, octave,
                 accent_follow=0.5,
                 groove_follow=0.5,
                 min_density_rate=1,
                 max_density_rate=8,
                 syncopation_follow=0.5,
                 coupling=None,
                 variant_table=None):
        super().__init__(name, octave, max_octave_range=1,
                         accent_follow=accent_follow,
                         groove_follow=groove_follow,
                         max_density_rate=max_density_rate,
                         syncopation_follow=syncopation_follow)
        if not 1 <= min_density_rate <= max_density_rate:
            raise ValueError(
                f"element '{name}': min_density_rate {min_density_rate} "
                f"must be in [1, max_density_rate={max_density_rate}]")
        self.min_density_rate = min_density_rate
        self.coupling = dict(coupling) if coupling else {}
        for ref, c in self.coupling.items():
            # Enforced, not clamped: the floor would absorb an
            # out-of-range c and produce plausible output, making the
            # failure invisible.
            if not -1 <= c <= 1:
                raise ValueError(
                    f"element '{name}': coupling coefficient for '{ref}' "
                    f"is {c}, outside [-1, 1]")
        self.variant_table = variant_table

    def density_per_measure(self, arousal):
        """The inherited mapping with this element's own floor in place
        of the base class's hardcoded 1: arousal still scales toward
        max_density_rate, but the count never drops below
        min_density_rate — a drum keeps time even when the band is calm."""
        return max(self.min_density_rate,
                   round(arousal * self.max_density_rate))

    def fundamental(self):
        """The pitch this element's oscillators tune to: the tonic of the
        current key at this element's octave. Same formula as the chord
        and bass anchors, so retuning the key retunes the whole kit."""
        return 12 * (self.octave + 1) + CURRENT_KEY


def default_drum_instrument():
    """A reasonable first-pass kick / snare / hat kit, matching the
    default_chord_instrument / default_bass_instrument factory pattern."""
    kick = DrumElement("kick", KICK_OCTAVE,
                       accent_follow=KICK_ACCENT_FOLLOW,
                       groove_follow=KICK_GROOVE_FOLLOW,
                       min_density_rate=KICK_MIN_DENSITY_RATE,
                       max_density_rate=KICK_MAX_DENSITY_RATE,
                       syncopation_follow=KICK_SYNCOPATION_FOLLOW,
                       coupling={"bass": KICK_BASS_COUPLING})
    snare = DrumElement("snare", SNARE_OCTAVE,
                        accent_follow=SNARE_ACCENT_FOLLOW,
                        groove_follow=SNARE_GROOVE_FOLLOW,
                        min_density_rate=SNARE_MIN_DENSITY_RATE,
                        max_density_rate=SNARE_MAX_DENSITY_RATE,
                        syncopation_follow=SNARE_SYNCOPATION_FOLLOW,
                        coupling={"kick": SNARE_KICK_COUPLING})
    hat = DrumElement("hat", HAT_OCTAVE,
                      accent_follow=HAT_ACCENT_FOLLOW,
                      groove_follow=HAT_GROOVE_FOLLOW,
                      min_density_rate=HAT_MIN_DENSITY_RATE,
                      max_density_rate=HAT_MAX_DENSITY_RATE,
                      syncopation_follow=HAT_SYNCOPATION_FOLLOW,
                      coupling={})   # couples to nothing — empty table,
                                     # never a dangling name
    return DrumsInstrument([kick, snare, hat])


# ----------------------------------------------------------------------
# Folding — external references down to one cell
# ----------------------------------------------------------------------
def _slot_is_hit(slot):
    """A strike in any of the shared per-slot spellings: the bass rhythm's
    plain "H", the (sym, data) tuple parts, or a realized {"type": ...}."""
    if isinstance(slot, dict):
        return slot.get("type") == "H"
    if isinstance(slot, (tuple, list)):
        return slot[0] == "H"
    return slot == "H"


def reference_mask(part, cell_slots):
    """
    Fold a full-song per-slot pattern down onto one cell:

        mask[q] = (repetitions hitting q) / (repetitions)     # 0..1

    Fold, not slice — a slice is only correct when the reference is
    exactly cell-periodic, and the bass's silent-measure repair plants
    hits that aren't in cell 1. Fractional, not boolean — at P = 2Q a
    slot hit in both halves is a stronger anchor than one hit in one.
    (Deliberately NOT a refactor of chord_hit_mask; see departure 2.)
    """
    reps = max(1, len(part) // cell_slots)
    counts = [0] * cell_slots
    for i, slot in enumerate(part):
        if _slot_is_hit(slot):
            counts[i % cell_slots] += 1
    return [c / reps for c in counts]


# ----------------------------------------------------------------------
# Archetype Engine
# ----------------------------------------------------------------------
def choose_drum_archetype():
    """Pick a placement shape for one element's cell."""
    return weighted_choice(DRUM_ARCHETYPES, DRUM_ARCHETYPE_CHOICE_WEIGHTS)

def drum_archetype_weights(archetype, cell_slots, n_hits):
    """
    Build the named archetype's per-slot shape weight over the cell, and
    its capacity — the number of slots actually open (nonzero weight),
    the same rule MI_Accent_Pattern_Engine.py:86 already applies. The
    caller clamps its hit count to capacity before placing.

    Shapes are the instrument-family variants (front/back/center/random),
    EXCEPT `alternating`, taken from the mask family because its hard
    zeros — a hat playing straight 8ths — are exactly its shape, and
    `even`, newly written as strong periodic peaks at the spacing
    interval so it composes into the weight product instead of bypassing
    it (departure 1). n_hits is read only by `even`.
    """
    if archetype == "front":
        weights = [cell_slots - i for i in range(cell_slots)]
    elif archetype == "back":
        weights = [1 + i for i in range(cell_slots)]
    elif archetype == "center":
        mid = cell_slots / 2
        # the instrument-family "+1" variant: the mask version zeroes
        # i = 0, and forbidding a kick's downbeat is a bug, not a shape
        weights = [mid - abs(i - mid) + 1 for i in range(cell_slots)]
    elif archetype == "alternating":
        start = random.randint(0, 1)
        weights = [1 if i % 2 == start else 0 for i in range(cell_slots)]
    elif archetype == "random":
        weights = [random.random() + RANDOM_WEIGHT_FLOOR
                   for _ in range(cell_slots)]
    elif archetype == "even":
        peaks = {int(i * cell_slots / n_hits) for i in range(n_hits)}
        weights = [EVEN_PEAK_WEIGHT if i in peaks else EVEN_FLOOR_WEIGHT
                   for i in range(cell_slots)]
    else:
        raise ValueError(f"unknown drum archetype {archetype!r}")

    capacity = sum(1 for w in weights if w > 0)
    return weights, capacity


# ----------------------------------------------------------------------
# Coupling Engine
# ----------------------------------------------------------------------
def coupling_multipliers(coupling, masks, cell_slots):
    """
    One multiplier per slot, folding in every reference this element
    couples to. Multiplicative, matching place_bass_cell's precedent —
    the result is simply a third multiplicand alongside syncopation and
    archetype. The floor keeps a maximally-avoided slot ten times less
    likely than neutral, never forbidden.
    """
    mult = [1.0] * cell_slots
    for name, c in coupling.items():
        mask = masks[name]
        for q in range(cell_slots):
            mult[q] *= max(DRUM_COUPLING_FLOOR,
                           1 + c * DRUM_COUPLING_BOOST * mask[q])
    return mult


# ----------------------------------------------------------------------
# Density + Cell Construction Engines
# ----------------------------------------------------------------------
def build_element_cell(element, valence, arousal, cell_measures, masks):
    """
    One element's cell: a binary hit list, cell_measures * 16 slots long.

    Density is decided per cell (density_per_measure * cell_measures,
    same line as the chord and bass engines) — progression length never
    enters. The three weight factors multiply into one placement weight
    per slot, the hit count is clamped to the archetype's capacity, and
    archetype_placer draws the positions without replacement.
    """
    cell_slots = cell_measures * SLOTS_PER_MEASURE
    n = min(element.density_per_measure(arousal) * cell_measures, cell_slots)

    archetype = choose_drum_archetype()
    arch, capacity = drum_archetype_weights(archetype, cell_slots, n)
    n = min(n, capacity)

    sync = element.syncopation_weights(valence) * cell_measures   # tiled
    couple = coupling_multipliers(element.coupling, masks, cell_slots)
    weights = [s * a * m for s, a, m in zip(sync, arch, couple)]

    positions = archetype_placer(n, weights, list(range(cell_slots)))
    cell = [0] * cell_slots
    for p in positions:
        cell[p] = 1
    return cell


# ----------------------------------------------------------------------
# Variant Selection Engine (generic; OFF for every default element)
# ----------------------------------------------------------------------
def select_variant(variant_table, emote_values):
    """
    Draw which sound one hit makes: a soft weighted choice over the
    table's variants, each weighted by closeness of the emote value to
    its center, floored so every variant stays reachable. One draw PER
    HIT — that is what keeps the key set genuinely dynamic.
    """
    axis = variant_table["axis"]
    if axis not in emote_values:
        raise ValueError(f"variant table names unknown axis {axis!r}; "
                         f"known: {sorted(emote_values)}")
    e = emote_values[axis]
    names = [name for name, _center in variant_table["variants"]]
    weights = [max(VARIANT_WEIGHT_FLOOR,
                   1 - abs(e - center) / VARIANT_AXIS_SPAN)
               for _name, center in variant_table["variants"]]
    return weighted_choice(names, weights)


# ----------------------------------------------------------------------
# Realization Engine
# ----------------------------------------------------------------------
def realize_drum_element(element, cell, progression, accent_map,
                         groove_vector, emote_values):
    """
    Tile one element's cell across the song and emit its stream(s), in
    the shared per-slot format:

        {"type": "H", "notes": [fundamental], "accent": <dB>, "timing": <offset>}
        {"type": "R"}

    accent/timing are this element's personal response to the shared
    maps — the same two calls the chord and bass instruments make. Each
    hit is sorted into its variant's stream (one draw per hit); with the
    table empty or absent, everything lands in one stream keyed by the
    element's name. Only streams that actually received a hit exist —
    the key set is dynamic.
    """
    total = len(progression)
    cell_slots = len(cell)
    fundamental = element.fundamental()
    accent_boosts = element.accent_volume(accent_map)   # per-slot dB, whole song
    groove = element.groove_offsets(groove_vector)      # 16 values, per measure

    table = element.variant_table
    has_variants = bool(table and table.get("variants"))

    streams = {}

    def stream_for(name):
        if name not in streams:
            streams[name] = [{"type": "R"} for _ in range(total)]
        return streams[name]

    for i in range(total):
        if not cell[i % cell_slots]:
            continue
        name = (select_variant(table, emote_values) if has_variants
                else element.name)
        stream_for(name)[i] = {
            "type": "H",
            "notes": [fundamental],
            "accent": accent_boosts[i],
            "timing": groove[i % SLOTS_PER_MEASURE],
        }
    return streams


# ----------------------------------------------------------------------
# The container
# ----------------------------------------------------------------------
class DrumsInstrument:
    """
    A thin container over the kit's elements. Deliberately NOT an
    Instrument — every Instrument parameter belongs to the individual
    elements, so a container built on it would have every field dead.
    It owns the cell length (inherited from the bass at generation time,
    the drum instrument's only global) and runs the elements in an order
    resolved from their coupling tables.
    """

    def __init__(self, elements):
        self.elements = list(elements)
        names = [e.name for e in self.elements]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate element names in kit: {names}")

    def _generation_order(self, kit):
        """Topological order over the intra-kit coupling edges, so every
        referenced element is generated before its dependents. Resolved
        from the tables, not hard-coded — adding an element adds a node.
        A cycle raises rather than deadlocking."""
        remaining = {name: {ref for ref in kit[name].coupling if ref in kit}
                     for name in kit}
        order = []
        listing = [e.name for e in self.elements]   # stable tie-break
        while remaining:
            ready = [n for n in listing
                     if n in remaining and not remaining[n]]
            if not ready:
                raise ValueError(
                    f"cyclic coupling graph among {sorted(remaining)}")
            for n in ready:
                order.append(n)
                del remaining[n]
            for deps in remaining.values():
                deps.difference_update(ready)
        return [kit[n] for n in order]

    def create_part(self, valence, arousal, progression, accent_map,
                    groove_vector, references):
        """
        Generate the whole kit for one song. references is
        {name: full_song_per_slot_pattern} (the caller supplies
        {"bass": bass_rhythm} — the rhythm, NOT bass_sequence, whose
        chord-change retriggers follow harmony rather than the cell).

        Resolution order per coupling name: another kit element's
        already-generated cell (used as-is, never folded), else a
        references key (folded via reference_mask), else raise — a
        dangling name is a wiring bug, and silent-skip makes it a quiet
        one. Kit names and reference keys must be disjoint, or the
        resolution order is ambiguous.
        """
        cell_measures = bass_cell_measures(progression)
        cell_slots = cell_measures * SLOTS_PER_MEASURE

        kit = {e.name: e for e in self.elements}
        collisions = set(kit) & set(references)
        if collisions:
            raise ValueError(
                f"names collide between kit elements and references: "
                f"{sorted(collisions)}")
        for e in self.elements:
            for ref in e.coupling:
                if ref not in kit and ref not in references:
                    raise ValueError(
                        f"element '{e.name}' couples to '{ref}', which is "
                        f"neither a kit element nor a references key")

        emote_values = {"valence": valence, "arousal": arousal}
        cells = {}
        package = {}
        for element in self._generation_order(kit):
            masks = {}
            for ref in element.coupling:
                if ref in kit:
                    masks[ref] = cells[ref]   # cell-length already; as-is
                else:
                    masks[ref] = reference_mask(references[ref], cell_slots)
            cell = build_element_cell(element, valence, arousal,
                                      cell_measures, masks)
            cells[element.name] = cell
            streams = realize_drum_element(element, cell, progression,
                                           accent_map, groove_vector,
                                           emote_values)
            for key, stream in streams.items():
                if key in package:
                    raise ValueError(f"duplicate stream key '{key}' "
                                     f"across the kit")
                package[key] = stream
        return package


def create_drum_part(valence, arousal, progression, accents, groove,
                     references, instrument=None):
    """
    Main entry point, parameter order matching realize_bass_notes as
    closely as the inputs allow. progression is the only length input:
    song length is len(progression), cell length is
    bass_cell_measures(progression). Returns the element-outer package
    of section 1 of the spec.
    """
    if instrument is None:
        instrument = default_drum_instrument()
    return instrument.create_part(valence, arousal, progression,
                                  accents, groove, references)


if __name__ == "__main__":
    from MI_Chord_Progression_Engine import (create_song_form,
                                             create_chord_progression)
    from MI_Chord_Instrument import (default_chord_instrument,
                                     create_chord_instrument_part)
    from MI_Bass_Instrument import (default_bass_instrument,
                                    create_bass_rhythm_part)
    from MI_Accent_Pattern_Engine import create_accent_pattern
    from MI_Groove_Delay_Engine import create_groove_pattern

    for valence, arousal in [(-0.7, 0.2), (0.0, 0.5), (0.8, 0.9)]:
        form = create_song_form(valence, arousal)
        length, _density, rep = form
        prog = create_chord_progression(valence, arousal, form)
        chord_part = create_chord_instrument_part(valence, arousal, prog,
                                                  default_chord_instrument())
        accents = create_accent_pattern(length, arousal, rep)
        groove = create_groove_pattern(valence, arousal)
        bass_rhythm = create_bass_rhythm_part(valence, arousal, prog,
                                              chord_part,
                                              default_bass_instrument())

        drums = create_drum_part(valence, arousal, prog, accents, groove,
                                 {"bass": bass_rhythm})
        cell = bass_cell_measures(prog)
        print(f"valence={valence} arousal={arousal}  "
              f"measures={len(prog) // SLOTS_PER_MEASURE}  cell={cell}m  "
              f"streams={list(drums)}")
        print("   bass / drums   (x=hit  .=silent)")
        bass_rows = ["".join("x" if s == "H" else "."
                             for s in bass_rhythm[i:i + SLOTS_PER_MEASURE])
                     for i in range(0, len(bass_rhythm), SLOTS_PER_MEASURE)]
        stream_rows = {
            name: ["".join("x" if slot["type"] == "H" else "."
                           for slot in stream[i:i + SLOTS_PER_MEASURE])
                   for i in range(0, len(stream), SLOTS_PER_MEASURE)]
            for name, stream in drums.items()}
        for m in range(len(bass_rows)):
            print(f"    bass  {bass_rows[m]}")
            for name in drums:
                print(f"    {name:<5} {stream_rows[name][m]}")
            print()
        for name, stream in drums.items():
            hit = next(s for s in stream if s["type"] == "H")
            hits = sum(1 for s in stream if s["type"] == "H")
            print(f"   {name:<5} hits={hits:<3} fundamental={hit['notes'][0]}")
        print()
