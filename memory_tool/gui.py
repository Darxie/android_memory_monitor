import tkinter as tk
from tkinter import ttk
import monkey_handler

APP_ID = "com.sygic.profi.beta"


# Function called when buttons are clicked
def on_button_click(use_case):
    root.destroy()
    monkey_handler.run_automation_tasks(APP_ID, use_case)


# Initialize main window
root = tk.Tk()

# Window dimensions
window_width = 400
window_height = 260

# Get screen dimensions
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calculate x and y coordinates
x = int((screen_width / 2) - (window_width / 2))
y = int((screen_height / 2) - (window_height / 2))

root.geometry(f"{window_width}x{window_height}+{x}+{y}")
root.title("Automated Memory Monitor")

# Styling for the buttons
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12), padding=10)

title_label = ttk.Label(root, text="Choose Your Fighter", font=("Helvetica", 16))
title_label.pack(pady=10)  # Add some padding for better spacing

# Create a frame for the top row of buttons
top_frame = ttk.Frame(root)
top_frame.pack(pady=10)

middle_frame = ttk.Frame(root)
middle_frame.pack(pady=10)

# Create a frame for the bottom row of buttons
bottom_frame = ttk.Frame(root)
bottom_frame.pack(pady=10)

# Buttons
button_names = ["search", "demonstrate", "compute", "fg_bg", "zoom"]
buttons = []

# Top row buttons
for name in button_names[:2]:
    button = ttk.Button(
        top_frame, text=name, command=lambda n=name: on_button_click(n), style="TButton"
    )
    button.pack(side=tk.LEFT, padx=10)
    buttons.append(button)

# Bottom row buttons
for name in button_names[2:3]:
    button = ttk.Button(
        bottom_frame,
        text=name,
        command=lambda n=name: on_button_click(n),
        style="TButton",
    )
    button.pack(side=tk.LEFT, padx=10)
    buttons.append(button)

for name in button_names[3:]:
    button = ttk.Button(
        middle_frame,
        text=name,
        command=lambda n=name: on_button_click(n),
        style="TButton",
    )
    button.pack(side=tk.LEFT, padx=10)
    buttons.append(button)

# Run the application
root.mainloop()
