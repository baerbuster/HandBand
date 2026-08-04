# Drum Instrument — Design Spec

**Status: DESIGNED, NOT IMPLEMENTED (2026-07-25).** Handed off for a future
agent to build. Supersedes the original hand-written drum parameter document
and diagram — see the "departures" notes in section 4.

Related work: the bass instrument spec, the sequencer/MIDI pipeline, the score
GUI, and Phase 8 of the MI implementation plan.

Running document. Sections are added as they're settled in conversation.
Nothing here is implemented yet.

---

## 0. Scope of the first pass

Three elements only: **kick, snare, hat**.

Explicitly deferred to a later pass:
- Fills (frequency, length, density, element variation)
- Toms, ride, crash — and the valence-driven cymbal-type selector that
  chose between them
- Element-to-element coupling as a full learnable matrix (v2) — but the
  architecture must leave room for it
- Sonic/synthesis parameters. This engine produces TRIGGERS ONLY. The
  multi-layer synthesized tone (snare = ring + snap + noise, etc.) is the
  synthesizer's job, downstream.

---

## 1. Output contract — SETTLED

### Shape: element outer, time inner

The drum instrument emits ONE package: a dict keyed by element name, where
each value is a full song-length per-slot list in **exactly** the format
`realize_chord_notes` and `realize_bass_notes` already emit.

```python
{
  "kick":  [ {...}, {...}, ... ],   # len == len(progression)
  "snare": [ {...}, {...}, ... ],
  "hat":   [ {...}, {...}, ... ],
}
```

Each slot entry:

```python
{"type": "H", "notes": [<fundamental>], "accent": <dB>, "timing": <offset>}
{"type": "R"}
```

**Why element-outer and not time-outer:** the two layouts are transposes of
each other, but only this one preserves the "completely equal data
structures" property. `drums["kick"]` is literally interchangeable with
`chord_sequence` / `bass_sequence`, so the sequencer's step loop is "for
every stream I know, read index t" with no drum special case. Routing to a
synth voice is decided ONCE per stream, not re-parsed every step.

Adding toms/ride/crash later = adding keys. Adding fills later = editing
these same lists. Neither changes the structure.

### Keys are SOUNDS, not elements — and the key set is dynamic

One stream = one synth voice. When the Variant Selection Engine (section 5)
is switched on, each variant an element produces gets its OWN stream —
`"ride"` and `"crash"` are separate keys, not a field inside a `"cymbal"`
stream. So element and stream stop being 1:1.

Two reasons this beats a variant field on a shared stream:

- **More expressive.** A variant field holds one value per slot, so a crash
  and a hi-hat could never sound on the same 16th. Separate streams can.
- **Nothing downstream changes.** The sequencer's rule stays "one stream =
  one synth voice, read index t." Adding variants adds keys — no new field,
  no conditional, no parsing. Same reasoning as element-outer over
  time-outer.

**The key set is dynamic:** the package carries only the streams the
generation actually produced, not every variant an element *could* make. A
song where the selector never chose crash has no `"crash"` key. Smaller,
and the key set tells you at a glance what is in the song.

### No "C"

Percussion is one-shot: nothing sustains, nothing is released. The type
alphabet collapses to `H` and `R`. This is still a valid *subset* of the
existing contract — a consumer that handles `C` simply never sees one — so
drums are not a new format, just a restricted instance of the shared one.

Consequence: the sustain/fill axis (`bass_fill`, the chord instrument's
sustain pass) has no drum analogue. Drums are NOT a copy of the bass
rhythm pipeline.

### `notes` = the synthesis fundamental, NOT a drum-map index

General MIDI's drum map (36=kick, 38=snare, 42=hat) is built for sample
playback — the number is an index into a kit. HandBand synthesizes its
drums, so the number is a real **pitch**: the fundamental the oscillators
tune to.

Element identity comes from the **stream key**. The note number does one
job only: pitch.

Every element sounds the **tonic of the current key**, at its own octave,
using the same formula the chord and bass instruments already use
(`MI_Chord_Instrument.py:214`, `MI_Bass_Instrument.py:703`):

```python
fundamental = 12 * (ELEMENT_OCTAVE + 1) + CURRENT_KEY
```

Key changes come free — all three read `CURRENT_KEY` from
`MI_Global_Parameters`, so retuning the key retunes the whole kit.

### Element octaves (configurable constants, top of module)

```python
KICK_OCTAVE  = 1
SNARE_OCTAVE = 3
HAT_OCTAVE   = 5
```

Chosen against real drum acoustics, since the key can move the pitch class
anywhere within the octave:

| element | octave | MIDI (in C) | range across all 12 keys | target |
|---|---|---|---|---|
| kick  | 1 | 24 (C1) | 32.7 – 61.7 Hz | 808 sub ≈ 50 Hz, acoustic ≈ 60 Hz |
| snare | 3 | 48 (C3) | 130.8 – 246.9 Hz | shell ring 180 – 250 Hz |
| hat   | 5 | 72 (C5) | 523 – 988 Hz | base for the metallic partial stack |

