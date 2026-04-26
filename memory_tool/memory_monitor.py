"""
Memory monitoring module for Android applications.
Provides real-time memory tracking with crash detection.
"""
import time
import logging
import re
from typing import Optional, Tuple
from threading import Event
from memory_tool.adb import get_app_pid, AdbDevice

# Configuration constants
DEFAULT_LOG_INTERVAL = 30  # seconds
CHECK_INTERVAL = 5  # seconds between crash checks

# Memory extraction patterns
MEMORY_PATTERNS = {
    'total_pss': r"TOTAL PSS:\s+(\d+)",
    'total': r"TOTAL:\s+(\d+)",
    'java_heap': r"Java Heap:\s+(\d+)",
    'native_heap': r"Native Heap:\s+(\d+)",
    'code': r"Code:\s+(\d+)",
    'stack': r"Stack:\s+(\d+)",
    'graphics': r"Graphics:\s+(\d+)",
}

CPU_PATTERNS = [
    r"\b([0-9]+(?:\.[0-9]+)?)%\s+\d+\/",  # e.g. "12.3% 1234/com.package"
    r"\b([0-9]+(?:\.[0-9]+)?)%\s+"         # fallback for varying output formats
]


class MemoryTool:
    """
    Monitors memory usage of an Android app using uiautomator2.

    Attributes:
        package_name: Android package name to monitor
        device: uiautomator2 device instance
        writer: Writer instance for data output
        log_interval: Seconds between memory checks
        check_interval: Seconds between crash checks
    """

    def __init__(
        self,
        writer,
        package_name: str,
        device,
        monitoring_finished_event: Optional[Event] = None,
        log_interval: int = DEFAULT_LOG_INTERVAL,
        dry_run: bool = False,
    ):
        self.writer = writer
        self.package_name = package_name
        self.device = device
        self.adb = AdbDevice(device.serial)
        self.monitoring_finished_event = monitoring_finished_event
        self.log_interval = log_interval
        self.check_interval = CHECK_INTERVAL
        self.dry_run = dry_run

        # State tracking
        self.is_monitoring = False
        self.last_total_memory = 0
        self.elapsed_time = 0
        self.data_points_collected = 0
        self.last_cpu_usage = 0.0
        self.cpu_cores = 1
        self._last_cpu_sample: Optional[Tuple[int, int]] = None

    @staticmethod
    def extract_memory_value(pattern: str, data: str) -> int:
        """
        Extract a memory value using regex from the data string.

        Args:
            pattern: Regex pattern to match
            data: Data string to search in

        Returns:
            Memory value in KB, or 0 if not found
        """
        try:
            match = re.search(pattern, data)
            if match:
                return int(match.group(1))
        except (ValueError, AttributeError, IndexError):
            pass
        return 0

    def check_for_crashes(self) -> bool:
        """
        Check if the app crashed by analyzing logs.

        Returns:
            True if crash detected, False otherwise
        """
        return self.writer.capture_app_log(self.package_name)

    def process_meminfo(self) -> bool:
        """
        Extract memory information using dumpsys meminfo and write to CSV.

        Returns:
            True if successful, False otherwise
        """
        timestamp = int(time.time())
        try:
            output = self.device.shell(f"dumpsys meminfo {self.package_name}").output
            if not output:
                logging.warning("Empty dumpsys output received")
                return False
        except Exception as e:
            logging.error(f"Failed to get meminfo: {e}")
            return False

        # Extract total memory with fallback
        total_memory = self.extract_memory_value(MEMORY_PATTERNS['total_pss'], output)
        if total_memory == 0:
            total_memory = self.extract_memory_value(MEMORY_PATTERNS['total'], output)

        if total_memory == 0:
            logging.warning("Could not extract total memory from dumpsys")
            return False

        self.last_total_memory = total_memory

        # Extract memory components
        java_heap = self.extract_memory_value(MEMORY_PATTERNS['java_heap'], output)
        native_heap = self.extract_memory_value(MEMORY_PATTERNS['native_heap'], output)
        code = self.extract_memory_value(MEMORY_PATTERNS['code'], output)
        stack = self.extract_memory_value(MEMORY_PATTERNS['stack'], output)
        graphics = self.extract_memory_value(MEMORY_PATTERNS['graphics'], output)

        cpu_usage = self.process_cpuinfo()

        success = self.writer.write_data(
            timestamp, total_memory, java_heap, native_heap, code, stack, graphics, cpu_usage
        )

        if success:
            self.data_points_collected += 1
            self.last_cpu_usage = cpu_usage

        return success

    def process_cpuinfo(self) -> float:
        """
        Extract app CPU usage percentage for current process.

        Returns:
            CPU usage percent as float, 0.0 if unavailable
        """
        # Primary method: /proc deltas per PID for stable and time-local readings.
        pid = get_app_pid(self.package_name, self.adb)
        if pid and pid != "None":
            cpu_value = self._read_cpu_from_proc(pid)
            if cpu_value is not None:
                return cpu_value

        # Fallback: parse dumpsys cpuinfo output.
        try:
            output = self.device.shell("dumpsys cpuinfo").output
            if not output:
                return 0.0

            for line in output.splitlines():
                if self.package_name not in line:
                    continue

                for pattern in CPU_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        return float(match.group(1))
        except Exception as e:
            logging.debug(f"Failed to extract CPU usage: {e}")

        return 0.0

    def _read_cpu_from_proc(self, pid: str) -> Optional[float]:
        """
        Compute per-app CPU percentage from /proc deltas.

        Returns:
            CPU percent where 100% ~= one fully utilized core, or None if unavailable.
        """
        try:
            proc_stat = self.device.shell(f"cat /proc/{pid}/stat").output.strip()
            if not proc_stat:
                return None

            end = proc_stat.rfind(")")
            if end == -1:
                return None

            after = proc_stat[end + 1 :].strip().split()
            if len(after) < 15:
                return None

            utime = int(after[11])
            stime = int(after[12])
            proc_jiffies = utime + stime

            cpu_stat = self.device.shell("cat /proc/stat").output
            total_line = next((line for line in cpu_stat.splitlines() if line.startswith("cpu ")), "")
            if not total_line:
                return None

            total_parts = total_line.split()[1:]
            total_jiffies = sum(int(x) for x in total_parts if x.isdigit())

            if self._last_cpu_sample is None:
                self._last_cpu_sample = (proc_jiffies, total_jiffies)
                return 0.0

            last_proc, last_total = self._last_cpu_sample
            delta_proc = proc_jiffies - last_proc
            delta_total = total_jiffies - last_total
            self._last_cpu_sample = (proc_jiffies, total_jiffies)

            if delta_total <= 0 or delta_proc < 0:
                return 0.0

            cpu_percent_total = (delta_proc / delta_total) * 100.0
            cpu_percent_one_core_scale = cpu_percent_total * max(self.cpu_cores, 1)
            return max(0.0, cpu_percent_one_core_scale)
        except Exception:
            return None

    def get_cpu_core_count(self) -> int:
        """
        Detect logical CPU core count on the connected Android device.

        Returns:
            Logical core count, defaults to 1 if detection fails
        """
        commands = [
            "getconf _NPROCESSORS_ONLN",
            "nproc",
            "cat /sys/devices/system/cpu/possible",
        ]

        for command in commands:
            try:
                output = self.device.shell(command).output.strip()
                if not output:
                    continue

                if "-" in output:
                    parts = output.split("-")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        return int(parts[1]) - int(parts[0]) + 1

                match = re.search(r"(\d+)", output)
                if match:
                    value = int(match.group(1))
                    if value > 0:
                        return value
            except Exception:
                continue

        return 1

    def start_monitoring(self):
        """Start monitoring the memory usage of the specified package."""
        self.is_monitoring = True
        logging.info(f"Starting memory monitoring for {self.package_name}")

        # Clear old logs so crash detection is based only on this run.
        self.adb.logcat_clear()
        logging.info("Logcat cleared before monitoring start")

        self.cpu_cores = self.get_cpu_core_count()
        self.writer.write_cpu_info(self.cpu_cores)
        logging.info(f"Detected logical CPU cores: {self.cpu_cores}")

        try:
            while self.is_monitoring:
                if self.elapsed_time % self.log_interval == 0:
                    self.process_meminfo()
                    memory_mb = self.last_total_memory / 1024
                    logging.info(
                        f"Monitoring... Memory: {memory_mb:.2f}MB, CPU: {self.last_cpu_usage:.2f}%"
                    )

                if self.check_for_crashes():
                    logging.warning("App crash detected, stopping monitor")
                    self.stop_monitoring()

                time.sleep(self.check_interval)
                self.elapsed_time += self.check_interval

        except Exception as e:
            logging.error(f"Error during memory monitoring: {e}", exc_info=True)
        finally:
            self.is_monitoring = False
            if self.monitoring_finished_event:
                self.monitoring_finished_event.set()
            logging.info(f"Monitoring stopped. Duration: {self.elapsed_time}s, Data points: {self.data_points_collected}")

    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.is_monitoring = False
