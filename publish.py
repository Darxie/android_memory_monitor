"""
Publish dashboard/ to feldis.cz over FTP.

Usage:
    python publish.py            # uploads everything
    python publish.py --dry-run  # lists what would be uploaded
"""
import argparse
import ftplib
import json
import sys
from collections import defaultdict
from pathlib import Path

CREDENTIALS_FILE = Path(".ftp_credentials")
DASHBOARD_DIR = Path("dashboard")
EXCLUDE_PARTS = {"serve.py", "__pycache__", ".DS_Store"}


def load_credentials() -> dict:
    if not CREDENTIALS_FILE.exists():
        sys.exit(
            f"Missing {CREDENTIALS_FILE}. Copy .ftp_credentials.example to "
            f"{CREDENTIALS_FILE} and fill in your details."
        )

    text = CREDENTIALS_FILE.read_text(encoding="utf-8").strip()
    if not text:
        sys.exit(
            f"{CREDENTIALS_FILE} is empty. Paste the contents of "
            f".ftp_credentials.example into it and fill in user/password."
        )

    try:
        creds = json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(
            f"{CREDENTIALS_FILE} is not valid JSON ({e}). "
            f"Use .ftp_credentials.example as a template."
        )

    required = {"host", "user", "password", "target_path"}
    missing = required - creds.keys()
    if missing:
        sys.exit(f"{CREDENTIALS_FILE} is missing keys: {', '.join(sorted(missing))}")

    return creds


def _should_include(rel_path: Path) -> bool:
    return not any(part in EXCLUDE_PARTS for part in rel_path.parts)


def _collect_files_by_dir(root: Path) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if not _should_include(rel):
            continue
        rel_dir = rel.parent.as_posix() if rel.parent != Path(".") else ""
        grouped[rel_dir].append(path)
    return grouped


def _navigate_to_target(ftp: ftplib.FTP, target_path: str) -> str:
    """CWD into target_path and return the absolute pwd. Tries one-shot first, then step-by-step."""
    try:
        ftp.cwd(target_path)
        return ftp.pwd()
    except ftplib.error_perm:
        pass

    parts = [p for p in target_path.replace("\\", "/").split("/") if p]
    if parts and parts[0].endswith(":"):
        ftp.cwd(parts[0] + "/")
        rest = parts[1:]
    elif target_path.startswith("/"):
        ftp.cwd("/")
        rest = parts
    else:
        rest = parts

    for part in rest:
        ftp.cwd(part)
    return ftp.pwd()


def _navigate_into_subdir(ftp: ftplib.FTP, target_pwd: str, rel_dir: str) -> None:
    """Reset to target_pwd, then descend into rel_dir, creating missing parts."""
    ftp.cwd(target_pwd)
    if not rel_dir:
        return
    for part in rel_dir.split("/"):
        if not part:
            continue
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def publish(creds: dict, dry_run: bool = False) -> None:
    if not DASHBOARD_DIR.exists():
        sys.exit(f"{DASHBOARD_DIR} not found. Run a batch first to populate it.")

    grouped = _collect_files_by_dir(DASHBOARD_DIR)
    total = sum(len(files) for files in grouped.values())
    print(f"{total} files to upload from {DASHBOARD_DIR}/")

    if dry_run:
        for rel_dir in sorted(grouped):
            print(f"  {rel_dir or '(root)'}/")
            for f in grouped[rel_dir]:
                print(f"    {f.name}  ({f.stat().st_size} B)")
        return

    ftp = ftplib.FTP(creds["host"], timeout=30)
    try:
        ftp.login(creds["user"], creds["password"])
        print(f"Connected to {creds['host']} as {creds['user']}")

        target_pwd = _navigate_to_target(ftp, creds["target_path"])
        print(f"Target: {target_pwd}")

        uploaded = 0
        for rel_dir in sorted(grouped):
            _navigate_into_subdir(ftp, target_pwd, rel_dir)
            current = ftp.pwd()
            for local_path in grouped[rel_dir]:
                with local_path.open("rb") as f:
                    ftp.storbinary(f"STOR {local_path.name}", f)
                uploaded += 1
                print(f"  [{uploaded}/{total}] {current.rstrip('/')}/{local_path.name}")

        print(f"Done. Uploaded {uploaded} files.")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    args = parser.parse_args()

    creds = load_credentials()
    publish(creds, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