Kick moved 0 → 1: octave 0 is 16–31 Hz, below the hearing threshold — that
is displacement, not tone. Octave 2 (65–123 Hz) tops out in tom territory.
Octave 1 lands the whole key-range inside the sub/kick band, and synth
kicks sweep DOWN into their fundamental anyway.

Snare octave 3 sits dead centre on shell-ring frequency. Hat octave 5 is an
anchor for the partial stack rather than an audible pitch — hat energy
lives at 3–10 kHz after high-passing.

### `notes` stays per-slot

The value is identical in every hit of a stream, so it *could* live once at
package level. Keep it per-slot: it preserves the identical-shape property,
and when mid-song key changes eventually land, the field is already in the
right place to vary.

### `accent` is load-bearing here

More so than for the other instruments — snare ghost notes and hat accents
are most of what makes a drum part feel human. The field already exists in
the shape, so nothing changes structurally, but the drum elements will want
much higher `accent_follow` values than chords or bass.

---

## 1.5 Input contract — SETTLED

### Entry point

```python
create_drum_part(valence, arousal, progression, accents, groove,
                 references, instrument=None)
```

Parameter order matches `realize_bass_notes` as closely as the different
inputs allow.

`progression` is the only length input: song length is `len(progression)`,
and cell length is `bass_cell_measures(progression)`, called directly. Cell
length is never passed in — deriving it from the same function the bass
uses is what guarantees the two cells stay in lockstep (section 2).

### `references`

A dict of `{name: full_song_per_slot_pattern}`. The caller supplies
`{"bass": bass_rhythm}`.

`bass_rhythm`, **not** `bass_sequence` — `bass_sequence` adds the
chord-change retriggers from `realize_bass_notes`, which follow harmony
rather than the cell. Folding those would smear harmonic events into the
drum cell.

This keeps `MI_Drum_Instrument` from importing the bass at all. The
element's coupling table names a reference; the caller decides what that
name points at. The only bass import is `bass_cell_measures`.

### Folding

The bass cell is not retrievable. `place_bass_cell:356` returns one, but
`create_bass_rhythm_part:427` binds it to a local and discards it, and
nothing exports it. (`bass_cell` in the bundle is the *degree* cell;
although its symbols are the rhythm cell verbatim, reaching rhythm through
its tuple shape would be a dependency on the wrong thing.)

So the drum module derives it, with its own `reference_mask(part, cell_slots)`,
about six lines:

```python
mask[q] = (number of repetitions hitting q) / (number of repetitions)   # 0..1
```

**Fold, not slice.** Slicing is only correct when the reference is exactly
cell-periodic at the drum's cell length, and the silent-measure repair
(`create_bass_rhythm_part:445-448`) runs *after* tiling — it can plant an
`H` on a later measure's downbeat that isn't in cell 1. Slicing misses
those. Fold works for every reference; slice is the special case.

**Fractional, not boolean.** A `P = Q` reference gives 1.0 on cell hits and
0.0 elsewhere, bit-identical to boolean. At `P = 2Q` it carries information
boolean discards: a slot the bass hits in both halves is a stronger anchor
than one it hits in one.

**Deliberate duplication.** `reference_mask` is *not* a generalization of
`chord_hit_mask:342`. That one is boolean; refactoring it to fractional
would change bass behavior and put done-item 6 in play for a change that
has nothing to do with drums. `MI_Bass_Instrument.py` stays untouched. The
duplication is intentional — recorded here so a later reader doesn't merge
them.

### Reference resolution

For each name in an element's coupling table, in order:

1. **Another element in this kit** — its already-generated cell pattern.
   Cell-length already; used as-is. Intra-kit references never fold.
2. **A key in `references`** — a full-song pattern, folded via
   `reference_mask`.
3. **Neither** — **raise**, naming the offender. A dangling name is a
   wiring bug, and silent-skip makes it a quiet one: the element generates
   fine, the part is subtly wrong, and no section 8 test catches it. An
   element that legitimately couples to nothing uses an empty table (hat,
   section 6), not a dangling name.

### Membership

`references` and the union of the coupling tables' names are different
sets, and neither contains the other. `references` may carry patterns
nothing couples to; coupling tables name kit-internal elements that never
appear in `references` at all. Stated outright because the asymmetry
invites the assumption that every coupling entry has a matching
`references` key.

Two invariants follow:

- **Names must be disjoint** across the kit's element names and
  `references`' keys. An element named `"kick"` and a reference key
  `"kick"` is ambiguous under the resolution order. Raise on collision.
