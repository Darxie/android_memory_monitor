"""
Memory data plotting and analysis module.
Generates visualizations and trend analysis reports.
"""
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.dates as mdates
import logging
import numpy as np
import csv
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from memory_tool.timestamp import ExecutionTimestamp


timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")
directory.mkdir(parents=True, exist_ok=True)

IMAGE_STACKED_MEMORY = directory / f"memory_stacked_line_chart_{timestamp}.png"
IMAGE_TOTAL_MEMORY = directory / f"memory_total_{timestamp}.png"
IMAGE_CPU_USAGE = directory / f"cpu_usage_{timestamp}.png"
ANALYSIS_FILE = directory / f"memory_analysis_{timestamp}.txt"
HTML_REPORT_FILE = directory / f"report_{timestamp}.html"
CPU_INFO_FILE = directory / f"cpu_info_{timestamp}.txt"

# Constants
MIN_DATA_POINTS = 10
CRITICAL_LEAK_THRESHOLD_MB_MIN = 0.5
WARNING_LEAK_THRESHOLD_MB_MIN = 0.05
CPU_WARNING_SLOPE_PERCENT_MIN = 0.1
CPU_CRITICAL_SLOPE_PERCENT_MIN = 0.5
CPU_HIGH_AVG_THRESHOLD = 70.0
MEMORY_GB_THRESHOLD = 1024  # MB
DEFAULT_DPI = 100
DEFAULT_FIGSIZE = (14, 8)
REQUIRED_COLUMNS = ["timestamp", "total_memory", "java_heap", "native_heap", "code", "stack", "graphics"]


