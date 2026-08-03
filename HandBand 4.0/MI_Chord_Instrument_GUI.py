"""
Chord Instrument GUI

A sibling of MI_Chord_Progression_GUI, in the same visual style, but it
renders the CHORD INSTRUMENT's performance chart rather than the raw
progression. Where the progression view shows which chord is *available*
at each slot, this shows what the player actually *does*:

  - a bright cell where the chord is STRUCK (a hit), with the chord name
  - a dimmer green cell where that chord is SUSTAINED (continue)
  - an empty cell where the player RESTS

So you can see the instrument's rhythm — its density, its syncopation,
and its staccato/legato articulation — laid over the same 16th-note grid
as the progression. Driven by the same live valence/arousal.

Run directly:  python3 MI_Chord_Instrument_GUI.py
"""

import tkinter as tk
from tkinter import font as tkfont

from MI_Song_Source import SongSource

SLOTS_PER_MEASURE = 16
SLOTS_PER_BEAT = 4
MAX_MEASURES = 8
MEASURES_PER_ROW = 2
CELL_W = 18
CELL_H = 46
ROW_GAP = 28
PAD = 16
GRID_M = 3
MEASURE_LINE_W = 3
BEAT_LINE_W = 1

BG = "#1e1e2e"
REST_BG = "#242436"           # a slot the player rests on
HIT_BG = "#00bf63"            # a struck chord (hit onset)
SUSTAIN_BG = "#1f7a4d"        # the same chord still ringing (continue)
CHORD_FG = "#0d0d14"
ONSET_MARK = "#eafff4"        # bright left edge marking each strike
MEASURE_LINE = "#cdd6f4"
BEAT_LINE = "#45475a"
LABEL_FG = "#a6adc8"


class ChordInstrumentView:
    """
    Renders the chord instrument's realized part, driven by the shared
    SongSource so it shows the SAME song as the progression view. It
    redraws whenever the source's song changes.
    """

    def __init__(self, master, source):
        self.master = master
        self.source = source
        self.last_key = None
        self.master.title("Chord Instrument")
        self.master.config(bg=BG)

        self.chord_fonts = [tkfont.Font(family="Helvetica", size=s, weight="bold")
                            for s in (12, 11, 10, 9, 8, 7)]
        self.small_font = tkfont.Font(family="Helvetica", size=10)
        self.readout_font = tkfont.Font(family="Helvetica", size=11, weight="bold")

        header = tk.Frame(master, bg=BG)
        header.pack(fill="x", padx=PAD, pady=(PAD, 6))
        tk.Label(header, text="Live input:", bg=BG, fg=LABEL_FG,
                 font=self.small_font).pack(side="left")
        self.readout = tk.Label(header, text="V —  A —", bg=BG, fg=HIT_BG,
                                font=self.readout_font)
        self.readout.pack(side="left", padx=(6, 16))
        tk.Label(header, text="■ hit", bg=BG, fg=HIT_BG,
                 font=self.small_font).pack(side="left")
        tk.Label(header, text="■ sustain", bg=BG, fg=SUSTAIN_BG,
                 font=self.small_font).pack(side="left", padx=(8, 0))

        max_rows = (MAX_MEASURES + MEASURES_PER_ROW - 1) // MEASURES_PER_ROW
        col_stride = SLOTS_PER_MEASURE * CELL_W + MEASURE_LINE_W + 12
        edge = MEASURE_LINE_W + 2
        grid_w = GRID_M + (MEASURES_PER_ROW - 1) * col_stride \
            + SLOTS_PER_MEASURE * CELL_W + edge
        grid_h = 18 + max_rows * (CELL_H + ROW_GAP)

        self.canvas = tk.Canvas(master, bg=BG, highlightthickness=0,
                                width=grid_w, height=grid_h)
        self.canvas.pack(anchor="w", padx=PAD, pady=(0, PAD))

        self.poll_live_input()

    def poll_live_input(self):
        song = self.source.poll()
        self.readout.config(text=f"V {song['valence']:+.2f}   A {song['arousal']:.2f}")
        if song['key'] != self.last_key:
            self.last_key = song['key']
            self.draw(song['chord_part'])
        self.master.after(100, self.poll_live_input)

    def fit_chord_font(self, text, max_w):
        for font in self.chord_fonts:
            if font.measure(text) <= max_w:
                return font
        return self.chord_fonts[-1]

    def draw(self, part):
        c = self.canvas
        c.delete("all")
        n_measures = len(part) // SLOTS_PER_MEASURE

        for m in range(n_measures):
            row = m // MEASURES_PER_ROW
            col = m % MEASURES_PER_ROW
            x0 = GRID_M + col * (SLOTS_PER_MEASURE * CELL_W + MEASURE_LINE_W + 12)
            y0 = 18 + row * (CELL_H + ROW_GAP)
            m_start = m * SLOTS_PER_MEASURE

            c.create_text(x0 + 2, y0 - 12, text=f"m{m + 1}",
                          anchor="w", fill=LABEL_FG, font=self.small_font)

            # 1) per-slot backgrounds: hit / sustain / rest
            for s in range(SLOTS_PER_MEASURE):
                sym, _chord = part[m_start + s]
                fill = {"H": HIT_BG, "C": SUSTAIN_BG, "R": REST_BG}[sym]
                cx0 = x0 + s * CELL_W
                c.create_rectangle(cx0, y0, cx0 + CELL_W, y0 + CELL_H,
                                   fill=fill, outline="")
                # faint beat separators
                if s % SLOTS_PER_BEAT == 0 and s != 0:
                    c.create_line(cx0, y0, cx0, y0 + CELL_H,
                                  fill=BEAT_LINE, width=BEAT_LINE_W)

            # 2) strike onset markers + chord names centered over each
            #    hit's sounding run within this measure
            s = 0
            while s < SLOTS_PER_MEASURE:
                sym, chord = part[m_start + s]
                if sym != "H":
                    s += 1
                    continue
                # extend over the sustain of this same strike
                e = s + 1
                while e < SLOTS_PER_MEASURE and part[m_start + e][0] == "C":
                    e += 1
                onset_x = x0 + s * CELL_W
                c.create_line(onset_x, y0, onset_x, y0 + CELL_H,
                              fill=ONSET_MARK, width=2)
                cxm = x0 + (s + e) / 2 * CELL_W
                label = chord if chord is not None else ""
                font = self.fit_chord_font(label, (e - s) * CELL_W - 4)
                c.create_text(cxm, y0 + CELL_H / 2, text=label,
                              fill=CHORD_FG, font=font)
                s = e

            # bold measure boundary lines
            right = x0 + SLOTS_PER_MEASURE * CELL_W
            for lx in (x0, right):
                c.create_line(lx, y0, lx, y0 + CELL_H,
                              fill=MEASURE_LINE, width=MEASURE_LINE_W)


def attach_to(parent, source):
    """Open the chord instrument view as its own window, driven by the
    shared SongSource so it stays in sync with the other views."""
    window = tk.Toplevel(parent)
    return ChordInstrumentView(window, source)


def main():
    """Standalone launch on the real Input + EMOTE pipeline."""
    from input import Input
    from emote import EMOTE

    input_val = Input()
    emote = EMOTE()
    source = SongSource(lambda: emote.transform(input_val.get_input_value()))
    attach_to(input_val.window, source)
    input_val.window.mainloop()


if __name__ == "__main__":
    main()
