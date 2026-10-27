
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, classification_report


# 1. Locate the project folders and files
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "vibration_features.csv"
)

MODEL_PATH = PROJECT_ROOT / "models" / "isolation_forest.joblib"


# 2. Load the processed feature table
df = pd.read_csv(DATA_PATH)

# 3. Define the numerical inputs for the model
FEATURE_COLUMNS = [
    "ax_g_rms",
    "ax_g_std",
    "ax_g_peak",
    "ax_g_peak_to_peak",
    "ay_g_rms",
    "ay_g_std",
    "ay_g_peak",
    "ay_g_peak_to_peak",
    "az_g_rms",
    "az_g_std",
    "az_g_peak",
    "az_g_peak_to_peak",
]


# 4. Separate training data from evaluation data
train_df = df[
    (df["scenario"] == "normal")
    & (df["start_time"] < 30)
].copy()

test_df = df[
    (df["start_time"] >= 30)
].copy()

X_train = train_df[FEATURE_COLUMNS]
X_test = test_df[FEATURE_COLUMNS]

# The known simulation labels are used only for evaluation.
y_true = (test_df["scenario"] == "unusual").astype(int)


# 5. Create and train the Isolation Forest model
model = IsolationForest(
    n_estimators=200,
    contamination="auto",
    random_state=42,
)

model.fit(X_train)


# 6. Predict which evaluation windows are unusual
raw_predictions = model.predict(X_test)

# Isolation Forest returns -1 for anomalies and 1 for inliers.
y_pred = (raw_predictions == -1).astype(int)


# 7. Evaluate the results
tn, fp, fn, tp = confusion_matrix(
    y_true,
    y_pred,
    labels=[0, 1],
).ravel()

print("\n--- Isolation Forest Evaluation ---")
print(f"Training windows: {len(X_train)}")
print(f"Evaluation windows: {len(X_test)}")
print(f"True negatives: {tn}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")
print(f"True positives: {tp}")

print("\nDetailed evaluation:")
print(
    classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["Normal", "Unusual"],
        zero_division=0,
    )
)


# 8. Save the trained model and feature configuration
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

joblib.dump(
    {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
    },
    MODEL_PATH,
)

print(f"Model saved to: {MODEL_PATH}")