def _configure_output_paths(csv_file_path: str) -> None:
    """
    Configure module-level output paths from the active CSV path.

    This prevents timestamp mismatches when this module was imported before
    the run timestamp was reset.
    """
    global IMAGE_STACKED_MEMORY, IMAGE_TOTAL_MEMORY, IMAGE_CPU_USAGE
    global ANALYSIS_FILE, HTML_REPORT_FILE, CPU_INFO_FILE

    csv_path = Path(csv_file_path)
    output_dir = csv_path.parent

    stem = csv_path.stem
    if stem.startswith("memory_usage_"):
        run_timestamp = stem.replace("memory_usage_", "", 1)
    else:
        run_timestamp = ExecutionTimestamp.get_timestamp()

    output_dir.mkdir(parents=True, exist_ok=True)
    IMAGE_STACKED_MEMORY = output_dir / f"memory_stacked_line_chart_{run_timestamp}.png"
    IMAGE_TOTAL_MEMORY = output_dir / f"memory_total_{run_timestamp}.png"
    IMAGE_CPU_USAGE = output_dir / f"cpu_usage_{run_timestamp}.png"
    ANALYSIS_FILE = output_dir / f"memory_analysis_{run_timestamp}.txt"
    HTML_REPORT_FILE = output_dir / f"report_{run_timestamp}.html"
    CPU_INFO_FILE = output_dir / f"cpu_info_{run_timestamp}.txt"


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float with safe fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_csv_rows(csv_file_path: str) -> List[Dict[str, float]]:
    """
    Load and normalize rows from the memory CSV file.

    Returns:
        List of rows with numeric values.
    """
    normalized_rows: List[Dict[str, float]] = []
    with open(csv_file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized_rows.append(
                {
                    "timestamp": _safe_float(row.get("timestamp")),
                    "total_memory": _safe_float(row.get("total_memory")),
                    "java_heap": _safe_float(row.get("java_heap")),
                    "native_heap": _safe_float(row.get("native_heap")),
                    "code": _safe_float(row.get("code")),
                    "stack": _safe_float(row.get("stack")),
                    "graphics": _safe_float(row.get("graphics")),
                    "cpu_usage": _safe_float(row.get("cpu_usage")),
                }
            )

    return normalized_rows


def _validate_rows(rows: List[Dict[str, float]]) -> Tuple[bool, Optional[str]]:
    """
    Validate parsed rows for plotting.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not rows:
        return False, "Data set is empty"

    if len(rows) < 2:
        return False, f"Insufficient data: {len(rows)} rows (need at least 2)"

    sample = rows[0]
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in sample]
    if missing_cols:
        return False, f"Missing columns: {', '.join(missing_cols)}"
    
    return True, None


def _determine_memory_unit(rows: List[Dict[str, float]]) -> Tuple[str, float]:
    """Return display unit and divider for values stored in KB."""
    max_kb = 0.0
    for row in rows:
        for metric in REQUIRED_COLUMNS[1:]:
            max_kb = max(max_kb, row[metric])

    max_mb = max_kb / 1024.0
    if max_mb > MEMORY_GB_THRESHOLD:
        return "GB", 1024.0 * 1024.0
    return "MB", 1024.0


def _timestamps_from_rows(rows: List[Dict[str, float]]) -> List[datetime]:
    """Convert unix timestamps in rows to datetime objects."""
    return [datetime.fromtimestamp(row["timestamp"]) for row in rows]


def analyze_trends(csv_file_path: str) -> bool:
    """
    Analyze memory usage trends to detect potential leaks.
    Writes a report to a text file and logs it.
    
    Args:
        csv_file_path: Path to CSV file
        
    Returns:
        True if analysis successful, False otherwise
    """
    try:
        _configure_output_paths(csv_file_path)
        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            logging.error(f"CSV file not found: {csv_file_path}")
            return False

        rows = _load_csv_rows(csv_file_path)
        
        # Validate data
        is_valid, error_msg = _validate_rows(rows)
        if not is_valid:
            logging.error(f"Data validation failed: {error_msg}")
            return False
        
        if len(rows) < MIN_DATA_POINTS:
            msg = f"Not enough data points (<{MIN_DATA_POINTS}) for reliable trend analysis."
            logging.warning(msg)
            return False

        timestamps = np.array([row["timestamp"] for row in rows], dtype=float)
        elapsed = timestamps - timestamps[0]


        report = []
        report.append("=" * 40)
        report.append("     MEMORY + CPU TREND ANALYSIS    ")
        report.append("=" * 40)
        report.append(f"Duration: {elapsed[-1] / 60:.2f} minutes")
        report.append(f"Data Points: {len(rows)}")
        report.append("-" * 40)

        metrics = ['total_memory', 'java_heap', 'native_heap', 'code', 'stack', 'graphics']
        leaks = []

        for metric in metrics:
            y_kb = np.array([row[metric] for row in rows], dtype=float)
            x_sec = elapsed

            # Linear regression: y = mx + c
            if len(x_sec) > 1:
                slope, _intercept = np.polyfit(x_sec, y_kb, 1)
            else:
                slope = 0

            # Convert slope to MB/minute for readability
            slope_mb_min = slope * 60 / 1024
            
            # Classify based on thresholds
            if slope_mb_min > CRITICAL_LEAK_THRESHOLD_MB_MIN:
                status = "CRITICAL LEAK"
                leaks.append(f"{metric} (Critical)")
            elif slope_mb_min > WARNING_LEAK_THRESHOLD_MB_MIN:
                status = "WARNING (Rising)"
                leaks.append(f"{metric} (Warning)")
            elif slope_mb_min < -WARNING_LEAK_THRESHOLD_MB_MIN:
                status = "Recovering"
            else:
                status = "Stable"

            report.append(f"{metric:<15} | {slope_mb_min:+.3f} MB/min | {status}")

        report.append("-" * 40)
        report.append("CPU METRICS")
        cpu = np.array([row.get("cpu_usage", 0.0) for row in rows], dtype=float)
        cpu_avg = float(np.mean(cpu)) if len(cpu) else 0.0
        cpu_peak = float(np.max(cpu)) if len(cpu) else 0.0

        if len(elapsed) > 1:
            cpu_slope, _cpu_intercept = np.polyfit(elapsed, cpu, 1)
        else:
            cpu_slope = 0.0

        cpu_slope_percent_min = cpu_slope * 60.0
        if cpu_slope_percent_min > CPU_CRITICAL_SLOPE_PERCENT_MIN:
            cpu_trend_status = "CRITICAL RISING"
        elif cpu_slope_percent_min > CPU_WARNING_SLOPE_PERCENT_MIN:
            cpu_trend_status = "WARNING (Rising)"
        elif cpu_slope_percent_min < -CPU_WARNING_SLOPE_PERCENT_MIN:
            cpu_trend_status = "Falling"
        else:
            cpu_trend_status = "Stable"

        cpu_load_status = "High" if cpu_avg >= CPU_HIGH_AVG_THRESHOLD else "Normal"
        report.append(f"avg_cpu         | {cpu_avg:.2f} %     | {cpu_load_status} load")
        report.append(f"peak_cpu        | {cpu_peak:.2f} %     | Peak")
        report.append(f"cpu_trend       | {cpu_slope_percent_min:+.3f} %/min | {cpu_trend_status}")

        report.append("-" * 40)
        if cpu_trend_status == "CRITICAL RISING" or cpu_avg >= CPU_HIGH_AVG_THRESHOLD:
            cpu_verdict = "FAIL"
        elif cpu_trend_status == "WARNING (Rising)" or cpu_peak >= 90.0:
            cpu_verdict = "WARN"
        else:
            cpu_verdict = "PASS"
        report.append(f"CPU_HEALTH_VERDICT: {cpu_verdict}")

        if CPU_INFO_FILE.exists():
            report.append("-" * 40)
            report.append("CPU INTERPRETATION")
            report.append(CPU_INFO_FILE.read_text(encoding="utf-8").strip())

        report.append("-" * 40)
        if leaks:
            report.append("POTENTIAL LEAKS DETECTED:")
            for leak in leaks:
                report.append(f" - {leak}")
        else:
            report.append("No significant continuous leaks detected.")
        report.append("=" * 40)

        report_str = "\n".join(report)
        logging.info("\n" + report_str + "\n")

        # Save to file
        ANALYSIS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
            f.write(report_str)
        
        return True

    except Exception as e:
        logging.error(f"Error analyzing memory trends: {e}", exc_info=True)
        return False


def plot_total_memory(csv_file: str) -> bool:
    """
    Plot total memory usage over time.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        _configure_output_paths(csv_file)
        rows = _load_csv_rows(csv_file)
        
        # Validate data
        is_valid, error_msg = _validate_rows(rows)
        if not is_valid:
            logging.error(f"Validation failed: {error_msg}")
            return False

        memory_unit, divisor = _determine_memory_unit(rows)
        timestamps = np.array(_timestamps_from_rows(rows), dtype=object)
        total_memory = np.array([row["total_memory"] / divisor for row in rows], dtype=float)

        plt.figure(figsize=DEFAULT_FIGSIZE)
        plt.plot(timestamps, total_memory, linewidth=2, color='steelblue')
        plt.title("Total Memory Usage Over Time", fontsize=14, fontweight='bold')
        plt.xlabel("Timestamp", fontsize=12)
        plt.ylabel(f"Total Memory Usage ({memory_unit})", fontsize=12)
        plt.grid(alpha=0.3)
        plt.tight_layout()

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)
        
        plt.savefig(IMAGE_TOTAL_MEMORY, dpi=DEFAULT_DPI)
        plt.close()
        logging.info("Total memory plot completed")
        return True
    except Exception as e:
        logging.error(f"Error plotting total memory: {e}", exc_info=True)
        return False


