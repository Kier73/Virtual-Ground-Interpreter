"""Build 20: a finite, generative Virtual Ground for a four-module rotor puzzle.

The puzzle is an original small algebraic fixture inspired by twisty puzzles; it is
not a model of the full Rubik's Cube.  Standard-library only.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import permutations, product
import heapq
from typing import Callable, Iterable, NamedTuple

N = 4
MOD = 3


class State(NamedTuple):
    """Piece at each slot and orientation of the piece at each slot."""
    perm: tuple[int, ...]
    ori: tuple[int, ...]


@dataclass(frozen=True)
class Transform:
    """A reversible operation: old slot i moves to dest[i], with twist[i]."""
    name: str
    dest: tuple[int, ...]
    twist: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.dest) != N or sorted(self.dest) != list(range(N)):
            raise ValueError("dest must be a permutation of slots")
        if len(self.twist) != N or any(x not in range(MOD) for x in self.twist):
            raise ValueError("twist entries must be in Z_3")
        if sum(self.twist) % MOD:
            raise ValueError("legal transforms must preserve total orientation modulo 3")


IDENTITY = Transform("I", tuple(range(N)), (0, 0, 0, 0))
SOLVED = State(tuple(range(N)), (0, 0, 0, 0))


def validate_state(state: State) -> bool:
    return (
        len(state.perm) == N
        and sorted(state.perm) == list(range(N))
        and len(state.ori) == N
        and all(x in range(MOD) for x in state.ori)
        and sum(state.ori) % MOD == 0
    )


def apply_transform(state: State, op: Transform) -> State:
    """Apply an operation; orientations travel with the pieces occupying old slots."""
    if not validate_state(state):
        raise ValueError("invalid input state")
    new_perm = [None] * N
    new_ori = [None] * N
    for old_slot, new_slot in enumerate(op.dest):
        new_perm[new_slot] = state.perm[old_slot]
        new_ori[new_slot] = (state.ori[old_slot] + op.twist[old_slot]) % MOD
    result = State(tuple(new_perm), tuple(new_ori))
    if not validate_state(result):
        raise AssertionError("legal operation violated the state invariant")
    return result


def compose(first: Transform, second: Transform, name: str | None = None) -> Transform:
    """Composition in execution order: apply first, then second."""
    dest = tuple(second.dest[first.dest[i]] for i in range(N))
    twist = tuple((first.twist[i] + second.twist[first.dest[i]]) % MOD for i in range(N))
    return Transform(name or f"({first.name}>{second.name})", dest, twist)


def inverse(op: Transform) -> Transform:
    inv_dest = [None] * N
    for old_slot, new_slot in enumerate(op.dest):
        inv_dest[new_slot] = old_slot
    inv_twist = [None] * N
    for old_slot, new_slot in enumerate(op.dest):
        inv_twist[new_slot] = (-op.twist[old_slot]) % MOD
    return Transform(f"{op.name}^-1", tuple(inv_dest), tuple(inv_twist))


def transform_of_state(state: State) -> Transform:
    """The unique transform taking SOLVED to state."""
    if not validate_state(state):
        raise ValueError("invalid state")
    # Piece i is currently at slot dest[i].
    dest = tuple(state.perm.index(piece) for piece in range(N))
    twist = tuple(state.ori[dest[piece]] for piece in range(N))
    return Transform("state", dest, twist)


def state_of_transform(op: Transform) -> State:
    return apply_transform(SOLVED, op)


def primitive_moves(twists_enabled: bool = True) -> tuple[Transform, ...]:
    moves: list[Transform] = []
    for i in range(N - 1):
        d = list(range(N))
        d[i], d[i + 1] = d[i + 1], d[i]
        moves.append(Transform(f"SWAP{i}{i+1}", tuple(d), (0, 0, 0, 0)))
    if twists_enabled:
        for i in range(N - 1):
            plus = [0] * N
            plus[i] = 1
            plus[N - 1] = 2
            op = Transform(f"TWIST{i}+", tuple(range(N)), tuple(plus))
            minus = tuple((-x) % MOD for x in plus)
            inv = Transform(f"TWIST{i}-", tuple(range(N)), minus)
            moves.extend((op, inv))
    return tuple(moves)


@dataclass(frozen=True)
class VirtualGround:
    """Generative specification, not an enumerated list of all states."""
    name: str
    version: int
    moves: tuple[Transform, ...]
    state_count: int = 648
    observer_names: tuple[str, ...] = ("full", "layout", "orientation")

    def transition(self, state: State, operation_name: str) -> State:
        matches = [m for m in self.moves if m.name == operation_name]
        if len(matches) != 1:
            raise KeyError(f"operation {operation_name!r} is not available in {self.name}")
        return apply_transform(state, matches[0])

    def revise_without_twists(self) -> "VirtualGround":
        """Illustrate a ground shift: the legal operation system changes."""
        return VirtualGround(
            name=f"{self.name}-orientation-locked",
            version=self.version + 1,
            moves=primitive_moves(twists_enabled=False),
            state_count=self.state_count,
            observer_names=self.observer_names,
        )


def base_ground() -> VirtualGround:
    return VirtualGround("Rotor-4", 1, primitive_moves(True))


def all_states() -> tuple[State, ...]:
    states = []
    for p in permutations(range(N)):
        for first_three in product(range(MOD), repeat=N - 1):
            last = (-sum(first_three)) % MOD
            states.append(State(tuple(p), tuple(first_three) + (last,)))
    return tuple(states)


def lehmer_rank(p: tuple[int, ...]) -> int:
    """Rank a permutation in [0, N!-1]."""
    if len(p) != N or sorted(p) != list(range(N)):
        raise ValueError("not a permutation")
    rank = 0
    for i in range(N):
        smaller = sum(1 for x in p[i + 1 :] if x < p[i])
        rank += smaller * factorial(N - 1 - i)
    return rank


def factorial(n: int) -> int:
    out = 1
    for k in range(2, n + 1):
        out *= k
    return out


def lehmer_unrank(rank: int) -> tuple[int, ...]:
    if not 0 <= rank < factorial(N):
        raise ValueError("permutation rank out of range")
    items = list(range(N))
    out = []
    r = rank
    for i in range(N):
        f = factorial(N - 1 - i)
        q, r = divmod(r, f)
        out.append(items.pop(q))
    return tuple(out)


def encode_state(state: State) -> int:
    """Bijective mixed-radix coordinate for this fixed finite state space."""
    if not validate_state(state):
        raise ValueError("invalid state")
    p_rank = lehmer_rank(state.perm)
    o_rank = state.ori[0] * 9 + state.ori[1] * 3 + state.ori[2]
    return p_rank * 27 + o_rank


def decode_state(code: int) -> State:
    if not 0 <= code < 648:
        raise ValueError("state code out of range")
    p_rank, o_rank = divmod(code, 27)
    a, r = divmod(o_rank, 9)
    b, c = divmod(r, 3)
    ori3 = (a, b, c)
    return State(lehmer_unrank(p_rank), ori3 + ((-sum(ori3)) % MOD,))


def bfs_policy(ground: VirtualGround, start: State = SOLVED) -> tuple[dict[State, int], dict[State, tuple[str, ...]]]:
    """Exact unit-cost shortest paths from start, using the ground's generators."""
    distances = {start: 0}
    paths: dict[State, tuple[str, ...]] = {start: ()}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for op in ground.moves:
            nxt = apply_transform(current, op)
            if nxt not in distances:
                distances[nxt] = distances[current] + 1
                paths[nxt] = paths[current] + (op.name,)
                queue.append(nxt)
    return distances, paths


