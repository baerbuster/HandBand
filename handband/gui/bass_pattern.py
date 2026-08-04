"""
Bass Pattern GUI

A sibling of MI_Bass_Contour_GUI, in the same visual style and driven the
same way: it renders the shared SongSource, so it shows the SAME song as
every other view, off the one live Input slider (via EMOTE).

Where the contour window draws the raw CURVE, this one draws the finished
PATTERN CELL — the bass line that relative pattern construction built by
folding the H/C/X rhythm together with that curve. One cell, the thing
that repeats.

Each slot is one 16th note:

  H   a struck note, drawn as a dot at its scale degree and labelled
  C   the note is still sounding, drawn as a bar continuing from the hit
  X   silence, drawn as nothing

Degrees are shown in the symbolic numbering (8..1, then -7..-1 below the
tonic). Because that numbering isn't monotonic — -7 sits just BELOW 1, and
-1 is the octave below — the vertical POSITION comes from the raw step
count and only the LABEL is symbolic. Otherwise the line would jump around
the screen in places where the pitch moves smoothly.

The degrees are key-relative: degree 1 is the tonic of the key. They are
not yet pointed at whatever chord is sounding.

Run directly:  python3 MI_Bass_Pattern_GUI.py
"""

import tkinter as tk
from tkinter import font as tkfont

from handband.mi.song_source import SongSource
from handband.mi.bass_instrument import (CONTOUR_CENTER, DEGREES_PER_OCTAVE,
                                from_symbolic_degree)

SLOTS_PER_MEASURE = 16
PAD = 16
MARGIN = 40
PLOT_H = 320
Y_DEGREE_RANGE = 9           # plot spans +/- this many steps around the tonic
SLOT_W = 34                  # horizontal pixels per 16th-note slot

BG = "#1e1e2e"
PANEL = "#242436"
GRID = "#45475a"
ZERO_LINE = "#cdd6f4"
OCTAVE_LINE = "#585b70"
HELD = "#00bf63"             # the sustain bar
DOT = "#eafff4"              # the struck note
REST = "#45475a"
LABEL_FG = "#a6adc8"


class BassPatternView:
    """
    Renders the bass pattern cell from the shared SongSource, redrawing
    whenever the source's song changes — same live pipeline as the other
    views.
    """

    def __init__(self, master, source):
        self.master = master
        self.source = source
        self.last_key = None
        self.master.title("Bass Pattern")
        self.master.config(bg=BG)

        self.small_font = tkfont.Font(family="Helvetica", size=10)
        self.degree_font = tkfont.Font(family="Helvetica", size=10, weight="bold")
        self.readout_font = tkfont.Font(family="Helvetica", size=11, weight="bold")

        header = tk.Frame(master, bg=BG)
        header.pack(fill="x", padx=PAD, pady=(PAD, 6))
        tk.Label(header, text="Live input:", bg=BG, fg=LABEL_FG,
                 font=self.small_font).pack(side="left")
        self.readout = tk.Label(header, text="V —  A —", bg=BG, fg=HELD,
                                font=self.readout_font)
        self.readout.pack(side="left", padx=(6, 16))
        self.info = tk.Label(header, text="", bg=BG, fg=LABEL_FG,
                             font=self.small_font)
        self.info.pack(side="left")

        max_slots = SLOTS_PER_MEASURE * 4
        self.canvas = tk.Canvas(master, bg=PANEL, highlightthickness=0,
                                width=2 * MARGIN + max_slots * SLOT_W,
                                height=PLOT_H)
        self.canvas.pack(anchor="w", padx=PAD, pady=(0, PAD))

        self.poll_live_input()

    def poll_live_input(self):
        song = self.source.poll()
        self.readout.config(
            text=f"V {song['valence']:+.2f}   A {song['arousal']:.2f}")
        if song['key'] != self.last_key:
            self.last_key = song['key']
            self.draw(song['bass_cell'], song['bass_cell_measures'])
        self.master.after(100, self.poll_live_input)

    def _y(self, step):
        """Vertical pixel for a RAW step count, tonic in the middle."""
        span = PLOT_H - 2 * MARGIN
        frac = (step - CONTOUR_CENTER + Y_DEGREE_RANGE) / (2 * Y_DEGREE_RANGE)
        return PLOT_H - MARGIN - frac * span

    def draw(self, cell, cell_measures):
        c = self.canvas
        c.delete("all")
        n_slots = len(cell)
        if n_slots == 0:
            return

        x = lambda i: MARGIN + i * SLOT_W
        plot_right = x(n_slots)

        hits = sum(1 for sym, _d in cell if sym == "H")
        held = sum(1 for sym, _d in cell if sym == "C")
        rests = sum(1 for sym, _d in cell if sym == "X")
        self.info.config(text=f"cell {cell_measures}m — {hits} hit"
                              f"{'' if hits == 1 else 's'}, "
                              f"{held} held, {rests} silent   "
                              f"(degree 1 = tonic)")

        # Horizontal reference lines: octave above, tonic, octave below,
        # positioned by raw step but labelled with the symbolic degree.
        for step, label, color, width in [
                (CONTOUR_CENTER + DEGREES_PER_OCTAVE, "8", OCTAVE_LINE, 1),
                (CONTOUR_CENTER, "1", ZERO_LINE, 2),
                (CONTOUR_CENTER - DEGREES_PER_OCTAVE, "-1", OCTAVE_LINE, 1)]:
            y = self._y(step)
            c.create_line(MARGIN, y, plot_right, y, fill=color, width=width)
            c.create_text(MARGIN - 8, y, text=label, anchor="e",
                          fill=LABEL_FG, font=self.small_font)

        # Vertical measure lines.
        for m in range(cell_measures + 1):
            slot = min(m * SLOTS_PER_MEASURE, n_slots)
            c.create_line(x(slot), MARGIN, x(slot), PLOT_H - MARGIN,
                          fill=GRID, width=1)

        # The line itself. A hit is a dot at its degree; the C slots after
        # it extend a bar at that same height until the note stops.
        current_step = None
        for i, (sym, degree) in enumerate(cell):
            slot_l, slot_r = x(i), x(i + 1)
            if sym == "H":
                current_step = from_symbolic_degree(degree)
                y = self._y(current_step)
                c.create_line(slot_l + 3, y, slot_r - 3, y, fill=HELD, width=4)
                c.create_oval(slot_l - 1, y - 5, slot_l + 9, y + 5,
                              fill=DOT, outline="")
                c.create_text((slot_l + slot_r) / 2, y - 15, text=str(degree),
                              fill=DOT, font=self.degree_font)
            elif sym == "C" and current_step is not None:
                y = self._y(current_step)
                c.create_line(slot_l, y, slot_r - 3, y, fill=HELD, width=4)
            else:
                current_step = None
                y = PLOT_H - MARGIN + 10
                c.create_line(slot_l + 4, y, slot_r - 4, y, fill=REST, width=2)

        # Slot ruler along the bottom: beat numbers within each measure.
        for i in range(n_slots):
            if i % 4 == 0:
                c.create_text(x(i) + SLOT_W / 2, PLOT_H - MARGIN + 24,
                              text=str(i % SLOTS_PER_MEASURE // 4 + 1),
                              fill=LABEL_FG, font=self.small_font)


def attach_to(parent, source):
    """Open the bass pattern view as its own window, driven by the shared
    SongSource so it stays in sync with the other views."""
    window = tk.Toplevel(parent)
    return BassPatternView(window, source)


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
