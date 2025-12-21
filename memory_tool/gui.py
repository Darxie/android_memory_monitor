import tkinter as tk
from tkinter import ttk, messagebox
from memory_tool import runner
from typing import List, Tuple
import re
import subprocess

# Import the application configuration
from memory_tool.config import APPLICATIONS, DEFAULT_LOG_INTERVAL

# --- Global Variables ---
selected_device_code = None
selected_app_name = None
selected_build_version = "release"

# Variables to store execution parameters after GUI closes
final_task = None
final_package_name = None
final_device_code = None
final_log_interval = DEFAULT_LOG_INTERVAL
final_internal_name = None
final_start_activity = None


def get_package_name():
    """Gets the package name based on the selected app and build version."""
    if selected_app_name and selected_build_version:
        app_config = APPLICATIONS.get(selected_app_name)
        if app_config:
            return app_config["package_name"].get(selected_build_version)
    return None


def on_task_selected(task):
    """Handles task button clicks."""
    global final_task, final_package_name, final_device_code, final_log_interval, final_internal_name, final_start_activity
    
    package_name = get_package_name()
    if not selected_device_code:
        messagebox.showwarning("Selection Missing", "Please select a device first.")
        return
    if not selected_app_name:
        messagebox.showwarning("Selection Missing", "Please select an application first.")
        return
    if not package_name:
        messagebox.showerror("Error", "Could not determine package name.")
        return
    
    try:
        log_interval = int(log_interval_var.get())
    except ValueError:
        log_interval = DEFAULT_LOG_INTERVAL
        print(f"Invalid log interval. Using default: {DEFAULT_LOG_INTERVAL}")

    # Store values for execution after mainloop
    final_task = task
    final_package_name = package_name
    final_device_code = selected_device_code
    final_log_interval = log_interval
    
    app_config = APPLICATIONS[selected_app_name]
    final_internal_name = app_config["internal_name"]
    final_start_activity = app_config.get("start_activity")

    print(f"Selection confirmed. Closing GUI to start test: {task}")
    
    # Force close the GUI
    root.quit()    # Stop mainloop
    root.destroy() # Destroy window


def get_connected_devices():
    try:
        # Use 'adb devices -l' to get more details about connected devices
        result = subprocess.check_output(["adb", "devices", "-l"])
        lines = result.splitlines()
        devices: List[Tuple[str, str]] = []
        for line in lines[1:]:  # Skip the first line which is a header
            line_str = line.decode("utf-8")
            if not line_str.strip(): continue
            # Use regex to find the model name, including models with spaces
            match = re.search(r"model:(\S+)", line_str)
            if match:
                model = match.group(1)
                # Replace underscores with spaces to handle models with spaces properly
                model_name = model.replace("_", " ")
                devices.append((model_name, line_str.split()[0]))
            else:
                # Fallback if model not found
                parts = line_str.split()
                if len(parts) > 0 and parts[0] != 'List':
                    devices.append(("Unknown Model", parts[0]))
        return devices
    except Exception as e:
        print(f"Error getting devices: {e}")
        return []


def on_combobox_select(event):
    global selected_device_code
    selection = device_dropdown.get()
    # Find the device code corresponding to the selection
    match = re.search(r"\((.*?)\)", selection)
    if match:
        selected_device_code = match.group(1)
    else:
        selected_device_code = selection.split()[-1]
    
    print(f"Device selected: {selected_device_code}")


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
style.configure("TSpinbox", font=("Helvetica", 12))

# Adjusted window dimensions
window_width = 1100
window_height = 500
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width / 2) - (window_width / 2)
y = (screen_height / 2) - (window_height / 2)
root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

# Dropdown for selecting connected Android devices
selected_device = tk.StringVar(value="Choose")
device_dropdown_label = ttk.Label(root, text="Select Device:", font=("Helvetica", 14))
device_dropdown_label.pack(pady=(20, 5))

# Get devices and format them for display
raw_devices = get_connected_devices()
formatted_devices = [f"{d[0]} ({d[1]})" for d in raw_devices]

device_dropdown = ttk.Combobox(
    root, textvariable=selected_device, state="readonly", width=40
)
device_dropdown["values"] = formatted_devices
device_dropdown.pack(pady=5)
device_dropdown.bind("<<ComboboxSelected>>", on_combobox_select)

# Auto-select first device if available
if formatted_devices:
    device_dropdown.current(0)
    # Manually trigger the selection logic
    on_combobox_select(None)

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

# Log Interval Input
log_interval_label = ttk.Label(root, text="Log Interval (s):", font=("Helvetica", 14))
log_interval_label.pack(pady=(20, 5))
log_interval_var = tk.StringVar(value=str(DEFAULT_LOG_INTERVAL))
log_interval_spinbox = ttk.Spinbox(root, from_=1, to=60, textvariable=log_interval_var, width=5, font=("Helvetica", 12))
log_interval_spinbox.pack(pady=5)

# Task selection area with more organized layout
task_frame = ttk.Frame(root)
task_frame.pack(pady=20)
update_task_buttons()  # Initial population

root.mainloop()

# --- Post-GUI Execution ---
if final_task and final_device_code and final_package_name:
    print(f"Starting execution for {final_task}...")
    runner.run_automation_tasks(
        final_internal_name,
        final_package_name,
        final_task,
        final_device_code,
        final_log_interval,
        start_activity=final_start_activity,
    )
