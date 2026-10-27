
from datetime import datetime, timezone
from pathlib import Path
import json
import re

from src.baseline_learning import (
    BASELINE_ROOT,
    FEATURE_COLUMNS,
    MINIMUM_WINDOWS,
    validate_machine_id,
)


def _machine_dir(machine_id: str) -> Path:
    machine_id = validate_machine_id(machine_id)
    return BASELINE_ROOT / machine_id


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json_atomically(path: Path, data: dict) -> None:
    """Write a JSON file through a temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.flush()

    temporary_path.replace(path)


def _baseline_path(machine_id: str, version: int) -> Path:
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("Baseline version must be a positive integer.")

    return _machine_dir(machine_id) / f"baseline_v{version:03d}.json"


def review_baseline(machine_id: str, version: int) -> dict:
    """Check baseline structure and return a review summary."""
    path = _baseline_path(machine_id, version)

    if not path.exists():
        raise FileNotFoundError(f"Baseline not found: {path}")

    baseline = _load_json(path)

    if baseline.get("machine_id") != validate_machine_id(machine_id):
        raise ValueError("Machine ID does not match the baseline.")

    if baseline.get("baseline_version") != version:
        raise ValueError("Baseline version metadata does not match its filename.")

    if baseline.get("schema_version") != 1:
        raise ValueError("Unsupported baseline schema version.")

    if baseline.get("status") != "pending_review":
        raise ValueError(
            "Only a baseline with status 'pending_review' can be reviewed "
            "for first-time activation."
        )

    if baseline.get("healthy_operation_verified") is not True:
        raise ValueError("Healthy-operation verification is missing.")

    if baseline.get("window_size_readings") != 100:
        raise ValueError("Unexpected window size.")

    if baseline.get("complete_windows", 0) < MINIMUM_WINDOWS:
        raise ValueError("The baseline does not contain enough windows.")

    if baseline.get("readings_used", 0) < (
        MINIMUM_WINDOWS * baseline["window_size_readings"]
    ):
        raise ValueError("Insufficient readings recorded in baseline metadata.")

    if baseline.get("feature_names") != FEATURE_COLUMNS:
        raise ValueError("Feature schema does not match this application.")

    summary = baseline.get("feature_summary")

    if not isinstance(summary, dict):
        raise ValueError("Feature summary is missing.")

    for feature in FEATURE_COLUMNS:
        stats = summary.get(feature)

        if not isinstance(stats, dict):
            raise ValueError(f"Missing statistics for feature: {feature}")

        for key in ("mean", "std", "median", "p05", "p95"):
            value = stats.get(key)

            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"Invalid {key} for feature: {feature}")

            if not __import__("math").isfinite(value):
                raise ValueError(f"Non-finite {key} for feature: {feature}")

        if stats["std"] < 0 or stats["p05"] > stats["p95"]:
            raise ValueError(f"Inconsistent statistics for feature: {feature}")

    return {
        "machine_id": machine_id,
        "version": version,
        "status": baseline["status"],
        "created_at_utc": baseline.get("created_at_utc"),
        "sensor_configuration": baseline.get("sensor_configuration"),
        "complete_windows": baseline["complete_windows"],
        "readings_used": baseline["readings_used"],
        "feature_count": len(FEATURE_COLUMNS),
        "review_required": True,
        "note": (
            "Structural checks passed. This does not prove that the "
            "machine was healthy or that the baseline is representative."
        ),
    }



def activate_baseline(
    machine_id: str,
    version: int,
    approved_by: str,
    approval_note: str,
    confirmed_healthy: bool,
) -> Path:
    """Approve and activate a reviewed baseline for one machine."""

    approved_by = approved_by.strip()
    approval_note = approval_note.strip()

    if not approved_by:
        raise ValueError("Record who approved this baseline.")

    if not approval_note:
        raise ValueError("Provide an approval note.")

    if confirmed_healthy is not True:
        raise ValueError(
            "Explicit confirmation of healthy operation is required."
        )

    # Revalidate the baseline immediately before activation.
    review_baseline(machine_id, version)

    machine_dir = _machine_dir(machine_id)
    registry_path = machine_dir / "registry.json"

    if registry_path.exists():
        registry = _load_json(registry_path)
    else:
        registry = {
            "machine_id": machine_id,
            "active_version": None,
            "history": [],
        }

    if registry.get("machine_id") != machine_id:
        raise ValueError("Registry machine ID does not match.")

    history = registry.get("history", [])
    if not isinstance(history, list):
        raise ValueError("Registry history is invalid.")

    previous_version = registry.get("active_version")

    # Do not create duplicate activation records for the same active version.
    if previous_version == version:
        raise ValueError(
            f"Baseline v{version:03d} is already active for {machine_id}."
        )

    now = datetime.now(timezone.utc).isoformat()

    # Record the previous activation as superseded in registry history.
    if previous_version is not None:
        for record in reversed(history):
            if (
                record.get("version") == previous_version
                and record.get("status") == "active"
            ):
                record["status"] = "superseded"
                record["superseded_at_utc"] = now
                break

    activation_record = {
        "version": version,
        "status": "active",
        "activated_at_utc": now,
        "approved_by": approved_by,
        "approval_note": approval_note,
        "previous_version": previous_version,
    }

    history.append(activation_record)

    registry["machine_id"] = machine_id
    registry["active_version"] = version
    registry["history"] = history
    registry["updated_at_utc"] = now

    _write_json_atomically(registry_path, registry)

    return registry_path




def get_active_baseline(machine_id: str) -> dict:
    """Return the active baseline with its registry approval record."""

    machine_id = validate_machine_id(machine_id)
    machine_dir = _machine_dir(machine_id)
    registry_path = machine_dir / "registry.json"

    if not registry_path.exists():
        raise FileNotFoundError(
            f"No baseline registry exists for machine {machine_id}."
        )

    registry = _load_json(registry_path)

    if registry.get("machine_id") != machine_id:
        raise ValueError("Registry machine ID does not match.")

    version = registry.get("active_version")

    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f"No valid active baseline for {machine_id}.")

    activation_record = next(
        (
            record
            for record in reversed(registry.get("history", []))
            if record.get("version") == version
            and record.get("status") == "active"
        ),
        None,
    )

    if activation_record is None:
        raise ValueError(
            "Registry does not contain a matching active approval record."
        )

    baseline_path = _baseline_path(machine_id, version)

    if not baseline_path.exists():
        raise FileNotFoundError(
            f"Active baseline file is missing: {baseline_path}"
        )

    baseline = _load_json(baseline_path)

    if baseline.get("machine_id") != machine_id:
        raise ValueError("Active baseline machine ID does not match.")

    if baseline.get("baseline_version") != version:
        raise ValueError("Active baseline version does not match the registry.")

    # Return a copy with activation status supplied by the registry.
    active_baseline = dict(baseline)
    active_baseline["status"] = "active"
    active_baseline["activation_record"] = activation_record

    return active_baseline



def list_baselines(machine_id: str) -> list[dict]:
    """List saved baseline versions without changing their status."""
    machine_dir = _machine_dir(machine_id)

    if not machine_dir.exists():
        return []

    results = []

    for path in sorted(machine_dir.glob("baseline_v*.json")):
        match = re.fullmatch(r"baseline_v(\d+)\.json", path.name)

        if not match:
            continue

        baseline = _load_json(path)

        results.append({
            "version": int(match.group(1)),
            "machine_id": baseline.get("machine_id"),
            "created_at_utc": baseline.get("created_at_utc"),
            "status": baseline.get("status"),
            "complete_windows": baseline.get("complete_windows"),
            "readings_used": baseline.get("readings_used"),
        })

    return results
