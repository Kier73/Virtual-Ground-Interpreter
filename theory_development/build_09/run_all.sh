#!/usr/bin/env bash
set -euo pipefail
python -m unittest discover -s tests -v
python cross_modal_response.py
