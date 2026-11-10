import json

from vgi.inquiry import inquire_unresolved_pairs
from vgi.relational import ObserverContext
from vgi.transitions import GroundTransitionSystem, TransitionObservation, TransitionOutcome


def main():
    ground = GroundTransitionSystem(
        ("p0", "p1"), ("A", "B"), "p0", ("x", "y"),
        (
            TransitionObservation("p0", "A", (TransitionOutcome("p0", (0, 0)),)),
            TransitionObservation("p1", "A", (TransitionOutcome("p1", (0, 0)),)),
            TransitionObservation("p0", "B", (TransitionOutcome("p0", (0, 0)),)),
            TransitionObservation("p1", "B", (TransitionOutcome("p1", (0, 1)),)),
        ),
        {"fixture": "complementary perception witness"},
    )
    observer = ObserverContext("current-view", ("A",), ("x",))
    report = inquire_unresolved_pairs(ground, observer, horizon=1)
    inquiries = []
    for item in report.inquiries:
        witness = item.witness
        inquiries.append({
            "pair": [item.left_state, item.right_state],
            "conclusion": item.conclusion,
            "witness": None if witness is None else {
                "action_word": list(witness.action_word),
                "differing_channels": list(witness.differing_channels),
                "left_output": list(witness.left_output),
                "right_output": list(witness.right_output),
                "newly_required_actions": list(witness.newly_required_actions),
                "newly_required_channels": list(witness.newly_required_channels),
                "required_horizon": witness.required_horizon,
            },
        })
    print(json.dumps({
        "observer": {"actions": list(observer.actions), "channels": list(observer.channels)},
        "unresolved_pair_count": report.unresolved_pair_count,
        "witness_count": report.witness_count,
        "boundary": {
            "declared_actions": list(report.boundary.declared_actions),
            "declared_channels": list(report.boundary.declared_channels),
            "declared_transition_system_complete":
                report.boundary.declared_transition_system_complete,
            "unknown_transition_cells": [list(x) for x in report.boundary.unknown_transition_cells],
            "ambiguous_transition_cells": [list(x) for x in report.boundary.ambiguous_transition_cells],
            "outside_declared_scope": report.boundary.outside_declared_scope,
            "is_open": report.boundary.is_open,
        },
        "inquiries": inquiries,
        "interpretation": (
            "Witnesses are verified against represented transitions. "
            "The finite schema does not enumerate distinctions outside the Ground."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