- **The coupling graph must be acyclic.** Rule 1 requires the referenced
  element to be already generated, so a topological order must exist. A
  cycle raises, rather than deadlocking or reading a half-built cell.

---

## 2. Generation scale — SETTLED

### Everything is derived at CELL level, then tiled

The original spec ran two scales: density engines computed a **total across
the progression** (`total kick hits = f(arousal, progression_length)`),
which the construction engines then "scaled to cell."

That round trip is dropped. Because the cell tiles uniformly,
`total = cell_hits × cell_count` — computing the total at progression scale
and dividing it back down lands where you started, minus a rounding error
on the divide.

**Density is decided per cell. Progression length enters only as the
tiling count.**

This also matches what both existing instruments already do — the same
line appears in `MI_Chord_Instrument.py:134` and `MI_Bass_Instrument.py:388`:

```python
n = min(instrument.density_per_measure(arousal) * cell_measures, cell_slots)
```

Density is per *measure*, multiplied up to the cell. Progression length is
never an input to it.

**What this gives up:** progression-scale density could produce a total
that is *not* a multiple of the cell count — hits distributed unevenly
across repetitions, so cell 3 differs from cell 1. Nothing in the original
spec did that; every element tiled identically. So nothing is lost.

**Side effect:** the cymbal/hat inconsistency disappears. The original spec
had kick and snare emitting progression totals while cymbal emitted "hits
per cell" — cymbal was already doing it the new way.

### The two lengths and what each is for

| | source | job |
|---|---|---|
| **pattern length** | `len(progression)` | how many times the cell tiles |
| **cell length** | inherited from the bass (`bass_cell_measures`) | the space hits are placed into |

Cell length is inherited from the bass specifically so the drum cell and
the bass cell repeat **in lockstep**. Equal lengths mean kick/bass coupling
holds at every repetition instead of drifting in and out of phase.

Cell length is the ONLY global parameter of the drum instrument.
Everything else is per-element.

---

## 3. Class architecture — SETTLED

Two pieces:

**`DrumElement`** — a subclass of `Instrument`. It keeps all existing
`Instrument` behavior unchanged and ADDS the coupling parameters. Nothing
in `Instrument` itself needs to be modified.

**`DrumsInstrument`** — a thin container. It is *not* an `Instrument`: all
of `Instrument`'s parameters (octave, accent_follow, groove_follow,
max_density_rate, syncopation_follow) belong to the individual elements, so
a container built on it would have every field dead. It owns cell length
and instantiates the elements.

Three elements for now — kick, snare, hat. Adding a fourth is one more
instantiation.

### Generation order

Topological over the coupling table: kick (couples to `bass`, external) →
snare (couples to kick) → hat (empty table). `DrumsInstrument` resolves the
order from the tables rather than hard-coding the sequence, so adding an
element adds a node instead of editing a list.

### Why `Instrument` is the right base for an element

Six of its seven constructor params are already what a drum element needs:

| param | drum element |
|---|---|
| `name` | "kick" / "snare" / "hat" |
| `octave` | the synthesis fundamental (KICK=1, SNARE=3, HAT=5) |
| `max_octave_range` | dead — drums have no register to widen |
| `accent_follow` | per-element, load-bearing |
| `groove_follow` | per-element |
| `max_density_rate` | the density knob |
| `syncopation_follow` | per-element |

The four methods that carry an element's personality — `accent_volume`,
`groove_offsets`, `density_per_measure`, `syncopation_weights` — are
already written and tested.

The dead members cost nothing. `MI_Instrument.py:11` states the class is
*"deliberately NO abstract methods, so nothing is forced on any particular
instrument (drums may later want funky per-piece placement, etc.)"*, and
line 13 names drums as an intended instance. `voicing_index` self-neuters
(`if chord_size <= 1: return 0`); `register_octaves` is never called.

### Why subclass instead of using `Instrument` directly

`DrumElement` will carry parameters and behavior of its own that
`Instrument` has no place for. Subclassing keeps everything `Instrument`
already provides and leaves room to add.

---

## 4. The generic element

Every engine below runs identically for kick, snare, and hat. Nothing here
knows which element it is — element identity enters ONLY through parameter
values and coupling sources. This section replaces the original parameter
document's three parallel element chains.

### Element Parameters

- Inherited from `Instrument`: name, octave (synthesis fundamental),
  accent_follow, groove_follow, max_density_rate, syncopation_follow.
- Added by `DrumElement`: coupling table, variant table.

### Density Engine

- Hits per cell = f(x, cell_length), where x = arousal and cell_length is
  the inherited global.
- Output: number of hits to place in one cell.
- Per-element scaling comes entirely from `max_density_rate` — there is no
  per-element density formula.

**The floor already exists.** `MI_Instrument.py:140` is
`max(1, round(arousal * self.max_density_rate))`, documented at `:138` as
*"Floored at 1 so every measure plays at least once."* `DrumElement`
inherits it. No new machinery.

