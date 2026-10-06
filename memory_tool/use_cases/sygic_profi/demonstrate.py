import time
import logging
from . import shared

# Offline maps installed by the runner before monitoring (see maps.py).
REQUIRED_MAPS = ["sk", "at", "de"]

BOTTOM_SHEET_CONTENT_ID = "com.sygic.profi.volvo:id/routePlannerDetailBottomSheetContent"
DEMONSTRATE_ROUTE_RESOURCE_IDS = [
    "InfoBarBottomSheet.Button.Demonstrate route",
    "InfoBarBottomSheet.Button.Demonstrate Route",
]
DEMONSTRATE_ROUTE_TEXT = "Demonstrate route"
# Stable markers that the Volvo route-planner screen is up (Get directions ->
# route calculated). On this screen the Demonstrate route button is a plain
# clickable View (no resource-id) inside a scrollable list.
ROUTE_PLANNER_READY_IDS = [
    "RoutePlannerBottomSheetContent.Box",
    "RoutePlannerToolbar.BackButton",
    "RoutePlanner.RouteSelect",
]
# Each attempt scrolls the planner panel once; landscape needs ~3 drags to reach the button.
DEMONSTRATE_BUTTON_ATTEMPTS = 6
DEMONSTRATION_SECONDS_FULL = 43200  # 12 hours
DEMONSTRATION_SECONDS_DRY_RUN = 60  # 5 minutes


def _expand_route_bottom_sheet(device):
    """Expand route bottom sheet using stable selectors where possible (legacy builds)."""
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


def _dismiss_route_warning(device, timeout=2):
    """
    Dismiss the Volvo "route violated your vehicle settings" warning dialog.

    Volvo/truck vehicle profiles show a modal "Attention!" dialog with an
    "OK, got it" button after the route is calculated. It blocks the route
    bottom sheet (and thus the Demonstrate route button) and can appear several
    seconds after Get directions is tapped, so callers poll for it.

    Returns True if the dialog was found and dismissed.
    """
    warning = device(text="OK, got it")
    if warning.exists(timeout=timeout):
        warning.click()
        logging.info("Dismissed 'route violates vehicle settings' warning")
        time.sleep(1)
        return True
    return False


def _demonstrate_route_xpath(device):
    """XPath handle to the Demonstrate route control on the Volvo route planner.

    The button is a clickable View wrapping a "Demonstrate route" TextView with
    no resource-id. UiSelector text matching is unreliable on this Compose
    screen, but XPath (which parses the dumped hierarchy directly) matches it.
    """
    return device.xpath(f'//*[@text="{DEMONSTRATE_ROUTE_TEXT}"]')


def _expand_route_planner_sheet(device) -> bool:
    """
    Expand / scroll the Volvo route-planner sheet to reveal its buttons.

    In landscape the planner is a left-side panel whose content (Demonstrate
    route sits at the bottom) needs a few drags to scroll into view; dismissing
    the vehicle-settings warning also collapses it. Drag upwards inside the
    panel, horizontally centred on RoutePlannerBottomSheetContent.Box — a drag
    in the middle of the screen would only pan the map. Returns True if the
    sheet was found and a drag was issued.
    """
    box = device(resourceId="RoutePlannerBottomSheetContent.Box")
    if not box.exists(timeout=2):
        return False

    width, height = device.window_size()
    x = width // 2
    try:
        bounds = box.info.get("visibleBounds") or box.info.get("bounds") or {}
        if bounds.get("left") is not None and bounds.get("right") is not None:
            x = (bounds["left"] + bounds["right"]) // 2
    except Exception as e:
        logging.debug("Failed to read route-planner sheet bounds: %s", e)

    # input swipe instead of device.swipe(): the latter crashes uiautomator2 on some devices.
    device.shell(["input", "swipe", str(x), str(int(height * 0.88)), str(x), str(int(height * 0.3)), "300"])
    time.sleep(1)
    return True


