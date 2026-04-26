import subprocess
import logging


def execute_adb_command(command_list, timeout=30) -> str:
    """Execute an ADB command and return stdout, or empty string on error."""
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


class AdbDevice:
    """Wraps ADB subprocess calls so every command automatically targets one device."""

    def __init__(self, device_code: str = None):
        self.device_code = device_code

    @property
    def _prefix(self) -> list:
        return ["adb", "-s", self.device_code] if self.device_code else ["adb"]

    def run(self, *args, timeout: int = 30) -> str:
        """Run any ADB command, e.g. adb.run("wait-for-device")."""
        return execute_adb_command(self._prefix + list(args), timeout=timeout)

    def shell(self, *args, timeout: int = 30) -> str:
        """Run an ADB shell command, e.g. adb.shell("am", "force-stop", pkg)."""
        return self.run("shell", *args, timeout=timeout)

    def logcat_clear(self) -> None:
        self.run("logcat", "-c", timeout=5)

    def logcat_dump(self) -> str:
        return self.run("logcat", "-d")


def get_app_pid(package_name: str, adb: AdbDevice) -> str:
    """
    Get the process ID for an app package name.

    Args:
        package_name: Android package name
        adb: AdbDevice instance targeting the correct device

    Returns:
        PID as string, or "None" if not found
    """
    try:
        result = adb.shell("ps", "-A")
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
