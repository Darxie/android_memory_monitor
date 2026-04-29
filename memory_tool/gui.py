from pathlib import Path
import importlib
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Optional, Union, cast
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
from memory_tool.use_cases.protocol import get_locations as _module_get_locations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UI Constants
MIN_WINDOW_WIDTH = 1100
MIN_WINDOW_HEIGHT = 600
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
final_dry_run: bool = False

BATCH_TASK_ID = "__sygic_core_batch__"
SYGIC_BATCH_INTERNAL_NAME = "sygic_profi"
FORM_LAYOUT_BREAKPOINT_MEDIUM = 980
FORM_LAYOUT_BREAKPOINT_NARROW = 680
TASK_LAYOUT_BREAKPOINT_3_COL = 1080
TASK_LAYOUT_BREAKPOINT_2_COL = 760
TASK_LAYOUT_BREAKPOINT_1_COL = 520

controls_fields = []
resize_after_id: Optional[str] = None

# Batch checkbox state. Maps use_case -> either:
#   - tk.BooleanVar (flat use case)
#   - dict[location_key, tk.BooleanVar] (variant-aware use case)
batch_selection: dict = {}
final_batch_sequence: Optional[list] = None


def _compute_form_columns(width: int) -> int:
    if width < FORM_LAYOUT_BREAKPOINT_NARROW:
        return 1
    if width < FORM_LAYOUT_BREAKPOINT_MEDIUM:
        return 2
    return 4


def _compute_task_columns(width: int) -> int:
    if width < TASK_LAYOUT_BREAKPOINT_1_COL:
        return 1
    if width < TASK_LAYOUT_BREAKPOINT_2_COL:
        return 2
    if width < TASK_LAYOUT_BREAKPOINT_3_COL:
        return 3
    return BUTTON_COLUMNS


def relayout_controls_grid() -> None:
    """Reflow the configuration controls based on the available width."""
    if not controls_fields:
        return

    width = controls_card.winfo_width() or root.winfo_width()
    columns = _compute_form_columns(width)

    for child in controls_grid.winfo_children():
        cast(tk.Widget, child).grid_forget()

    for col in range(BUTTON_COLUMNS):
        controls_grid.columnconfigure(col, weight=0, uniform="")
    for col in range(columns):
        controls_grid.columnconfigure(col, weight=1, uniform="form")

    for idx, (label_widget, input_widget) in enumerate(controls_fields):
        col = idx % columns
        row_group = idx // columns
        base_row = row_group * 2
        is_last_col = col == columns - 1
        right_pad = 0 if is_last_col else 10

        label_widget.grid(row=base_row, column=col, sticky="w", padx=(0, right_pad), pady=(0, 4))
        input_widget.grid(row=base_row + 1, column=col, sticky="ew", padx=(0, right_pad), pady=(0, 10))


def relayout_task_buttons() -> None:
    """Reflow task buttons based on current card width."""
    buttons = task_buttons_frame.winfo_children()
    if not buttons:
        return

    width = task_card.winfo_width() or root.winfo_width()
    columns = _compute_task_columns(width)

    for col in range(BUTTON_COLUMNS):
        task_buttons_frame.columnconfigure(col, weight=0, uniform="")
    for col in range(columns):
        task_buttons_frame.columnconfigure(col, weight=1, uniform="task")

    for idx, button in enumerate(buttons):
        cast(tk.Widget, button).grid_configure(
            row=idx // columns,
            column=idx % columns,
            padx=8,
            pady=8,
            sticky="ew",
        )


def schedule_relayout() -> None:
    """Debounce layout updates while user resizes the window."""
    global resize_after_id

    if resize_after_id is not None:
        root.after_cancel(resize_after_id)
    resize_after_id = root.after(120, perform_relayout)


def perform_relayout() -> None:
    """Apply responsive layout updates for both form and task area."""
    global resize_after_id
    resize_after_id = None
    relayout_controls_grid()
    relayout_task_buttons()


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

    # Only quit the mainloop; root.destroy() is called in the main thread after mainloop
    # to prevent Tcl_AsyncDelete crashes from background threads later.
    root.quit()


