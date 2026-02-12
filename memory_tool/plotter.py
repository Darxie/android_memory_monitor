"""
Memory data plotting and analysis module.
Generates visualizations and trend analysis reports.
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.dates as mdates
import logging
import numpy as np
from typing import Optional, Tuple
from memory_tool.timestamp import ExecutionTimestamp


timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")

IMAGE_STACKED_MEMORY = directory / f"memory_stacked_line_chart_{timestamp}.png"
IMAGE_TOTAL_MEMORY = directory / f"memory_total_{timestamp}.png"
ANALYSIS_FILE = directory / f"memory_analysis_{timestamp}.txt"

# Constants
MIN_DATA_POINTS = 10
CRITICAL_LEAK_THRESHOLD_MB_MIN = 0.5
WARNING_LEAK_THRESHOLD_MB_MIN = 0.05
MEMORY_GB_THRESHOLD = 1024  # MB
DEFAULT_DPI = 100
DEFAULT_FIGSIZE = (14, 8)


def _validate_dataframe(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """
    Validate dataframe for plotting.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if df.empty:
        return False, "DataFrame is empty"
    
    if len(df) < 2:
        return False, f"Insufficient data: {len(df)} rows (need at least 2)"
    
    required_columns = ['timestamp', 'total_memory', 'java_heap', 'native_heap', 
                       'code', 'stack', 'graphics']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        return False, f"Missing columns: {', '.join(missing_cols)}"
    
    return True, None


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
        df = pd.read_csv(csv_file_path)
        
        # Validate data
        is_valid, error_msg = _validate_dataframe(df)
        if not is_valid:
            logging.error(f"DataFrame validation failed: {error_msg}")
            return False
        
        if len(df) < MIN_DATA_POINTS:
            msg = f"Not enough data points (<{MIN_DATA_POINTS}) for reliable trend analysis."
            logging.warning(msg)
            return False

        # Normalize time to start from 0
        df['elapsed'] = df['timestamp'] - df['timestamp'].iloc[0]

        report = []
        report.append("=" * 40)
        report.append("       MEMORY TREND ANALYSIS       ")
        report.append("=" * 40)
        report.append(f"Duration: {df['elapsed'].iloc[-1] / 60:.2f} minutes")
        report.append(f"Data Points: {len(df)}")
        report.append("-" * 40)

        metrics = ['total_memory', 'java_heap', 'native_heap', 'code', 'stack', 'graphics']
        leaks = []

        for metric in metrics:
            if metric not in df.columns:
                continue

            # Clean data: Convert to numeric, handle NA
            y_kb = pd.to_numeric(df[metric], errors='coerce').fillna(0)
            x_sec = df['elapsed']

            # Linear regression: y = mx + c
            if len(x_sec) > 1:
                slope, intercept = np.polyfit(x_sec, y_kb, 1)
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
        if leaks:
            report.append(f"⚠️  POTENTIAL LEAKS DETECTED:\n   - " + "\n   - ".join(leaks))
        else:
            report.append("✅  No significant continuous leaks detected.")
        report.append("=" * 40)

        report_str = "\n".join(report)
        logging.info("\n" + report_str + "\n")

        # Save to file
        with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
            f.write(report_str)
        
        return True

    except FileNotFoundError:
        logging.error(f"CSV file not found: {csv_file_path}")
        return False
    except Exception as e:
        logging.error(f"Error analyzing memory trends: {e}", exc_info=True)
        return False


def _convert_kb_to_display_unit(df: pd.DataFrame, memory_unit_ref=None) -> Tuple[pd.DataFrame, str]:
    """
    Convert memory values from KB to appropriate display unit (MB or GB).
    
    Args:
        df: DataFrame with memory data
        memory_unit_ref: Unused parameter (kept for backward compatibility)
        
    Returns:
        Tuple of (modified DataFrame, unit string)
    """
    numeric_columns = df.columns.difference(["timestamp"])
    memory_data = df[numeric_columns].apply(pd.to_numeric, errors="coerce") / 1024
    
    if memory_data.to_numpy().max() > MEMORY_GB_THRESHOLD:
        memory_data = memory_data / 1024
        unit = "GB"
    else:
        unit = "MB"
    
    df[numeric_columns] = memory_data
    return df, unit


def plot_total_memory(csv_file: str) -> bool:
    """
    Plot total memory usage over time.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        df = pd.read_csv(csv_file)
        df.fillna(0, inplace=True)
        
        # Validate data
        is_valid, error_msg = _validate_dataframe(df)
        if not is_valid:
            logging.error(f"Validation failed: {error_msg}")
            return False
        
        df, memory_unit = _convert_kb_to_display_unit(df, None)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

        plt.figure(figsize=DEFAULT_FIGSIZE)
        plt.plot(df["timestamp"], df["total_memory"], linewidth=2, color='steelblue')
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


def plot_memory_data(csv_file: str) -> bool:
    """
    Plot stacked memory data and generate analysis report.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        True if all operations successful, False otherwise
    """
    try:
        df = pd.read_csv(csv_file)

        # Validate data
        is_valid, error_msg = _validate_dataframe(df)
        if not is_valid:
            logging.error(f"Validation failed: {error_msg}")
            return False

        df.fillna(0, inplace=True)
        df, memory_unit = _convert_kb_to_display_unit(df, None)
        
        logging.info(f"Memory unit selected: {memory_unit}")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

        # Create stacked area plot
        plt.figure(figsize=DEFAULT_FIGSIZE)
        plt.stackplot(
            df["timestamp"],
            df["java_heap"],
            df["native_heap"],
            df["code"],
            df["stack"],
            df["graphics"],
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
        success &= analyze_trends(csv_file)
        
        return success
        
    except FileNotFoundError:
        logging.error(f"CSV file not found: {csv_file}")
        return False
    except Exception as e:
        logging.error(f"Error plotting memory data: {e}", exc_info=True)
        return False
