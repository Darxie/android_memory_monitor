# CLAUDE.md

Project context and conventions established across iterative refactoring.
Read this first when picking up the codebase.

## What the project does

Python tool that drives `uiautomator2` to run UI test scenarios against Android
nav apps (primarily Sygic Profi, also EW Navi). It samples PSS memory + CPU via
`dumpsys meminfo`/`cpuinfo` while the test runs and produces:

- Per-run plots (PNG) and trend analysis (TXT)
- A per-batch HTML report inside the batch folder
- An aggregated multi-SDK dashboard (`dashboard/`) hosted via FTP at
  `memory.feldis.cz`, used to compare memory behavior across SDK releases

Runs are launched from a Tkinter GUI (`memory_tool.gui`).

## Top-level layout

```
memory_tool/
  gui.py               # Tkinter UI; "Run Batch" + "Run Dry Batch" entry points
  runner.py            # run_automation_tasks / run_automation_batch
  memory_monitor.py    # background sampling thread (MemoryTool class)
  writer.py            # CSV writer + crash detection (Writer class)
  plotter.py           # per-run plots + trend analysis + per-run report.html
  reporter.py          # aggregated batch HTML report
  archive.py           # copies CSVs into dashboard/, updates manifest.json
  app_info.py          # device + app metadata; SDK extraction via About screen
  adb.py               # AdbDevice wrapper — every command targets a serial
  utils.py             # _write_to_file helper (the only thing left here)
  timestamp.py         # ExecutionTimestamp singleton
  config.py            # APPLICATIONS dict + use case lists
  use_cases/
    protocol.py        # validate(module) — fails import-time if run_test missing
    sygic_profi/       # compute, search, fg_bg, zoom, demonstrate, recompute_offroute, ...
    ew_navi/

dashboard/             # static viewer (committed to git for portability)
  index.html
  assets/{app.js, style.css}
  data/manifest.json   # archived runs (one per SDK, replace-on-same-SDK)
  data/use_cases.json  # use case descriptions + required maps
  data/runs/<id>/      # per-batch CSV archives
  serve.py             # local HTTP server for preview (http://localhost:8000)

publish.py             # FTP uploader for dashboard (webhouse, plain FTP)
archive_manual.py      # backfill old output/ runs into dashboard
cleanup_output.py      # manage output/ size (--list, --keep N, --older-than)
.ftp_credentials       # gitignored; copy from .ftp_credentials.example
.pylintrc              # disables noisy rules; max-line-length=120
.github/workflows/pylint.yml  # CI; Python 3.10+, --fail-under=9.0
.vscode/launch.json    # Run GUI / Publish (dry-run + real) / Serve dashboard
```

## Established patterns

### AdbDevice wrapper (`memory_tool/adb.py`)

Every ADB call goes through `AdbDevice(device_code)` so multi-device setups
work — you can run a test on one phone while doing other Android dev on a
second phone.

```python
adb = AdbDevice(device.serial)
adb.shell("am", "force-stop", pkg)
adb.run("wait-for-device")
adb.logcat_clear()
adb.logcat_dump()
```

Never use raw `["adb", "-s", ...]` lists or `adb.shell("logcat -c")` strings.
`get_app_pid(package, adb)` accepts the wrapper.

### Output folder structure

**Batch run** (output of `run_automation_batch`):
```
output/<timestamp>_batch/
  compute/
    memory_usage_<ts>.csv
    memory_*.png
    memory_analysis_<ts>.txt
    report_<ts>.html        # per-run HTML (kept by user request)
    app_info.txt
  search/
  fg_bg/
  zoom/
  demonstrate/
  batch_report.html         # aggregated batch report inside the folder
```

**Single use-case run**:
```
output/<timestamp>_<use_case>/
  ...
```

The batch folder is created in `run_automation_batch` and threaded through
`run_automation_tasks → Writer / print_app_info / generate_batch_report` via
the `output_dir` parameter. Plotter derives its paths from the CSV path passed
to it.

### Dry-run flag

`MemoryTool` has `dry_run: bool`. Each use case picks `ITERATIONS_DRY_RUN` vs
`ITERATIONS_FULL` based on it. `demonstrate.py` uses `DEMONSTRATION_SECONDS_DRY_RUN`
(300s) vs `DEMONSTRATION_SECONDS_FULL` (43200s = 12h). `recompute_offroute.py`
uses `DURATION_SECONDS_DRY_RUN` (300s) vs `DURATION_SECONDS_FULL` (36000s = 10h).
GUI has separate "Run Dry Batch" button that sets the flag.

### SDK extraction

`print_app_info()` accepts a `read_about` callback (provided by
`sygic_profi/shared.py:read_about_screen`) which navigates Menu → Settings →
Info → About → Product, dumps the UI hierarchy, and returns
`{"ui_hierarchy": "..."}`. The SDK version is extracted via regex
`SDK\s+(\d+(?:\.\d+)+)` and written as a clean `SDK: 28.4.13` line in
`app_info.txt`. The verbose hierarchy text is **not** persisted (user request).

`archive.py` reads the `SDK:` line via `SDK_FIELD_PATTERN` regex; runs without
a parsable SDK are skipped.

### Dashboard archive flow

After each batch, `runner.run_automation_batch` calls `archive_batch`:

1. Parses SDK from any use case's `app_info.txt`
2. Creates `dashboard/data/runs/<timestamp>_sdk<X.Y.Z>/<use_case>.csv` for each
   successful use case
