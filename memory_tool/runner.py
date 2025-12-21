import sys
import utils
import shutil
import logging
import threading
import importlib
import uiautomator2 as u2
from pathlib import Path

from timestamp import ExecutionTimestamp
from writer import Writer, directory, CSV_FILE
from memory_monitor import MemoryTool
import plotter


# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("python_run_log.txt"), logging.StreamHandler()]
)
logging.getLogger('matplotlib').setLevel(logging.WARNING)


def initialize_device(package_name, device_code, start_activity=None):
    """
    Initialize connection to the Android device and launch the application.
    """
    device = u2.connect(device_code)
    device.app_stop(package_name)  # force close app if running
    logging.info(f"Connected to device: \n{device_code}  \n{device.info}")
    device.screen_on()

    if start_activity:
        logging.info(f"Starting specific activity: {start_activity}")
        # Construct component name: package/activity
        component = f"{package_name}/{start_activity}"
        utils.execute_adb_command(
            [
                "adb",
                "shell",
                "am",
                "start",
                "-n",
                component,
            ]
        )
    else:
        logging.info(f"Starting default activity for package: {package_name}")
        device.app_start(package_name)

    utils.execute_adb_command(["adb", "logcat", "-c"])
    return device


def run_automation_tasks(app_name_internal, package_name, use_case, device_code, log_interval=5, start_activity=None):
    """
    Runs automation tasks for the given package name.

    Args:
        app_name_internal (str): The internal name of the application.
        package_name (str): The name of the package to run automation tasks for.
        use_case (str): use case shortened name
        device_code (str): unique device code
        log_interval (int): Interval in seconds for memory logging.
        start_activity (str): Optional specific activity to launch.
    """

    ExecutionTimestamp.get_timestamp()
    device = initialize_device(package_name, device_code, start_activity)
    monitoring_finished_event = threading.Event()
    writer = Writer()
    memory_tool = MemoryTool(writer, package_name, device, monitoring_finished_event)
    threading.Thread(target=memory_tool.start_monitoring).start()

    utils.print_app_info(device, package_name, use_case)

    try:
        module_name = f"use_cases.{app_name_internal}.{use_case}"
        logging.info(f"Dynamically loading module: {module_name}")
        use_case_module = importlib.import_module(module_name)

        # The new standard entry point for all use cases is run_test.
        # The run_test function is responsible for its own threading if needed (e.g., freedrive).
        # The signature is consistent: run_test(device, memory_tool).
        use_case_module.run_test(device, memory_tool)

    except Exception as e:
        logging.error(f"Exception in automation: {e}", exc_info=True)
        memory_tool.stop_monitoring()
        try:
            logging.info(f"An error occurred. Deleting output directory: {directory}")
            shutil.rmtree(directory)
            logging.info("Output directory deleted successfully.")
        except OSError as e_rm:
            logging.error(f"Error deleting directory {directory}: {e_rm}")

    monitoring_finished_event.wait()
    writer.plot_data_from_csv()
    device.app_stop(package_name)
