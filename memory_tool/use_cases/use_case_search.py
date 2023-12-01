import time
import logging


"""
NECESSARY MAPS - Slovakia, South Carolina, Singapore
"""

# crashes spontaneously
def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(0, 50):
        logging.info(f"Mambo number {i+1}")
        time.sleep(1)
        tap_search_bar(device)
        time.sleep(1)
        set_search_text(device, "market horlbeck")
        time.sleep(1)
        select_first_result(device)
        time.sleep(3)
        tap_x_button(device)
        time.sleep(1)
        set_search_text(device, "kam kreta ayer")
        time.sleep(1)
        select_first_result(device)
        time.sleep(3)
        tap_x_button(device)
        time.sleep(1)
        device.xpath('//*[@resource-id="com.sygic.profi.beta:id/navButton"]').click()
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


def set_search_text(device, input_text):
    device(resourceId="com.sygic.profi.beta:id/inputField").set_text(input_text)


def select_first_result(device):
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/recyclerView"]/android.view.ViewGroup[1]/android.widget.TextView[1]'
    ).click()


def tap_x_button(device):
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/compose_searchBar"]/android.view.View[1]/android.view.View[1]/android.view.View[2]'
    ).click()
