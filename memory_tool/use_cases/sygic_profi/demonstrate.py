import time
import logging
import threading
from . import shared

"""
NECESSARY MAPS - Slovakia, Austria, Germany
"""


def add_watcher(device, memory_tool, stop_event):
    logging.info("Removing watchers")
    device.watcher.remove("FinishWatcher")  # Remove the existing watcher if any
    logging.info("Adding watcher")
    device.watcher("FinishWatcher").when(
        "Bürgerhaus, Zeughausstraße, Philippsburg"
    ).call(lambda: stop_demonstrate(device, memory_tool, stop_event))
    device.watcher.start()


def watcher_refresh_loop(device, memory_tool, stop_event):
    device.reset_uiautomator()
    while not stop_event.is_set():
        add_watcher(device, memory_tool, stop_event)
        time.sleep(1800)  # Wait for 30 min before refreshing the watcher


def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """

    stop_event = threading.Event()
    # Set a timer to automatically stop the demonstration after 12 hours
    stop_timer = threading.Timer(
        43200, stop_demonstrate, args=(device, memory_tool, stop_event)
    )
    stop_timer.start()  # Start the timer

    shared.tap_search_bar(device)

    device(focused=True).set_text(
        "burgerhaus zeughaustrasse philippsburg"
    )
    if (device(resourceId="com.sygic.profi.beta:id/searchItemTitle").exists(timeout=5)):
        device(resourceId="com.sygic.profi.beta:id/searchItemTitle").click()

    time.sleep(1)

    device(resourceId="SearchDestination.GetDirections").click()

    if (device(text="OK, got it").exists(timeout=10)):
        device(text="OK, got it").click()

    device(text="No traffic data").click()
    time.sleep(1)
    device(text="Demonstrate route").click(timeout=5)

    time.sleep(3)

    threading.Thread(target=watcher_refresh_loop, args=(device, memory_tool, stop_event), daemon=True).start()


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
    device(resourceId="InfoBarBottomSheet.Button.Expand").click()  # swipe up
    time.sleep(1)
    device(resourceId="InfoBarBottomSheet.Button.Cancel route").click()  # cancel route 
    logging.info("canceled route")
    time.sleep(5)
    memory_tool.stop_monitoring()
