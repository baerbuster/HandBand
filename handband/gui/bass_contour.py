"""
Bass Contour GUI

A sibling of MI_Chord_Instrument_GUI, in the same visual style and driven
the same way: it renders the shared SongSource, so it shows the SAME song
as every other view, off the one live Input slider (via EMOTE). No sliders
of its own — the single system input drives valence/arousal like everywhere
else.

It plots the bass CONTOUR (MI_Bass_Instrument.bass_contour): the curve the
bass line rides, in SCALE DEGREES, one point per 16th-note slot across ONE
CELL. The cell repeats across the song, re-anchored to each chord, so what's
drawn here is the riff shape.

The vertical axis counts scale steps, not semitones: degree 1 is the tonic,
8 the octave above, -6 the octave below.

  - Valence tilts the line: descending when sad, ascending when happy, up
    to a full octave (7 degrees) of climb or fall across the cell.
  - Arousal sets the wiggle: a single slow bump when calm, up to jumping
    every 16th note when frantic, swinging up to an octave off the tilt.

Horizontal lines mark the octave above/below and the tonic (degree 1);
vertical lines mark the measures.

Run directly:  python3 MI_Bass_Contour_GUI.py
"""

import tkinter as tk
from tkinter import font as tkfont

from handband.mi.song_source import SongSource
from handband.mi.bass_instrument import CONTOUR_CENTER, DEGREES_PER_OCTAVE

SLOTS_PER_MEASURE = 16
PAD = 16
MARGIN = 40
PLOT_H = 300
Y_DEGREE_RANGE = 15          # plot spans +/- this many degrees around the tonic
SLOT_W = 10                  # horizontal pixels per 16th-note slot

BG = "#1e1e2e"
PANEL = "#242436"
GRID = "#45475a"
ZERO_LINE = "#cdd6f4"
OCTAVE_LINE = "#585b70"
CURVE = "#00bf63"
DOT = "#eafff4"
LABEL_FG = "#a6adc8"


class BassContourView:
    """
    Renders the bass contour from the shared SongSource, redrawing whenever
    the source's song changes — same live pipeline as the other views.
    """

    def __init__(self, master, source):
        self.master = master
        self.source = source
        self.last_key = None
        self.master.title("Bass Contour")
        self.master.config(bg=BG)

        self.small_font = tkfont.Font(family="Helvetica", size=10)
        self.readout_font = tkfont.Font(family="Helvetica", size=11, weight="bold")

        header = tk.Frame(master, bg=BG)
        header.pack(fill="x", padx=PAD, pady=(PAD, 6))
        tk.Label(header, text="Live input:", bg=BG, fg=LABEL_FG,
                 font=self.small_font).pack(side="left")
        self.readout = tk.Label(header, text="V —  A —", bg=BG, fg=CURVE,
                                font=self.readout_font)
        self.readout.pack(side="left", padx=(6, 16))
        tk.Label(header, text="scale degree  (1 = tonic, 8 = octave up)",
                 bg=BG, fg=LABEL_FG, font=self.small_font).pack(side="left")

        max_slots = SLOTS_PER_MEASURE * 8
        self.canvas = tk.Canvas(master, bg=PANEL, highlightthickness=0,
                                width=2 * MARGIN + max_slots * SLOT_W,
                                height=PLOT_H)
        self.canvas.pack(anchor="w", padx=PAD, pady=(0, PAD))

        self.poll_live_input()

    def poll_live_input(self):
        song = self.source.poll()
        self.readout.config(text=f"V {song['valence']:+.2f}   A {song['arousal']:.2f}")
        if song['key'] != self.last_key:
            self.last_key = song['key']
            self.draw(song['bass_contour'])
        self.master.after(100, self.poll_live_input)

    def _y(self, degree):
        """Vertical pixel for a scale degree, with the tonic in the middle."""
        span = PLOT_H - 2 * MARGIN
        frac = (degree - CONTOUR_CENTER + Y_DEGREE_RANGE) / (2 * Y_DEGREE_RANGE)
        return PLOT_H - MARGIN - frac * span

    def draw(self, curve):
        c = self.canvas
        c.delete("all")
        n_slots = len(curve)
        if n_slots == 0:
            return
        x = lambda i: MARGIN + i * SLOT_W
        plot_right = x(n_slots - 1)

        # Horizontal reference lines: the octave above, the tonic, the
        # octave below — labelled by scale degree (8 / 1 / -6).
        for degree, color, width in [(CONTOUR_CENTER + DEGREES_PER_OCTAVE,
                                      OCTAVE_LINE, 1),
                                     (CONTOUR_CENTER, ZERO_LINE, 2),
                                     (CONTOUR_CENTER - DEGREES_PER_OCTAVE,
                                      OCTAVE_LINE, 1)]:
            y = self._y(degree)
            c.create_line(MARGIN, y, plot_right, y, fill=color, width=width)
            c.create_text(MARGIN - 6, y, text=f"{degree:d}", anchor="e",
                          fill=LABEL_FG, font=self.small_font)

        # Vertical measure lines.
        n_measures = n_slots // SLOTS_PER_MEASURE
        for m in range(n_measures + 1):
            slot = min(m * SLOTS_PER_MEASURE, n_slots - 1)
            c.create_line(x(slot), MARGIN, x(slot), PLOT_H - MARGIN,
                          fill=GRID, width=1)

        # The contour: a smooth polyline with a dot per 16th-note slot.
        pts = [(x(i), self._y(curve[i])) for i in range(n_slots)]
        if len(pts) >= 2:
            flat = [coord for xy in pts for coord in xy]
            c.create_line(*flat, fill=CURVE, width=2, smooth=True)
        for px, py in pts:
            c.create_oval(px - 2, py - 2, px + 2, py + 2, fill=DOT, outline="")

        lo, hi = min(curve), max(curve)
        c.create_text(plot_right, MARGIN - 6,
                      text=f"degree {lo:+.1f} to {hi:+.1f}", anchor="e",
                      fill=LABEL_FG, font=self.small_font)


def attach_to(parent, source):
    """Open the bass contour view as its own window, driven by the shared
    SongSource so it stays in sync with the other views."""
    window = tk.Toplevel(parent)
    return BassContourView(window, source)


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
