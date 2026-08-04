"""
Groove/Delay Engine

Phase 4 of Musical Intelligence (Tier 3). The independent
other half of the rhythmic layer, alongside the Accent
Pattern Engine.

Unlike the chord and accent engines, this one does NOT build
form. A groove is a repeating *feel*, not a structure that
evolves — if it changed section to section it wouldn't groove.
So the engine produces exactly ONE measure of timing feel:
a flat 16-value displacement vector that any instrument may
choose to apply to every measure it plays (or ignore).

Each of the 16 entries is a signed timing offset, expressed as
a fraction of a 16th-note slot:
    0        = hit lands on the grid
    positive = hit lays back, behind the beat  (pull)
    negative = hit rushes, on top of the beat   (push)

The emotional roles (valence and arousal come straight from
EMOTE and are treated as independent dimensions here):

  arousal [0,1]  — the entire intensity engine. It sets both
                   HOW MANY slots get displaced (density) and
                   HOW FAR each one moves (magnitude). At the
                   neutral center arousal is 0, so the groove
                   is empty — everything sits on the grid.

  valence [-1,1] — contributes only the SIGN, i.e. direction.
                   Positive valence pulls (laid back, behind);
                   negative valence pushes (anxious, on top).

The pipeline:
  1. groove_density        — how many of the 16 slots move
  2. choose_groove_archetype — a placement shape + its capacity
  3. apply_groove_archetype — drop the displacements into slots,
     each carrying sign(valence) × arousal × MAX_DELAY

Future work (not now): per-hit sin()/cos() stochasticism so
displaced hits vary instead of sharing one uniform magnitude.
"""

from handband.mi.pattern_primitives import (
    weighted_choice, density_calculator, archetype_placer,
)
import random

SLOTS_PER_MEASURE = 16
MAX_DELAYS_PER_MEASURE = 8    # b — density scalar (max displaced slots)
MAX_DELAY = 0.33              # cap on the shift, as a fraction of a slot


def groove_density_calculator(arousal):
    """
    How many of the measure's 16 slots get displaced: b * arousal.

    Minimum is 0 — at the neutral center (arousal 0) the groove is
    genuinely empty and every hit sits on the grid.
    """
    return density_calculator(1 * SLOTS_PER_MEASURE, MAX_DELAYS_PER_MEASURE / SLOTS_PER_MEASURE,
                              arousal, minimum=0)


def groove_archetype_calculator():
    """Pick a placement shape for the displaced slots. Flat random."""
    return weighted_choice(
        ["front", "back", "center", "alternating", "even", "random"],
        [1, 1, 1, 1, 1, 1],
    )


def choose_groove_archetype(slots):
    """
    Pick a placement shape and build its slot-weight layout.

    Returns the archetype name, its weight vector, and its capacity —
    the number of slots actually open for a displacement (non-zero
    weight). Some archetypes (e.g. alternating) leave slots empty, so
    the caller clamps its displacement count to this capacity before
    placing, so nothing overflows the layout.

    "even" is a special case: its hits are spread by regular spacing
    at placement time rather than by weighted draw, so every slot is
    nominally open (capacity = slots).
    """
    archetype = groove_archetype_calculator()
    if archetype == "front":
        weights = [slots - i for i in range(slots)]
    elif archetype == "back":
        weights = [slots + i for i in range(slots)]
    elif archetype == "center":
        mid = slots / 2
        weights = [mid - abs(i - mid) for i in range(slots)]
    elif archetype == "alternating":
        start = random.randint(0, 1)
        weights = [1 if i % 2 == start else 0 for i in range(slots)]
    elif archetype == "random":
        weights = [1 for i in range(slots)]
    elif archetype == "even":
        weights = [1 for i in range(slots)]

    capacity = sum(1 for w in weights if w > 0)
    return archetype, weights, capacity


def displacement_value(valence, arousal):
    """
    The signed timing offset every displaced hit carries, as a
    fraction of a slot: sign(valence) × arousal × MAX_DELAY.

    Positive valence -> positive offset (pull / behind the beat).
    Negative valence -> negative offset (push / on top of the beat).
    Valence exactly 0 -> 0 (no direction).
    """
    direction = (valence > 0) - (valence < 0)   # sign(valence): +1, -1, or 0
    return direction * arousal * MAX_DELAY


def apply_groove_archetype(slots, n_delays, archetype, weights, valence, arousal):
    """
    Place n_delays displacements into the measure's 16th-note slots
    and return the displacement vector (0 where a hit sits on the
    grid, signed offset where it moves).

    "even" spreads the hits at regular spacing (first on the downbeat);
    every other archetype draws positions from its weight vector
    without replacement. The count is already clamped to the layout's
    capacity upstream. All displaced slots share one uniform offset.
    """
    if n_delays <= 0:
        return [0.0] * slots
    if archetype == "even":
        positions = [int(i * slots / n_delays) for i in range(n_delays)]
    else:
        positions = archetype_placer(n_delays, weights, list(range(slots)))
    offset = displacement_value(valence, arousal)
    hits = set(positions)
    return [offset if i in hits else 0.0 for i in range(slots)]


def create_groove_pattern(valence, arousal):
    """
    Main entry point. Takes valence and arousal, returns one measure
    of groove as a flat 16-value signed-displacement vector (fraction
    of a 16th-note slot per entry). Instruments apply it per measure
    or ignore it.
    """
    density = groove_density_calculator(arousal)
    archetype, weights, capacity = choose_groove_archetype(SLOTS_PER_MEASURE)
    n = min(density, capacity)
    return apply_groove_archetype(SLOTS_PER_MEASURE, n, archetype, weights, valence, arousal)


if __name__ == "__main__":
    for inp in [0.0, 0.3, -0.5, 0.8, -1.0, 1.0]:
        valence = inp
        arousal = abs(inp) ** 2.0
        groove = create_groove_pattern(valence, arousal)
        cells = " ".join(f"{v:+.2f}" if v else "  .  " for v in groove)
        moved = sum(1 for v in groove if v)
        print(f"input={inp:+.1f}  valence={valence:+.2f} arousal={arousal:.2f}  moved={moved}")
        print("  ", cells)
        print()
