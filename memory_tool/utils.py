import subprocess
import logging
from pathlib import Path
from memory_tool.timestamp import ExecutionTimestamp

timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")

# Output file paths
INFO_FILE = directory / f"app_info.txt"
JPEG_FILE = directory / f"app-about.jpg"

# Constants for process lookup
MAX_PROCESS_LOOKUP_ATTEMPTS = 1


def execute_adb_command(command_list, timeout=30) -> str:
    """
    Execute an ADB command and return its output.
    
    Args:
        command_list: List of command arguments
        timeout: Command timeout in seconds
        
    Returns:
        Command stdout as string, or empty string on error
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
            timeout=timeout,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        logging.error(f"ADB command timed out: {' '.join(command_list)}")
        return ""
    except Exception as e:
        logging.error(f"Error executing ADB command: {e}")
        return ""


def get_app_pid(package_name) -> str:
    """
    Get the process ID for an app package name.
    
    Args:
        package_name: Android package name
        
    Returns:
        PID as string, or "None" if not found
    """
    try:
        result = execute_adb_command(["adb", "shell", "ps", "-A"])
        if not result:
            logging.warning(f"Could not retrieve process list for {package_name}")
            return "None"
            
        for line in result.splitlines():
            if package_name in line:
                parts = line.split()
                if len(parts) > 1:
                    return parts[1]
    except Exception as e:
        logging.error(f"Error getting PID for {package_name}: {e}")
    return "None"


def get_device_id() -> str:
    """
    Get the device ID for the connected device.
    
    Returns:
        Device ID string
        
    Raises:
        RuntimeError: If no device is found
    """
    try:
        result = execute_adb_command(["adb", "devices"])
        if result:
            lines = result.splitlines()
            if len(lines) > 2:
                device_id = lines[1].split()[0]
                if device_id and device_id != "List":
                    return device_id
        
        raise RuntimeError("No devices found in adb devices output")
    except Exception as e:
        logging.error(f"Error getting device ID: {e}")
        raise


def _write_to_file(filename, content) -> bool:
    """
    Append content to a file.
    
    Args:
        filename: File path to append to
        content: Content to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error writing to file {filename}: {e}")
        return False


def print_app_info(device, package_name, use_case, screenshot_callback=None):
    """
    Log and save application and device information.
    
    Args:
        device: uiautomator2 device object
        package_name: App package name
        use_case: Current test use case
        screenshot_callback: Optional callback to take screenshots
    """
    try:
        app_info = device.app_info(package_name)
        device_id = get_device_id()
        pid = get_app_pid(package_name)

        logging.info(f"Device: {device_id}")
        logging.info(f"PID: {pid}")
        logging.info(f"App Info: {app_info}")

        # Take screenshot if callback provided
        if screenshot_callback:
            try:
                screenshot_callback(device, JPEG_FILE)
                logging.info(f"Screenshot saved to {JPEG_FILE}")
            except Exception as e:
                logging.warning(f"Failed to take screenshot: {e}")

        # Write info to file
        info_lines = [
            f"Use case: {use_case}\n",
            f"Device: {device_id}\n",
            f"PID: {pid}\n",
            f"Device Info:\n{device.info}\n",
            f"App Info:\n{app_info}\n",
        ]
        
        for line in info_lines:
            _write_to_file(INFO_FILE, line)
            
    except Exception as e:
        logging.error(f"Error printing app info: {e}", exc_info=True)
