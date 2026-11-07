#!/usr/bin/env sh
set -eu
python -m unittest discover -s tests -v
python active_observer.py
