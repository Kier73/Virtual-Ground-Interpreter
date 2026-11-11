"""Cell-specific counterfactual attention for incomplete transition Grounds."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence
from .relational import ObserverContext
from .sparse import sparse_partial_contextual_comparison
from .transitions import GroundTransitionSystem, TransitionObservation, TransitionOutcome

class PartialAttentionError(ValueError):
    """Invalid partial-attention request or scenario model."""

@dataclass(frozen=True, slots=True)
class ProbeScenario:
    outcome: TransitionOutcome
    weight: Fraction | None = None
    def __post_init__(self):
        if not isinstance(self.outcome, TransitionOutcome):
            raise PartialAttentionError("scenario outcome must be a TransitionOutcome")
        if self.weight is not None:
            if isinstance(self.weight, float) or isinstance(self.weight, bool):
                raise PartialAttentionError("scenario weight must be an exact Fraction or integer")
            weight = Fraction(self.weight)
            if weight <= 0:
                raise PartialAttentionError("scenario weight must be positive")
            object.__setattr__(self, "weight", weight)

@dataclass(frozen=True, slots=True)
class TransitionProbe:
    state: str
    action: str
    scenarios: tuple[ProbeScenario, ...]
    cost: Fraction = Fraction(1, 1)
    label: str = ""
    def __post_init__(self):
        scenarios = tuple(self.scenarios)
        if not isinstance(self.state, str) or not self.state or not isinstance(self.action, str) or not self.action:
            raise PartialAttentionError("probe state and action must be non-empty strings")
        if not scenarios or any(not isinstance(x, ProbeScenario) for x in scenarios):
            raise PartialAttentionError("probe requires at least one scenario")
        if len({x.outcome for x in scenarios}) != len(scenarios):
            raise PartialAttentionError("probe scenarios must have distinct outcomes")
        weights = tuple(x.weight for x in scenarios)
        if any(x is None for x in weights) and any(x is not None for x in weights):
            raise PartialAttentionError("weights must be supplied for every scenario or none")
        if all(x is not None for x in weights) and sum(weights, Fraction(0)) != 1:
            raise PartialAttentionError("scenario weights must sum exactly to one")
        if isinstance(self.cost, float) or isinstance(self.cost, bool):
            raise PartialAttentionError("probe cost must be an exact Fraction or integer")
        cost = Fraction(self.cost)
        if cost <= 0:
            raise PartialAttentionError("probe cost must be positive")
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(self, "cost", cost)

@dataclass(frozen=True, slots=True)
class ProbeScenarioScore:
    outcome: TransitionOutcome
    weight: Fraction | None
    unresolved_before: int
    unresolved_after: int
    resolved_pairs: int
    new_distinguishing_witnesses: int

@dataclass(frozen=True, slots=True)
class PartialProbeScore:
    probe: TransitionProbe
    affected_pairs: int
    scenario_scores: tuple[ProbeScenarioScore, ...]
    minimum_resolved_pairs: int
    maximum_resolved_pairs: int
    expected_resolved_pairs: Fraction | None
    expected_gain_per_cost: Fraction | None
    @property
    def estimation_kind(self):
        return "exact_expectation" if self.expected_resolved_pairs is not None else "scenario_bounds_only"


def _counterfactual_system(system, probe, outcome):
    observations = [
        item for item in system.observations
        if (item.source, item.action) != (probe.state, probe.action)
    ]
    observations.append(TransitionObservation(
        probe.state, probe.action, (outcome,), support_count=1,
        evidence=("counterfactual-probe-scenario",),
    ))
    metadata = dict(system.metadata)
    metadata["vgi_counterfactual_probe"] = {
        "state": probe.state, "action": probe.action, "label": probe.label,
    }
    return GroundTransitionSystem(
        system.states, system.actions, system.initial_state, system.channels,
        tuple(observations), metadata,
    )


def score_partial_probe(system, observer, probe, horizon):
    """Score one missing/ambiguous cell by re-evaluating only affected state pairs.

    Replacing one (state, action) cell can affect only pairs containing state.
    The score is therefore O(K*H*S*A), rather than recounting all S^2 pairs for
    every scenario. No probability is inferred: expected value is returned only
    when the caller provides an exact complete scenario distribution.
    """
    if not isinstance(system, GroundTransitionSystem) or not isinstance(observer, ObserverContext):
        raise PartialAttentionError("system and observer have invalid types")
    if not isinstance(probe, TransitionProbe):
        raise PartialAttentionError("probe must be a TransitionProbe")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise PartialAttentionError("horizon must be a non-negative integer")
    observer.validate(system)
    if probe.state not in system.states or probe.action not in system.actions:
        raise PartialAttentionError("probe cell is outside the Ground schema")
    if probe.action not in observer.actions:
        raise PartialAttentionError("probe action is not visible to the observer")
    if system.status(probe.state, probe.action) == "known":
        raise PartialAttentionError("only unknown or ambiguous cells qualify")
    for scenario in probe.scenarios:
        if scenario.outcome.target not in system.states:
            raise PartialAttentionError("scenario target is outside the Ground")
        if len(scenario.outcome.output) != len(system.channels):
            raise PartialAttentionError("scenario output width does not match Ground channels")

    before = sparse_partial_contextual_comparison(system, observer, horizon)
    others = tuple(state for state in system.states if state != probe.state)
    baseline = {state: before.status(probe.state, state) for state in others}
    unresolved_before = sum(value == "unresolved" for value in baseline.values())
    scores = []
    for scenario in probe.scenarios:
        hypothetical = _counterfactual_system(system, probe, scenario.outcome)
        after = sparse_partial_contextual_comparison(hypothetical, observer, horizon)
        new = {state: after.status(probe.state, state) for state in others}
        unresolved_after = sum(value == "unresolved" for value in new.values())
        resolved = sum(
            baseline[state] == "unresolved" and new[state] != "unresolved"
            for state in others
        )
        witnesses = sum(
            baseline[state] == "unresolved" and new[state] == "distinguishable"
            for state in others
        )
        scores.append(ProbeScenarioScore(
            scenario.outcome, scenario.weight, unresolved_before,
            unresolved_after, resolved, witnesses,
        ))
    weighted = all(item.weight is not None for item in probe.scenarios)
    expected = (
        sum((score.resolved_pairs * score.weight for score in scores), Fraction(0))
        if weighted else None
    )
    return PartialProbeScore(
        probe, len(others), tuple(scores),
        min(item.resolved_pairs for item in scores),
        max(item.resolved_pairs for item in scores),
        expected, expected / probe.cost if expected is not None else None,
    )


def rank_partial_probes(system, observer, probes: Sequence[TransitionProbe], horizon: int):
    """Rank calibrated expectations first, otherwise robust scenario bounds."""
    scores = tuple(score_partial_probe(system, observer, probe, horizon) for probe in probes)
    return tuple(sorted(scores, key=lambda item: (
        item.expected_gain_per_cost is None,
        -(item.expected_gain_per_cost or Fraction(0)),
        -item.minimum_resolved_pairs,
        -item.maximum_resolved_pairs,
        item.probe.cost, item.probe.state, item.probe.action,
    )))


__all__ = [
    "PartialAttentionError", "ProbeScenario", "TransitionProbe",
    "ProbeScenarioScore", "PartialProbeScore", "score_partial_probe",
    "rank_partial_probes",
]