- Cell floor is `1 * cell_measures`. At arousal 0 every element places
  exactly that many hits.
- Per-element by construction (each element calls its own inherited
  method), uniform in practice (the `1` is hardcoded in the base class, not
  a constructor param). `max_density_rate` scales the ceiling only, so it
  has no effect at arousal 0.
- **Zero hits is not legal**, and stays not legal for the first pass.
  Recorded as a limitation rather than overridden: an all-`R` stream forces
  a second decision about whether a silent element emits a key at all under
  section 1's dynamic key set. Deferred with fills. The consequence to
  accept meanwhile is that no element can drop out — at arousal 0 the kick,
  snare and hat all sound every measure.
- Drums do **not** get the silent-measure repair that chord
  (`MI_Chord_Instrument.py:184-188`) and bass
  (`MI_Bass_Instrument.py:445-448`) apply. A silent measure in one kit
  element is ordinary drumming; a silent measure across the whole band is a
  hole in the arrangement, and that is the case the repair exists for.

Note that the repair, not the floor, is what actually delivers "every
measure plays at least once" in the other two instruments: the floor is per
*measure* but placement is per *cell*, so a front-weighted archetype on a
two-measure cell can legally leave measure 2 empty. Drums accept that.

### Archetype Engine

- Placement archetype = weighted_choice([front, back, center, alternating,
  even, random], w). Static weights, learnable later.
- Output: a per-slot shape weight over the cell.

There are two archetype families in the codebase, and they are not
interchangeable:

| family | archetypes | `alternating` | clamp |
|---|---|---|---|
| **mask** — accent `:51`, groove `:68`, progression durations `:96` | six | yes, hard zeros | `capacity` |
| **instrument placement** — chord `:106`, bass `:328` | five | no | `min(n, cell_slots)` |

Drums take **`alternating` from the mask family**. It is a hi-hat playing
straight 8ths — the most idiomatic figure in the kit — and hard zeros are
exactly its shape.

**Carry the dispatch, not just the weights.** In the mask family `random`
(`:98`) and `even` (`:100`) have *identical* weight vectors; the two-branch
dispatch at `apply_accent_archetype:100-103` is the only thing
distinguishing them. Take mask weights without mask dispatch and six names
collapse to five behaviors, and the one lost is even spacing.

Which variant of each archetype drums use:

| archetype | source | why |
|---|---|---|
| `front` | instrument | mask agrees in shape, differs only in ratio |
| `back` | instrument | same |
| `center` | instrument (`+1`, `:336`) | the mask version has a zero at `i = 0` — forbidding a kick's downbeat is a bug, not a shape |
| `alternating` | mask (`:97`, hard zeros) | the reason for taking from the mask family at all |
| `random` | instrument (`random.random() + 0.1`) | mask `random` is flat; the jitter gives a different contour per draw |
| `even` | **newly written** | see below |

**`even` is new.** The mask version bypasses the weight product entirely —
regular spacing computed at placement time. For accent and groove that is
harmless, because the weights *are* the archetype. For a drum element the
placement weight is a product of three things (syncopation, archetype,
coupling), and an `even` bypass discards two of them.
Concretely: the kick's bass coupling would silently vanish whenever `even`
is drawn, roughly one cell in six, and section 8's coupling tests would be
intermittently unable to observe the effect they assert.

So `even` is implemented as **strong periodic peaks at the spacing
interval, floored elsewhere**, composing into the product like the other
five. It still reads as even placement, coupling still bites, nothing is
bypassed. **Departure — record under done-item 7.**

**Capacity.** `capacity` is already written down, at
`MI_Accent_Pattern_Engine.py:86` — `sum(1 for w in weights if w > 0)` —
with the rule spelled out in the docstring at `:60-64` and tests asserting
it (`test_caa_alternating_half_capacity`, `test_cga_alternating_half_capacity`:
capacity 8 over 16 slots). Point at that rather than inventing a new one.

The clamp is `min(n, capacity)`. Capacity equals `cell_slots` for every
archetype except `alternating`.

### Syncopation Weighting Engine

- Per-slot metric weight over one measure, reweighted toward weak slots by
  valence × syncopation_follow. Tiled across the cell.
- Output: a per-slot weight over the cell.

### Coupling Engine

- For each named reference pattern the element couples to, a coefficient c.
  A reference is any per-slot pattern — another drum element, or an
  instrument outside the kit.
- Output: a per-slot weight bias over the cell. Slots where the reference
  hits are boosted (c positive) or suppressed (c negative).

**Multiplicative**, by existing precedent. `place_bass_cell:385` already
applies coupling as one multiplicand among the weight factors:

```python
(1 + coupling * COUPLING_BOOST * m)
```

