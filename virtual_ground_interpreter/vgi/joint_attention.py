"""Joint navigation through observer configurations and predictive quotients.

Every search node carries two linked coordinates:
1. the perception configuration (available action probes and output channels);
2. the predictive quotient induced by that configuration.

The bounded beam planner retains zero-immediate-gain configurations because
future combinations can reveal distinctions that no individual capability
exposes. Candidate costs remain caller-declared relative units.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .relational import ContextualQuotient, ObserverContext, contextual_quotient
from .transitions import GroundTransitionSystem

from .attention import (
    AttentionCandidate,
    AttentionError,
    _evaluate,
    _extend_observer,
    _validate_budget,
    _validate_candidates,
    _validate_horizon,
    unresolved_pair_count,
)


@dataclass(frozen=True, slots=True)
class AttentionRouteStep:
    """One edge in the route through perception-configuration space."""

    index: int
    candidate: AttentionCandidate
    actions: tuple[str, ...]
    channels: tuple[str, ...]
    unresolved_before: int
    unresolved_after: int
    cumulative_cost: float
    class_count: int


@dataclass(frozen=True, slots=True)
class AttentionSearchRecord:
    """Audit record for one visited observer configuration."""

    depth: int
    selected: tuple[AttentionCandidate, ...]
    actions: tuple[str, ...]
    channels: tuple[str, ...]
    total_cost: float
    unresolved_pairs: int
    class_count: int
    retained_in_beam: bool


@dataclass(frozen=True, slots=True)
class JointAttentionPlan:
    """Best route found by bounded beam search."""

    strategy: str
    horizon: int
    initial_observer: ObserverContext
    observer: ObserverContext
    selected: tuple[AttentionCandidate, ...]
    total_cost: float
    initial_unresolved_pairs: int
    final_unresolved_pairs: int
    quotient: ContextualQuotient
    route: tuple[AttentionRouteStep, ...]
    search_records: tuple[AttentionSearchRecord, ...]
    expanded_nodes: int
    beam_width: int
    max_depth: int
    termination_reason: str

    @property
    def reduction(self) -> int:
        return self.initial_unresolved_pairs - self.final_unresolved_pairs

    @property
    def visited_configurations(self) -> int:
        return len(self.search_records)


@dataclass(frozen=True, slots=True)
class _Node:
    observer: ObserverContext
    selected: tuple[AttentionCandidate, ...]
    next_candidate_index: int
    total_cost: float
    quotient: ContextualQuotient
    unresolved_pairs: int
    route: tuple[AttentionRouteStep, ...]

    @property
    def sort_key(self) -> tuple:
        # Objective first, then resource cost, then a deterministic route key.
        return (
            self.unresolved_pairs,
            self.total_cost,
            len(self.selected),
            tuple(candidate.key for candidate in self.selected),
        )


def beam_attention_plan(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    candidates: Sequence[AttentionCandidate],
    horizon: int,
    budget: float,
    *,
    beam_width: int = 8,
    max_depth: int | None = None,
) -> JointAttentionPlan:
    """Search observer configurations while measuring their induced Ground quotients.

    Unlike greedy attention, this planner expands candidates with zero current
    marginal gain. It enumerates capability subsets in canonical order and
    retains at most beam_width configurations at each depth.

    The beam is a bounded heuristic, not an exact solver. It may prune a useful
    configuration when many alternatives have equal local objective. The
    search record preserves that pruning decision for inspection.
    """
    _validate_horizon(horizon)
    budget = _validate_budget(budget)
    pool = _validate_candidates(system, observer, candidates)
    if isinstance(beam_width, bool) or not isinstance(beam_width, int) or beam_width < 1:
        raise AttentionError("beam_width must be a positive integer")
    if max_depth is None:
        max_depth = len(pool)
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise AttentionError("max_depth must be a non-negative integer")
    max_depth = min(max_depth, len(pool))

    # Canonical candidate order gives every subset exactly one construction path.
    pool = tuple(sorted(pool, key=lambda item: item.key))
    initial_quotient, initial_unresolved = _evaluate(system, observer, horizon)
    root = _Node(observer, (), 0, 0.0, initial_quotient, initial_unresolved, ())
    frontier = [root]
    best = root
    expanded_nodes = 0
    records: list[dict] = [{
        "depth": 0,
        "selected": (),
        "actions": observer.actions,
        "channels": observer.channels,
        "total_cost": 0.0,
        "unresolved_pairs": initial_unresolved,
        "class_count": initial_quotient.class_count,
        "retained": True,
    }]
    termination = "max_depth"

    if initial_unresolved == 0:
        termination = "already_resolved"
    else:
        for depth in range(1, max_depth + 1):
            children: list[tuple[_Node, int]] = []
            for parent in frontier:
                for index in range(parent.next_candidate_index, len(pool)):
                    candidate = pool[index]
                    total_cost = parent.total_cost + candidate.cost
                    if total_cost > budget + 1e-12:
                        continue
                    next_observer = _extend_observer(system, parent.observer, (candidate,))
                    quotient, unresolved = _evaluate(system, next_observer, horizon)
                    if unresolved > parent.unresolved_pairs:
                        raise AttentionError(
                            "adding an observation unexpectedly merged predictive classes"
                        )
                    route_step = AttentionRouteStep(
                        index=len(parent.route) + 1,
                        candidate=candidate,
                        actions=next_observer.actions,
                        channels=next_observer.channels,
                        unresolved_before=parent.unresolved_pairs,
                        unresolved_after=unresolved,
                        cumulative_cost=total_cost,
                        class_count=quotient.class_count,
                    )
                    child = _Node(
                        next_observer,
                        parent.selected + (candidate,),
                        index + 1,
                        total_cost,
                        quotient,
                        unresolved,
                        parent.route + (route_step,),
                    )
                    expanded_nodes += 1
                    record_index = len(records)
                    records.append({
                        "depth": depth,
                        "selected": child.selected,
                        "actions": next_observer.actions,
                        "channels": next_observer.channels,
                        "total_cost": total_cost,
                        "unresolved_pairs": unresolved,
                        "class_count": quotient.class_count,
                        "retained": False,
                    })
                    children.append((child, record_index))
                    if child.sort_key < best.sort_key:
                        best = child

            if not children:
                termination = "frontier_exhausted"
                break

            children.sort(key=lambda pair: pair[0].sort_key)
            retained = children[:beam_width]
            for _, record_index in retained:
                records[record_index]["retained"] = True
            frontier = [node for node, _ in retained]

            if best.unresolved_pairs == 0:
                # Zero is the global lower bound; additional positive-cost
                # observations cannot improve the primary objective or tie-break.
                termination = "fully_resolved"
                break
        else:
            termination = "max_depth"

    return JointAttentionPlan(
        strategy="bounded_beam",
        horizon=horizon,
        initial_observer=observer,
        observer=best.observer,
        selected=best.selected,
        total_cost=best.total_cost,
        initial_unresolved_pairs=initial_unresolved,
        final_unresolved_pairs=best.unresolved_pairs,
        quotient=best.quotient,
        route=best.route,
        search_records=tuple(
            AttentionSearchRecord(
                depth=item["depth"],
                selected=item["selected"],
                actions=item["actions"],
                channels=item["channels"],
                total_cost=item["total_cost"],
                unresolved_pairs=item["unresolved_pairs"],
                class_count=item["class_count"],
                retained_in_beam=item["retained"],
            )
            for item in records
        ),
        expanded_nodes=expanded_nodes,
        beam_width=beam_width,
        max_depth=max_depth,
        termination_reason=termination,
    )
