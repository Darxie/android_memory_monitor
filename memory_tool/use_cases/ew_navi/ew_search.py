import time
import logging
from . import ew_shared


def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(0, 50):
        logging.info(f"Mambo number {i+1}")
        ew_shared.tap_search_bar(device)
        time.sleep(1)
        ew_shared.set_search_text(device, "bezier apartments")
        time.sleep(1)
        ew_shared.select_first_result(device)
        time.sleep(3)
        ew_shared.tap_x_button(device)
        ew_shared.tap_search_bar(device)
        ew_shared.set_search_text(device, "plaza de san nicolás")
        time.sleep(1)
        ew_shared.select_first_result(device)
        time.sleep(3)
        ew_shared.tap_x_button(device)
        ew_shared.tap_search_bar(device)
        ew_shared.set_search_text(device, "duomo di milano")
        time.sleep(1)
        ew_shared.select_first_result(device)
        time.sleep(3)
        ew_shared.tap_x_button(device)
    memory_tool.stop_monitoring()
