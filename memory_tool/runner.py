from pathlib import Path
from datetime import datetime
import sys
import logging
import threading
import importlib
import time
import subprocess
import uiautomator2 as u2

if __package__ is None and __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from memory_tool.timestamp import ExecutionTimestamp
from memory_tool.writer import Writer
from memory_tool.memory_monitor import MemoryTool
from memory_tool.adb import AdbDevice, execute_adb_command
from memory_tool.app_info import print_app_info
from memory_tool.archive import archive_batch
from memory_tool.reporter import generate_batch_report, collect_run_artifacts
from memory_tool.use_cases.protocol import validate as validate_use_case

# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("python_run_log.txt"),
        logging.StreamHandler()
    ]
)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

SYGIC_CORE_BATCH_SEQUENCE = ["compute", "search", "fg_bg", "zoom", "demonstrate"]
UIAUTOMATOR_CONNECT_ATTEMPTS = 3
UIAUTOMATOR_RECOVERY_WAIT_SECONDS = 1
DEVICE_READY_TIMEOUT_SECONDS = 120
MAESTRO_DEVICE_PACKAGES = [
    "dev.mobile.maestro",
    "dev.mobile.maestro.test",
    "com.google.android.apps.wearables.maestro.companion",
]



def _is_uiautomator_already_registered_error(error: Exception) -> bool:
    """Detect the uiautomator accessibility registration conflict error."""
    message = str(error)
    return (
        "AccessibilityServiceAlreadyRegisteredError" in message
        or "UiAutomationService" in message and "already registered" in message
    )


