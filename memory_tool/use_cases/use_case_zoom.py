import logging


"""
NECESSARY MAPS - Nepal
"""


def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    zoom_to_nepal(device)
    device.xpath(
        '//*[@resource-id="android:id/content"]/android.view.ViewGroup[1]/android.widget.FrameLayout[3]/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/android.widget.LinearLayout[1]'
    ).click()

    for i in range(0, 100):
        logging.info(f"Mambo number {i+1}")

        for zoom_out in range(0, 20):
            device.click(976, 1392)

        for zoom_in in range(0, 20):
            device.click(976, 1053)

    memory_tool.stop_monitoring()


def zoom_to_nepal(device):
    tap_search_bar(device)
    set_search_text(device, "27°55'40.5\"N 86°53'07.5\"E")
    select_first_result(device)


def tap_search_bar(device):
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/composeView_searchBar"]/android.view.View[1]/android.view.View[1]'
    ).click()


def set_search_text(device, input_text):
    device(resourceId="com.sygic.profi.beta:id/inputField").set_text(input_text)


def select_first_result(device):
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/recyclerView"]/android.view.ViewGroup[1]/android.widget.TextView[1]'
    ).click()
