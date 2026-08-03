"""
	The Input module is HandBand’s sensory interface - 
    the single point where external reality enters the system. 
    Its only job is to read sensor data and normalize it to a 
    standardized range of -1.0 to +1.0, where -1 represents 
    one emotional extreme (calm/low arousal), 
    0 is neutral baseline, and +1 is the opposite extreme 
    (intense/high arousal). 
    Currently this is a GUI slider, 
    but the architecture is designed so we can swap in 
    biosensors later without touching any other module.

	Input does not interpret what the value means, 
    make musical decisions, or store history. 
    It’s purely mechanical - just accurate sensor reading 
    and normalization. The rest of the system treats it as 
    a black box that provides a single float value. 
    If the sensor fails, it should signal error clearly 
    rather than produce garbage data.

	The evolution path goes from GUI slider to single biosensor 
    (HRV or skin conductance) to multi-sensor fusion, and 
    eventually integrates with Northstar for 
    context-aware calibration. But through all phases, 
    the interface stays simple: get the current state value, 
    check if sensor is connected, and report what type of 
    sensor is active. No downstream module needs to know or 
    care what’s actually providing that number.​​​​​​​​​​​​​​​​
"""

import tkinter as tk

#===================#
#===Configurables===#
#===================#

main_window_title = "HandBand"
main_window_height = "692" #pixels
main_window_width = "400" #pixels
window_bg_color = "#0E0E0E"

slider_track_color = "#4d4d4c"
slider_range_low = -1
slider_range_high = 1
slider_res = 0.001
slider_length_per = 0.95 * int(main_window_width) # Slider length as percentage of overall width.
slider_width = 30 #pixels
slider_height = 0.67 #percent of window
slider_center = 0.5 #percent of window
slider_anchor = "center"

display_bg_color = "#00bf63"
display_width = 100
display_height = 100
display_center = 0.5
display_in_window_height = 0.7
display_anchor = "center"

#===========#
#===TESTS===#
#===========#

debug_values = False

class Input:
    """
    This class is the entire module. It establishes
    the window, slider, and the method for retrieving
    the slider value.
    """
    def __init__(self):
        """This method instantiates the window and slider."""
        self.window = tk.Tk()
        self.window.title(main_window_title)
        self.window.geometry(main_window_width + "x" + main_window_height)
        self.window.config(bg= window_bg_color)

        self.slider = tk.Scale(self.window, from_= slider_range_low, to= slider_range_high, resolution= slider_res, orient = tk.HORIZONTAL, length= slider_length_per, width= slider_width, troughcolor= slider_track_color, showvalue=0)
        self.slider.place(relx=slider_center, rely=slider_height, anchor= slider_anchor)

        if debug_values:
            self.slider.config(command= self.update_debug_display)
            self.test_input_module()

    def get_input_value(self):
        """
        This method will be called by other modules
        to retrieve the value of the slider at the
        current instant.
        """
        return self.slider.get()
    
    def test_input_module(self):
        self.display = tk.Frame(self.window, bg= display_bg_color, width = display_width, height = display_height)
        self.display.place(relx = display_center, rely=display_in_window_height,anchor = display_anchor)

        self.value = tk.Label(self.display, text= str(self.get_input_value()))
        self.value.pack(padx=5, pady=5)

    def update_debug_display(self, value):
        self.value.config(text=value)

if __name__ == "__main__":
    input = Input()
    input.window.mainloop()