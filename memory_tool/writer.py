"""
Memory data writer module for Android memory monitoring.
Handles CSV writing, crash detection, and plot generation.
"""
import csv
from pathlib import Path
import logging
import time
from typing import Optional, List, Tuple, Union
from memory_tool.adb import AdbDevice, get_app_pid
from memory_tool.utils import _write_to_file
from memory_tool.timestamp import ExecutionTimestamp
from memory_tool import plotter

# Constants
CRASH_LOOKAHEAD_LINES = 50
CSV_HEADERS = [
    "timestamp",
    "total_memory",
    "java_heap",
    "native_heap",
    "code",
    "stack",
    "graphics",
    "cpu_usage",
]
FILE_READABLE_TIMEOUT = 5  # seconds
LOGCAT_CLEAR_TIMEOUT = 5  # seconds

# Crash detection patterns
JAVA_CRASH_INDICATORS = ["FATAL EXCEPTION", "java.lang.RuntimeException", "AndroidRuntime"]
NATIVE_CRASH_INDICATORS = ["Fatal signal", "backtrace:", "SIGSEGV", "SIGABRT"]


class Writer:
    """
    Handles writing memory data to CSV and capturing crash logs.
    
    Attributes:
        directory: Output directory for test run
        csv_file: Path to CSV file
        logcat_file: Path to filtered logcat file
        crash_log_file: Path to crash log file
    """
    
    def __init__(self, adb: Optional[AdbDevice] = None, output_dir: Optional[Path] = None):
        """
        Initialize CSV file with headers.

        Args:
            adb: AdbDevice targeting the monitored device; falls back to whichever device ADB finds
            output_dir: Optional custom output directory. If None, uses default timestamped directory.
        """
        self.adb = adb or AdbDevice()
        timestamp = ExecutionTimestamp.get_timestamp()
        
        if output_dir:
            self.directory = output_dir
        else:
            self.directory = Path(f"output/{timestamp}")
        
        # Ensure directory exists
        self.directory.mkdir(parents=True, exist_ok=True)
        
        # Set file paths
        self.csv_file = self.directory / f"memory_usage_{timestamp}.csv"
        self.logcat_file = self.directory / f"logcat_{timestamp}.txt"
        self.crash_log_file = self.directory / f"crash_log_{timestamp}.txt"
        self.cpu_info_file = self.directory / f"cpu_info_{timestamp}.txt"
        
        # Statistics tracking
        self.rows_written = 0
        self.write_errors = 0
        self.crash_checks = 0
        self.crashes_detected = 0
        
        # Initialize CSV
        self._initialize_csv()
    
    def _initialize_csv(self) -> None:
        """Initialize CSV file with headers."""
        try:
            with open(self.csv_file, mode="w", newline="", encoding="utf-8") as file:
                csv_writer = csv.writer(file)
                csv_writer.writerow(CSV_HEADERS)
            logging.info(f"CSV initialized: {self.csv_file}")
        except Exception as e:
            logging.error(f"Failed to initialize CSV: {e}")
            raise
    
    def _validate_memory_data(self, data: Tuple[Union[int, float], ...]) -> bool:
        """
        Validate memory data before writing.
        
        Args:
            data: Tuple of memory values
            
        Returns:
            True if valid, False otherwise
        """
        if len(data) != len(CSV_HEADERS):
            logging.warning(f"Invalid data length: {len(data)} vs {len(CSV_HEADERS)}")
            return False
        
        # Check that timestamp is reasonable
        if data[0] < 1000000000:  # Before year 2001
            logging.warning(f"Invalid timestamp: {data[0]}")
            return False
        
        return True

    def write_data(
        self,
        timestamp: int,
        total_memory: int,
        java_heap: int,
        native_heap: int,
        code: int,
        stack: int,
        graphics: int,
        cpu_usage: float = 0.0,
    ) -> bool:
        """
        Write memory data row to CSV file.
        
        Args:
            timestamp: Unix timestamp
            total_memory: Total memory in KB
            java_heap: Java heap in KB
            native_heap: Native heap in KB
            code: Code memory in KB
            stack: Stack memory in KB
            graphics: Graphics memory in KB
            cpu_usage: CPU usage in percent for monitored process
            
        Returns:
            True if write successful, False otherwise
        """
        data = (timestamp, total_memory, java_heap, native_heap, code, stack, graphics, cpu_usage)
        
        if not self._validate_memory_data(data):
            self.write_errors += 1
            return False
        
        try:
            with open(self.csv_file, mode="a", newline="", encoding="utf-8") as file:
                csv_writer = csv.writer(file)
                csv_writer.writerow(data)
            self.rows_written += 1
            return True
        except Exception as e:
            logging.error(f"Failed to write data to CSV: {e}")
            self.write_errors += 1
            return False

    def plot_data_from_csv(self) -> bool:
        """
        Generate plots from CSV data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.csv_file.exists():
                logging.error(f"CSV file not found: {self.csv_file}")
                return False
            
            logging.info("Generating plots from memory data...")
            self._wait_until_file_is_readable(self.csv_file)
            plotter.plot_memory_data(str(self.csv_file))
            logging.info("Plot generation completed")
            return True
        except Exception as e:
            logging.error(f"Failed to plot data: {e}", exc_info=True)
            return False

    def write_cpu_info(self, cpu_cores: int) -> bool:
        """
        Write CPU core context to output so CPU percentages are easier to interpret.

        Args:
            cpu_cores: Number of logical CPU cores on the device

        Returns:
            True if successful, False otherwise
        """
        try:
            max_percent = max(cpu_cores, 1) * 100
            info_lines = [
                "CPU INTERPRETATION INFO",
                "======================",
                f"Detected logical CPU cores: {cpu_cores}",
                "",
                "Why values above 100% are possible:",
                "- Android cpuinfo percentage for an app is aggregated across CPU cores.",
                "- 100% means roughly one fully utilized core.",
                f"- On this device, theoretical app maximum is about {max_percent}%.",
                "- Example: 160% means approximately 1.6 cores worth of CPU time, which is normal.",
            ]
            self.cpu_info_file.write_text("\n".join(info_lines) + "\n", encoding="utf-8")
            logging.info(f"CPU info written: {self.cpu_info_file}")
            return True
        except Exception as e:
            logging.error(f"Failed to write CPU info: {e}", exc_info=True)
            return False
    
    def _wait_until_file_is_readable(self, path: Path, timeout: int = FILE_READABLE_TIMEOUT) -> None:
        """
        Wait for file to become readable.
        
        Args:
            path: File path
            timeout: Timeout in seconds
            
        Raises:
            FileNotFoundError: If file doesn't exist
            TimeoutError: If file remains locked after timeout
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        start_time = time.time()
        while True:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    f.read(1)  # Try to read one byte
                return  # File is readable
            except (PermissionError, OSError) as e:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"File locked after {timeout}s: {path}")
                time.sleep(0.1)

    def _detect_java_crash(self, lines: List[str], package_name: str, start_idx: int) -> bool:
        """
        Detect Java/Android runtime crashes.
        
        Args:
            lines: Logcat lines
            package_name: Package to check for
            start_idx: Starting index in lines
            
        Returns:
            True if Java crash detected for this package
        """
        end_idx = min(start_idx + CRASH_LOOKAHEAD_LINES, len(lines))
        
        for j in range(start_idx, end_idx):
            line = lines[j]
            # Look for explicit process marker
            if f"Process: {package_name}" in line:
                return True
            # Check for package in stack trace
            if package_name in line and ("at " in line or "Caused by:" in line):
                return True
        
        return False
    
    def _detect_native_crash(self, lines: List[str], package_name: str, start_idx: int) -> bool:
        """
        Detect native/signal crashes.
        
        Args:
            lines: Logcat lines
            package_name: Package to check for
            start_idx: Starting index in lines
            
        Returns:
            True if native crash detected for this package
        """
        end_idx = min(start_idx + CRASH_LOOKAHEAD_LINES, len(lines))
        
        for j in range(start_idx, end_idx):
            if f">>> {package_name} <<<" in lines[j]:
                return True
        
        return False
    def _app_crashed(self, logcat_output: str, package_name: str) -> bool:
        """
        Check if the app crashed using logcat output.
        
        Args:
            logcat_output: Full logcat output
            package_name: Package name to match against
            
        Returns:
            True if crash detected, False otherwise
        """
        if not logcat_output:
            return False
            
        lines = logcat_output.splitlines()
        
        for i, line in enumerate(lines):
            # Check for Java crashes
            if any(indicator in line for indicator in JAVA_CRASH_INDICATORS):
                if self._detect_java_crash(lines, package_name, i):
                    logging.warning(f"Java crash detected at line {i}")
                    return True
            
            # Check for native crashes
            if any(indicator in line for indicator in NATIVE_CRASH_INDICATORS):
                if self._detect_native_crash(lines, package_name, i):
                    logging.warning(f"Native crash detected at line {i}")
                    return True
        
        return False

    def _filter_logs_by_pid(self, logcat_output: str, pid: str) -> List[str]:
        """
        Filter logcat output by process ID.
        
        Args:
            logcat_output: Full logcat output
            pid: Process ID to filter by
            
        Returns:
            List of filtered log lines
        """
        if not pid or pid == "None":
            return []
        
        # Filter lines containing the PID
        filtered_logs = [
            line for line in logcat_output.splitlines()
            if f" {pid} " in line or f"{pid}:" in line or f"({pid})" in line
        ]
        
        return filtered_logs
    
    def capture_app_log(self, package_name: str) -> bool:
        """
        Capture application logs and check for crashes.
        
        Args:
            package_name: Package name to capture logs for
            
        Returns:
            True if crash detected, False otherwise
        """
        self.crash_checks += 1
        
        try:
            logcat_output = self.adb.logcat_dump()

            if not logcat_output:
                logging.debug("Empty logcat output received")
                return False

            # Check for crashes
            if self._app_crashed(logcat_output, package_name):
                self.crashes_detected += 1
                logging.warning(f"Crash detected in {package_name}. Saving crash logs.")
                _write_to_file(self.crash_log_file, logcat_output)
                return True

            # Save filtered logs by PID
            pid = get_app_pid(package_name, self.adb)
            filtered_logs = self._filter_logs_by_pid(logcat_output, pid)

            if filtered_logs:
                log_content = "\n".join(filtered_logs) + "\n"
                _write_to_file(self.logcat_file, log_content)
                logging.debug(f"Captured {len(filtered_logs)} log lines for PID {pid}")

            # Clear logcat buffer
            self.adb.logcat_clear()
            return False

        except Exception as e:
            logging.error(f"Error capturing app log: {e}", exc_info=True)
            return False
    
    def get_output_directory(self) -> Path:
        """Get the output directory path."""
        return self.directory
    
    def get_csv_file(self) -> Path:
        """Get the CSV file path."""
        return self.csv_file
    
    def get_statistics(self) -> dict:
        """
        Get writer statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'rows_written': self.rows_written,
            'write_errors': self.write_errors,
            'crash_checks': self.crash_checks,
            'crashes_detected': self.crashes_detected,
            'csv_file': str(self.csv_file),
            'cpu_info_file': str(self.cpu_info_file),
            'output_directory': str(self.directory),
        }