def _start_batch(dry_run: bool) -> None:
    """Shared logic for both full and dry batch buttons."""
    global final_task, final_package_name, final_device_code, final_log_interval
    global final_internal_name, final_start_activity, final_dry_run, final_batch_sequence

    if not validate_selection():
        return

    app_config = APPLICATIONS.get(selected_app_name) if selected_app_name else None
    if not app_config or app_config.get("internal_name") != SYGIC_BATCH_INTERNAL_NAME:
        messagebox.showwarning("Unsupported", "Batch sequence is available only for Sygic Profi.")
        return

    sequence = _selected_batch_sequence()
    if not sequence:
        messagebox.showwarning("Empty Batch", "Tick at least one use case (or variant) to run.")
        return

    try:
        log_interval = int(log_interval_var.get())
        if log_interval < 1 or log_interval > 300:
            raise ValueError("Interval must be between 1 and 300 seconds")
    except ValueError:
        messagebox.showwarning("Invalid Input", f"Using default interval: {DEFAULT_LOG_INTERVAL}s")
        log_interval = DEFAULT_LOG_INTERVAL

    final_task = BATCH_TASK_ID
    final_package_name = get_package_name()
    final_device_code = selected_device_code
    final_log_interval = log_interval
    final_dry_run = dry_run
    final_batch_sequence = sequence

    if selected_app_name is None:
        messagebox.showerror("Error", "No application selected.")
        return

    app_config = APPLICATIONS[selected_app_name]
    final_internal_name = app_config["internal_name"]
    final_start_activity = app_config.get("start_activity")

    mode = "dry batch" if dry_run else "batch"
    logger.info(
        "Starting %s: %s on device %s",
        mode,
        runner.format_sequence(sequence),
        final_device_code,
    )

    root.quit()


def on_batch_selected() -> None:
    """Handle the full batch button."""
    _start_batch(dry_run=False)


def on_dry_batch_selected() -> None:
    """Handle the dry batch button (shortened iterations for fast dashboard testing)."""
    _start_batch(dry_run=True)


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


def _get_use_case_locations(app_internal_name: str, use_case: str) -> Optional[dict]:
    """Look up LOCATIONS dict from the use case module, or None if flat."""
    try:
        module = importlib.import_module(
            f"memory_tool.use_cases.{app_internal_name}.{use_case}"
        )
    except ImportError:
        return None
    return _module_get_locations(module)


def _build_batch_options(app_internal_name: Optional[str]) -> None:
    """Rebuild the batch options checkbox panel for the current app."""
    for child in batch_options_frame.winfo_children():
        child.destroy()
    batch_selection.clear()

    if app_internal_name != SYGIC_BATCH_INTERNAL_NAME:
        # Empty panel collapses to zero height; nothing more to do.
        return

    # Walk SYGIC_CORE_BATCH_SEQUENCE to keep order; collect default-selected variants.
    seen_use_cases: list[str] = []
    default_locations: dict[str, set[str]] = {}
    for entry in runner.SYGIC_CORE_BATCH_SEQUENCE:
        use_case, location = runner.normalize_sequence_entry(entry)
        if use_case not in seen_use_cases:
            seen_use_cases.append(use_case)
        if location is not None:
            default_locations.setdefault(use_case, set()).add(location)

    row = 0
    for use_case in seen_use_cases:
        all_locations = _get_use_case_locations(app_internal_name, use_case)
        if all_locations:
            parent_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                batch_options_frame,
                text=use_case,
                variable=parent_var,
                style="BatchParent.TCheckbutton",
            ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=(0, 2))
            row += 1

            child_vars: dict[str, tk.BooleanVar] = {}
            defaults = default_locations.get(use_case, set())
            for loc_key, loc_meta in all_locations.items():
                child_var = tk.BooleanVar(value=loc_key in defaults)
                label = loc_meta.get("label", loc_key) if isinstance(loc_meta, dict) else loc_key
                ttk.Checkbutton(
                    batch_options_frame,
                    text=label,
                    variable=child_var,
                    style="BatchChild.TCheckbutton",
                ).grid(row=row, column=0, sticky="w", padx=(24, 8), pady=(0, 2))
                row += 1
                child_vars[loc_key] = child_var
            # The parent checkbox toggles all children together.
            def make_toggle(parent=parent_var, children=child_vars):
                def toggle(*_):
                    state = parent.get()
                    for v in children.values():
                        v.set(state)
                return toggle
            parent_var.trace_add("write", make_toggle())
            batch_selection[use_case] = child_vars
        else:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                batch_options_frame,
                text=use_case,
                variable=var,
                style="BatchParent.TCheckbutton",
            ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=(0, 2))
            row += 1
            batch_selection[use_case] = var


