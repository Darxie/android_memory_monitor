import subprocess
import logging
from pathlib import Path
from timestamp import ExecutionTimestamp


timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")

# Construct filenames with the timestamp
INFO_FILE = directory / f"app_info.txt"
JPEG_FILE = directory / f"app-about.jpg"


def execute_adb_command(command_list) -> str:
    """
    Executes an ADB command and returns the output as a string.

    Args:
        command_list (list): A list of strings representing the ADB command to execute.

    Returns:
        str: The output of the ADB command as a string.

    """
    try:
        result = subprocess.run(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return result.stdout
    except Exception as e:
        logging.error(f"Error executing ADB command {command_list}: {e}")
        return ""


def get_app_pid(package_name) -> str:
    """
    Get the process ID (PID) for a given app package name.
    The PID is typically the second field, but it's best to check based
    on the layout of your `ps` output.

    :param package_name: Name of the app package.
    :return: PID as a string if found, None otherwise.
    """
    result = execute_adb_command(["adb", "shell", "ps", "-A"])

    if result:
        for line in result.splitlines():
            if package_name in line:
                parts = line.split()
                return parts[1]
    return "None"


def get_device_id() -> str:
    """
    Fetch the device ID for the connected device.

    :return: Device ID as a string if found, None otherwise.
    """
    result = execute_adb_command(["adb", "devices"])

    if result:
        lines = result.splitlines()
        if len(lines) > 2:
            return lines[1].split()[0]
    logging.warning("No devices found!")
    exit(1)


def print_app_info(device, package_name, use_case):
    app_info = device.app_info(package_name)
    device_id = get_device_id()
    pid = get_app_pid(package_name)

    logging.info(app_info)
    logging.info(f"Process ID: {pid}")
    logging.info(f"Device ID: {device_id}")

    take_info_about_screenshot(device)

    _write_to_file(INFO_FILE, f"Use case: {use_case}\n")
    _write_to_file(INFO_FILE, f"Device Info: \n{device.info}\n")
    _write_to_file(INFO_FILE, f"Device Code: {device_id}\n")
    _write_to_file(INFO_FILE, f"Application Info: \n{app_info}\n")


def _write_to_file(filename, content):
    """
    Append content to a file.

    :param filename: Name of the file.
    :param content: Content to append.
    """
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logging.error(f"Error writing to file {filename}: {e}")


def take_info_about_screenshot(device):
    # Menu - Settings - Info - About
    device.xpath(
        '//*[@resource-id="com.sygic.profi.beta:id/composeView_searchBar"]/android.view.View[1]/android.view.View[2]'
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[6]"
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[2]/android.view.View[5]"
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[2]/android.view.View[1]"
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[2]/android.view.View[1]"
    ).click()
    # Take screenshot
    device.screenshot(JPEG_FILE)
    # Get back to map
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[1]"
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[1]"
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[1]"
    ).click()
    device.xpath(
        "//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[1]"
    ).click()
