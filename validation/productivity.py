"""Productivity benchmarks for Builds 20-23.

These benchmarks compare a generative Virtual Ground to the obvious baselines:
a materialized transition graph, a lookup table of paths, and for Build 23 a
naive explicit transition table.  The point is not to claim a universal win;
it is to make the cost trade observable.
"""
from __future__ import annotations

import math
import statistics

if __package__ in (None, ""):
    from common import gd22_module, gs23_module, vg20_module
else:
    from .common import gd22_module, gs23_module, vg20_module


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def build20_productivity(sample_limit: int = 96) -> dict:
    vg = vg20_module()
    ground = vg.base_ground()
    states = vg.all_states()
    distances, paths = vg.bfs_policy(ground)
    step = max(1, len(states) // max(1, sample_limit))
    sample = states[::step][:sample_limit]
    macro_counts: list[int] = []
    expanded_lengths: list[int] = []
    bfs_lengths: list[int] = []
    for target in sample:
        expanded, macros = vg.factorized_plan(vg.SOLVED, target)
        if vg.apply_named_path(vg.SOLVED, expanded, ground) != target:
            raise AssertionError("factorized plan did not reach target")
        macro_counts.append(sum(bool(exp) for _, exp in macros))
        expanded_lengths.append(len(expanded))
        bfs_lengths.append(distances[target])
    descriptor = vg.ground_descriptor(ground)
    return {
        "state_count": len(states),
        "operation_count": len(ground.moves),
        "descriptor_operation_count": len(descriptor["operations"]),
        "materialized_transition_entries": len(states) * len(ground.moves),
        "lookup_path_entries": len(paths),
        "graph_edge_count": len(vg.graph_edges(ground)),
        "sample_count": len(sample),
        "mean_macro_commands": _mean(macro_counts),
        "max_macro_commands": max(macro_counts) if macro_counts else 0,
        "mean_expanded_length": _mean(expanded_lengths),
        "mean_bfs_length": _mean(bfs_lengths),
        "mean_expanded_to_bfs_ratio": (
            _mean(expanded_lengths) / _mean(bfs_lengths) if bfs_lengths else 0.0
        ),
        "generative_rule_parameters": len(ground.moves) * (vg.N + vg.MOD),
        "interpretation": (
            "Two macro commands compress command count, not primitive expansion "
            "length. The ground avoids storing the materialized transition "
            "table; Build 20's navigator still precomputes a path policy."
        ),
    }


def build22_productivity() -> dict:
    gd = gd22_module()
    candidates = gd.candidate_grounds()
    probes = gd.probe_catalog()
    active = [gd.run_active_identification(h) for h in candidates]
    passive = [gd.run_passive_identification(h, 12) for h in candidates]
    active_probes = [int(x["probe_count"]) for x in active]
    active_costs = [float(x["total_probe_cost"]) for x in active]
    return {
        "candidate_count": len(candidates),
        "probe_catalog_count": len(probes),
        "materialized_observation_entries": len(candidates) * len(probes),
        "active_identified_count": sum(bool(x["identified"]) for x in active),
        "active_probe_count_mean": _mean(active_probes),
        "active_probe_count_max": max(active_probes) if active_probes else 0,
        "active_total_cost_mean": _mean(active_costs),
        "active_total_cost_max": max(active_costs) if active_costs else 0.0,
        "passive_identified_count": sum(bool(x["identified"]) for x in passive),
        "passive_min_remaining_hypotheses": min(
            int(x["remaining_hypotheses"]) for x in passive
        ),
        "interpretation": (
            "Active probing beats passive HOLD for identification inside the "
            "closed 32-model family, at the cost of the probe catalogue."
        ),
    }


def build23_productivity() -> dict:
    gs = gs23_module()
    rows = []
    for ground in gs.ground_catalog():
        train, heldout = gs.make_dataset(ground)
        program = gs.induce_ground(train, max_residue_modulus=4)
        held = gs.evaluate_program(program, heldout)
        coverage = gs.full_domain_coverage(program, ground)
        productivity = gs.program_productivity(program, ground)
        rows.append(
            {
                "ground": ground.name,
                "state_count": coverage["state_count"],
                "heldout_correct": held["correct"],
                "heldout_count": held["count"],
                "transition_coverage": coverage["transition_coverage"],
                "explicit_transition_entries": productivity[
                    "explicit_transition_entries"
                ],
                "program_syntax_cost_units": productivity[
                    "program_syntax_cost_units"
                ],
                "generated_transitions_per_syntax_unit": productivity[
                    "generated_transitions_per_syntax_unit"
                ],
            }
        )
    syntax = [float(x["program_syntax_cost_units"]) for x in rows]
    explicit = [float(x["explicit_transition_entries"]) for x in rows]
    return {
        "grounds": rows,
        "mean_syntax_cost": _mean(syntax),
        "max_syntax_cost": max(syntax) if syntax else 0.0,
        "mean_explicit_entries": _mean(explicit),
        "min_generated_per_syntax_unit": min(
            float(x["generated_transitions_per_syntax_unit"]) for x in rows
        ),
        "interpretation": (
            "Induced programs generate the full finite transition relation from "
            "a compact syntax cost. This is finite-domain compression, not an "
            "asymptotic runtime claim."
        ),
    }


def productivity_summary() -> dict:
    return {
        "build20": build20_productivity(),
        "build22": build22_productivity(),
        "build23": build23_productivity(),
    }


def all_builds_exact() -> bool:
    b20 = build20_productivity()
    b22 = build22_productivity()
    b23 = build23_productivity()
    return (
        b20["graph_edge_count"] == b20["state_count"] * b20["operation_count"]
        and b22["active_identified_count"] == b22["candidate_count"]
        and b22["passive_identified_count"] == 0
        and all(x["transition_coverage"] == 1.0 for x in b23["grounds"])
    )
