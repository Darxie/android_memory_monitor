import time

"""
NECESSARY MAPS - Slovakia, Austria, Italy
"""

def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """

    time.sleep(2)
    tap_search_bar(device)
    time.sleep(2)
    device(resourceId="com.sygic.profi.beta:id/inputField").set_text(
        "Lagerhaus Tamsweg"
    )
    time.sleep(2)
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

    device.watcher("FinishWatcher").when("Finish").call(
        lambda: stop_demonstrate(device, memory_tool)
    )
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
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/mapInfoAnimator"]/android.widget.LinearLayout[1]/android.widget.ImageView[2]'
    ).click()  # press stop
    device(resourceId="com.sygic.profi.beta:id/remainingTime").click()  # swipe up
    time.sleep(1)
    device(
        resourceId="com.sygic.profi.beta:id/infoBarMenuActionsButton",
        text="Cancel route",
    ).click()  # cancel route
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
