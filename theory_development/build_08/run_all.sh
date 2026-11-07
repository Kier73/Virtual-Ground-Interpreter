#!/usr/bin/env bash
set -euo pipefail
python -m unittest discover -s tests -v
python cross_observer_generalization.py --out .