That settles the operation *and* the combination order in one line: a
multiplier applied to the weight **is** a third multiplicand alongside
archetype and syncopation. Neither had to be chosen.

The drum term matches that shape, with a clamp:

```python
multiplier = max(DRUM_COUPLING_FLOOR,
                 1 + c * DRUM_COUPLING_BOOST * mask[q])
```

**`DRUM_COUPLING_FLOOR = 0.1`** — clamped on **the multiplier**, not on
`c`, because the multiplier is what reaches zero. Without it, `c = -1` at
`mask = 1.0` gives exactly `0`, a forbidden slot, violating section 8's
"coupling never forbids a slot"; any boost above 1.0 drives it negative,
which breaks `archetype_placer` outright. 0.1 is the value every other
floor in the codebase uses (`VOICING_WEIGHT_FLOOR`,
`CHORD_TONE_WEIGHT_FLOOR`, `ENDPOINT_WEIGHT_FLOOR`, and the `+ 0.1` in
`_bass_archetype_weights`). Multiplicatively it means a maximally-avoided
slot keeps a tenth of its unbiased weight — ten times less likely than
neutral, never impossible.

**`DRUM_COUPLING_BOOST = 1.0`** — a separate constant from the bass's
`COUPLING_BOOST`, which was tuned against a boolean `m`. This one
multiplies a continuous `m ∈ [0, 1]`, so the same number produces a
different effective bias distribution. They are expected to diverge under
tuning; sharing the constant would silently couple two unrelated tuning
decisions.

**Division of labor between `c` and the boost.** At 1.0 the boost is
currently a no-op dial, since `c` already spans the full effect range. It
is not dead: **`c` is authored per element** — the personality, one value
per coupling entry — while **`DRUM_COUPLING_BOOST` is the global depth
knob** that scales all coupling at once without touching any element's
table. That is the handle a tuning pass (or the parameter neural net)
reaches for, and it is why it exists at a value that currently changes
nothing.

**`c ∈ [-1, 1]`, enforced.** Out of range raises, rather than being
silently clamped: the floor would absorb an out-of-range `c` and produce
plausible-looking output, so the failure would be invisible. Raising is
consistent with the dangling-reference rule in section 1.5.

The term is asymmetric — full attract doubles a slot's weight, full avoid
divides it by ten. That is inherent to the multiplicative form and is fine:
attract is bounded by competition against other slots, avoid by the floor.

**Bass defect — recorded, not fixed.** `place_bass_cell:385` has this same
zero-crossing with a negative coefficient, violating the
never-forbids-a-slot invariant. It is latent only because nothing currently
passes the bass a negative one; drums are the first consumer with an
"avoid" relationship. Fixing it is out of scope and would put done-item 6
in play — but it is recorded here and in section 9 so the next person to
add a negative coefficient to the bass doesn't walk into it unwarned.

### Cell Construction Engine

- Inputs: hits per cell, archetype weights, syncopation weights, coupling
  bias, cell length.
- Multiplies the weight vectors into one placement weight per slot, then
  places the hits without replacement.
- Output: per cell hit pattern.

### Realization Engine

- Tiles the cell across progression length.
- Applies accent_follow × accent matrix -> per-hit velocity.
- Applies groove_follow × groove matrix -> per-hit timing.
- Resolves the element's fundamental: `12 * (octave + 1) + CURRENT_KEY`.
- Sorts hits into variant streams (section 5).
- Output: this element's full-song per-slot stream(s), in the shared
  instrument format.

### Three departures from the original parameter document

**1. Kick's two-stage placement became one stage.** The original placed
bass-aligned kicks first, then placed `total − bass_aligned` remaining
kicks into what was left. Bass-alignment is now a *weight boost* instead of
a pre-placement, so all hits are placed in one pass. Same intent, and it is
what `place_bass_cell` already does with chord coupling.

**2. Kick-couples-to-bass and snare-avoids-kick became one engine.** They
are the identical operation with opposite coefficient signs — attract vs.
avoid. This is also what the original wrote up separately as "Drum Element
Coupling (v2+)"; making it generic now means v2 is adding entries, not
adding machinery.

**3. Accent and groove moved out of the merge and into the element.** The
original Drum Pattern Construction Engine applied them once to the combined
pattern. But `accent_follow` and `groove_follow` are per-element
parameters — a hat and a kick lean into groove differently — so they must
be applied before the streams combine.

That leaves the container with nothing but assembly, which matches the
output shape in section 1: streams stay separate, keyed by sound.

---

## 5. Variant Selection Engine — generic, OFF in the first pass

The original document's Cymbal Type Engine (valence picks ride / crash /
hi-hat), generalized. It stops being "which cymbal" and becomes "which
sound does this element make" — every element can eventually have one.

- Each element carries a **variant table**: named sounds it can produce,
  positioned along an input axis. An empty or single-entry table means the
  engine is off and the element always produces its one sound.
