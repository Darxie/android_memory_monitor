import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.dates as mdates
import logging
from timestamp import ExecutionTimestamp


timestamp = ExecutionTimestamp.get_timestamp()
directory = Path(f"output/{timestamp}")

IMAGE_STACKED_MEMORY = directory / f"memory_stacked_line_chart_{timestamp}.png"
IMAGE_TOTAL_MEMORY = directory / f"memory_total_{timestamp}.png"


def plot_total_memory(csv_file):
    df = pd.read_csv(csv_file)
    df.fillna(0, inplace=True)

    numeric_columns = df.columns.difference(["timestamp"])
    memory_data = (
        df[numeric_columns].apply(pd.to_numeric, errors="coerce") / 1024
    )  # Convert to MB

    # Check if total_memory column exceeds 1024 MB (1 GB)
    if memory_data["total_memory"].max() > 1024:
        memory_data["total_memory"] = (
            memory_data["total_memory"] / 1024
        )  # Convert to GB
        memory_unit = "GB"
    else:
        memory_unit = "MB"

    df[numeric_columns] = memory_data

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    plt.figure(figsize=(14, 8))
    plt.plot(df["timestamp"], df["total_memory"])
    plt.title("Total Memory Usage Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel(f"Total Memory Usage ({memory_unit})")
    plt.tight_layout()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.xticks(rotation=45)
    plt.savefig(IMAGE_TOTAL_MEMORY)
    logging.info("\nPlotting total memory data completed.\n\n")
    plt.show()


def plot_memory_data(csv_file):
    df = pd.read_csv(csv_file)

    if len(df) < 2:
        logging.error(
            "The data output is not suitable for plotting as it contains less than 2 points"
        )
        exit(1)

    df.fillna(0, inplace=True) # Fill any NA/NaN values with 0

    numeric_columns = df.columns.difference(["timestamp"])
    # Convert numeric columns to float (MB) in one step
    memory_data = df[numeric_columns].apply(pd.to_numeric, errors="coerce") / 1024

    # Decide whether to scale to GB
    if memory_data.to_numpy().max() > 1024:
        memory_data = memory_data / 1024
        memory_unit = "GB"
    else:
        memory_unit = "MB"

    df[numeric_columns] = memory_data

    logging.info(f"Memory unit selected: {memory_unit}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

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
    plt.ylabel(f"Memory Usage ({memory_unit})")
    plt.tight_layout()
    plt.xticks(rotation=45)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.savefig(IMAGE_STACKED_MEMORY)
    logging.info("\nPlotting stacked memory data plot completed.\n\n")
    plt.show()

    plot_total_memory(csv_file)
