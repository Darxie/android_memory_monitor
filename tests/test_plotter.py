"""Tests for plotter.py — pure helpers + analyze_trends end-to-end on synthetic CSVs."""
import csv
from pathlib import Path

import pytest

from memory_tool import plotter


# ------- _safe_float --------------------------------------------------------

def test_safe_float_parses_valid_strings():
    assert plotter._safe_float("3.14") == 3.14
    assert plotter._safe_float("0") == 0.0
    assert plotter._safe_float("-1.5") == -1.5


def test_safe_float_passes_through_numbers():
    assert plotter._safe_float(42) == 42.0
    assert plotter._safe_float(2.71) == 2.71


def test_safe_float_returns_default_on_invalid():
    assert plotter._safe_float("abc") == 0.0
    assert plotter._safe_float("") == 0.0
    assert plotter._safe_float(None) == 0.0


def test_safe_float_uses_custom_default():
    assert plotter._safe_float("nope", default=99.0) == 99.0


# ------- _validate_rows -----------------------------------------------------

def _full_row(value=1.0):
    return {col: value for col in plotter.REQUIRED_COLUMNS}


def test_validate_rows_rejects_empty():
    ok, err = plotter._validate_rows([])
    assert not ok
    assert "empty" in err.lower()


def test_validate_rows_rejects_single_row():
    ok, err = plotter._validate_rows([_full_row()])
    assert not ok
    assert "insufficient" in err.lower()


def test_validate_rows_rejects_missing_required_columns():
    rows = [{"timestamp": 1.0, "total_memory": 100.0}, {"timestamp": 2.0, "total_memory": 200.0}]
    ok, err = plotter._validate_rows(rows)
    assert not ok
    assert "missing" in err.lower()


def test_validate_rows_accepts_complete():
    rows = [_full_row(), _full_row()]
    ok, err = plotter._validate_rows(rows)
    assert ok
    assert err is None


# ------- _determine_memory_unit ---------------------------------------------

def test_determine_memory_unit_picks_mb_below_1gb():
    rows = [{m: 100_000.0 for m in plotter.REQUIRED_COLUMNS[1:]} for _ in range(2)]
    rows[0]["timestamp"] = rows[1]["timestamp"] = 0.0
    unit, divisor = plotter._determine_memory_unit(rows)
    assert unit == "MB"
    assert divisor == 1024.0


def test_determine_memory_unit_picks_gb_above_1gb():
    big = {m: 2_000_000.0 for m in plotter.REQUIRED_COLUMNS[1:]}  # ~1.9 GB
    big["timestamp"] = 0.0
    unit, divisor = plotter._determine_memory_unit([big, dict(big)])
    assert unit == "GB"
    assert divisor == 1024.0 * 1024.0


# ------- _load_csv_rows -----------------------------------------------------

def _write_csv(path: Path, rows):
    fields = list(plotter.REQUIRED_COLUMNS) + ["cpu_usage"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for row in rows:
            w.writerow([row.get(k, 0) for k in fields])


def test_load_csv_rows_parses_valid_floats(tmp_path):
    csv_path = tmp_path / "mem.csv"
    _write_csv(csv_path, [
        {"timestamp": 1000, "total_memory": 50000, "cpu_usage": 25.5},
        {"timestamp": 1010, "total_memory": 55000, "cpu_usage": 30.0},
    ])
    rows = plotter._load_csv_rows(str(csv_path))
    assert len(rows) == 2
    assert rows[0]["timestamp"] == 1000.0
    assert rows[1]["cpu_usage"] == 30.0


def test_load_csv_rows_falls_back_on_invalid(tmp_path):
    csv_path = tmp_path / "mem.csv"
    csv_path.write_text(
        "timestamp,total_memory,java_heap,native_heap,code,stack,graphics,cpu_usage\n"
        "1000,abc,10000,20000,5000,1000,14000,bad\n",
        encoding="utf-8",
    )
    rows = plotter._load_csv_rows(str(csv_path))
    # Invalid values silently fall back to 0.0; the row is preserved.
    assert rows[0]["total_memory"] == 0.0
    assert rows[0]["cpu_usage"] == 0.0
    assert rows[0]["timestamp"] == 1000.0


# ------- analyze_trends -----------------------------------------------------

def test_analyze_trends_writes_report_for_stable_memory(tmp_path):
    csv_path = tmp_path / "memory_usage_stable.csv"
    _write_csv(csv_path, [
        {
            "timestamp": 1000 + i * 5,
            "total_memory": 100_000,
            "java_heap": 30_000,
            "native_heap": 40_000,
            "code": 20_000,
            "stack": 1_000,
            "graphics": 9_000,
            "cpu_usage": 20.0,
        }
        for i in range(60)
    ])

    assert plotter.analyze_trends(str(csv_path)) is True

    analysis_files = list(tmp_path.glob("memory_analysis_*.txt"))
    assert len(analysis_files) == 1
    text = analysis_files[0].read_text(encoding="utf-8")
    # Stable values -> low slope -> "Stable" classification + PASS verdict.
    assert "Stable" in text
    assert "PASS" in text


def test_analyze_trends_detects_critical_leak(tmp_path):
    csv_path = tmp_path / "memory_usage_leak.csv"
    # 60 samples 5s apart = 295s = ~5min. 1 MB/min slope = 5 MB rise = 5*1024 KB.
    base_kb = 50_000
    rows = []
    for i in range(60):
        # +1.2 MB/min on total_memory => 1.2*1024 KB / 60s = 20.48 KB/s
        rise = i * 5 * 20.48
        rows.append({
            "timestamp": 1000 + i * 5,
            "total_memory": base_kb + rise,
            "java_heap": 10_000,
            "native_heap": 15_000,
            "code": 8_000,
            "stack": 500,
            "graphics": 6_500,
            "cpu_usage": 30.0,
        })
    _write_csv(csv_path, rows)

    assert plotter.analyze_trends(str(csv_path)) is True
    text = next(tmp_path.glob("memory_analysis_*.txt")).read_text(encoding="utf-8")
    assert "CRITICAL LEAK" in text
    assert "POTENTIAL LEAKS DETECTED" in text


def test_analyze_trends_returns_false_for_too_few_samples(tmp_path):
    csv_path = tmp_path / "memory_usage_short.csv"
    _write_csv(csv_path, [{"timestamp": i, "total_memory": 1000} for i in range(3)])
    assert plotter.analyze_trends(str(csv_path)) is False


def test_analyze_trends_returns_false_for_missing_file(tmp_path):
    assert plotter.analyze_trends(str(tmp_path / "missing.csv")) is False