class GroundNavigator:
    """Precomputed shortest-policy ground with direct relative-state lookup."""
    def __init__(self, ground: VirtualGround):
        self.ground = ground
        self.distances, self.paths = bfs_policy(ground, SOLVED)

    def query(self, start: State, target: State) -> tuple[tuple[str, ...], int] | None:
        if not (validate_state(start) and validate_state(target)):
            raise ValueError("invalid start or target")
        relative = compose(inverse(transform_of_state(start)), transform_of_state(target), "relative")
        relative_state = state_of_transform(relative)
        if relative_state not in self.paths:
            return None
        path = self.paths[relative_state]
        if apply_named_path(start, path, self.ground) != target:
            raise AssertionError("cached relative policy failed to reach target")
        return path, self.distances[relative_state]


def dijkstra_policy(ground: VirtualGround, move_costs: dict[str, float], start: State = SOLVED) -> tuple[dict[State, float], dict[State, tuple[str, ...]]]:
    """Minimum-cost navigation under an observer/resource-specific move cost."""
    distances: dict[State, float] = {start: 0.0}
    paths: dict[State, tuple[str, ...]] = {start: ()}
    heap: list[tuple[float, int, State]] = [(0.0, 0, start)]
    serial = 1
    while heap:
        cost, _, current = heapq.heappop(heap)
        if cost != distances.get(current):
            continue
        for op in ground.moves:
            edge_cost = float(move_costs.get(op.name, 1.0))
            if edge_cost <= 0:
                raise ValueError("Dijkstra requires strictly positive operation costs")
            nxt = apply_transform(current, op)
            next_cost = cost + edge_cost
            if next_cost < distances.get(nxt, float("inf")):
                distances[nxt] = next_cost
                paths[nxt] = paths[current] + (op.name,)
                heapq.heappush(heap, (next_cost, serial, nxt))
                serial += 1
    return distances, paths


