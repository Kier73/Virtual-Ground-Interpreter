"""Counterexample-led inquiries with an explicit open-world boundary."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations

from .relational import ContextualQuotient, ObserverContext, contextual_quotient
from .transitions import GroundTransitionSystem


class InquiryError(ValueError):
    """Invalid perception-inquiry request."""


@dataclass(frozen=True, slots=True)
class BlockedTransition:
    state: str
    action: str
    status: str


@dataclass(frozen=True, slots=True)
class DistinguishingWitness:
    left_state: str
    right_state: str
    action_word: tuple[str, ...]
    left_trace: tuple[tuple[int, ...], ...]
    right_trace: tuple[tuple[int, ...], ...]
    differing_channels: tuple[str, ...]
    left_output: tuple[int, ...]
    right_output: tuple[int, ...]
    newly_required_actions: tuple[str, ...]
    newly_required_channels: tuple[str, ...]

    @property
    def required_horizon(self) -> int:
        return len(self.action_word)

    @property
    def requires_observer_extension(self) -> bool:
        return bool(self.newly_required_actions or self.newly_required_channels)


@dataclass(frozen=True, slots=True)
class PairInquiry:
    left_state: str
    right_state: str
    conclusion: str
    witness: DistinguishingWitness | None
    explored_pairs: int
    blocked_transitions: tuple[BlockedTransition, ...]
    horizon_bound_reached: bool


@dataclass(frozen=True, slots=True)
class OpenWorldBoundary:
    declared_states: tuple[str, ...]
    declared_actions: tuple[str, ...]
    declared_channels: tuple[str, ...]
    declared_transition_system_complete: bool
    unknown_transition_cells: tuple[tuple[str, str], ...]
    ambiguous_transition_cells: tuple[tuple[str, str], ...]
    outside_declared_scope: str = "open_unenumerated"

    @property
    def is_open(self) -> bool:
        # Completeness of a finite schema cannot close its unrepresented exterior.
        return True


@dataclass(frozen=True, slots=True)
class PerceptionInquiryReport:
    system_fingerprint: str
    observer: ObserverContext
    horizon: int
    search_horizon: int
    quotient: ContextualQuotient
    inquiries: tuple[PairInquiry, ...]
    boundary: OpenWorldBoundary

    @property
    def unresolved_pair_count(self) -> int:
        return len(self.inquiries)

    @property
    def witness_count(self) -> int:
        return sum(item.witness is not None for item in self.inquiries)


def _validate_bound(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InquiryError(f"{label} must be a non-negative integer")


def _search_pair(system, observer, left, right, max_horizon) -> PairInquiry:
    """Return a shortest known distinguishing word, or an explicit limitation."""
    queue = deque([(left, right, (), (), ())])
    visited = {(left, right)}
    blocked = {}
    bound_reached = False
    explored = 0

    while queue:
        current_left, current_right, word, left_trace, right_trace = queue.popleft()
        explored += 1
        if len(word) >= max_horizon:
            bound_reached = True
            continue

        for action in system.actions:
            left_status = system.status(current_left, action)
            right_status = system.status(current_right, action)
            if left_status != "known" or right_status != "known":
                for state, status in ((current_left, left_status),
                                      (current_right, right_status)):
                    if status != "known":
                        blocked[(state, action)] = BlockedTransition(state, action, status)
                continue

            left_step = system.step(current_left, action)
            right_step = system.step(current_right, action)
            next_word = word + (action,)
            next_left_trace = left_trace + (left_step.output,)
            next_right_trace = right_trace + (right_step.output,)
            differing = tuple(
                channel for index, channel in enumerate(system.channels)
                if left_step.output[index] != right_step.output[index]
            )
            if differing:
                new_actions = tuple(dict.fromkeys(
                    item for item in next_word if item not in observer.actions
                ))
                new_channels = tuple(
                    item for item in differing if item not in observer.channels
                )
                witness = DistinguishingWitness(
                    left, right, next_word, next_left_trace, next_right_trace,
                    differing, left_step.output, right_step.output,
                    new_actions, new_channels,
                )
                return PairInquiry(
                    left, right, "witness_found", witness, explored,
                    tuple(blocked.values()), bound_reached,
                )

            next_pair = (left_step.target, right_step.target)
            if next_pair[0] == next_pair[1] or next_pair in visited:
                continue
            if len(next_word) >= max_horizon:
                bound_reached = True
                continue
            visited.add(next_pair)
            queue.append((
                next_pair[0], next_pair[1], next_word,
                next_left_trace, next_right_trace,
            ))

    if blocked:
        conclusion = "inconclusive_missing_evidence"
    elif bound_reached:
        conclusion = "no_witness_within_horizon"
    else:
        conclusion = "equivalent_over_declared_ground"
    return PairInquiry(
        left, right, conclusion, None, explored,
        tuple(blocked.values()), bound_reached,
    )


def inquire_unresolved_pairs(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    horizon: int,
    *,
    search_horizon: int | None = None,
) -> PerceptionInquiryReport:
    """Search current quotient pairs against all capabilities declared by Ground.

    A returned witness is verified only against known single-valued transitions
    and the Ground's existing output channels. The report always leaves the
    unrepresented exterior open; undeclared capabilities are not synthesized.
    """
    if not isinstance(system, GroundTransitionSystem):
        raise InquiryError("system must be a GroundTransitionSystem")
    if not isinstance(observer, ObserverContext):
        raise InquiryError("observer must be an ObserverContext")
    _validate_bound(horizon, "horizon")
    observer.validate(system)
    if search_horizon is None:
        search_horizon = max(1, len(system.states) ** 2)
    _validate_bound(search_horizon, "search_horizon")

    quotient = contextual_quotient(system, observer, horizon)
    inquiries = tuple(
        _search_pair(system, observer, left, right, search_horizon)
        for group in quotient.classes
        for left, right in combinations(group, 2)
    )
    boundary = OpenWorldBoundary(
        system.states, system.actions, system.channels, system.complete,
        system.unknown_pairs, system.ambiguous_pairs,
    )
    return PerceptionInquiryReport(
        system.fingerprint, observer, horizon, search_horizon,
        quotient, inquiries, boundary,
    )
