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


def take_about_screenshot(device, file_path):
    """
    Navigates to the About screen, takes a screenshot, and returns to the map.

    Args:
        device: The device object.
        file_path: Path to save the screenshot.
    """
    # Menu - Settings - Info - About
    device(resourceId="FreeDrive.Avatar").click()
    device(text="Settings").click()
    device(text="Info").click()
    device(text="About").click()
    device(text="Product").click()
    # Take screenshot
    device.screenshot(file_path)
    # Get back to map
    # Back button is at bounds [19,155][145,281], center (82, 218)
    device.click(82, 218)
    device.click(82, 218)
    device.click(82, 218)
    device.click(82, 218)
