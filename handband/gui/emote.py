"""
EMOTE GUI

A single dark-themed panel that replaces the two old green debug
windows (raw input value + valence/arousal). It shows the live state
of the EMOTE pipeline as three readouts with meters:

  - Input   : the raw slider value, -1 .. +1
  - Valence : -1 .. +1, a center-anchored meter (green when positive
              / pleasant, pink when negative / unpleasant)
  - Arousal : 0 .. 1, a left-to-right meter (orange)

It owns no controls of its own. Like the MI window, it takes a
`state_provider` callable returning the current
{'input', 'valence', 'arousal'} and polls it continuously.

Run directly:  python3 -m handband.gui.emote
"""

import tkinter as tk
from tkinter import font as tkfont

PAD = 18
METER_W = 240
METER_H = 16
ROW_GAP = 14

BG = "#1e1e2e"
PANEL = "#2a2a3d"
TRACK = "#222232"
VAL_POS = "#00bf63"      # pleasant valence
VAL_NEG = "#f38ba8"      # unpleasant valence
AROUSAL = "#f9a03f"      # activation
CENTER_TICK = "#cdd6f4"
LABEL_FG = "#a6adc8"
VALUE_FG = "#cdd6f4"


class EmoteView:
    """
    Renders the live EMOTE state driven by the main HandBand program.
    Polls `state_provider` and repaints the meters each tick.
    """

    def __init__(self, master, state_provider):
        self.master = master
        self.state_provider = state_provider
        master.title("EMOTE")
        master.config(bg=BG)

        self.label_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self.value_font = tkfont.Font(family="Helvetica", size=13, weight="bold")

        body = tk.Frame(master, bg=BG)
        body.pack(padx=PAD, pady=PAD)

        self.input_val = self._make_row(body, "Input")
        self.valence_canvas, self.valence_val = self._make_meter(body, "Valence")
        self.arousal_canvas, self.arousal_val = self._make_meter(body, "Arousal")

        self.poll()

    def _make_row(self, parent, name):
        """A plain label + numeric value row (used for raw input)."""
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, ROW_GAP))
        tk.Label(row, text=name, bg=BG, fg=LABEL_FG, font=self.label_font,
                 width=8, anchor="w").pack(side="left")
        value = tk.Label(row, text="—", bg=BG, fg=VALUE_FG, font=self.value_font)
        value.pack(side="left")
        return value

    def _make_meter(self, parent, name):
        """A labeled meter row: name, a canvas track, and a numeric value."""
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, ROW_GAP))
        tk.Label(row, text=name, bg=BG, fg=LABEL_FG, font=self.label_font,
                 width=8, anchor="w").pack(side="left")
        canvas = tk.Canvas(row, width=METER_W, height=METER_H, bg=BG,
                           highlightthickness=0)
        canvas.pack(side="left", padx=(0, 10))
        value = tk.Label(row, text="—", bg=BG, fg=VALUE_FG, font=self.value_font,
                         width=6, anchor="w")
        value.pack(side="left")
        return canvas, value

    def _draw_valence(self, v):
        """Center-anchored meter: fills left (negative) or right (positive)."""
        c = self.valence_canvas
        c.delete("all")
        c.create_rectangle(0, 0, METER_W, METER_H, fill=TRACK, outline="")
        mid = METER_W / 2
        end = mid + (v / 1.0) * (mid - 1)
        color = VAL_POS if v >= 0 else VAL_NEG
        c.create_rectangle(min(mid, end), 2, max(mid, end), METER_H - 2,
                           fill=color, outline="")
        c.create_line(mid, 0, mid, METER_H, fill=CENTER_TICK, width=1)

    def _draw_arousal(self, a):
        """Left-to-right meter: 0 at the left edge, 1 at the right."""
        c = self.arousal_canvas
        c.delete("all")
        c.create_rectangle(0, 0, METER_W, METER_H, fill=TRACK, outline="")
        c.create_rectangle(0, 2, max(0, a) * METER_W, METER_H - 2,
                           fill=AROUSAL, outline="")

    def poll(self):
        state = self.state_provider()
        i = state.get("input", 0.0)
        v = state["valence"]
        a = state["arousal"]

        self.input_val.config(text=f"{i:+.3f}")
        self.valence_val.config(text=f"{v:+.2f}")
        self.arousal_val.config(text=f"{a:.2f}")
        self._draw_valence(v)
        self._draw_arousal(a)

        self.master.after(50, self.poll)


def attach_to(parent, state_provider):
    """
    Open the EMOTE panel as its own window, driven by the given live
    state provider (a callable returning {'input', 'valence', 'arousal'}).
    """
    window = tk.Toplevel(parent)
    return EmoteView(window, state_provider)


def main():
    """Standalone launch on the real Input + EMOTE pipeline."""
    from handband.input import Input
    from handband.emote import EMOTE

    input_val = Input()
    emote = EMOTE()

    def state():
        raw = input_val.get_input_value()
        dims = emote.transform(raw)
        return {"input": raw, "valence": dims["valence"], "arousal": dims["arousal"]}

    attach_to(input_val.window, state)
    input_val.window.mainloop()


if __name__ == "__main__":
    main()
