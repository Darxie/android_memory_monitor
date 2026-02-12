from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Optional
import re
import subprocess
import logging

if __package__ is None and __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# Import the application configuration
from memory_tool import runner
from memory_tool.config import APPLICATIONS, DEFAULT_LOG_INTERVAL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UI Constants
MIN_WINDOW_WIDTH = 1100
MIN_WINDOW_HEIGHT = 500
BUTTON_COLUMNS = 4

# Global Variables
selected_device_code: Optional[str] = None
selected_app_name: Optional[str] = None
selected_build_version: str = "release"

# Execution parameters
final_task: Optional[str] = None
final_package_name: Optional[str] = None
final_device_code: Optional[str] = None
final_log_interval: int = DEFAULT_LOG_INTERVAL
final_internal_name: Optional[str] = None
final_start_activity: Optional[str] = None


def get_package_name() -> Optional[str]:
    """Get the package name for the selected app and build version."""
    if selected_app_name and selected_build_version:
        app_config = APPLICATIONS.get(selected_app_name)
        if app_config:
            return app_config["package_name"].get(selected_build_version)
    return None


def validate_selection() -> bool:
    """Validate that all required selections are made."""
    if not selected_device_code:
        messagebox.showwarning("Selection Missing", "Please select a device.")
        return False
    if not selected_app_name:
        messagebox.showwarning("Selection Missing", "Please select an application.")
        return False
    if not get_package_name():
        messagebox.showerror("Error", "Could not determine package name.")
        return False
    return True


def on_task_selected(task: str) -> None:
    """Handle task button selection."""
    global final_task, final_package_name, final_device_code, final_log_interval
    global final_internal_name, final_start_activity

    if not validate_selection():
        return

    try:
        log_interval = int(log_interval_var.get())
        if log_interval < 1 or log_interval > 300:
            raise ValueError("Interval must be between 1 and 300 seconds")
    except ValueError:
        messagebox.showwarning("Invalid Input", f"Using default interval: {DEFAULT_LOG_INTERVAL}s")
        log_interval = DEFAULT_LOG_INTERVAL

    # Store execution parameters
    final_task = task
    final_package_name = get_package_name()
    final_device_code = selected_device_code
    final_log_interval = log_interval

    if selected_app_name is None:
        messagebox.showerror("Error", "No application selected.")
        return

    app_config = APPLICATIONS[selected_app_name]
    final_internal_name = app_config["internal_name"]
    final_start_activity = app_config.get("start_activity")

    logger.info(f"Starting test: {task} on device {final_device_code}")
    
    # Close GUI and start execution
    root.quit()
    root.destroy()


def get_connected_devices() -> List[Tuple[str, str]]:
    """Get list of connected Android devices."""
    try:
        result = subprocess.check_output(["adb", "devices", "-l"], timeout=5)
        devices: List[Tuple[str, str]] = []
        
        for line in result.splitlines()[1:]:  # Skip header
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
                
            # Extract device code
            device_code = line_str.split()[0]
            if device_code == "List":
                continue
            
            # Extract model name
            match = re.search(r"model:(\S+)", line_str)
            if match:
                model_name = match.group(1).replace("_", " ")
                devices.append((model_name, device_code))
            else:
                devices.append(("Unknown Device", device_code))
        
        return devices
    except subprocess.TimeoutExpired:
        messagebox.showerror("Error", "ADB command timed out. Check device connection.")
        return []
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        messagebox.showerror("Error", f"Failed to get devices: {e}")
        return []


def on_combobox_select(event) -> None:
    """Handle device selection from dropdown."""
    global selected_device_code
    selection = device_dropdown.get()
    
    # Extract device code from formatted string
    match = re.search(r"\((.*?)\)", selection)
    if match:
        selected_device_code = match.group(1)
    else:
        selected_device_code = selection.split()[-1] if selection else None
    
    logger.info(f"Selected device: {selected_device_code}")


def on_build_version_selected(event) -> None:
    """Handle build version selection."""
    global selected_build_version
    selected_build_version = app_mode.get()
    logger.info(f"Build version: {selected_build_version}")


