"""Partition-first partial predictive refinement with lazy pair explanations."""
from __future__ import annotations
from functools import lru_cache
from types import MappingProxyType
from typing import Mapping
from .relational import ObserverContext, PartialPairBlocker
from .transitions import GroundTransitionSystem

class SparsePartialError(ValueError):
    """Invalid sparse partial-refinement request."""

class SparsePartialComparison:
    """Store definite-equivalence classes and decide other pairs on demand."""
    def __init__(self, system: GroundTransitionSystem, observer: ObserverContext,
                 horizon: int, classes, state_to_class: Mapping[str, int]):
        self.system = system
        self.system_fingerprint = system.fingerprint
        self.observer = observer
        self.horizon = horizon
        self.classes = tuple(tuple(group) for group in classes)
        self.state_to_class = MappingProxyType(dict(state_to_class))
        self._order = {state: index for index, state in enumerate(system.states)}
        action_order = {action: index for index, action in enumerate(observer.actions)}
        channel_indices = tuple(system.channels.index(channel) for channel in observer.channels)

        @lru_cache(maxsize=None)
        def decide(level: int, left: str, right: str):
            if left == right or level == 0:
                return "equivalent", None, ()
            if self._order[left] > self._order[right]:
                left, right = right, left
            candidates, blockers = [], []
            for action in observer.actions:
                ls, rs = system.status(left, action), system.status(right, action)
                if ls != "known" or rs != "known":
                    blockers.append(PartialPairBlocker(action, ls, rs))
                    continue
                le, re = system.step(left, action), system.step(right, action)
                lo = tuple(le.output[i] for i in channel_indices)
                ro = tuple(re.output[i] for i in channel_indices)
                if lo != ro:
                    candidates.append((action,))
                    continue
                status, witness, _ = decide(level - 1, le.target, re.target)
                if status == "distinguishable":
                    candidates.append((action,) + witness)
                elif status == "unresolved":
                    blockers.append(PartialPairBlocker(action, "known", "known", "unresolved"))
            if candidates:
                witness = min(candidates, key=lambda word: (
                    len(word), tuple(action_order[item] for item in word)
                ))
                return "distinguishable", witness, ()
            if blockers:
                return "unresolved", None, tuple(blockers)
            return "equivalent", None, ()
        self._decide = decide

    @property
    def class_count(self):
        return len(self.classes)

    @property
    def equivalent_pair_count(self):
        return sum(len(group) * (len(group) - 1) // 2 for group in self.classes)

    @property
    def stored_pair_records(self):
        return 0

    def _validate(self, left, right):
        if left not in self.state_to_class or right not in self.state_to_class:
            raise SparsePartialError("pair contains a state outside this comparison")

    def status(self, left, right):
        self._validate(left, right)
        if left == right or self.state_to_class[left] == self.state_to_class[right]:
            return "equivalent"
        return self._decide(self.horizon, left, right)[0]

    def witness(self, left, right):
        self._validate(left, right)
        if left == right or self.state_to_class[left] == self.state_to_class[right]:
            return None
        status, witness, _ = self._decide(self.horizon, left, right)
        return witness if status == "distinguishable" else None

    def blockers(self, left, right):
        self._validate(left, right)
        if left == right or self.state_to_class[left] == self.state_to_class[right]:
            return ()
        status, _, blockers = self._decide(self.horizon, left, right)
        return blockers if status == "unresolved" else ()

    def unresolved_pair_count(self):
        states, count = self.system.states, 0
        for i, left in enumerate(states):
            for right in states[i + 1:]:
                count += self.status(left, right) == "unresolved"
        return count

    def pair_status_counts(self):
        counts = {"equivalent": len(self.system.states), "distinguishable": 0, "unresolved": 0}
        for i, left in enumerate(self.system.states):
            for right in self.system.states[i + 1:]:
                counts[self.status(left, right)] += 1
        return counts


def sparse_partial_refinement_series(system, observer, max_horizon):
    """Build equivalence partitions in O(H*S*A); pair explanations stay lazy."""
    if not isinstance(system, GroundTransitionSystem):
        raise SparsePartialError("system must be a GroundTransitionSystem")
    if not isinstance(observer, ObserverContext):
        raise SparsePartialError("observer must be an ObserverContext")
    if isinstance(max_horizon, bool) or not isinstance(max_horizon, int) or max_horizon < 0:
        raise SparsePartialError("max_horizon must be a non-negative integer")
    observer.validate(system)
    states = tuple(system.states)
    classes = (states,)
    state_to_class = {state: 0 for state in states}
    results = [SparsePartialComparison(system, observer, 0, classes, state_to_class)]
    for horizon in range(1, max_horizon + 1):
        signatures, groups = {}, []
        for state in states:
            parts, blocked = [], False
            for action in observer.actions:
                if system.status(state, action) != "known":
                    blocked = True
                    break
                step = system.step(state, action)
                output = tuple(step.output[system.channels.index(ch)] for ch in observer.channels)
                parts.append((output, state_to_class[step.target]))
            signature = ("blocked-state", state) if blocked else ("known-signature", *parts)
            class_id = signatures.get(signature)
            if class_id is None:
                class_id = len(groups)
                signatures[signature] = class_id
                groups.append([])
            groups[class_id].append(state)
        classes = tuple(tuple(group) for group in groups)
        state_to_class = {
            state: class_id for class_id, group in enumerate(classes) for state in group
        }
        results.append(SparsePartialComparison(system, observer, horizon, classes, state_to_class))
    return tuple(results)


def sparse_partial_contextual_comparison(system, observer, horizon):
    return sparse_partial_refinement_series(system, observer, horizon)[-1]


__all__ = [
    "SparsePartialError", "SparsePartialComparison",
    "sparse_partial_refinement_series", "sparse_partial_contextual_comparison",
]
