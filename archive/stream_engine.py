
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from src.features import extract_window_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_PATH = (
    PROJECT_ROOT / "data" / "raw" / "simulated_vibration.csv"
)

MODEL_PATH = PROJECT_ROOT / "models" / "isolation_forest.joblib"

@st.cache_resource
def load_saved_model():
    """Load the trained model once and reuse it across reruns."""
    return joblib.load(MODEL_PATH)

def load_simulation():
    """Load the simulation data and reuse the cached trained model."""
    raw_df = pd.read_csv(RAW_DATA_PATH)
    saved_model = load_saved_model()

    return raw_df, saved_model



def predict_window(window, model, feature_columns):
    """Extract features and predict one window."""
    features = extract_window_features(window)

    feature_row = pd.DataFrame(
        [[features[column] for column in feature_columns]],
        columns=feature_columns,
    )

    raw_prediction = model.predict(feature_row)[0]
    anomaly_score = model.decision_function(feature_row)[0]

    result = {
        "start_time": features["start_time"],
        "end_time": features["end_time"],
        "prediction": "Unusual" if raw_prediction == -1 else "Normal",
        "anomaly_score": float(anomaly_score),
    }

    # Synthetic data has a known scenario; live data does not.
    if "scenario" in window.columns:
        result["scenario"] = window["scenario"].iloc[0]

    return result


def replay_all_windows():
    """Return predictions generated one window at a time."""
    raw_df, saved_model = load_simulation()

    model = saved_model["model"]
    feature_columns = saved_model["feature_columns"]

    window_size = 100
    results = []

    for start in range(
        0,
        len(raw_df) - window_size + 1,
        window_size,
    ):
        window = raw_df.iloc[start : start + window_size].copy()

        result = predict_window(
            window,
            model,
            feature_columns,
        )

        results.append(result)

    return pd.DataFrame(results)



@st.cache_resource
def _get_live_prediction_state():
    """Create reusable state for incremental live predictions."""
    return {
        "processed_readings": 0,
        "predictions": [],
        "last_file_signature": None,
    }


def predict_live_csv():
    """Predict newly completed 100-reading windows from live sensor data."""
    live_data_path = (
        PROJECT_ROOT / "data" / "processed" / "live_sensor_data.csv"
    )

    if not live_data_path.exists():
        raise FileNotFoundError(
            f"Live sensor data not found: {live_data_path}"
        )

    raw_df = pd.read_csv(live_data_path)

    required_columns = [
        "time_seconds",
        "ax_g",
        "ay_g",
        "az_g",
    ]

    missing = set(required_columns) - set(raw_df.columns)
    if missing:
        raise ValueError(
            f"Live CSV is missing columns: {sorted(missing)}"
        )

    saved_model = load_saved_model()
    model = saved_model["model"]
    feature_columns = saved_model["feature_columns"]

    window_size = 100
    state = _get_live_prediction_state()

    # Detect a cleared, replaced, or restarted CSV.
    file_signature = (
        len(raw_df),
        raw_df["time_seconds"].iloc[0] if not raw_df.empty else None,
        raw_df["time_seconds"].iloc[-1] if not raw_df.empty else None,
    )

    if (
        state["last_file_signature"] is not None
        and (
            len(raw_df) < state["processed_readings"]
            or (
                state["processed_readings"] > 0
                and file_signature[1]
                != state["last_file_signature"][1]
            )
        )
    ):
        state["processed_readings"] = 0
        state["predictions"] = []

    # Process only complete windows that have not been processed before.
    complete_readings = (len(raw_df) // window_size) * window_size

    for start in range(
        state["processed_readings"],
        complete_readings,
        window_size,
    ):
        window = raw_df.iloc[start : start + window_size].copy()

        result = predict_window(
            window,
            model,
            feature_columns,
        )

        result["window_number"] = start // window_size + 1
        state["predictions"].append(result)

    state["processed_readings"] = complete_readings
    state["last_file_signature"] = file_signature

    return pd.DataFrame(state["predictions"])

