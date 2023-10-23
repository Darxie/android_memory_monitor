import subprocess
import time
import utils
import logging


class MemoryTool:
    is_monitoring = True
    TEST_DURATION = 5 * 60  # 30 minutes
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
            ["adb", "shell", "dumpsys", "meminfo", self.package_name],
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
            while self.is_monitoring and elapsed_time < self.TEST_DURATION:
                timestamp = int(time.time())
                self.process_meminfo(timestamp)

                if elapsed_time % self.LOG_INTERVAL == 0:
                    logging.info(
                        f"[{timestamp}] Monitoring in progress... (Total Memory: {self.last_total_memory/1024}MB)"
                    )

                self.check_for_crashes()
                time.sleep(self.LOG_INTERVAL)
                elapsed_time += self.LOG_INTERVAL
            self.writer.plot_data_from_csv()

        except Exception as e:
            self.stop_monitoring()
            logging.error(f"Error during memory monitoring: {e}")
            logging.info("\nPlotting memory data from CSV file...")
            self.writer.plot_data_from_csv()

    def stop_monitoring(self):
        self.is_monitoring = False
        logging.info("Memory monitoring has been stopped.")
