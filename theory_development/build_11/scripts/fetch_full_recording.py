#!/usr/bin/env python3
"""Fetch the exact public Build 11 source files and verify basic structure.

Network access is required. Downloads are saved locally; nothing is uploaded.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main"
FILES = {
    "measurement_01.csv": f"{BASE}/data/processed/measurement_01.csv",
    "change_points.csv": f"{BASE}/documentation/change_points.csv",
    "metadata.json": f"{BASE}/metadata/metadata.json",
    "LICENSE": f"{BASE}/LICENSE",
}
EXPECTED_HEADER = ["time_s", "gforce_x", "gforce_y", "gforce_z"]
EXPECTED_ROWS = 8157


def fetch(url: str, target: Path, retries: int = 3) -> bytes:
    target.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VL-Build11-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
            target.write_bytes(data)
            return data
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("downloaded_source"))
    parser.add_argument("--allow-row-count-change", action="store_true", help="Do not fail if the upstream row count differs from v1.0.0 metadata.")
    args = parser.parse_args()
    manifest = {"repository": "https://github.com/witulska/vibration-changepoint-dataset", "version": "1.0.0", "files": {}}
    for name, url in FILES.items():
        try:
            data = fetch(url, args.out / name)
            manifest["files"][name] = {"url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            print(f"Fetched {name}: {len(data):,} bytes")
        except RuntimeError as exc:
            if name == "LICENSE":
                manifest["files"][name] = {"url": url, "fetch_error": str(exc)}
                print(f"Warning: {exc}")
            else:
                raise

    csv_path = args.out / "measurement_01.csv"
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != EXPECTED_HEADER:
            raise ValueError(f"Unexpected measurement_01 header: {header!r}; expected {EXPECTED_HEADER!r}")
        rows = sum(1 for _ in reader)
    manifest["measurement_01"] = {"header": header, "rows": rows, "expected_rows": EXPECTED_ROWS, "row_count_matches_metadata": rows == EXPECTED_ROWS}
    if rows != EXPECTED_ROWS and not args.allow_row_count_change:
        raise ValueError(f"Expected {EXPECTED_ROWS} data rows from v1.0.0, got {rows}. Use --allow-row-count-change only after checking upstream version changes.")

    metadata = json.loads((args.out / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("version") != "1.0.0":
        raise ValueError(f"Upstream metadata version changed: {metadata.get('version')!r}")
    (args.out / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["measurement_01"], indent=2))
    print(f"Manifest: {args.out / 'download_manifest.json'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
