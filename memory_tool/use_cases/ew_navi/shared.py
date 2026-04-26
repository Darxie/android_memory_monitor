import logging


def tap_search_bar(device):
    """
    Taps on the search bar of the Sygic app.

    Args:
        device: The device object representing the Android device.
    """
    device(resourceId="FreeDrive.SearchBar").click()

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
