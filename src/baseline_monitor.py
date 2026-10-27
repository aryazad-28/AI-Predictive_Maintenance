
from pathlib import Path

import pandas as pd

from src.baseline_learning import (
    FEATURE_COLUMNS,
    LIVE_DATA_PATH,
    WINDOW_SIZE,
    load_and_validate_data,
)
from src.baseline_registry import get_active_baseline
from src.features import extract_window_features


# Initial prototype thresholds. Validate these against real motor data.
RANGE_MARGIN = 0.10
MIN_DEVIATING_FEATURES = 3


def compare_features(features: dict, baseline: dict) -> dict:
    """Compare one vibration window with the approved healthy baseline."""

    summary = baseline["feature_summary"]
    deviations = []

    for name in FEATURE_COLUMNS:
        value = float(features[name])
        stats = summary[name]

        lower = float(stats["p05"])
        upper = float(stats["p95"])
        margin = max(abs(upper - lower) * RANGE_MARGIN, 1e-9)

        if value < lower - margin or value > upper + margin:
            deviations.append(name)

    is_anomaly = len(deviations) >= MIN_DEVIATING_FEATURES

    return {
        "baseline_version": baseline["baseline_version"],
        "deviating_feature_count": len(deviations),
        "deviating_features": ", ".join(deviations),
        "baseline_status": (
            "Anomaly Detected" if is_anomaly else "Monitoring"
        ),
        "baseline_deviation": is_anomaly,
    }


def _empty_monitor_frame() -> pd.DataFrame:
    """Return an empty result with the expected columns."""

    return pd.DataFrame(columns=[
        "machine_id",
        "session_id",
        "start_time",
        "end_time",
        "window_received_timestamp",
        "baseline_version",
        "deviating_feature_count",
        "deviating_features",
        "baseline_status",
        "baseline_deviation",
        "recent_anomalies",
        "persistent_fault",
    ])


def monitor_machine(
    machine_id: str,
    csv_path: Path = LIVE_DATA_PATH,
    persistence_window: int = 5,
    required_anomalies: int = 3,
) -> pd.DataFrame:
    """
    Monitor complete windows collected strictly after baseline activation.

    A possible fault is raised when at least 3 of the latest 5 complete
    monitoring windows are anomalous. The baseline is never retrained here.
    """

    if persistence_window < 1:
        raise ValueError("persistence_window must be at least 1.")

    if not 1 <= required_anomalies <= persistence_window:
        raise ValueError(
            "required_anomalies must be between 1 and persistence_window."
        )

    baseline = get_active_baseline(machine_id)

    if baseline.get("status") != "active":
        raise ValueError(
            f"No approved active baseline for machine {machine_id}."
        )

    if not baseline.get("sensor_configuration"):
        raise ValueError("Baseline sensor configuration is missing.")

    activation_record = baseline.get("activation_record") or {}
    activated_at = activation_record.get("activated_at_utc")

    if not activated_at:
        raise ValueError(
            "The active baseline has no activation timestamp. "
            "Activate a validated baseline using the baseline registry."
        )

    try:
        activation_epoch = pd.Timestamp(activated_at).timestamp()
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            "The baseline activation timestamp is invalid."
        ) from error

    df = load_and_validate_data(Path(csv_path))

    if "received_timestamp" not in df.columns:
        raise ValueError(
            "The live CSV needs a received_timestamp column. "
            "Restart the updated serial collector."
        )

    df["received_timestamp"] = pd.to_numeric(
        df["received_timestamp"], errors="coerce"
    )

    if df["received_timestamp"].isna().any():
        raise ValueError(
            "The live CSV contains invalid received_timestamp values."
        )

    # Critical: exclude all readings collected before baseline activation.
    df = df[df["received_timestamp"] > activation_epoch].copy()

    if df.empty:
        return _empty_monitor_frame()

    results = []

    # Never join windows across separate collector sessions.
    for session_id, session_df in df.groupby("session_id", sort=False):
        session_df = session_df.reset_index(drop=True)

        complete_readings = (
            len(session_df) // WINDOW_SIZE
        ) * WINDOW_SIZE

        for start in range(0, complete_readings, WINDOW_SIZE):
            window = session_df.iloc[
                start:start + WINDOW_SIZE
            ].copy()

            features = extract_window_features(window)
            comparison = compare_features(features, baseline)

            results.append({
                "machine_id": machine_id,
                "session_id": int(session_id),
                "start_time": features["start_time"],
                "end_time": features["end_time"],
                "window_received_timestamp": float(
                    window["received_timestamp"].iloc[-1]
                ),
                **comparison,
            })

    if not results:
        return _empty_monitor_frame()

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values(
        "window_received_timestamp"
    ).reset_index(drop=True)

    # Count abnormal windows in the recent window history.
    anomaly_flags = result_df["baseline_deviation"].astype(int)

    result_df["recent_anomalies"] = anomaly_flags.rolling(
        window=persistence_window,
        min_periods=1,
    ).sum().astype(int)

    # Do not declare a persistent fault until enough complete windows exist.
    result_df["persistent_fault"] = (
        anomaly_flags.rolling(
            window=persistence_window,
            min_periods=persistence_window,
        )
        .sum()
        .ge(required_anomalies)
    )

    return result_df[[
        "machine_id",
        "session_id",
        "start_time",
        "end_time",
        "window_received_timestamp",
        "baseline_version",
        "deviating_feature_count",
        "deviating_features",
        "baseline_status",
        "baseline_deviation",
        "recent_anomalies",
        "persistent_fault",
    ]]