- Selection = f(e), where e is an emote input. Valence for now, but the
  axis is a parameter, so an element could key off arousal or something
  else later.
- Assignment is **per hit**, not per cell.
- Input: emote value, element's variant table, the element's cell pattern.
  Output: cell pattern with a variant assigned per hit.

### Bands are out — centers instead

Ordered bands over `e` select ONE variant deterministically for a given
emote value, so every hit in the song would get the same one. That makes
per-hit assignment vacuous, leaves the dynamic key set with exactly one
variant key per element, and gives section 8's partition test nothing to
partition.

So a variant is represented by a **center** on the axis, and the variant is
drawn per hit.

```python
VARIANT_AXIS_SPAN    = 2.0    # valence range, -1..1
VARIANT_WEIGHT_FLOOR = 0.1    # house floor; keeps every variant reachable

variant_table = {
    "axis": "valence",
    "variants": [("ride", -0.75), ("hi-hat", 0.0), ("crash", 0.75)],
}
```

An entry is `(stream_name, center)`. Two fields, and the stream name IS the
dict key it produces in section 1's package, so there is no separate naming
step.

**Ordering is implied by the centers, not stored.** Explicit `(name, lo,
hi)` triples would need contiguity and full-coverage invariants validated;
centers make gaps and overlaps unrepresentable.

`"axis"` names which emote value to read, satisfying "the axis is a
parameter." Resolved by the caller against `{"valence": v, "arousal": a}`;
an unknown axis raises, same rule as a dangling coupling reference.

### Selection

```python
w_i  = max(VARIANT_WEIGHT_FLOOR, 1 - abs(e - center_i) / VARIANT_AXIS_SPAN)
name = weighted_choice(names, w)     # once per hit
```

A soft draw with a floor, matching every other selector in this layer —
`voicing_index`, `pattern_endpoint`, `syncopation_weights`, the archetype
choice. Nothing is ever forbidden, so the key set stays genuinely dynamic:
at valence −0.9 the element produces mostly ride, some hi-hat, a rare
crash, and if crash never comes up the song has no `"crash"` key.

**The original thresholds fall out.** Centers at −0.75 / 0.0 / +0.75 put
the equal-weight crossovers at exactly ±0.375 — the original document's
ride/crash thresholds, to the digit. They stop being magic constants and
become a derived consequence of three evenly spaced centers.

### Degenerate cases — this is what "off" means

| table | streams |
|---|---|
| empty / absent | one, keyed by the **element name** (`"kick"`) |
| one entry | one, keyed by the **entry name** — weight is irrelevant with a single option |
| n ≥ 2 | up to n, keyed by entry names; the element name never appears |

**Generation stays at element level; the split happens at realization.**
One cell pattern is generated per element — density, archetype,
syncopation, and coupling all operate on the whole cymbal part — and only
at realization is each hit sorted into its variant's output stream.

That keeps the musical logic where it belongs: a ride hit and a crash hit
both count as cymbal hits for density, and the snare avoids all of them
equally. If variants were generation units instead, three separate density
engines would be running for one physical limb.

**Off for all three elements in the first pass** — all three get empty
tables. Hat's ride/hi-hat/crash table is written into the module as a
commented constant, so the on-state is one uncomment away for the test.

### The example over-promises — recorded

"A ride pattern to take a crash on the downbeat" is not reachable from the
emote axis alone: with a pure emote draw, a crash landing on the downbeat
is luck, not design. Making it deliberate needs a second term —
`METRIC_STRENGTH` multiplied into the weights, so metric position pulls
crash toward slot 0 while its center pulls it in on valence. That is a real
addition, not a tweak, and nothing exercises it while the engine is off.
Left out; noted so the gap between the example and the mechanism is on the
record.

---

## 6. Element-specific

Only what does not generalize.

### Kick
- Fundamental octave: 1.
- Couples to: bass pattern, positive coefficient.

### Snare
- Fundamental octave: 3.
- Couples to: kick pattern, negative coefficient.

### Hat
- Fundamental octave: 5.
- Couples to: nothing.
- Density scalar higher than kick and snare.
- Variant table (ride / crash / hi-hat) exists but is off in the first
  pass. Does not generalize to kick or snare.

---

## 7. GUI — drum tablature lane in `MI_Score_GUI.py`

An addition to the existing Band Score window, not a new window. The whole
band reads off one aligned grid: chords, bass, drums.

### Lane stack

Each measure block goes from two lanes to THREE. The drums get ONE lane —
the same height as the chord lane and the bass lane — subdivided internally
into three thin rows, the way drum tablature actually looks:

```
C    chords            (LANE_H)
B    bass              (LANE_H)
D    drums             (LANE_H total, split into 3 rows)
       Cy  cymbals       row 0, top
       Sn  snare         row 1
       Kk  kick          row 2, bottom
```

