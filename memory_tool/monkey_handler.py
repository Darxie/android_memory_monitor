from uiautomator import Device
from utils import Utils
import time
import logging
import threading
import subprocess

from writer import Writer
from memory_monitor import MemoryTool

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_device():
    """
    Initialize connection to the Android device and launch the application.
    """
    deviceId = Utils().get_device_id()
    device = Device(deviceId)
    logging.info(f"Connected to device: \n{deviceId}  \n{device.info}")
    device.screen.on()
    subprocess.run(
        [
            "adb",
            "shell",
            "am",
            "start",
            "-n",
            "com.sygic.profi.beta.debug/com.sygic.aura.activity.NaviNativeActivity",
        ]
    )
    subprocess.run(["adb", "logcat", "-c"])
    time.sleep(10)
    return device


def simulate_user_interactions(device):
    """
    Simulate user interactions on the device.
    """
    device(text="Address, GPS or Station").click()
    time.sleep(2)
    device(resourceId="com.sygic.profi.beta.debug:id/inputField").set_text("Cuneo")
    time.sleep(2)
    device(
        resourceId="com.sygic.profi.beta.debug:id/searchItemTitle",
        text="Cuneo",
    ).click()
    time.sleep(1)

    device.click(550, 2200)
    time.sleep(10)  # depends on the device's compute performance. adjust accordingly
    device(
        resourceId="com.sygic.profi.beta.debug:id/routePlannerDetailBottomSheetContent"
    ).swipe.up(steps=10)
    time.sleep(1)
    device(text="Demonstrate route").click()


def run_automation_tasks():
    device = initialize_device()

    # Start Monitoring Event
    package_name = "com.sygic.profi.beta.debug"
    writer = Writer()

    memory_tool = MemoryTool(writer, package_name)
    thread = threading.Thread(target=memory_tool.start_monitoring).start()

    # User Interaction Event
    simulate_user_interactions(device)


if __name__ == "__main__":
    run_automation_tasks()
    print("Automation tasks completed, monitoring still running")
