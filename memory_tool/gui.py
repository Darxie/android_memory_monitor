import tkinter as tk
from tkinter import ttk
import monkey_handler
from typing import List, Tuple
import re
import subprocess

# Import the application configuration
from config import APPLICATIONS

# --- Global Variables ---
selected_device_code = None
selected_app_name = None
selected_build_version = "release"


def get_package_name():
    """Gets the package name based on the selected app and build version."""
    if selected_app_name and selected_build_version:
        app_config = APPLICATIONS.get(selected_app_name)
        if app_config:
            return app_config["package_name"].get(selected_build_version)
    return None


def on_task_selected(task):
    """Handles task button clicks."""
    package_name = get_package_name()
    if not selected_device_code:
        print("Please select a device.")
        return
    if not selected_app_name:
        print("Please select an application.")
        return
    if not package_name:
        print("Could not determine package name.")
        return

    print(
        f"Executing {task} for {selected_app_name} ({package_name}) on device {selected_device_code}"
    )
    root.destroy()
    monkey_handler.run_automation_tasks(
        APPLICATIONS[selected_app_name]["internal_name"],
        package_name,
        task,
        selected_device_code,
    )


def get_connected_devices():
    # Use 'adb devices -l' to get more details about connected devices
    result = subprocess.check_output(["adb", "devices", "-l"])
    lines = result.splitlines()
    devices: List[Tuple[str, str]] = []
    for line in lines[1:]:  # Skip the first line which is a header
        line_str = line.decode("utf-8")
        # Use regex to find the model name, including models with spaces
        match = re.search(r"model:(\S+)", line_str)
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


def on_build_version_selected(event):
    global selected_build_version
    selected_build_version = app_mode.get()


def on_app_selected(event):
    global selected_app_name
    selected_app_name = app_name_var.get()
    update_task_buttons()


def update_task_buttons():
    """Clears and creates task buttons based on the selected application."""
    for widget in task_frame.winfo_children():
        widget.destroy()

    if selected_app_name:
        app_config = APPLICATIONS.get(selected_app_name)
        if app_config:
            task_options = app_config["use_cases"]
            for idx, task in enumerate(task_options):
                button = ttk.Button(
                    task_frame,
                    text=task,
                    command=lambda button_task=task: on_task_selected(button_task),
                    style="TButton",
                )
                button.grid(row=idx // 4, column=idx % 4, padx=10, pady=10)

    # Adjust window size to fit contents, maintaining minimum width
    root.update_idletasks()
    new_width = max(1100, root.winfo_reqwidth())
    new_height = root.winfo_reqheight()
    root.geometry(f"{new_width}x{new_height}")


# Initialize the main window
root = tk.Tk()
root.title("Automated Memory Monitor")

# Styling
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 14))
style.configure("TCombobox", font=("Helvetica", 12), padding=10)

# Adjusted window dimensions to accommodate all elements
window_width = 1100
window_height = 400
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
device_dropdown.pack(pady=5)
device_dropdown.bind("<<ComboboxSelected>>", on_device_selected)

# Application Dropdown
app_label = ttk.Label(root, text="Select Application:", font=("Helvetica", 14))
app_label.pack(pady=(20, 5))
app_name_var = tk.StringVar()
app_dropdown = ttk.Combobox(root, textvariable=app_name_var, state="readonly", width=20)
app_dropdown["values"] = list(APPLICATIONS.keys())
app_dropdown.pack(pady=5)
app_dropdown.bind("<<ComboboxSelected>>", on_app_selected)

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
app_mode_dropdown.bind("<<ComboboxSelected>>", on_build_version_selected)


# Task selection area with more organized layout
task_frame = ttk.Frame(root)
task_frame.pack(pady=20)
update_task_buttons()  # Initial population (will be empty)

root.mainloop()