"""Build 21: environment-coupled Virtual Ground with control/flow separation.

A finite deterministic canal fixture. This is an abstract discrete model, not a
hydraulic simulator. Standard library only.
"""
from __future__ import annotations

from collections import deque, defaultdict
from dataclasses import dataclass
from functools import lru_cache
import heapq
from typing import Callable, Iterable, NamedTuple


ACTIONS = ("HOLD", "A_TO_B", "B_TO_A")
OBSERVERS = ("FULL", "LEVELS", "TOTAL", "TOTAL_PHASE", "PHASE")


class FlowState(NamedTuple):
    a: int
    b: int
    phase: int


@dataclass(frozen=True)
class StepLedger:
    action: str
    requested_transfer: int
    actual_transfer: int
    inflow: int
    requested_demand: int
    actual_demand: int
    spill: int
    unmet_demand: int
    before_total: int
    after_total: int

    @property
    def mass_balance_residual(self) -> int:
        return self.after_total - (
            self.before_total + self.inflow - self.actual_demand - self.spill
        )


@dataclass(frozen=True)
class FlowGround:
    """Generative rules, structural limits, and exogenous forcing law."""
    name: str = "Flow-2"
    version: int = 1
    capacity: int = 3
    inflow: tuple[int, ...] = (1, 0, 0, 1)
    demand: tuple[int, ...] = (0, 1, 0, 0)
    phase_next: tuple[int, ...] = (1, 2, 3, 0)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be positive")
        if not self.inflow or len(self.inflow) != len(self.demand):
            raise ValueError("inflow and demand schedules must have equal nonzero length")
        n = len(self.inflow)
        if len(self.phase_next) != n or sorted(self.phase_next) != list(range(n)):
            raise ValueError("phase_next must be a permutation of phases")
        if any(x < 0 for x in self.inflow + self.demand):
            raise ValueError("environmental rates must be nonnegative integers")

    @property
    def phase_count(self) -> int:
        return len(self.inflow)

    @property
    def structural_descriptor(self) -> tuple:
        return (self.capacity, self.inflow, self.demand, self.phase_next, ACTIONS)

    def validate(self, s: FlowState) -> bool:
        return (
            isinstance(s, FlowState)
            and 0 <= s.a <= self.capacity
            and 0 <= s.b <= self.capacity
            and 0 <= s.phase < self.phase_count
        )

    def legal_actions(self, s: FlowState) -> tuple[str, ...]:
        if not self.validate(s):
            raise ValueError("state is outside this ground")
        out = ["HOLD"]
        if s.a > 0 and s.b < self.capacity:
            out.append("A_TO_B")
        if s.b > 0 and s.a < self.capacity:
            out.append("B_TO_A")
        return tuple(out)

    def step_with_ledger(self, s: FlowState, action: str) -> tuple[FlowState, StepLedger]:
        if action not in self.legal_actions(s):
            raise ValueError(f"illegal action {action} at {s}")
        a, b = s.a, s.b
        requested = 0
        actual = 0
        if action == "A_TO_B":
            requested = 1
            a -= 1
            b += 1
            actual = 1
        elif action == "B_TO_A":
            requested = -1
            b -= 1
            a += 1
            actual = -1

        inflow = self.inflow[s.phase]
        demand = self.demand[s.phase]
        raw_a = a + inflow
        spill = max(0, raw_a - self.capacity)
        a_next = min(self.capacity, raw_a)
        raw_b = b - demand
        unmet = max(0, -raw_b)
        b_next = max(0, raw_b)
        demand_actual = b - b_next
        nxt = FlowState(a_next, b_next, self.phase_next[s.phase])
        if not self.validate(nxt):
            raise AssertionError("transition violated ground state constraints")
        ledger = StepLedger(
            action=action,
            requested_transfer=requested,
            actual_transfer=actual,
            inflow=inflow,
            requested_demand=demand,
            actual_demand=demand_actual,
            spill=spill,
            unmet_demand=unmet,
            before_total=s.a + s.b,
            after_total=nxt.a + nxt.b,
        )
        if ledger.mass_balance_residual != 0:
            raise AssertionError("mass balance invariant violated")
        return nxt, ledger

    def transition(self, s: FlowState, action: str) -> FlowState:
        return self.step_with_ledger(s, action)[0]

    def revise_capacity(self, capacity: int) -> "FlowGround":
        return FlowGround(
            name=f"{self.name}-capacity-{capacity}", version=self.version + 1,
            capacity=capacity, inflow=self.inflow, demand=self.demand,
            phase_next=self.phase_next,
        )

    def revise_environment(
        self, inflow: tuple[int, ...] | None = None,
        demand: tuple[int, ...] | None = None,
    ) -> "FlowGround":
        return FlowGround(
            name=f"{self.name}-environment-revised", version=self.version + 1,
            capacity=self.capacity,
            inflow=self.inflow if inflow is None else inflow,
            demand=self.demand if demand is None else demand,
            phase_next=self.phase_next,
        )

    def all_states(self) -> tuple[FlowState, ...]:
        return tuple(
            FlowState(a, b, p)
            for a in range(self.capacity + 1)
            for b in range(self.capacity + 1)
            for p in range(self.phase_count)
        )


