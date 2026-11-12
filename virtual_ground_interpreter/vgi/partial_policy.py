"""Finite minimax policy trees for cell-specific partial transition probes.

The solver explores only a caller-supplied finite candidate set. A selected
probe branches over its declared counterfactual outcomes; every branch must be
handled. The objective is lexicographic:

1. minimize the worst-branch unresolved-pair count at the declared horizon;
2. minimize exact worst-branch cumulative probe cost;
3. minimize the maximum number of probes on any branch;
4. break ties deterministically.

Scenario weights, when present, are retained as metadata but are never used by
this worst-case objective. The result is optimal only over the supplied
candidate definitions and their declared scenario sets. Those sets are not
asserted to be physically exhaustive or probabilistically calibrated.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping, Optional, Sequence

from .partial_attention import (
    PartialAttentionError,
    ProbeScenario,
    TransitionProbe,
    counterfactual_probe_ground,
)
from .relational import ObserverContext
from .sparse import sparse_partial_contextual_comparison
from .transitions import GroundTransitionSystem, TransitionOutcome


class PartialProbePolicyError(ValueError):
    """Invalid partial-probe policy request or exceeded exact-search bound."""


def _fraction(value: object, label: str, *, allow_zero: bool = False) -> Optional[Fraction]:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise PartialProbePolicyError(f"{label} must be an exact integer or Fraction")
    try:
        result = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise PartialProbePolicyError(f"{label} must be an exact rational") from exc
    if result < 0 or (result == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise PartialProbePolicyError(f"{label} must be {qualifier}")
    return result


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PartialProbePolicyError(f"{label} must be a positive integer")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PartialProbePolicyError(f"{label} must be a non-negative integer")
    return value


def _outcome_key(outcome: TransitionOutcome) -> tuple:
    return outcome.target, tuple(outcome.output)


def _fraction_record(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _probe_key(probe: TransitionProbe) -> tuple:
    """Stable policy identity; scenario weights do not affect minimax semantics."""
    if not isinstance(probe.label, str):
        raise PartialProbePolicyError("probe label must be text")
    outcomes = tuple(sorted(
        (_outcome_key(item.outcome) for item in probe.scenarios)
    ))
    return (
        probe.state,
        probe.action,
        probe.label,
        probe.cost.numerator,
        probe.cost.denominator,
        outcomes,
    )


def _probe_record(probe: TransitionProbe) -> dict[str, Any]:
    return {
        "state": probe.state,
        "action": probe.action,
        "label": probe.label,
        "cost": _fraction_record(probe.cost),
        "scenarios": [
            {
                "outcome": {
                    "target": scenario.outcome.target,
                    "output": list(scenario.outcome.output),
                },
                "weight": (
                    None if scenario.weight is None
                    else _fraction_record(Fraction(scenario.weight))
                ),
                "weight_role": "metadata_only_not_used_by_worst_case_objective",
            }
            for scenario in sorted(probe.scenarios, key=lambda item: _outcome_key(item.outcome))
        ],
    }


@dataclass(frozen=True, slots=True)
class PartialProbePolicyBranch:
    """One declared outcome branch and the policy selected after that outcome."""

    outcome: TransitionOutcome
    weight: Optional[Fraction]
    child: "PartialProbePolicyNode"

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": {
                "target": self.outcome.target,
                "output": list(self.outcome.output),
            },
            "weight": None if self.weight is None else _fraction_record(self.weight),
            "weight_role": "metadata_only_not_used_by_worst_case_objective",
            "policy": self.child.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PartialProbePolicyNode:
    """A probe decision or a terminal stop at one counterfactual Ground."""

    ground_fingerprint: str
    unresolved_before: int
    worst_case_unresolved_pairs: int
    worst_case_cost: Fraction
    maximum_probes: int
    probe: Optional[TransitionProbe] = None
    branches: tuple[PartialProbePolicyBranch, ...] = ()
    terminal_reason: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        return self.probe is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ground_fingerprint": self.ground_fingerprint,
            "unresolved_before": self.unresolved_before,
            "worst_case_unresolved_pairs": self.worst_case_unresolved_pairs,
            "worst_case_cost": _fraction_record(self.worst_case_cost),
            "maximum_probes": self.maximum_probes,
            "probe": None if self.probe is None else _probe_record(self.probe),
            "branches": [item.to_dict() for item in self.branches],
            "terminal_reason": self.terminal_reason,
        }


@dataclass(frozen=True, slots=True)
class PartialProbePolicyPlan:
    """Exact finite policy tree with explicit worst-case and scope metadata."""

    system_fingerprint: str
    observer: ObserverContext
    horizon: int
    budget: Optional[Fraction]
    max_probes: int
    maximum_search_states: int
    root: PartialProbePolicyNode
    expanded_states: int
    objective: str = "minimize_worst_case_unresolved_then_exact_worst_case_cost"
    scenario_semantics: str = "declared_counterfactual_branches_not_probability_or_exhaustiveness_claim"
    optimality_scope: str = "finite_supplied_probe_candidates_and_declared_scenario_sets_only"

    @property
    def first_probe(self) -> Optional[TransitionProbe]:
        return self.root.probe

    @property
    def worst_case_unresolved_pairs(self) -> int:
        return self.root.worst_case_unresolved_pairs

    @property
    def worst_case_cost(self) -> Fraction:
        return self.root.worst_case_cost

    @property
    def maximum_probes_on_path(self) -> int:
        return self.root.maximum_probes

    @property
    def resolved_in_every_declared_branch(self) -> bool:
        return self.worst_case_unresolved_pairs == 0

    def to_dict(self) -> dict[str, Any]:
        core = {
            "format": "VGI-PartialProbePolicy-1",
            "system_fingerprint": self.system_fingerprint,
            "observer": {
                "name": self.observer.name,
                "actions": list(self.observer.actions),
                "channels": list(self.observer.channels),
            },
            "horizon": self.horizon,
            "budget": None if self.budget is None else _fraction_record(self.budget),
            "max_probes": self.max_probes,
            "maximum_search_states": self.maximum_search_states,
            "expanded_states": self.expanded_states,
            "objective": self.objective,
            "scenario_semantics": self.scenario_semantics,
            "optimality_scope": self.optimality_scope,
            "worst_case_unresolved_pairs": self.worst_case_unresolved_pairs,
            "worst_case_cost": _fraction_record(self.worst_case_cost),
            "maximum_probes_on_path": self.maximum_probes_on_path,
            "resolved_in_every_declared_branch": self.resolved_in_every_declared_branch,
            "root": self.root.to_dict(),
        }
        digest = hashlib.sha256(
            json.dumps(
                core, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        return {**core, "policy_digest": digest}


class _MinimaxSolver:
    def __init__(
        self,
        system: GroundTransitionSystem,
        observer: ObserverContext,
        candidates: tuple[TransitionProbe, ...],
        horizon: int,
        budget: Optional[Fraction],
        max_probes: int,
        max_states: int,
    ) -> None:
        self.system = system
        self.observer = observer
        self.candidates = candidates
        self.horizon = horizon
        self.budget = budget
        self.max_probes = max_probes
        self.max_states = max_states
        self.memo: dict[tuple, PartialProbePolicyNode] = {}
        self.expanded_states = 0

    def _unresolved(self, system: GroundTransitionSystem) -> int:
        comparison = sparse_partial_contextual_comparison(
            system, self.observer, self.horizon
        )
        return comparison.unresolved_pair_count()

    def _terminal_reason(
        self,
        unresolved: int,
        used_cells: frozenset[tuple[str, str]],
        remaining_budget: Optional[Fraction],
    ) -> str:
        if unresolved == 0:
            return "resolved"
        remaining = [
            item for item in self.candidates
            if (item.state, item.action) not in used_cells
        ]
        if not remaining:
            return "candidate_pool_exhausted"
        if len(used_cells) >= self.max_probes:
            return "probe_limit_reached"
        if remaining_budget is not None and not any(
            item.cost <= remaining_budget for item in remaining
        ):
            return "budget_exhausted"
        return "stop_is_optimal"

    def solve(
        self,
        system: GroundTransitionSystem,
        used_cells: frozenset[tuple[str, str]],
        remaining_budget: Optional[Fraction],
    ) -> PartialProbePolicyNode:
        key = (
            system.fingerprint,
            tuple(sorted(used_cells)),
            remaining_budget,
        )
        cached = self.memo.get(key)
        if cached is not None:
            return cached
        if self.expanded_states >= self.max_states:
            raise PartialProbePolicyError(
                f"exact policy search exceeded max_states={self.max_states}; "
                "no approximate policy is returned"
            )
        self.expanded_states += 1

        unresolved = self._unresolved(system)
        stop_reason = self._terminal_reason(
            unresolved, used_cells, remaining_budget
        )
        best = PartialProbePolicyNode(
            ground_fingerprint=system.fingerprint,
            unresolved_before=unresolved,
            worst_case_unresolved_pairs=unresolved,
            worst_case_cost=Fraction(0),
            maximum_probes=0,
            terminal_reason=stop_reason,
        )
        best_key = (unresolved, Fraction(0), 0, ())

        if unresolved == 0 or len(used_cells) >= self.max_probes:
            self.memo[key] = best
            return best

        available = [
            item for item in self.candidates
            if (item.state, item.action) not in used_cells
            and (remaining_budget is None or item.cost <= remaining_budget)
        ]
        available.sort(key=_probe_key)

        for probe in available:
            next_budget = (
                None if remaining_budget is None
                else remaining_budget - probe.cost
            )
            cell = (probe.state, probe.action)
            branches = []
            children = []
            for scenario in sorted(
                probe.scenarios,
                key=lambda item: _outcome_key(item.outcome),
            ):
                try:
                    next_system = counterfactual_probe_ground(
                        system, probe, scenario.outcome
                    )
                except PartialAttentionError as exc:
                    raise PartialProbePolicyError(str(exc)) from exc
                child = self.solve(
                    next_system,
                    used_cells | frozenset((cell,)),
                    next_budget,
                )
                children.append(child)
                branches.append(PartialProbePolicyBranch(
                    outcome=scenario.outcome,
                    weight=(
                        None if scenario.weight is None
                        else Fraction(scenario.weight)
                    ),
                    child=child,
                ))

            worst_unresolved = max(
                item.worst_case_unresolved_pairs for item in children
            )
            worst_cost = probe.cost + max(
                item.worst_case_cost for item in children
            )
            maximum_probes = 1 + max(item.maximum_probes for item in children)
            candidate_key = _probe_key(probe)
            objective_key = (
                worst_unresolved,
                worst_cost,
                maximum_probes,
                candidate_key,
            )
            if objective_key < best_key:
                best_key = objective_key
                best = PartialProbePolicyNode(
                    ground_fingerprint=system.fingerprint,
                    unresolved_before=unresolved,
                    worst_case_unresolved_pairs=worst_unresolved,
                    worst_case_cost=worst_cost,
                    maximum_probes=maximum_probes,
                    probe=probe,
                    branches=tuple(branches),
                    terminal_reason=None,
                )

        self.memo[key] = best
        return best


def plan_partial_probe_policy(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    probes: Sequence[TransitionProbe],
    horizon: int,
    *,
    budget: Optional[object] = None,
    max_probes: Optional[int] = None,
    max_states: int = 10_000,
) -> PartialProbePolicyPlan:
    """Build an exact finite minimax policy tree over unknown transition cells.

    Each selected cell is measured at most once on any policy path. Distinct
    methods for the same cell may compete, but after one method is chosen all
    alternatives for that cell are removed from that branch. Only unknown
    cells are accepted: an ambiguous cell is never collapsed by a policy
    scenario. The caller supplies the finite scenario set for each candidate.

    A node chooses one probe (OR); every declared scenario is a required branch
    (AND). Scenario weights are recorded but ignored by the worst-case search.
    The planner is exact only over the supplied candidate pool and scenario
    sets. Search is capped by max_probes and max_states; exceeding max_states
    raises rather than returning a result with unproven optimality.
    """
    if not isinstance(system, GroundTransitionSystem):
        raise PartialProbePolicyError("system must be a GroundTransitionSystem")
    if not isinstance(observer, ObserverContext):
        raise PartialProbePolicyError("observer must be an ObserverContext")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise PartialProbePolicyError("horizon must be a non-negative integer")
    observer.validate(system)
    normalized_budget = _fraction(budget, "budget", allow_zero=True)
    max_states = _positive_integer(max_states, "max_states")

    if not isinstance(probes, (tuple, list)):
        raise PartialProbePolicyError("probes must be a sequence")
    normalized = tuple(probes)
    if any(not isinstance(item, TransitionProbe) for item in normalized):
        raise PartialProbePolicyError("every candidate must be a TransitionProbe")
    keys = tuple(_probe_key(item) for item in normalized)
    if len(set(keys)) != len(keys):
        raise PartialProbePolicyError(
            "probe pool contains an exact duplicate policy candidate"
        )

    cells = set()
    for index, probe in enumerate(normalized):
        cell = (probe.state, probe.action)
        if probe.state not in system.states or probe.action not in system.actions:
            raise PartialProbePolicyError(
                f"probes[{index}] refers to a cell outside the Ground schema"
            )
        if probe.action not in observer.actions:
            raise PartialProbePolicyError(
                f"probes[{index}] action is not visible to the observer"
            )
        status = system.status(*cell)
        if status != "unknown":
            if status == "ambiguous":
                raise PartialProbePolicyError(
                    f"probes[{index}] targets an ambiguous cell; policy scenarios "
                    "must not collapse existing ambiguity"
                )
            raise PartialProbePolicyError(
                f"probes[{index}] targets a known cell"
            )
        cells.add(cell)
        for scenario in probe.scenarios:
            if scenario.outcome.target not in system.states:
                raise PartialProbePolicyError(
                    f"probes[{index}] scenario target is outside the Ground"
                )
            if len(scenario.outcome.output) != len(system.channels):
                raise PartialProbePolicyError(
                    f"probes[{index}] scenario output width does not match Ground channels"
                )

    if max_probes is None:
        normalized_max_probes = min(16, len(cells))
    else:
        normalized_max_probes = _nonnegative_integer(max_probes, "max_probes")
    if normalized_max_probes > len(cells):
        raise PartialProbePolicyError(
            "max_probes cannot exceed the number of distinct candidate cells"
        )

    solver = _MinimaxSolver(
        system,
        observer,
        normalized,
        horizon,
        normalized_budget,
        normalized_max_probes,
        max_states,
    )
    root = solver.solve(system, frozenset(), normalized_budget)
    return PartialProbePolicyPlan(
        system_fingerprint=system.fingerprint,
        observer=observer,
        horizon=horizon,
        budget=normalized_budget,
        max_probes=normalized_max_probes,
        maximum_search_states=max_states,
        root=root,
        expanded_states=solver.expanded_states,
    )


__all__ = [
    "PartialProbePolicyError",
    "PartialProbePolicyBranch",
    "PartialProbePolicyNode",
    "PartialProbePolicyPlan",
    "plan_partial_probe_policy",
]
