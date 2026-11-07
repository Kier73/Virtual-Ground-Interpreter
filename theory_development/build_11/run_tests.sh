#!/usr/bin/env bash
set -euo pipefail
python build_11.py --out .
python -m unittest discover -s tests -v
