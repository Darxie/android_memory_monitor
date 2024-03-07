import tkinter as tk
from tkinter import ttk
import monkey_handler

# Initialize APP_ID with a default value
APP_ID = "com.sygic.profi.beta"

# Function to be called when dropdown selections are made or buttons are clicked
def on_selection_made(selection_type, value):
    global APP_ID
    if selection_type == "app_mode":
        APP_ID = (
            "com.sygic.profi.beta"
            if value == "release"
            else "com.sygic.profi.beta.debug"
        )
    else:  # For other selections (tasks), handle accordingly
        print(f"Executing {value} with APP_ID {APP_ID}")
        root.destroy()
        monkey_handler.run_automation_tasks(APP_ID, value)


# Initialize the main window
root = tk.Tk()
root.title("Automated Memory Monitor")

# Styling
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 14))
style.configure("TCombobox", font=("Helvetica", 12), padding=10)

# Adjusted window dimensions to accommodate all elements
window_width = 800  # Increased width
window_height = 300
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width / 2) - (window_width / 2)
y = (screen_height / 2) - (window_height / 2)
root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

# Label for build version selection
build_version_label = ttk.Label(root, text="Build Version:", font=("Helvetica", 14))
build_version_label.pack(pady=(20, 5))

# Dropdown for selecting app mode
app_mode = tk.StringVar(value="release")
app_mode_dropdown = ttk.Combobox(
    root, textvariable=app_mode, state="readonly", width=20
)
app_mode_dropdown["values"] = ("release", "debug")
app_mode_dropdown.pack(pady=5)
app_mode_dropdown.bind(
    "<<ComboboxSelected>>", lambda event: on_selection_made("app_mode", app_mode.get())
)

# Task selection area with more organized layout
task_frame = ttk.Frame(root)
task_frame.pack(pady=20)

# Organizing buttons with better spacing
task_options = ["search", "demonstrate", "compute", "fg_bg", "zoom"]
for task in task_options:
    button = ttk.Button(
        task_frame,
        text=task,
        command=lambda task=task: on_selection_made("task", task),
        style="TButton",
    )
    # This arrangement will ensure all buttons are visible and well spaced
    button.pack(side=tk.LEFT, padx=10, pady=10)

root.mainloop()
