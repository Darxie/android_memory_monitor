import logging
import time
from pathlib import Path


SEARCH_BAR_ID = "FreeDrive.SearchBar"
SEARCH_FIELD_ID = "com.roadlords.android:id/inputField"
AVATAR_ID = "FreeDrive.Avatar"


def dump_hierarchy(device, name: str) -> None:
    """Save current UI hierarchy to output/_debug_<name>.xml for offline inspection."""
    try:
        xml = device.dump_hierarchy(compressed=False)
        out = Path(f"output/_debug_{name}.xml")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(xml, encoding="utf-8")
        logging.warning("Dumped UI hierarchy to %s", out)
    except Exception as e:
        logging.warning("Failed to dump hierarchy: %s", e)


def _get_selector_center(selector):
    """Return selector center coordinates from uiautomator bounds info, if available."""
    try:
        info = selector.info
    except Exception as e:
        logging.debug("Failed to read selector info: %s", e)
        return None

    bounds = info.get("visibleBounds") or info.get("bounds") or {}
    left = bounds.get("left")
    right = bounds.get("right")
    top = bounds.get("top")
    bottom = bounds.get("bottom")
    if left is None or right is None or top is None or bottom is None:
        return None
    return ((left + right) // 2, (top + bottom) // 2)


def _tap_search_bar_fallback(device) -> bool:
    """
    Tap the top-bar search area when FreeDrive.SearchBar is not individually exposed.

    Uses the Avatar icon's vertical position to locate the search bar row, and
    taps horizontally centred on the screen.
    """
    avatar = device(resourceId=AVATAR_ID)
    avatar_center = _get_selector_center(avatar) if avatar.exists(timeout=1) else None
    if avatar_center is None:
        return False

    width = device.info.get("displayWidth", 1080)
    x = width // 2
    y = avatar_center[1]

    logging.info("FreeDrive.SearchBar missing; tapping fallback search area at (%s, %s)", x, y)
    device.click(x, y)
    return True


def wait_for_map_ready(device, timeout: int = 30) -> bool:
    """
    Wait until the EW Navi main map chrome is visible.

    Waits for FreeDrive.SearchBar or FreeDrive.Avatar. If neither appears,
    performs a recovery pass (back-button presses) and retries.
    Dumps the UI hierarchy if everything fails.
    """
    if (
        device(resourceId=SEARCH_BAR_ID).exists(timeout=timeout)
        or device(resourceId=AVATAR_ID).exists(timeout=1)
    ):
        return True

    logging.warning("FreeDrive.SearchBar not visible after %ss — attempting recovery", timeout)

    for _ in range(3):
        if (
            device(resourceId=SEARCH_BAR_ID).exists(timeout=2)
            or device(resourceId=AVATAR_ID).exists(timeout=1)
        ):
            return True
        try:
            device.press("back")
        except Exception as e:
            logging.debug("Back press during recovery failed: %s", e)
        time.sleep(1)

    if (
        device(resourceId=SEARCH_BAR_ID).exists(timeout=5)
        or device(resourceId=AVATAR_ID).exists(timeout=1)
    ):
        return True

    dump_hierarchy(device, "ew_navi_map_not_ready")
    return False


def tap_search_bar(device):
    """
    Wait for the map to be ready, then tap the EW Navi search bar.

    Raises:
        RuntimeError: if the search bar never appears (hierarchy is dumped to
            output/_debug_ew_navi_map_not_ready.xml for inspection).
    """
    search_field = device(resourceId=SEARCH_FIELD_ID)
    if search_field.exists(timeout=2):
        search_field.click()
        return

    if not wait_for_map_ready(device):
        raise RuntimeError(
            "EW Navi main map screen not ready: FreeDrive.SearchBar never appeared. "
            "Inspect output/_debug_ew_navi_map_not_ready.xml."
        )

    search_bar = device(resourceId=SEARCH_BAR_ID)
    if search_bar.exists(timeout=3):
        search_bar.click()
        return

    if _tap_search_bar_fallback(device):
        if search_field.exists(timeout=5):
            search_field.click()
            return
        if search_bar.exists(timeout=2):
            search_bar.click()
            return

    dump_hierarchy(device, "ew_navi_search_bar_missing")
    raise RuntimeError(
        "EW Navi search bar is not accessible even though the map appears ready. "
        "Inspect output/_debug_ew_navi_search_bar_missing.xml."
    )

def set_search_text(device, input_text):
    """
    Sets the text in the search input field.

    Args:
        device: The device object.
        input_text (str): The text to enter.
    """
    device(resourceId="com.roadlords.android:id/inputField").set_text(input_text)

def select_first_result(device):
    """
    Clicks on the first search result in the list.

    Args:
        device: The device object.
    """
    # Click at center of bounds [0,370][1080,644] -> (540, 507)
    device.click(540, 507)

def tap_x_button(device):
    """
    Taps the 'X' button to close a detail view.

    Args:
        device: The device object.
    """
    device(resourceId="SearchBar.CloseButton").click()


def read_about_screen(device):
    """
    Navigate to the About screen, dump the UI hierarchy, and return to the map.

    Returns:
        {"ui_hierarchy": "<XML dump>"} — used by app_info.py to extract the SDK version.
    """
    # Menu - Settings - Info - About
    device(resourceId="FreeDrive.Avatar").click()
    device(text="Settings").click()
    device(text="Info").click()
    device(text="About").click()
    device(text="Product").click()

    ui_hierarchy = ""
    try:
        ui_hierarchy = device.dump_hierarchy(compressed=False)
    except Exception as e:
        logging.warning(f"Failed to dump About UI hierarchy: {e}")

    # Back to map (4 back-button presses; bounds [19,155][145,281], center 82,218)
    for _ in range(4):
        device.click(82, 218)

    return {"ui_hierarchy": ui_hierarchy}
