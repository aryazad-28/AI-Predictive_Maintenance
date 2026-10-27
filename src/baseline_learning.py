
from datetime import datetime, timezone
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd

from src.features import extract_window_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LIVE_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "live_sensor_data.csv"
)

BASELINE_ROOT = PROJECT_ROOT / "data" / "baselines"

WINDOW_SIZE = 100
MINIMUM_WINDOWS = 20

REQUIRED_COLUMNS = [
    "time_seconds",
    "ax_g",
    "ay_g",
    "az_g",
]

FEATURE_COLUMNS = [
    f"{axis}_{feature}"
    for axis in ["ax_g", "ay_g", "az_g"]
    for feature in ["rms", "std", "peak", "peak_to_peak"]
]


def validate_machine_id(machine_id: str) -> str:
    """Validate machine identifiers used for baseline storage."""
    machine_id = machine_id.strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", machine_id):
        raise ValueError(
            "Machine ID must contain only letters, numbers, "
            "hyphens, or underscores, with a maximum of 50 characters."
        )

    return machine_id


def load_and_validate_data(csv_path: Path) -> pd.DataFrame:
    """Load sensor data and identify collection-session boundaries."""

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Sensor data file not found: {csv_path}"
        )

    df = pd.read_csv(csv_path)

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"Sensor CSV is missing columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError("The sensor CSV contains no readings.")

    for column in REQUIRED_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(
            "Sensor data contains missing or non-numeric values."
        )

    if not np.isfinite(df[REQUIRED_COLUMNS].to_numpy()).all():
        raise ValueError(
            "Sensor data contains infinite or invalid numeric values."
        )

    # A decreasing timestamp indicates a collection-session boundary.
    time_reset = df["time_seconds"].diff() < 0

    if "batch_number" in df.columns:
        batch_number = pd.to_numeric(
            df["batch_number"], errors="coerce"
        )

        if batch_number.isna().any():
            raise ValueError(
                "The batch_number column contains invalid values."
            )

        batch_reset = batch_number.diff() < 0
        session_boundary = time_reset | batch_reset
    else:
        session_boundary = time_reset

    df = df.copy()
    df["session_id"] = session_boundary.cumsum().astype(int)

    # Timestamps must not decrease within a collection session.
    for session_id, session_df in df.groupby(
        "session_id", sort=False
    ):
        if (
            session_df["time_seconds"].diff().dropna() < 0
        ).any():
            raise ValueError(
                f"Timestamps decrease within session {session_id}."
            )

    return df



def next_baseline_version(machine_dir: Path) -> int:
    """Find the next unused baseline version number."""

    existing_versions = []

    if machine_dir.exists():
        for path in machine_dir.glob("baseline_v*.json"):
            match = re.fullmatch(
                r"baseline_v(\d+)\.json",
                path.name,
            )

            if match:
                existing_versions.append(int(match.group(1)))

    return max(existing_versions, default=0) + 1