def _selected_batch_sequence() -> list:
    """Build the actual batch sequence from current checkbox state."""
    sequence: list = []
    seen_use_cases: list[str] = []
    for entry in runner.SYGIC_CORE_BATCH_SEQUENCE:
        use_case, _ = runner.normalize_sequence_entry(entry)
        if use_case not in seen_use_cases:
            seen_use_cases.append(use_case)

    for use_case in seen_use_cases:
        sel = batch_selection.get(use_case)
        if sel is None:
            continue
        if isinstance(sel, dict):
            for loc_key, var in sel.items():
                if var.get():
                    sequence.append((use_case, loc_key))
        elif isinstance(sel, tk.BooleanVar):
            if sel.get():
                sequence.append(use_case)
    return sequence


def update_batch_button_state() -> None:
    """Keep batch action visible and clearly communicate availability."""
    app_config = APPLICATIONS.get(selected_app_name) if selected_app_name else None
    supports_batch = bool(app_config and app_config.get("internal_name") == SYGIC_BATCH_INTERNAL_NAME)

    if supports_batch:
        batch_button.configure(state="normal")
        dry_batch_button.configure(state="normal")
        actions_hint.configure(text="Batch mode runs the complete Sygic core sequence in one go. Dry batch shortens each scenario for fast dashboard testing.")
    else:
        batch_button.configure(state="disabled")
        dry_batch_button.configure(state="disabled")
        actions_hint.configure(text="Batch mode is available only for Sygic Profi.")


def update_task_buttons() -> None:
    """Update task buttons based on selected application."""
    for widget in task_buttons_frame.winfo_children():
        widget.destroy()

    if selected_app_name:
        app_config = APPLICATIONS.get(selected_app_name)
        if app_config:
            task_options = app_config["use_cases"]
            for idx, task in enumerate(task_options):
                button = ttk.Button(
                    task_buttons_frame,
                    text=task,
                    command=lambda btn_task=task: on_task_selected(btn_task),
                    style="Task.TButton",
                )
                button.grid(row=idx // BUTTON_COLUMNS, column=idx % BUTTON_COLUMNS, padx=8, pady=8, sticky="ew")

    relayout_task_buttons()
    update_batch_button_state()
    app_config = APPLICATIONS.get(selected_app_name) if selected_app_name else None
    _build_batch_options(app_config.get("internal_name") if app_config else None)

    schedule_relayout()

# --- GUI Setup ---
# Initialize the main window
root = tk.Tk()
root.title("Android Memory Monitor")
root.resizable(True, True)
root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
root.configure(bg="#f2f4f7")

palette = {
    "bg": "#f2f4f7",
    "card": "#ffffff",
    "ink": "#16212b",
    "muted": "#536270",
    "line": "#d7dee7",
    "accent": "#006e5f",
    "accent_hover": "#005247",
}

# Apply styling
style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background=palette["bg"])
style.configure("Card.TFrame", background=palette["card"], borderwidth=1, relief="solid")
style.configure("Title.TLabel", background=palette["bg"], foreground=palette["ink"], font=("Segoe UI Semibold", 21))
style.configure("Subtitle.TLabel", background=palette["bg"], foreground=palette["muted"], font=("Segoe UI", 11))
style.configure("Section.TLabel", background=palette["card"], foreground=palette["ink"], font=("Segoe UI Semibold", 12))
style.configure("Field.TLabel", background=palette["card"], foreground=palette["muted"], font=("Segoe UI", 10))
style.configure("TCombobox", font=("Segoe UI", 11), padding=7)
style.configure("Device.TCombobox", font=("Segoe UI Semibold", 11), padding=8)
style.configure("TSpinbox", font=("Segoe UI", 11), padding=6)
style.configure("Task.TButton", font=("Segoe UI Semibold", 10), padding=(10, 8))
style.configure("BatchParent.TCheckbutton", background=palette["card"], foreground=palette["ink"], font=("Segoe UI Semibold", 10))
style.configure("BatchChild.TCheckbutton", background=palette["card"], foreground=palette["muted"], font=("Segoe UI", 9))
style.configure("Accent.TButton", font=("Segoe UI Semibold", 11), padding=(14, 10), background=palette["accent"], foreground="#ffffff")
style.map(
    "Device.TCombobox",
    fieldbackground=[("readonly", "#f9fbfd")],
    selectbackground=[("readonly", "#f9fbfd")],
    selectforeground=[("readonly", palette["ink"])],
)
style.map(
    "Accent.TButton",
    background=[("active", palette["accent_hover"]), ("pressed", palette["accent_hover"])],
    foreground=[("disabled", "#c6d0da"), ("!disabled", "#ffffff")],
)

