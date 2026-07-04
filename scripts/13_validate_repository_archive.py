from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO / "release_manifest.csv"

class ArchiveValidationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ArchiveValidationError(f"Release manifest not found: {path.relative_to(REPO)}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_manifest(path: Path) -> int:
    rows = read_manifest(path)
    required = {
        "file_path",
        "package_section",
        "file_role",
        "required_for",
        "sha256",
        "bytes",
        "claim_boundary",
    }
    if not rows:
        raise ArchiveValidationError("Release manifest has no data rows.")
    missing_columns = required - set(rows[0])
    if missing_columns:
        raise ArchiveValidationError(f"Release manifest missing columns: {', '.join(sorted(missing_columns))}")

    manifest_files = {row["file_path"].replace("\\", "/") for row in rows}
    tracked = subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True)
    tracked_files = {line.strip().replace("\\", "/") for line in tracked.splitlines() if line.strip()}
    extra_files = sorted(tracked_files - manifest_files)
    if extra_files:
        shown = "\n".join(extra_files[:30])
        raise ArchiveValidationError(f"Tracked files absent from release manifest:\n{shown}")

    seen: set[str] = set()
    for row in rows:
        rel = row["file_path"]
        if rel in seen:
            raise ArchiveValidationError(f"Duplicate manifest row: {rel}")
        seen.add(rel)

        target = REPO / rel
        if not target.exists():
            raise ArchiveValidationError(f"Manifest file not found: {rel}")
        if target.is_dir():
            raise ArchiveValidationError(f"Manifest row points to a directory: {rel}")

        if row["sha256"] != "not_applicable_self_manifest":
            observed_hash = sha256(target)
            if observed_hash != row["sha256"]:
                raise ArchiveValidationError(f"Hash mismatch for {rel}: {observed_hash} != {row['sha256']}")

        if row["bytes"] != "not_applicable_self_manifest":
            observed_size = target.stat().st_size
            if str(observed_size) != row["bytes"]:
                raise ArchiveValidationError(f"Size mismatch for {rel}: {observed_size} != {row['bytes']}")
    return len(rows)


def run_reproduction_check() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "reproduce_all.py"), "--verify-only"],
        cwd=str(REPO),
        check=False,
    )
    if completed.returncode != 0:
        raise ArchiveValidationError("Repository reproduction verification failed.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the repository release manifest and reproduction entry point."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--skip-reproduction", action="store_true")
    args = parser.parse_args()

    try:
        row_count = validate_manifest(args.manifest)
        if not args.skip_reproduction:
            run_reproduction_check()

        print(f"Release manifest rows: {row_count}")
        if args.skip_reproduction:
            print("Repository reproduction verification: skipped")
        else:
            print("Repository reproduction verification: pass")
        print("Repository archive validation: pass")
        return 0
    except ArchiveValidationError as error:
        print("Repository archive validation: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
