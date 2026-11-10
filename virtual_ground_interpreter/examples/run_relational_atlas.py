"""Run the finite observer-relative relational-atlas experiment.

From this package directory:
    python examples/run_relational_atlas.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vgi.relational import (  # noqa: E402
    ObserverContext, behavioral_distance, quotient_map, quotient_transition_table,
    refinement_series,
)
from vgi.transitions import (  # noqa: E402
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
)


def delayed_six() -> GroundTransitionSystem:
    source = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(source)


def cyclic_recurrence() -> GroundTransitionSystem:
    states = ("c0", "c1", "c2", "c3")
    observations = tuple(
        TransitionObservation(
            state, "STEP",
            (TransitionOutcome(states[(index + 1) % 4], (index,)),),
        )
        for index, state in enumerate(states)
    )
    return GroundTransitionSystem(
        states, ("STEP",), "c0", ("phase",), observations,
        {"family": "cyclic recurrence", "modulus": 4},
    )


def non_bijective_automaton() -> GroundTransitionSystem:
    states = ("left", "right", "sink")
    detail = {"left": 0, "right": 1, "sink": 2}
    observations = tuple(
        TransitionObservation(
            state, "ERASE",
            (TransitionOutcome("sink", (0, detail[state])),),
        )
        for state in states
    )
    return GroundTransitionSystem(
        states, ("ERASE",), "left", ("coarse", "detail"), observations,
        {"family": "non-bijective automaton"},
    )


def summarize(system, observer, max_horizon: int) -> dict:
    series = refinement_series(system, observer, max_horizon)
    stable = next((item.horizon for item in series if item.stable), None)
    return {
        "observer": observer.name,
        "actions": list(observer.actions),
        "channels": list(observer.channels),
        "horizons": [item.horizon for item in series],
        "class_counts": [item.class_count for item in series],
        "stable_horizon": stable,
        "classes_at_last_horizon": [list(group) for group in series[-1].classes],
    }


def build_report() -> dict:
    delayed = delayed_six()
    full = ObserverContext.full(delayed, "all-actions-and-output")
    routine = ObserverContext("without-PROBE_A", ("HOLD", "PROBE_B"), ("channel_0",))
    delayed_series = refinement_series(delayed, full, 8)
    q4, q3 = delayed_series[4], delayed_series[3]
    delayed_map = quotient_map(q4, q3)
    delayed_edges = quotient_transition_table(delayed, q4, q3)

    cycle = cyclic_recurrence()
    cycle_blind = ObserverContext("no-phase-observation", ("STEP",), ())
    cycle_phase = ObserverContext("phase-observation", ("STEP",), ("phase",))

    automaton = non_bijective_automaton()
    coarse = ObserverContext("coarse-channel", ("ERASE",), ("coarse",))
    detail = ObserverContext("detail-channel", ("ERASE",), ("detail",))

    return {
        "format": "VGI-RelationalAtlasReport-1",
        "scope": (
            "Finite deterministic predictive contexts under declared action and "
            "channel projections; not a claim about physical hidden-state identity."
        ),
        "delayed_six": {
            "full_observer": summarize(delayed, full, 8),
            "restricted_observer": summarize(delayed, routine, 8),
            "q4_to_q3_class_map_size": len(delayed_map),
            "q4_to_q3_transition_edges": len(delayed_edges),
            "q0_q1_distance_horizon_4": behavioral_distance(delayed, full, "q0", "q1", 4),
            "q0_q1_distance_horizon_5": behavioral_distance(delayed, full, "q0", "q1", 5),
            "restricted_q0_q1_distance_horizon_5": behavioral_distance(
                delayed, routine, "q0", "q1", 5
            ),
        },
        "cyclic_recurrence": {
            "observer_without_phase": summarize(cycle, cycle_blind, 6),
            "observer_with_phase": summarize(cycle, cycle_phase, 6),
        },
        "non_bijective_automaton": {
            "coarse_observer": summarize(automaton, coarse, 3),
            "detail_observer": summarize(automaton, detail, 3),
        },
        "interpretation": [
            "A restricted observer may leave distinct predictive contexts equivalent.",
            "A new action or channel can split an existing equivalence class.",
            "Increasing horizon reveals delayed distinctions without enumerating every action trace.",
            "The same finite machine can induce different valid quotients under different observers.",
            "The distance is a profile parameterized by observer, action weights, horizon, and discount.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
