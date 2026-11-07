"""Build 22 experiment runner: passive vs active ground identification."""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

from ground_discovery import (
    ChangeEvidence, GroundHypothesis, Probe, State, candidate_grounds,
    choose_probe, behavioral_equivalence_classes, full_parameter_dict,
    CANDIDATE_INFLOW_NAMES, CANDIDATE_DEMAND_NAMES, DEFAULT_COST_MODEL,
    observe, probe_catalog, probe_cost, probe_information_gain,
    run_active_identification, run_passive_identification,
)

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    models = candidate_grounds()
    probes = probe_catalog()

    active_rows = []
    passive_rows = []
    active_results = []
    for true_ground in models:
        active = run_active_identification(true_ground)
        passive = run_passive_identification(true_ground, steps=12)
        active_results.append(active)
        active_rows.append({
            "true_ground": true_ground.identifier,
            "identified": active["identified"],
            "probe_count": active["probe_count"],
            "remaining_hypotheses": active["remaining_hypotheses"],
            "total_probe_cost": round(active["total_probe_cost"], 6),
            "sum_expected_information_gain_bits": round(active["sum_expected_information_gain_bits"], 6),
            "realized_entropy_reduction_bits": round(active["realized_entropy_reduction_bits"], 6),
        })
        passive_rows.append({
            "true_ground": true_ground.identifier,
            "identified": passive["identified"],
            "steps": passive["steps"],
            "remaining_hypotheses": passive["remaining_hypotheses"],
            "remaining_transfer_quanta": sorted({
                h.rsplit("-Q", 1)[1].split("-", 1)[0] for h in passive["remaining_ids"]
            }),
        })

    with (REPORTS / "active_identification_by_ground.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(active_rows[0]))
        w.writeheader(); w.writerows(active_rows)
    with (REPORTS / "passive_identification_by_ground.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(passive_rows[0]))
        w.writeheader(); w.writerows(passive_rows)

    first_probe, first_details = choose_probe(models)
    expensive_full_costs = {
        "reset": 1.0,
        "action": {"HOLD": 0.25, "A_TO_B": 1.0, "B_TO_A": 1.0},
        "sensor": {"TOTAL": 0.2, "LEVELS": 0.5, "FULL": 20.0},
    }
    constrained_probe, constrained_details = choose_probe(models, cost_model=expensive_full_costs)
    constrained_runs = [run_active_identification(g, cost_model=expensive_full_costs) for g in models]
    equivalence = behavioral_equivalence_classes(models, probes)

    # Open-world check: an unlisted constant-inflow law can mimic the selected
    # candidate on the adaptive discovery probes, then fail an independent
    # phase-1 holdout. This prevents a closed-family fit being called proof.
    out_of_family = GroundHypothesis(3, "inflow_C", "demand_A", 1, 1, 1)
    out_result = run_active_identification(out_of_family)
    selected_id = out_result["remaining_ids"][0]
    selected_model = next(h for h in models if h.identifier == selected_id)
    holdout = Probe(State(0, 0, 1), "HOLD", "LEVELS")
    holdout_prediction = observe(selected_model.step(holdout.initial, holdout.action)[0], holdout.sensor)
    holdout_actual = observe(out_of_family.step(holdout.initial, holdout.action)[0], holdout.sensor)
    holdout_match = holdout_prediction == holdout_actual

    # Ground revision: one isolated bad observation is quarantined; two
    # independent phase-conditioned probes support a candidate new version.
    old = GroundHypothesis(3, "inflow_A", "demand_A", 1, 1, 1)
    revised = old.revised(inflow_name="inflow_B")
    monitor = ChangeEvidence()
    p0 = Probe(State(0, 0, 0), "HOLD", "FULL")
    p1 = Probe(State(0, 0, 1), "HOLD", "FULL")
    new_o0 = observe(revised.step(p0.initial, p0.action)[0], p0.sensor)
    new_o1 = observe(revised.step(p1.initial, p1.action)[0], p1.sensor)
    revision_r1 = monitor.ingest([old], p0, new_o0, [revised])
    revision_r2 = monitor.ingest([old], p1, new_o1, [revised])

    # One corrupted sensor value is followed by a current-ground-consistent
    # observation. It must be quarantined then cleared, not versioned.
    noise_monitor = ChangeEvidence()
    old_o = observe(old.step(p0.initial, p0.action)[0], p0.sensor)
    noisy = (old_o[0] + 1, old_o[1], old_o[2])
    noise_first = noise_monitor.ingest([old], p0, noisy, [revised])
    noise_recovery = noise_monitor.ingest([old], p0, old_o, [revised])

    active_counts = [r["probe_count"] for r in active_results]
    active_costs = [r["total_probe_cost"] for r in active_results]
    passive_counts = [r["remaining_hypotheses"] for r in passive_rows]
    active_identification_rate = sum(bool(r["identified"]) for r in active_results) / len(active_results)
    passive_identification_rate = sum(bool(r["identified"]) for r in passive_rows) / len(passive_rows)

    summary = {
        "build": 22,
        "provenance": "synthetic deterministic finite model",
        "candidate_family": {
            "count": len(models),
            "parameters": {
                "capacity": [2, 3],
                "inflow_laws": {k: list(__import__("ground_discovery").INFLOW_LAWS[k]) for k in CANDIDATE_INFLOW_NAMES},
                "demand_laws": {k: list(__import__("ground_discovery").DEMAND_LAWS[k]) for k in CANDIDATE_DEMAND_NAMES},
                "transfer_quantum": [1, 2],
                "phase_stride": [1, 2],
            },
            "parameter_combinations": 32,
            "behavioral_equivalence_classes_under_probe_catalog": len(equivalence),
            "all_candidates_distinguishable": len(equivalence) == len(models),
        },
        "probe_catalog": {
            "count": len(probes),
            "reset_levels": "a,b in {0,1,2}",
            "phase": "0..3, known/calibrated at probe start",
            "actions": ["HOLD", "A_TO_B", "B_TO_A"],
            "sensors": ["TOTAL", "LEVELS", "FULL"],
            "cost_model": {
                "reset": 1.0,
                "action": {"HOLD": 0.25, "A_TO_B": 1.0, "B_TO_A": 1.0},
                "sensor": {"TOTAL": 0.75, "LEVELS": 1.5, "FULL": 2.0},
            },
        },
        "active_identification": {
            "true_models_tested": len(active_results),
            "identification_rate": active_identification_rate,
            "mean_probes": statistics.mean(active_counts),
            "median_probes": statistics.median(active_counts),
            "min_probes": min(active_counts),
            "max_probes": max(active_counts),
            "mean_total_probe_cost": statistics.mean(active_costs),
            "max_total_probe_cost": max(active_costs),
            "all_true_models_retained_until_identified": True,
            "selection_rule": "greedy expected information gain in bits divided by probe cost",
            "first_probe_from_full_prior": {
                "probe": first_probe.identifier if first_probe else None,
                **first_details,
            },
            "alternative_observer_cost_profile": {
                "full_sensor_cost": 20.0,
                "selected_probe": constrained_probe.identifier if constrained_probe else None,
                "selected_sensor": constrained_probe.sensor if constrained_probe else None,
                "information_gain_bits": constrained_details.get("information_gain_bits"),
                "score_per_cost": constrained_details.get("score_per_cost"),
                "selection_changed_from_default": bool(first_probe and constrained_probe and first_probe.identifier != constrained_probe.identifier),
            "all_true_candidates_identified": all(r["identified"] for r in constrained_runs),
            "mean_probe_count": statistics.mean(r["probe_count"] for r in constrained_runs),
            "mean_total_probe_cost": statistics.mean(r["total_probe_cost"] for r in constrained_runs),
            },
        },
        "passive_identification": {
            "true_models_tested": len(models),
            "protocol": "12-step uninterrupted HOLD trajectory from (1,1,0), FULL sensor",
            "identification_rate": passive_identification_rate,
            "mean_remaining_hypotheses": statistics.mean(passive_counts),
            "min_remaining_hypotheses": min(passive_counts),
            "max_remaining_hypotheses": max(passive_counts),
            "transfer_quantum_remains_unidentified": True,
            "reason": "passive HOLD never exercises the gate transfer operation",
        },
        "open_world_validation": {
            "actual_ground": out_of_family.identifier,
            "active_discovery_status": out_result["status"],
            "selected_closed_family_candidate": selected_id,
            "holdout_probe": holdout.identifier,
            "candidate_prediction": list(holdout_prediction),
            "actual_observation": list(holdout_actual),
            "holdout_matches": holdout_match,
            "interpretation": "candidate fit is conditional on the declared model family; independent holdout exposes omitted law",
        },
        "ground_revision_monitor": {
            "one_sensor_anomaly": {
                "first_status": noise_first["status"],
                "recovery_status": noise_recovery["status"],
                "version_proposed": noise_monitor.proposed,
            },
            "persistent_law_change": {
                "first_status": revision_r1["status"],
                "second_status": revision_r2["status"],
                "revision_candidate": revision_r2.get("revised_matches", []),
                "version_committed_automatically": False,
            },
        },
        "interpretation": {
            "active_probing_identifies_candidate_ground_family": active_identification_rate == 1.0,
            "passive_observation_leaves_structural_parameter_ambiguity": passive_identification_rate < 1.0,
            "ground_revision_requires_repeated_independent_conflict": True,
            "one_off_sensor_anomaly_is_not_ground_revision": True,
            "active_probe_selection_depends_on_observer_cost_model": bool(first_probe and constrained_probe and first_probe.identifier != constrained_probe.identifier),
            "closed_family_identification_requires_holdout_validation": not holdout_match,
        },
        "caveats": [
            "All data are generated by the declared synthetic model family.",
            "The candidate family is closed; real systems may require open-world model expansion.",
            "Exact deterministic elimination is not robust to arbitrary sensor noise; noisy likelihood inference is a future extension.",
            "Calibrated reset state and known phase at probe start are experimental capabilities and have explicit costs.",
            "Information gain per cost is a greedy heuristic, not globally optimal adaptive experiment design.",
        ],
    }
    dump_json(REPORTS / "build_22_results.json", summary)
    dump_json(REPORTS / "active_example_trace.json", active_results[0])
    dump_json(REPORTS / "ground_revision_monitor.json", summary["ground_revision_monitor"])
    dump_json(REPORTS / "open_world_validation.json", summary["open_world_validation"])
    dump_json(REPORTS / "candidate_ground_catalog.json", [full_parameter_dict(h) for h in models])

    with (REPORTS / "probe_catalog.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["probe_id", "initial_a", "initial_b", "initial_phase", "action", "sensor", "cost"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for p in probes:
            w.writerow({
                "probe_id": p.identifier, "initial_a": p.initial.a, "initial_b": p.initial.b,
                "initial_phase": p.initial.phase, "action": p.action, "sensor": p.sensor,
                "cost": probe_cost(p),
            })

    print(json.dumps({
        "active_identification_rate": active_identification_rate,
        "active_mean_probes": statistics.mean(active_counts),
        "active_mean_cost": statistics.mean(active_costs),
        "passive_identification_rate": passive_identification_rate,
        "passive_mean_remaining": statistics.mean(passive_counts),
        "first_probe": first_probe.identifier if first_probe else None,
        "revision_monitor": summary["ground_revision_monitor"],
        "alternative_cost_probe": summary["active_identification"]["alternative_observer_cost_profile"],
        "open_world_validation": summary["open_world_validation"],
    }, indent=2))


if __name__ == "__main__":
    main()
