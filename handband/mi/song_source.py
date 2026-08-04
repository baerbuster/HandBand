"""
Song Source

A single shared source of the CURRENT song, so every view (the
progression window, the chord-instrument window, ...) renders the same
generated song instead of each rolling its own. Generation is
stochastic, so without this two windows on the same input would show
unrelated songs.

Given a valence/arousal provider, it generates the whole song bundle
ONCE per input change and caches it. Every view polls the same instance;
the bundle carries a 'key' so a view knows when to redraw.
"""

from handband.mi.chord_progression_engine import create_song_form, create_chord_progression
from handband.mi.accent_pattern_engine import create_accent_pattern
from handband.mi.groove_delay_engine import create_groove_pattern
from handband.mi.chord_instrument import (default_chord_instrument,
                                 create_chord_instrument_part,
                                 realize_chord_notes)
from handband.mi.bass_instrument import (bass_cell_measures, default_bass_instrument,
                                create_bass_pattern_cell, realize_bass_notes,
                                bass_degree_stream)
from handband.mi.drum_instrument import default_drum_instrument, create_drum_part


class SongSource:
    """
    Wraps a live valence/arousal provider and produces one consistent
    song for all views. Regenerates only when the input actually
    changes, so views stay both live and in sync.
    """

    def __init__(self, va_provider):
        self.va_provider = va_provider
        self._key = None
        self._bundle = None
        # One persistent chord instrument, so the rhythm and the realized
        # notes are produced by the same player each generation.
        self.chord_instrument = default_chord_instrument()
        self.bass_instrument = default_bass_instrument()
        self.drum_instrument = default_drum_instrument()

    def poll(self):
        """
        Return the current song bundle, regenerating only when the
        valence/arousal input changes. Views compare the bundle's 'key'
        against the last one they drew to decide whether to redraw.
        """
        va = self.va_provider()
        v, a = va["valence"], va["arousal"]
        key = (round(v, 3), round(a, 3))
        if key != self._key:
            self._key = key
            form = create_song_form(v, a)
            length, _density, rep = form
            progression = create_chord_progression(v, a, form)
            accents = create_accent_pattern(length, a, rep)
            groove = create_groove_pattern(v, a)
            part = create_chord_instrument_part(v, a, progression,
                                                self.chord_instrument)
            # The realized performance stream the sequencer will read:
            # per slot, ("H", notes/accent/timing) / C / R.
            chord_sequence = realize_chord_notes(part, a, self.chord_instrument,
                                                 accents, groove)
            # The bass, in one call so the rhythm, the contour, and the
            # line built from them all come from the SAME generation —
            # both the rhythm and the contour are stochastic, so a view
            # drawing a separately-generated contour would be showing a
            # curve the line never followed.
            #
            # The contour is ONE CELL long, the same length as the rhythm
            # cell, and repeats across the song. The cell is one cell of
            # bass line in symbolic scale degrees, still KEY-relative —
            # pointing the degrees at the sounding chord comes later.
            cell_measures = bass_cell_measures(progression)
            bass_rhythm, bass_curve, bass_cell = create_bass_pattern_cell(
                v, a, progression, part, self.bass_instrument)
            # Tier 4: point the key-relative degree cell at the sounding
            # chords and resolve it to concrete MIDI for the whole song, with
            # accent/groove folded in the same way as the chord instrument —
            # so bass_sequence and chord_sequence are the SAME per-slot shape.
            # Holds crossing a chord change are re-struck on the new chord's
            # harmonic degree, so this stream carries a few more attacks than
            # bass_rhythm.
            bass_sequence = realize_bass_notes(bass_rhythm, bass_cell,
                                               progression, a,
                                               self.bass_instrument,
                                               accents, groove)
            # The symbolic degree sounding at each slot (retriggers included),
            # aligned 1:1 with bass_sequence. Views use it to LABEL the line
            # (the concrete MIDI is in bass_sequence); it carries no pitch.
            bass_degrees = bass_degree_stream(bass_rhythm, bass_cell,
                                              progression)
            # The kit: a dict of per-slot streams keyed by sound (kick/
            # snare/hat for now — the key set is dynamic), each stream
            # the SAME per-slot shape as chord_sequence/bass_sequence.
            # The kick couples to the bass RHYTHM, not bass_sequence,
            # whose chord-change retriggers follow harmony, not the cell.
            drum_sequence = create_drum_part(v, a, progression, accents,
                                             groove, {"bass": bass_rhythm},
                                             self.drum_instrument)
            self._bundle = {
                "key": key,
                "valence": v,
                "arousal": a,
                "form": form,
                "progression": progression,
                "accents": accents,
                "groove": groove,
                "chord_part": part,
                "chord_sequence": chord_sequence,
                "bass_cell_measures": cell_measures,
                "bass_rhythm": bass_rhythm,
                "bass_contour": bass_curve,
                "bass_cell": bass_cell,
                "bass_sequence": bass_sequence,
                "bass_degrees": bass_degrees,
                "drum_sequence": drum_sequence,
            }
        return self._bundle
