import time
import logging


"""
NECESSARY MAPS - Slovakia, Austria
"""


def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(0, 100):
        logging.info(f"Mambo number {i+1}")
        time.sleep(2)
        tap_search_bar(device)
        time.sleep(2)
        device(resourceId="com.sygic.profi.beta:id/inputField").set_text(
            "Lagerhaus Tamsweg"
        )
        time.sleep(2)
        device(
            resourceId="com.sygic.profi.beta:id/searchItemTitle",
            text="Lagerhaus",
        ).click()
        time.sleep(1)

        device(text="Get directions").click()
        time.sleep(
            10
        )  # depends on the device's compute performance. adjust accordingly

        device.press("back")
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
