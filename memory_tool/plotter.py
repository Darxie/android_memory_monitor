import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.dates as mdates
import logging
from timestamp import ExecutionTimestamp


timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")

IMAGE = directory / f"memory_stacked_line_chart_{timestamp}.png"
IMAGE_TOTAL_MEMORY = directory / f"memory_total_{timestamp}.png"


def plot_total_memory(csv_file):
    df = pd.read_csv(csv_file)
    df = df.fillna(0)  # Fill any NA/NaN values with 0
    df.iloc[:, df.columns != "timestamp"].apply(pd.to_numeric).div(
        1024
    )  # convert to MB

    # Check if any value in total_memory exceeds 1000 MB (1 GB)
    if df["total_memory"].max() > 1000:
        df["total_memory"] = df["total_memory"].div(1024)  # convert to GB
        memory_unit = "GB"
    else:
        memory_unit = "MB"

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    plt.figure(figsize=(14, 8))
    plt.plot(df["timestamp"], df["total_memory"])
    plt.title("Total Memory Usage Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel(f"Total Memory Usage ({memory_unit})")
    plt.tight_layout()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator())

    plt.xticks(rotation=45)
    plt.savefig(IMAGE_TOTAL_MEMORY)
    logging.info("\nPlotting total memory data completed.\n\n")
    plt.show()


def plot_memory_data(csv_file, timestamp):
    df = pd.read_csv(csv_file)
    df = df.fillna(0)  # Fill any NA/NaN values with 0
    df.iloc[:, df.columns != "timestamp"].apply(pd.to_numeric).div(
        1024
    )  # convert to MB
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df["timestamp"] = df["timestamp"].dt.strftime("%H:%M")

    plt.figure(figsize=(14, 8))
    plt.stackplot(
        df["timestamp"],
        df["java_heap"],
        df["native_heap"],
        df["code"],
        df["stack"],
        df["graphics"],
        labels=["Java Heap", "Native Heap", "Code", "Stack", "Graphics"],
    )
    plt.legend(loc="upper left")
    plt.title("Memory Usage Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Memory Usage (MB)")
    plt.tight_layout()
    plt.xticks(rotation=45)
    plt.savefig(IMAGE)
    logging.info("\nPlotting stacked memory data plot completed.\n\n")
    plt.show()

    plot_total_memory(csv_file)
