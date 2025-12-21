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
