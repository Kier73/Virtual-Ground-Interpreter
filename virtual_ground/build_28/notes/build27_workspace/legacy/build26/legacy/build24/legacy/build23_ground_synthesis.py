"""Build 23: bounded inductive synthesis of finite Virtual Grounds.

Learns a generative transition program from state/action/next-state records.
The learner is not given a candidate catalogue. It infers capacity evidence,
phase progression, environmental schedules, and action-transfer laws, then
compresses those laws into a small exact expression grammar.

Standard library only. All experiments are synthetic, finite and deterministic.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from itertools import product
from typing import Iterable, NamedTuple
import math

ACTIONS = ("HOLD", "A_TO_B", "B_TO_A")


class State(NamedTuple):
    a: int
    b: int
    phase: int


@dataclass(frozen=True)
class TransitionRecord:
    state: State
    action: str
    next_state: State

    def as_dict(self) -> dict:
        return {
            "state": list(self.state),
            "action": self.action,
            "next_state": list(self.next_state),
        }


@dataclass(frozen=True)
class HiddenGround:
    """Synthetic data-generating ground; never passed to the learner."""
    capacity: int
    inflow: tuple[int, ...]
    demand: tuple[int, ...]
    phase_next: tuple[int, ...]
    transfer_by_phase_residue: tuple[tuple[int, ...], ...]
    transfer_modulus: int = 1
    name: str = "hidden"

    @property
    def period(self) -> int:
        return len(self.inflow)

    def quantum(self, phase: int, source_level: int) -> int:
        return self.transfer_by_phase_residue[phase][source_level % self.transfer_modulus]

    def step(self, state: State, action: str) -> State:
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        if not (0 <= state.a <= self.capacity and 0 <= state.b <= self.capacity and 0 <= state.phase < self.period):
            raise ValueError(f"invalid state: {state}")
        a, b, p = state
        q_ab = self.quantum(p, a)
        q_ba = self.quantum(p, b)
        ab = min(q_ab, a, self.capacity - b) if action == "A_TO_B" else 0
        ba = min(q_ba, b, self.capacity - a) if action == "B_TO_A" else 0
        a_pre = a - ab + ba
        b_pre = b + ab - ba
        raw_a = a_pre + self.inflow[p]
        spill = max(0, raw_a - self.capacity)
        a_next = min(self.capacity, raw_a)
        demand_actual = min(b_pre, self.demand[p])
        b_next = b_pre - demand_actual
        return State(a_next, b_next, self.phase_next[p])

    def ledger(self, state: State, action: str) -> dict:
        a, b, p = state
        q_ab = self.quantum(p, a)
        q_ba = self.quantum(p, b)
        ab = min(q_ab, a, self.capacity - b) if action == "A_TO_B" else 0
        ba = min(q_ba, b, self.capacity - a) if action == "B_TO_A" else 0
        a_pre = a - ab + ba
        b_pre = b + ab - ba
        raw_a = a_pre + self.inflow[p]
        spill = max(0, raw_a - self.capacity)
        demand_actual = min(b_pre, self.demand[p])
        nxt = self.step(state, action)
        residual = nxt.a + nxt.b - (a + b + self.inflow[p] - demand_actual - spill)
        return {
            "transfer_ab": ab, "transfer_ba": ba,
            "inflow": self.inflow[p], "requested_demand": self.demand[p],
            "actual_demand": demand_actual, "spill": spill,
            "unmet_demand": self.demand[p] - demand_actual,
            "mass_balance_residual": residual,
        }


@dataclass(frozen=True)
class SequenceLaw:
    mode: str
    values: tuple[int, ...]
    params: tuple[int, ...] = ()

    def evaluate(self, phase: int) -> int:
        n = len(self.values)
        if not 0 <= phase < n:
            raise ValueError("phase out of range")
        if self.mode == "constant":
            return self.params[0]
        if self.mode == "affine":
            return self.params[0] + self.params[1] * phase
        if self.mode == "modular_ramp":
            base, slope, modulus = self.params
            return base + slope * (phase % modulus)
        if self.mode == "periodic_motif":
            return self.values[phase % self.params[0]]
        if self.mode == "lookup":
            return self.values[phase]
        if self.mode == "permutation_stride":
            return (phase + self.params[0]) % n
        raise ValueError(f"unknown sequence law mode {self.mode}")

    @property
    def expression(self) -> str:
        if self.mode == "constant":
            return str(self.params[0])
        if self.mode == "affine":
            a, b = self.params
            return f"{a} + {b}*phase"
        if self.mode == "modular_ramp":
            a, b, m = self.params
            return f"{a} + {b}*(phase mod {m})"
        if self.mode == "periodic_motif":
            return f"lookup(periodic={self.values[:self.params[0]]})"
        if self.mode == "permutation_stride":
            return f"(phase + {self.params[0]}) mod {len(self.values)}"
        return f"lookup({self.values})"

    @property
    def syntax_cost(self) -> int:
        if self.mode == "constant": return 1
        if self.mode == "affine": return 3
        if self.mode == "modular_ramp": return 4
        if self.mode == "periodic_motif": return 2 + self.params[0]
        if self.mode == "permutation_stride": return 3
        if self.mode == "lookup": return 1 + len(self.values)
        raise ValueError(f"unknown sequence law mode {self.mode}")


def synthesize_sequence(values: Iterable[int], *, allow_stride: bool = False) -> SequenceLaw:
    vals = tuple(int(v) for v in values)
    if not vals:
        raise ValueError("empty sequence")
    n = len(vals)
    if len(set(vals)) == 1:
        return SequenceLaw("constant", vals, (vals[0],))
    if allow_stride and sorted(vals) == list(range(n)):
        strides = [s for s in range(n) if tuple((p + s) % n for p in range(n)) == vals]
        if strides:
            return SequenceLaw("permutation_stride", vals, (strides[0],))
    if n >= 2:
        slope = vals[1] - vals[0]
        if all(vals[i] == vals[0] + slope * i for i in range(n)):
            return SequenceLaw("affine", vals, (vals[0], slope))
    modular = []
    for m in range(2, n + 1):
        for slope in range(-4, 5):
            base = vals[0]
            if all(vals[i] == base + slope * (i % m) for i in range(n)):
                modular.append((2 + abs(slope) + m, base, slope, m))
    if modular:
        _, base, slope, m = min(modular)
        return SequenceLaw("modular_ramp", vals, (base, slope, m))
    for period in range(1, n):
        if n % period == 0 and all(vals[i] == vals[i % period] for i in range(n)):
            return SequenceLaw("periodic_motif", vals, (period,))
    return SequenceLaw("lookup", vals)


@dataclass(frozen=True)
class TransferLaw:
    """Quantum lookup over phase and source-level residue."""
    modulus: int
    values: tuple[tuple[int, ...], ...]  # phase x residue

    def evaluate(self, phase: int, source_level: int) -> int:
        return self.values[phase][source_level % self.modulus]

    @property
    def expression(self) -> str:
        if self.modulus == 1 and len(set(row[0] for row in self.values)) == 1:
            return f"q={self.values[0][0]}"
        if self.modulus == 1:
            seq = tuple(row[0] for row in self.values)
            return "q(phase)=" + synthesize_sequence(seq).expression
        return f"q(phase, source mod {self.modulus})={self.values}"

    @property
    def syntax_cost(self) -> int:
        return 2 + len(self.values) * self.modulus


@dataclass(frozen=True)
class GroundProgram:
    capacity: int
    inflow: SequenceLaw
    demand: SequenceLaw
    phase_next: SequenceLaw
    transfer: TransferLaw
    capacity_status: str
    inferred_roles: tuple[tuple[str, str], ...]
    training_count: int
    invariant_residuals: tuple[int, ...]

    @property
    def period(self) -> int:
        return len(self.inflow.values)

    def step(self, s: State, action: str) -> State:
        if action not in ACTIONS:
            raise ValueError(f"unknown action {action}")
        if not (0 <= s.a <= self.capacity and 0 <= s.b <= self.capacity and 0 <= s.phase < self.period):
            raise ValueError(f"state outside inferred ground: {s}")
        qab = self.transfer.evaluate(s.phase, s.a)
        qba = self.transfer.evaluate(s.phase, s.b)
        ab = min(qab, s.a, self.capacity - s.b) if action == "A_TO_B" else 0
        ba = min(qba, s.b, self.capacity - s.a) if action == "B_TO_A" else 0
        a_pre = s.a - ab + ba
        b_pre = s.b + ab - ba
        a_next = min(self.capacity, max(0, a_pre + self.inflow.evaluate(s.phase)))
        b_next = min(self.capacity, max(0, b_pre - self.demand.evaluate(s.phase)))
        p_next = self.phase_next.evaluate(s.phase)
        return State(a_next, b_next, p_next)

    def as_dict(self) -> dict:
        return {
            "capacity": self.capacity,
            "capacity_status": self.capacity_status,
            "period": self.period,
            "inflow": {"mode": self.inflow.mode, "values": list(self.inflow.values), "params": list(self.inflow.params), "expression": self.inflow.expression},
            "demand": {"mode": self.demand.mode, "values": list(self.demand.values), "params": list(self.demand.params), "expression": self.demand.expression},
            "phase_next": {"mode": self.phase_next.mode, "values": list(self.phase_next.values), "params": list(self.phase_next.params), "expression": self.phase_next.expression},
            "transfer": {"modulus": self.transfer.modulus, "values": [list(r) for r in self.transfer.values], "expression": self.transfer.expression},
            "inferred_roles": dict(self.inferred_roles),
            "training_count": self.training_count,
            "invariant_residuals": list(self.invariant_residuals),
            "syntax_cost": self.inflow.syntax_cost + self.demand.syntax_cost + self.phase_next.syntax_cost + self.transfer.syntax_cost + 3,
        }


class InductionError(ValueError):
    pass


def _unique(values: Iterable[int], label: str) -> int:
    vals = sorted(set(int(v) for v in values))
    if not vals:
        raise InductionError(f"no observations for {label}")
    if len(vals) != 1:
        raise InductionError(f"conflicting observations for {label}: {vals}")
    return vals[0]


def induce_ground(records: Iterable[TransitionRecord], max_residue_modulus: int = 4) -> GroundProgram:
    rows = tuple(records)
    if len(rows) < 10:
        raise InductionError("insufficient transition records")
    if any(r.action not in ACTIONS for r in rows):
        raise InductionError("unknown action in records")

    capacity = max(max(r.state.a, r.state.b) for r in rows)
    phases_seen = sorted({r.state.phase for r in rows} | {r.next_state.phase for r in rows})
    if phases_seen != list(range(max(phases_seen) + 1)):
        raise InductionError("phase labels must be contiguous from zero")
    period = max(phases_seen) + 1

    holds_by_phase: dict[int, list[TransitionRecord]] = defaultdict(list)
    for r in rows:
        if r.action == "HOLD":
            holds_by_phase[r.state.phase].append(r)
    inflow_vals, demand_vals, next_vals = [], [], []
    saturation_evidence = False
    for p in range(period):
        hrows = holds_by_phase.get(p, [])
        if not hrows:
            raise InductionError(f"no HOLD records for phase {p}")
        # At a=0, no capacity clipping can hide nonnegative inflow.
        inflow = _unique((r.next_state.a - r.state.a for r in hrows if r.state.a == 0), f"inflow phase {p}")
        # At b=capacity, nonnegative demand is fully observable if demand<=capacity.
        demand = _unique((r.state.b - r.next_state.b for r in hrows if r.state.b == capacity), f"demand phase {p}")
        nxt = _unique((r.next_state.phase for r in hrows), f"phase progression {p}")
        if not 0 <= nxt < period:
            raise InductionError("phase progression leaves inferred phase domain")
        inflow_vals.append(inflow); demand_vals.append(demand); next_vals.append(nxt)
        if any(r.state.a == capacity and r.next_state.a == capacity and inflow > 0 for r in hrows):
            saturation_evidence = True

    # Search the smallest source-level residue modulus that gives a consistent
    # phase x residue transfer law. Use uncensored A_TO_B samples only.
    transfer_samples: list[tuple[int, int, int]] = []
    demand_law = tuple(demand_vals)
    for r in rows:
        if r.action != "A_TO_B":
            continue
        p = r.state.phase
        # b' > 0 ensures the entire requested environmental demand was met.
        if r.next_state.b <= 0:
            continue
        actual = r.next_state.b + demand_law[p] - r.state.b
        if actual <= 0:
            continue
        # Strict headroom/source conditions guarantee actual == requested quantum.
        if r.state.a > actual and capacity - r.state.b > actual:
            transfer_samples.append((p, r.state.a, actual))
    if not transfer_samples:
        raise InductionError("no uncensored transfer observations; active probing required")

    transfer = None
    for modulus in range(1, min(max_residue_modulus, capacity + 1) + 1):
        cells: dict[tuple[int, int], set[int]] = defaultdict(set)
        for p, source, q in transfer_samples:
            cells[(p, source % modulus)].add(q)
        matrix = []
        complete = True
        for p in range(period):
            row = []
            for residue in range(modulus):
                vals = cells.get((p, residue), set())
                if len(vals) != 1:
                    complete = False
                    break
                row.append(next(iter(vals)))
            if not complete:
                break
            matrix.append(tuple(row))
        if complete:
            transfer = TransferLaw(modulus, tuple(matrix))
            break
    if transfer is None:
        raise InductionError("transfer observations require a richer rule or more probes")

    # Capacity is exact only when we observed a saturated boundary under positive inflow.
    capacity_status = "exact_from_observed_saturation" if saturation_evidence else "lower_bound_only"
    roles = (
        ("capacity", "structural_constraint"),
        ("action", "controlled_input"),
        ("a", "endogenous_state"),
        ("b", "endogenous_state"),
        ("phase", "exogenous_context"),
        ("inflow_law", "structural_environment_rule"),
        ("demand_law", "structural_environment_rule"),
        ("phase_progression", "structural_environment_rule"),
        ("transfer_quantum", "controlled_operation_rule"),
    )

    # Construct once, then independently evaluate invariant residuals on every
    # supplied transition using the inferred program.
    provisional = GroundProgram(
        capacity, synthesize_sequence(inflow_vals), synthesize_sequence(demand_vals),
        synthesize_sequence(next_vals, allow_stride=True), transfer,
        capacity_status, roles, len(rows), (),
    )
    residuals = []
    for r in rows:
        predicted = provisional.step(r.state, r.action)
        if predicted != r.next_state:
            raise InductionError(
                f"induced program fails training record {r.state}/{r.action}: "
                f"predicted {predicted}, observed {r.next_state}"
            )
        ledger = inferred_ledger(provisional, r.state, r.action, r.next_state)
        residuals.append(ledger["mass_balance_residual"])
    return GroundProgram(
        capacity, provisional.inflow, provisional.demand, provisional.phase_next,
        transfer, capacity_status, roles, len(rows), tuple(residuals),
    )


def inferred_ledger(program: GroundProgram, state: State, action: str, nxt: State) -> dict:
    p = state.phase
    qab = program.transfer.evaluate(p, state.a)
    qba = program.transfer.evaluate(p, state.b)
    ab = min(qab, state.a, program.capacity - state.b) if action == "A_TO_B" else 0
    ba = min(qba, state.b, program.capacity - state.a) if action == "B_TO_A" else 0
    b_pre = state.b + ab - ba
    a_pre = state.a - ab + ba
    inflow = program.inflow.evaluate(p)
    demand = program.demand.evaluate(p)
    spill = max(0, a_pre + inflow - program.capacity)
    actual_demand = min(b_pre, demand)
    residual = nxt.a + nxt.b - (state.a + state.b + inflow - actual_demand - spill)
    return {
        "inflow": inflow, "demand": demand, "actual_demand": actual_demand,
        "spill": spill, "transfer_ab": ab, "transfer_ba": ba,
        "mass_balance_residual": residual,
    }


def make_dataset(ground: HiddenGround) -> tuple[tuple[TransitionRecord, ...], tuple[TransitionRecord, ...]]:
    train, heldout = [], []
    for a, b, p in product(range(ground.capacity + 1), range(ground.capacity + 1), range(ground.period)):
        s = State(a, b, p)
        # Some complete states are withheld (all actions); additional active
        # transitions are withheld at observed states. HOLD coverage over the
        # remaining states still spans every phase and boundary evidence.
        state_code = (a * 13 + b * 7 + p * 5) % 11
        whole_state_holdout = state_code == 0
        for action in ACTIONS:
            row = TransitionRecord(s, action, ground.step(s, action))
            action_code = (a * 17 + b * 11 + p * 7 + (0 if action == "A_TO_B" else 1)) % 5
            if not whole_state_holdout and (action == "HOLD" or action_code != 0):
                train.append(row)
            else:
                heldout.append(row)
    return tuple(train), tuple(heldout)


def evaluate_program(program: GroundProgram, records: Iterable[TransitionRecord]) -> dict:
    rows = tuple(records)
    mismatches = []
    for r in rows:
        try:
            pred = program.step(r.state, r.action)
        except Exception as exc:
            mismatches.append({"state": list(r.state), "action": r.action, "error": str(exc)})
            continue
        if pred != r.next_state:
            mismatches.append({
                "state": list(r.state), "action": r.action,
                "predicted": list(pred), "observed": list(r.next_state),
            })
    return {"count": len(rows), "correct": len(rows) - len(mismatches), "mismatches": mismatches}


def full_domain_coverage(program: GroundProgram, ground: HiddenGround) -> dict:
    records = [
        TransitionRecord(State(a, b, p), action, ground.step(State(a, b, p), action))
        for a, b, p, action in product(range(ground.capacity + 1), range(ground.capacity + 1), range(ground.period), ACTIONS)
    ]
    result = evaluate_program(program, records)
    result["state_count"] = (ground.capacity + 1) ** 2 * ground.period
    result["transition_coverage"] = result["correct"] / result["count"] if result["count"] else 1.0
    return result


def ground_catalog() -> tuple[HiddenGround, ...]:
    """Grounds include rules not present in Build 22's 32-model catalogue."""
    return (
        HiddenGround(4, (1, 0, 0, 1), (0, 1, 0, 0), (1, 2, 3, 0), ((1,), (1,), (1,), (1,)), 1, "cycle4-constant"),
        HiddenGround(5, (0, 1, 2, 0, 1, 2), (0, 1, 0, 0, 1, 0), (1, 2, 3, 4, 5, 0), ((1,), (2,), (1,), (2,), (1,), (2,)), 1, "period6-modular-inflow"),
        HiddenGround(4, (1, 0, 2, 1, 0), (0, 2, 0, 1, 0), (1, 3, 0, 4, 2), ((1, 2), (1, 2), (1, 2), (1, 2), (1, 2)), 2, "irregular-phase-source-parity"),
        HiddenGround(5, (0, 2, 1, 0, 2), (1, 0, 2, 0, 1), (1, 2, 3, 4, 0), ((1, 2, 3), (1, 2, 3), (1, 2, 3), (1, 2, 3), (1, 2, 3)), 3, "source-mod3-operation"),
        HiddenGround(6, (1, 0, 2, 1), (0, 1, 0, 2), (1, 2, 3, 0), ((1, 2, 3, 1), (1, 2, 3, 1), (1, 2, 3, 1), (1, 2, 3, 1)), 4, "source-mod4-operation"),
    )


