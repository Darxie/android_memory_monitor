import time
import logging
import utils


class MemoryTool:
    """
    A class that provides functionality to monitor memory usage of an Android app.

    """

    is_monitoring = True
    LOG_INTERVAL = 60  # 30 seconds
    last_total_memory = 0
    last_timestamp = 0
    elapsed_time = 0
    check_interval = 5

    def __init__(self, writer, package_name, monitoring_finished_event=None):
        self.writer = writer
        self.package_name = package_name
        self.monitoring_finished_event = monitoring_finished_event

    def extract_memory_info(self, label, data) -> str:
        """
        Extracts memory information from the given data based on the provided label.

        Args:
            label (str): The label to search for in the data.
            data (List[str]): The list of strings containing memory information.

        Returns:
            str: The extracted memory information as a string.
        """
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

    def process_meminfo(self):
        """
        Extracts memory information using adb shell dumpsys meminfo command 
        and writes it to a file.
        """
        timestamp = int(time.time())
        result = utils.execute_adb_command(
            ["adb", "shell", "dumpsys", "meminfo", self.package_name]
        )

        data_lines = result.split("\n")
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
        """
        Starts monitoring the memory usage of the specified package.
        """
        utils.print_info(self.package_name)

        try:
            while self.is_monitoring:
                if self.elapsed_time % self.LOG_INTERVAL == 0:
                    self.process_meminfo()
                    logging.info(
                        f" Monitoring in progress... (Total Memory: {self.last_total_memory/1024}MB)"
                    )

                self.check_for_crashes()  # ToDo SDC-10346
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
