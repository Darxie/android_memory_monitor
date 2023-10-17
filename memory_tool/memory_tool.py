import subprocess
import time
import utils
from writer import Writer


class MemoryTool(Writer):
    TEST_DURATION = 10 * 60  # 10 minutes
    LOG_INTERVAL = 30  # 30 seconds
    last_total_memory = 0
    last_timestamp = 0

    def __init__(self, writer, package_name):
        self.writer = writer
        self.package_name = package_name

    def extract_memory_info(self, label, data) -> str:
        found_app_summary = False
        for line in data:
            if "App Summary" in line:
                found_app_summary = True
                continue
            if found_app_summary:
                if label in line:
                    line_splits = line.split()
                    if label == "TOTAL PSS":
                        return line.split()[2]
                    if label in ["Code:", "Stack:", "Graphics:"]:
                        return line.split()[1]
                    return line.split()[2]
        return "NA"

    def check_for_crashes(self):
        self.writer.capture_sygic_log(self.package_name)

    def process_meminfo(self, timestamp):
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "meminfo", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        data_lines = result.stdout.split("\n")
        total_memory = self.extract_memory_info("TOTAL PSS", data_lines)
        self.last_total_memory = int(total_memory)
        java_heap = self.extract_memory_info("Java Heap:", data_lines)
        native_heap = self.extract_memory_info("Native Heap:", data_lines)
        code = self.extract_memory_info("Code:", data_lines)
        stack = self.extract_memory_info("Stack:", data_lines)
        graphics = self.extract_memory_info("Graphics:", data_lines)

        self.writer.write_data(
            timestamp, total_memory, java_heap, native_heap, code, stack, graphics
        )

    def start_monitoring(self):
        utils.Utils().print_info(self.package_name)
        try:
            elapsed_time = 0
            while elapsed_time < self.TEST_DURATION:
                timestamp = int(time.time())
                self.process_meminfo(timestamp)

                if elapsed_time % self.LOG_INTERVAL == 0:
                    print(
                        f"[{timestamp}] Monitoring in progress... (Total Memory: {self.last_total_memory/1024}MB)"
                    )

                self.check_for_crashes()
                time.sleep(self.LOG_INTERVAL)
                elapsed_time += self.LOG_INTERVAL
            self.writer.plot_data_from_csv()

        except KeyboardInterrupt:
            print("\nMonitoring script has been manually terminated.")
            print("\nPlotting memory data from CSV file...")
            self.writer.plot_data_from_csv()


if __name__ == "__main__":
    # you would get the package name via argument parser
    package_name = "com.sygic.profi.beta.debug"

    writer = Writer()
    memory_tool = MemoryTool(writer, package_name)

    memory_tool.start_monitoring()
