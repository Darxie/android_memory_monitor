import time
import logging
from . import shared


"""
NECESSARY MAPS - Slovakia, Austria
"""

ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 20


def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")
        time.sleep(1)
        shared.tap_search_bar(device)
        time.sleep(1)
        device(resourceId="com.sygic.profi.beta:id/inputField").set_text(
            "Lagerhaus Tamsweg"
        )
        time.sleep(1)
        device(
            resourceId="com.sygic.profi.beta:id/searchItemTitle",
            text="Lagerhaus",
        ).click()
        time.sleep(1)

        device(text="Get directions").click()
        time.sleep(
            5
        )  # depends on the device's compute performance. adjust accordingly
        
        # Make "OK, got it" optional
        if device(text="OK, got it").exists(timeout=5):
            device(text="OK, got it").click()
            
        device.press("back")
    memory_tool.stop_monitoring()
