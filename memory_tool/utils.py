import subprocess
import logging


class Utils:
    def _execute_adb_command(self, command_list):
        """
        Execute an ADB command and return the result.

        :param command_list: List of command components.
        :return: subprocess.CompletedProcess object if successful, None otherwise.
        """
        try:
            result = subprocess.run(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return result
        except Exception as e:
            logging.error(f"Error executing ADB command {command_list}: {e}")
            return None

    def get_app_pid(self, package_name) -> str:
        """
        Get the process ID (PID) for a given app package name.
        The PID is typically the second field, but it's best to check based on the layout of your `ps` output.

        :param package_name: Name of the app package.
        :return: PID as a string if found, None otherwise.
        """
        result = self._execute_adb_command(["adb", "shell", "ps", "-A"])

        if result:
            for line in result.stdout.splitlines():
                if package_name in line:
                    parts = line.split()
                    return parts[1]
        return "None"

    def get_device_id(self) -> str:
        """
        Fetch the device ID for the connected device.

        :return: Device ID as a string if found, None otherwise.
        """
        result = self._execute_adb_command(["adb", "devices"])

        if result:
            lines = result.stdout.splitlines()
            if len(lines) > 2:
                return lines[1].split()[0]
        logging.warning("No devices found!")
        exit(1)

    def print_info(self, package_name):
        """
        Print device information including process ID and device ID.

        :param package_name: Name of the app package.
        """
        pid = self.get_app_pid(package_name)
        device_id = self.get_device_id()

        if pid:
            logging.info(f"Process ID: {pid}")
        else:
            logging.warning(f"Could not get PID for {package_name}")

        if device_id:
            logging.info(f"Device ID: {device_id}")

        logging.info("Printing device information completed.\n\n")

    def print_app_info(self, device, package_name):
        logging.info(device.app_info(package_name))
