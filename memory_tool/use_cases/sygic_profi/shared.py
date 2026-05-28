import logging
import time
from pathlib import Path


SEARCH_BAR_ID = "SearchBar.Input"
SEARCH_FIELD_ID = "com.sygic.profi.beta:id/inputField"
MENU_ICON_ID = "SearchBar.MenuIcon"
PROFILE_ICON_ID = "SearchBar.ProfileIcon"


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
    Tap the top-bar search area when SearchBar.Input is not individually exposed.

    Some app states render the menu/profile icons but do not expose the center
    search bar as a separate UIAutomator node. In that case, tap the visual
    search-bar area between the visible chrome elements.
    """
    menu_icon = device(resourceId=MENU_ICON_ID)
    profile_icon = device(resourceId=PROFILE_ICON_ID)

    menu_center = _get_selector_center(menu_icon) if menu_icon.exists(timeout=1) else None
    profile_center = _get_selector_center(profile_icon) if profile_icon.exists(timeout=1) else None
    if menu_center is None and profile_center is None:
        return False

    width = device.info.get("displayWidth", 1080)
    height = device.info.get("displayHeight", 2400)
    x = width // 2
    y = int(height * 0.10)

    if menu_center is not None and profile_center is not None:
        x = (menu_center[0] + profile_center[0]) // 2
        y = (menu_center[1] + profile_center[1]) // 2
    elif menu_center is not None:
        y = menu_center[1]
    elif profile_center is not None:
        y = profile_center[1]

    logging.info("SearchBar.Input missing; tapping fallback search area at (%s, %s)", x, y)
    device.click(x, y)
    return True


def dismiss_route_restore_popup(device) -> bool:
    """
    Detect and dismiss the "Are you still heading to ...?" popup that Sygic
    shows when the app starts with a leftover route from a previous session.

    The popup has two textual buttons (no resourceId): "Continue" and "Cancel
    route". We always pick "Cancel route" so tests start from a clean state.

    Returns True if the popup was found and dismissed.
    """
    if not device(textContains="Are you still heading to").exists(timeout=1):
        return False

    logging.info("Detected 'Are you still heading to' popup — clicking Cancel route")
    cancel_route = device(text="Cancel route")
    if cancel_route.exists(timeout=2):
        cancel_route.click()
        time.sleep(2)
        return True

    logging.warning("Restore-route popup detected but Cancel route button not clickable")
    return False


def wait_for_map_ready(device, timeout: int = 30) -> bool:
    """
    Wait until the Sygic main map chrome is visible.

    First dismiss the "Are you still heading to ...?" popup if present, since
    it blocks the main map from rendering. Then SearchBar.Input is preferred,
    but menu/profile icons also count as "ready" because some app states
    expose the top bar without exposing the center input node. If the chrome
    doesn't appear, try a recovery pass: cancel any active route via the
    InfoBar bottom sheet, press back a couple of times to dismiss overlays,
    then retry. Dumps the UI hierarchy if everything fails.
    """
    dismiss_route_restore_popup(device)

    if (
        device(resourceId=SEARCH_BAR_ID).exists(timeout=timeout)
        or device(resourceId=MENU_ICON_ID).exists(timeout=1)
        or device(resourceId=PROFILE_ICON_ID).exists(timeout=1)
    ):
        return True

    # Popup may render late — retry once after the initial wait.
    if dismiss_route_restore_popup(device) and (
        device(resourceId=SEARCH_BAR_ID).exists(timeout=5)
        or device(resourceId=MENU_ICON_ID).exists(timeout=1)
        or device(resourceId=PROFILE_ICON_ID).exists(timeout=1)
    ):
        return True

    logging.warning("SearchBar.Input not visible after %ss — attempting recovery", timeout)

    try:
        expand = device(resourceId="InfoBarBottomSheet.Button.Expand")
        if expand.exists(timeout=2):
            expand.click()
            time.sleep(1)
        cancel_route = device(resourceId="InfoBarBottomSheet.Button.Cancel route")
        if cancel_route.exists(timeout=2):
            cancel_route.click()
            logging.info("Cancelled active route during map-ready recovery")
            time.sleep(2)
    except Exception as e:
        logging.debug("Route cancel during recovery failed: %s", e)

    for _ in range(3):
        if (
            device(resourceId=SEARCH_BAR_ID).exists(timeout=2)
            or device(resourceId=MENU_ICON_ID).exists(timeout=1)
            or device(resourceId=PROFILE_ICON_ID).exists(timeout=1)
        ):
            return True
        try:
            device.press("back")
        except Exception as e:
            logging.debug("Back press during recovery failed: %s", e)
        time.sleep(1)

    if (
        device(resourceId=SEARCH_BAR_ID).exists(timeout=5)
        or device(resourceId=MENU_ICON_ID).exists(timeout=1)
        or device(resourceId=PROFILE_ICON_ID).exists(timeout=1)
    ):
        return True

    dump_hierarchy(device, "sygic_map_not_ready")
    return False


def tap_search_bar(device):
    """
    Wait for the map to be ready, then tap the Sygic search bar.

    Raises:
        RuntimeError: if the search bar never appears (hierarchy is dumped to
            output/_debug_sygic_map_not_ready.xml for inspection).
    """
    search_field = device(resourceId=SEARCH_FIELD_ID)
    if search_field.exists(timeout=2):
        search_field.click()
        return

    if not wait_for_map_ready(device):
        raise RuntimeError(
            "Sygic main map screen not ready: SearchBar.Input never appeared. "
            "Inspect output/_debug_sygic_map_not_ready.xml."
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

    dump_hierarchy(device, "sygic_search_bar_missing")
    raise RuntimeError(
        "Sygic search bar is not accessible even though the map appears ready. "
        "Inspect output/_debug_sygic_search_bar_missing.xml."
    )


def set_search_text(device, input_text):
    """
    Sets the text in the search input field.

    Args:
        device: The device object.
        input_text (str): The text to enter.
    """
    device(resourceId="com.sygic.profi.beta:id/inputField").set_text(input_text)

def select_first_result(device):
    """
    Clicks on the first search result in the list.

    Args:
        device: The device object.
    """
    device(resourceId="com.sygic.profi.beta:id/recyclerView").child(index=0).click()

def tap_x_button(device):
    """
    Taps the 'X' button to close a detail view.

    Args:
        device: The device object.
    """
    device.xpath('//*[@resource-id="PoiDetail.Close"]').click()


def read_about_screen(device):
    """
    Navigate to the About screen, dump the UI hierarchy, and return to the map.

    Returns:
        {"ui_hierarchy": "<XML dump>"} — used by app_info.py to extract the SDK version.
    """
    # The About screen lives behind the main map's menu — wait for the map first.
    if not wait_for_map_ready(device):
        raise RuntimeError(
            "Sygic main map screen not ready before About navigation. "
            "Inspect output/_debug_sygic_map_not_ready.xml."
        )

    # Menu - Settings - Info - About
    menu_icon = device(resourceId=MENU_ICON_ID)
    profile_icon = device(resourceId=PROFILE_ICON_ID)
    if menu_icon.exists(timeout=3):
        menu_icon.click()
    elif profile_icon.exists(timeout=3):
        logging.info("SearchBar.MenuIcon not found, using SearchBar.ProfileIcon")
        profile_icon.click()
    else:
        dump_hierarchy(device, "sygic_about_no_menu_icon")
        raise RuntimeError(
            "Neither SearchBar.MenuIcon nor SearchBar.ProfileIcon was found"
        )
    device(resourceId="MainMenu.Settings").click()
    device(resourceId="Settings.Info").click()
    device(resourceId="Settings.Info.About").click()
    device(resourceId="Settings.Info.Product").click()

    ui_hierarchy = ""
    try:
        ui_hierarchy = device.dump_hierarchy(compressed=False)
    except Exception as e:
        logging.warning(f"Failed to dump About UI hierarchy: {e}")

    # Get back to map
    device(resourceId="BackButton").click()
    device(resourceId="Settings.Back").click()
    device(resourceId="Settings.Back").click()
    device(resourceId="MainMenu.Back").click()

    return {"ui_hierarchy": ui_hierarchy}
