
import numpy as np
import pandas as pd


AXES = ["ax_g", "ay_g", "az_g"]


def extract_window_features(window: pd.DataFrame) -> dict:
    """Calculate vibration features for one window of sensor readings."""

    features = {
        "start_time": float(window["time_seconds"].iloc[0]),
        "end_time": float(window["time_seconds"].iloc[-1]),
    }

    for axis in AXES:
        signal = window[axis].to_numpy(dtype=float)

        # Remove the window's mean before measuring vibration.
        centred_signal = signal - np.mean(signal)

        features[f"{axis}_rms"] = float(
            np.sqrt(np.mean(centred_signal ** 2))
        )

        features[f"{axis}_std"] = float(np.std(signal))

        features[f"{axis}_peak"] = float(
            np.max(np.abs(centred_signal))
        )

        features[f"{axis}_peak_to_peak"] = float(
            np.ptp(centred_signal)
        )

    return features


def extract_features(
    df: pd.DataFrame,
    window_size: int = 100,
) -> pd.DataFrame:
    """Convert raw readings into one feature row per complete window."""

    required_columns = ["time_seconds", *AXES]
    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    feature_rows = []

    for start in range(0, len(df) - window_size + 1, window_size):
        window = df.iloc[start : start + window_size]
        features = extract_window_features(window)

        # Preserve the known simulation label for later evaluation.
        if "scenario" in window.columns:
            features["scenario"] = window["scenario"].iloc[0]

        feature_rows.append(features)

    return pd.DataFrame(feature_rows)
