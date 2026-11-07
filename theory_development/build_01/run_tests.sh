#!/usr/bin/env sh
set -eu
python -m unittest -v
python vl_response_geometry.py > demo_report.json
python dynamic_response.py > dynamic_report.json
