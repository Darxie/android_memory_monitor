import time
import logging

"""
NECESSARY MAPS - Slovakia, Austria, Germany
"""

def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """

    time.sleep(2)
    tap_search_bar(device)
    time.sleep(2)
    device(focused=True).set_text(
        "burgerhaus zeughaustrasse philippsburg"
    )
    time.sleep(4)
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/recyclerView"]/android.view.ViewGroup[1]/android.widget.TextView[1]'
    ).click()
    time.sleep(1)

    device(text="Get directions").click()
    time.sleep(10)  # depends on the device's compute performance. adjust accordingly
    device(
        resourceId="com.sygic.profi.beta:id/routePlannerDetailBottomSheetContent"
    ).swipe("up")
    time.sleep(1)
    device(text="Demonstrate route").click()

    time.sleep(3)

    logging.info("adding watcher")
    device.watcher("FinishWatcher").when(
        "Bürgerhaus, Zeughausstraße, Philippsburg"
    ).call(lambda: stop_demonstrate(device, memory_tool))
    logging.info("starting watcher")
    device.watcher.start()


def stop_demonstrate(device, memory_tool):
    """
    Stops the demonstration by clicking the stop button, swiping up, and cancelling the route.
    Also stops the memory monitoring.

    Args:
        device: The device object used to interact with the Android device.
        memory_tool: The memory tool object used to monitor memory usage.

    Returns:
        None
    """
    device(resourceId="com.sygic.profi.beta:id/remainingTime").click()  # swipe up
    time.sleep(1)
    device.xpath('//*[@text="Cancel route"]').click()  # cancel route
    logging.info("canceled route")
    time.sleep(5)
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
