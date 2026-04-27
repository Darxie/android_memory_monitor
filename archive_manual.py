"""
Backfill existing output directories into the dashboard under a given SDK version.

Useful when a previous batch ran without SDK detection (older code) or when
you want to manually re-tag historical results.

Examples:
    # See which use case each output directory belongs to
    python archive_manual.py --list

    # Archive five output dirs as one batch tagged SDK 28.4.13
    python archive_manual.py --sdk 28.4.13 output/20260424_163211 output/20260424_164336 ...

The script:
  1. Injects SDK: <version> into each app_info.txt (replacing any existing line)
  2. Reads the use case from each app_info.txt's "Use case:" line
  3. Runs the standard archive flow

Because archive_batch replaces any prior dashboard entry with the same SDK,
this is also the safe way to swap out an older entry (e.g. a dry run) for a
real run on the same SDK.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_tool.archive import archive_batch
from memory_tool.reporter import collect_run_artifacts

OUTPUT_ROOT = Path("output")
SDK_LINE_PATTERN = re.compile(r"^SDK:.*$", re.MULTILINE)


def parse_use_case(app_info_path: Path) -> str:
    for line in app_info_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Use case:"):
            return line.split(":", 1)[1].strip()
    raise ValueError(f"No 'Use case:' line in {app_info_path}")


def inject_sdk(app_info_path: Path, sdk: str) -> None:
    """Add or replace the SDK: line in app_info.txt."""
    text = app_info_path.read_text(encoding="utf-8")
    new_line = f"SDK: {sdk}"
    if SDK_LINE_PATTERN.search(text):
        text = SDK_LINE_PATTERN.sub(new_line, text, count=1)
    else:
        lines = text.splitlines(keepends=True)
        inserted = False
        for i, line in enumerate(lines):
            if line.startswith("PID:"):
                lines.insert(i + 1, new_line + "\n")
                inserted = True
                break
        if not inserted:
            lines.insert(0, new_line + "\n")
        text = "".join(lines)
    app_info_path.write_text(text, encoding="utf-8")


def list_output_dirs() -> None:
    """Print each output dir (single-run or batch subdir) with its use case."""
    if not OUTPUT_ROOT.is_dir():
        print(f"{OUTPUT_ROOT}/ does not exist")
        return

    rows = []
    for app_info in sorted(OUTPUT_ROOT.rglob("app_info.txt")):
        run_dir = app_info.parent
        rel = run_dir.relative_to(OUTPUT_ROOT)
        try:
            uc = parse_use_case(app_info)
        except ValueError:
            uc = "(no Use case: line)"
        rows.append((str(rel).replace("\\", "/"), uc))

    if not rows:
        print("(no runs found)")
        return

    width = max(len(name) for name, _ in rows)
    for name, uc in rows:
        print(f"{name:<{width}}  {uc}")


def _expand_paths(paths: list[str]) -> list[Path]:
    """Accept either a use-case dir or a batch dir; return list of use-case dirs."""
    expanded: list[Path] = []
    for d in paths:
        path = Path(d)
        if not path.is_dir():
            sys.exit(f"Not a directory: {d}")

        if (path / "app_info.txt").exists():
            expanded.append(path)
            continue

        # Treat as batch dir: look for subdirs containing app_info.txt
        subdirs = [c for c in sorted(path.iterdir()) if c.is_dir() and (c / "app_info.txt").exists()]
        if not subdirs:
            sys.exit(f"No app_info.txt in {path} or its subdirectories")
        expanded.extend(subdirs)

    return expanded


def archive(sdk: str, app: str, dirs: list[str]) -> None:
    use_case_dirs = _expand_paths(dirs)
    artifacts = []
    for path in use_case_dirs:
        app_info = path / "app_info.txt"
        inject_sdk(app_info, sdk)
        use_case = parse_use_case(app_info)
        artifacts.append(collect_run_artifacts(path, use_case))
        rel = path.relative_to(OUTPUT_ROOT) if path.is_relative_to(OUTPUT_ROOT) else path
        print(f"  prepared {use_case:<14} from {str(rel).replace(chr(92), '/')}")

    result = archive_batch(artifacts, app)
    if result:
        print(f"\nArchived as {result['batch_id']} ({len(artifacts)} use cases)")
        print(f"Manifest: {result['manifest']}")
    else:
        sys.exit("Archive failed - check logs above")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--list", action="store_true", help="List output/ directories with their use case")
    parser.add_argument("--sdk", help="SDK version to tag, e.g. 28.4.13")
    parser.add_argument("--app", default="sygic_profi", help="App internal name (default: sygic_profi)")
    parser.add_argument("dirs", nargs="*", help="Output directories to archive")
    args = parser.parse_args()

    if args.list:
        list_output_dirs()
        return

    if not args.sdk or not args.dirs:
        parser.error("Provide --sdk and at least one output directory (or use --list)")

    archive(args.sdk, args.app, args.dirs)


if __name__ == "__main__":
    main()
