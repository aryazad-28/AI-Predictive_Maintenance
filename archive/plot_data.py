
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# 1. Locate the generated dataset
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "simulated_vibration.csv"

# 2. Load the CSV file
df = pd.read_csv(DATA_PATH)

# 3. Select the first 50 seconds of data
plot_df = df[df["time_seconds"] < 50]

# 4. Create three plots, one for each sensor axis
fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

axes[0].plot(plot_df["time_seconds"], plot_df["ax_g"])
axes[0].set_ylabel("X acceleration (g)")
axes[0].set_title("Simulated Motor Vibration")

axes[1].plot(plot_df["time_seconds"], plot_df["ay_g"])
axes[1].set_ylabel("Y acceleration (g)")

axes[2].plot(plot_df["time_seconds"], plot_df["az_g"])
axes[2].set_ylabel("Z acceleration (g)")
axes[2].set_xlabel("Time (seconds)")

# 5. Mark where the artificial anomaly begins
for ax in axes:
    ax.axvline(40, color="red", linestyle="--", label="Anomaly begins")
    ax.legend()

plt.tight_layout()
plt.show()
