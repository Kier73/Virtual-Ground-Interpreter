"""Build 22: active discovery of finite Virtual Grounds.

The experiment distinguishes hidden ground parameters from the observed state,
chooses calibrated probes by expected information gain per resource cost, and
proposes (but never silently commits) a new ground version after persistent,
independently supported model conflict.

Standard-library only. Synthetic discrete model; not a physical simulator.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from itertools import product
import math
from typing import Iterable, NamedTuple


ACTIONS = ("HOLD", "A_TO_B", "B_TO_A")
SENSORS = ("TOTAL", "LEVELS", "FULL")

INFLOW_LAWS = {
    "inflow_A": (1, 0, 0, 1),
    "inflow_B": (0, 1, 1, 0),
    # Reserved out-of-family law used only to test model rejection.
    "inflow_C": (1, 1, 1, 1),
}
DEMAND_LAWS = {
    "demand_A": (0, 1, 0, 0),
    "demand_B": (1, 0, 0, 1),
}
CANDIDATE_INFLOW_NAMES = ("inflow_A", "inflow_B")
CANDIDATE_DEMAND_NAMES = ("demand_A", "demand_B")


class State(NamedTuple):
    a: int
    b: int
    phase: int


@dataclass(frozen=True)
class GroundHypothesis:
    capacity: int
    inflow_name: str
    demand_name: str
    transfer_quantum: int
    phase_stride: int
    version: int = 1

    @property
    def inflow(self) -> tuple[int, ...]:
        return INFLOW_LAWS[self.inflow_name]

    @property
    def demand(self) -> tuple[int, ...]:
        return DEMAND_LAWS[self.demand_name]

    @property
    def identifier(self) -> str:
        return (
            f"C{self.capacity}-{self.inflow_name}-{self.demand_name}-"
            f"Q{self.transfer_quantum}-P{self.phase_stride}-V{self.version}"
        )

    def valid(self, s: State) -> bool:
        return 0 <= s.a <= self.capacity and 0 <= s.b <= self.capacity and 0 <= s.phase < 4

    def step(self, s: State, action: str) -> tuple[State, dict]:
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        if not self.valid(s):
            raise ValueError(f"invalid initial state {s} for {self.identifier}")

        a, b = s.a, s.b
        requested = 0
        actual = 0
        if action == "A_TO_B":
            requested = self.transfer_quantum
            actual = min(requested, a, self.capacity - b)
            a -= actual
            b += actual
        elif action == "B_TO_A":
            requested = self.transfer_quantum
            actual = min(requested, b, self.capacity - a)
            b -= actual
            a += actual

        inflow = self.inflow[s.phase]
        demand = self.demand[s.phase]
        raw_a = a + inflow
        spill = max(0, raw_a - self.capacity)
        a_next = min(self.capacity, raw_a)
        actual_demand = min(b, demand)
        b_next = b - actual_demand
        unmet = demand - actual_demand
        nxt = State(a_next, b_next, (s.phase + self.phase_stride) % 4)
        if not self.valid(nxt):
            raise AssertionError("generated state violates ground constraints")

        # Gate transfer is internal and cancels in the total balance.
        before_total = s.a + s.b
        after_total = nxt.a + nxt.b
        residual = after_total - (before_total + inflow - actual_demand - spill)
        if residual != 0:
            raise AssertionError(f"mass balance residual {residual}")

        ledger = {
            "requested_transfer": requested,
            "actual_transfer": actual,
            "inflow": inflow,
            "requested_demand": demand,
            "actual_demand": actual_demand,
            "unmet_demand": unmet,
            "spill": spill,
            "mass_balance_residual": residual,
        }
        return nxt, ledger

    def revised(self, **changes) -> "GroundHypothesis":
        values = asdict(self)
        values.update(changes)
        values["version"] = self.version + 1
        return GroundHypothesis(**values)


@dataclass(frozen=True)
class Probe:
    initial: State
    action: str
    sensor: str

    @property
    def identifier(self) -> str:
        return f"{tuple(self.initial)}|{self.action}|{self.sensor}"


DEFAULT_COST_MODEL = {
    "reset": 1.0,
    "action": {"HOLD": 0.25, "A_TO_B": 1.0, "B_TO_A": 1.0},
    "sensor": {"TOTAL": 0.75, "LEVELS": 1.5, "FULL": 2.0},
}


def observe(s: State, sensor: str) -> tuple[int, ...]:
    if sensor == "TOTAL":
        return (s.a + s.b,)
    if sensor == "LEVELS":
        return (s.a, s.b)
    if sensor == "FULL":
        return (s.a, s.b, s.phase)
    raise KeyError(sensor)


def candidate_grounds(version: int = 1) -> tuple[GroundHypothesis, ...]:
    rows = [
        GroundHypothesis(c, i, d, q, p, version)
        for c, i, d, q, p in product(
            (2, 3), CANDIDATE_INFLOW_NAMES, CANDIDATE_DEMAND_NAMES, (1, 2), (1, 2)
        )
    ]
    return tuple(sorted(rows, key=lambda h: h.identifier))


def probe_catalog() -> tuple[Probe, ...]:
    # The experiment can reset reservoir levels and wait for / identify a phase.
    # Initial levels are <= 2, hence valid in every candidate ground.
    probes = []
    for a, b, phase, action, sensor in product(range(3), range(3), range(4), ACTIONS, SENSORS):
        probes.append(Probe(State(a, b, phase), action, sensor))
    return tuple(probes)


def probe_cost(probe: Probe, cost_model: dict | None = None) -> float:
    model = DEFAULT_COST_MODEL if cost_model is None else cost_model
    return float(model["reset"] + model["action"][probe.action] + model["sensor"][probe.sensor])


def entropy_bits(weights: Iterable[float]) -> float:
    vals = [w for w in weights if w > 0]
    total = sum(vals)
    if total <= 0:
        return 0.0
    return -sum((w / total) * math.log2(w / total) for w in vals)


def predict(h: GroundHypothesis, probe: Probe) -> tuple[int, ...]:
    nxt, _ = h.step(probe.initial, probe.action)
    return observe(nxt, probe.sensor)


def partition_hypotheses(
    hypotheses: Iterable[GroundHypothesis], probe: Probe
) -> dict[tuple[int, ...], tuple[GroundHypothesis, ...]]:
    groups: dict[tuple[int, ...], list[GroundHypothesis]] = defaultdict(list)
    for h in hypotheses:
        groups[predict(h, probe)].append(h)
    return {k: tuple(v) for k, v in groups.items()}


def probe_information_gain(
    hypotheses: Iterable[GroundHypothesis], probe: Probe
) -> float:
    hs = tuple(hypotheses)
    if not hs:
        return 0.0
    groups = partition_hypotheses(hs, probe)
    # Deterministic observation of a uniformly sampled model: IG = H(output).
    return entropy_bits(len(g) for g in groups.values())


def choose_probe(
    hypotheses: Iterable[GroundHypothesis], probes: Iterable[Probe] | None = None,
    cost_model: dict | None = None,
) -> tuple[Probe | None, dict]:
    hs = tuple(hypotheses)
    if len(hs) <= 1:
        return None, {"information_gain_bits": 0.0, "score_per_cost": 0.0}
    catalog = tuple(probe_catalog() if probes is None else probes)
    best = None
    for probe in catalog:
        ig = probe_information_gain(hs, probe)
        if ig <= 1e-12:
            continue
        cost = probe_cost(probe, cost_model)
        score = ig / cost
        candidate = (score, ig, -cost, probe.identifier, probe, cost)
        if best is None or candidate[:4] > best[:4]:
            best = candidate
    if best is None:
        return None, {"information_gain_bits": 0.0, "score_per_cost": 0.0}
    return best[4], {
        "information_gain_bits": best[1],
        "probe_cost": best[5],
        "score_per_cost": best[0],
        "remaining_hypotheses": len(hs),
        "predicted_outcomes": len(partition_hypotheses(hs, best[4])),
    }


def update_hypotheses(
    hypotheses: Iterable[GroundHypothesis], probe: Probe, observation: tuple[int, ...]
) -> tuple[GroundHypothesis, ...]:
    return tuple(h for h in hypotheses if predict(h, probe) == observation)


def run_active_identification(
    true_ground: GroundHypothesis,
    max_probes: int = 12,
    cost_model: dict | None = None,
) -> dict:
    hypotheses = candidate_grounds(true_ground.version)
    trace = []
    total_cost = 0.0
    total_expected_ig = 0.0
    realized_entropy_reduction = 0.0
    for index in range(max_probes):
        if len(hypotheses) <= 1:
            break
        probe, score = choose_probe(hypotheses, cost_model=cost_model)
        if probe is None:
            break
        actual_state, _ = true_ground.step(probe.initial, probe.action)
        observation = observe(actual_state, probe.sensor)
        before = len(hypotheses)
        before_entropy = math.log2(before)
        survivors = update_hypotheses(hypotheses, probe, observation)
        after = len(survivors)
        after_entropy = math.log2(after) if after else None
        realized_reduction = before_entropy - after_entropy if after_entropy is not None else None
        total_cost += probe_cost(probe, cost_model)
        total_expected_ig += score["information_gain_bits"]
        if realized_reduction is not None:
            realized_entropy_reduction += realized_reduction
        trace.append({
            "index": index + 1,
            "probe": probe.identifier,
            "initial": list(probe.initial),
            "action": probe.action,
            "sensor": probe.sensor,
            "observation": list(observation),
            "hypotheses_before": before,
            "hypotheses_after": after,
            "prior_entropy_bits": before_entropy,
            "posterior_entropy_bits": after_entropy,
            "expected_information_gain_bits": score["information_gain_bits"],
            "realized_entropy_reduction_bits": realized_reduction,
            "cost": probe_cost(probe, cost_model),
            "score_per_cost": score["score_per_cost"],
        })
        hypotheses = survivors
        if not hypotheses:
            return {
                "status": "candidate_family_rejected",
                "true_ground": true_ground.identifier,
                "identified": False,
                "remaining_hypotheses": 0,
                "remaining_ids": [],
                "probe_count": len(trace),
                "total_probe_cost": total_cost,
                "sum_expected_information_gain_bits": total_expected_ig,
                "realized_entropy_reduction_bits": realized_entropy_reduction,
                "trace": trace,
                "rejection_observation": list(observation),
                "rejection_probe": probe.identifier,
            }
    return {
        "status": "identified_within_candidate_family" if len(hypotheses) == 1 else "ambiguous_within_probe_catalog",
        "true_ground": true_ground.identifier,
        "identified": len(hypotheses) == 1,
        "remaining_hypotheses": len(hypotheses),
        "remaining_ids": [h.identifier for h in hypotheses],
        "probe_count": len(trace),
        "total_probe_cost": total_cost,
        "sum_expected_information_gain_bits": total_expected_ig,
        "realized_entropy_reduction_bits": realized_entropy_reduction,
        "trace": trace,
    }


def run_passive_identification(
    true_ground: GroundHypothesis,
    steps: int = 12,
    initial: State = State(1, 1, 0),
    sensor: str = "FULL",
) -> dict:
    """Fixed no-gate trajectory. Observes a naturally evolving environment."""
    hypotheses = [(h, initial) for h in candidate_grounds(true_ground.version) if h.valid(initial)]
    actual_state = initial
    trace = []
    for index in range(steps):
        actual_state, _ = true_ground.step(actual_state, "HOLD")
        observation = observe(actual_state, sensor)
        before = len(hypotheses)
        survivors = []
        for h, s in hypotheses:
            nxt, _ = h.step(s, "HOLD")
            if observe(nxt, sensor) == observation:
                survivors.append((h, nxt))
        hypotheses = survivors
        if not hypotheses:
            raise AssertionError("true ground was eliminated by passive observation")
        trace.append({
            "index": index + 1,
            "action": "HOLD",
            "sensor": sensor,
            "observation": list(observation),
            "hypotheses_before": before,
            "hypotheses_after": len(hypotheses),
        })
    remaining = [h for h, _ in hypotheses]
    return {
        "true_ground": true_ground.identifier,
        "identified": len(remaining) == 1,
        "remaining_hypotheses": len(remaining),
        "remaining_ids": [h.identifier for h in remaining],
        "steps": len(trace),
        "trace": trace,
    }


def behavioral_equivalence_classes(
    hypotheses: Iterable[GroundHypothesis], probes: Iterable[Probe] | None = None
) -> tuple[tuple[str, ...], ...]:
    """Group models that agree on every experiment in the declared probe catalogue."""
    hs = tuple(hypotheses)
    catalog = tuple(probe_catalog() if probes is None else probes)
    groups: dict[tuple, list[str]] = defaultdict(list)
    for h in hs:
        signature = tuple(predict(h, p) for p in catalog)
        groups[signature].append(h.identifier)
    return tuple(sorted((tuple(sorted(v)) for v in groups.values()), key=lambda x: x[0]))


@dataclass
class ChangeEvidence:
    """Conservative version-shift monitor: anomalies are quarantined first."""
    conflict_streak: int = 0
    conflict_records: list[dict] | None = None
    proposed: bool = False

    def __post_init__(self):
        if self.conflict_records is None:
            self.conflict_records = []

    def ingest(
        self,
        old_candidates: Iterable[GroundHypothesis],
        probe: Probe,
        observation: tuple[int, ...],
        revised_candidates: Iterable[GroundHypothesis] = (),
    ) -> dict:
        old_candidates = tuple(old_candidates)
        revised_candidates = tuple(revised_candidates)
        old_ok = [h.identifier for h in old_candidates if predict(h, probe) == observation]
        new_ok = [h.identifier for h in revised_candidates if predict(h, probe) == observation]
        if old_ok:
            self.conflict_streak = 0
            self.conflict_records = []
            return {"status": "consistent_with_current_ground", "old_matches": old_ok, "new_matches": new_ok}

        self.conflict_streak += 1
        self.conflict_records.append({"probe": probe.identifier, "probe_obj": probe, "observation": list(observation), "new_matches": new_ok})
        if self.conflict_streak == 1:
            return {"status": "quarantined_single_conflict", "old_matches": [], "new_matches": new_ok}

        # Revision proposal requires at least two distinct probes, and a common
        # revised candidate must explain all quarantined observations.
        distinct = len({r["probe"] for r in self.conflict_records}) >= 2
        revised = tuple(revised_candidates)
        common = [
            h.identifier for h in revised
            if all(
                predict(h, rec["probe_obj"]) == tuple(rec["observation"])
                for rec in self.conflict_records
            )
        ] if distinct else []
        if distinct and common:
            self.proposed = True
            return {"status": "ground_revision_candidate", "old_matches": [], "revised_matches": common}
        return {"status": "persistent_conflict_unresolved", "old_matches": [], "new_matches": new_ok}


def full_parameter_dict(h: GroundHypothesis) -> dict:
    return asdict(h) | {"identifier": h.identifier, "inflow": h.inflow, "demand": h.demand}
