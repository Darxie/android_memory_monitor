import csv
import plotter
import subprocess
from datetime import datetime
from pathlib import Path

directory = Path("output")
# Get the current timestamp in a specific format
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Construct filenames with the timestamp
CSV_FILE = directory / f"memory_usage_{timestamp}.csv"
LOGCAT_FILE = directory / f"logcat_sygic_tag_{timestamp}.txt"
CRASH_LOG_FILE = directory / f"crash_log_{timestamp}.txt"


class Writer:
    def __init__(self):
        if not directory.exists():
            directory.mkdir(parents=True)

        # Initialize CSV file with headers
        with open(CSV_FILE, mode="w", newline="") as file:
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
        with open(CSV_FILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [timestamp, total_memory, java_heap, native_heap, code, stack, graphics]
            )

    def plot_data_from_csv(self):
        plotter.plot_memory_data(CSV_FILE)

    def capture_sygic_log(self, package_name):
        logcat_cmd = ["adb", "logcat", "-d", package_name]
        logcat_output = subprocess.run(
            logcat_cmd, capture_output=True, text=True
        ).stdout
        if "FATAL EXCEPTION" in logcat_output:
            filtered_logs = [
                line for line in logcat_output.splitlines() if package_name in line
            ]
            if filtered_logs:
                # if the app crashed, filter the logs and plot the memory data graph and exit
                print("The app seems to have crashed. Relevant logs:")
                for log in filtered_logs:
                    print(log)
                    with open(CRASH_LOG_FILE, "a") as f:
                        f.write(log + "\n")
                self.plot_data_from_csv()
                exit(0)
            else:
                print("No crashes found for the specified app.")
        else:
            with open(LOGCAT_FILE, "a") as f:
                output = subprocess.run(
                    ["adb", "logcat", "-d", "-s", "SYGIC"],
                    capture_output=True,
                    text=True,
                ).stdout
                for line in output.splitlines()[1:]:
                    f.write(line + "\n")

                subprocess.run(["adb", "logcat", "-c"])
                print(f"Logs with tag 'SYGIC' have been saved to {LOGCAT_FILE}")
