"""Run the joint observer-configuration / predictive-quotient search."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vgi.attention import (  # noqa: E402
    AttentionCandidate, exhaustive_attention_plan, greedy_attention_plan,
)
from vgi.joint_attention import beam_attention_plan  # noqa: E402
from vgi.relational import ObserverContext  # noqa: E402
from vgi.transitions import (  # noqa: E402
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
)


def delayed_six():
    source = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(source)


def complementary_probe_ground():
    states = ("p0", "p1")
    observations = (
        TransitionObservation("p0", "A", (TransitionOutcome("p0", (0, 0)),)),
        TransitionObservation("p1", "A", (TransitionOutcome("p1", (0, 0)),)),
        TransitionObservation("p0", "B", (TransitionOutcome("p0", (0, 0)),)),
        TransitionObservation("p1", "B", (TransitionOutcome("p1", (0, 1)),)),
    )
    return GroundTransitionSystem(
        states, ("A", "B"), "p0", ("x", "y"), observations,
        {"family": "complementary observation fixture"},
    )


def summarize(plan):
    return {
        "selected": [
            {"kind": item.kind, "name": item.name, "cost": item.cost}
            for item in plan.selected
        ],
        "total_cost": plan.total_cost,
        "unresolved_pairs": {
            "initial": plan.initial_unresolved_pairs,
            "final": plan.final_unresolved_pairs,
            "reduction": plan.reduction,
        },
        "final_observer": {
            "actions": list(plan.observer.actions),
            "channels": list(plan.observer.channels),
        },
        "final_predictive_quotient": {
            "class_count": plan.quotient.class_count,
            "classes": [list(group) for group in plan.quotient.classes],
        },
    }


def report_joint(plan):
    return {
        **summarize(plan),
        "search": {
            "beam_width": plan.beam_width,
            "max_depth": plan.max_depth,
            "visited_configurations": plan.visited_configurations,
            "expanded_nodes": plan.expanded_nodes,
            "termination_reason": plan.termination_reason,
        },
        "perception_to_prediction_route": [
            {
                "step": item.index,
                "added_capability": {"kind": item.candidate.kind, "name": item.candidate.name},
                "observer": {"actions": list(item.actions), "channels": list(item.channels)},
                "predictive_quotient": {
                    "class_count": item.class_count,
                    "unresolved_before": item.unresolved_before,
                    "unresolved_after": item.unresolved_after,
                },
                "cumulative_cost": item.cumulative_cost,
            }
            for item in plan.route
        ],
        "search_records": [
            {
                "depth": item.depth,
                "selected": [candidate.key for candidate in item.selected],
                "observer_actions": list(item.actions),
                "observer_channels": list(item.channels),
                "cost": item.total_cost,
                "unresolved_pairs": item.unresolved_pairs,
                "class_count": item.class_count,
                "retained": item.retained_in_beam,
            }
            for item in plan.search_records
        ],
    }


def build_report():
    system = complementary_probe_ground()
    observer = ObserverContext("initial", ("A",), ("x",))
    candidates = (
        AttentionCandidate("action", "B", 1.0),
        AttentionCandidate("channel", "y", 1.0),
    )
    greedy = greedy_attention_plan(system, observer, candidates, 1, 2.0)
    exact = exhaustive_attention_plan(system, observer, candidates, 1, 2.0)
    joint = beam_attention_plan(
        system, observer, candidates, 1, 2.0, beam_width=2, max_depth=2
    )

    delayed = delayed_six()
    delayed_observer = ObserverContext("routine", ("HOLD", "PROBE_B"), ("channel_0",))
    delayed_candidate = (AttentionCandidate("action", "PROBE_A", 1.0),)
    delayed_joint = beam_attention_plan(
        delayed, delayed_observer, delayed_candidate, 5, 1.0,
        beam_width=2, max_depth=2,
    )

    return {
        "format": "VGI-JointPerceptionNavigationReport-1",
        "model": {
            "perception_space": "observer configurations: selected action probes and output channels",
            "predictive_space": "horizon-indexed quotient classes induced by each observer configuration",
            "navigation_edge": "add one affordable observation capability and recompute the induced quotient",
        },
        "complementary_probe_fixture": {
            "greedy": summarize(greedy),
            "exhaustive": summarize(exact),
            "joint_beam": report_joint(joint),
            "finding": (
                "The search retains both one-step observer configurations despite zero "
                "immediate reduction, then follows their complementary route to a fully "
                "separating predictive quotient."
            ),
        },
        "delayed_six_control": {
            "joint_beam": report_joint(delayed_joint),
            "finding": "The joint planner also preserves the direct single-probe path.",
        },
        "limits": [
            "The beam search is bounded and can prune a useful configuration.",
            "The search space is a finite subset lattice over caller-supplied observation capabilities.",
            "The predictive quotient is relative to the declared deterministic Ground and horizon.",
            "Candidate costs are declared relative units, not measured latency or energy.",
            "No probabilistic expectation or physical hidden-state interpretation is inferred.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