def _wait_for_device_ready(adb: AdbDevice, timeout_seconds: int = DEVICE_READY_TIMEOUT_SECONDS) -> bool:
    """Wait until adb sees the device and Android reports boot complete."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        adb.run("wait-for-device", timeout=15)
        boot_completed = adb.shell("getprop", "sys.boot_completed", timeout=10).strip()
        if boot_completed == "1":
            return True
        time.sleep(2)
    return False


def _kill_host_maestro_processes() -> None:
    """Terminate host-side Maestro processes that may hold automation sessions."""
    if sys.platform.startswith("win"):
        tasklist = subprocess.run(
            ["tasklist"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if not tasklist.stdout:
            return

        image_names = set()
        for line in tasklist.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            image = line.split()[0]
            if "maestro" in image.lower():
                image_names.add(image)

        for image in sorted(image_names):
            logging.warning("Stopping host process: %s", image)
            subprocess.run(
                ["taskkill", "/F", "/T", "/IM", image],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
    else:
        subprocess.run(
            ["pkill", "-f", "maestro"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )


def _stop_conflicting_device_automation_services(adb: AdbDevice) -> None:
    """Stop known automation packages that can clash with uiautomator2."""
    shell_commands = [
        ["cmd", "activity", "stop-app", "com.android.shell"],
        ["cmd", "activity", "force-stop", "com.android.shell"],
        ["am", "force-stop", "com.github.uiautomator"],
        ["am", "force-stop", "com.github.uiautomator.test"],
        ["pkill", "-f", "com.wetest.uia2.Main"],
        ["pkill", "-f", "uiautomator"],
    ]
    for package_name in MAESTRO_DEVICE_PACKAGES:
        shell_commands.append(["cmd", "activity", "stop-app", package_name])
        shell_commands.append(["cmd", "activity", "force-stop", package_name])
        shell_commands.append(["am", "force-stop", package_name])

    for cmd in shell_commands:
        adb.shell(*cmd, timeout=15)


def _restart_adb_server(adb: AdbDevice) -> None:
    """Restart adb server and wait for the selected device to come back."""
    logging.warning("Restarting adb server before automation connection")
    execute_adb_command(["adb", "kill-server"], timeout=30)
    execute_adb_command(["adb", "start-server"], timeout=30)
    if not _wait_for_device_ready(adb):
        logging.warning("Device %s did not become ready after adb restart", adb.device_code)


def _prepare_automation_environment(adb: AdbDevice) -> None:
    """Preflight cleanup to minimize automation framework conflicts."""
    _kill_host_maestro_processes()
    _restart_adb_server(adb)
    _stop_conflicting_device_automation_services(adb)
    time.sleep(UIAUTOMATOR_RECOVERY_WAIT_SECONDS)


def _recover_uiautomator_session(adb: AdbDevice, aggressive: bool = False) -> None:
    """Best-effort cleanup of stale uiautomator processes on the target device."""
    logging.warning("Attempting UiAutomator recovery on device %s", adb.device_code)
    _kill_host_maestro_processes()
    _restart_adb_server(adb)
    _stop_conflicting_device_automation_services(adb)

    if aggressive:
        logging.warning("Running aggressive Android user-space restart on %s", adb.device_code)
        adb.shell("cmd", "activity", "restart", timeout=30)
        if not _wait_for_device_ready(adb):
            logging.warning("Device %s did not report boot completion within timeout after restart", adb.device_code)

    # Give Android a short grace period to release the stale accessibility binding.
    time.sleep(UIAUTOMATOR_RECOVERY_WAIT_SECONDS)


def initialize_device(package_name, device_code, start_activity=None):
    """
    Initialize connection to the Android device and launch the application.

    Args:
        package_name: The package name to run
        device_code: Device serial or identifier
        start_activity: Optional specific activity to launch

    Returns:
        Initialized device object

    Raises:
        Exception: If device initialization fails
    """
    adb = AdbDevice(device_code)
    _prepare_automation_environment(adb)

    for attempt in range(1, UIAUTOMATOR_CONNECT_ATTEMPTS + 1):
        try:
            device = u2.connect(device_code)
            device.app_stop(package_name)  # force close app if running
            logging.info(f"Connected to device: {device_code}\n{device.info}")
            device.screen_on()

            if start_activity:
                logging.info(f"Starting activity: {start_activity}")
                component = f"{package_name}/{start_activity}"
                adb.shell("am", "start", "-n", component)
            else:
                logging.info(f"Starting package: {package_name}")
                device.app_start(package_name)

            adb.logcat_clear()
            return device
        except Exception as e:
            is_recoverable = _is_uiautomator_already_registered_error(e)
            is_last_attempt = attempt == UIAUTOMATOR_CONNECT_ATTEMPTS

            if is_recoverable and not is_last_attempt:
                aggressive_recovery = attempt >= 2
                logging.warning(
                    "UiAutomator session conflict detected on %s (attempt %s/%s). Retrying after recovery.",
                    device_code,
                    attempt,
                    UIAUTOMATOR_CONNECT_ATTEMPTS,
                )
                _recover_uiautomator_session(adb, aggressive=aggressive_recovery)
                continue

            logging.error(f"Failed to initialize device: {e}", exc_info=True)
            raise


def run_automation_tasks(app_name_internal, package_name, use_case, device_code, log_interval=5, start_activity=None, dry_run=False, output_dir=None):
    """
    Runs automation tasks for the given package name.

    Args:
        app_name_internal: Internal application name
        package_name: Android package name
        use_case: Use case name to execute
        device_code: Device serial or identifier
        log_interval: Seconds between memory checks
        start_activity: Optional specific activity to launch
        dry_run: Shorten use case for fast dashboard validation
        output_dir: Where to write artifacts. Defaults to output/<timestamp>_<use_case>/
            for single-use-case runs; supplied by run_automation_batch for batch runs.
    """
    run_output_dir = None
    device = None
    monitor_thread = None
    monitor_started = False
    try:
        ExecutionTimestamp.get_timestamp()
        adb = AdbDevice(device_code)
        device = initialize_device(package_name, device_code, start_activity)
        monitoring_finished_event = threading.Event()

        if output_dir is None:
            run_timestamp = ExecutionTimestamp.get_timestamp()
            output_dir = Path(f"output/{run_timestamp}_{use_case}")

        writer = Writer(adb, output_dir=Path(output_dir))
        run_output_dir = writer.get_output_directory()
        memory_tool = MemoryTool(writer, package_name, device, monitoring_finished_event, log_interval, dry_run=dry_run)

        read_about = None
        try:
            shared_module = importlib.import_module(f"memory_tool.use_cases.{app_name_internal}.shared")
            read_about = getattr(shared_module, "read_about_screen", None)
        except ImportError:
            logging.debug(f"No shared module for {app_name_internal}; SDK detection disabled")

        print_app_info(device, package_name, use_case, adb, read_about, output_dir=run_output_dir)

        # Start monitoring after metadata collection.
        monitor_thread = threading.Thread(target=memory_tool.start_monitoring, daemon=True)
        monitor_thread.start()
        monitor_started = True

        # Execute use case
        try:
            module_name = f"memory_tool.use_cases.{app_name_internal}.{use_case}"
            logging.info(f"Loading use case module: {module_name}")
            use_case_module = importlib.import_module(module_name)
            validate_use_case(use_case_module)
            use_case_module.run_test(device, memory_tool)
        except ImportError as e:
            logging.error(f"Failed to load use case module: {e}", exc_info=True)
            raise
        except Exception as e:
            logging.error(f"Error executing use case: {e}", exc_info=True)
            raise
        finally:
            if monitor_started:
                memory_tool.stop_monitoring()

    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)
        if run_output_dir and run_output_dir.exists():
            logging.info(f"Keeping output directory for diagnostics: {run_output_dir}")
        raise
    finally:
        # Wait for monitoring to finish and plot results
        if 'monitoring_finished_event' in locals():
            monitoring_finished_event.wait(timeout=10)
        if 'writer' in locals():
            writer.plot_data_from_csv()
        if device is not None:
            device.app_stop(package_name)

    if run_output_dir:
        return collect_run_artifacts(run_output_dir, use_case)
    return {"use_case": use_case, "output_dir": None}


def run_automation_batch(app_name_internal, package_name, device_code, log_interval=5, start_activity=None, use_cases=None, dry_run=False):
    """
    Run multiple use-cases sequentially and generate one aggregate HTML report.

    Args:
        app_name_internal: Internal application name
        package_name: Android package name
        device_code: Device serial or identifier
        log_interval: Seconds between memory checks
        start_activity: Optional specific activity to launch
        use_cases: Optional explicit sequence of use-cases

    Returns:
        Dictionary with run artifacts and final batch report path
    """
    sequence = use_cases or SYGIC_CORE_BATCH_SEQUENCE
    batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = Path(f"output/{batch_timestamp}_batch")
    batch_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts = []

    for use_case in sequence:
        logging.info(f"Starting batch use-case: {use_case}")
        ExecutionTimestamp.reset()
        artifacts = run_automation_tasks(
            app_name_internal,
            package_name,
            use_case,
            device_code,
            log_interval,
            start_activity=start_activity,
            dry_run=dry_run,
            output_dir=batch_dir / use_case,
        )
        run_artifacts.append(artifacts)

    batch_report = generate_batch_report(run_artifacts, app_name_internal, output_dir=batch_dir)
    archive_result = archive_batch(run_artifacts, app_name_internal)
    return {
        "sequence": sequence,
        "runs": run_artifacts,
        "batch_report": batch_report,
        "archive": archive_result,
        "batch_dir": batch_dir,
    }
