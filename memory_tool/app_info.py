import re
import html
import logging
from pathlib import Path
from typing import Optional

from memory_tool.adb import AdbDevice, get_app_pid
from memory_tool.timestamp import ExecutionTimestamp
from memory_tool.utils import _write_to_file

SDK_PATTERN = re.compile(r"SDK\s+(\d+(?:\.\d+)+)", re.IGNORECASE)


def _get_output_info_path() -> Path:
    run_timestamp = ExecutionTimestamp.get_timestamp()
    return Path(f"output/{run_timestamp}") / "app_info.txt"


def _extract_text_from_ui_hierarchy(ui_hierarchy: str) -> str:
    """Extract visible text values from a uiautomator XML hierarchy dump."""
    if not ui_hierarchy:
        return ""

    texts = re.findall(r'text="([^"]*)"', ui_hierarchy)
    lines = []
    seen = set()
    for text in texts:
        value = html.unescape(text).strip()
        if len(value) < 2:
            continue
        lower = value.lower()
        if lower in seen:
            continue
        seen.add(lower)
        lines.append(value)
    return "\n".join(lines)


def _extract_sdk(device, read_about) -> Optional[str]:
    """Open the About screen via read_about callback and pull the SDK version."""
    if read_about is None:
        return None
    try:
        result = read_about(device)
    except Exception as e:
        logging.warning("About reader failed: %s", e)
        return None

    if not isinstance(result, dict):
        return None

    text = _extract_text_from_ui_hierarchy(result.get("ui_hierarchy", ""))
    if not text:
        return None

    match = SDK_PATTERN.search(text)
    return match.group(1) if match else None


def print_app_info(device, package_name: str, use_case: str, adb: AdbDevice, read_about=None):
    """
    Log and save application and device information.

    Args:
        device: uiautomator2 device object
        package_name: App package name
        use_case: Current test use case
        adb: AdbDevice instance targeting the correct device
        read_about: Optional callable(device) that opens the About screen and
            returns {"ui_hierarchy": "..."}; used solely to pull the SDK version.
    """
    try:
        info_file = _get_output_info_path()
        app_info = device.app_info(package_name)
        device_id = adb.device_code or device.serial
        pid = get_app_pid(package_name, adb)

        logging.info(f"Device: {device_id}")
        logging.info(f"PID: {pid}")
        logging.info(f"App Info: {app_info}")

        sdk_version = _extract_sdk(device, read_about)
        if sdk_version:
            logging.info(f"SDK: {sdk_version}")
        else:
            logging.warning("SDK version could not be extracted from About screen")

        info_lines = [
            f"Use case: {use_case}\n",
            f"Device: {device_id}\n",
            f"PID: {pid}\n",
            f"SDK: {sdk_version or 'unknown'}\n",
            f"Device Info:\n{device.info}\n",
            f"App Info:\n{app_info}\n",
        ]

        for line in info_lines:
            _write_to_file(info_file, line)

    except Exception as e:
        logging.error(f"Error printing app info: {e}", exc_info=True)
