"""
Archive completed batch runs into the dashboard data store.

Each batch is identified by its SDK version (parsed from app_info.txt).
A new run for the same SDK replaces the previous entry — only one run
per SDK is kept in the dashboard.
"""
import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

DASHBOARD_DIR = Path("dashboard")
DASHBOARD_DATA_DIR = DASHBOARD_DIR / "data"
DASHBOARD_RUNS_DIR = DASHBOARD_DATA_DIR / "runs"
MANIFEST_PATH = DASHBOARD_DATA_DIR / "manifest.json"

SDK_FIELD_PATTERN = re.compile(r"^SDK:\s*(\d+(?:\.\d+)+)\s*$", re.MULTILINE)


def _parse_sdk_from_app_info(app_info_path: Path) -> Optional[str]:
    """Read the SDK: line written by print_app_info. Returns None if absent."""
    if not app_info_path.exists():
        return None

    try:
        text = app_info_path.read_text(encoding="utf-8")
    except OSError as e:
        logging.warning("Could not read %s: %s", app_info_path, e)
        return None

    match = SDK_FIELD_PATTERN.search(text)
    return match.group(1) if match else None


def _resolve_batch_sdk(run_artifacts: list[dict]) -> Optional[str]:
    """Return the SDK version shared by the runs in this batch, or None."""
    for run in run_artifacts:
        app_info = run.get("app_info")
        if not app_info:
            continue
        sdk = _parse_sdk_from_app_info(Path(app_info))
        if sdk:
            return sdk
    return None


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"runs": []}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logging.warning("Manifest unreadable, starting fresh: %s", e)
        return {"runs": []}


def _write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def archive_batch(run_artifacts: list[dict], app_name_internal: str) -> Optional[dict]:
    """
    Copy successful use-case CSVs from a batch into the dashboard archive.

    Args:
        run_artifacts: The "runs" list returned by run_automation_batch.
        app_name_internal: The internal app key (e.g. "sygic_profi").

    Returns:
        Archive metadata dict, or None if the SDK could not be parsed.
    """
    sdk = _resolve_batch_sdk(run_artifacts)
    if not sdk:
        logging.warning("Could not parse SDK from any app_info.txt; skipping dashboard archive")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_id = f"{timestamp}_sdk{sdk}"
    dest_dir = DASHBOARD_RUNS_DIR / batch_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    use_case_files: dict[str, str] = {}
    for run in run_artifacts:
        use_case = run.get("use_case")
        csv_path = run.get("csv")
        if not use_case or not csv_path:
            continue
        csv_path = Path(csv_path)
        if not csv_path.exists():
            continue

        dest_csv = dest_dir / f"{use_case}.csv"
        shutil.copy(csv_path, dest_csv)
        # Use forward slashes so the path is valid in HTML fetch() calls on any OS.
        use_case_files[use_case] = f"data/runs/{batch_id}/{use_case}.csv"

    if not use_case_files:
        logging.warning("No CSVs to archive for SDK %s; cleaning up empty directory", sdk)
        try:
            dest_dir.rmdir()
        except OSError:
            pass
        return None

    manifest = _load_manifest()
    runs = [r for r in manifest.get("runs", []) if r.get("sdk") != sdk]

    # Remove on-disk artifacts of any previous runs for this SDK.
    for old_run in manifest.get("runs", []):
        if old_run.get("sdk") == sdk:
            old_dir = DASHBOARD_RUNS_DIR / old_run.get("id", "")
            if old_dir.exists() and old_dir != dest_dir:
                shutil.rmtree(old_dir, ignore_errors=True)

    runs.append({
        "id": batch_id,
        "sdk": sdk,
        "date": datetime.now().isoformat(timespec="seconds"),
        "app": app_name_internal,
        "use_cases": use_case_files,
    })
    manifest["runs"] = runs
    _write_manifest(manifest)

    logging.info("Archived batch for SDK %s as %s (%d use-cases)", sdk, batch_id, len(use_case_files))
    return {
        "batch_id": batch_id,
        "sdk": sdk,
        "manifest": MANIFEST_PATH,
        "use_cases": use_case_files,
    }
