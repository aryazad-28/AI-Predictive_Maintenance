
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PREDICTIONS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "predictions.csv"
)

df = pd.read_csv(PREDICTIONS_PATH)

# The simulation labels tell us what actually happened.
y_true = (df["scenario"] == "unusual").astype(int)

# Convert the model's text predictions into 0 and 1.
y_pred = (df["prediction"] == "Unusual").astype(int)

tn, fp, fn, tp = confusion_matrix(
    y_true, y_pred, labels=[0, 1]
).ravel()

print("\n--- Prediction Evaluation ---")
print(f"Correctly identified normal windows: {tn}")
print(f"False alarms: {fp}")
print(f"Missed unusual windows: {fn}")
print(f"Correctly identified unusual windows: {tp}")

print("\nDetailed report:")
print(
    classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["Normal", "Unusual"],
        zero_division=0,
    )
)
