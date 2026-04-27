"""
Tidy up the output/ directory.

Usage:
    python cleanup_output.py --list                # show every output dir
    python cleanup_output.py --keep 10             # keep 10 newest, delete rest
    python cleanup_output.py --older-than 7        # delete dirs older than 7 days
    python cleanup_output.py --all                 # delete everything in output/

Add --dry-run to any delete command to preview without touching disk.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

OUTPUT_ROOT = Path("output")


def _parse_use_case(app_info_path: Path) -> str:
    if not app_info_path.exists():
        return "?"
    try:
        for line in app_info_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Use case:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "?"


def _label(directory: Path) -> str:
    """Single use-case dir → use case name. Batch dir → 'batch (N use cases)'."""
    if (directory / "app_info.txt").exists():
        return _parse_use_case(directory / "app_info.txt")
    sub_count = sum(
        1 for c in directory.iterdir()
        if c.is_dir() and (c / "app_info.txt").exists()
    )
    if sub_count:
        return f"batch ({sub_count} use cases)"
    return "?"


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def _human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def _human_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h"
    return f"{int(seconds / 86400)}d"


def _collect_dirs() -> list[Path]:
    if not OUTPUT_ROOT.is_dir():
        return []
    return sorted(
        (p for p in OUTPUT_ROOT.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _print_table(dirs: list[Path], header: str = "") -> None:
    if header:
        print(header)
    if not dirs:
        print("  (no directories)")
        return

    now = time.time()
    rows = []
    for d in dirs:
        try:
            mtime = d.stat().st_mtime
        except OSError:
            mtime = 0
        rows.append((
            d.name,
            _label(d),
            _human_size(_dir_size_bytes(d)),
            _human_age(now - mtime) if mtime else "?",
        ))

    name_w = max(len(r[0]) for r in rows)
    uc_w = max(len(r[1]) for r in rows)
    sz_w = max(len(r[2]) for r in rows)
    for name, uc, sz, age in rows:
        print(f"  {name:<{name_w}}  {uc:<{uc_w}}  {sz:>{sz_w}}  {age}")


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


def _delete_dirs(dirs: list[Path], dry_run: bool) -> None:
    if not dirs:
        print("Nothing to delete.")
        return

    _print_table(dirs, header=f"Will delete {len(dirs)} directories:")

    if dry_run:
        print("\n(--dry-run, nothing actually deleted)")
        return

    print()
    if not _confirm("Proceed?"):
        print("Aborted.")
        return

    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
        print(f"  deleted {d}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List output directories")
    mode.add_argument("--keep", type=int, metavar="N", help="Keep N newest, delete the rest")
    mode.add_argument("--older-than", type=int, metavar="DAYS", help="Delete directories older than DAYS")
    mode.add_argument("--all", action="store_true", help="Delete every directory in output/")
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    args = parser.parse_args()

    dirs = _collect_dirs()

    if args.list:
        _print_table(dirs)
        return

    if args.keep is not None:
        if args.keep < 0:
            sys.exit("--keep must be >= 0")
        _delete_dirs(dirs[args.keep:], args.dry_run)
        return

    if args.older_than is not None:
        cutoff = time.time() - args.older_than * 86400
        to_delete = [d for d in dirs if d.stat().st_mtime < cutoff]
        _delete_dirs(to_delete, args.dry_run)
        return

    if args.all:
        _delete_dirs(dirs, args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