def factorized_plan(start: State, target: State) -> tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]:
    """A two-stage generative plan: place pieces, then set orientations.

    Returns expanded primitive operations and high-level macro commands.
    This is valid but not guaranteed to be shortest in primitive moves.
    """
    if not (validate_state(start) and validate_state(target)):
        raise ValueError("invalid start or target")
    current = start
    swaps: list[str] = []
    swap_by_name = {m.name: m for m in primitive_moves(True) if m.name.startswith("SWAP")}
    # Stable adjacent-swap insertion to realize the target piece arrangement.
    for desired_slot in range(N):
        desired_piece = target.perm[desired_slot]
        source_slot = current.perm.index(desired_piece)
        while source_slot > desired_slot:
            op_name = f"SWAP{source_slot-1}{source_slot}"
            current = apply_transform(current, swap_by_name[op_name])
            swaps.append(op_name)
            source_slot -= 1
    if current.perm != target.perm:
        raise AssertionError("permutation stage failed")

    twist_names = []
    all_moves = {m.name: m for m in primitive_moves(True)}
    for slot in range(N - 1):
        delta = (target.ori[slot] - current.ori[slot]) % MOD
        if delta == 1:
            op_name = f"TWIST{slot}+"
            current = apply_transform(current, all_moves[op_name])
            twist_names.append(op_name)
        elif delta == 2:
            op_name = f"TWIST{slot}-"
            current = apply_transform(current, all_moves[op_name])
            twist_names.append(op_name)
    if current != target:
        raise AssertionError("orientation stage failed")
    macros = (
        ("SET_LAYOUT", tuple(swaps)),
        ("SET_ORIENTATION", tuple(twist_names)),
    )
    expanded = tuple(swaps + twist_names)
    return expanded, macros


def apply_named_path(start: State, path: Iterable[str], ground: VirtualGround) -> State:
    current = start
    for name in path:
        current = ground.transition(current, name)
    return current


def observer_view(state: State, observer: str) -> tuple[int, ...]:
    if observer == "full":
        return tuple(state.perm) + tuple(state.ori)
    if observer == "layout":
        return tuple(state.perm)
    if observer == "orientation":
        return tuple(state.ori)
    raise KeyError(observer)


def quotient_classes(states: Iterable[State], observer: str) -> set[tuple[int, ...]]:
    return {observer_view(s, observer) for s in states}


def quotient_bfs(ground: VirtualGround, start: State, observer: str) -> dict[tuple[int, ...], int]:
    """BFS on observer classes; validates that the chosen view is transition-congruent."""
    states = all_states()
    classes = quotient_classes(states, observer)
    # Check that all representatives of one class produce the same next class
    # for each labelled action. Without this, a quotient is not well-defined.
    reps: dict[tuple[int, ...], State] = {}
    for s in states:
        reps.setdefault(observer_view(s, observer), s)
    for s in states:
        v = observer_view(s, observer)
        for op in ground.moves:
            nxt = observer_view(apply_transform(s, op), observer)
            rep_next = observer_view(apply_transform(reps[v], op), observer)
            if nxt != rep_next:
                raise ValueError(f"observer {observer} does not define a congruent quotient")
    start_view = observer_view(start, observer)
    dist = {start_view: 0}
    queue = deque([start_view])
    while queue:
        v = queue.popleft()
        rep = reps[v]
        for op in ground.moves:
            nv = observer_view(apply_transform(rep, op), observer)
            if nv not in dist:
                dist[nv] = dist[v] + 1
                queue.append(nv)
    return dist


