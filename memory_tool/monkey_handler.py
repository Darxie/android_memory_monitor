from uiautomator import Device
from utils import Utils
import time
from writer import Writer
from memory_monitor import MemoryTool
import threading
import subprocess


def lel():
    device = Device(Utils().get_device_id())
    print("connected to device")
    device.screen.on()
    print(device.info)
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

    time.sleep(5)

    # monitoriiiiiiiiiing zapni
    package_name = "com.sygic.profi.beta.debug"
    writer = Writer()
    memory_tool = MemoryTool(writer, package_name)
    thread = threading.Thread(target=memory_tool.start_monitoring).start()

    device(text="Address, GPS or Station").click()
    time.sleep(2)
    device(resourceId="com.sygic.profi.beta.debug:id/inputField").set_text(
        "Varhaňovce 159"
    )

    time.sleep(2)
    device(
        resourceId="com.sygic.profi.beta.debug:id/searchItemTitle",
        text="Varhaňovce 159",
    ).click()
    time.sleep(2)

    device.click(550, 2200)
    time.sleep(5)

    device(
        resourceId="com.sygic.profi.beta.debug:id/routePlannerDetailBottomSheetContent",
    ).swipe.up(steps=10)
    time.sleep(2)

    device(text="Demonstrate route").click()


if __name__ == "__main__":
    lel()

    print("finished")
