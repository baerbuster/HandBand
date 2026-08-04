"""
Band Score GUI

One window that shows the whole band stacked like sheet music: for every
measure, the CHORD instrument on top, the BASS under it, and the DRUMS at
the bottom, on the same 16th-note grid, so you can read at a glance what
each player is doing measure by measure.

  - Chord lane: each struck cell carries the CHORD NAME; sustains dim; rests
    empty.
  - Bass lane: each struck cell carries the SCALE DEGREE the bass plays,
    spelled by the CURRENT chord's mode (so a 3rd over ii reads "b3", not
    "3") with the concrete note name under it.
  - Drum lane: ONE lane the same height as the others, subdivided into thin
    rows the way drum tablature looks — cymbals on top, snare, kick on the
    bottom. Rows are built from the keys actually present in the drum
    package (the key set is dynamic), in a display order that slots ride
    and crash in correctly when variants are switched on. Glyphs follow tab
    convention: x for cymbals, o for snare/kick; an ACCENT capitalizes the
    glyph (X/O) and GROOVE nudges it left/right inside its cell,
    proportional to the timing offset — which is literally what groove is.

Both lanes also show, per strike, a simple read of the two expressive
layers:

  ›  (top, gold)   an ACCENT — this strike is emphasized (louder)
  ‹ / › (bottom, pink)  GROOVE — the strike is nudged AHEAD (‹, pushed) or
                        BEHIND (›, laid back) the grid

and a one-line summary per instrument in the header (accent depth + groove
feel), since accent and groove are per-instrument responses to the shared
band-wide maps.

Driven by the shared SongSource, so it always shows the SAME song as every
other view, off the one live Input slider (via EMOTE).

Run directly:  python3 -m handband.gui.score
"""

import tkinter as tk
from tkinter import font as tkfont

from handband.mi.song_source import SongSource
from handband.mi.chord_instrument import active_chords
from handband.mi.bass_modes import modal_degree_label
from handband.mi.instrument import MAX_ACCENT_DB
from handband.mi.global_parameters import CURRENT_KEY, calculate_global_parameters

SLOTS_PER_MEASURE = 16
SLOTS_PER_BEAT = 4
MEASURES_PER_ROW = 2

CELL_W = 16
LANE_H = 42
LANE_GAP = 3
LANE_LABEL = 15          # space above each measure block for "m1"
BLOCK_H = 3 * LANE_H + 2 * LANE_GAP    # chords + bass + drums
ROW_GAP = 26
COL_GAP = 22
LEFT_GUTTER = 26
TOP = 14
PAD = 16

BG = "#1e1e2e"
REST_BG = "#242436"
CHORD_HIT = "#00bf63"
CHORD_SUS = "#1f7a4d"
BASS_HIT = "#89b4fa"
BASS_SUS = "#39406b"
HIT_TEXT = "#0d0d14"
ONSET = "#eafff4"
ACCENT_MARK = "#f9e2af"       # gold
GROOVE_MARK = "#f5c2e7"       # pink
MEASURE_LINE = "#cdd6f4"
BEAT_LINE = "#45475a"
LABEL_FG = "#a6adc8"
DRUM_HIT = "#fab387"          # the drum glyphs (orange)
DRUM_ROW_LINE = "#313244"     # faint separators between the tab rows

# The BPM window the header readout maps valence into (min/max BPM are
# configurable at the caller level, per mi/global_parameters.py).
SCORE_MIN_BPM = 60
SCORE_MAX_BPM = 180

# Drum tab rows, top to bottom: cymbals above snare above kick. Built from
# the keys actually present in the package (the key set is dynamic);
# unrecognized keys are appended, so future sounds still get a row.
DRUM_DISPLAY_ORDER = ["crash", "ride", "hi-hat", "hat", "snare", "kick"]
DRUM_ROW_LABELS = {"crash": "Cr", "ride": "Rd", "hi-hat": "Hh",
                   "hat": "Cy", "snare": "Sn", "kick": "Kk"}
DRUM_CYMBAL_KEYS = {"crash", "ride", "hi-hat", "hat"}   # glyph x; others o

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]


def _note_name(midi):
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def _groove_feel(timings):
    """One-word read of an instrument's groove from its per-strike offsets."""
    nonzero = [t for t in timings if t]
    if not nonzero:
        return "on grid"
    peak = max(abs(t) for t in nonzero)
    # All displaced hits share one sign (see the groove engine), so any is
    # enough to tell push from pull.
    direction = "laid back" if nonzero[0] > 0 else "pushed"
    return f"{direction} ≤{peak:.2f}"


