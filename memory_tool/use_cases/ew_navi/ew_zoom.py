import logging
import time
from . import shared


ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 20

LOCATIONS = {
    "edinburgh": {
        "label": "Edinburgh",
        "search_query": "55.95517881042256, -3.1955480266077254",
        "maps": "UK",
    },
    "paris": {
        "label": "Paris (Tour Eiffel)",
        "search_query": "Tour Eiffel",
        "maps": "France",
    },
}
DEFAULT_LOCATION = "edinburgh"

# Center of the on-screen zoom button area [880,1154][1038,1312]
ZOOM_BUTTON_X = 959
ZOOM_BUTTON_Y = 1233


def run_test(device, memory_tool, location=None):
    """
    Drive the zoom interaction for the given location preset.

    After navigating to the target, a right swipe unlocks the camera from
    auto-follow mode, the detail card is dismissed, and then the zoom button
    is tapped repeatedly each iteration.

    Args:
        device: uiautomator2 device.
        memory_tool: MemoryTool instance.
        location: Key in LOCATIONS (e.g. "edinburgh", "paris"). None = DEFAULT_LOCATION.
    """
    location = location or DEFAULT_LOCATION
    if location not in LOCATIONS:
        raise ValueError(
            f"Unknown zoom location '{location}'. Available: {list(LOCATIONS)}"
        )

    config = LOCATIONS[location]
    logging.info(f"Zoom location: {config['label']} ({location})")

    _navigate_to_target(device, config["search_query"])

    # Swipe right from screen centre to detach the camera from auto-follow
    width = device.info.get("displayWidth", 1080)
    height = device.info.get("displayHeight", 2400)
    cx, cy = width // 2, height // 2
    device.swipe(cx, cy, cx + 300, cy, duration=0.3)
    time.sleep(1)

    shared.tap_x_button(device)
    time.sleep(1)

    device.click(ZOOM_BUTTON_X, ZOOM_BUTTON_Y)
    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")
        for _zoom_out in range(0, 20):
            time.sleep(0.1)
            device.click(976, 1392)

        for _zoom_in in range(0, 20):
            time.sleep(0.1)
            device.click(976, 1053)

    memory_tool.stop_monitoring()


def _navigate_to_target(device, search_query):
    shared.tap_search_bar(device)
    shared.set_search_text(device, search_query)
    time.sleep(1)
    shared.select_first_result(device)
    time.sleep(1)