def plot_cpu_usage(csv_file: str) -> bool:
    """
    Plot per-process CPU usage over time.

    Args:
        csv_file: Path to CSV file

    Returns:
        True if successful, False otherwise
    """
    try:
        _configure_output_paths(csv_file)
        rows = _load_csv_rows(csv_file)

        # Validate data
        is_valid, error_msg = _validate_rows(rows)
        if not is_valid:
            logging.error(f"Validation failed: {error_msg}")
            return False

        timestamps = np.array(_timestamps_from_rows(rows), dtype=object)
        cpu_usage = np.array([row.get("cpu_usage", 0.0) for row in rows], dtype=float)

        plt.figure(figsize=DEFAULT_FIGSIZE)
        plt.plot(timestamps, cpu_usage, linewidth=2, color="darkorange")
        plt.title("CPU Usage Over Time", fontsize=14, fontweight="bold")
        plt.xlabel("Timestamp", fontsize=12)
        plt.ylabel("CPU Usage (%)", fontsize=12)
        plt.grid(alpha=0.3)
        plt.tight_layout()

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)

        plt.savefig(IMAGE_CPU_USAGE, dpi=DEFAULT_DPI)
        plt.close()
        logging.info("CPU usage plot completed")
        return True
    except Exception as e:
        logging.error(f"Error plotting CPU usage: {e}", exc_info=True)
        return False


