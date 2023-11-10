import csv
import subprocess
from datetime import datetime
from pathlib import Path
import logging
import utils
import plotter

directory = Path("output")
# Get the current timestamp in a specific format
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Construct filenames with the timestamp
CSV_FILE = directory / f"memory_usage_{timestamp}.csv"
LOGCAT_FILE = directory / f"logcat_sygic_tag_{timestamp}.txt"
CRASH_LOG_FILE = directory / f"crash_log_{timestamp}.txt"

FATAL_EXCEPTION_LOOKAHEAD = (
    10  # Number of lines to look ahead for package name after a FATAL EXCEPTION
)


class Writer:
    def __init__(self):
        if not directory.exists():
            directory.mkdir(parents=True)

        # Initialize CSV file with headers
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "timestamp",
                    "total_memory",
                    "java_heap",
                    "native_heap",
                    "code",
                    "stack",
                    "graphics",
                ]
            )

    def write_data(
        self, timestamp, total_memory, java_heap, native_heap, code, stack, graphics
    ):
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [timestamp, total_memory, java_heap, native_heap, code, stack, graphics]
            )

    def plot_data_from_csv(self):
        logging.info("\nPlotting memory data from CSV file...")
        plotter.plot_memory_data(CSV_FILE)

    @staticmethod
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

    def _app_crashed(self, logcat_output, package_name):
        """
        Check if the app crashed by looking for FATAL EXCEPTION related to the package name.

        :param logcat_output: The full logcat output.
        :param package_name: The app package name.
        :return: True if crash detected, False otherwise.
        """
        lines = logcat_output.splitlines()
        for i in range(len(lines)):
            if "FATAL EXCEPTION" in lines[i]:
                for j in range(i, min(i + FATAL_EXCEPTION_LOOKAHEAD, len(lines))):
                    if package_name in lines[j]:
                        return True
        return False

    def capture_sygic_log(self, package_name):
        logcat_output = utils.execute_adb_command(["adb", "logcat", "-d"])

        if self._app_crashed(logcat_output, package_name):
            logging.warning("The app seems to have crashed. Capturing full logs.")
            self._write_to_file(CRASH_LOG_FILE, logcat_output)
            self.plot_data_from_csv()
            exit(0)
        else:
            sygic_logs = "\n".join(
                utils.execute_adb_command(
                    ["adb", "logcat", "-d", "-s", "SYGIC"]
                ).splitlines()[1:]
            )
            self._write_to_file(LOGCAT_FILE, sygic_logs + "\n")
            subprocess.run(["adb", "logcat", "-c"])
            logging.info(f"Logs with tag 'SYGIC' have been saved to {LOGCAT_FILE}")
