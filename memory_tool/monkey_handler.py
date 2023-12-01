import sys
import utils
import logging
import threading
import uiautomator2 as u2
import use_case_demonstrate
import use_case_compute
import use_case_fg_bg
import use_case_search
from timestamp import ExecutionTimestamp

from writer import Writer
from memory_monitor import MemoryTool

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_device(package_name):
    """
    Initialize connection to the Android device and launch the application.
    """

    device_id = utils.get_device_id()
    device = u2.connect(device_id)
    device.app_stop(package_name)  # force close app if running
    logging.info(f"Connected to device: \n{device_id}  \n{device.info}")
    device.screen_on()
    utils.execute_adb_command(
        [
            "adb",
            "shell",
            "am",
            "start",
            "-n",
            "com.sygic.profi.beta/com.sygic.aura.activity.NaviNativeActivity",
        ]
    )
    utils.execute_adb_command(["adb", "logcat", "-c"])
    if device.app_wait(package_name, front=True):
        pass
    else:
        logging.error(f"App {package_name} failed to start!")
        sys.exit(1)

    return device


def run_automation_tasks(package_name, use_case):
    """
    Runs automation tasks for the given package name.

    Args:
        package_name (str): The name of the package to run automation tasks for.

    Returns:
        None
    """

    # initialize timestamp
    ExecutionTimestamp.get_timestamp()

    device = initialize_device(package_name)

    # Set up synchronization event
    monitoring_finished_event = threading.Event()

    # Start Monitoring Event
    writer = Writer()

    memory_tool = MemoryTool(writer, package_name, monitoring_finished_event)
    threading.Thread(target=memory_tool.start_monitoring).start()

    utils.print_app_info(device, package_name)

    # User Interaction Event
    try:
        if use_case == "search":
            use_case_search.simulate_user_interactions(device, memory_tool)
        elif use_case == "demonstrate":
            use_case_demonstrate.simulate_user_interactions(device, memory_tool)
        elif use_case == "compute":
            use_case_compute.simulate_user_interactions(device, memory_tool)
        elif use_case == "fg_bg":
            use_case_fg_bg.simulate_user_interactions(memory_tool)
    except Exception:
        logging.warn("Exception in automation, stopping monitoring")
        memory_tool.stop_monitoring()

    monitoring_finished_event.wait()

    writer.plot_data_from_csv()


if __name__ == "__main__":
    package_name = "com.sygic.profi.beta"
    run_automation_tasks(package_name, "search")
