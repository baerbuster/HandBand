"""
Chord Progression GUI

A small standalone window that renders the output of the
Phase 3 Chord Progression Engine.

The engine returns a flat list of 16th-note slots. Each slot is
either a Roman numeral (a chord onset) or "C" (the previous chord
continuing / no new chord). This view draws that list as a grid:

  - Measures are separated by a bold vertical line (16 slots each).
  - Slots with a chord onset show the Roman numeral.
  - Slots with no chord onset show a classic musical rest symbol
    (Unicode quarter rest), falling back to "X" if the font on this
    machine can't render it.

Beneath each measure's chord row is an aligned accent strip from the
Phase 4 Accent Pattern Engine — one cell per 16th-note slot, lit
(orange) where that slot is accented.

Below the whole grid is a single-measure groove strip from the Phase 4
Groove/Delay Engine. Because a groove is a repeating feel rather than a
form, only one measure is shown — it applies to every measure. Each
slot marks the timing offset for that hit: a marker pushed left of the
grid tick means the hit rushes (on top of the beat), pushed right means
it lays back (behind the beat), and the further from center the larger
the offset. All are driven off the same live valence/arousal.

Run directly:  python3 MI_Chord_Progression_GUI.py
"""

import tkinter as tk
from tkinter import font as tkfont

from MI_Groove_Delay_Engine import MAX_DELAY
from MI_Song_Source import SongSource

SLOTS_PER_MEASURE = 16
SLOTS_PER_BEAT = 4
MAX_MEASURES = 8              # longest progression the engine can produce
MEASURES_PER_ROW = 2          # wrap to a new row after this many measures
CELL_W = 18
CELL_H = 46
ACCENT_H = 14                 # height of the accent strip under each measure
ACCENT_GAP = 4                # gap between the chord row and the accent strip
ROW_GAP = 22
PAD = 16
GRID_M = 3                    # small internal margin inside the canvases
MEASURE_LINE_W = 3            # bold line between measures
BEAT_LINE_W = 1               # faint line between beats

BG = "#1e1e2e"
CELL_BG = "#2a2a3d"
CHORD_BG = "#00bf63"
CHORD_FG = "#0d0d14"
REST_FG = "#6c7086"
ACCENT_ON = "#f9a03f"         # accented 16th-note slot
ACCENT_OFF = "#222232"        # un-accented slot in the strip
MEASURE_LINE = "#cdd6f4"
BEAT_LINE = "#45475a"
LABEL_FG = "#a6adc8"

GROOVE_H = 40                 # height of the one-measure groove strip
GROOVE_TICK = "#313244"       # faint on-grid tick (off-beat slots)
GROOVE_PUSH = "#f38ba8"       # hit ahead of the beat  (rush / on top)
GROOVE_PULL = "#89b4fa"       # hit behind the beat    (lay back)

UNICODE_REST = "\U0001D13D"   # 𝄽  MUSICAL SYMBOL QUARTER REST


def pick_rest_glyph(root):
    """
    Return the classic Unicode quarter rest if it can be drawn on this
    machine, otherwise a plain "X" fallback.

    Tk's font.measure() is unreliable here: on macOS it reports the
    same "tofu" width for the rest as for an unassigned code point even
    though Core Text renders the real glyph via font fallback. So we do
    a live render test instead — draw the rest to an offscreen canvas
    and compare its bounding box against a known-missing glyph's box.
    If they differ, a real glyph was drawn.
    """
    probe = tkfont.Font(family="Helvetica", size=20)
    scratch = tk.Canvas(root)
    rest_id = scratch.create_text(0, 0, text=UNICODE_REST, font=probe)
    miss_id = scratch.create_text(0, 0, text="\U000FFFFF", font=probe)
    rest_box = scratch.bbox(rest_id)
    miss_box = scratch.bbox(miss_id)
    scratch.destroy()

    renders = bool(rest_box) and (miss_box is None or rest_box != miss_box)
    return UNICODE_REST if renders else "X"