def on_app_selected(event) -> None:
    """Handle application selection."""
    global selected_app_name
    selected_app_name = app_name_var.get()
    update_task_buttons()
    logger.info(f"Selected app: {selected_app_name}")


def update_task_buttons() -> None:
    """Update task buttons based on selected application."""
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
                    command=lambda btn_task=task: on_task_selected(btn_task),
                )
                button.grid(row=idx // BUTTON_COLUMNS, column=idx % BUTTON_COLUMNS, padx=10, pady=10)

    # Resize window to fit content
    root.update_idletasks()
    new_width = max(MIN_WINDOW_WIDTH, root.winfo_reqwidth())
    new_height = root.winfo_reqheight()
    root.geometry(f"{new_width}x{new_height}")

# --- GUI Setup ---
# Initialize the main window
root = tk.Tk()
root.title("Android Memory Monitor")
root.resizable(True, True)

# Apply styling
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 14))
style.configure("TCombobox", font=("Helvetica", 12), padding=10)
style.configure("TSpinbox", font=("Helvetica", 12))

# Center window on screen
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - MIN_WINDOW_WIDTH) // 2
y = (screen_height - MIN_WINDOW_HEIGHT) // 2
root.geometry(f"{MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}+{x}+{y}")

# --- Device Selection ---
device_dropdown_label = ttk.Label(root, text="Select Device:")
device_dropdown_label.pack(pady=(20, 5))

selected_device = tk.StringVar(value="Loading devices...")
device_dropdown = ttk.Combobox(root, textvariable=selected_device, state="readonly", width=40)

# Load devices
raw_devices = get_connected_devices()
if not raw_devices:
    messagebox.showwarning("No Devices", "No Android devices found. Connect a device and try again.")
    
formatted_devices = [f"{d[0]} ({d[1]})" for d in raw_devices]
device_dropdown["values"] = formatted_devices
device_dropdown.pack(pady=5)
device_dropdown.bind("<<ComboboxSelected>>", on_combobox_select)

# Auto-select first device
if formatted_devices:
    device_dropdown.current(0)
    on_combobox_select(None)

# --- Application Selection ---
app_label = ttk.Label(root, text="Select Application:")
app_label.pack(pady=(20, 5))

app_name_var = tk.StringVar()
app_dropdown = ttk.Combobox(root, textvariable=app_name_var, state="readonly", width=20)
app_dropdown["values"] = list(APPLICATIONS.keys())
app_dropdown.pack(pady=5)
app_dropdown.bind("<<ComboboxSelected>>", on_app_selected)

# --- Build Version Selection ---
build_version_label = ttk.Label(root, text="Build Version:")
build_version_label.pack(pady=(20, 5))

app_mode = tk.StringVar(value="release")
app_mode_dropdown = ttk.Combobox(root, textvariable=app_mode, state="readonly", width=20)
app_mode_dropdown["values"] = ("release", "debug")
app_mode_dropdown.pack(pady=5)
app_mode_dropdown.bind("<<ComboboxSelected>>", on_build_version_selected)

# --- Log Interval Input ---
log_interval_label = ttk.Label(root, text="Log Interval (s):")
log_interval_label.pack(pady=(20, 5))

log_interval_var = tk.StringVar(value=str(DEFAULT_LOG_INTERVAL))
log_interval_spinbox = ttk.Spinbox(
    root, from_=1, to=300, textvariable=log_interval_var, width=5
)
log_interval_spinbox.pack(pady=5)

# --- Task Selection ---
task_frame = ttk.Frame(root)
task_frame.pack(pady=20, fill=tk.BOTH, expand=True)
update_task_buttons()

# Start GUI
root.mainloop()

# --- Execute after GUI closes ---
if final_task and final_device_code and final_package_name:
    try:
        logger.info(f"Executing: {final_task} on {final_device_code}")
        runner.run_automation_tasks(
            final_internal_name,
            final_package_name,
            final_task,
            final_device_code,
            final_log_interval,
            start_activity=final_start_activity,
        )
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        messagebox.showerror("Test Failed", f"Test execution failed: {e}")
