from handband.input import Input
from handband.emote import EMOTE
from handband.gui.emote import attach_to as attach_emote
from handband.gui.chord_progression import attach_to as attach_mi
from handband.gui.chord_instrument import attach_to as attach_chord_inst
from handband.gui.bass_contour import attach_to as attach_bass_contour
from handband.gui.bass_pattern import attach_to as attach_bass_pattern
from handband.gui.score import attach_to as attach_score
from handband.mi.song_source import SongSource
import tkinter as tk


#===================#
#===Configurables===#
#===================#

control_bg = "#0E0E0E"
control_fg = "#cdd6f4"
control_select = "#00bf63"
control_active_bg = "#1e1e2e"

#===============#
#===MAIN CODE===#
#===============#

input_val = Input()
emote = EMOTE()


def emote_state():
    """Live {'input', 'valence', 'arousal'} straight from the pipeline."""
    raw = input_val.get_input_value()
    dims = emote.transform(raw)
    return {"input": raw, "valence": dims["valence"], "arousal": dims["arousal"]}


def va_state():
    """Live {'valence', 'arousal'} for the Musical Intelligence window."""
    return emote.transform(input_val.get_input_value())


# One shared song source, so the Musical Intelligence window and the
# Chord Instrument window render the SAME generated song rather than each
# rolling its own.
song_source = SongSource(va_state)


#===================#
#===WINDOW TOGGLES==#
#===================#

# Child windows are built lazily on first open, then shown/hidden with
# the checkboxes. Both start hidden.
views = {"emote": None, "mi": None, "chord_inst": None, "bass_contour": None,
         "bass_pattern": None, "score": None}


def make_toggle(key, var, builder):
    """
    Return a checkbox command that opens the child window when checked
    and hides it when unchecked. The window is built once on first open.
    Closing it via the window's X button unchecks the box.
    """
    def toggle():
        if var.get():
            if views[key] is None:
                view = builder()
                views[key] = view
                # Closing the window just hides it and unchecks the box.
                def on_close():
                    var.set(False)
                    view.master.withdraw()
                view.master.protocol("WM_DELETE_WINDOW", on_close)
            else:
                views[key].master.deiconify()
        else:
            if views[key] is not None:
                views[key].master.withdraw()
    return toggle


controls = tk.Frame(input_val.window, bg=control_bg)
controls.place(relx=0.5, rely=0.06, anchor="center")

emote_var = tk.BooleanVar(value=False)
mi_var = tk.BooleanVar(value=False)
chord_inst_var = tk.BooleanVar(value=False)
bass_contour_var = tk.BooleanVar(value=False)
bass_pattern_var = tk.BooleanVar(value=False)
score_var = tk.BooleanVar(value=False)


def checkbox(parent, text, var, command):
    return tk.Checkbutton(
        parent, text=text, variable=var, command=command,
        bg=control_bg, fg=control_fg, selectcolor=control_active_bg,
        activebackground=control_bg, activeforeground=control_select,
        highlightthickness=0, bd=0, font=("Helvetica", 12), anchor="w",
    )


emote_toggle = make_toggle("emote", emote_var,
                           lambda: attach_emote(input_val.window, emote_state))
mi_toggle = make_toggle("mi", mi_var,
                        lambda: attach_mi(input_val.window, song_source))
chord_inst_toggle = make_toggle("chord_inst", chord_inst_var,
                                lambda: attach_chord_inst(input_val.window, song_source))
bass_contour_toggle = make_toggle("bass_contour", bass_contour_var,
                                  lambda: attach_bass_contour(input_val.window, song_source))
bass_pattern_toggle = make_toggle("bass_pattern", bass_pattern_var,
                                  lambda: attach_bass_pattern(input_val.window, song_source))
score_toggle = make_toggle("score", score_var,
                           lambda: attach_score(input_val.window, song_source))

checkbox(controls, "EMOTE  (valence / arousal)", emote_var, emote_toggle).pack(anchor="w")
checkbox(controls, "Musical Intelligence", mi_var, mi_toggle).pack(anchor="w")
checkbox(controls, "Chord Instrument", chord_inst_var, chord_inst_toggle).pack(anchor="w")
checkbox(controls, "Bass Contour", bass_contour_var, bass_contour_toggle).pack(anchor="w")
checkbox(controls, "Bass Pattern", bass_pattern_var, bass_pattern_toggle).pack(anchor="w")
checkbox(controls, "Score  (Full Band)", score_var, score_toggle).pack(anchor="w")

input_val.window.mainloop()
