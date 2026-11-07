#!/usr/bin/env bash
set -euo pipefail
python -m unittest discover -s tests -v
python build_17.py --output reports
