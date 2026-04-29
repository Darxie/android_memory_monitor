"""Tests for archive.py — manifest mutation, replace-on-same-SDK, variant nesting."""
import json
from pathlib import Path

import pytest

from memory_tool import archive


# ------- Helpers ------------------------------------------------------------

def write_app_info(path: Path, sdk):
    """Build a minimal app_info.txt that archive's regex can parse."""
    lines = ["Use case: x\n", "Device: serial\n", "PID: 1234\n"]
    if sdk:
        lines.append(f"SDK: {sdk}\n")
    else:
        lines.append("SDK: unknown\n")
    path.write_text("".join(lines), encoding="utf-8")


def make_artifact(src_dir: Path, use_case: str, sdk, location=None):
    """Create a fake run dir with a CSV + app_info.txt and return the artifact dict."""
    suffix = f"_{location}" if location else ""
    sub = src_dir / f"{use_case}{suffix}"
    sub.mkdir(parents=True, exist_ok=True)
    csv = sub / "memory_usage_x.csv"
    csv.write_text("timestamp,total_memory\n100,1000\n", encoding="utf-8")
    info = sub / "app_info.txt"
    write_app_info(info, sdk)
    artifact = {"use_case": use_case, "csv": str(csv), "app_info": str(info)}
    if location:
        artifact["location"] = location
    return artifact


@pytest.fixture
def dashboard_root(tmp_path, monkeypatch):
    """Redirect archive's dashboard paths to a temp dir for each test."""
    runs_dir = tmp_path / "runs"
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(archive, "DASHBOARD_RUNS_DIR", runs_dir)
    monkeypatch.setattr(archive, "MANIFEST_PATH", manifest)
    return tmp_path


# ------- _parse_sdk_from_app_info -------------------------------------------

def test_parse_sdk_basic(tmp_path):
    info = tmp_path / "app_info.txt"
    write_app_info(info, "28.4.13")
    assert archive._parse_sdk_from_app_info(info) == "28.4.13"


def test_parse_sdk_returns_none_when_unknown(tmp_path):
    info = tmp_path / "app_info.txt"
    write_app_info(info, None)
    assert archive._parse_sdk_from_app_info(info) is None


def test_parse_sdk_returns_none_when_file_missing(tmp_path):
    assert archive._parse_sdk_from_app_info(tmp_path / "missing.txt") is None


def test_parse_sdk_handles_extra_whitespace(tmp_path):
    info = tmp_path / "app_info.txt"
    info.write_text("Use case: x\nSDK:    25.7.0   \nDevice: y\n", encoding="utf-8")
    assert archive._parse_sdk_from_app_info(info) == "25.7.0"


def test_parse_sdk_only_matches_dedicated_line(tmp_path):
    """The regex requires SDK: at start of line. 'X SDK: 1.0' should not match."""
    info = tmp_path / "app_info.txt"
    info.write_text("note: legacy SDK: 1.0 will be removed\n", encoding="utf-8")
    assert archive._parse_sdk_from_app_info(info) is None


# ------- _resolve_batch_sdk -------------------------------------------------

