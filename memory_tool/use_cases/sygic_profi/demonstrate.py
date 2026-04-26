import time
import logging
from . import shared

"""
NECESSARY MAPS - Slovakia, Austria, Germany
"""

BOTTOM_SHEET_CONTENT_ID = "com.sygic.profi.beta:id/routePlannerDetailBottomSheetContent"
DEMONSTRATE_ROUTE_RESOURCE_IDS = [
    "InfoBarBottomSheet.Button.Demonstrate route",
    "InfoBarBottomSheet.Button.Demonstrate Route",
]
DEMONSTRATION_SECONDS_FULL = 43200  # 12 hours
DEMONSTRATION_SECONDS_DRY_RUN = 300  # 5 minutes


def _expand_route_bottom_sheet(device):
    """Expand route bottom sheet using stable selectors where possible."""
    expand_button = device(resourceId="InfoBarBottomSheet.Button.Expand")
    if expand_button.exists(timeout=3):
        expand_button.click()
        return

    sheet = device(resourceId=BOTTOM_SHEET_CONTENT_ID)
    if sheet.exists(timeout=3):
        sheet.swipe("up")
        return

    # Last-resort gesture when element IDs are not exposed in this app state.
    width = device.info.get("displayWidth", 1080)
    height = device.info.get("displayHeight", 2400)
    device.swipe(width // 2, int(height * 0.92), width // 2, int(height * 0.62), 0.15)


def _click_demonstrate_route(device):
    """Click Demonstrate route, preferring resource IDs over localized text."""
    for resource_id in DEMONSTRATE_ROUTE_RESOURCE_IDS:
        candidate = device(resourceId=resource_id)
        if candidate.exists(timeout=2):
            candidate.click()
            return

    if device(text="Demonstrate route").exists(timeout=3):
        device(text="Demonstrate route").click()
        return

    hierarchy = device.dump_hierarchy(compressed=False)
    logging.error("Could not find Demonstrate route button. Current hierarchy:\n%s", hierarchy)
    raise RuntimeError("Demonstrate route button not found")


def _cancel_route(device):
    """Best-effort cancel of the active route after the timed run finishes."""
    try:
        expand = device(resourceId="InfoBarBottomSheet.Button.Expand")
        if expand.exists(timeout=2):
            expand.click()
            time.sleep(1)

        cancel_route = device(resourceId="InfoBarBottomSheet.Button.Cancel route")
        if cancel_route.exists(timeout=2):
            cancel_route.click()
            logging.info("canceled route")
            time.sleep(2)
        else:
            logging.info("Cancel route button not visible during cleanup")
    except Exception as e:
        logging.warning("Failed to cleanly cancel route: %s", e)


def run_test(device, memory_tool):
    """Search a destination, start Demonstrate route, run for a fixed duration, then cancel."""
    shared.tap_search_bar(device)

    device(focused=True).set_text("51.19091873759982, 6.892719499268459")
    if device(resourceId="com.sygic.profi.beta:id/searchItemTitle").exists(timeout=5):
        device(resourceId="com.sygic.profi.beta:id/searchItemTitle").click()

    time.sleep(1)

    device(resourceId="SearchDestination.GetDirections").click()

    if device(text="OK, got it").exists(timeout=10):
        device(text="OK, got it").click()

    _expand_route_bottom_sheet(device)
    time.sleep(1)
    _click_demonstrate_route(device)

    duration = DEMONSTRATION_SECONDS_DRY_RUN if memory_tool.dry_run else DEMONSTRATION_SECONDS_FULL
    logging.info("Demonstration started; running for %s seconds", duration)
    time.sleep(duration)

    _cancel_route(device)
