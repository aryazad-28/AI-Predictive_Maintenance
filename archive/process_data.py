
from pathlib import Path

import pandas as pd

from src.features import extract_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]

input_path = PROJECT_ROOT / "data" / "raw" / "simulated_vibration.csv"
output_path = PROJECT_ROOT / "data" / "processed" / "vibration_features.csv"

# Load the raw measurements.
raw_df = pd.read_csv(input_path)

# Calculate one feature row per one-second window.
features_df = extract_features(raw_df, window_size=100)

# Create the output folder if needed.
output_path.parent.mkdir(parents=True, exist_ok=True)

# Save the feature table.
features_df.to_csv(output_path, index=False)

print(f"Raw samples: {len(raw_df)}")
print(f"Feature windows: {len(features_df)}")
print(f"Saved features to: {output_path}")
print(features_df.head())
