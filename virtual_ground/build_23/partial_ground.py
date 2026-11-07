"""Build 20 companion: a tiny Jenga-like support-logic ground.

This is an abstract symbolic support puzzle, not a physical mechanics model.
Actions remove blocks and are irreversible. Stability is a declared support-graph
predicate, not an estimate of real-world structural strength.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass

BLOCKS = tuple(range(9))
BASE = (0, 1, 2)
MIDDLE = (3, 4, 5)
TOP = (6, 7, 8)

# Each middle block has two possible base supports; each top block has two
# possible middle supports. Indexing is cyclic to make alternate support paths.
SUPPORTS = {
    3: (0, 1), 4: (1, 2), 5: (2, 0),
    6: (3, 4), 7: (4, 5), 8: (5, 3),
}


@dataclass(frozen=True)
class PartialGround:
    name: str = "Support-9"
    version: int = 1
    supports: tuple[tuple[int, tuple[int, ...]], ...] = tuple(sorted(SUPPORTS.items()))

    def support_map(self) -> dict[int, tuple[int, ...]]:
        return dict(self.supports)

    def stable(self, mask: int) -> bool:
        support_map = self.support_map()
        for block, supports in support_map.items():
            if mask & (1 << block):
                if not any(mask & (1 << support) for support in supports):
                    return False
        return True

    def legal_actions(self, mask: int) -> tuple[str, ...]:
        if not self.stable(mask):
            return ()
        legal = []
        for block in BLOCKS:
            if mask & (1 << block):
                nxt = mask & ~(1 << block)
                if self.stable(nxt):
                    legal.append(f"REMOVE_{block}")
        return tuple(legal)

    def transition(self, mask: int, action: str) -> int:
        if action not in self.legal_actions(mask):
            raise ValueError(f"illegal action {action} in state {mask:09b}")
        block = int(action.split("_")[1])
        return mask & ~(1 << block)

    def revise_support(self, block: int, new_supports: tuple[int, ...]) -> "PartialGround":
        """Versioned logic revision: change the support rule, not just occupancy."""
        support_map = self.support_map()
        support_map[block] = tuple(new_supports)
        return PartialGround(
            name=f"{self.name}-support-revised",
            version=self.version + 1,
            supports=tuple(sorted(support_map.items())),
        )


def initial_state() -> int:
    return (1 << len(BLOCKS)) - 1


def enumerate_reachable(ground: PartialGround, start: int | None = None):
    start = initial_state() if start is None else start
    distances = {start: 0}
    parents = {start: None}
    queue = deque([start])
    edges = set()
    while queue:
        state = queue.popleft()
        for action in ground.legal_actions(state):
            nxt = ground.transition(state, action)
            edges.add((state, action, nxt))
            if nxt not in distances:
                distances[nxt] = distances[state] + 1
                parents[nxt] = (state, action)
                queue.append(nxt)
    return distances, parents, edges


def level_counts(mask: int) -> tuple[int, int, int]:
    return tuple(sum(bool(mask & (1 << i)) for i in layer) for layer in (BASE, MIDDLE, TOP))


def profile_is_transition_congruent(ground: PartialGround, states: tuple[int, ...]) -> bool:
    """Whether level counts alone define a congruent quotient for labelled removes."""
    groups: dict[tuple[int, int, int], list[int]] = {}
    for state in states:
        groups.setdefault(level_counts(state), []).append(state)
    for group in groups.values():
        if len(group) < 2:
            continue
        reference = group[0]
        ref_actions = set(ground.legal_actions(reference))
        for state in group[1:]:
            if set(ground.legal_actions(state)) != ref_actions:
                return False
    return True
