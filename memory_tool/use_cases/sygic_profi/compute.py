import time
import logging
from . import shared


"""
NECESSARY MAPS - Slovakia, Austria
"""


def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    for i in range(0, 100):
        logging.info(f"Mambo number {i+1}")
        time.sleep(2)
        shared.tap_search_bar(device)
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
        
        # Make "OK, got it" optional
        if device(text="OK, got it").exists(timeout=5):
            device(text="OK, got it").click()
            
        device.press("back")
    memory_tool.stop_monitoring()
