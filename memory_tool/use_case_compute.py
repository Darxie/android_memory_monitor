import time


def simulate_user_interactions(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(1, 50):
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

        device.click(550, 2200)
        time.sleep(
            10
        )  # depends on the device's compute performance. adjust accordingly

        device.press("back")
    memory_tool.stop_monitoring()


def tap_search_bar(device):
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/composeView_searchBar"]/android.view.View[1]/android.view.View[1]'
    ).click()