@dataclass(frozen=True)
class VariablePartition:
    structural: tuple[str, ...]
    controlled: tuple[str, ...]
    endogenous: tuple[str, ...]
    exogenous: tuple[str, ...]


FLOW_PARTITION = VariablePartition(
    structural=("capacity", "legal-action-rules", "mass-balance-law", "phase-transition-law"),
    controlled=("gate_command",),
    endogenous=("reservoir_a", "reservoir_b", "actual_transfer", "spill", "unmet_demand"),
    exogenous=("inflow_schedule", "demand_schedule", "environment_phase"),
)


def observe(s: FlowState, observer: str) -> tuple[int, ...]:
    if observer == "FULL":
        return (s.a, s.b, s.phase)
    if observer == "LEVELS":
        return (s.a, s.b)
    if observer == "TOTAL":
        return (s.a + s.b,)
    if observer == "TOTAL_PHASE":
        return (s.a + s.b, s.phase)
    if observer == "PHASE":
        return (s.phase,)
    raise KeyError(observer)


def reachable_states(ground: FlowGround, start: FlowState) -> tuple[FlowState, ...]:
    if not ground.validate(start):
        raise ValueError("invalid start")
    seen = {start}
    q = deque([start])
    while q:
        s = q.popleft()
        for action in ground.legal_actions(s):
            n = ground.transition(s, action)
            if n not in seen:
                seen.add(n)
                q.append(n)
    return tuple(sorted(seen))


def reachable_edges(ground: FlowGround, states: Iterable[FlowState]) -> int:
    return sum(len(ground.legal_actions(s)) for s in states)


def partition_refinement(
    ground: FlowGround, observer: str, states: Iterable[FlowState] | None = None,
) -> dict:
    """Compute the coarsest strong action-labelled bisimulation refining observation.

    The output partition is a diagnostic of the observer's predictive sufficiency.
    Splits imply hidden distinctions the sensor does not directly expose.
    """
    ss = tuple(ground.all_states() if states is None else states)
    obs_values = {s: observe(s, observer) for s in ss}
    unique_obs = sorted(set(obs_values.values()))
    obs_ids = {v: i for i, v in enumerate(unique_obs)}
    blocks = {s: obs_ids[obs_values[s]] for s in ss}
    rounds = 0
    while True:
        signatures = {}
        for s in ss:
            trans = []
            for action in ACTIONS:
                if action not in ground.legal_actions(s):
                    trans.append((action, "disabled"))
                else:
                    trans.append((action, blocks[ground.transition(s, action)]))
            signatures[s] = (obs_values[s], tuple(trans))
        sig_values = sorted(set(signatures.values()), key=repr)
        sig_ids = {v: i for i, v in enumerate(sig_values)}
        new_blocks = {s: sig_ids[signatures[s]] for s in ss}
        # Compare equivalence relations, not raw label numbers.
        same = all(
            (blocks[s1] == blocks[s2]) == (new_blocks[s1] == new_blocks[s2])
            for i, s1 in enumerate(ss) for s2 in ss[i:]
        )
        blocks = new_blocks
        rounds += 1
        if same:
            break
        if rounds > len(ss) + 1:
            raise AssertionError("partition refinement failed to converge")
    by_block: dict[int, list[FlowState]] = defaultdict(list)
    for s, b in blocks.items():
        by_block[b].append(s)
    return {
        "observer": observer,
        "initial_observation_classes": len(unique_obs),
        "refined_predictive_classes": len(by_block),
        "refinement_rounds": rounds,
        "split_count": len(by_block) - len(unique_obs),
        "blocks": {k: tuple(v) for k, v in by_block.items()},
        "block_of": blocks,
    }


