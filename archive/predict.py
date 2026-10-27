
from pathlib import Path

import joblib
import pandas as pd


# 1. Locate the project files
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "vibration_features.csv"
)

MODEL_PATH = PROJECT_ROOT / "models" / "isolation_forest.joblib"

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "predictions.csv"
)


# 2. Load the trained model and its feature configuration
saved_model = joblib.load(MODEL_PATH)

model = saved_model["model"]
feature_columns = saved_model["feature_columns"]


# 3. Load the extracted vibration features
df = pd.read_csv(DATA_PATH)

X = df[feature_columns]


# 4. Predict normal and unusual vibration patterns
raw_predictions = model.predict(X)

df["prediction"] = [
    "Unusual" if prediction == -1 else "Normal"
    for prediction in raw_predictions
]

# Lower scores indicate patterns that are more anomalous.
df["anomaly_score"] = model.decision_function(X)


# 5. Save the predictions
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT_PATH, index=False)


# 6. Display a summary
print("\n--- Predictive Maintenance Results ---")
print(f"Total windows analysed: {len(df)}")
print(f"Normal windows: {(df['prediction'] == 'Normal').sum()}")
print(f"Unusual windows: {(df['prediction'] == 'Unusual').sum()}")

print("\nFirst 10 predictions:")
print(
    df[
        ["start_time", "end_time", "prediction", "anomaly_score"]
    ].head(10).to_string(index=False)
)

print(f"\nResults saved to: {OUTPUT_PATH}")
