import tkinter as tk
from tkinter import ttk
import monkey_handler
import re
import subprocess

# Initialize APP_ID with a default value
APP_ID = "com.sygic.profi.beta"
selected_device_code = None

# Function to be called when dropdown selections are made or buttons are clicked
def on_selection_made(selection_type, value):
    global APP_ID, selected_device_code
    if selection_type == "app_mode":
        APP_ID = (
            "com.sygic.profi.beta"
            if value == "release"
            else "com.sygic.profi.beta.debug"
        )
    else:  # For other selections (tasks), handle accordingly
        print(f"Executing {value} with APP_ID {APP_ID}")
        root.destroy()
        monkey_handler.run_automation_tasks(APP_ID, value, selected_device_code)


def get_connected_devices():
    # Use 'adb devices -l' to get more details about connected devices
    result = subprocess.check_output(["adb", "devices", "-l"])
    lines = result.splitlines()
    devices = []
    for line in lines[1:]:  # Skip the first line which is a header
        line_str = line.decode("utf-8")
        # Use regex to find the model name, including models with spaces
        match = re.search(r"model:([^\s]+)", line_str)
        if match:
            model = match.group(1)
            # Replace underscores with spaces to handle models with spaces properly
            model_name = model.replace("_", " ")
            devices.append((model_name, line_str.split()[0]))
    return devices


def on_device_selected(event):
    global selected_device_code
    # Extract device code from the dropdown's value
    selected_device_code = device_dropdown.get().split()[-1]


# Initialize the main window
root = tk.Tk()
root.title("Automated Memory Monitor")

# Styling
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 14))
style.configure("TCombobox", font=("Helvetica", 12), padding=10)

# Adjusted window dimensions to accommodate all elements
window_width = 1000
window_height = 300
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width / 2) - (window_width / 2)
y = (screen_height / 2) - (window_height / 2)
root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

# Dropdown for selecting connected Android devices
selected_device = tk.StringVar(value="Choose")
device_dropdown_label = ttk.Label(root, text="Select Device:", font=("Helvetica", 14))
device_dropdown_label.pack(pady=(20, 5))

device_dropdown = ttk.Combobox(
    root, textvariable=selected_device, state="readonly", width=20
)
device_dropdown["values"] = (
    get_connected_devices()
)  
# Populate dropdown with connected devices
device_dropdown.pack(pady=5)
device_dropdown.bind("<<ComboboxSelected>>", on_device_selected)

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
task_options = ["search", "demonstrate", "compute", "fg_bg", "zoom", "freedrive"]
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
