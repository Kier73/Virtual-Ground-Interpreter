#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m unittest discover -s tests -v > test_run.txt 2>&1
python generate_artifacts.py > build_execution.log 2>&1
cat test_run.txt
cat build_execution.log
