"""Generate the Build 06 JSON/CSV artifacts from the deterministic experiment."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from s3_active_observer import (
    DEFAULT_ALG, IDENTITY, OBSERVERS, PROBES, REGULAR_INTENTS,
    antipodal_pair, build_antipodal_intent, fibre_phase, hopf_project,
    make_candidates, measurement, probe_ranking_csv, s3_distance,
    signed_solid_angle, so3_distance, so3_signed_k_angle,
    s3_phase_absolute, csv_trace, make_report,
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
DATA.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

candidates = make_candidates()
report = make_report(candidates)
(REPORTS / "build_06_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
(DATA / "regular_hopf_paths.csv").write_text(csv_trace(candidates))
(DATA / "probe_rankings.csv").write_text(probe_ranking_csv(candidates))

with (DATA / "geometry_summary.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "candidate", "theta_rad", "direction", "signed_area_sr", "expected_phase_rad",
        "measured_phase_rad", "phase_error_rad", "base_endpoint_error",
        "off_fibre_residual", "so3_signed_k_angle_rad", "s3_endpoint_distance_rad",
        "so3_endpoint_distance_rad",
    ])
    writer.writeheader()
    for c in candidates:
        phase, residual = fibre_phase(IDENTITY, c.q_final)
        endpoint = hopf_project(c.q_final)
        base_error = sum((a-b)**2 for a,b in zip(endpoint, (0.0,0.0,1.0)))**0.5
        area = signed_solid_angle(c.base_path)
        writer.writerow({
            "candidate": c.name,
            "theta_rad": f"{c.theta:.16g}",
            "direction": c.direction,
            "signed_area_sr": f"{area:.16g}",
            "expected_phase_rad": f"{0.5*area:.16g}",
            "measured_phase_rad": f"{phase:.16g}",
            "phase_error_rad": f"{abs(phase-0.5*area):.16g}",
            "base_endpoint_error": f"{base_error:.16g}",
            "off_fibre_residual": f"{residual:.16g}",
            "so3_signed_k_angle_rad": f"{so3_signed_k_angle(c.q_final):.16g}",
            "s3_endpoint_distance_rad": f"{s3_distance(IDENTITY,c.q_final):.16g}",
            "so3_endpoint_distance_rad": f"{so3_distance(IDENTITY,c.q_final):.16g}",
        })

anti = antipodal_pair(candidates[0])
anti_intent = build_antipodal_intent()
with (DATA / "antipodal_control.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["state", "hopf_x", "hopf_y", "hopf_z",
                                           "s3_phase_rad", "so3_signed_k_angle_rad"])
    writer.writeheader()
    for c in anti:
        n = hopf_project(c.q_final)
        writer.writerow({"state": c.name, "hopf_x": n[0], "hopf_y": n[1], "hopf_z": n[2],
                         "s3_phase_rad": s3_phase_absolute(c.q_final),
                         "so3_signed_k_angle_rad": so3_signed_k_angle(c.q_final)})

with (REPORTS / "antipodal_control.json").open("w") as f:
    import json as _json
    m = report["antipodal_quotient_control"]
    _json.dump(m, f, indent=2, sort_keys=True)
    f.write("\n")

# Short plain-text summary for quick verification.
lines = ["Build 06 artifact generation completed.",
         f"Hamilton product instructions: {len(DEFAULT_ALG.product_program.instructions)}",
         f"Regular path hypotheses: {len(candidates)}",
         "Observer / intent selections:"]
for observer, intentions in report["observer_intention_probe_selection"].items():
    for intention, selection in intentions.items():
        status = report["observer_intention_selection_status"][observer][intention]
        if selection:
            choice = selection["probe"]
        elif status == "no_probe_needed_target_constant":
            choice = "NO PROBE NEEDED (target constant over candidates)"
        else:
            choice = "UNRESOLVED (no available distinguishing probe)"
        lines.append(f"  {observer} / {intention}: {choice}")
lines.append("Antipodal pair selections:")
for observer, selection in report["antipodal_quotient_control"]["observer_intention_probe_selection"].items():
    lines.append(f"  {observer}: {selection['probe'] if selection else 'UNRESOLVED (antipodes indistinguishable)'}")
(REPORTS / "summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
