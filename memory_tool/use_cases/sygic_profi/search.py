import time
import logging
from . import shared


"""
NECESSARY MAPS - Slovakia, South Carolina, Singapore, Italy
"""

ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 20


# crashes spontaneously
def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")
        shared.tap_search_bar(device)
        time.sleep(1)
        shared.set_search_text(device, "market horlbeck")
        time.sleep(1)
        shared.select_first_result(device)
        time.sleep(3)
        shared.tap_x_button(device)
        shared.tap_search_bar(device)
        shared.set_search_text(device, "kam kreta ayer")
        time.sleep(1)
        shared.select_first_result(device)
        time.sleep(3)
        shared.tap_x_button(device)
        shared.tap_search_bar(device)
        shared.set_search_text(device, "duomo di milano")
        time.sleep(1)
        shared.select_first_result(device)
        time.sleep(3)
        shared.tap_x_button(device)
    memory_tool.stop_monitoring()
