import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

directory = Path("output")
# Get the current timestamp in a specific format
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

IMAGE = directory / f"memory_stacked_line_chart_{timestamp}.png"
IMAGE_TOTAL_MEMORY = directory / f"memory_total_{timestamp}.png"


def plot_total_memory(csv_file):
    df = pd.read_csv(csv_file)
    df = df.fillna(0)  # Fill any NA/NaN values with 0
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    plt.figure(figsize=(14, 8))
    plt.plot(df["timestamp"], df["total_memory"])
    plt.title("Total Memory Usage Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Total Memory Usage (KB)")
    plt.tight_layout()
    plt.savefig(IMAGE_TOTAL_MEMORY)
    plt.show()


def plot_memory_data(csv_file):
    df = pd.read_csv(csv_file)
    df = df.fillna(0)  # Fill any NA/NaN values with 0
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
    plt.ylabel("Memory Usage (KB)")
    # plt.tight_layout()
    plt.savefig(IMAGE)
    plt.show()

    plot_total_memory(csv_file)
