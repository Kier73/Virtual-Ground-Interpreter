#!/usr/bin/env python3
"""Download one TAPS split from Zenodo and optionally extract it safely.

Default is the held-out test split (about 452 MB), not the entire 2.7 GB corpus.
The script uses the Zenodo record API and verifies the published MD5 checksum.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

RECORD_ID = "18324208"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
FILES = {
    "test": ("TAPS_data_test.zip", "7793d1272a4a0a3957a44014db283cbb"),
    "dev": ("TAPS_data_dev.zip", "7ac8b2f4cd6db1757ba9f711acc6ee7a"),
}


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "VL-Response-Geometry-Build14/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, destination: Path, expected_md5: str) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    md5 = hashlib.md5()
    size = 0
    req = urllib.request.Request(url, headers={"User-Agent": "VL-Response-Geometry-Build14/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block); md5.update(block); size += len(block)
        actual = md5.hexdigest()
        if actual.lower() != expected_md5.lower():
            raise ValueError(f"MD5 mismatch: expected {expected_md5}, received {actual}")
        tmp.replace(destination)
    except Exception:
        try: tmp.unlink()
        except FileNotFoundError: pass
        raise
    return {"path": str(destination), "bytes": size, "md5": md5.hexdigest(), "verified": True}


def safe_extract(zip_path: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            raw = info.filename.replace("\\", "/")
            rel = PurePosixPath(raw)
            if rel.is_absolute() or any(p in ("..", "") for p in rel.parts):
                raise ValueError(f"Unsafe ZIP member path: {info.filename}")
            target = (root / Path(*rel.parts)).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"ZIP member escapes destination: {info.filename}")
        zf.extractall(root)
        count = len(zf.infolist())
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("test", "dev"), default="test")
    ap.add_argument("--output", default="data/raw")
    ap.add_argument("--no-extract", action="store_true")
    args = ap.parse_args()
    filename, expected_md5 = FILES[args.split]
    record = fetch_json(API_URL)
    entries = record.get("files", [])
    match = next((x for x in entries if x.get("key") == filename or x.get("filename") == filename), None)
    if not match:
        raise SystemExit(f"Could not find {filename} in Zenodo record {RECORD_ID}")
    links = match.get("links", {})
    url = links.get("content") or links.get("download") or links.get("self")
    if not url:
        raise SystemExit("Zenodo API did not provide a download link")
    checksum = match.get("checksum", "")
    if checksum.startswith("md5:"):
        expected_md5 = checksum.split(":", 1)[1]
    elif checksum and checksum.lower() != expected_md5.lower():
        raise SystemExit(f"Zenodo checksum metadata differs from verified page checksum: {checksum}")
    output = Path(args.output)
    archive = output / filename
    result = download(url, archive, expected_md5)
    result.update({"dataset": "TAPS", "split": args.split, "record_id": RECORD_ID})
    if not args.no_extract:
        extracted_root = output / Path(filename).stem
        result["extracted_members"] = safe_extract(archive, extracted_root)
        result["extracted_root"] = str(extracted_root)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
