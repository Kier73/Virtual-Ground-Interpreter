#!/usr/bin/env python3
"""Download the versioned University of Rochester RIR article from Figshare.

Requires network access on the machine running the script. No credentials are
needed for this public article. It records Figshare metadata and archive SHA-256.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time, urllib.request
from pathlib import Path

ARTICLE_ID = 26801089
VERSION = 3
BASE = "https://api.figshare.com/v2"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "VL-Response-Geometry-Build12/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, dest: Path, max_bytes: int) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "VL-Response-Geometry-Build12/1.0"})
    h = hashlib.sha256(); size = 0
    with urllib.request.urlopen(req, timeout=90) as response:
        expected = response.headers.get("Content-Length")
        if expected and int(expected) > max_bytes:
            raise RuntimeError(f"Download is {expected} bytes, above configured maximum {max_bytes}")
        with dest.open("wb") as f:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > max_bytes:
                    raise RuntimeError(f"Download exceeded maximum {max_bytes} bytes")
                f.write(block); h.update(block)
    return {"path": str(dest), "size_bytes": size, "sha256": h.hexdigest(), "content_length_header": expected}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/rochester"))
    ap.add_argument("--max-mb", type=int, default=200)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    meta_url = f"{BASE}/articles/{ARTICLE_ID}/versions/{VERSION}"
    metadata = get_json(meta_url)
    (args.out / "figshare_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    archive_url = f"{BASE}/articles/{ARTICLE_ID}/versions/{VERSION}/download"
    archive_path = args.out / "rochester_rir_v3.zip"
    result = download(archive_url, archive_path, args.max_mb * 1024 * 1024)
    result.update({"dataset_title": metadata.get("title"), "article_id": ARTICLE_ID,
                   "version": VERSION, "doi": metadata.get("doi"), "source_url": meta_url,
                   "license": metadata.get("license")})
    (args.out / "download_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Download failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
