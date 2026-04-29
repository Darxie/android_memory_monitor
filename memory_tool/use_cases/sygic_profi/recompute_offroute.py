"""
Off-route recompute test.

Computes a long route from the device's start location to a far destination,
then starts a Mock Locations saved-route preset that pulls the GPS feed
*backwards* across the planned route. Sygic continuously recomputes because
the device is constantly off-route — exercises the recompute memory paths.

Requirements:
    1. Mock Locations app (ru.gavrikov.mocklocations) installed.
    2. Developer Options → Select mock location app → Mock Locations.
    3. A saved route preset in Mock Locations covering 
        City Stade Brun, Bordeaux, France → Vlak bus shopping, Banska Bystrica, Slovakia
    4. Sygic must already have necessary maps downloaded (see use_cases.json).

The Mock Locations selectors below are best-guess. The first time you run this,
buttons that can't be found will dump the current UI hierarchy to
`output/_debug_<name>.xml` so you can pick correct selectors.

Necessary maps: France, Germany, Slovakia, Austria, Switzerland, Czechia
"""
import time
import logging
from pathlib import Path
from . import shared

# Test duration
DURATION_SECONDS_FULL = 36000   # 10 hours
DURATION_SECONDS_DRY_RUN = 300  # 5 minutes for dashboard validation

# Sygic destination — long route from device's location toward this point
ROUTE_DEST_QUERY = "Paris, France"

# Sygic
SYGIC_PACKAGE = "com.sygic.profi.beta"
SYGIC_ACTIVITY = "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity"

# Mock Locations
MOCK_LOCATIONS_PACKAGE = "ru.gavrikov.mocklocations"
SAVED_ROUTE_NAME = "bordeaux-banska"  # Name of the saved route preset to load

# --- Mock Locations UI selectors ---
# Validate after first run via the _debug_*.xml dumps in output/.
SAVED_ROUTES_BUTTON_CANDIDATES = [
    {"resourceId": "ru.gavrikov.mocklocations:id/button_save"}
]
RUN_BUTTON_CANDIDATES = [
    {"resourceId": "ru.gavrikov.mocklocations:id/runButton"},
    {"text": "Run!"},
]
STOP_BUTTON_CANDIDATES = [
    {"resourceId": "ru.gavrikov.mocklocations:id/stop_button"},
    {"description": "Stop"},
    {"text": "STOP"},
]


def run_test(device, memory_tool):
    """Compute Sygic route → start mock GPS feed → start navigation → wait → cleanup."""
    _setup_sygic_route(device)
    _start_mock_location(device, memory_tool)
    _bring_sygic_to_foreground(memory_tool)
    _start_navigation(device)

    duration = DURATION_SECONDS_DRY_RUN if memory_tool.dry_run else DURATION_SECONDS_FULL
    logging.info("Off-route recompute test running for %s seconds", duration)
    time.sleep(duration)

    _stop_mock_location(device, memory_tool)
    _bring_sygic_to_foreground(memory_tool)
    _cancel_route(device)


def _setup_sygic_route(device):
    """Search a far destination, hit Get directions, leave route active."""
    shared.tap_search_bar(device)
    device(focused=True).set_text(ROUTE_DEST_QUERY)

    if device(resourceId="com.sygic.profi.beta:id/searchItemTitle").exists(timeout=5):
        device(resourceId="com.sygic.profi.beta:id/searchItemTitle").click()
    time.sleep(1)

    device(resourceId="SearchDestination.GetDirections").click()

    if device(text="OK, got it").exists(timeout=10):
        device(text="OK, got it").click()

    time.sleep(3)
    logging.info("Sygic route to %s computed and active", ROUTE_DEST_QUERY)


def _start_mock_location(device, memory_tool):
    """Force-stop Mock Locations for a clean state, then launch and start the saved route."""
    memory_tool.adb.shell("am", "force-stop", MOCK_LOCATIONS_PACKAGE)
    time.sleep(1)

    memory_tool.adb.shell("monkey", "-p", MOCK_LOCATIONS_PACKAGE, "1")
    time.sleep(3)

    if not _try_click(device, SAVED_ROUTES_BUTTON_CANDIDATES):
        _dump_hierarchy(device, "mock_loc_no_saved_routes_btn")
        raise RuntimeError(
            "Mock Locations: saved-routes button not found. "
            "Inspect output/_debug_mock_loc_no_saved_routes_btn.xml and update "
            "SAVED_ROUTES_BUTTON_CANDIDATES."
        )
    time.sleep(2)

    if not _try_click(device, [{"text": SAVED_ROUTE_NAME}]):
        _dump_hierarchy(device, "mock_loc_no_saved_route")
        raise RuntimeError(
            f"Mock Locations: saved route '{SAVED_ROUTE_NAME}' not found. "
            "Inspect output/_debug_mock_loc_no_saved_route.xml and check "
            "SAVED_ROUTE_NAME."
        )
    time.sleep(2)

    if not _try_click(device, RUN_BUTTON_CANDIDATES):
        _dump_hierarchy(device, "mock_loc_no_run_btn")
        raise RuntimeError(
            "Mock Locations: Run button not found. "
            "Inspect output/_debug_mock_loc_no_run_btn.xml and update "
            "RUN_BUTTON_CANDIDATES."
        )

    logging.info("Mock location feed started")


def _stop_mock_location(device, memory_tool):
    """Bring Mock Locations to foreground and stop the simulation."""
    memory_tool.adb.shell("monkey", "-p", MOCK_LOCATIONS_PACKAGE, "1")
    time.sleep(2)

    if not _try_click(device, STOP_BUTTON_CANDIDATES):
        _dump_hierarchy(device, "mock_loc_no_stop_btn")
        logging.warning(
            "Mock Locations: Stop button not found, simulation may keep running. "
            "Inspect output/_debug_mock_loc_no_stop_btn.xml."
        )
    else:
        logging.info("Mock location feed stopped")


def _bring_sygic_to_foreground(memory_tool):
    memory_tool.adb.shell("am", "start", "-n", f"{SYGIC_PACKAGE}/{SYGIC_ACTIVITY}")
    time.sleep(2)


def _start_navigation(device):
    """After mock GPS is feeding, tap RouteSelect to begin live navigation."""
    if device(resourceId="RoutePlanner.RouteSelect").exists(timeout=5):
        device(resourceId="RoutePlanner.RouteSelect").click()
        logging.info("Sygic navigation started")
    else:
        logging.warning("RoutePlanner.RouteSelect not found - navigation may not have started")


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


def _try_click(device, candidates: list[dict]) -> bool:
    """Try a list of selector dicts; click the first one that exists. Returns True on hit."""
    for sel in candidates:
        if device(**sel).exists(timeout=2):
            device(**sel).click()
            logging.debug("clicked Mock Locations selector %s", sel)
            return True
    return False


def _dump_hierarchy(device, name: str) -> None:
    """Save current UI hierarchy to a debug file so we can iterate selectors offline."""
    try:
        xml = device.dump_hierarchy(compressed=False)
        out = Path(f"output/_debug_{name}.xml")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(xml, encoding="utf-8")
        logging.warning("Dumped UI hierarchy to %s", out)
    except Exception as e:
        logging.warning("Failed to dump hierarchy: %s", e)