# Center window on screen
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - MIN_WINDOW_WIDTH) // 2
y = (screen_height - MIN_WINDOW_HEIGHT) // 2
root.geometry(f"{MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}+{x}+{y}")

container = ttk.Frame(root, padding=(26, 20, 26, 20))
container.pack(fill=tk.BOTH, expand=True)

header = ttk.Frame(container)
header.pack(fill=tk.X, pady=(0, 14))
ttk.Label(header, text="Android Memory Monitor", style="Title.TLabel").pack(anchor="w")
ttk.Label(
    header,
    text="Pick device, app and scenario. Then launch profiling in one click.",
    style="Subtitle.TLabel",
).pack(anchor="w", pady=(2, 0))

controls_card = ttk.Frame(container, style="Card.TFrame", padding=(18, 14, 18, 12))
controls_card.pack(fill=tk.X)

controls_grid = ttk.Frame(controls_card, style="Card.TFrame")
controls_grid.pack(fill=tk.X)
for col in range(4):
    controls_grid.columnconfigure(col, weight=1)

ttk.Label(controls_card, text="Test Configuration", style="Section.TLabel").pack(anchor="w", pady=(0, 10))

# --- Device Selection ---
device_label = ttk.Label(controls_grid, text="Device", style="Field.TLabel")

selected_device = tk.StringVar(value="Loading devices...")
device_dropdown = ttk.Combobox(
    controls_grid,
    textvariable=selected_device,
    state="readonly",
    style="Device.TCombobox",
    height=10,
)

# Load devices
raw_devices = get_connected_devices()
if not raw_devices:
    messagebox.showwarning("No Devices", "No Android devices found. Connect a device and try again.")

formatted_devices = [f"{d[0]} ({d[1]})" for d in raw_devices]
if not formatted_devices:
    formatted_devices = ["No devices detected"]
device_dropdown["values"] = formatted_devices
device_dropdown.bind("<<ComboboxSelected>>", on_combobox_select)

# Auto-select first device
if formatted_devices:
    device_dropdown.current(0)
    if raw_devices:
        on_combobox_select(None)

# --- Application Selection ---
app_label = ttk.Label(controls_grid, text="Application", style="Field.TLabel")

app_name_var = tk.StringVar()
app_dropdown = ttk.Combobox(controls_grid, textvariable=app_name_var, state="readonly")
app_dropdown["values"] = list(APPLICATIONS.keys())
app_dropdown.bind("<<ComboboxSelected>>", on_app_selected)

# --- Build Version Selection ---
build_label = ttk.Label(controls_grid, text="Build Version", style="Field.TLabel")

app_mode = tk.StringVar(value="release")
app_mode_dropdown = ttk.Combobox(controls_grid, textvariable=app_mode, state="readonly")
app_mode_dropdown["values"] = ("release", "debug")
app_mode_dropdown.bind("<<ComboboxSelected>>", on_build_version_selected)

