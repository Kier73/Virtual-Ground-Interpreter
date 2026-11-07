#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
python build_10.py --out "$ROOT" --seed 20261105
python -m unittest discover -s tests -v