def task_observability(
    ground: FlowGround, observer: str, goal: Callable[[FlowState], bool],
) -> dict:
    states = ground.all_states()
    groups: dict[tuple[int, ...], list[FlowState]] = defaultdict(list)
    for s in states:
        groups[observe(s, observer)].append(s)
    mixed = []
    for key, group in groups.items():
        vals = {bool(goal(s)) for s in group}
        if len(vals) > 1:
            mixed.append({"observation": key, "target_and_non_target": len(group)})
    partition = partition_refinement(ground, observer, states)
    return {
        "observer": observer,
        "task_goal_is_observable": not mixed,
        "mixed_goal_observation_classes": mixed,
        "transition_congruent_without_refinement": partition["split_count"] == 0,
        "predictive_refinement_classes": partition["refined_predictive_classes"],
    }


def belief_for_observation(ground: FlowGround, observer: str, value: tuple[int, ...]) -> frozenset[FlowState]:
    return frozenset(s for s in ground.all_states() if observe(s, observer) == value)


def robust_belief_plan(
    ground: FlowGround,
    belief: frozenset[FlowState],
    observer: str,
    goal: Callable[[FlowState], bool],
    max_depth: int = 12,
) -> dict | None:
    """Find a worst-case observation-contingent policy for a finite belief.

    An action must be legal in every state still considered possible. Each next
    observation creates a branch. Returns None if no policy meets max_depth.
    """
    if not belief:
        return None

    @lru_cache(maxsize=None)
    def solve(b: frozenset[FlowState], depth: int):
        if all(goal(s) for s in b):
            return (0, None, {})
        if depth <= 0:
            return None
        common = set(ACTIONS)
        for s in b:
            common &= set(ground.legal_actions(s))
        best = None
        for action in sorted(common):
            next_states = {ground.transition(s, action) for s in b}
            groups: dict[tuple[int, ...], set[FlowState]] = defaultdict(set)
            for n in next_states:
                groups[observe(n, observer)].add(n)
            branches = {}
            worst = 0
            feasible = True
            for obs, group in sorted(groups.items()):
                result = solve(frozenset(group), depth - 1)
                if result is None:
                    feasible = False
                    break
                branches[obs] = result
                worst = max(worst, result[0])
            if feasible:
                candidate = (1 + worst, action, branches)
                if best is None or candidate[0] < best[0]:
                    best = candidate
        return best

    result = solve(belief, max_depth)
    if result is None:
        return None
    return {
        "worst_case_steps": result[0],
        "first_action": result[1],
        "belief_nodes_expanded": solve.cache_info().currsize,
        "branches": result[2],
    }