`BLOCK_H = 3 * LANE_H + 2 * LANE_GAP`. Each drum row is `LANE_H / 3`
(~14px at the current 42px lane). Drums sit at the bottom of the stack;
within the drum lane, cymbals on top, kick on the bottom.

### What the existing code already gives for free

Vertical alignment is automatic. Every lane draws at the same `x0` with the
same `CELL_W`, so a kick hit lines up under the chord and bass strikes at
that slot by construction. Nothing needs to be synchronized by hand.

### What is new

`_draw_lane` cannot be reused as-is — it fills full-lane-height cells. The
drum lane needs its own draw routine that renders three short rows inside
one lane rectangle. It still consumes the same per-slot record shape
(`type` / `accent` / `timing`), one record list per stream.

**Glyphs** follow drum tab convention: `x` for cymbals, `o` for snare and
kick. No `sub` text — the synthesis fundamental is not something a drummer
reads, and there is no vertical room for it.

**Accent and groove marks go IN the cell, not above and below it.** At
~14px a row has no space for the gold `›` over the glyph and the pink
`‹`/`›` under it that the chord and bass lanes use. Both fold into the
glyph instead, which is also truer to real tablature:

- **accent** -> capital glyph (`X` / `O`) instead of lowercase (`x` / `o`)
- **groove** -> the glyph is nudged left or right inside its own cell,
  proportional to the timing offset. Which is literally what groove is.

**Left gutter** gets three tiny stacked row labels (`Cy` / `Sn` / `Kk`) in
place of one lane letter, drawn at `col == 0` like the existing `C` and `B`.

**Header** gains one summary line per element (accent depth + groove feel),
since `accent_follow` and `groove_follow` are per-element. Also add BPM and
key to the header readout — the chart is unreadable as a band part without
them, and `calculate_global_parameters` already computes BPM.

**Lanes are built from the keys present** in the drum package, not a
hardcoded three, since the key set is dynamic (section 1). A display-order
list puts cymbals above snare above kick, with unrecognized keys appended —
so ride and crash slot in correctly when variants are switched on.

### Upstream prerequisite

`SongSource` needs a persistent drum instrument alongside
`chord_instrument` and `bass_instrument`, and a `drum_sequence` key in the
bundle.

---

## 8. Test suite

A test suite must exist and must pass before this work counts as done.

**File:** `MI_Drum_Instrument_Test.py`, in the same style as the existing
suites (`MI_Instrument_Test.py`, `MI_Accent_Pattern_Engine_Test.py`) —
plain `run_test(name, fn)` harness, module-level asserts, a
`RESULTS: N passed, M failed` summary at the bottom. No pytest.

Required coverage:

**Output contract**
- Package is a dict; every value is a list of length `len(progression)`.
- Every slot is either `{"type": "R"}` or a hit carrying exactly `type`,
  `notes`, `accent`, `timing`.
- `"C"` never appears in any drum stream.
- `notes` is a single-element list, and its value equals
  `12 * (octave + 1) + CURRENT_KEY` for that element.
- With the variant engine off, the key set is exactly the element names.

**Generation scale**
- Drum cell length equals `bass_cell_measures(progression)` for the same
  progression.
- The realized stream is the cell tiled exactly — slot `i` and slot
  `i + cell_slots` carry the same type.

**Density**
- Hits per cell is monotonic in arousal (statistical, over many seeds).
- Never exceeds the cell's slot count, and never drops below the floor.
  State the floor at **cell** scale: `hits >= cell_measures`. NOT "every
  measure has a hit" — that is what someone writes pattern-matching off the
  chord and bass suites, and it would fail legitimately on any front- or
  back-weighted multi-measure archetype, since drums omit the
  silent-measure repair.
- Higher `max_density_rate` yields more hits at equal arousal.

**Capacity clamp**
- Density is clamped to `min(n, capacity)` before placement, at every
  archetype and at arousal 1.0. `capacity` is the existing mechanism
  (`MI_Accent_Pattern_Engine.py:86`), not a new one. This is the specific
  bug class that crashed the chord progression engine — cover it directly.

**Coupling**
- Overlap with the reference increases **monotonically in `c`** across at
  least three coefficient values (e.g. −1, 0, +1). Not merely "more than
  zero" — that is trivially satisfied by a saturated mask and would pass
  while coupling did nothing.
- The mask is **not uniform** for any reference the test uses. A uniform
  mask is a uniform bias, which is no bias at all, and would make the
  monotonicity assertion vacuous.
- A `P = Q` reference **round-trips to its own cell**: folding a pattern
  that is already periodic at the drum's cell length returns exactly that
  cell.
- Coupling never forbids a slot: with any coefficient, every slot stays
  reachable over many seeds. Same "never forbidden" rule the existing
  weighting engines are tested against — and the direct test of
  `DRUM_COUPLING_FLOOR`.