# --- Log Interval Input ---
interval_label = ttk.Label(controls_grid, text="Log Interval (s)", style="Field.TLabel")

log_interval_var = tk.StringVar(value=str(DEFAULT_LOG_INTERVAL))
log_interval_spinbox = ttk.Spinbox(
    controls_grid, from_=1, to=300, textvariable=log_interval_var, width=8
)

controls_fields = [
    (device_label, device_dropdown),
    (app_label, app_dropdown),
    (build_label, app_mode_dropdown),
    (interval_label, log_interval_spinbox),
]

# --- Task Selection ---
task_card = ttk.Frame(container, style="Card.TFrame", padding=(18, 14, 18, 14))
task_card.pack(pady=(14, 0), fill=tk.BOTH, expand=True)

ttk.Label(task_card, text="Use Cases", style="Section.TLabel").pack(anchor="w", pady=(0, 10))

batch_options_label = ttk.Label(task_card, text="Batch contents:", style="Field.TLabel")
batch_options_label.pack(anchor="w", pady=(0, 4))
batch_options_frame = ttk.Frame(task_card, style="Card.TFrame")
batch_options_frame.pack(fill=tk.X, pady=(0, 10), anchor="w")

actions_frame = ttk.Frame(task_card, style="Card.TFrame")
actions_frame.pack(fill=tk.X, pady=(0, 10))
actions_frame.columnconfigure(0, weight=1)

actions_hint = ttk.Label(
    actions_frame,
    text="Batch mode runs the complete Sygic core sequence in one go. Dry batch shortens each scenario for fast dashboard testing.",
    style="Field.TLabel",
)
actions_hint.grid(row=0, column=0, columnspan=2, sticky="w", padx=(0, 10), pady=(0, 8))

dry_batch_button = ttk.Button(
    actions_frame,
    text="Run Dry Batch (shortened, ~10-20 min)",
    command=on_dry_batch_selected,
    style="Accent.TButton",
)
dry_batch_button.grid(row=1, column=0, sticky="e", padx=(0, 8))

batch_button = ttk.Button(
    actions_frame,
    text="Run Batch (selected use cases)",
    command=on_batch_selected,
    style="Accent.TButton",
)
batch_button.grid(row=1, column=1, sticky="e")

task_buttons_frame = ttk.Frame(task_card, style="Card.TFrame")
task_buttons_frame.pack(fill=tk.BOTH, expand=True)

# Auto-select first application only after task widgets exist.
if app_dropdown["values"]:
    app_dropdown.current(0)
    on_app_selected(None)

update_task_buttons()
update_batch_button_state()
perform_relayout()
root.bind("<Configure>", lambda event: schedule_relayout() if event.widget is root else None)

# Start GUI
try:
    root.mainloop()
except KeyboardInterrupt:
    logger.info("GUI interrupted by user (Ctrl+C). Exiting cleanly.")
    try:
        root.destroy()
    except Exception:
        pass
    sys.exit(0)

# Destroy Tk root and explicitly delete all StringVar/widget references in the main
# thread before any automation background threads start.  This prevents the
# 'Tcl_AsyncDelete: async handler deleted by the wrong thread' crash that occurs
# when Python GC collects Tk objects from a non-main thread.
try:
    root.destroy()
except Exception:
    pass

import gc as _gc
try:
    del selected_device, app_name_var, app_mode, log_interval_var
    del device_dropdown, app_dropdown, app_mode_dropdown, log_interval_spinbox
except Exception:
    pass
_gc.collect()

# --- Execute after GUI closes ---
if final_task and final_device_code and final_package_name:
    try:
        logger.info(f"Executing: {final_task} on {final_device_code}")
        if final_task == BATCH_TASK_ID:
            result = runner.run_automation_batch(
                final_internal_name,
                final_package_name,
                final_device_code,
                final_log_interval,
                start_activity=final_start_activity,
                use_cases=final_batch_sequence,
                dry_run=final_dry_run,
            )
            batch_report = result.get("batch_report")
            if batch_report:
                title = "Dry Batch Finished" if final_dry_run else "Batch Finished"
                messagebox.showinfo(title, f"Batch report saved to:\n{batch_report}")
        else:
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
