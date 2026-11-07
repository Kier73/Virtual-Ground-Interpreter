"""Build 21 reproducible experiments and machine-readable reports."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path
from flow_ground import *

LEGACY = Path(__file__).resolve().parent / "legacy_build_20"
sys.path.insert(0, str(LEGACY))
import virtual_ground as legacy_vg
import partial_ground as legacy_pg

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def jsonable(obj):
    if isinstance(obj, FlowState):
        return list(obj)
    if isinstance(obj, tuple):
        return [jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items() if k not in {"blocks", "block_of"}}
    if isinstance(obj, (list, set, frozenset)):
        return [jsonable(x) for x in obj]
    return obj


def main():
    ground = FlowGround()
    verification = verify_ground(ground)
    canonical_start = FlowState(1, 1, 0)
    reachable = reachable_states(ground, canonical_start)
    edge_count = reachable_edges(ground, reachable)

    # Observer refinement: initial observations vs the distinctions needed to
    # predict all action-labelled transitions exactly.
    observer_rows = []
    for observer in OBSERVERS:
        p = partition_refinement(ground, observer)
        observer_rows.append({
            "observer": observer,
            "initial_observation_classes": p["initial_observation_classes"],
            "refined_predictive_classes": p["refined_predictive_classes"],
            "refinement_rounds": p["refinement_rounds"],
            "additional_predictive_splits": p["split_count"],
        })
    with (REPORTS / "observer_refinement.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(observer_rows[0]))
        w.writeheader(); w.writerows(observer_rows)

    inventory_goal = lambda s: s.a + s.b == 3
    exact_goal = lambda s: s.a == 1 and s.b == 2
    task_rows = [
        task_observability(ground, "TOTAL", inventory_goal),
        task_observability(ground, "TOTAL", exact_goal),
        task_observability(ground, "TOTAL_PHASE", exact_goal),
        task_observability(ground, "LEVELS", exact_goal),
        task_observability(ground, "FULL", exact_goal),
    ]

    # Same actual state, different sensor views and belief sizes. The planner
    # must reach the exact distribution goal for every state consistent with
    # each observer's initial reading.
    sensor_cases = [
        ("TOTAL", (2,)),
        ("TOTAL_PHASE", (2, 0)),
        ("LEVELS", (1, 1)),
        ("FULL", (1, 1, 0)),
    ]
    sensor_rows = []
    sensor_policies = {}
    for observer, value in sensor_cases:
        alphabet_size = len({observe(s, observer) for s in ground.all_states()})
        code_bits = math.ceil(math.log2(alphabet_size))
        compiled = compile_navigation_task(ground, observer, value, exact_goal, max_depth=16)
        policy = compiled.get("policy")
        sensor_rows.append({
            "observer": observer,
            "initial_observation": value,
            "fixed_width_observation_bits": code_bits,
            "initial_belief_size": compiled.get("initial_belief_size", 0),
            "policy_exists": compiled["compiled"],
            "policy_certificate_verified": compiled.get("certificate", {}).get("verified", False),
            "worst_case_steps": None if policy is None else policy["worst_case_steps"],
            "belief_search_nodes": None if policy is None else policy["belief_nodes_expanded"],
        })
        sensor_policies[observer] = jsonable(compiled)
    with (REPORTS / "observer_resource_tradeoff.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sensor_rows[0]))
        w.writeheader(); w.writerows(sensor_rows)
    (REPORTS / "belief_policy_examples.json").write_text(json.dumps(sensor_policies, indent=2) + "\n")

    # Resource Pareto example. The faster route uses more energy and commands;
    # the longer route waits for exogenous inflow and uses fewer gate operations.
    route_start = FlowState(0, 1, 0)
    route_target = FlowState(1, 2, 3)
    routes = pareto_routes(ground, route_start, lambda s: s == route_target)
    profiles = [
        ResourceProfile("time-first", time_weight=1.0, energy_weight=0.05),
        ResourceProfile("energy-first", time_weight=0.2, energy_weight=1.0),
        ResourceProfile("tight-energy", time_weight=1.0, energy_weight=0.0, max_energy=9.0),
        ResourceProfile("tight-time-and-energy", time_weight=1.0, energy_weight=0.0, max_time=8.0, max_energy=9.0),
    ]
    resource_choices = []
    for profile in profiles:
        selected = choose_route(routes, profile)
        resource_choices.append({
            "profile": profile.name,
            "feasible": selected is not None,
            "cost": None if selected is None else selected["cost"],
            "path": None if selected is None else selected["path"],
            "target": None if selected is None else selected["target"],
        })
    with (REPORTS / "resource_pareto_routes.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "energy", "communication", "path"])
        for r in routes:
            w.writerow([*r["cost"], " ".join(r["path"])])

    # Exhaustive state and transition catalogue for independent inspection.
    with (REPORTS / "flow_state_catalog.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["a", "b", "phase", "total", "valid"])
        for s in ground.all_states():
            w.writerow([s.a, s.b, s.phase, s.a + s.b, ground.validate(s)])
    with (REPORTS / "flow_transition_catalog.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["a", "b", "phase", "action", "next_a", "next_b", "next_phase", "inflow", "actual_demand", "spill", "unmet_demand", "mass_balance_residual"])
        for s in ground.all_states():
            for action in ground.legal_actions(s):
                nxt, ledger = ground.step_with_ledger(s, action)
                w.writerow([s.a, s.b, s.phase, action, nxt.a, nxt.b, nxt.phase,
                            ledger.inflow, ledger.actual_demand, ledger.spill,
                            ledger.unmet_demand, ledger.mass_balance_residual])

    # Controlled invariance vs autonomous persistence.
    safe = lambda s: s.a >= 1 and s.b >= 1
    controlled_kernel = controlled_invariant_kernel(ground, safe)
    autonomous_kernel = autonomous_invariant_kernel(ground, safe)
    safe_policy = viability_policy(ground, controlled_kernel)
    action_counts = {a: sum(chosen == a for chosen in safe_policy.values()) for a in ACTIONS}
    with (REPORTS / "viability_policy.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["a", "b", "phase", "chosen_action", "next_a", "next_b", "next_phase"])
        for s, action in sorted(safe_policy.items()):
            nxt = ground.transition(s, action)
            w.writerow([s.a, s.b, s.phase, action, nxt.a, nxt.b, nxt.phase])

    # Environment trajectory and exact conservation ledger.
    env_trace = []
    trace_state = canonical_start
    for _ in range(8):
        nxt, ledger = ground.step_with_ledger(trace_state, "HOLD")
        env_trace.append({
            "before": trace_state,
            "action": "HOLD",
            "inflow": ledger.inflow,
            "demand_requested": ledger.requested_demand,
            "demand_actual": ledger.actual_demand,
            "spill": ledger.spill,
            "after": nxt,
            "ground_version": ground.version,
        })
        trace_state = nxt

    # Versioned ground shifts vs ordinary environmental progress.
    expanded = ground.revise_capacity(4)
    reduced = ground.revise_capacity(2)
    env_revised = ground.revise_environment(inflow=(0, 1, 0, 1))
    migration = {
        "capacity_expansion": migration_report(ground, expanded),
        "capacity_reduction": migration_report(ground, reduced),
        "environment_law_revision": migration_report(ground, env_revised),
        "ordinary_phase_advance": {
            "version_before": ground.version,
            "version_after": ground.version,
            "ground_shift": False,
        },
        "observer_sensor_change": {"ground_version_change": 0, "ground_shift": False},
        "resource_profile_change": {"ground_version_change": 0, "ground_shift": False},
    }

    legacy_rotor = legacy_vg.base_ground()
    legacy_rotor_distances, legacy_rotor_paths = legacy_vg.bfs_policy(legacy_rotor)
    legacy_support = legacy_pg.PartialGround()
    legacy_support_distances, _, legacy_support_edges = legacy_pg.enumerate_reachable(legacy_support)
    legacy_regression = {
        "rotor4_valid_states": len(legacy_vg.all_states()),
        "rotor4_reachable_states": len(legacy_rotor_distances),
        "rotor4_policy_entries": len(legacy_rotor_paths),
        "support9_reachable_stable_states": len(legacy_support_distances),
        "support9_directed_edges": len(legacy_support_edges),
    }

    result = {
        "build": 21,
        "provenance": "synthetic_deterministic_finite_model_not_physical_hydraulics",
        "ground": {
            "name": ground.name,
            "version": ground.version,
            "capacity_per_reservoir": ground.capacity,
            "phase_count": ground.phase_count,
            "environment_inflow_schedule": ground.inflow,
            "environment_demand_schedule": ground.demand,
            "variable_partition": {
                "structural_banks": FLOW_PARTITION.structural,
                "controlled": FLOW_PARTITION.controlled,
                "endogenous_flow_and_storage": FLOW_PARTITION.endogenous,
                "exogenous_environment": FLOW_PARTITION.exogenous,
            },
        },
        "verification": verification,
        "build20_regression": legacy_regression,
        "reachable_from_canonical_start": {
            "start": canonical_start,
            "state_count": len(reachable),
            "directed_edge_count": edge_count,
        },
        "observer_refinement": observer_rows,
        "task_observability": task_rows,
        "same_world_sensor_tradeoff": {
            "actual_initial_state": FlowState(1, 1, 0),
            "exact_goal": "a=1 and b=2; any phase",
            "cases": sensor_rows,
        },
        "resource_pareto": {
            "start": route_start,
            "target": route_target,
            "nondominated_routes": len(routes),
            "routes": routes,
            "resource_profile_choices": resource_choices,
        },
        "viability": {
            "safe_predicate": "a>=1 and b>=1",
            "controlled_kernel_size": len(controlled_kernel),
            "hold_only_kernel_size": len(autonomous_kernel),
            "states_kept_viable_by_control": len(controlled_kernel - autonomous_kernel),
            "viability_policy_action_counts": action_counts,
        },
        "environment_trace_under_hold": env_trace,
        "ground_version_migration": migration,
        "interpretation": {
            "normal_phase_progress_is_not_ground_revision": True,
            "capacity_or_forcing_law_change_is_ground_revision": True,
            "observer_capability_change_is_not_ground_revision": True,
            "resource_budget_change_is_not_ground_revision": True,
            "observer_quotient_requires_transition_congruence_for_memoryless_navigation": True,
            "belief_policies_can_navigate_without_full_state_observation": True,
        },
    }
    (REPORTS / "build_21_results.json").write_text(json.dumps(jsonable(result), indent=2) + "\n")
    (REPORTS / "environment_trace.json").write_text(json.dumps(jsonable(env_trace), indent=2) + "\n")
    migration_rows = []
    for name, entry in migration.items():
        if "directly_migratable_states" in entry:
            migration_rows.append({
                "revision": name,
                "old_version": entry["old_version"],
                "new_version": entry["new_version"],
                "old_state_count": entry["old_state_count"],
                "new_state_count": entry["new_state_count"],
                "directly_migratable_states": entry["directly_migratable_states"],
                "unmappable_states": entry["unmappable_states"],
                "law_changed": entry["law_changed"],
            })
    with (REPORTS / "ground_migration_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(migration_rows[0]))
        w.writeheader(); w.writerows(migration_rows)
    print(json.dumps(jsonable(result), indent=2))

if __name__ == "__main__":
    main()
