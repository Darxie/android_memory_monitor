import time
import logging
from . import shared


"""
NECESSARY MAPS - Slovakia, South Carolina, Singapore
"""

# crashes spontaneously
def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(0, 50):
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
        time.sleep(2)
    memory_tool.stop_monitoring()
