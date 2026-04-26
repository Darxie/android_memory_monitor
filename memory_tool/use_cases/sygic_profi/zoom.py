import logging
from . import shared


"""
NECESSARY MAPS - Nepal
"""

ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 20


def run_test(device, memory_tool):
    """
    Simulate user interactions on the device.
    """
    zoom_to_nepal(device)
    device.xpath('//*[@resource-id="com.sygic.profi.beta:id/zoomControls"]').click()

    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")

        for _zoom_out in range(0, 20):
            device.click(976, 1392)

        for _zoom_in in range(0, 20):
            device.click(976, 1053)

    memory_tool.stop_monitoring()


def zoom_to_nepal(device):
    shared.tap_search_bar(device)
    shared.set_search_text(device, "27°55'40.5\"N 86°53'07.5\"E")
    shared.select_first_result(device)