3. Updates `dashboard/data/manifest.json` with **replace-on-same-SDK**
   semantics — older entry for the same SDK is removed from disk + manifest

Frontend (Plotly) loads `manifest.json` + `use_cases.json`, renders one chart
per use case with one line per SDK:
- Semver-sorted SDK list
- Vertical legend on right with title "SDK"
- Y-axis unit auto-picked: MB by default, GB when max > 1024 MB

### Use case protocol

Every use case module exposes `def run_test(device, memory_tool): ...`. Runner
calls `validate(module)` after `importlib.import_module`; missing `run_test`
raises `ImportError` immediately, not at execution time.

Module-level "NECESSARY MAPS" strings in use case files are documentation. The
canonical per-use-case maps live in `dashboard/data/use_cases.json` (which the
dashboard reads to render the "Required Maps" overview at the top).

### ExecutionTimestamp

Singleton in `timestamp.py`. `reset()` is called per use case in
`run_automation_batch`. Most code now takes `output_dir` explicitly rather than
deriving from `ExecutionTimestamp` — the timestamp is only used for filenames
within a directory, not for the directory itself. Don't add module-level code
that derives paths from `ExecutionTimestamp` — see "Anti-patterns" below.

## Decisions and reasons

- **`dashboard/data/` committed to git.** Backup + portability outweighs minor
  repo growth (KB to a few MB per batch). Webhouse is just publication, not
  source of truth.
- **Replace-on-same-SDK.** Only one run per SDK in the dashboard. Git history
  preserves prior runs if needed (`git log dashboard/data/manifest.json`).
- **Time-based `demonstrate`.** Originally had arrival watchers + threading.Timer
  hybrid, but uiautomator2 watcher background threads were keeping Python alive
  for hours after `run_test` returned. Simplified to fixed
  `time.sleep(DURATION_SECONDS_FULL)` for predictable duration and clean exit.
- **Per-run `report_*.html` kept.** User explicitly wants it despite some
  overlap with `batch_report.html` and the dashboard.
- **Pylint config.** Noisy rules disabled: `logging-fstring-interpolation`,
  `broad-exception-caught`, `missing-*-docstring`, `too-many-*`,
  `duplicate-code`, `global-statement`, `import-error`, `wrong-import-position`,
  etc. `max-line-length=120`. CI uses `--fail-under=9.0` and installs
  `requirements.txt`. Python 3.10+ only.
- **Pylint workflow uses Python 3.10/3.11/3.12.** Older Pythons fail on modern
  type hints (`Path | None`, `dict[str, str]`).

## Recent additions worth remembering

- **`recompute_offroute.py`** — drives Mock Locations app
  (`ru.gavrikov.mocklocations`) via uiautomator2 to feed off-route GPS while
  Sygic navigates a long route. Constant recompute stress test, 10h. Selectors
  in `SAVED_ROUTES_BUTTON_CANDIDATES` / `RUN_BUTTON_CANDIDATES` /
  `STOP_BUTTON_CANDIDATES` may need adjustment per Mock Locations version;
  `_dump_hierarchy()` saves UI XML to `output/_debug_*.xml` on miss.
- **Force-stop before launch** when driving another app's UI (Mock Locations
  is force-stopped first to ensure clean state).
- **`cleanup_output.py`** detects batch dirs and labels them
  `batch (N use cases)`. Deletes the entire batch folder atomically.
- **`archive_manual.py`** accepts both batch dirs (auto-expands to subdirs) and
  individual use-case dirs. Replaces existing dashboard entry for the same SDK.

## Anti-patterns to avoid

- **Module-level disk side-effects.** `mkdir()` at module load creates phantom
  folders before any use case runs (this happened in `plotter.py` line 23 —
  removed). Path objects are fine; just don't materialize them.
- **`ExecutionTimestamp` captured at module import time and used as a path.**
  Leads to stale paths if the module imports before the run starts. Always
  pass `output_dir` explicitly through the call chain.
- **Raw `["adb", "shell", ...]` lists.** Use `AdbDevice.shell(*args)`. Same for
  `device.shell("logcat -c")` strings — use `adb.logcat_clear()`.
- **Catching arrival via uiautomator2 watchers in long-running daemon
  threads.** The uiautomator2 watcher background thread is **not** a daemon and
  prevents process exit. If you must use watchers, `device.watcher.stop()` +
  `device.watcher.reset()` in cleanup.
- **Mixing data and code in git.** Original instinct was to gitignore
  `dashboard/data/` — reverted because losing data on a fresh clone is worse
  than the size cost.

## Common workflows

**Run a batch:**
```
python -m memory_tool.gui     # → Run Batch / Run Dry Batch button
```

**Preview dashboard before publishing:**
```
python dashboard/serve.py     # → http://localhost:8000
```

**Publish to feldis.cz:**
```
python publish.py --dry-run   # preview file list
python publish.py             # real upload (FTP, plain)
```

**Backfill an old run that lacked SDK info:**
```
python archive_manual.py --list                                    # see what's there
python archive_manual.py --sdk 28.4.13 output/<batch_or_use_case>  # archive it
```

**Clean up output/:**
```
python cleanup_output.py --list
python cleanup_output.py --keep 10 --dry-run
python cleanup_output.py --keep 10
```

**Commit dashboard data after a batch:**
```
git add dashboard/data/
git commit -m "archive run for SDK X.Y.Z"
git push
```
