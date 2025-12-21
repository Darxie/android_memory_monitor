import time
import logging
import re


class MemoryTool:
    """
    A class that provides functionality to monitor memory usage of an Android app
    using uiautomator2 and robust regex parsing.
    """

    is_monitoring = False
    LOG_INTERVAL = 30  # in seconds
    last_total_memory = 0
    elapsed_time = 0
    check_interval = 5  # in seconds

    def __init__(
        self, writer, package_name, device, monitoring_finished_event=None, log_interval=30
    ):
        self.writer = writer
        self.package_name = package_name
        self.device = device
        self.monitoring_finished_event = monitoring_finished_event
        self.log_interval = log_interval

    @staticmethod
    def extract_memory_value(pattern, data) -> str:
        """
        Extracts a memory value using regex from the data string.
        Returns "NA" if not found.
        """
        match = re.search(pattern, data)
        if match:
            return match.group(1)
        return "0"

    def check_for_crashes(self):
        # capture_app_log returns True if app crashed
        return self.writer.capture_app_log(self.package_name)

    def process_meminfo(self):
        """
        Extracts memory information using adb shell dumpsys meminfo command
        via uiautomator2 and writes it to a file.
        """
        timestamp = int(time.time())
        try:
            # Execute command using uiautomator2 device connection
            output = self.device.shell(f"dumpsys meminfo {self.package_name}").output
        except Exception as e:
            logging.error(f"Failed to get meminfo: {e}")
            return

        # Robust regex parsing
        # Matches "TOTAL PSS:   12345" or similar patterns
        # Note: Dumpsys output format can vary, but "TOTAL PSS" is fairly standard in the App Summary or main table.
        # We look for the main PSS value usually labeled as TOTAL or TOTAL PSS.
        
        # Strategy: Look for the specific lines in "App Summary" or the main table.
        # This regex looks for the TOTAL PSS line.
        total_memory = self.extract_memory_value(r"TOTAL PSS:\s+(\d+)", output)
        if total_memory == "0":
             # Fallback: sometimes it's just "TOTAL:"
             total_memory = self.extract_memory_value(r"TOTAL:\s+(\d+)", output)

        self.last_total_memory = int(total_memory)
        
        # Extract other metrics
        java_heap = self.extract_memory_value(r"Java Heap:\s+(\d+)", output)
        native_heap = self.extract_memory_value(r"Native Heap:\s+(\d+)", output)
        code = self.extract_memory_value(r"Code:\s+(\d+)", output)
        stack = self.extract_memory_value(r"Stack:\s+(\d+)", output)
        graphics = self.extract_memory_value(r"Graphics:\s+(\d+)", output)

        self.writer.write_data(
            timestamp, total_memory, java_heap, native_heap, code, stack, graphics
        )

    def start_monitoring(self):
        """
        Starts monitoring the memory usage of the specified package.
        """
        self.is_monitoring = True
        try:
            while self.is_monitoring:
                if self.elapsed_time % self.log_interval == 0:
                    self.process_meminfo()
                    logging.info(
                        f" Monitoring in progress... (Total Memory: {self.last_total_memory/1024:.2f}MB)"
                    )

                if self.check_for_crashes():
                    self.stop_monitoring()
                time.sleep(self.check_interval)
                self.elapsed_time += self.check_interval

        except Exception as e:
            logging.error(f"Error during memory monitoring: {e}")

        finally:
            self.stop_monitoring()

    def stop_monitoring(self):
        """
        Stops the memory monitoring process and logs the elapsed time.
        """
        self.is_monitoring = False
        logging.info("Elapsed time: " + str(self.elapsed_time) + " seconds.")
        if self.monitoring_finished_event:
            self.monitoring_finished_event.set()
        logging.info("Memory monitoring has been stopped.")