def task_satisfied(state: State, target: State, intention: str) -> bool:
    return observer_view(state, intention) == observer_view(target, intention)


def stable_consensus(observations: Iterable[tuple[int, ...]], dwell: int) -> tuple[bool, tuple[int, ...] | None]:
    """Consensus as an observer-relative value retained for dwell consecutive samples."""
    if dwell < 1:
        raise ValueError("dwell must be >= 1")
    run_value = None
    run_length = 0
    for value in observations:
        if value == run_value:
            run_length += 1
        else:
            run_value = value
            run_length = 1
        if run_length >= dwell:
            return True, run_value
    return False, None



def shortest_plan_between(start: State, target: State, ground: VirtualGround) -> tuple[str, ...] | None:
    """Exact shortest path via the relative group element; None if unreachable."""
    if not (validate_state(start) and validate_state(target)):
        raise ValueError("invalid start or target")
    start_g = transform_of_state(start)
    target_g = transform_of_state(target)
    relative = compose(inverse(start_g), target_g, "relative")
    relative_state = state_of_transform(relative)
    _, paths = bfs_policy(ground, SOLVED)
    path = paths.get(relative_state)
    if path is None:
        return None
    if apply_named_path(start, path, ground) != target:
        raise AssertionError("relative transform did not map start to target")
    return path


def quotient_plan(start: State, target: State, ground: VirtualGround, observer: str) -> tuple[str, ...] | None:
    """Shortest action sequence to the target's observer class, not necessarily full state."""
    # Never navigate on a quotient until its transition congruence is verified.
    quotient_bfs(ground, start, observer)
    start_view = observer_view(start, observer)
    target_view = observer_view(target, observer)
    representatives: dict[tuple[int, ...], State] = {start_view: start}
    parent: dict[tuple[int, ...], tuple[tuple[int, ...] | None, str | None]] = {start_view: (None, None)}
    queue = deque([start_view])
    while queue and target_view not in parent:
        view = queue.popleft()
        representative = representatives[view]
        for op in ground.moves:
            next_state = apply_transform(representative, op)
            next_view = observer_view(next_state, observer)
            if next_view not in parent:
                parent[next_view] = (view, op.name)
                representatives[next_view] = next_state
                queue.append(next_view)
    if target_view not in parent:
        return None
    path = []
    cursor = target_view
    while cursor != start_view:
        previous, action = parent[cursor]
        path.append(action)
        cursor = previous
    path.reverse()
    result = apply_named_path(start, path, ground)
    if observer_view(result, observer) != target_view:
        raise AssertionError("quotient plan failed its observer goal")
    return tuple(path)


def coordinate_transition(code: int, operation_name: str, ground: VirtualGround) -> int:
    """Transition in integer coordinates, conjugate to the state transition."""
    state = decode_state(code)
    next_state = ground.transition(state, operation_name)
    return encode_state(next_state)


def observer_cost(path: Iterable[str], macros: tuple[tuple[str, tuple[str, ...]], ...] | None = None) -> dict:
    """Separate abstract command count from low-level execution count."""
    primitive = tuple(path)
    macro_list = tuple((name, tuple(expansion)) for name, expansion in (macros or ()))
    return {
        "primitive_steps": len(primitive),
        "macro_commands": sum(bool(expansion) for _, expansion in macro_list),
        "macro_expansion_steps": sum(len(expansion) for _, expansion in macro_list),
    }

def graph_edges(ground: VirtualGround) -> set[tuple[State, str, State]]:
    return {
        (s, op.name, apply_transform(s, op))
        for s in all_states()
        for op in ground.moves
    }


def ground_descriptor(ground: VirtualGround) -> dict:
    return {
        "name": ground.name,
        "version": ground.version,
        "state_encoding": "4-piece permutation x four Z3 orientations with sum zero",
        "state_count": ground.state_count,
        "operations": [
            {"name": m.name, "dest": list(m.dest), "twist": list(m.twist)}
            for m in ground.moves
        ],
        "invariant": "sum(orientation) == 0 mod 3",
        "observers": list(ground.observer_names),
    }