def naive_transition_table_size(ground: HiddenGround) -> int:
    return (ground.capacity + 1) ** 2 * ground.period * len(ACTIONS)


def program_productivity(program: GroundProgram, ground: HiddenGround) -> dict:
    # This is a transparent count-based yield, not a universal compression metric.
    explicit_entries = naive_transition_table_size(ground)
    generated = explicit_entries
    cost = program.as_dict()["syntax_cost"]
    return {
        "explicit_transition_entries": explicit_entries,
        "program_syntax_cost_units": cost,
        "generated_transitions_per_syntax_unit": generated / cost,
        "interpretation": "finite-domain generative yield; not an asymptotic runtime claim",
    }


def counterexample_refinement(program: GroundProgram, train: Iterable[TransitionRecord], holdout: Iterable[TransitionRecord]) -> dict:
    """Report a minimal refinement trace from simple constant rules to learned law."""
    rows = tuple(train); held = tuple(holdout)
    qvals = sorted({
        program.transfer.evaluate(r.state.phase, r.state.a)
        for r in rows if r.action == "A_TO_B"
    })
    source_dependent = program.transfer.modulus > 1
    phase_dependent = len({row[0] for row in program.transfer.values}) > 1 or any(
        len(set(row)) > 1 for row in program.transfer.values
    )
    if source_dependent:
        refinement = [
            {"model": "constant_quantum", "status": "rejected_by_counterexample", "reason": "same phase requires different transfer at different source residues"},
            {"model": f"phase_x_source_mod_{program.transfer.modulus}", "status": "selected", "expression": program.transfer.expression},
        ]
    elif phase_dependent:
        refinement = [
            {"model": "global_constant_quantum", "status": "rejected_by_counterexample", "reason": "quantum varies by phase"},
            {"model": "phase_lookup_quantum", "status": "selected", "expression": program.transfer.expression},
        ]
    else:
        refinement = [{"model": "global_constant_quantum", "status": "retained", "expression": program.transfer.expression}]
    return {
        "trace": refinement,
        "transfer_quantum_values": qvals,
        "holdout": evaluate_program(program, held),
    }