class ChordProgressionView:
    """
    Renders a chord progression driven by the live emotional state of
    the main HandBand program.

    It does not own any valence/arousal controls of its own — those
    live in the main Input window, and it does not generate the song
    itself. Instead it takes a shared `SongSource` that all views poll,
    so every window renders the same generated song. It redraws whenever
    the source's song changes (staying put while the slider is idle).
    """

    def __init__(self, master, source):
        self.master = master
        self.source = source
        self.last_key = None
        self.master.title("Chord Progression")
        self.master.config(bg=BG)

        self.rest_glyph = pick_rest_glyph(master)
        # A ladder of chord-label fonts; draw() picks the largest that
        # fits a chord's held width so long names (IVmaj7, vii°ø9) never
        # overflow their block.
        self.chord_fonts = [tkfont.Font(family="Helvetica", size=s, weight="bold")
                            for s in (12, 11, 10, 9, 8, 7)]
        self.chord_font = self.chord_fonts[1]
        self.rest_font = tkfont.Font(family="Helvetica", size=13)
        self.small_font = tkfont.Font(family="Helvetica", size=10)
        self.readout_font = tkfont.Font(family="Helvetica", size=11, weight="bold")

        header = tk.Frame(master, bg=BG)
        header.pack(fill="x", padx=PAD, pady=(PAD, 6))
        tk.Label(header, text="Live input:", bg=BG, fg=LABEL_FG,
                 font=self.small_font).pack(side="left")
        self.readout = tk.Label(header, text="V —  A —", bg=BG, fg=CHORD_BG,
                                font=self.readout_font)
        self.readout.pack(side="left", padx=(6, 16))

        tk.Label(header, text="■ chord", bg=BG, fg=CHORD_BG,
                 font=self.small_font).pack(side="left")
        tk.Label(header, text="■ accent", bg=BG, fg=ACCENT_ON,
                 font=self.small_font).pack(side="left", padx=(8, 0))

        # Size the grid canvas once for the LONGEST progression (8
        # measures). Shorter progressions just leave the extra rows
        # blank, so the window never resizes as the length changes.
        block_h = CELL_H + ACCENT_GAP + ACCENT_H
        max_rows = (MAX_MEASURES + MEASURES_PER_ROW - 1) // MEASURES_PER_ROW
        col_stride = SLOTS_PER_MEASURE * CELL_W + MEASURE_LINE_W + 12
        edge = MEASURE_LINE_W + 2       # room for the bold boundary line width
        grid_w = GRID_M + (MEASURES_PER_ROW - 1) * col_stride \
            + SLOTS_PER_MEASURE * CELL_W + edge
        grid_h = 18 + max_rows * (block_h + ROW_GAP)

        self.canvas = tk.Canvas(master, bg=BG, highlightthickness=0,
                                width=grid_w, height=grid_h)
        self.canvas.pack(anchor="w", padx=PAD, pady=(0, 6))

        groove_header = tk.Frame(master, bg=BG)
        groove_header.pack(fill="x", padx=PAD, pady=(4, 2))
        tk.Label(groove_header, text="Groove — 1 measure, repeats",
                 bg=BG, fg=LABEL_FG, font=self.small_font).pack(side="left")
        tk.Label(groove_header, text="◄ push (on top)", bg=BG, fg=GROOVE_PUSH,
                 font=self.small_font).pack(side="left", padx=(16, 0))
        tk.Label(groove_header, text="pull (behind) ►", bg=BG, fg=GROOVE_PULL,
                 font=self.small_font).pack(side="left", padx=(8, 0))

        # One measure wide, pinned to the bottom-left corner.
        groove_w = GRID_M + SLOTS_PER_MEASURE * CELL_W + MEASURE_LINE_W + 6
        self.groove_canvas = tk.Canvas(master, bg=BG, highlightthickness=0,
                                       width=groove_w, height=GROOVE_H + 8)
        self.groove_canvas.pack(anchor="w", padx=PAD, pady=(0, PAD))

        self.poll_live_input()

    def poll_live_input(self):
        """
        Poll the shared song source. Update the readout every tick, and
        redraw only when the source's song actually changes — so it
        responds live but doesn't flicker while the slider is idle.
        """
        song = self.source.poll()
        self.readout.config(text=f"V {song['valence']:+.2f}   A {song['arousal']:.2f}")
        if song['key'] != self.last_key:
            self.last_key = song['key']
            self.draw(song['progression'], song['accents'])
            self.draw_groove(song['groove'])
        self.master.after(100, self.poll_live_input)

    def fit_chord_font(self, text, max_w):
        """Largest chord font whose rendered text fits within max_w px."""
        for font in self.chord_fonts:
            if font.measure(text) <= max_w:
                return font
        return self.chord_fonts[-1]

    def draw(self, progression, accents):
        c = self.canvas
        c.delete("all")

        block_h = CELL_H + ACCENT_GAP + ACCENT_H
        n_measures = len(progression) // SLOTS_PER_MEASURE

        # Chord sounding at each slot: carry an onset forward over its
        # "C" continuation slots, so we know each chord's held span.
        active = []
        current = None
        for slot in progression:
            if slot != "C":
                current = slot
            active.append(current)
        # Backfill any leading continuation slots (before the first onset)
        # into the first chord, so the row never opens with a stray rest.
        first = next((x for x in active if x is not None), None)
        for i in range(len(active)):
            if active[i] is None:
                active[i] = first
            else:
                break

        for m_index in range(n_measures):
            row = m_index // MEASURES_PER_ROW
            col = m_index % MEASURES_PER_ROW

            x0 = GRID_M + col * (SLOTS_PER_MEASURE * CELL_W + MEASURE_LINE_W + 12)
            y0 = 18 + row * (block_h + ROW_GAP)
            y_acc = y0 + CELL_H + ACCENT_GAP
            block_bottom = y_acc + ACCENT_H
            m_start = m_index * SLOTS_PER_MEASURE

            # measure number
            c.create_text(x0 + 2, y0 - 12, text=f"m{m_index + 1}",
                          anchor="w", fill=LABEL_FG, font=self.small_font)

            # Split the measure into chord blocks by grouping contiguous
            # slots that share the same sounding chord. A re-onset of the
            # same chord stays one block; each block gives its (possibly
            # long) name the full held width to render in.
            segments = []
            s = 0
            while s < SLOTS_PER_MEASURE:
                label = active[m_start + s]
                e = s + 1
                while e < SLOTS_PER_MEASURE and active[m_start + e] == label:
                    e += 1
                segments.append((s, e, label))
                s = e

            # 1) block backgrounds
            for s_i, e_i, label in segments:
                c.create_rectangle(x0 + s_i * CELL_W, y0, x0 + e_i * CELL_W,
                                   y0 + CELL_H,
                                   fill=CHORD_BG if label is not None else CELL_BG,
                                   outline="")

            # 2) accent strip (per-slot). Beat separators live here only,
            # so the chord row above stays clean.
            for s_index in range(SLOTS_PER_MEASURE):
                cx0 = x0 + s_index * CELL_W
                accented = accents[m_start + s_index] == 1
                c.create_rectangle(cx0, y_acc, cx0 + CELL_W, block_bottom,
                                   fill=ACCENT_ON if accented else ACCENT_OFF,
                                   outline="")
                if s_index % SLOTS_PER_BEAT == 0 and s_index != 0:
                    c.create_line(cx0, y_acc, cx0, block_bottom,
                                  fill=BEAT_LINE, width=BEAT_LINE_W)

            # 3) chord-block dividers (make adjacent green blocks distinct)
            for s_i, e_i, label in segments[1:]:
                dx = x0 + s_i * CELL_W
                c.create_line(dx, y0, dx, y0 + CELL_H, fill=BG, width=2)

            # 4) chord names LAST, centered in each block, on top of all
            for s_i, e_i, label in segments:
                if label is None:
                    continue
                cxm = x0 + (s_i + e_i) / 2 * CELL_W
                font = self.fit_chord_font(label, (e_i - s_i) * CELL_W - 6)
                c.create_text(cxm, y0 + CELL_H / 2, text=label,
                              fill=CHORD_FG, font=font)

            # bold vertical lines bounding this measure's block only
            right = x0 + SLOTS_PER_MEASURE * CELL_W
            for lx in (x0, right):
                c.create_line(lx, y0, lx, block_bottom,
                              fill=MEASURE_LINE, width=MEASURE_LINE_W)

    def draw_groove(self, groove):
        """
        Draw the single repeating groove measure as 16 slots. Each slot
        has an evenly-spaced center tick marking its on-grid position;
        the four downbeat ticks (every 4th slot) are brighter and full
        height so the beat structure reads at a glance. A displaced hit
        is a marker offset horizontally from its tick — left for a push
        (rushing), right for a pull (laying back) — by an amount scaled
        to the offset against MAX_DELAY. Slots with no offset show only
        the tick.
        """
        c = self.groove_canvas
        c.delete("all")

        x0 = GRID_M
        y0 = 4
        cy = y0 + GROOVE_H / 2
        cy_bottom = y0 + GROOVE_H
        max_shift = CELL_W / 2 - 2

        # single flat background behind all slots (no per-cell seams)
        c.create_rectangle(x0, y0, x0 + SLOTS_PER_MEASURE * CELL_W, cy_bottom,
                           fill=CELL_BG, outline="")

        for i, offset in enumerate(groove):
            cx0 = x0 + i * CELL_W
            center_x = cx0 + CELL_W / 2

            # evenly-spaced grid tick; downbeats brighter and full height
            downbeat = i % SLOTS_PER_BEAT == 0
            c.create_line(center_x, y0 + (2 if downbeat else 8),
                          center_x, cy_bottom - (2 if downbeat else 8),
                          fill=BEAT_LINE if downbeat else GROOVE_TICK, width=1)

            if offset != 0:
                frac = max(-1.0, min(1.0, offset / MAX_DELAY))
                mx = center_x + frac * max_shift
                color = GROOVE_PULL if offset > 0 else GROOVE_PUSH
                c.create_line(center_x, cy, mx, cy, fill=color, width=2)
                r = 4
                c.create_oval(mx - r, cy - r, mx + r, cy + r, fill=color, outline="")

        right = x0 + SLOTS_PER_MEASURE * CELL_W
        for lx in (x0, right):
            c.create_line(lx, y0, lx, cy_bottom, fill=MEASURE_LINE, width=MEASURE_LINE_W)


def attach_to(parent, source):
    """
    Open the chord progression as its own separate window, driven by the
    given shared SongSource. Call this from the main HandBand program,
    passing the same source used by the other views so they stay in sync.
    """
    window = tk.Toplevel(parent)
    return ChordProgressionView(window, source)


def main():
    """
    Standalone launch: spins up the real Input + EMOTE pipeline so the
    window is driven by the same emotional input as the main program.
    """
    from input import Input
    from emote import EMOTE

    input_val = Input()
    emote = EMOTE()
    source = SongSource(lambda: emote.transform(input_val.get_input_value()))
    attach_to(input_val.window, source)
    input_val.window.mainloop()


if __name__ == "__main__":
    main()
