import logging

def tap_search_bar(device):
    """
    Taps on the search bar of the Sygic app.

    Args:
        device: The device object representing the Android device.
    """
    device(resourceId="SearchBar.Input").click()

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
    # Menu - Settings - Info - About
    menu_icon = device(resourceId="SearchBar.MenuIcon")
    profile_icon = device(resourceId="SearchBar.ProfileIcon")
    if menu_icon.exists(timeout=3):
        menu_icon.click()
    elif profile_icon.exists(timeout=3):
        logging.info("SearchBar.MenuIcon not found, using SearchBar.ProfileIcon")
        profile_icon.click()
    else:
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