def program_fingerprint(program: GroundProgram) -> str:
    """Stable digest of the inferred operational law, excluding training volume."""
    import hashlib, json
    payload = {
        "capacity": program.capacity,
        "period": program.period,
        "inflow": [program.inflow.mode, program.inflow.values, program.inflow.params],
        "demand": [program.demand.mode, program.demand.values, program.demand.params],
        "phase_next": [program.phase_next.mode, program.phase_next.values, program.phase_next.params],
        "transfer": [program.transfer.modulus, program.transfer.values],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def compare_programs(old: GroundProgram, new: GroundProgram) -> dict:
    changes = []
    fields = (
        ("capacity", old.capacity, new.capacity),
        ("period", old.period, new.period),
        ("inflow_law", (old.inflow.mode, old.inflow.values, old.inflow.params), (new.inflow.mode, new.inflow.values, new.inflow.params)),
        ("demand_law", (old.demand.mode, old.demand.values, old.demand.params), (new.demand.mode, new.demand.values, new.demand.params)),
        ("phase_progression", (old.phase_next.mode, old.phase_next.values, old.phase_next.params), (new.phase_next.mode, new.phase_next.values, new.phase_next.params)),
        ("operation_law", (old.transfer.modulus, old.transfer.values), (new.transfer.modulus, new.transfer.values)),
    )
    for name, before, after in fields:
        if before != after:
            changes.append({"component": name, "old": before, "new": after})
    state_encoding_compatible = old.capacity == new.capacity and old.period == new.period
    return {
        "old_fingerprint": program_fingerprint(old),
        "new_fingerprint": program_fingerprint(new),
        "same_ground": not changes,
        "revision_required": bool(changes),
        "changed_components": changes,
        "state_encoding_compatible": state_encoding_compatible,
        "interpretation": "transition-law revision" if state_encoding_compatible and changes else ("state-domain revision" if changes else "no detected revision"),
    }


def infer_variable_roles(records: Iterable[TransitionRecord]) -> dict[str, str]:
    """Infer roles from interventions and observed temporal variation.

    This is intentionally evidence-based and limited to this schema. It does
    not infer arbitrary latent variable names from raw sensor streams.
    """
    rows = tuple(records)
    actions = {r.action for r in rows}
    phase_pairs = {(r.state.phase, r.next_state.phase) for r in rows}
    phase_moves_under_hold = any(r.action == "HOLD" and r.state.phase != r.next_state.phase for r in rows)
    a_action_effect = any(r.action != "HOLD" and (r.next_state.a - r.state.a) != 0 for r in rows)
    b_action_effect = any(r.action != "HOLD" and (r.next_state.b - r.state.b) != 0 for r in rows)
    return {
        "action": "controlled_input" if len(actions) > 1 else "unidentified_input_role",
        "phase": "exogenous_context" if phase_moves_under_hold else "unidentified_context_role",
        "a": "endogenous_state" if a_action_effect else "unidentified_state_role",
        "b": "endogenous_state" if b_action_effect else "unidentified_state_role",
        "capacity": "structural_bound_inferred_from_boundary_evidence",
        "phase_pairs_observed": str(len(phase_pairs)),
    }


def heldout_probe_design(program: GroundProgram, hidden: HiddenGround) -> list[TransitionRecord]:
    """Independent counterfactual probes at states omitted from training selection."""
    probes = []
    # Focus on boundary and interior combinations plus all environmental phases.
    for p in range(hidden.period):
        for a, b in ((0, 0), (hidden.capacity, 0), (0, hidden.capacity), (hidden.capacity, hidden.capacity), (hidden.capacity - 1, 1)):
            s = State(a, b, p)
            for action in ACTIONS:
                probes.append(TransitionRecord(s, action, hidden.step(s, action)))
    return probes


def audit_projection(ground: HiddenGround, projection: str) -> dict:
    """Check deterministic transition congruence of common observer projections."""
    def obs(s: State):
        if projection == "FULL": return (s.a, s.b, s.phase)
        if projection == "LEVELS": return (s.a, s.b)
        if projection == "TOTAL": return (s.a + s.b,)
        if projection == "TOTAL_PHASE": return (s.a + s.b, s.phase)
        raise ValueError(projection)

    groups: dict[tuple[int, ...], list[State]] = defaultdict(list)
    for a, b, p in product(range(ground.capacity + 1), range(ground.capacity + 1), range(ground.period)):
        s = State(a, b, p)
        groups[obs(s)].append(s)
    conflicts = []
    for key, states in groups.items():
        if len(states) < 2:
            continue
        for action in ACTIONS:
            outputs = {obs(ground.step(s, action)) for s in states}
            if len(outputs) > 1:
                conflicts.append({"observation": key, "action": action, "distinct_next_observations": len(outputs)})
                break
    return {
        "projection": projection,
        "class_count": len(groups),
        "transition_congruent": not conflicts,
        "conflict_count": len(conflicts),
        "example_conflicts": conflicts[:5],
        "interpretation": "safe generative quotient" if not conflicts else "task observation only; cannot independently generate transitions",
    }


def explicit_transition_count(ground: HiddenGround) -> int:
    return naive_transition_table_size(ground)


def inferred_program_report(program: GroundProgram) -> dict:
    return program.as_dict() | {
        "fingerprint_sha256": program_fingerprint(program),
        "role_inference": infer_roles_from_program(program),
    }


def infer_roles_from_program(program: GroundProgram) -> dict:
    return dict(program.inferred_roles)


def compile_program_spec(spec: dict) -> GroundProgram:
    """Reconstruct an executable ground program from its serialized specification."""
    def seq(name: str) -> SequenceLaw:
        row = spec[name]
        return SequenceLaw(str(row["mode"]), tuple(int(v) for v in row["values"]), tuple(int(v) for v in row.get("params", ())))
    tr = spec["transfer"]
    transfer = TransferLaw(int(tr["modulus"]), tuple(tuple(int(v) for v in row) for row in tr["values"]))
    roles = tuple(sorted((str(k), str(v)) for k, v in spec.get("inferred_roles", {}).items()))
    return GroundProgram(
        int(spec["capacity"]), seq("inflow"), seq("demand"), seq("phase_next"),
        transfer, str(spec["capacity_status"]), roles,
        int(spec.get("training_count", 0)),
        tuple(int(v) for v in spec.get("invariant_residuals", ())),
    )