- `c` outside `[-1, 1]` raises.

**Weighting**
- Syncopation weights are strictly positive over the whole cell.
- Archetype weights are NOT — `alternating` legitimately has zeros, which
  is the whole reason `capacity` exists. Test capacity instead of
  positivity; `test_caa_alternating_half_capacity` is the template. The
  invariant that matters is that `archetype_placer` is never handed more
  hits than the weight list has nonzero entries.

**Emote extremes**
- Generates without raising at valence −1 / 0 / +1 crossed with arousal
  0 / 1, and at the shortest and longest progression the form engine can
  produce.

**Variant engine**
- **Partition** — summed `"H"` counts across an element's variant streams
  equals `cell_hits × tile_count`. No hit lost.
- **Disjoint** — no slot index carries `"H"` in two of one element's
  variant streams. No hit duplicated.
- **Off** — an empty table yields exactly one stream keyed by the ELEMENT
  name; a single-entry table yields exactly one stream keyed by the ENTRY
  name.
- **Axis** — at `e` equal to a variant's center, that variant is the modal
  draw over many seeds.
- **Reachability** — over many seeds at any `e`, every variant appears at
  least once. `VARIANT_WEIGHT_FLOOR` doing its job.
- An unknown `"axis"` raises.

**Input contract (section 1.5)**
- A coupling table naming a reference that is neither a kit element nor a
  `references` key raises, naming the offender.
- A name colliding between the kit and `references` raises.
- A cyclic coupling graph raises rather than deadlocking.

---

## 9. Definition of done

All of the following, in order. Nothing here is optional.

**1. `MI_Drum_Instrument.py` exists** and contains:
- `DrumElement(Instrument)`
- `DrumsInstrument` (thin container)
- the six generic engines of section 4
- `default_drum_instrument()`, matching the existing
  `default_chord_instrument()` / `default_bass_instrument()` factory pattern
- element octaves as named module constants (`KICK_OCTAVE`,
  `SNARE_OCTAVE`, `HAT_OCTAVE`), and every other tunable as a named module
  constant too — no magic numbers inline. (See the parameter-neural-net
  goal: all tunables named and centralized.)

**2. The output contract of section 1 holds exactly.** A drum stream is
substitutable for `chord_sequence` or `bass_sequence` anywhere a consumer
reads the shared per-slot format.

**3. Wired into `SongSource`** — a persistent drum instrument on the
instance, a `drum_sequence` key in the bundle, regenerating on the same
V/A change as everything else.

**4. The GUI of section 7 renders**, drum lane aligned to the chord and
bass lanes on the same grid, live off the slider, no crash at any input.

**5. `MI_Drum_Instrument_Test.py` exists and reports 0 failures.** Run it
and paste the summary line.

**6. The three existing suites still pass** — `MI_Instrument_Test.py`,
`MI_Chord_Progression_Engine_Test.py`, `MI_Accent_Pattern_Engine_Test.py` —
since `DrumElement` subclasses `Instrument` and the GUI is shared.

**7. Every departure taken from this spec is written down** in the module
docstring, with the reason. This spec already records three departures from
the original parameter document (section 4); the same discipline applies to
whatever the implementation has to change.

The list is already known, so the docstring starts with these seven:

1. **`even` rewritten** as weights-based, rather than the mask family's
   placement-time bypass — a bypass would discard three of the four weight
   factors (section 4).
2. **`reference_mask` duplicates `chord_hit_mask`'s intent deliberately** —
   fractional vs. boolean; `MI_Bass_Instrument.py` left untouched
   (section 1.5).
3. **`DRUM_COUPLING_BOOST` separate from the bass's `COUPLING_BOOST`** —
   continuous mask vs. boolean; expected to diverge under tuning
   (section 4).
4. **Zero hits per cell is not legal** — the inherited floor is kept and
   the limitation deferred with fills, because an all-`R` stream forces a
   decision about the dynamic key set (section 4).
5. **Drums omit the silent-measure repair** that chord and bass apply — a
   silent measure in one kit element is ordinary drumming (section 4).
6. **Section 5's crash-on-downbeat example is unreachable** without a
   metric term in variant selection (section 5).
7. **Bass defect at `place_bass_cell:385`** — a negative coefficient can
   zero a slot, violating never-forbids-a-slot. Noted, NOT fixed; out of
   scope and would put done-item 6 in play (section 4).

Plus whatever the implementation has to change on contact.

### Explicitly NOT part of done

Musical quality. First-pass output is expected to be structurally correct
and musically rough, exactly as the chord and bass engines were — taste
tuning is a separate later pass. Do not tune weights to make the output
sound better as part of this work; get the structure right and leave the
constants named so they can be tuned deliberately.

Also not part of done: fills, toms, ride, crash, the variant engine being
switched on, and anything touching the synthesizer.
