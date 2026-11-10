"""Cost-aware active attention for finite predictive Grounds.

The deterministic objective is reduction in unresolved state-pairs under an
observer-relative predictive quotient. This deliberately avoids calling the
score an expectation: probabilistic information gain requires calibrated
likelihoods and priors that this finite reference does not infer.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
from typing import Sequence

from .relational import (
    ContextualQuotient,
    ObserverContext,
    RelationalError,
    contextual_quotient,
)
from .transitions import GroundTransitionSystem


class AttentionError(ValueError):
    """Invalid active-attention candidate, budget, or search request."""


@dataclass(frozen=True, slots=True)
class AttentionCandidate:
    """One observation capability that can be added to an observer.

    kind='action' adds an available probe action.
    kind='channel' reveals one additional output channel.
    cost is a strictly positive relative cost in caller-declared units.
    """

    kind: str
    name: str
    cost: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in ("action", "channel"):
            raise AttentionError("candidate kind must be 'action' or 'channel'")
        if not isinstance(self.name, str) or not self.name:
            raise AttentionError("candidate name must be a non-empty string")
        if isinstance(self.cost, bool) or not isinstance(self.cost, (int, float)):
            raise AttentionError("candidate cost must be a finite positive number")
        cost = float(self.cost)
        if not math.isfinite(cost) or cost <= 0.0:
            raise AttentionError("candidate cost must be a finite positive number")
        object.__setattr__(self, "cost", cost)

    @property
    def key(self) -> tuple[str, str]:
        return self.kind, self.name


@dataclass(frozen=True, slots=True)
class AttentionScore:
    candidate: AttentionCandidate
    unresolved_before: int
    unresolved_after: int
    reduction: int
    gain_per_cost: float
    resulting_class_count: int


@dataclass(frozen=True, slots=True)
class AttentionPlan:
    strategy: str
    horizon: int
    observer: ObserverContext
    selected: tuple[AttentionCandidate, ...]
    total_cost: float
    initial_unresolved_pairs: int
    final_unresolved_pairs: int
    quotient: ContextualQuotient

    @property
    def reduction(self) -> int:
        return self.initial_unresolved_pairs - self.final_unresolved_pairs


def unresolved_pair_count(quotient: ContextualQuotient) -> int:
    """Count state pairs still indistinguishable in a quotient."""
    return sum(len(group) * (len(group) - 1) // 2 for group in quotient.classes)


def _extend_observer(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    candidates: Sequence[AttentionCandidate],
) -> ObserverContext:
    actions = list(observer.actions)
    channels = list(observer.channels)
    for candidate in candidates:
        if candidate.kind == "action":
            if candidate.name not in system.actions:
                raise AttentionError(f"action candidate {candidate.name!r} is not in the Ground")
            if candidate.name in actions:
                raise AttentionError(f"action {candidate.name!r} is already in the observer")
            actions.append(candidate.name)
        else:
            if candidate.name not in system.channels:
                raise AttentionError(f"channel candidate {candidate.name!r} is not in the Ground")
            if candidate.name in channels:
                raise AttentionError(f"channel {candidate.name!r} is already in the observer")
            channels.append(candidate.name)
    return ObserverContext(observer.name, tuple(actions), tuple(channels))


def _validate_candidates(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    candidates: Sequence[AttentionCandidate],
) -> tuple[AttentionCandidate, ...]:
    result = tuple(candidates)
    keys = []
    for candidate in result:
        if not isinstance(candidate, AttentionCandidate):
            raise AttentionError("all candidates must be AttentionCandidate instances")
        keys.append(candidate.key)
    if len(set(keys)) != len(keys):
        raise AttentionError("candidate pool contains duplicate kind/name pairs")
    _extend_observer(system, observer, result)
    return result


def _validate_horizon(horizon: int) -> None:
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise AttentionError("horizon must be a non-negative integer")


def _validate_budget(budget: float) -> float:
    if isinstance(budget, bool) or not isinstance(budget, (int, float)):
        raise AttentionError("budget must be a finite non-negative number")
    value = float(budget)
    if not math.isfinite(value) or value < 0.0:
        raise AttentionError("budget must be a finite non-negative number")
    return value


def _evaluate(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    horizon: int,
) -> tuple[ContextualQuotient, int]:
    quotient = contextual_quotient(system, observer, horizon)
    return quotient, unresolved_pair_count(quotient)


def rank_attention_probes(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    candidates: Sequence[AttentionCandidate],
    horizon: int,
) -> tuple[AttentionScore, ...]:
    """Rank single additional observations by pair ambiguity reduced per cost.

    This is a local score. It intentionally does not assume that the value of
    multiple probes is additive or submodular.
    """
    _validate_horizon(horizon)
    pool = _validate_candidates(system, observer, candidates)
    _, baseline = _evaluate(system, observer, horizon)
    scores = []
    for candidate in pool:
        extended = _extend_observer(system, observer, (candidate,))
        quotient, remaining = _evaluate(system, extended, horizon)
        if remaining > baseline:
            raise AttentionError("adding an observation unexpectedly merged predictive classes")
        reduction = baseline - remaining
        scores.append(AttentionScore(
            candidate=candidate,
            unresolved_before=baseline,
            unresolved_after=remaining,
            reduction=reduction,
            gain_per_cost=reduction / candidate.cost,
            resulting_class_count=quotient.class_count,
        ))
    return tuple(sorted(
        scores,
        key=lambda item: (
            -item.gain_per_cost,
            -item.reduction,
            item.candidate.cost,
            item.candidate.kind,
            item.candidate.name,
        ),
    ))


def greedy_attention_plan(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    candidates: Sequence[AttentionCandidate],
    horizon: int,
    budget: float,
) -> AttentionPlan:
    """Greedily add the best currently informative probe until budget is spent.

    The method stops when every remaining single probe has zero marginal gain.
    Complementary probes that are only useful together can therefore be missed;
    exhaustive_attention_plan is provided as a finite lookahead baseline.
    """
    _validate_horizon(horizon)
    budget = _validate_budget(budget)
    pool = _validate_candidates(system, observer, candidates)
    current = observer
    selected: list[AttentionCandidate] = []
    remaining_candidates = list(pool)
    initial_quotient, initial_ambiguity = _evaluate(system, current, horizon)
    current_quotient, current_ambiguity = initial_quotient, initial_ambiguity
    spent = 0.0

    while remaining_candidates:
        affordable = [
            candidate for candidate in remaining_candidates
            if spent + candidate.cost <= budget + 1e-12
        ]
        if not affordable:
            break
        scores = rank_attention_probes(system, current, affordable, horizon)
        best = scores[0]
        if best.reduction <= 0:
            break
        selected.append(best.candidate)
        current = _extend_observer(system, current, (best.candidate,))
        current_quotient, current_ambiguity = _evaluate(system, current, horizon)
        spent += best.candidate.cost
        remaining_candidates.remove(best.candidate)

    return AttentionPlan(
        "greedy",
        horizon,
        current,
        tuple(selected),
        spent,
        initial_ambiguity,
        current_ambiguity,
        current_quotient,
    )


def exhaustive_attention_plan(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    candidates: Sequence[AttentionCandidate],
    horizon: int,
    budget: float,
    *,
    max_candidates: int = 16,
) -> AttentionPlan:
    """Find the exact best subset under a finite additive probe-cost budget.

    The objective is minimum unresolved state-pair count. Ties prefer lower
    total cost and then deterministic lexical candidate ordering. The search
    enumerates subsets, not action traces. It is intended as a ground-truth
    comparator for small candidate pools, not an unbounded planning algorithm.
    """
    _validate_horizon(horizon)
    budget = _validate_budget(budget)
    pool = _validate_candidates(system, observer, candidates)
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or max_candidates < 0:
        raise AttentionError("max_candidates must be a non-negative integer")
    if len(pool) > max_candidates:
        raise AttentionError(
            f"exact search has {len(pool)} candidates; maximum is {max_candidates}"
        )

    initial_quotient, initial_ambiguity = _evaluate(system, observer, horizon)
    best_key = (initial_ambiguity, 0.0, ())
    best_selected: tuple[AttentionCandidate, ...] = ()
    best_observer = observer
    best_quotient = initial_quotient

    for size in range(1, len(pool) + 1):
        for subset in itertools.combinations(pool, size):
            cost = sum(item.cost for item in subset)
            if cost > budget + 1e-12:
                continue
            extended = _extend_observer(system, observer, subset)
            quotient, ambiguity = _evaluate(system, extended, horizon)
            stable_names = tuple(sorted(item.key for item in subset))
            key = (ambiguity, cost, stable_names)
            if key < best_key:
                best_key = key
                best_selected = tuple(sorted(subset, key=lambda item: item.key))
                # Canonical order for the resulting observer, independent of subset enumeration.
                best_observer = _extend_observer(system, observer, best_selected)
                best_quotient, _ = _evaluate(system, best_observer, horizon)

    return AttentionPlan(
        "exhaustive",
        horizon,
        best_observer,
        best_selected,
        best_key[1],
        initial_ambiguity,
        best_key[0],
        best_quotient,
    )