def test_resolve_batch_sdk_returns_first_present(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    write_app_info(a, "25.7.0")
    write_app_info(b, "28.1.11")
    runs = [{"app_info": str(a)}, {"app_info": str(b)}]
    assert archive._resolve_batch_sdk(runs) == "25.7.0"


def test_resolve_batch_sdk_skips_runs_without_sdk(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    write_app_info(a, None)
    write_app_info(b, "28.1.11")
    runs = [{"app_info": str(a)}, {"app_info": str(b)}]
    assert archive._resolve_batch_sdk(runs) == "28.1.11"


def test_resolve_batch_sdk_returns_none_if_all_missing(tmp_path):
    a = tmp_path / "a.txt"
    write_app_info(a, None)
    runs = [{"app_info": str(a)}, {}, {"app_info": str(tmp_path / "missing.txt")}]
    assert archive._resolve_batch_sdk(runs) is None


def test_resolve_batch_sdk_handles_runs_without_app_info_field():
    runs = [{"use_case": "compute"}, {"use_case": "search"}]
    assert archive._resolve_batch_sdk(runs) is None


# ------- archive_batch (integration) ----------------------------------------

def test_archive_batch_writes_flat_use_cases(dashboard_root):
    src = dashboard_root / "src"
    artifacts = [make_artifact(src, "compute", "28.4.13")]

    result = archive.archive_batch(artifacts, "sygic_profi")

    assert result is not None
    assert result["sdk"] == "28.4.13"
    manifest = json.loads(archive.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert len(manifest["runs"]) == 1
    entry = manifest["runs"][0]
    assert entry["sdk"] == "28.4.13"
    # Flat use case = string path
    assert isinstance(entry["use_cases"]["compute"], str)
    assert entry["use_cases"]["compute"].endswith("compute.csv")


def test_archive_batch_writes_nested_variant_use_cases(dashboard_root):
    src = dashboard_root / "src"
    artifacts = [
        make_artifact(src, "compute", "28.4.13"),
        make_artifact(src, "zoom", "28.4.13", location="nepal"),
        make_artifact(src, "zoom", "28.4.13", location="paris"),
    ]

    result = archive.archive_batch(artifacts, "sygic_profi")

    manifest = json.loads(archive.MANIFEST_PATH.read_text(encoding="utf-8"))
    use_cases = manifest["runs"][0]["use_cases"]
    assert isinstance(use_cases["zoom"], dict), "variant-aware entries should be nested"
    assert set(use_cases["zoom"].keys()) == {"nepal", "paris"}
    assert use_cases["zoom"]["nepal"].endswith("zoom_nepal.csv")
    assert use_cases["zoom"]["paris"].endswith("zoom_paris.csv")
    # Flat compute is still a plain string.
    assert isinstance(use_cases["compute"], str)

    # CSVs were copied with variant-suffixed names.
    batch_dir = archive.DASHBOARD_RUNS_DIR / result["batch_id"]
    files = sorted(p.name for p in batch_dir.iterdir())
    assert files == ["compute.csv", "zoom_nepal.csv", "zoom_paris.csv"]


def test_archive_batch_replace_on_same_sdk(dashboard_root):
    import time
    src = dashboard_root / "src"

    artifacts1 = [make_artifact(src / "first", "compute", "28.4.13")]
    result1 = archive.archive_batch(artifacts1, "sygic_profi")
    first_dir = archive.DASHBOARD_RUNS_DIR / result1["batch_id"]
    assert first_dir.exists()

    # Sleep to force a different second-resolution timestamp; otherwise both
    # calls produce the same batch_id (and dest_dir == old_dir, no removal).
    time.sleep(1.1)

    artifacts2 = [make_artifact(src / "second", "compute", "28.4.13")]
    result2 = archive.archive_batch(artifacts2, "sygic_profi")

    assert result1["batch_id"] != result2["batch_id"]
    # Old run dir should have been removed.
    assert not first_dir.exists()
    # Manifest only contains the new run for that SDK.
    manifest = json.loads(archive.MANIFEST_PATH.read_text(encoding="utf-8"))
    sdk_runs = [r for r in manifest["runs"] if r["sdk"] == "28.4.13"]
    assert len(sdk_runs) == 1
    assert sdk_runs[0]["id"] == result2["batch_id"]


def test_archive_batch_keeps_runs_for_different_sdks(dashboard_root):
    src = dashboard_root / "src"
    archive.archive_batch([make_artifact(src / "a", "compute", "25.7.0")], "sygic_profi")
    archive.archive_batch([make_artifact(src / "b", "compute", "28.4.13")], "sygic_profi")

    manifest = json.loads(archive.MANIFEST_PATH.read_text(encoding="utf-8"))
    sdks = sorted(r["sdk"] for r in manifest["runs"])
    assert sdks == ["25.7.0", "28.4.13"]


def test_archive_batch_returns_none_when_no_sdk(dashboard_root):
    src = dashboard_root / "src"
    artifacts = [make_artifact(src, "compute", None)]
    assert archive.archive_batch(artifacts, "sygic_profi") is None
    # Manifest should not be created if nothing was archived.
    assert not archive.MANIFEST_PATH.exists()


def test_archive_batch_skips_artifacts_with_missing_csv(dashboard_root):
    src = dashboard_root / "src"
    art = make_artifact(src, "compute", "28.4.13")
    Path(art["csv"]).unlink()  # delete CSV before archiving
    assert archive.archive_batch([art], "sygic_profi") is None
