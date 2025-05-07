import tkinter as tk
from ProgrammablePlaySequence import ProgrammablePlaySequence

root = tk.Tk()

root.title("Programmable Songs")

play_button = tk.Button(root, text="Play", command=lambda: ProgrammablePlaySequence(measure.get()))
play_button.pack(padx=20, pady=20)
stop_button = tk.Button(root, text="Stop", command=lambda: KeyboardInterrupt)
stop_button.pack(padx=20, pady=20)

measure = tk.StringVar()
tk.Radiobutton(root, text='A', variable=measure, value="measure1").pack(anchor='w')
tk.Radiobutton(root, text='B', variable=measure, value="measure2").pack(anchor='w')

root.mainloop()

