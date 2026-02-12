"""
Memory monitoring module for Android applications.
Provides real-time memory tracking with crash detection.
"""
import time
import logging
import re
from typing import Optional, Dict
from threading import Event

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
        log_interval: int = DEFAULT_LOG_INTERVAL
    ):
        self.writer = writer
        self.package_name = package_name
        self.device = device
        self.monitoring_finished_event = monitoring_finished_event
        self.log_interval = log_interval
        self.check_interval = CHECK_INTERVAL
        
        # State tracking
        self.is_monitoring = False
        self.last_total_memory = 0
        self.elapsed_time = 0
        self.data_points_collected = 0

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

        success = self.writer.write_data(
            timestamp, total_memory, java_heap, native_heap, code, stack, graphics
        )
        
        if success:
            self.data_points_collected += 1
        
        return success

    def start_monitoring(self):
        """Start monitoring the memory usage of the specified package."""
        self.is_monitoring = True
        logging.info(f"Starting memory monitoring for {self.package_name}")
        
        try:
            while self.is_monitoring:
                if self.elapsed_time % self.log_interval == 0:
                    self.process_meminfo()
                    memory_mb = self.last_total_memory / 1024
                    logging.info(f"Monitoring... Memory: {memory_mb:.2f}MB")

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
    