def _route_planner_ready(device) -> bool:
    """True if the route-planner screen (or legacy route bottom sheet) is up."""
    if _demonstrate_route_xpath(device).exists:
        return True
    for resource_id in DEMONSTRATE_ROUTE_RESOURCE_IDS + ROUTE_PLANNER_READY_IDS:
        if device(resourceId=resource_id).exists(timeout=1):
            return True
    if device(resourceId="InfoBarBottomSheet.Button.Expand").exists(timeout=1):
        return True
    return device(resourceId=BOTTOM_SHEET_CONTENT_ID).exists(timeout=1)


def _wait_for_route_ready(device, timeout=60):
    """
    Wait until the route is calculated and the route-planner screen is ready.

    Route calculation can take tens of seconds, and a Volvo vehicle-settings
    violation dialog may appear mid-way and must be dismissed. Poll until either
    the Demonstrate route control / route-planner screen appears or the timeout
    expires, dismissing the warning dialog whenever it shows.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        _dismiss_route_warning(device, timeout=1)
        if _route_planner_ready(device):
            return
    logging.warning("Route planner not detected within %ss; proceeding anyway", timeout)


def _click_demonstrate_route(device):
    """
    Click Demonstrate route.

    Legacy builds exposed it as an InfoBarBottomSheet resource-id. The Volvo
    route-planner screen renders it as a plain clickable View (no resource-id)
    holding a "Demonstrate route" TextView. Click the label via XPath (resolves
    to its clickable parent). The button can be hidden by a late vehicle-settings
    warning or by the bottom sheet collapsing after that warning is dismissed, so
    each retry both dismisses the warning and expands the sheet.
    """
    for _ in range(DEMONSTRATE_BUTTON_ATTEMPTS):
        for resource_id in DEMONSTRATE_ROUTE_RESOURCE_IDS:
            candidate = device(resourceId=resource_id)
            if candidate.exists(timeout=2):
                candidate.click()
                return

        # Volvo route-planner screen: click the label via XPath, which resolves
        # to its clickable parent.
        button = _demonstrate_route_xpath(device)
        if button.wait(timeout=3):
            button.click()
            return

        # Button not visible. Recover from the two Volvo route-planner states
        # that hide it: a late vehicle-settings warning covering it, or the
        # bottom sheet collapsing (which happens after the warning is dismissed).
        dismissed = _dismiss_route_warning(device, timeout=2)
        expanded = _expand_route_planner_sheet(device)
        if dismissed or expanded:
            continue
        break

    hierarchy = device.dump_hierarchy(compressed=False)
    logging.error("Could not find Demonstrate route button. Current hierarchy:\n%s", hierarchy)
    raise RuntimeError("Demonstrate route button not found")


DEFAULT_DESTINATION = "51.19091873759982, 6.892719499268459"


def start_demonstration(device, destination_text=DEFAULT_DESTINATION):
    """
    Search a destination, request directions, and start the Demonstrate route.

    Reusable by demonstrate-based use cases (e.g. navi_fg_bg). Handles the Volvo
    route-planner flow, including the late vehicle-settings warning and the
    collapsing bottom sheet. Returns once the demonstration has been started.
    """
    shared.tap_search_bar(device)

    device(focused=True).set_text(destination_text)
    try:
        shared.select_first_result(device)
    except RuntimeError:
        pass  # coordinates may auto-resolve; GetDirections appears directly

    time.sleep(1)

    device(resourceId="SearchDestination.GetDirections").click()

    # Route calculation takes tens of seconds and (on Volvo truck profiles) may
    # pop a "route violates vehicle settings" dialog that must be dismissed
    # before the route planner is reachable.
    _wait_for_route_ready(device)
    time.sleep(1)
    _click_demonstrate_route(device)
    logging.info("Demonstration started")


def cancel_route(device):
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
    start_demonstration(device)

    duration = DEMONSTRATION_SECONDS_DRY_RUN if memory_tool.dry_run else DEMONSTRATION_SECONDS_FULL
    logging.info("Running demonstration for %s seconds", duration)
    time.sleep(duration)

    cancel_route(device)
