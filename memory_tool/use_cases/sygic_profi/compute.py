import time
import logging
from . import shared


# Offline maps installed by the runner before monitoring (see maps.py).
REQUIRED_MAPS = ["sk", "at"]

ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 5


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
        device(className="android.widget.EditText").set_text(
            "Lagerhaus Tamsweg"
        )
        time.sleep(1)
        shared.select_first_result(device)
        time.sleep(1)

        device(resourceId="SearchDestination.GetDirections").click()
        time.sleep(
            5
        )  # depends on the device's compute performance. adjust accordingly

        # Make "OK, got it" optional
        if device(text="OK, got it").exists(timeout=5):
            device(text="OK, got it").click()

        device.press("back")
    memory_tool.stop_monitoring()
