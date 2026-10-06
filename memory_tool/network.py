"""Run use cases offline: Wi-Fi and mobile data off for the duration, restored afterwards.

Measurements are taken offline so online services (traffic, online search, ads in
helper apps like Mock Locations) don't affect memory or UI flows. adb over USB is
not affected.
"""
import logging
import time
from contextlib import contextmanager

from memory_tool.adb import AdbDevice

OFFLINE_CHECK_TIMEOUT_SECONDS = 30


def _is_online(adb: AdbDevice) -> bool:
    return " 0% packet loss" in adb.shell("ping", "-c", "1", "-W", "2", "8.8.8.8", timeout=10)


@contextmanager
def device_offline(adb: AdbDevice):
    """Disable Wi-Fi and mobile data; re-enable whatever was on before when the block exits."""
    wifi_was_on = adb.shell("settings", "get", "global", "wifi_on").strip() not in ("", "0")
    data_was_on = adb.shell("settings", "get", "global", "mobile_data").strip() == "1"
    logging.info("Going offline (wifi was %s, mobile data was %s)",
                 "on" if wifi_was_on else "off", "on" if data_was_on else "off")
    adb.shell("svc", "wifi", "disable")
    adb.shell("svc", "data", "disable")

    deadline = time.time() + OFFLINE_CHECK_TIMEOUT_SECONDS
    while _is_online(adb) and time.time() < deadline:
        time.sleep(2)
    if _is_online(adb):
        logging.warning("Device still reaches the internet after disabling Wi-Fi and mobile data")
    else:
        logging.info("Device is offline")

    try:
        yield
    finally:
        if wifi_was_on:
            adb.shell("svc", "wifi", "enable")
        if data_was_on:
            adb.shell("svc", "data", "enable")
        logging.info("Network restored")
