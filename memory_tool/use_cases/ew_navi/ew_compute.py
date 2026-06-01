import time
import logging
from . import shared


def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(0, 100):
        logging.info(f"Mambo number {i+1}")
        time.sleep(2)
        shared.tap_search_bar(device)
        time.sleep(2)
        shared.set_search_text(device, "lagerhaus tamsweg")
        time.sleep(2)
        shared.select_first_result(device)
        time.sleep(1)
        device(text="Get directions").click()
        if not device(resourceId="RoutePlannerBottomSheetContentView.RouteSelectedButton").exists(timeout=30):
            logging.warning("RouteSelectedButton not visible after 30s (iteration %s)", i + 1)

        if device(text="OK, got it").exists(timeout=5):
            device(text="OK, got it").click()

        device.press("back")
    memory_tool.stop_monitoring()
