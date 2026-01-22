from input import Input
from emote import EMOTE
import tkinter as tk


#===================#
#===Configurables===#
#===================#

input_debug_window_title = "Input Values Test"
input_debug_window_size = "100x100"
input_debug_window_color = "#00bf63"

emote_debug_window_title = "EMOTE Values Test"
emote_debug_window_size = "100x100"
emote_debug_window_color = "#00bf63"

debug_input_value = True
debug_emote_values = True

#===============#
#===MAIN CODE===#
#===============#

input_val = Input()

emote = EMOTE()

idp = emote.transform(input_val.get_input_value()) #info-dimensional package

#===========#
#===TESTS===#
#===========#

def display_values_from_input(input_val):
    input_val.input_test = tk.Toplevel()
    input_val.input_test.title(input_debug_window_title)
    input_val.input_test.geometry(input_debug_window_size)
    input_val.input_test.config(bg= input_debug_window_color)
    input_val.debug_input_value = tk.Label(input_val.input_test, text= str(input_val.get_input_value()))
    input_val.debug_input_value.pack(padx=5, pady=5)

def display_values_from_emote(input_val):
    input_val.emote_test = tk.Toplevel()
    input_val.emote_test.title(emote_debug_window_title)
    input_val.emote_test.geometry(emote_debug_window_size)
    input_val.emote_test.config(bg=emote_debug_window_color)
    input_val.debug_emote_values = tk.Label(input_val.emote_test, text="")
    input_val.debug_emote_values.pack(padx=5, pady=5)

def update_input_debug_display():
    input_val.debug_input_value.config(text=input_val.get_input_value())
    input_val.window.after(10, update_input_debug_display)

def update_emote_debug_display():
    dimensions = emote.transform(input_val.get_input_value())
    text = f"V: {dimensions['valence']:.2f}\nA: {dimensions['arousal']:.2f}"
    input_val.debug_emote_values.config(text=text)
    input_val.window.after(10, update_emote_debug_display)

if debug_input_value:
    display_values_from_input(input_val)
    update_input_debug_display()

if debug_emote_values:
    display_values_from_emote(input_val)
    update_emote_debug_display()

input_val.window.mainloop()