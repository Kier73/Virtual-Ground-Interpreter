from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from virtual_ground import (
    SOLVED, VirtualGround, all_states, apply_named_path, apply_transform,
    base_ground, bfs_policy, decode_state, encode_state, factorized_plan,
    graph_edges, ground_descriptor, inverse, observer_view, quotient_bfs,
    quotient_classes, stable_consensus, transform_of_state, compose,
    dijkstra_policy, shortest_plan_between, quotient_plan, GroundNavigator,
)
from partial_ground import PartialGround, enumerate_reachable, level_counts, profile_is_transition_congruent

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def run() -> dict:
    ground = base_ground()
    states = all_states()
    distances, shortest_paths = bfs_policy(ground)
    navigator = GroundNavigator(ground)
    if len(distances) != 648:
        raise AssertionError(f"ground generated {len(distances)} states, expected 648")

    # Coordinate chart: every valid state has one mixed-radix code and back.
    coordinate_roundtrips = all(decode_state(encode_state(s)) == s for s in states)

    # Every primitive edge generated from a state remains within the valid state set.
    edges = graph_edges(ground)

    # Compare a generative factorized plan for every target from the canonical ground.
    all_factorized_lengths = []
    all_macro_counts = []
    all_macro_expansion = []
    all_macro_vs_shortest_differences = 0
    state_catalog = []
    for target in states:
        path, macros = factorized_plan(SOLVED, target)
        if apply_named_path(SOLVED, path, ground) != target:
            raise AssertionError("ground factorization failed to regenerate a target")
        all_factorized_lengths.append(len(path))
        macro_count = sum(bool(expansion) for _, expansion in macros)
        all_macro_counts.append(macro_count)
        all_macro_expansion.append(sum(len(expansion) for _, expansion in macros))
        all_macro_vs_shortest_differences += (len(path) != distances[target])
        state_catalog.append({
            "state_code": encode_state(target),
            "shortest_primitive_distance": distances[target],
            "factorized_primitive_steps": len(path),
            "macro_commands": macro_count,
        })

    # All-pair deterministic sample: shortest path is generated from the relative group element.
    full_lengths = []
    factor_lengths = []
    macro_counts = []
    macro_expansion_counts = []
    pair_records = []
    sample_indices = list(range(0, len(states), 13))[:50]
    for k, ix in enumerate(sample_indices):
        start = states[ix]
        target = states[(ix * 37 + 113) % len(states)]
        # Transform taking start to target in the group, using execution-order composition.
        relative = compose(inverse(transform_of_state(start)), transform_of_state(target), "relative")
        relative_state = apply_transform(SOLVED, relative)
        shortest = distances[relative_state]
        navigator_result = navigator.query(start, target)
        if navigator_result is None:
            raise AssertionError("base group should connect every state pair")
        shortest_path, navigator_cost = navigator_result
        if navigator_cost != shortest:
            raise AssertionError("navigator cost disagrees with exact Cayley distance")
        if apply_named_path(start, shortest_path, ground) != target:
            raise AssertionError("relative shortest path failed")
        path, macros = factorized_plan(start, target)
        reached = apply_named_path(start, path, ground)
        if reached != target:
            raise AssertionError("factorized ground did not reach target")
        full_lengths.append(shortest)
        factor_lengths.append(len(path))
        macro_counts.append(sum(1 for _, expansion in macros if expansion))
        macro_expansion_counts.append(sum(len(expansion) for _, expansion in macros))
        pair_records.append({
            "case": k,
            "start_code": encode_state(start),
            "target_code": encode_state(target),
            "shortest_primitive_steps": shortest,
            "factorized_primitive_steps": len(path),
            "macro_commands": sum(1 for _, expansion in macros if expansion),
            "macro_expansion_steps": sum(len(expansion) for _, expansion in macros),
            "shortest_path": list(shortest_path),
            "factorized_path": list(path),
            "macros": [{"name": n, "expansion": list(e)} for n, e in macros if e],
        })

    # Intention selects the observer quotient and its goal condition.
    layout_target = next(s for s in states if s.perm == SOLVED.perm and s.ori != SOLVED.ori)
    layout_path = quotient_plan(SOLVED, layout_target, ground, "layout")
    full_path = quotient_plan(SOLVED, layout_target, ground, "full")

    # Resource profile changes the preferred operation sequence.
    unit_cost = {m.name: 1.0 for m in ground.moves}
    twist_expensive = {m.name: (4.0 if m.name.startswith("TWIST") else 1.0) for m in ground.moves}
    unit_dist, unit_policy = dijkstra_policy(ground, unit_cost)
    weighted_dist, weighted_policy = dijkstra_policy(ground, twist_expensive)
    cost_sensitive_example = next(
        s for s in states if unit_policy[s] != weighted_policy[s]
    )

    # Observer quotients: each is an intentional loss of distinctions.
    observer_counts = {
        name: len(quotient_classes(states, name))
        for name in ("full", "layout", "orientation")
    }
    quotient_reachability = {}
    for name in ("full", "layout", "orientation"):
        qdist = quotient_bfs(ground, SOLVED, name)
        quotient_reachability[name] = {
            "class_count": len(qdist),
            "max_distance": max(qdist.values()),
        }

    # A layout observer cannot distinguish states with identical piece placement
    # but different orientations. It is sufficient only for layout intentions.
    same_layout = next(
        (a, b) for a in states for b in states
        if a.perm == b.perm and a.ori != b.ori
    )
    layout_collapses_orientation = observer_view(same_layout[0], "layout") == observer_view(same_layout[1], "layout")
    full_distinguishes_orientation = observer_view(same_layout[0], "full") != observer_view(same_layout[1], "full")

    # Consensus is a stable observed value, not a metaphysical proof of truth.
    consensus_examples = {
        "stable": stable_consensus([(1, 2), (1, 2), (1, 2), (3, 4)], 3)[0],
        "unstable": stable_consensus([(1, 2), (1, 2), (3, 4), (1, 2)], 3)[0],
    }

    # Ground shift: remove orientation-changing operations. Layout remains
    # navigable, but most full states cease to be reachable from SOLVED.
    locked = ground.revise_without_twists()
    locked_dist, _ = bfs_policy(locked)

    # Companion Jenga-like support logic: partial, state-dependent, irreversible actions.
    support_ground = PartialGround()
    support_distances, support_parents, support_edges = enumerate_reachable(support_ground)
    revised_support_ground = support_ground.revise_support(6, (3,))
    revised_support_distances, _, revised_support_edges = enumerate_reachable(revised_support_ground)
    support_stable_masks = {mask for mask in range(512) if support_ground.stable(mask)}
    revised_support_stable_masks = {mask for mask in range(512) if revised_support_ground.stable(mask)}
    support_witness = None
    support_buckets = {}
    for mask in support_distances:
        support_buckets.setdefault(level_counts(mask), []).append(mask)
    for profile, group in support_buckets.items():
        reference_actions = set(support_ground.legal_actions(group[0]))
        for candidate in group[1:]:
            candidate_actions = set(support_ground.legal_actions(candidate))
            if candidate_actions != reference_actions:
                support_witness = {
                    "level_counts": list(profile),
                    "state_a_mask": group[0],
                    "state_a_legal_actions": sorted(reference_actions),
                    "state_b_mask": candidate,
                    "state_b_legal_actions": sorted(candidate_actions),
                }
                break
        if support_witness:
            break

    # Inverse and composition checks over a deterministic sample.
    inverse_checks = 0
    composition_checks = 0
    moves = ground.moves
    for op in moves:
        assert apply_transform(apply_transform(SOLVED, op), inverse(op)) == SOLVED
        inverse_checks += 1
    for i in range(0, len(moves), 2):
        a, b, c = moves[i], moves[(i + 1) % len(moves)], moves[(i + 2) % len(moves)]
        left = compose(compose(a, b), c)
        right = compose(a, compose(b, c))
        assert (left.dest, left.twist) == (right.dest, right.twist)
        composition_checks += 1

    # Compare serialization footprints. These are JSON payload byte counts,
    # not Python heap usage or a universal compression benchmark.
    descriptor_payload = json.dumps(ground_descriptor(ground), separators=(",", ":")).encode("utf-8")
    coordinate_schema_payload = json.dumps({
        "permutation": "Lehmer rank 0..23",
        "orientation": "three base-3 digits 0..26; fourth implied by zero-sum invariant",
        "address": "permutation_rank * 27 + orientation_rank",
    }, separators=(",", ":")).encode("utf-8")
    macro_schema_payload = json.dumps({
        "SET_LAYOUT": "parameterized target permutation; expanded by adjacent swaps",
        "SET_ORIENTATION": "parameterized target orientation; expanded by pair twists",
    }, separators=(",", ":")).encode("utf-8")
    policy_payload = json.dumps([
        {"state": encode_state(s), "distance": distances[s], "path": shortest_paths[s]}
        for s in states
    ], separators=(",", ":")).encode("utf-8")
    edge_payload = json.dumps([
        {"s": encode_state(s), "a": op.name, "t": encode_state(apply_transform(s, op))}
        for s in states for op in ground.moves
    ], separators=(",", ":")).encode("utf-8")

    report = {
        "status": "complete",
        "provenance": "synthetic finite algebraic fixture; no physical puzzle or sensor was measured",
        "virtual_ground": ground_descriptor(ground),
        "state_space": {
            "valid_states": len(states),
            "reachable_states_from_solved": len(distances),
            "directed_edges": len(edges),
            "group_order_expected": "4! * 3^3 = 648",
            "graph_diameter": max(distances.values()),
            "coordinate_bijection_verified": coordinate_roundtrips,
        },
        "navigation": {
            "all_targets_from_solved": {
                "target_count": len(states),
                "mean_exact_shortest_primitive_steps": statistics.mean(distances.values()),
                "mean_factorized_primitive_steps": statistics.mean(all_factorized_lengths),
                "mean_macro_commands": statistics.mean(all_macro_counts),
                "mean_macro_expansion_steps": statistics.mean(all_macro_expansion),
                "factorized_path_differs_from_shortest_for_targets": all_macro_vs_shortest_differences,
                "factorized_paths_reach_every_target": True,
            },
            "sampled_start_target_pairs": len(sample_indices),
            "mean_exact_shortest_primitive_steps": statistics.mean(full_lengths),
            "mean_factorized_primitive_steps": statistics.mean(factor_lengths),
            "mean_macro_commands": statistics.mean(macro_counts),
            "max_macro_commands": max(macro_counts),
            "mean_macro_expansion_steps": statistics.mean(macro_expansion_counts),
            "factorized_paths_all_reach_target": True,
            "factorized_paths_are_not_claimed_shortest": True,
            "intention_example": {
                "target_code": encode_state(layout_target),
                "same_layout_as_solved": True,
                "same_full_state_as_solved": False,
                "layout_quotient_plan": list(layout_path or ()),
                "full_state_plan_primitive_steps": len(full_path or ()),
            },
            "resource_weighting_example": {
                "target_code": encode_state(cost_sensitive_example),
                "unit_cost_plan": list(unit_policy[cost_sensitive_example]),
                "unit_cost": unit_dist[cost_sensitive_example],
                "twists_cost_four_plan": list(weighted_policy[cost_sensitive_example]),
                "twists_cost_four_total": weighted_dist[cost_sensitive_example],
                "purpose": "same ground, different observer/resource cost profile, different optimal navigation",
            },
        },
        "observer_quotients": {
            "class_counts": observer_counts,
            "reachable_quotient_classes": quotient_reachability,
            "layout_observer_collapses_orientation": layout_collapses_orientation,
            "full_observer_distinguishes_orientation": full_distinguishes_orientation,
            "task_note": "layout-only observation is sufficient for layout goals, not exact full-state goals",
        },
        "consensus": {
            "definition": "observer value retained for a configured number of consecutive samples",
            "examples": consensus_examples,
            "not_claimed": "stable observation does not prove external truth or permanence",
        },
        "ground_shift": {
            "new_version": locked.version,
            "new_operation_count": len(locked.moves),
            "reachable_from_solved_after_orientation_lock": len(locked_dist),
            "old_reachable_count": len(distances),
            "interpretation": "changing legal operations changes the generative ground, not merely the state coordinate",
        },
        "partial_irreversible_ground": {
            "model": "symbolic nine-block support graph; not a physical mechanics simulation",
            "initial_state_mask": 511,
            "reachable_stable_states": len(support_distances),
            "all_stable_masks": len(support_stable_masks),
            "every_stable_mask_reachable": set(support_distances) == support_stable_masks,
            "directed_removal_edges": len(support_edges),
            "max_removal_depth": max(support_distances.values()),
            "terminal_states": sum(not support_ground.legal_actions(s) for s in support_distances),
            "all_transitions_remove_exactly_one_block": all((after.bit_count() == before.bit_count() - 1) for before, _, after in support_edges),
            "level_count_observer_is_transition_congruent": profile_is_transition_congruent(support_ground, tuple(support_distances)),
            "same_profile_different_legal_actions_witness": support_witness,
            "revised_support_ground_version": revised_support_ground.version,
            "revised_reachable_states": len(revised_support_distances),
            "revised_all_stable_masks": len(revised_support_stable_masks),
            "every_revised_stable_mask_reachable": set(revised_support_distances) == revised_support_stable_masks,
            "revised_edges": len(revised_support_edges),
            "interpretation": "partial irreversible logic needs state-dependent legality; coarse height/count observations can be insufficient",
        },
        "algebra_checks": {
            "primitive_inverse_checks": inverse_checks,
            "composition_associativity_checks": composition_checks,
            "all_primitive_moves_preserve_orientation_sum": True,
        },
        "representation_storage": {
            "measurement": "serialized JSON payload bytes; excludes runtime objects and executable code",
            "primitive_ground_descriptor_bytes": len(descriptor_payload),
            "coordinate_chart_schema_bytes": len(coordinate_schema_payload),
            "macro_schema_bytes": len(macro_schema_payload),
            "materialized_graph_payload_bytes": len(edge_payload),
            "shortest_policy_payload_bytes": len(policy_payload),
            "interpretation": "procedural rules are compact relative to expanded state/edge/policy tables in this fixture; storage does not measure total compute cost",
        },
        "representation_tradeoffs": {
            "primitive_generator_count": len(ground.moves),
            "coordinate_addresses": len(states),
            "explicit_graph_edges": len(edges),
            "observer_class_counts": observer_counts,
            "macro_stages": ["SET_LAYOUT", "SET_ORIENTATION"],
            "interpretation": "different operational views trade retained detail, planning work, storage and command depth",
        },
        "cost_model": {
            "primitive_steps": "count of low-level legal state transitions",
            "macro_commands": "number of high-level procedural commands; each has a primitive expansion",
            "planning_work": "state expansions required by exact search; separate from action count",
            "constant_time_claim": "not established; fixed-state indexing is constant-size arithmetic only for this fixed four-piece system",
        },
        "sampled_pairs": pair_records,
    }
    (REPORTS / "build_20_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    import csv
    with (REPORTS / "state_navigation_catalog.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["state_code", "shortest_primitive_distance", "factorized_primitive_steps", "macro_commands"])
        writer.writeheader()
        writer.writerows(state_catalog)
    graph_rows = [
        {"source": encode_state(s), "operation": op.name, "target": encode_state(apply_transform(s, op))}
        for s in states for op in ground.moves
    ]
    (REPORTS / "materialized_transition_graph.json").write_bytes(edge_payload)
    (REPORTS / "shortest_policy_table.json").write_bytes(policy_payload)
    (REPORTS / "ground_descriptor.json").write_bytes(descriptor_payload)
    (REPORTS / "support_ground_results.json").write_text(json.dumps({
        "base": {
            "ground": support_ground.name,
            "version": support_ground.version,
            "stable_masks": len(support_stable_masks),
            "reachable_masks": len(support_distances),
            "every_stable_mask_reachable": set(support_distances) == support_stable_masks,
            "edges": len(support_edges),
            "max_depth": max(support_distances.values()),
        },
        "revised": {
            "ground": revised_support_ground.name,
            "version": revised_support_ground.version,
            "stable_masks": len(revised_support_stable_masks),
            "reachable_masks": len(revised_support_distances),
            "every_stable_mask_reachable": set(revised_support_distances) == revised_support_stable_masks,
            "edges": len(revised_support_edges),
            "max_depth": max(revised_support_distances.values()),
        },
        "observer_witness": support_witness,
        "provenance": "symbolic fixture only, not physical mechanics",
    }, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({
        "status": result["status"],
        "states": result["state_space"]["valid_states"],
        "edges": result["state_space"]["directed_edges"],
        "diameter": result["state_space"]["graph_diameter"],
        "mean_shortest_all_targets": result["navigation"]["all_targets_from_solved"]["mean_exact_shortest_primitive_steps"],
        "mean_factorized_all_targets": result["navigation"]["all_targets_from_solved"]["mean_factorized_primitive_steps"],
        "mean_macro_commands_all_targets": result["navigation"]["all_targets_from_solved"]["mean_macro_commands"],
        "locked_reachable": result["ground_shift"]["reachable_from_solved_after_orientation_lock"],
        "support_states": result["partial_irreversible_ground"]["reachable_stable_states"],
        "support_revised_states": result["partial_irreversible_ground"]["revised_reachable_states"],
    }, indent=2))
