import csv
import subprocess
from pathlib import Path
import logging
import time
from utils import execute_adb_command, _write_to_file
from timestamp import ExecutionTimestamp
import plotter


timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")

# Construct filenames with the timestamp
CSV_FILE = directory / f"memory_usage_{timestamp}.csv"
LOGCAT_FILE = directory / f"logcat_sygic_tag_{timestamp}.txt"
CRASH_LOG_FILE = directory / f"crash_log_{timestamp}.txt"

FATAL_EXCEPTION_LOOKAHEAD = (
    10  # Number of lines to look ahead for package name after a FATAL EXCEPTION
)
ERROR_SIGNALS = ["FATAL EXCEPTION", "Fatal signal"]


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
        wait_until_file_is_readable(CSV_FILE)
        plotter.plot_memory_data(CSV_FILE)

    def _app_crashed(self, logcat_output, package_name):
        """
        Check if the app crashed by looking for FATAL EXCEPTION related to the package name.

        :param logcat_output: The full logcat output.
        :param package_name: The app package name.
        :return: True if crash detected, False otherwise.
        """
        lines = logcat_output.splitlines()
        for i, line in enumerate(lines):
            if any(error_signal in line for error_signal in ERROR_SIGNALS):
                for j in range(i, min(i + FATAL_EXCEPTION_LOOKAHEAD, len(lines))):
                    if package_name in lines[j]:
                        return True
        return False

    def capture_sygic_log(self, package_name):
        logcat_output = execute_adb_command(["adb", "logcat", "-d"])

        if self._app_crashed(logcat_output, package_name):
            logging.warning("The app seems to have crashed. Capturing full logs.")
            _write_to_file(CRASH_LOG_FILE, logcat_output)
            logging.info("crash check returned true - app crashed")
            return True
        else:
            sygic_logs = "\n".join(
                execute_adb_command(
                    ["adb", "logcat", "-d", "-s", "SYGIC"]
                ).splitlines()[1:]
            )
            _write_to_file(LOGCAT_FILE, sygic_logs + "\n")
            subprocess.run(["adb", "logcat", "-c"])
            # logging.info(f"Logs with tag 'SYGIC' have been saved to {LOGCAT_FILE}")
            # logging.info("crash check returned false")
            return False


def wait_until_file_is_readable(path, timeout=5):
    """Wait until the file can be opened for reading."""
    start_time = time.time()
    while True:
        try:
            with open(path, "r", encoding="utf-8"):
                return  # File is ready
        except (PermissionError, OSError):
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"File {path} is still locked after {timeout} seconds."
                )
            time.sleep(0.1)
