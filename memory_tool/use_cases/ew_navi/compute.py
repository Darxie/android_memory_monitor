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
        shared.set_search_text(device, "station-service u express maraussan")
        time.sleep(2)
        shared.select_first_result(device)
        time.sleep(1)
        device(text="Get directions").click()
        time.sleep(
            10
        )  # depends on the online service

        if device(text="OK, got it").exists(timeout=5):
            device(text="OK, got it").click()

        device.press("back")
    memory_tool.stop_monitoring()
