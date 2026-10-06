"""
Make sure the offline maps a use case needs are installed before monitoring starts.

Maps are requested through the app's own deep link ``com.sygic.aura://update|<isos>``
(DeeplinkActivity -> RuntimeAction.MapUpdate). It downloads missing maps and updates
installed ones, so it is safe to send on every run. ISO codes are the lowercase ones
the map manager uses in its ``MapItem.<iso>`` test tags: countries (``sk``, ``de`` —
split countries download all their regions) and US states (``us-sc``).

Progress is watched on Menu -> Maps: while anything downloads, the screen shows a
"Downloading. Don't turn off device." banner and "x GB / y GB" subtitles.
"""
import logging
import re
import time

from . import shared

DEEPLINK_ACTIVITY = "com.sygic.navi.navilink.deeplink.DeeplinkActivity"
DOWNLOADING_TEXT = "Downloading"
DOWNLOAD_TIMEOUT_SECONDS = 3600
POLL_SECONDS = 10
# Consecutive polls without the banner before downloads count as finished. The
# app needs a moment after the deep link before the first download starts.
IDLE_POLLS_TO_FINISH = 3
MAPS_MANAGER_OPEN_ATTEMPTS = 3
MAPS_MANAGER_LOAD_SECONDS = 60
INSTALLED_MAPS_BACK = "InstalledMaps.Back"
INSTALLED_REGIONS_BACK = "InstalledRegions.Back"
MAP_ITEM_PATTERN = re.compile(r'resource-id="MapItem\.([^"]+)"')
# Continent rows have no test tag: a title TextView followed by "<size> • N countries".
CONTINENT_ROW_PATTERN = re.compile(r'text="([^"]+)"[^>]*>\s*(?:</node>\s*)?<node[^>]*text="[^"]* • \d+ countr')
PROGRESS_PATTERN = re.compile(r'text="([^"]*\d GB / [^"]*)"')


def request_maps(adb, package_name, isos) -> None:
    """Ask the app to download/update the given maps via its deep link."""
    uri = "com.sygic.aura://update|" + ",".join(isos)
    logging.info("Requesting maps via deep link: %s", uri)
    # adb joins shell args into one device-side command; quote so '|' isn't a pipe.
    adb.shell(
        "am", "start",
        "-n", f"{package_name}/{DEEPLINK_ACTIVITY}",
        "-a", "android.intent.action.VIEW",
        "-d", f"'{uri}'",
    )


def finish_onboarding(device) -> None:
    """
    Get past the first-run "Download maps for offline use" screen.

    The app only lets the user continue once a map is installed or installing,
    so this must run after request_maps. No-op when the onboarding is not shown.
    """
    choose_country = device(text="Choose another country")
    if not choose_country.exists(timeout=3):
        return
    logging.info("First-run map onboarding detected")
    # The continent list has no Next button; the per-continent country list does.
    choose_country.click()
    time.sleep(2)
    shared.scroll_to_resource_id(device, "AddRegion.Europe").click(timeout=10)
    next_button = device(text="Next")
    if next_button.exists(timeout=10):
        next_button.click()
        logging.info("Finished first-run map onboarding")
        time.sleep(2)
    else:
        shared.dump_hierarchy(device, "onboarding_next_missing")
        logging.warning("Onboarding Next button not found; see output/_debug_onboarding_next_missing.xml")


def _open_installed_maps(device) -> None:
    """
    Open Menu -> Maps. With maps from a single continent it lands on the country
    list (InstalledMaps.*); with several continents on a continent list
    (InstalledRegions.*) whose rows open the per-continent country list.
    """
    either_screen = f'//*[@resource-id="{INSTALLED_MAPS_BACK}" or @resource-id="{INSTALLED_REGIONS_BACK}"]'
    for attempt in range(MAPS_MANAGER_OPEN_ATTEMPTS):
        if not shared.wait_for_map_ready(device):
            raise RuntimeError("Map screen not ready; cannot open Maps manager.")
        device(resourceId=shared.MENU_ICON_ID).click()
        device(resourceId="MainMenu.Maps").click()
        # Right after a map request the list can stay blank ("Maps" title only)
        # for over 30 s while the app checks/updates every requested map.
        if device.xpath(either_screen).wait(timeout=MAPS_MANAGER_LOAD_SECONDS):
            return
        logging.warning("Maps manager list not loaded (attempt %d); reopening", attempt + 1)
        device(resourceId="BackButton").click_exists(timeout=2)
        device(resourceId="MainMenu.Back").click_exists(timeout=2)
    shared.dump_hierarchy(device, "maps_manager_missing")
    raise RuntimeError("Maps manager did not open. Inspect output/_debug_maps_manager_missing.xml.")


