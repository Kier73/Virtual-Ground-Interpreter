"""Observer-relative finite quotients and behavioral distance profiles.

This module makes observer scope explicit: an observer chooses which actions
may be probed and which output channels may be perceived. It does not claim
that the resulting quotient is a physical hidden-state decomposition.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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

        stable = _same_partition(classes, previous_classes)
        quotient = ContextualQuotient(
            system.fingerprint, observer, horizon, classes, state_map, stable
        )
        result.append(quotient)
        previous_map = state_map
        previous_classes = classes
        if stable and stop_when_stable:
            break

    return tuple(result)


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
