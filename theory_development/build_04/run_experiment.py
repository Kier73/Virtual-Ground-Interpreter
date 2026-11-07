from __future__ import annotations

import json
from pathlib import Path

from s3_codonic_navigation import (
    build_report, cap_loop, horizontal_lift, trace_csv,
    wavy_cap_loop,
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
DATA.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

report = build_report()
(DATA / "main_loop_trace.csv").write_text(
    trace_csv(cap_loop(0.62), horizontal_lift(cap_loop(0.62))), encoding="utf-8"
)
(DATA / "second_loop_trace.csv").write_text(
    trace_csv(cap_loop(0.98), horizontal_lift(cap_loop(0.98))), encoding="utf-8"
)
wavy = wavy_cap_loop(0.72, 0.13, 3)
(DATA / "wavy_loop_trace.csv").write_text(
    trace_csv(wavy, horizontal_lift(wavy)), encoding="utf-8"
)
report["trace_files"] = [
    "data/main_loop_trace.csv",
    "data/second_loop_trace.csv",
    "data/wavy_loop_trace.csv",
]
report.pop("trace_csv", None)
(REPORTS / "build_04_report.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps({k: v for k, v in report.items() if k not in ("main_loop", "second_loop")}, indent=2))
print("\nMain loop:")
print(json.dumps(report["main_loop"], indent=2))
print("\nSecond loop:")
print(json.dumps(report["second_loop"], indent=2))