def verify_belief_policy(
    ground: FlowGround,
    belief: frozenset[FlowState],
    observer: str,
    goal: Callable[[FlowState], bool],
    policy: dict,
) -> dict:
    """Independently verify every branch of a compiled robust belief policy."""
    def walk(b: frozenset[FlowState], node) -> int:
        depth, action, branches = node
        if all(goal(s) for s in b):
            if depth != 0 or action is not None or branches:
                raise AssertionError("terminal policy node is malformed")
            return 0
        if action is None or any(action not in ground.legal_actions(s) for s in b):
            raise AssertionError("policy action is not enabled for every possible state")
        next_states = {ground.transition(s, action) for s in b}
        groups: dict[tuple[int, ...], set[FlowState]] = defaultdict(set)
        for nxt in next_states:
            groups[observe(nxt, observer)].add(nxt)
        if set(groups) != set(branches):
            raise AssertionError("policy does not cover every possible next observation")
        child_depths = []
        for obs, group in groups.items():
            child_depths.append(walk(frozenset(group), branches[obs]))
        expected = 1 + max(child_depths, default=0)
        if depth != expected:
            raise AssertionError("declared worst-case depth does not match policy branches")
        return expected

    node = (policy["worst_case_steps"], policy["first_action"], policy["branches"])
    depth = walk(belief, node)
    return {"verified": True, "worst_case_steps": depth, "initial_belief_size": len(belief)}


def compile_navigation_task(
    ground: FlowGround,
    observer: str,
    initial_observation: tuple[int, ...],
    goal: Callable[[FlowState], bool],
    max_depth: int = 16,
) -> dict:
    """Small executable compiler stage: observation -> belief -> robust policy.

    This is finite-domain compilation, not the general Virtual Ground compiler.
    """
    belief = belief_for_observation(ground, observer, initial_observation)
    if not belief:
        return {"compiled": False, "reason": "observation has no matching ground states"}
    policy = robust_belief_plan(ground, belief, observer, goal, max_depth)
    if policy is None:
        return {
            "compiled": False,
            "reason": "no robust policy exists within the declared horizon",
            "initial_belief_size": len(belief),
        }
    certificate = verify_belief_policy(ground, belief, observer, goal, policy)
    return {
        "compiled": True,
        "ground_version": ground.version,
        "observer": observer,
        "initial_observation": initial_observation,
        "initial_belief_size": len(belief),
        "policy": policy,
        "certificate": certificate,
    }


@dataclass(frozen=True)
class ResourceProfile:
    name: str
    time_weight: float = 1.0
    energy_weight: float = 0.0
    communication_weight: float = 0.0
    max_time: float | None = None
    max_energy: float | None = None


DEFAULT_ACTION_COSTS = {
    "HOLD": (1.0, 0.0, 0.0),
    "A_TO_B": (1.0, 3.0, 1.0),
    "B_TO_A": (1.0, 1.0, 1.0),
}


def pareto_routes(
    ground: FlowGround,
    start: FlowState,
    goal: Callable[[FlowState], bool],
    costs: dict[str, tuple[float, float, float]] = DEFAULT_ACTION_COSTS,
    max_labels: int = 100000,
) -> list[dict]:
    """Enumerate nondominated (time, energy, communication) route labels."""
    if not ground.validate(start):
        raise ValueError("invalid start")
    labels: dict[FlowState, list[tuple[tuple[float, float, float], tuple[str, ...]]]] = defaultdict(list)
    initial = (0.0, 0.0, 0.0)
    labels[start].append((initial, ()))
    heap = [(0.0, 0.0, 0.0, 0, start, ())]
    serial = 1
    expansions = 0
    while heap:
        t, e, c, _, state, path = heapq.heappop(heap)
        vec = (t, e, c)
        if not any(v == vec and p == path for v, p in labels[state]):
            continue
        expansions += 1
        if expansions > max_labels:
            raise RuntimeError("Pareto label cap exceeded")
        for action in ground.legal_actions(state):
            nxt = ground.transition(state, action)
            delta = costs[action]
            nv = (t + delta[0], e + delta[1], c + delta[2])
            existing = labels[nxt]
            if any(all(x <= y for x, y in zip(v, nv)) for v, _ in existing):
                continue
            labels[nxt] = [(v, p) for v, p in existing if not all(x <= y for x, y in zip(nv, v))]
            np = path + (action,)
            labels[nxt].append((nv, np))
            heapq.heappush(heap, (*nv, serial, nxt, np))
            serial += 1
    out = []
    for state, entries in labels.items():
        if goal(state):
            for vec, path in entries:
                out.append({"target": state, "cost": vec, "path": path})
    # Remove dominance across different target states too; goal-equivalent states
    # are all valid target outcomes.
    frontier = []
    for item in sorted(out, key=lambda x: (sum(x["cost"]), x["cost"], x["path"])):
        v = item["cost"]
        if any(all(a <= b for a, b in zip(x["cost"], v)) for x in frontier):
            continue
        frontier = [x for x in frontier if not all(a <= b for a, b in zip(v, x["cost"]))]
        frontier.append(item)
    return frontier


