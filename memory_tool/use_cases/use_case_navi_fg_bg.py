import time
import logging
import threading
import utils

"""
NECESSARY MAPS - Slovakia, Austria, Italy
"""


def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """

    stop_event = threading.Event()
    # Set a timer to automatically stop the demonstration after 5 hours
    stop_timer = threading.Timer(
        18000, stop_demonstrate, args=(device, memory_tool, stop_event)
    )
    stop_timer.start()  # Start the timer

    time.sleep(2)
    tap_search_bar(device)
    time.sleep(2)
    device(focused=True).set_text("37.798910869409795, 12.439788716063287")
    time.sleep(4)
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/recyclerView"]/android.view.ViewGroup[1]/android.widget.TextView[1]'
    ).click()
    time.sleep(1)

    device(text="Get directions").click()
    time.sleep(15)  # depends on the device's compute performance. adjust accordingly
    device(
        resourceId="com.sygic.profi.beta:id/routePlannerDetailBottomSheetContent"
    ).swipe("up")
    time.sleep(1)
    device(text="Demonstrate route").click()

    time.sleep(3)

    

    for i in range(0, 1800):
        if stop_event.is_set():
            break  # Exit the loop if the stop_event is set
        logging.info(f"Mambo number {i+1}")
        time.sleep(10)
        utils.execute_adb_command(
            [
                "adb",
                "shell",
                "monkey",
                "-p ",
                "com.google.android.calendar",
                "1",
            ],
        )
        logging.info("switched to calendar")
        time.sleep(10)
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
        logging.info("switched to profi navi")


def stop_demonstrate(device, memory_tool, stop_event):
    """
    Stops the demonstration by clicking the stop button, swiping up, and cancelling the route.
    Also stops the memory monitoring.

    Args:
        device: The device object used to interact with the Android device.
        memory_tool: The memory tool object used to monitor memory usage.

    Returns:
        None
    """
    stop_event.set()
    memory_tool.stop_monitoring()


def tap_search_bar(device):
    """
    Taps on the search bar of the Sygic app.

    Args:
        device: The device object representing the Android device.

    Returns:
        None
    """
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/composeView_searchBar"]/android.view.View[1]/android.view.View[1]'
    ).click()
