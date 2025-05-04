import sys
import utils
import logging
import threading
import uiautomator2 as u2
import use_cases.use_case_demonstrate as demon
import use_cases.use_case_compute as compute
import use_cases.use_case_fg_bg as fg_bg
import use_cases.use_case_search as search
import use_cases.use_case_zoom as zoom
import use_cases.use_case_freedrive as freedrive
import use_cases.use_case_navi_fg_bg as demon_fg_bg

from timestamp import ExecutionTimestamp
from writer import Writer
from memory_monitor import MemoryTool


# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("python_run_log.txt"), logging.StreamHandler()]
)


def initialize_device(package_name, device_code):
    """
    Initialize connection to the Android device and launch the application.
    """
    device = u2.connect(device_code)
    device.app_stop(package_name)  # force close app if running
    logging.info(f"Connected to device: \n{device_code}  \n{device.info}")
    device.screen_on()
    # device.app_start(package_name)
    utils.execute_adb_command(
        [
            "adb",
            "shell",
            "am",
            "start",
            "-n",
            "com.sygic.profi.beta/com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
        ]
    )
    utils.execute_adb_command(["adb", "logcat", "-c"])
    return device


def run_automation_tasks(package_name, use_case, device_code):
    """
    Runs automation tasks for the given package name.

    Args:
        package_name (str): The name of the package to run automation tasks for.
        use_case (str): use case shortened name
        device_code (str): unique device code

    Returns:
        None
    """

    # initialize timestamp
    ExecutionTimestamp.get_timestamp()

    device = initialize_device(package_name, device_code)

    # Set up synchronization event
    monitoring_finished_event = threading.Event()

    # Start Monitoring Event
    writer = Writer()

    memory_tool = MemoryTool(writer, package_name, monitoring_finished_event)
    threading.Thread(target=memory_tool.start_monitoring).start()

    utils.print_app_info(device, package_name, use_case)

    # User Interaction Event
    try:
        if use_case == "search":
            search.simulate_user_interactions(device, memory_tool)
        elif use_case == "demonstrate":
            demon.simulate_user_interactions(device, memory_tool)
        elif use_case == "compute":
            compute.simulate_user_interactions(device, memory_tool)
        elif use_case == "fg_bg":
            fg_bg.simulate_user_interactions(memory_tool)
        elif use_case == "zoom":
            zoom.simulate_user_interactions(device, memory_tool)
        elif use_case == "freedrive":
            threading.Thread(target=freedrive.run, args=(memory_tool,)).start()
        elif use_case == "demon_fg_bg":
            demon_fg_bg.simulate_user_interactions(device, memory_tool)
    except Exception:
        logging.warning("Exception in automation, stopping monitoring")
        memory_tool.stop_monitoring()

    monitoring_finished_event.wait()

    writer.plot_data_from_csv()
    device.app_stop(package_name)
