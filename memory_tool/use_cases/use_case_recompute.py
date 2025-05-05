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
    
    stop_timer = threading.Timer(
        18000, stop_demonstrate, args=(device, memory_tool, stop_event)
    )
    stop_timer.start()  # Start the timer

    time.sleep(2)
    tap_search_bar(device)
    time.sleep(2)
    device(focused=True).set_text("Horné obdokovce")
    time.sleep(4)
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/recyclerView"]/android.view.ViewGroup[1]/android.widget.TextView[1]'
    ).click()
    time.sleep(1)

    device(text="Get directions").click()
    time.sleep(15)  # depends on the device's compute performance. adjust accordingly
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/routePlannerDetailBottomSheetContent"]/android.view.View[1]/android.view.View[3]'
    ).click()


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
