
from pathlib import Path

import numpy as np
import pandas as pd


# 1. Configure the simulation
SAMPLE_RATE = 100
DURATION_SECONDS = 60
MACHINE_ID = "MOTOR_01"
RANDOM_SEED = 42

# 2. Build a reproducible time axis
rng = np.random.default_rng(RANDOM_SEED)
total_samples = SAMPLE_RATE * DURATION_SECONDS
time_seconds = np.arange(total_samples) / SAMPLE_RATE

# 3. Simulate baseline acceleration (in g)
ax = 0.03 * np.sin(2 * np.pi * 5 * time_seconds)
ay = 0.02 * np.sin(2 * np.pi * 7 * time_seconds)
az = 1.00 + 0.02 * np.sin(2 * np.pi * 5 * time_seconds)

# 4. Add realistic-looking random measurement noise
ax += rng.normal(0, 0.01, total_samples)
ay += rng.normal(0, 0.01, total_samples)
az += rng.normal(0, 0.01, total_samples)

# 5. Introduce an artificial anomaly after 40 seconds
anomaly_start = int(40 * SAMPLE_RATE)
ax[anomaly_start:] += 0.20 * np.sin(
    2 * np.pi * 5 * time_seconds[anomaly_start:]
)

# 6. Label the simulated operating conditions
scenario = np.full(total_samples, "normal", dtype=object)
scenario[anomaly_start:] = "unusual"

# 7. Assemble the readings into a table
df = pd.DataFrame({
    "time_seconds": time_seconds,
    "machine_id": MACHINE_ID,
    "ax_g": ax,
    "ay_g": ay,
    "az_g": az,
    "scenario": scenario,
})

# 8. Save the dataset inside the project
output_path = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "simulated_vibration.csv"
)

output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)

# 9. Report what was generated
print(f"Dataset saved to: {output_path}")
print(f"Total samples: {len(df)}")
print(f"Sampling rate: {SAMPLE_RATE} Hz")
print(f"Duration: {DURATION_SECONDS} seconds")
print(f"Normal samples: {(df['scenario'] == 'normal').sum()}")
print(f"Unusual samples: {(df['scenario'] == 'unusual').sum()}")
print(df.head())