class ScoreView:
    """
    Renders the chord + bass lanes together from the shared SongSource,
    redrawing whenever the source's song changes.
    """

    def __init__(self, master, source):
        self.master = master
        self.source = source
        self.last_key = None
        self.master.title("Band Score")
        self.master.config(bg=BG)

        self.label_fonts = [tkfont.Font(family="Helvetica", size=s, weight="bold")
                            for s in (12, 11, 10, 9, 8, 7)]
        self.tiny_font = tkfont.Font(family="Helvetica", size=8)
        self.mark_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self.small_font = tkfont.Font(family="Helvetica", size=10)
        self.readout_font = tkfont.Font(family="Helvetica", size=11, weight="bold")

        header = tk.Frame(master, bg=BG)
        header.pack(fill="x", padx=PAD, pady=(PAD, 2))
        tk.Label(header, text="Live input:", bg=BG, fg=LABEL_FG,
                 font=self.small_font).pack(side="left")
        self.readout = tk.Label(header, text="V —  A —", bg=BG, fg=CHORD_HIT,
                                font=self.readout_font)
        self.readout.pack(side="left", padx=(6, 16))
        tk.Label(header, text="› accent", bg=BG, fg=ACCENT_MARK,
                 font=self.small_font).pack(side="left")
        tk.Label(header, text="‹ ahead  › behind  (groove)", bg=BG,
                 fg=GROOVE_MARK, font=self.small_font).pack(side="left", padx=(10, 0))

        summary = tk.Frame(master, bg=BG)
        summary.pack(fill="x", padx=PAD, pady=(0, 6))
        self.chord_summary = tk.Label(summary, text="", bg=BG, fg=CHORD_HIT,
                                      font=self.small_font)
        self.chord_summary.pack(anchor="w")
        self.bass_summary = tk.Label(summary, text="", bg=BG, fg=BASS_HIT,
                                     font=self.small_font)
        self.bass_summary.pack(anchor="w")
        # One summary line per drum ELEMENT — accent_follow/groove_follow
        # are per-element parameters, so each gets its own readout.
        self.drum_summaries = {}
        for el in source.drum_instrument.elements:
            label = tk.Label(summary, text="", bg=BG, fg=DRUM_HIT,
                             font=self.small_font)
            label.pack(anchor="w")
            self.drum_summaries[el.name] = label

        self.canvas = tk.Canvas(master, bg=BG, highlightthickness=0)
        self.canvas.pack(anchor="w", padx=PAD, pady=(0, PAD))

        self.poll_live_input()

    def poll_live_input(self):
        song = self.source.poll()
        # BPM and key in the readout — the chart is unreadable as a band
        # part without them.
        bpm = calculate_global_parameters(song['valence'],
                                          SCORE_MIN_BPM, SCORE_MAX_BPM)
        self.readout.config(
            text=f"V {song['valence']:+.2f}   A {song['arousal']:.2f}   "
                 f"{bpm:.0f} BPM   key {NOTE_NAMES[CURRENT_KEY]}")
        if song['key'] != self.last_key:
            self.last_key = song['key']
            self.draw(song)
        self.master.after(100, self.poll_live_input)

    def _fit_font(self, text, max_w):
        for font in self.label_fonts:
            if font.measure(text) <= max_w:
                return font
        return self.label_fonts[-1]

    def _lane_records(self, song):
        """Build the per-slot draw records for both lanes, aligned by slot."""
        chord_part = song['chord_part']
        chord_seq = song['chord_sequence']
        bass_seq = song['bass_sequence']
        bass_deg = song['bass_degrees']
        active = active_chords(song['progression'])

        chord = []
        bass = []
        for i in range(len(chord_part)):
            ct = chord_part[i][0]
            crec = {"type": ct, "accent": 0.0, "timing": 0.0,
                    "main": None, "sub": None}
            if ct == "H":
                crec["accent"] = chord_seq[i].get("accent", 0.0)
                crec["timing"] = chord_seq[i].get("timing", 0.0)
                crec["main"] = chord_part[i][1]
            chord.append(crec)

            bt = bass_seq[i]["type"]
            brec = {"type": bt, "accent": 0.0, "timing": 0.0,
                    "main": None, "sub": None}
            if bt == "H":
                brec["accent"] = bass_seq[i].get("accent", 0.0)
                brec["timing"] = bass_seq[i].get("timing", 0.0)
                brec["main"] = modal_degree_label(bass_deg[i][1], active[i])
                brec["sub"] = _note_name(bass_seq[i]["notes"][0])
            bass.append(brec)
        return chord, bass

    def _drum_streams(self, song):
        """The drum package's streams as an ordered (key, stream) list,
        cymbals above snare above kick, unrecognized keys appended."""
        seq = song['drum_sequence']
        ordered = [k for k in DRUM_DISPLAY_ORDER if k in seq]
        ordered += [k for k in seq if k not in DRUM_DISPLAY_ORDER]
        return [(k, seq[k]) for k in ordered]

    def draw(self, song):
        c = self.canvas
        c.delete("all")
        chord, bass = self._lane_records(song)
        drums = self._drum_streams(song)
        n_measures = len(chord) // SLOTS_PER_MEASURE

        # Per-instrument accent depth + groove feel summaries.
        ci, bi = self.source.chord_instrument, self.source.bass_instrument
        self.chord_summary.config(
            text=f"Chords  —  accent ≤{ci.accent_follow * MAX_ACCENT_DB:.1f} dB"
                 f"   ·   groove {_groove_feel([r['timing'] for r in chord])}")
        self.bass_summary.config(
            text=f"Bass    —  accent ≤{bi.accent_follow * MAX_ACCENT_DB:.1f} dB"
                 f"   ·   groove {_groove_feel([r['timing'] for r in bass])}")
        seq = song['drum_sequence']
        for el in self.source.drum_instrument.elements:
            # With variants off the element's stream shares its name; a
            # variant-split element shows its follow value instead.
            if el.name in seq:
                feel = _groove_feel([s.get("timing", 0.0)
                                     for s in seq[el.name]])
            else:
                feel = f"follow {el.groove_follow:.1f}"
            self.drum_summaries[el.name].config(
                text=f"{el.name.capitalize():<7} —  accent "
                     f"≤{el.accent_follow * MAX_ACCENT_DB:.1f} dB"
                     f"   ·   groove {feel}")

        rows = (n_measures + MEASURES_PER_ROW - 1) // MEASURES_PER_ROW
        grid_w = LEFT_GUTTER + MEASURES_PER_ROW * SLOTS_PER_MEASURE * CELL_W \
            + (MEASURES_PER_ROW - 1) * COL_GAP + 8
        grid_h = TOP + rows * (LANE_LABEL + BLOCK_H + ROW_GAP)
        c.config(width=grid_w, height=grid_h)

        for m in range(n_measures):
            row = m // MEASURES_PER_ROW
            col = m % MEASURES_PER_ROW
            x0 = LEFT_GUTTER + col * (SLOTS_PER_MEASURE * CELL_W + COL_GAP)
            y0 = TOP + LANE_LABEL + row * (LANE_LABEL + BLOCK_H + ROW_GAP)
            m_start = m * SLOTS_PER_MEASURE
            chord_y = y0
            bass_y = y0 + LANE_H + LANE_GAP
            drum_y = y0 + 2 * (LANE_H + LANE_GAP)

            c.create_text(x0 + 2, y0 - 8, text=f"m{m + 1}", anchor="w",
                          fill=LABEL_FG, font=self.small_font)
            if col == 0:
                c.create_text(LEFT_GUTTER - 8, chord_y + LANE_H / 2, text="C",
                              anchor="e", fill=CHORD_HIT, font=self.mark_font)
                c.create_text(LEFT_GUTTER - 8, bass_y + LANE_H / 2, text="B",
                              anchor="e", fill=BASS_HIT, font=self.mark_font)
                # Tiny stacked row labels in place of one lane letter.
                row_h = LANE_H / len(drums)
                for r, (key, _stream) in enumerate(drums):
                    label = DRUM_ROW_LABELS.get(key, key[:2].capitalize())
                    c.create_text(LEFT_GUTTER - 8,
                                  drum_y + (r + 0.5) * row_h, text=label,
                                  anchor="e", fill=DRUM_HIT,
                                  font=self.tiny_font)

            self._draw_lane(x0, chord_y, chord[m_start:m_start + SLOTS_PER_MEASURE],
                            CHORD_HIT, CHORD_SUS)
            self._draw_lane(x0, bass_y, bass[m_start:m_start + SLOTS_PER_MEASURE],
                            BASS_HIT, BASS_SUS)
            self._draw_drum_lane(x0, drum_y, drums, m_start)

    def _draw_drum_lane(self, x0, y0, drums, m_start):
        """One lane the same height as the others, subdivided into a thin
        tab row per drum stream. Reads the same per-slot record shape
        (type / accent / timing), one record list per stream. At this row
        height accent and groove marks fold INTO the glyph: accent
        capitalizes it, groove nudges it sideways inside its own cell."""
        c = self.canvas
        n_rows = len(drums)
        row_h = LANE_H / n_rows

        # 1) lane background + faint beat separators + row separators
        c.create_rectangle(x0, y0, x0 + SLOTS_PER_MEASURE * CELL_W,
                           y0 + LANE_H, fill=REST_BG, outline="")
        for s in range(1, SLOTS_PER_MEASURE):
            if s % SLOTS_PER_BEAT == 0:
                c.create_line(x0 + s * CELL_W, y0, x0 + s * CELL_W,
                              y0 + LANE_H, fill=BEAT_LINE, width=1)
        for r in range(1, n_rows):
            c.create_line(x0, y0 + r * row_h,
                          x0 + SLOTS_PER_MEASURE * CELL_W, y0 + r * row_h,
                          fill=DRUM_ROW_LINE, width=1)

        # 2) glyphs: x for cymbals, o for snare/kick; accent -> capital,
        #    groove -> horizontal nudge proportional to the timing offset
        for r, (key, stream) in enumerate(drums):
            base = "x" if key in DRUM_CYMBAL_KEYS else "o"
            ry = y0 + (r + 0.5) * row_h
            for s in range(SLOTS_PER_MEASURE):
                rec = stream[m_start + s]
                if rec["type"] != "H":
                    continue
                glyph = base.upper() if rec.get("accent", 0.0) > 0 else base
                nudge = rec.get("timing", 0.0) * CELL_W
                c.create_text(x0 + (s + 0.5) * CELL_W + nudge, ry,
                              text=glyph, fill=DRUM_HIT, font=self.tiny_font)

        # 3) bold measure boundary lines
        for lx in (x0, x0 + SLOTS_PER_MEASURE * CELL_W):
            c.create_line(lx, y0, lx, y0 + LANE_H, fill=MEASURE_LINE, width=2)

    def _draw_lane(self, x0, y0, recs, hit_c, sus_c):
        c = self.canvas

        # 1) per-slot backgrounds + faint beat separators
        for s, rec in enumerate(recs):
            fill = {"H": hit_c, "C": sus_c, "R": REST_BG}[rec["type"]]
            cx0 = x0 + s * CELL_W
            c.create_rectangle(cx0, y0, cx0 + CELL_W, y0 + LANE_H,
                               fill=fill, outline="")
            if s % SLOTS_PER_BEAT == 0 and s != 0:
                c.create_line(cx0, y0, cx0, y0 + LANE_H,
                              fill=BEAT_LINE, width=1)

        # 2) strike runs: onset mark, label, accent + groove marks
        s = 0
        while s < len(recs):
            if recs[s]["type"] != "H":
                s += 1
                continue
            e = s + 1
            while e < len(recs) and recs[e]["type"] == "C":
                e += 1
            onset_x = x0 + s * CELL_W
            c.create_line(onset_x, y0, onset_x, y0 + LANE_H,
                          fill=ONSET, width=2)

            main = recs[s]["main"] or ""
            sub = recs[s]["sub"]
            cxm = x0 + (s + e) / 2 * CELL_W
            font = self._fit_font(main, (e - s) * CELL_W - 3)
            if sub:
                c.create_text(cxm, y0 + LANE_H / 2 - 6, text=main,
                              fill=HIT_TEXT, font=font)
                c.create_text(cxm, y0 + LANE_H / 2 + 9, text=sub,
                              fill=HIT_TEXT, font=self.tiny_font)
            else:
                c.create_text(cxm, y0 + LANE_H / 2, text=main,
                              fill=HIT_TEXT, font=font)

            if recs[s]["accent"] > 0:
                c.create_text(onset_x + 3, y0 + 7, text="›", anchor="w",
                              fill=ACCENT_MARK, font=self.mark_font)
            tm = recs[s]["timing"]
            if tm:
                glyph = "‹" if tm < 0 else "›"
                c.create_text(onset_x + 3, y0 + LANE_H - 7, text=glyph,
                              anchor="w", fill=GROOVE_MARK, font=self.mark_font)
            s = e

        # 3) bold measure boundary lines
        for lx in (x0, x0 + SLOTS_PER_MEASURE * CELL_W):
            c.create_line(lx, y0, lx, y0 + LANE_H,
                          fill=MEASURE_LINE, width=2)


def attach_to(parent, source):
    """Open the band score view as its own window, driven by the shared
    SongSource so it stays in sync with the other views."""
    window = tk.Toplevel(parent)
    return ScoreView(window, source)


def main():
    """Standalone launch on the real Input + EMOTE pipeline."""
    from handband.input import Input
    from handband.emote import EMOTE

    input_val = Input()
    emote = EMOTE()
    source = SongSource(lambda: emote.transform(input_val.get_input_value()))
    attach_to(input_val.window, source)
    input_val.window.mainloop()


if __name__ == "__main__":
    main()
