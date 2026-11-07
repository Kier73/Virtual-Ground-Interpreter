#!/usr/bin/env python3
"""Build 17: compare temporal representations under clock symmetries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

from temporal_representations import run_representation_comparison


def write_reports(out: Path) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    result=run_representation_comparison()
    (out/"temporal_representation_comparison.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    summary={
        "build":17,
        "status":"synthetic_temporal_representation_comparison_complete",
        "empirical_sensor_data_processed":False,
        "source_data_status":"synthetic unlabelled event-pulse fixture only",
        "fourier_shift_invariance_error":result["fourier"]["circular_shift_magnitude_relative_error"],
        "stft_shift_covariance_error":result["stft"]["circular_shift_covariance_relative_error"],
        "stationary_haar_shift_invariance_error":result["stationary_haar_detail_energy"]["circular_shift_energy_relative_error"],
        "mellin_dilation_invariance_error":result["mellin"]["dilation_magnitude_relative_error"],
        "event_graph_affine_invariance_error":result["event_graph_fourier"]["affine_clock_eigenvalue_relative_error"],
        "event_graph_nonlinear_drift_distance":result["event_graph_fourier"]["nonlinear_clock_eigenvalue_relative_error"],
        "important_scope":"The outputs establish finite-fixture implementation properties only, not empirical sensor or universal-invariant claims."
    }
    (out/"build_17_status.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",default="reports")
    args=p.parse_args()
    print(json.dumps(write_reports(Path(args.output)),indent=2))
