"""Compare greedy attention with exact finite probe planning."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vgi.attention import (  # noqa: E402
    AttentionCandidate, exhaustive_attention_plan, greedy_attention_plan,
    rank_attention_probes,
)
from vgi.relational import ObserverContext  # noqa: E402
from vgi.transitions import (  # noqa: E402
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
)


def delayed_six():
    data = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(data)


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


def plan_summary(plan):
    return {
        "strategy": plan.strategy,
        "selected": [
            {"kind": item.kind, "name": item.name, "cost": item.cost}
            for item in plan.selected
        ],
        "total_cost": plan.total_cost,
        "initial_unresolved_pairs": plan.initial_unresolved_pairs,
        "final_unresolved_pairs": plan.final_unresolved_pairs,
        "reduction": plan.reduction,
        "final_class_count": plan.quotient.class_count,
    }


def build_report():
    delayed = delayed_six()
    routine = ObserverContext("routine", ("HOLD", "PROBE_B"), ("channel_0",))
    delayed_candidates = (AttentionCandidate("action", "PROBE_A", 1.0),)
    delayed_scores = rank_attention_probes(delayed, routine, delayed_candidates, 5)
    delayed_greedy = greedy_attention_plan(delayed, routine, delayed_candidates, 5, 1.0)
    delayed_exact = exhaustive_attention_plan(delayed, routine, delayed_candidates, 5, 1.0)

    synergy = complementary_probe_ground()
    initial = ObserverContext("initial", ("A",), ("x",))
    candidates = (
        AttentionCandidate("action", "B", 1.0),
        AttentionCandidate("channel", "y", 1.0),
    )
    scores = rank_attention_probes(synergy, initial, candidates, 1)
    synergy_greedy = greedy_attention_plan(synergy, initial, candidates, 1, 2.0)
    synergy_exact = exhaustive_attention_plan(synergy, initial, candidates, 1, 2.0)

    return {
        "format": "VGI-ActiveAttentionReport-1",
        "objective": (
            "Minimize unresolved state-pair count in a fixed finite predictive "
            "Ground, subject to additive observation cost and a declared horizon."
        ),
        "delayed_six": {
            "candidate_scores": [
                {
                    "kind": item.candidate.kind,
                    "name": item.candidate.name,
                    "reduction": item.reduction,
                    "gain_per_cost": item.gain_per_cost,
                }
                for item in delayed_scores
            ],
            "greedy": plan_summary(delayed_greedy),
            "exhaustive": plan_summary(delayed_exact),
        },
        "complementary_probes": {
            "single_probe_scores": [
                {
                    "kind": item.candidate.kind,
                    "name": item.candidate.name,
                    "reduction": item.reduction,
                }
                for item in scores
            ],
            "greedy": plan_summary(synergy_greedy),
            "exhaustive": plan_summary(synergy_exact),
            "interpretation": (
                "Neither action B nor channel y is informative alone under the "
                "initial observer. Together, they reveal the B-by-y observation "
                "that distinguishes the two predictive contexts."
            ),
        },
        "conclusion": (
            "Single-probe greedy attention is useful when marginal information "
            "is visible, but it is not complete: observation capabilities can "
            "have complementary value. Exact finite lookahead detects this "
            "interaction on the supplied control."
        ),
        "limits": [
            "The objective is deterministic pair separation, not probabilistic expected information gain.",
            "Candidate costs are caller-supplied relative units, not measured energy or latency.",
            "Exact subset search is bounded to a small candidate pool.",
            "All conclusions are relative to the given finite predictive Ground and horizon.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
