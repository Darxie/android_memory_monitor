from pathlib import Path
import sys
import shutil
import logging
import threading
import importlib
import uiautomator2 as u2

if __package__ is None and __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from memory_tool.timestamp import ExecutionTimestamp
from memory_tool.writer import Writer, directory, CSV_FILE
from memory_tool.memory_monitor import MemoryTool
from memory_tool import utils
from memory_tool import plotter

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
    try:
        device = u2.connect(device_code)
        device.app_stop(package_name)  # force close app if running
        logging.info(f"Connected to device: {device_code}\n{device.info}")
        device.screen_on()

        if start_activity:
            logging.info(f"Starting activity: {start_activity}")
            component = f"{package_name}/{start_activity}"
            utils.execute_adb_command(["adb", "shell", "am", "start", "-n", component])
        else:
            logging.info(f"Starting package: {package_name}")
            device.app_start(package_name)

        utils.execute_adb_command(["adb", "logcat", "-c"])
        return device
    except Exception as e:
        logging.error(f"Failed to initialize device: {e}", exc_info=True)
        raise


def run_automation_tasks(app_name_internal, package_name, use_case, device_code, log_interval=5, start_activity=None):
    """
    Runs automation tasks for the given package name.

    Args:
        app_name_internal: Internal application name
        package_name: Android package name
        use_case: Use case name to execute
        device_code: Device serial or identifier
        log_interval: Seconds between memory checks
        start_activity: Optional specific activity to launch
    """
    try:
        ExecutionTimestamp.get_timestamp()
        device = initialize_device(package_name, device_code, start_activity)
        monitoring_finished_event = threading.Event()
        writer = Writer()
        memory_tool = MemoryTool(writer, package_name, device, monitoring_finished_event, log_interval)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=memory_tool.start_monitoring, daemon=True)
        monitor_thread.start()

        # Load shared module for optional screenshot callback
        screenshot_callback = None
        try:
            shared_module_name = f"memory_tool.use_cases.{app_name_internal}.shared"
            shared_module = importlib.import_module(shared_module_name)
            if hasattr(shared_module, "take_about_screenshot"):
                screenshot_callback = shared_module.take_about_screenshot
        except ImportError:
            logging.debug(f"No shared module found for {app_name_internal}")

        utils.print_app_info(device, package_name, use_case, screenshot_callback)

        # Execute use case
        try:
            module_name = f"memory_tool.use_cases.{app_name_internal}.{use_case}"
            logging.info(f"Loading use case module: {module_name}")
            use_case_module = importlib.import_module(module_name)
            use_case_module.run_test(device, memory_tool)
        except ImportError as e:
            logging.error(f"Failed to load use case module: {e}", exc_info=True)
            raise
        except Exception as e:
            logging.error(f"Error executing use case: {e}", exc_info=True)
            raise
        finally:
            memory_tool.stop_monitoring()

    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)
        try:
            if directory.exists():
                logging.info(f"Cleaning up output directory: {directory}")
                shutil.rmtree(directory)
        except OSError as e_rm:
            logging.error(f"Error deleting directory: {e_rm}")
        raise
    finally:
        # Wait for monitoring to finish and plot results
        if 'monitoring_finished_event' in locals():
            monitoring_finished_event.wait(timeout=10)
        if 'writer' in locals():
            writer.plot_data_from_csv()
        if 'device' in locals() and 'package_name' in locals():
            device.app_stop(package_name)
