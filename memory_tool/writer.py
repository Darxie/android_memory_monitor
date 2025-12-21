import csv
import subprocess
from pathlib import Path
import logging
import time
from utils import execute_adb_command, _write_to_file, get_app_pid
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
        lookahead = 50  # Increased lookahead to catch the process name in stack traces
        
        for i, line in enumerate(lines):
            # 1. Java Crash Detection
            if "FATAL EXCEPTION" in line:
                # Look for "Process: com.example.package" which is standard in AndroidRuntime logs
                # Or check if the package name appears in the stack trace lines immediately following
                for j in range(i, min(i + lookahead, len(lines))):
                    if f"Process: {package_name}" in lines[j]:
                        return True
                    if package_name in lines[j]:
                        return True

            # 2. Native Crash Detection
            if "Fatal signal" in line:
                # Native crashes (tombstones) usually print: 
                # "pid: 1234, tid: 5678, name: ThreadName  >>> com.example.package <<<"
                for j in range(i, min(i + lookahead, len(lines))):
                    if f">>> {package_name} <<<" in lines[j]:
                        return True
                    
        return False

    def capture_app_log(self, package_name):
        logcat_output = execute_adb_command(["adb", "logcat", "-d"])

        if self._app_crashed(logcat_output, package_name):
            logging.warning("The app seems to have crashed. Capturing full logs.")
            _write_to_file(CRASH_LOG_FILE, logcat_output)
            logging.info("crash check returned true - app crashed")
            return True
        else:
            # Filter logs by PID
            pid = get_app_pid(package_name)
            if pid and pid != "None":
                # Filter lines containing the PID (surrounded by spaces or followed by colon)
                # This helps avoid matching similar numbers in timestamps etc.
                filtered_logs = [
                    line for line in logcat_output.splitlines() 
                    if f" {pid} " in line or f"{pid}:" in line
                ]
                if filtered_logs:
                    _write_to_file(LOGCAT_FILE, "\n".join(filtered_logs) + "\n")
            
            subprocess.run(["adb", "logcat", "-c"])
            return False


def wait_until_file_is_readable(path, timeout=5):
    """Wait until the file can be opened for reading."""
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File {path} does not exist.")

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