def create_baseline(
    machine_id: str,
    sensor_configuration: str,
    healthy_operation_verified: bool,
    csv_path: Path = LIVE_DATA_PATH,
    minimum_windows: int = MINIMUM_WINDOWS,
) -> Path:
    """
    Create a versioned machine baseline for verified healthy operation.

    The saved baseline remains pending_review and is not activated.
    """

    machine_id = validate_machine_id(machine_id)

    if not isinstance(sensor_configuration, str) or not sensor_configuration.strip():
        raise ValueError(
            "Describe the sensor model, placement, and orientation."
        )

    if healthy_operation_verified is not True:
        raise ValueError(
            "Baseline learning requires explicit verification that "
            "the machine is operating in a known healthy condition."
        )

    if (
        not isinstance(minimum_windows, int)
        or isinstance(minimum_windows, bool)
        or minimum_windows < MINIMUM_WINDOWS
    ):
        raise ValueError(
            f"At least {MINIMUM_WINDOWS} windows are required "
            "for this prototype."
        )

    df = load_and_validate_data(Path(csv_path))

    feature_rows = []
    complete_windows = 0
    readings_used = 0

    # Process each collection session independently so that a window
    # never combines readings from before and after a collector restart.
    for _, session_df in df.groupby("session_id", sort=False):
        session_df = session_df.reset_index(drop=True)

        session_complete_readings = (
            len(session_df) // WINDOW_SIZE
        ) * WINDOW_SIZE

        readings_used += session_complete_readings

        for start in range(
            0, session_complete_readings, WINDOW_SIZE
        ):
            window = session_df.iloc[
                start : start + WINDOW_SIZE
            ].copy()

            features = extract_window_features(window)

            feature_rows.append({
                name: features[name]
                for name in FEATURE_COLUMNS
            })

            complete_windows += 1

    if complete_windows < minimum_windows:
        required_readings = minimum_windows * WINDOW_SIZE

        raise ValueError(
            f"Only {complete_windows} complete windows are available "
            f"across all sessions; need at least {minimum_windows}. "
            f"At least {required_readings} readings are needed in total, "
            "with enough complete windows inside individual sessions."
        )

    feature_df = pd.DataFrame(
        feature_rows,
        columns=FEATURE_COLUMNS,
    )

    if not np.isfinite(feature_df.to_numpy()).all():
        raise ValueError(
            "Feature extraction produced invalid values. "
            "The baseline was not saved."
        )

    # Catch a dataset where every extracted feature is constant.
    if (feature_df.std(ddof=0) == 0).all():
        raise ValueError(
            "All extracted features are constant across windows. "
            "Check the sensor and collect representative data."
        )

    feature_summary = {}

    for column in FEATURE_COLUMNS:
        values = feature_df[column]

        feature_summary[column] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
            "median": float(values.median()),
            "p05": float(values.quantile(0.05)),
            "p95": float(values.quantile(0.95)),
        }

    machine_dir = BASELINE_ROOT / machine_id
    machine_dir.mkdir(parents=True, exist_ok=True)

    version = next_baseline_version(machine_dir)

    baseline = {
        "schema_version": 1,
        "baseline_version": version,
        "machine_id": machine_id,
        "sensor_configuration": sensor_configuration.strip(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(Path(csv_path)),
        "window_size_readings": WINDOW_SIZE,
        "complete_windows": complete_windows,
        "readings_used": readings_used,
        "healthy_operation_verified": True,
        "status": "pending_review",
        "feature_names": FEATURE_COLUMNS,
        "feature_summary": feature_summary,
        "review_notes": (
            "Review data quality, operating conditions, and "
            "representativeness before approving activation."
        ),
    }

    output_path = (
        machine_dir / f"baseline_v{version:03d}.json"
    )

    # Exclusive creation prevents accidentally overwriting a version.
    with output_path.open("x", encoding="utf-8") as file:
        json.dump(baseline, file, indent=2)

    return output_path


if __name__ == "__main__":
    print("=== Machine Baseline Learning ===")
    print("This creates a baseline for review; it does not activate it.")
    print(f"Default data source: {LIVE_DATA_PATH}")

    machine_id = input(
        "Machine ID (example: MOTOR_001): "
    ).strip()

    sensor_configuration = input(
        "Sensor model, placement, and orientation: "
    ).strip()

    confirmation = input(
        "Has this machine's healthy operation been independently "
        "verified? Type YES to confirm: "
    ).strip()

    if confirmation != "YES":
        print("Cancelled. No baseline was created.")
    else:
        try:
            saved_path = create_baseline(
                machine_id=machine_id,
                sensor_configuration=sensor_configuration,
                healthy_operation_verified=True,
            )

            print(f"Baseline saved for review: {saved_path}")
            print("Status: pending_review")
            print("It has NOT been activated for monitoring.")

        except (
            OSError,
            ValueError,
            pd.errors.ParserError,
        ) as error:
            print(f"Baseline creation failed: {error}")
