"""Run the three-valued partial predictive-relation experiment.

From this package directory:
    python examples/run_partial_predictive_relations.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vgi.relational import (  # noqa: E402
    ObserverContext,
    partial_refinement_series,
)
from vgi.transitions import (  # noqa: E402
    GroundTransitionSystem,
    TransitionObservation,
    TransitionOutcome,
)


def delayed_six() -> GroundTransitionSystem:
    source = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(source)


def partial_cycle() -> GroundTransitionSystem:
    # A has been observed. B has not. The two states are equivalent under A
    # alone, but a full A/B observer cannot claim equivalence yet.
    return GroundTransitionSystem(
        states=("p0", "p1"),
        actions=("A", "B"),
        initial_state="p0",
        channels=("y",),
        observations=(
            TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),
            TransitionObservation("p1", "A", (TransitionOutcome("p0", (0,)),)),
        ),
        metadata={"fixture": "partial-cycle", "B": "not-yet-observed"},
    )


def summarize(system, observer, horizon: int) -> dict:
    comparisons = partial_refinement_series(system, observer, horizon)
    last = comparisons[-1]
    pairs = []
    for left_index, left in enumerate(system.states):
        for right in system.states[left_index + 1:]:
            pairs.append({
                "left": left,
                "right": right,
                "status": last.status(left, right),
                "witness": list(last.witness(left, right) or ()),
                "blockers": [
                    {
                        "action": item.action,
                        "reason": item.reason,
                        "left_edge_status": item.left_edge_status,
                        "right_edge_status": item.right_edge_status,
                        "successor_status": item.successor_status,
                    }
                    for item in last.blockers(left, right)
                ],
            })
    return {
        "observer": observer.name,
        "horizons": [item.horizon for item in comparisons],
        "pair_statuses": pairs,
    }


def build_report() -> dict:
    delayed = delayed_six()
    full = ObserverContext.full(delayed, "full")
    no_probe = ObserverContext("no-PROBE_A", ("HOLD", "PROBE_B"), ("channel_0",))
    target = ObserverContext("PROBE_A-only", ("PROBE_A",), ("channel_0",))

    partial = partial_cycle()
    all_partial_actions = ObserverContext("A-and-B", ("A", "B"), ("y",))
    observed_a_only = ObserverContext("A-only", ("A",), ("y",))

    full_series = partial_refinement_series(delayed, full, 5)
    return {
        "format": "VGI-PartialPredictiveRelationReport-1",
        "scope": (
            "Finite observer-relative predictive comparison. Unknown and ambiguous "
            "edges remain blockers; this is not a physical hidden-state claim."
        ),
        "build24_delayed_six": {
            "q0_q1_horizon_4": full_series[4].status("q0", "q1"),
            "q0_q1_horizon_5": full_series[5].status("q0", "q1"),
            "q0_q1_witness": list(full_series[5].witness("q0", "q1") or ()),
            "restricted_q0_q5": summarize(delayed, no_probe, 8),
            "targeted_q0_q5": summarize(delayed, target, 1),
        },
        "partial_ground": {
            "full_observer": summarize(partial, all_partial_actions, 3),
            "A_only_observer": summarize(partial, observed_a_only, 3),
        },
        "interpretation": [
            "Equivalent is a bounded claim under one Ground version and observer.",
            "Distinguishable requires a concrete word of known singleton transitions.",
            "Unresolved is neither equivalent nor distinguishable.",
            "Unknown, ambiguous, and unresolved-successor blockers remain separately inspectable.",
            "New evidence is evaluated as a new Ground version; old comparison objects remain unchanged.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
