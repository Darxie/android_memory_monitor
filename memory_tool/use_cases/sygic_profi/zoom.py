import logging
import time
from . import shared


ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 20

# Variant-aware: the runner reads LOCATIONS to know this use case has variants.
# Each entry must have a search_query the in-app search bar can resolve.
LOCATIONS = {
    "nepal": {
        "label": "Nepal (Mt. Everest)",
        "search_query": "27°55'40.5\"N 86°53'07.5\"E",
        "maps": "Nepal",
    },
    "paris": {
        "label": "Paris (Tour Eiffel)",
        "search_query": "Tour Eiffel",
        "maps": "France",
    },
}
DEFAULT_LOCATION = "nepal"


def run_test(device, memory_tool, location=None):
    """
    Drive the zoom interaction for the given location preset.

    Args:
        device: uiautomator2 device.
        memory_tool: MemoryTool instance.
        location: Key in LOCATIONS (e.g. "nepal", "paris"). None = DEFAULT_LOCATION.
    """
    location = location or DEFAULT_LOCATION
    if location not in LOCATIONS:
        raise ValueError(
            f"Unknown zoom location '{location}'. Available: {list(LOCATIONS)}"
        )

    config = LOCATIONS[location]
    logging.info(f"Zoom location: {config['label']} ({location})")

    _navigate_to_target(device, config["search_query"])
    time.sleep(1)
    device.xpath('//*[@resource-id="com.sygic.profi.beta:id/zoomControls"]').click()

    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")

        for _zoom_out in range(0, 30):
            device.click(976, 1392)

        for _zoom_in in range(0, 30):
            device.click(976, 1053)

    memory_tool.stop_monitoring()


def _navigate_to_target(device, search_query):
    shared.tap_search_bar(device)
    shared.set_search_text(device, search_query)
    time.sleep(1)
    shared.select_first_result(device)
