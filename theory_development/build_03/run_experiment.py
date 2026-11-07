from __future__ import annotations
import csv
import json
from pathlib import Path
from math import pi

from codonic_connection import (
    Registry, compile_rotation, transport_matrix, summarize, path_samples,
    finite_difference_rms, matvec, oriented_phase, RADIAL_OBSERVER,
    FULL_OBSERVER, observer_closed, determinant, trace, conjugate,
    max_abs_matrix_delta, identity, reverse_path,
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
DATA.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    theta = 0.8
    default = summarize(theta)

    # Same abstract operations, different spellings: nomenclature is not identity.
    renamed = summarize(theta, Registry(add="plus", multiply="times"))

    # Time schedules change the observed response profile, not the endpoint map.
    uniform = path_samples(theta, (1.0, 1.0, 1.0), samples_per_segment=80)
    warped = path_samples(theta, (2.0, 0.7, 1.3), samples_per_segment=80)
    write_csv(DATA / "trajectory_uniform.csv", uniform)
    write_csv(DATA / "trajectory_warped.csv", warped)

    uniform_final = (uniform[-1]["x"], uniform[-1]["y"])
    warped_final = (warped[-1]["x"], warped[-1]["y"])

    # Reverse traversal is the inverse edge sequence in reverse order.
    path = compile_rotation(theta)
    reversed_path = reverse_path(path)
    reverse_h = transport_matrix(reversed_path)
    reverse_start = (1.0, 0.0)
    reverse_final = (reverse_h[0][0], reverse_h[1][0])

    # Holonomy covariance under a change of basis: H' = B H B^-1.
    h = transport_matrix(path)
    basis = ((2.0, 0.5), (0.0, 0.5))
    h_changed = conjugate(h, basis)

    report = {
        "build": "03",
        "title": "Codonic connection geometry",
        "status": "prototype experiment; not a universal invariant claim",
        "scope": {
            "codons_used": ["ad", "mx"],
            "semantics": {"ad": "addition", "mx": "multiplication"},
            "registry_names_are_configurable": True,
            "observer_base": "radius norm; states with equal radius are observationally identified",
            "hidden_fibre": "orientation of the 2-D state",
            "transport": "ordered product of invertible shear matrices",
            "terminology_caveat": "discrete connection / holonomy analogue, not a complete principal-bundle connection",
        },
        "main_experiment": default,
        "renamed_registry": {
            "profile": {"addition": "plus", "multiplication": "times"},
            "same_transport_matrix_max_abs_error": max_abs_matrix_delta(
                h, transport_matrix(compile_rotation(theta, Registry(add="plus", multiply="times")))
            ),
            "same_holonomy_phase_rad": oriented_phase((1.0, 0.0), matvec(
                transport_matrix(compile_rotation(theta, Registry(add="plus", multiply="times"))), (1.0, 0.0)
            )),
        },
        "time_reparameterization": {
            "uniform_durations": [1.0, 1.0, 1.0],
            "warped_durations": [2.0, 0.7, 1.3],
            "uniform_total_time": uniform[-1]["time"],
            "warped_total_time": warped[-1]["time"],
            "uniform_final_state": list(uniform_final),
            "warped_final_state": list(warped_final),
            "final_state_max_abs_error": max(abs(a-b) for a,b in zip(uniform_final, warped_final)),
            "uniform_radius_rate_rms": finite_difference_rms(uniform, "radius"),
            "warped_radius_rate_rms": finite_difference_rms(warped, "radius"),
            "uniform_angle_rate_rms": finite_difference_rms(uniform, "angle"),
            "warped_angle_rate_rms": finite_difference_rms(warped, "angle"),
            "interpretation": "same ordered path and endpoint transport; different time-resolved response",
        },
        "reverse_path": {
            "forward_phase_rad": default["holonomy_phase_rad"],
            "reverse_phase_rad": oriented_phase(reverse_start, reverse_final),
            "reverse_transport_matrix": [list(row) for row in reverse_h],
            "forward_reverse_product_max_abs_error": max_abs_matrix_delta(
                __import__("codonic_connection").matmul(reverse_h, h), identity()
            ),
        },
        "basis_change": {
            "basis_matrix": [list(row) for row in basis],
            "original_trace": trace(h),
            "changed_trace": trace(h_changed),
            "trace_abs_error": abs(trace(h) - trace(h_changed)),
            "original_determinant": determinant(h),
            "changed_determinant": determinant(h_changed),
            "determinant_abs_error": abs(determinant(h) - determinant(h_changed)),
            "interpretation": "trace and determinant of holonomy are preserved by conjugation",
        },
        "files": [
            "data/trajectory_uniform.csv",
            "data/trajectory_warped.csv",
        ],
    }
    (REPORTS / "build_03_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "build": "03",
        "holonomy_phase_rad": report["main_experiment"]["holonomy_phase_rad"],
        "matrix_error": report["main_experiment"]["rotation_matrix_max_abs_error"],
        "radial_closed": report["main_experiment"]["radial_observer_closed"],
        "full_closed": report["main_experiment"]["full_observer_closed"],
        "schedule_rate_rms": [report["time_reparameterization"]["uniform_angle_rate_rms"], report["time_reparameterization"]["warped_angle_rate_rms"]],
        "report": str(REPORTS / "build_03_report.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