def generate_html_report(csv_file: str) -> bool:
    """
    Generate an HTML report that includes all generated plots and analysis text.

    Args:
        csv_file: Path to CSV file

    Returns:
        True if successful, False otherwise
    """
    try:
        _configure_output_paths(csv_file)
        csv_path = Path(csv_file)
        run_name = csv_path.stem

        rows = _load_csv_rows(csv_file)
        is_valid, _ = _validate_rows(rows)
        if not is_valid:
            return False

        start_dt = datetime.fromtimestamp(rows[0]["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        end_dt = datetime.fromtimestamp(rows[-1]["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

        analysis_text = "Analysis file was not generated."
        if ANALYSIS_FILE.exists():
            analysis_text = ANALYSIS_FILE.read_text(encoding="utf-8")

        def image_section_lines(title: str, image_path: Path) -> List[str]:
            if image_path.exists():
                return [
                    "    <section>",
                    f"      <h2>{title}</h2>",
                    f"      <img src=\"{image_path.name}\" alt=\"{title}\" loading=\"lazy\">",
                    "    </section>",
                ]
            return [
                "    <section>",
                f"      <h2>{title}</h2>",
                "      <p>Image not available.</p>",
                "    </section>",
            ]

        html_lines = [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            f"  <title>Memory Monitor Report - {run_name}</title>",
            "  <style>",
            "    :root { --bg: #f7f7f5; --card: #ffffff; --ink: #1f2328; --muted: #5b616b; --line: #d8dde5; --accent: #0f766e; }",
            "    * { box-sizing: border-box; }",
            "    body { margin: 0; font-family: \"Segoe UI\", \"Helvetica Neue\", Helvetica, Arial, sans-serif; color: var(--ink); background: radial-gradient(circle at top right, #e9f5f3, var(--bg) 38%); }",
            "    .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }",
            "    .head { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; }",
            "    h1 { margin: 0 0 8px 0; font-size: 1.5rem; }",
            "    .meta { margin: 4px 0; color: var(--muted); }",
            "    section { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px; margin-bottom: 16px; }",
            "    h2 { margin: 0 0 10px 0; color: var(--accent); font-size: 1.1rem; }",
            "    img { width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--line); }",
            "    pre { margin: 0; white-space: pre-wrap; word-break: break-word; background: #fbfcfd; border: 1px solid var(--line); border-radius: 8px; padding: 12px; color: #111827; font-size: 0.93rem; line-height: 1.45; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <main class=\"wrap\">",
            "    <header class=\"head\">",
            "      <h1>Android Memory Monitor Report</h1>",
            f"      <p class=\"meta\"><strong>Run:</strong> {run_name}</p>",
            f"      <p class=\"meta\"><strong>Samples:</strong> {len(rows)}</p>",
            f"      <p class=\"meta\"><strong>Start:</strong> {start_dt}</p>",
            f"      <p class=\"meta\"><strong>End:</strong> {end_dt}</p>",
            "    </header>",
        ]
        html_lines.extend(image_section_lines("Memory Usage (Stacked)", IMAGE_STACKED_MEMORY))
        html_lines.extend(image_section_lines("Total Memory", IMAGE_TOTAL_MEMORY))
        html_lines.extend(image_section_lines("CPU Usage", IMAGE_CPU_USAGE))
        html_lines.extend(
            [
                "    <section>",
                "      <h2>Analysis Summary</h2>",
                f"      <pre>{analysis_text}</pre>",
                "    </section>",
                "  </main>",
                "</body>",
                "</html>",
            ]
        )

        HTML_REPORT_FILE.write_text("\n".join(html_lines) + "\n", encoding="utf-8")
        logging.info(f"HTML report generated: {HTML_REPORT_FILE}")
        return True
    except Exception as e:
        logging.error(f"Error generating HTML report: {e}", exc_info=True)
        return False


def plot_memory_data(csv_file: str) -> bool:
    """
    Plot stacked memory data and generate analysis report.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        True if all operations successful, False otherwise
    """
    try:
        _configure_output_paths(csv_file)
        csv_path = Path(csv_file)
        if not csv_path.exists():
            logging.error(f"CSV file not found: {csv_file}")
            return False

        IMAGE_STACKED_MEMORY.parent.mkdir(parents=True, exist_ok=True)
        rows = _load_csv_rows(csv_file)

        # Validate data
        is_valid, error_msg = _validate_rows(rows)
        if not is_valid:
            logging.error(f"Validation failed: {error_msg}")
            return False

        memory_unit, divisor = _determine_memory_unit(rows)
        timestamps = np.array(_timestamps_from_rows(rows), dtype=object)
        java_heap = np.array([row["java_heap"] / divisor for row in rows], dtype=float)
        native_heap = np.array([row["native_heap"] / divisor for row in rows], dtype=float)
        code = np.array([row["code"] / divisor for row in rows], dtype=float)
        stack = np.array([row["stack"] / divisor for row in rows], dtype=float)
        graphics = np.array([row["graphics"] / divisor for row in rows], dtype=float)
        
        logging.info(f"Memory unit selected: {memory_unit}")

        # Create stacked area plot
        plt.figure(figsize=DEFAULT_FIGSIZE)
        plt.stackplot(
            timestamps,
            java_heap,
            native_heap,
            code,
            stack,
            graphics,
            labels=["Java Heap", "Native Heap", "Code", "Stack", "Graphics"],
            alpha=0.8,
        )
        plt.legend(loc="upper left", fontsize=10)
        plt.title("Memory Usage Over Time", fontsize=14, fontweight='bold')
        plt.xlabel("Timestamp", fontsize=12)
        plt.ylabel(f"Memory Usage ({memory_unit})", fontsize=12)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.xticks(rotation=45)

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

        plt.savefig(IMAGE_STACKED_MEMORY, dpi=DEFAULT_DPI)
        plt.close()
        logging.info("Stacked memory plot completed")

        # Generate additional plots and analysis
        success = True
        success &= plot_total_memory(csv_file)
        success &= plot_cpu_usage(csv_file)
        success &= analyze_trends(csv_file)
        success &= generate_html_report(csv_file)
        
        return success
        
    except Exception as e:
        logging.error(f"Error plotting memory data: {e}", exc_info=True)
        return False
