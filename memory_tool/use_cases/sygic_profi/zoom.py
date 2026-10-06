import logging
import re
import time
from . import shared


ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 5
CLICKS_PER_DIRECTION = 20

ZOOM_CONTROLS_ID = "ZoomControlsCollapsed"
BOUNDS_PATTERN = re.compile(
    rf'resource-id="{ZOOM_CONTROLS_ID}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
)

# Variant-aware: the runner reads LOCATIONS to know this use case has variants.
# Each entry must have a search_query the in-app search bar can resolve, and
# required_maps (map-manager ISO codes) installed before the run.
LOCATIONS = {
    "nepal": {
        "label": "Nepal (Mt. Everest)",
        "search_query": "27°55'40.5\"N 86°53'07.5\"E",
        "maps": "Nepal",
        "required_maps": ["np"],
    },
    "paris": {
        "label": "Paris (Tour Eiffel)",
        "search_query": "Tour Eiffel",
        "maps": "France",
        "required_maps": ["fr"],
    },
}
DEFAULT_LOCATION = "nepal"


def run_test(device, memory_tool, location=None):
    """
    Search the location, then zoom out and back in with the on-map +/- buttons.

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
    time.sleep(2)

    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")
        zoom_in, zoom_out = _zoom_buttons(device)
        for _zoom_out in range(CLICKS_PER_DIRECTION):
            device.click(*zoom_out)
        for _zoom_in in range(CLICKS_PER_DIRECTION):
            device.click(*zoom_in)

    memory_tool.stop_monitoring()


def _navigate_to_target(device, search_query):
    shared.tap_search_bar(device)
    shared.set_search_text(device, search_query)
    time.sleep(1)
    shared.select_first_result(device)


def _control_buttons(device) -> list:
    """(left, top, right, bottom) of every ZoomControlsCollapsed node, from one hierarchy dump."""
    xml = device.dump_hierarchy(compressed=False)
    return [tuple(map(int, m)) for m in BOUNDS_PATTERN.findall(xml)]


def _zoom_buttons(device):
    """
    Expand the map zoom controls and return the centres of (+, -).

    Collapsed, the controls are a single "±" button; tapping it expands a column
    of +, 3D, - buttons. All of them (and the unrelated sound button on the left)
    share the ZoomControlsCollapsed test tag, so + / - are picked by position:
    the right-most column, top and bottom. The column collapses again after a few
    seconds without interaction, so this runs before every zoom sequence.
    """
    for _ in range(3):
        buttons = _control_buttons(device)
        if buttons:
            right_x = max(b[0] for b in buttons)
            column = sorted((b for b in buttons if b[0] == right_x), key=lambda b: b[1])
            if len(column) >= 3:
                plus, minus = column[0], column[-1]
                return _centre(plus), _centre(minus)
            device.click(*_centre(column[0]))
            time.sleep(1)
    shared.dump_hierarchy(device, "zoom_controls_missing")
    raise RuntimeError("Zoom controls did not expand. Inspect output/_debug_zoom_controls_missing.xml.")


def _centre(bounds):
    left, top, right, bottom = bounds
    return (left + right) // 2, (top + bottom) // 2
