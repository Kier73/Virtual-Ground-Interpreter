#!/usr/bin/env python3
"""Create contiguous fixed-duration windows and analyze a downloaded full recording.

Example:
  python scripts/analyze_full_recording.py downloaded_source/measurement_01.csv --out full_run --window 1.0

This generates analysis windows, never interpolates missing samples, and marks
only windows wholly inside the source-declared [66, 68] s observer interval.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_11 import run  # noqa: E402

EXPECTED_HEADER = ["time_s", "gforce_x", "gforce_y", "gforce_z"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--out", type=Path, default=Path("full_recording_analysis"))
    parser.add_argument("--window", type=float, default=1.0, help="Window duration in seconds (default: 1.0).")
    args = parser.parse_args()
    if args.window <= 0 or not math.isfinite(args.window):
        parser.error("--window must be a finite positive number")
    if not args.csv_path.exists():
        parser.error(f"CSV not found: {args.csv_path}")

    times = []
    parsed = []
    with args.csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXPECTED_HEADER:
            raise ValueError(f"Unexpected header {reader.fieldnames!r}; expected {EXPECTED_HEADER!r}")
        for line_no, row in enumerate(reader, start=2):
            t = float(row["time_s"])
            values = [float(row[k]) for k in EXPECTED_HEADER[1:]]
            if not all(math.isfinite(v) for v in [t, *values]):
                raise ValueError(f"Non-finite sample at source line {line_no}")
            parsed.append((line_no, t, *values))
            times.append(t)
    if len(parsed) < 8:
        raise ValueError("Full recording contains fewer than eight samples")
    if any(times[i] <= times[i - 1] for i in range(1, len(times))):
        raise ValueError("Non-increasing timestamps found; inspect source before windowing")

    start = times[0]
    bins: dict[int, list[tuple]] = {}
    for item in parsed:
        idx = int(math.floor((item[1] - start) / args.window))
        bins.setdefault(idx, []).append(item)

    window_rows = []
    for idx in sorted(bins):
        group = bins[idx]
        if len(group) < 8:
            continue
        t0 = start + idx * args.window
        label = f"window_{idx:04d}_{t0:.3f}_{t0 + args.window:.3f}"
        for line_no, t, x, y, z in group:
            window_rows.append({"window_id": label, "source_line": line_no, "time_s": t, "gforce_x": x, "gforce_y": y, "gforce_z": z})
    args.out.mkdir(parents=True, exist_ok=True)
    window_file = args.out / "full_recording_windows.csv"
    with window_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["window_id", "source_line", *EXPECTED_HEADER])
        writer.writeheader(); writer.writerows(window_rows)

    report = run(args.out, window_file)
    report["scope"] = "Full downloaded measurement_01 recording divided into contiguous fixed-duration windows. No interpolation was performed."
    report["source"]["source_excerpt_rows"] = None
    report["source"]["source_excerpt_windows"] = None
    report["full_recording_input"] = {"path": str(args.csv_path), "source_rows": len(parsed), "analysis_window_s": args.window, "generated_windows": len({r['window_id'] for r in window_rows}), "discarded_rows_in_short_final_bins": len(parsed) - len(window_rows)}
    report_path = args.out / "reports" / "build_11_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    key_path = args.out / "reports" / "key_results.json"
    if key_path.exists():
        key = json.loads(key_path.read_text(encoding="utf-8"))
        key.pop("source_rows_in_excerpt", None)
        key["source_rows_full_recording"] = len(parsed)
        key["analysis_window_s"] = args.window
        key["generated_windows"] = report["full_recording_input"]["generated_windows"]
        key["conclusion"] = "Full recording was analyzed in fixed-duration windows; interpret results with the report's sensor and sampling caveats."
        key_path.write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(json.dumps(report["full_recording_input"], indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
