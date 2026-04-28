# Android Memory Monitor

Python tool that automates Android UI scenarios and measures the resulting memory (PSS) and CPU usage of the app under test. Drives `uiautomator2`, samples `dumpsys meminfo` / `cpuinfo` on a configurable interval, detects crashes via logcat, and produces per-run plots plus an aggregated batch HTML report.

Targets two apps today: **Sygic Profi** and **EW Navi**.

## Requirements

- Python 3.10+
- ADB on `PATH`
- An Android device with USB debugging enabled
- `pip install -r requirements.txt` — installs `uiautomator2`, `matplotlib`, `seaborn`, `pandas`, `packaging`

## Quick start

1. Connect a device via USB, accept the debugging prompt
2. Verify ADB sees it: `adb devices`
3. Launch the GUI:
   ```
   python -m memory_tool.gui
   ```
4. Pick device, app, build version (release/debug), log interval
5. Click a use case button to run a single scenario, or **Run Batch** to run the full Sygic core sequence (`compute → search → fg_bg → zoom → demonstrate`)

## Multiple connected devices

The GUI device dropdown lists every device returned by `adb devices`. The selected device's serial is propagated through every ADB call (`AdbDevice` wrapper in `memory_tool/adb.py`) so you can run tests on one device while doing other Android work on another.

## Use cases (Sygic Profi)

| Use case             | What it does |
|----------------------|--------------|
| `compute`            | Searches for a destination, computes a route, presses back. Repeats. |
| `search`             | Two POI searches in different countries, taps results, returns to typing. Repeats. |
| `fg_bg`              | Switches the app to background (Calendar) and back. Stress-tests foreground/background lifecycle. |
| `zoom`               | Searches Mt. Everest, zooms out 20× then in 20×. Repeats. |
| `demonstrate`        | Computes a long route and runs Demonstrate route for a fixed duration (12h full / 5min dry-run). |
| `recompute_offroute` | Drives the Mock Locations app (`ru.gavrikov.mocklocations`) over a saved route that pulls the GPS feed off the planned path, forcing constant recomputes. 10-hour stress test. |

Use case descriptions visible in the dashboard live in `dashboard/data/use_cases.json` and can be edited without touching code.

## Output artifacts

Each run drops files into `output/<timestamp>/`:

- `memory_usage_<timestamp>.csv` — raw samples (timestamp, total_memory, java_heap, native_heap, code, stack, graphics, cpu_usage)
- `memory_stacked_line_chart_<timestamp>.png` — stacked memory components over time
- `memory_total_<timestamp>.png` — total PSS over time
- `cpu_usage_<timestamp>.png` — CPU usage over time
- `memory_analysis_<timestamp>.txt` — leak detection (linear regression slopes, classifications)
- `app_info.txt` — device / app / PID metadata
- `crash_log_<timestamp>.txt` — only if a crash was detected

A batch run additionally produces `output/batch_report_<app>_<timestamp>.html` aggregating every use case into one document.

## Dashboard — compare SDK versions

After every batch, `memory_tool/archive.py` copies the per-use-case CSVs into `dashboard/data/runs/<timestamp>_sdk<version>/` and updates `dashboard/data/manifest.json`. The SDK is parsed from `versionName` in `app_info.txt` (regex `SDK\s+(\d+(?:\.\d+)+)`); only one run per SDK is kept (a new run for the same SDK replaces the old one).

To preview locally:

```
python dashboard/serve.py
```

This serves `dashboard/` on `http://localhost:8000` (browsers block `fetch()` from `file://`, so `index.html` won't work when opened directly).

The dashboard renders one Plotly chart per use case, with one line per SDK version (semver-sorted, oldest → newest). Each use case has its own tab — click a tab at the top to switch between them; charts are pre-loaded in the background after the first one renders, so subsequent tab switches are instant.

By default only the **5 most recent SDKs** are shown as solid lines. Older versions stay in the legend faded out (`visible: 'legendonly'`); click a legend entry to toggle visibility.

The dashboard ships with historical data backfilled from earlier manual runs (SDKs 25.7.0, 25.9.9, 28.1.11, 28.2.0, 28.3.3) alongside the recent captures from the live tooling — sample counts are normalized to the most recent SDK so traces overlay cleanly.

## Publish to feldis.cz over FTP

Once the local dashboard looks right, upload it:

1. First time only: copy the credentials template and fill in your details:
   ```
   copy .ftp_credentials.example .ftp_credentials
   ```
   `.ftp_credentials` is gitignored. Edit it to set `user` and `password`.

2. Dry-run to preview what will be uploaded:
   ```
   python publish.py --dry-run
   ```

3. Real upload:
   ```
   python publish.py
   ```

The script connects via plain FTP (webhouse.sk doesn't support FTPS), navigates to `target_path` (creating subdirectories as needed) and uploads everything in `dashboard/` except `serve.py`.

## Project structure

```
memory_tool/
  gui.py             # Tkinter UI: device + app + use case selection
  runner.py          # Orchestration: device init, batch sequencing, finalization
  memory_monitor.py  # Background sampling thread (dumpsys meminfo / cpuinfo, /proc deltas)
  writer.py          # CSV + crash log writer
  plotter.py         # Per-run plots and trend analysis
  reporter.py        # Aggregated batch HTML report
  archive.py         # Copies batch results into dashboard/, updates manifest
  app_info.py        # Captures device + app metadata into app_info.txt
  adb.py             # AdbDevice wrapper; every command targets the selected serial
  utils.py           # _write_to_file helper
  timestamp.py       # Singleton run timestamp
  config.py          # APPLICATIONS dict (package names, use cases, start activity)
  use_cases/
    protocol.py      # validate(module) — fails import-time if run_test is missing
    sygic_profi/     # compute, search, fg_bg, zoom, demonstrate, ...
    ew_navi/         # compute, search

dashboard/
  index.html         # Plotly viewer
  assets/{app.js, style.css}
  data/manifest.json # archived runs (kept up to date by archive.py)
  data/use_cases.json
  serve.py           # local HTTP server for previewing the dashboard

publish.py           # FTP uploader for the dashboard
```

## Why PSS instead of RSS

When measuring app memory on Android, two metrics are commonly available — PSS (Proportional Set Size) and RSS (Resident Set Size).

**PSS** divides shared memory proportionally between processes that use it. If three apps share a 3 MB segment, each is charged 1 MB. This is the realistic memory cost of your app to the system, and it is what we sample via `dumpsys meminfo`.

**RSS** counts the entire shared segment against every process holding it open. The same 3 MB above would be counted as 3 MB for each of the three apps. RSS overstates per-app cost and can move for reasons unrelated to your code (other apps loading the same library).

For app-level optimization on Android — which is what this tool is for — PSS is the right metric.
