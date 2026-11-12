"""Observer-relative finite quotients and behavioral distance profiles.

This module makes observer scope explicit: an observer chooses which actions
may be probed and which output channels may be perceived. It does not claim
that the resulting quotient is a physical hidden-state decomposition.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations_with_replacement
import math
from types import MappingProxyType
from typing import Mapping

from .transitions import GroundTransitionSystem, TransitionStep


class RelationalError(ValueError):
    """Invalid observer contract, quotient relation, or refinement request."""


@dataclass(frozen=True, slots=True)
class ObserverContext:
    """A finite perception contract over actions and output channels.

    The action order is also the deterministic signature order. Channel order
    controls the projected output tuple. Names are descriptive; compatibility
    depends on the action and channel selections, not the name.
    """

    name: str
    actions: tuple[str, ...]
    channels: tuple[str, ...]

    def __post_init__(self) -> None:
        actions, channels = tuple(self.actions), tuple(self.channels)
        if not isinstance(self.name, str) or not self.name:
            raise RelationalError("observer name must be a non-empty string")
        if not actions or any(not isinstance(x, str) or not x for x in actions):
            raise RelationalError("observer actions must be non-empty action names")
        if len(set(actions)) != len(actions):
            raise RelationalError("observer actions must be unique")
        if any(not isinstance(x, str) or not x for x in channels):
            raise RelationalError("observer channels must be non-empty names")
        if len(set(channels)) != len(channels):
            raise RelationalError("observer channels must be unique")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "channels", channels)

    @classmethod
    def full(cls, system: GroundTransitionSystem, name: str = "full") -> "ObserverContext":
        """Observe every declared action and output channel."""
        return cls(name, system.actions, system.channels)

    @property
    def projection_key(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return self.actions, self.channels

    def validate(self, system: GroundTransitionSystem) -> None:
        missing_actions = set(self.actions) - set(system.actions)
        missing_channels = set(self.channels) - set(system.channels)
        if missing_actions or missing_channels:
            raise RelationalError(
                "observer refers to undeclared items: "
                f"actions={sorted(missing_actions)}, channels={sorted(missing_channels)}"
            )


@dataclass(frozen=True, slots=True)
class ContextualQuotient:
    """A partition of predictive contexts at one observer and horizon."""

    system_fingerprint: str
    observer: ObserverContext
    horizon: int
    classes: tuple[tuple[str, ...], ...]
    state_to_class: Mapping[str, int]
    stable: bool = False

    def __post_init__(self) -> None:
        classes = tuple(tuple(group) for group in self.classes)
        mapping = dict(self.state_to_class)
        flattened = [state for group in classes for state in group]
        if not classes or any(not group for group in classes):
            raise RelationalError("a quotient must contain non-empty classes")
        if len(flattened) != len(set(flattened)) or set(flattened) != set(mapping):
            raise RelationalError("quotient classes and state map do not form a partition")
        if any(mapping[state] != index for index, group in enumerate(classes) for state in group):
            raise RelationalError("state_to_class does not agree with class ordering")
        object.__setattr__(self, "classes", classes)
        object.__setattr__(self, "state_to_class", MappingProxyType(mapping))

    @property
    def class_count(self) -> int:
        return len(self.classes)

    def equivalent(self, left: str, right: str) -> bool:
        try:
            return self.state_to_class[left] == self.state_to_class[right]
        except KeyError as exc:
            raise RelationalError(f"state {exc.args[0]!r} is outside this quotient") from exc


@dataclass(frozen=True, slots=True)
class PartialPairBlocker:
    """Why one selected action cannot support pair equivalence at this horizon."""

    action: str
    left_edge_status: str
    right_edge_status: str
    successor_status: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, str) or not self.action:
            raise RelationalError("blocker action must be a non-empty string")
        allowed = {"known", "unknown", "ambiguous"}
        if (not isinstance(self.left_edge_status, str)
                or not isinstance(self.right_edge_status, str)
                or self.left_edge_status not in allowed
                or self.right_edge_status not in allowed):
            raise RelationalError("blocker edge status must be known, unknown, or ambiguous")
        if self.successor_status not in (None, "unresolved"):
            raise RelationalError("blocker successor status must be absent or unresolved")
        if self.successor_status is not None and (
            self.left_edge_status != "known" or self.right_edge_status != "known"
        ):
            raise RelationalError("successor blocker requires two known current edges")
        if (self.left_edge_status == "known" and self.right_edge_status == "known"
                and self.successor_status is None):
            raise RelationalError("known edge pair requires an unresolved successor blocker")

    @property
    def reason(self) -> str:
        if self.left_edge_status == "unknown" or self.right_edge_status == "unknown":
            return "missing_edge"
        if self.left_edge_status == "ambiguous" or self.right_edge_status == "ambiguous":
            return "ambiguous_edge"
        return "unresolved_successor"


@dataclass(frozen=True, slots=True)
class PartialContextualComparison:
    """Three-valued predictive comparison for a possibly partial Ground.

    Equivalent means selected behavior through this horizon is known and
    equal. Distinguishable carries a concrete observed action word.
    Unresolved means no witness is known, but missing or ambiguous evidence
    prevents an equivalence claim. Unresolved is neither equality nor inequality.
    """

    system_fingerprint: str
    states: tuple[str, ...]
    observer: ObserverContext
    horizon: int
    pair_statuses: Mapping[tuple[str, str], str]
    distinguishing_sequences: Mapping[tuple[str, str], tuple[str, ...]]
    unresolved_blockers: Mapping[tuple[str, str], tuple[PartialPairBlocker, ...]]

    def __post_init__(self) -> None:
        states = tuple(self.states)
        if not states or len(set(states)) != len(states):
            raise RelationalError("partial comparison requires unique declared states")
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int) or self.horizon < 0:
            raise RelationalError("partial comparison horizon must be non-negative")
        status_map = dict(self.pair_statuses)
        order = {state: index for index, state in enumerate(states)}
        expected = {
            (states[left], states[right])
            for left in range(len(states))
            for right in range(left, len(states))
        }
        if set(status_map) != expected:
            raise RelationalError("partial comparison must classify every unordered state pair")
        allowed = {"equivalent", "distinguishable", "unresolved"}
        if any(value not in allowed for value in status_map.values()):
            raise RelationalError("unknown partial comparison status")
        witnesses = {
            pair: tuple(sequence)
            for pair, sequence in self.distinguishing_sequences.items()
        }
        expected_witnesses = {
            pair for pair, status in status_map.items() if status == "distinguishable"
        }
        if set(witnesses) != expected_witnesses:
            raise RelationalError("every and only distinguishable pairs require a witness")
        for (left, right), sequence in witnesses.items():
            if order[left] > order[right] or not sequence:
                raise RelationalError("distinguishing witnesses require canonical pairs and non-empty words")
            if any(action not in self.observer.actions for action in sequence):
                raise RelationalError("distinguishing witness uses an action outside its observer")
        blockers = {
            pair: tuple(items)
            for pair, items in self.unresolved_blockers.items()
        }
        expected_unresolved = {
            pair for pair, status in status_map.items() if status == "unresolved"
        }
        if set(blockers) != expected_unresolved:
            raise RelationalError("every unresolved pair requires blocker provenance")
        if any(not items for items in blockers.values()):
            raise RelationalError("unresolved pairs require at least one blocker")
        for pair, items in blockers.items():
            if any(not isinstance(item, PartialPairBlocker) for item in items):
                raise RelationalError("blocker records must be PartialPairBlocker instances")
            if any(item.action not in self.observer.actions for item in items):
                raise RelationalError("blocker action is outside its observer")
            if len({item.action for item in items}) != len(items):
                raise RelationalError("each selected action may block a pair only once")
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "pair_statuses", MappingProxyType(status_map))
        object.__setattr__(self, "distinguishing_sequences", MappingProxyType(witnesses))
        object.__setattr__(self, "unresolved_blockers", MappingProxyType(blockers))

    def _key(self, left: str, right: str) -> tuple[str, str]:
        try:
            left_index = self.states.index(left)
            right_index = self.states.index(right)
        except ValueError as exc:
            raise RelationalError(f"state {exc.args[0]!r} is outside this comparison") from exc
        return (left, right) if left_index <= right_index else (right, left)

    def status(self, left: str, right: str) -> str:
        """Return equivalent, distinguishable, or unresolved for this pair."""
        return self.pair_statuses[self._key(left, right)]

    def witness(self, left: str, right: str) -> tuple[str, ...] | None:
        """Return the shortest retained distinguishing action word, if known."""
        return self.distinguishing_sequences.get(self._key(left, right))

    def blockers(self, left: str, right: str) -> tuple[PartialPairBlocker, ...]:
        """Return structured reasons why an equivalence claim is blocked."""
        return self.unresolved_blockers.get(self._key(left, right), ())

    def blocked(self, left: str, right: str) -> tuple[str, ...]:
        """Return selected action names whose evidence blocks equivalence."""
        return tuple(item.action for item in self.blockers(left, right))

    @property
    def equivalent_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            pair for pair, status in self.pair_statuses.items()
            if pair[0] != pair[1] and status == "equivalent"
        )

    @property
    def distinguishable_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            pair for pair, status in self.pair_statuses.items()
            if status == "distinguishable"
        )

    @property
    def unresolved_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            pair for pair, status in self.pair_statuses.items()
            if pair[0] != pair[1] and status == "unresolved"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-PartialContextualComparison-1",
            "system_fingerprint": self.system_fingerprint,
            "states": list(self.states),
            "observer": {
                "name": self.observer.name,
                "actions": list(self.observer.actions),
                "channels": list(self.observer.channels),
            },
            "horizon": self.horizon,
            "pairs": [
                {
                    "left": pair[0],
                    "right": pair[1],
                    "status": status,
                    "witness": list(self.distinguishing_sequences[pair])
                    if pair in self.distinguishing_sequences else None,
                    "blockers": [
                        {
                            "action": item.action,
                            "left_edge_status": item.left_edge_status,
                            "right_edge_status": item.right_edge_status,
                            "successor_status": item.successor_status,
                            "reason": item.reason,
                        }
                        for item in self.unresolved_blockers.get(pair, ())
                    ],
                }
                for pair, status in self.pair_statuses.items()
            ],
        }


@dataclass(frozen=True, slots=True)
class QuotientEdge:
    """One well-defined edge from a finer quotient to its coarser successor."""

    source_class: int
    action: str
    target_class: int
    output: tuple[int, ...]


def _same_partition(
    left: tuple[tuple[str, ...], ...], right: tuple[tuple[str, ...], ...]
) -> bool:
    return {frozenset(group) for group in left} == {frozenset(group) for group in right}


def _resolve_context_edges(
    system: GroundTransitionSystem, observer: ObserverContext
) -> tuple[dict[tuple[str, str], TransitionStep], tuple[int, ...]]:
    observer.validate(system)
    channel_indices = tuple(system.channels.index(channel) for channel in observer.channels)
    edges = {
        (state, action): system.step(state, action)
        for state in system.states
        for action in observer.actions
    }
    return edges, channel_indices


def refinement_series(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    max_horizon: int,
    *,
    stop_when_stable: bool = True,
) -> tuple[ContextualQuotient, ...]:
    """Build exact predictive quotients from horizon zero through a bound.

    At horizon h+1, two states remain equivalent only when every selected
    action gives the same projected immediate output and successors equivalent
    at horizon h. Unknown or ambiguous selected edges are never imputed.
    """
    if isinstance(max_horizon, bool) or not isinstance(max_horizon, int) or max_horizon < 0:
        raise RelationalError("max_horizon must be a non-negative integer")
    observer.validate(system)
    first = ContextualQuotient(
        system.fingerprint,
        observer,
        0,
        (tuple(system.states),),
        {state: 0 for state in system.states},
        False,
    )
    result = [first]
    if max_horizon == 0:
        return tuple(result)
    edges, channel_indices = _resolve_context_edges(system, observer)
    previous_map = dict(first.state_to_class)
    previous_classes = first.classes

    for horizon in range(1, max_horizon + 1):
        signatures: dict[tuple[tuple[tuple[int, ...], int], ...], int] = {}
        groups: list[list[str]] = []
        for state in system.states:
            signature = tuple(
                (
                    tuple(edges[(state, action)].output[index] for index in channel_indices),
                    previous_map[edges[(state, action)].target],
                )
                for action in observer.actions
            )
            class_id = signatures.get(signature)
            if class_id is None:
                class_id = len(groups)
                signatures[signature] = class_id
                groups.append([])
            groups[class_id].append(state)

        classes = tuple(tuple(group) for group in groups)
        state_map = {
            state: class_id
            for class_id, group in enumerate(classes)
            for state in group
        }
        # Refinement may split a class, but it must never merge one.
        for group in classes:
            if len({previous_map[state] for state in group}) != 1:
                raise RelationalError("internal refinement error: a later horizon merged classes")

        # A discrete partition cannot be refined any further; otherwise, wait
        # for one unchanged horizon before certifying a non-discrete fixed point.
        stable = _same_partition(classes, previous_classes) or len(classes) == len(system.states)
        quotient = ContextualQuotient(
            system.fingerprint, observer, horizon, classes, state_map, stable
        )
        result.append(quotient)
        previous_map = state_map
        previous_classes = classes
        if stable and stop_when_stable:
            break

    return tuple(result)


def partial_refinement_series(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    max_horizon: int,
) -> tuple[PartialContextualComparison, ...]:
    """Build three-valued predictive comparisons from horizon zero to a bound.

    Unknown or ambiguous transitions are not filled in. A pair is equivalent
    only when every selected action is known on both sides, has the same
    projected output, and reaches states equivalent at the preceding horizon.
    One concrete distinguishing word is sufficient to prove distinguishability
    even if another action remains unresolved.
    """
    if not isinstance(system, GroundTransitionSystem):
        raise RelationalError("system must be a GroundTransitionSystem")
    if not isinstance(observer, ObserverContext):
        raise RelationalError("observer must be an ObserverContext")
    if isinstance(max_horizon, bool) or not isinstance(max_horizon, int) or max_horizon < 0:
        raise RelationalError("max_horizon must be a non-negative integer")
    observer.validate(system)

    states = tuple(system.states)
    order = {state: index for index, state in enumerate(states)}
    pairs = tuple(
        (states[left], states[right])
        for left, right in combinations_with_replacement(range(len(states)), 2)
    )
    channel_indices = tuple(system.channels.index(channel) for channel in observer.channels)
    action_order = {action: index for index, action in enumerate(observer.actions)}

    def canonical(left: str, right: str) -> tuple[str, str]:
        return (left, right) if order[left] <= order[right] else (right, left)

    def witness_key(word: tuple[str, ...]) -> tuple[int, tuple[int, ...]]:
        return len(word), tuple(action_order[action] for action in word)

    previous_statuses = {pair: "equivalent" for pair in pairs}
    previous_witnesses: dict[tuple[str, str], tuple[str, ...]] = {}
    results = [
        PartialContextualComparison(
            system.fingerprint, states, observer, 0, previous_statuses, {}, {},
        )
    ]

    for horizon in range(1, max_horizon + 1):
        current_statuses: dict[tuple[str, str], str] = {}
        current_witnesses: dict[tuple[str, str], tuple[str, ...]] = {}
        current_blockers: dict[tuple[str, str], tuple[PartialPairBlocker, ...]] = {}

        for pair in pairs:
            left, right = pair
            if left == right:
                current_statuses[pair] = "equivalent"
                continue

            if previous_statuses[pair] == "distinguishable":
                current_statuses[pair] = "distinguishable"
                current_witnesses[pair] = previous_witnesses[pair]
                continue

            candidates: list[tuple[str, ...]] = []
            blockers: list[PartialPairBlocker] = []
            for action in observer.actions:
                left_edge_status = system.status(left, action)
                right_edge_status = system.status(right, action)
                if left_edge_status != "known" or right_edge_status != "known":
                    blockers.append(PartialPairBlocker(
                        action, left_edge_status, right_edge_status,
                    ))
                    continue

                left_step = system.step(left, action)
                right_step = system.step(right, action)
                left_output = tuple(left_step.output[index] for index in channel_indices)
                right_output = tuple(right_step.output[index] for index in channel_indices)

                if left_output != right_output:
                    candidates.append((action,))
                    continue

                target_pair = canonical(left_step.target, right_step.target)
                target_status = previous_statuses[target_pair]
                if target_status == "distinguishable":
                    candidates.append((action,) + previous_witnesses[target_pair])
                elif target_status == "unresolved":
                    blockers.append(PartialPairBlocker(
                        action, "known", "known", "unresolved",
                    ))

            if candidates:
                current_statuses[pair] = "distinguishable"
                current_witnesses[pair] = min(candidates, key=witness_key)
            elif previous_statuses[pair] == "unresolved" and not blockers:
                raise RelationalError(
                    "an unresolved pair cannot become equivalent without new evidence"
                )
            elif blockers:
                current_statuses[pair] = "unresolved"
                current_blockers[pair] = tuple(blockers)
            else:
                current_statuses[pair] = "equivalent"

        results.append(PartialContextualComparison(
            system.fingerprint, states, observer, horizon,
            current_statuses, current_witnesses, current_blockers,
        ))
        previous_statuses = current_statuses
        previous_witnesses = current_witnesses

    return tuple(results)


def partial_contextual_comparison(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    horizon: int,
) -> PartialContextualComparison:
    """Return the three-valued comparison at exactly one bounded horizon."""
    return partial_refinement_series(system, observer, horizon)[-1]


def contextual_quotient(
    system: GroundTransitionSystem, observer: ObserverContext, horizon: int
) -> ContextualQuotient:
    """Return the quotient at exactly the requested horizon."""
    return refinement_series(
        system, observer, horizon, stop_when_stable=False
    )[-1]


def quotient_map(
    finer: ContextualQuotient, coarser: ContextualQuotient
) -> Mapping[int, int]:
    """Map each finer class into its unique containing coarser class."""
    if finer.system_fingerprint != coarser.system_fingerprint:
        raise RelationalError("quotients come from different transition systems")
    if finer.observer.projection_key != coarser.observer.projection_key:
        raise RelationalError("quotients use different observer action/channel selections")
    if finer.horizon < coarser.horizon:
        raise RelationalError("the first quotient must have an equal or finer horizon")

    mapping: dict[int, int] = {}
    for class_id, members in enumerate(finer.classes):
        targets = {coarser.state_to_class[state] for state in members}
        if len(targets) != 1:
            raise RelationalError("the proposed quotient map is not well-defined")
        mapping[class_id] = next(iter(targets))
    return MappingProxyType(mapping)


def quotient_transition_table(
    system: GroundTransitionSystem,
    source_finer: ContextualQuotient,
    target_coarser: ContextualQuotient,
) -> tuple[QuotientEdge, ...]:
    """Verify the one-step transition/output map from Q_(h+1) into Q_h.

    For every class in the horizon-(h+1) quotient, all representatives must
    emit the same selected output and land in the same horizon-h class.
    """
    if source_finer.system_fingerprint != system.fingerprint:
        raise RelationalError("source quotient does not belong to this transition system")
    if target_coarser.system_fingerprint != system.fingerprint:
        raise RelationalError("target quotient does not belong to this transition system")
    if source_finer.observer.projection_key != target_coarser.observer.projection_key:
        raise RelationalError("quotients use different observer action/channel selections")
    if source_finer.horizon != target_coarser.horizon + 1:
        raise RelationalError("transition maps require adjacent horizons h+1 -> h")

    edges, channel_indices = _resolve_context_edges(system, source_finer.observer)
    result = []
    for source_class, members in enumerate(source_finer.classes):
        for action in source_finer.observer.actions:
            projected = {
                (
                    tuple(edges[(state, action)].output[index] for index in channel_indices),
                    target_coarser.state_to_class[edges[(state, action)].target],
                )
                for state in members
            }
            if len(projected) != 1:
                raise RelationalError(
                    "transition/output is not well-defined on this source quotient; "
                    "increase the source horizon or narrow the observer"
                )
            output, target_class = next(iter(projected))
            result.append(QuotientEdge(source_class, action, target_class, output))
    return tuple(result)


def _output_distance(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left:
        return 0.0
    distances = []
    for a, b in zip(left, right):
        clockwise = (a - b) % 8
        distances.append(min(clockwise, 8 - clockwise) / 4.0)
    return sum(distances) / len(distances)


def behavioral_distance(
    system: GroundTransitionSystem,
    observer: ObserverContext,
    left: str,
    right: str,
    horizon: int,
    *,
    discount: float = 1.0,
    action_weights: Mapping[str, float] | None = None,
) -> float:
    """Compute a bounded observer-relative behavioral pseudometric.

    A shared action is sampled at each step according to action_weights. The
    output metric is the mean normalized cyclic distance on selected Z/8Z
    channels. Full-support weights make zero distance equivalent to equality
    of all selected output traces up to the given horizon.
    """
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise RelationalError("horizon must be a non-negative integer")
    if left not in system.states or right not in system.states:
        raise RelationalError("distance endpoints must be declared states")
    if isinstance(discount, bool) or not isinstance(discount, (int, float)):
        raise RelationalError("discount must be a finite number in [0, 1]")
    discount = float(discount)
    if not math.isfinite(discount) or not 0.0 <= discount <= 1.0:
        raise RelationalError("discount must be a finite number in [0, 1]")
    if horizon == 0:
        observer.validate(system)
        return 0.0

    edges, channel_indices = _resolve_context_edges(system, observer)
    if action_weights is None:
        weights = {action: 1.0 / len(observer.actions) for action in observer.actions}
    else:
        unknown = set(action_weights) - set(observer.actions)
        if unknown:
            raise RelationalError(f"weights supplied for unobserved actions: {sorted(unknown)}")
        raw_weights = {}
        for action in observer.actions:
            value = action_weights.get(action, 0.0)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RelationalError("action weights must be finite non-negative numbers")
            value = float(value)
            if not math.isfinite(value) or value < 0.0:
                raise RelationalError("action weights must be finite non-negative numbers")
            raw_weights[action] = value
        total = sum(raw_weights.values())
        if total <= 0.0:
            raise RelationalError("at least one observed action must have positive weight")
        weights = {action: value / total for action, value in raw_weights.items()}

    @lru_cache(maxsize=None)
    def distance(source: str, target: str, remaining: int) -> float:
        if remaining == 0:
            return 0.0
        immediate = 0.0
        future = 0.0
        for action, weight in weights.items():
            if weight == 0.0:
                continue
            source_edge = edges[(source, action)]
            target_edge = edges[(target, action)]
            source_output = tuple(source_edge.output[index] for index in channel_indices)
            target_output = tuple(target_edge.output[index] for index in channel_indices)
            immediate += weight * _output_distance(source_output, target_output)
            future += weight * distance(
                source_edge.target, target_edge.target, remaining - 1
            )
        return immediate + discount * future

    normalizer = sum(discount ** index for index in range(horizon))
    return distance(left, right, horizon) / normalizer
