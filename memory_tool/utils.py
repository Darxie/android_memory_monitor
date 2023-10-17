import subprocess


class Utils:
    def get_app_pid(self, package_name) -> str:
        result = subprocess.run(
            [
                "adb",
                "shell",
                "ps",
                "-A",
            ],  # Use "ps" alone for older versions of Android.
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        for line in result.stdout.splitlines():
            if package_name in line:
                parts = line.split()
                # The PID is typically the second field, but it's best to check based on the layout of your `ps` output.
                return parts[1]

        return "Could not get PID!"

    # Fetch the device ID
    def get_device_id(self) -> str:
        result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, text=True)

        lines = result.stdout.splitlines()
        # The first line is a header, so we take the second line which should have the format "device_id device_status"
        if len(lines) > 1:
            return lines[1].split()[0]
        else:
            print("No devices found!")
            exit(1)

    def print_info(self, package_name):
        print(
            f"Printing device information...\n"
            f"Process ID: {self.get_app_pid(package_name)}\n"
            f"Device ID: {self.get_device_id()}\n\n"
        )