def choose_route(routes: list[dict], profile: ResourceProfile) -> dict | None:
    feasible = []
    for r in routes:
        t, e, c = r["cost"]
        if profile.max_time is not None and t > profile.max_time:
            continue
        if profile.max_energy is not None and e > profile.max_energy:
            continue
        score = (
            profile.time_weight * t + profile.energy_weight * e
            + profile.communication_weight * c
        )
        feasible.append((score, r))
    return min(feasible, key=lambda x: x[0])[1] if feasible else None


def migration_report(old: FlowGround, new: FlowGround) -> dict:
    states = old.all_states()
    valid = [s for s in states if new.validate(s)]
    lost = [s for s in states if not new.validate(s)]
    return {
        "old_version": old.version,
        "new_version": new.version,
        "old_state_count": len(states),
        "new_state_count": len(new.all_states()),
        "directly_migratable_states": len(valid),
        "unmappable_states": len(lost),
        "migration_is_total": not lost,
        "lost_examples": [tuple(s) for s in lost[:8]],
        "law_changed": old.structural_descriptor != new.structural_descriptor,
    }


def controlled_invariant_kernel(ground: FlowGround, safe: Callable[[FlowState], bool]) -> frozenset[FlowState]:
    """Greatest fixed point of states from which safety can be maintained forever."""
    kernel = {s for s in ground.all_states() if safe(s)}
    while True:
        keep = {
            s for s in kernel
            if any(ground.transition(s, a) in kernel for a in ground.legal_actions(s))
        }
        if keep == kernel:
            return frozenset(kernel)
        kernel = keep


def viability_policy(
    ground: FlowGround, kernel: frozenset[FlowState],
) -> dict[FlowState, str]:
    """Choose one action per controlled-viable state that stays in the kernel."""
    policy = {}
    for s in sorted(kernel):
        safe_actions = [
            a for a in ground.legal_actions(s)
            if ground.transition(s, a) in kernel
        ]
        if not safe_actions:
            raise AssertionError("kernel contains a state with no safe control")
        policy[s] = safe_actions[0]
    return policy


def autonomous_invariant_kernel(ground: FlowGround, safe: Callable[[FlowState], bool]) -> frozenset[FlowState]:
    """States safe forever when only environmental HOLD evolution is allowed."""
    kernel = {s for s in ground.all_states() if safe(s)}
    while True:
        keep = {s for s in kernel if ground.transition(s, "HOLD") in kernel}
        if keep == kernel:
            return frozenset(kernel)
        kernel = keep


def verify_ground(ground: FlowGround) -> dict:
    states = ground.all_states()
    transitions = 0
    max_mass_residual = 0
    for s in states:
        for action in ground.legal_actions(s):
            nxt, ledger = ground.step_with_ledger(s, action)
            transitions += 1
            max_mass_residual = max(max_mass_residual, abs(ledger.mass_balance_residual))
            if not ground.validate(nxt):
                raise AssertionError("invalid transition result")
    return {
        "state_count": len(states),
        "directed_transition_count": transitions,
        "max_mass_balance_residual": max_mass_residual,
        "all_transitions_valid": True,
    }