def _close_installed_maps(device) -> None:
    """Back out of the Maps manager (and main menu) to the map screen."""
    for _ in range(4):
        for back_id in (INSTALLED_MAPS_BACK, INSTALLED_REGIONS_BACK, "MainMenu.Back"):
            if device(resourceId=back_id).click_exists(timeout=1):
                time.sleep(1)
                break
        else:
            return
    logging.warning("Still inside Maps manager / menu after backing out")


def _wait_for_downloads(device, timeout) -> bool:
    """Poll the Maps manager until the Downloading banner stays gone."""
    deadline = time.time() + timeout
    idle_polls = 0
    while time.time() < deadline:
        xml = device.dump_hierarchy(compressed=False)
        if DOWNLOADING_TEXT in xml:
            idle_polls = 0
            logging.info("Maps downloading: %s", ", ".join(PROGRESS_PATTERN.findall(xml)) or "in progress")
        else:
            idle_polls += 1
            if idle_polls >= IDLE_POLLS_TO_FINISH:
                return True
        time.sleep(POLL_SECONDS)
    return False


def _collect_by_scrolling(device, pattern) -> list:
    """Scroll to the end of the current list, returning pattern matches in order of appearance."""
    found = []
    for _ in range(30):
        visible = pattern.findall(device.dump_hierarchy(compressed=False))
        new = [v for v in visible if v not in found]
        if visible and not new:
            break
        found.extend(new)
        shared.scroll_list(device, up=True)
    return found


def _scroll_to_text(device, text) -> bool:
    """Bring a row with the given text on screen, searching back towards the top of the list."""
    for _ in range(30):
        if device(text=text).exists(timeout=1):
            return True
        shared.scroll_list(device, up=False)
    return False


def _installed_isos(device) -> set:
    """Collect MapItem.<iso> tags from the Maps manager (per continent when grouped)."""
    if not device(resourceId=INSTALLED_REGIONS_BACK).exists(timeout=2):
        return set(_collect_by_scrolling(device, MAP_ITEM_PATTERN))

    found = set()
    for continent in _collect_by_scrolling(device, CONTINENT_ROW_PATTERN):
        if not _scroll_to_text(device, continent):
            logging.warning("Continent row %r not found in Maps manager", continent)
            continue
        device(text=continent).click()
        if device(resourceId=INSTALLED_MAPS_BACK).exists(timeout=5):
            found.update(_collect_by_scrolling(device, MAP_ITEM_PATTERN))
            device(resourceId=INSTALLED_MAPS_BACK).click()
            device(resourceId=INSTALLED_REGIONS_BACK).exists(timeout=5)
    return found


def ensure_maps(device, adb, package_name, isos, timeout=DOWNLOAD_TIMEOUT_SECONDS) -> None:
    """
    Install/update the given maps and block until they are ready.

    Raises:
        RuntimeError: if downloads do not finish within the timeout or a map is
            still missing afterwards.
    """
    if not isos:
        return
    isos = sorted(set(isos))
    request_maps(adb, package_name, isos)
    time.sleep(3)
    finish_onboarding(device)

    _open_installed_maps(device)
    try:
        if not _wait_for_downloads(device, timeout):
            shared.dump_hierarchy(device, "maps_download_timeout")
            raise RuntimeError(f"Map downloads did not finish within {timeout}s")
        missing = set(isos) - _installed_isos(device)
        if missing:
            shared.dump_hierarchy(device, "maps_missing")
            raise RuntimeError(f"Maps still missing after download: {sorted(missing)}")
        logging.info("Required maps installed: %s", ", ".join(isos))
    finally:
        _close_installed_maps(device)
