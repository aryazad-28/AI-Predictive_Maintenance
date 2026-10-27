
from pathlib import Path

import joblib
import pandas as pd

from src.features import extract_window_features


# 1. Locate the project files
PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_PATH = (
    PROJECT_ROOT / "data" / "raw" / "simulated_vibration.csv"
)

MODEL_PATH = PROJECT_ROOT / "models" / "isolation_forest.joblib"

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "stream_simulation.csv"
)


# 2. Load the existing sensor data and trained model
raw_df = pd.read_csv(RAW_DATA_PATH)
saved_model = joblib.load(MODEL_PATH)

model = saved_model["model"]
feature_columns = saved_model["feature_columns"]


# 3. Replay data in one-second windows
window_size = 100
results = []

for start in range(0, len(raw_df) - window_size + 1, window_size):
    window = raw_df.iloc[start : start + window_size].copy()

    # Extract features using the existing feature pipeline.
    features = extract_window_features(window)

    # Arrange the features in the exact order expected by the model.
    feature_row = pd.DataFrame(
        [[features[column] for column in feature_columns]],
        columns=feature_columns,
    )

    # Use the saved model without retraining it.
    raw_prediction = model.predict(feature_row)[0]
    anomaly_score = model.decision_function(feature_row)[0]

    results.append(
        {
            "start_time": features["start_time"],
            "end_time": features["end_time"],
            "prediction": (
                "Unusual" if raw_prediction == -1 else "Normal"
            ),
            "anomaly_score": float(anomaly_score),
            "scenario": window["scenario"].iloc[0],
        }
    )


# 4. Save the replay results separately
results_df = pd.DataFrame(results)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
results_df.to_csv(OUTPUT_PATH, index=False)


# 5. Print a simulation summary
normal_count = (results_df["prediction"] == "Normal").sum()
unusual_count = (results_df["prediction"] == "Unusual").sum()

print("\n--- Software-in-the-Loop Simulation ---")
print(f"Raw samples processed: {len(raw_df)}")
print(f"Window size: {window_size} samples")
print(f"Windows processed: {len(results_df)}")
print(f"Normal predictions: {normal_count}")
print(f"Unusual predictions: {unusual_count}")
print(f"Results saved to: {OUTPUT_PATH}")
print("\nFirst 10 simulated predictions:")
print(results_df.head(10).to_string(index=False))
