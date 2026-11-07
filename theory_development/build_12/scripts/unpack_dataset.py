#!/usr/bin/env python3
"""Safely extract the Figshare archive without allowing path traversal."""
from __future__ import annotations
import argparse, zipfile
from pathlib import Path, PurePosixPath

p=argparse.ArgumentParser(); p.add_argument("archive", type=Path); p.add_argument("--out", type=Path, default=Path("data/rochester/extracted")); a=p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(a.archive) as z:
    root=a.out.resolve()
    for item in z.infolist():
        target=(a.out / item.filename).resolve()
        if root not in target.parents and target != root:
            raise SystemExit(f"Unsafe archive path: {item.filename}")
    z.extractall(a.out)
print(f"Extracted {len(z.infolist())} archive entries to {a.out}")
