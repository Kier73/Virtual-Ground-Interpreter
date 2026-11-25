"""VLD-002C: observation-preserving guarded affine execution and live Ground lifts.

A conditional predicate can depend on state hidden from an observer. We
refine the observer space until all projected branch updates and their
necessary guards factor through it. Admission checks identities independent
of discovery; neither sampled traces nor a hash assert equivalence.

Sound for every initial state over the declared prime field. Not a proof of
minimality for piecewise-affine machines, nor a source of authenticated probes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .symbolic_reduction import (
    AdmittedSymbolicGround, AffineAction, SymbolicReductionError as GuardError,
    _canonical, _coordinates, _decode, _digest, _field, _int, _label, _matrix,
    _mm, _mv, _rank, _rm, _row, _add_independent,
)

SCHEMA = "VGI-GuardedAffineGround-1"
CERT_SCHEMA = "VGI-GuardedObserverQuotient-1"
RECEIPT_SCHEMA = "VGI-GuardedExecutionReceipt-1"
MAX_DIMENSION = 128
MAX_ACTIONS = 12
MAX_OBSERVATIONS = 64
MAX_STEPS = 4096


def _keys(obj: Any, fields: set[str], label: str) -> dict:
    if type(obj) is not dict or set(obj) != fields:
        raise GuardError(f"{label} has noncanonical fields")
    return obj


def _dot(x: tuple[int, ...], y: tuple[int, ...], p: int) -> int:
    return sum(a*b for a, b in zip(x, y)) % p


def _coeff(row: tuple[int, ...], basis: tuple[tuple[int, ...], ...], p: int) -> tuple[int, ...] | None:
    try:
        return _coordinates(row, basis, p) if basis else (() if not any(row) else None)
    except GuardError:
        return None


@dataclass(frozen=True, slots=True)
class GuardedAction:
    symbol: str
    guard: tuple[int, ...]
    equals: int
    on_true: AffineAction
    on_false: AffineAction

    def to_dict(self) -> dict[str, Any]:
        return {"symbol": self.symbol, "guard": list(self.guard), "equals": self.equals,
                "on_true": {"matrix": [list(r) for r in self.on_true.matrix], "offset": list(self.on_true.offset)},
                "on_false": {"matrix": [list(r) for r in self.on_false.matrix], "offset": list(self.on_false.offset)}}


@dataclass(frozen=True, slots=True)
class GuardedGround:
    modulus: int
    dimension: int
    actions: tuple[GuardedAction, ...]
    observations: tuple[tuple[int, ...], ...]
    observation_bias: tuple[int, ...]

    def __post_init__(self) -> None:
        p, n = _field(self.modulus), _int(self.dimension, "dimension")
        if not 1 <= n <= MAX_DIMENSION or type(self.actions) is not tuple or not 1 <= len(self.actions) <= MAX_ACTIONS:
            raise GuardError("unsupported guarded dimension or action count")
        if (type(self.observations) is not tuple or
            any(type(row) is not tuple for row in self.observations) or
            type(self.observation_bias) is not tuple):
            raise GuardError("source state descriptions must be immutable tuples")
        symbols = []
        for a in self.actions:
            if not isinstance(a, GuardedAction):
                raise GuardError("expected typed guarded action")
            symbols.append(_label(a.symbol))
            if type(a.guard) is not tuple:
                raise GuardError("guard rows must be immutable tuples")
            _row(a.guard, n, p, "guard row")
            if _int(a.equals, "guard threshold") not in range(p):
                raise GuardError("guard threshold outside field")
            for branch in (a.on_true, a.on_false):
                if not isinstance(branch, AffineAction) or branch.symbol != a.symbol:
                    raise GuardError("branch must match input symbol")
                if (type(branch.matrix) is not tuple or
                    any(type(row) is not tuple for row in branch.matrix) or
                    type(branch.offset) is not tuple):
                    raise GuardError("branch matrices and offsets must be immutable tuples")
                _matrix(branch.matrix, n, p, "branch matrix", expected_rows=n)
                _row(branch.offset, n, p, "branch offset")
        if symbols != sorted(set(symbols)):
            raise GuardError("input symbols must be sorted and unique")
        if type(self.observations) is not tuple or len(self.observations) > MAX_OBSERVATIONS:
            raise GuardError("invalid observations")
        _matrix(self.observations, n, p, "observations")
        _row(self.observation_bias, len(self.observations), p, "observation bias")

    def dynamics_dict(self) -> dict[str, Any]:
        return {"modulus": self.modulus, "dimension": self.dimension,
                "actions": [a.to_dict() for a in self.actions]}

    @property
    def dynamics_fingerprint(self) -> str:
        return _digest(self.dynamics_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, **self.dynamics_dict(),
                "observations": [list(row) for row in self.observations],
                "observation_bias": list(self.observation_bias)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def step(self, x: tuple[int, ...], symbol: str) -> tuple[int, ...]:
        x = _row(x, self.dimension, self.modulus, "source state")
        action = next((a for a in self.actions if a.symbol == symbol), None)
        if action is None:
            raise GuardError("unknown input")
        branch = action.on_true if _dot(action.guard, x, self.modulus) == action.equals else action.on_false
        return tuple((v+b) % self.modulus for v, b in zip(_mv(branch.matrix, x, self.modulus), branch.offset))

    def observe(self, x: tuple[int, ...]) -> tuple[int, ...]:
        x = _row(x, self.dimension, self.modulus, "source state")
        return tuple((v+b) % self.modulus for v, b in zip(_mv(self.observations, x, self.modulus), self.observation_bias))


def discover_guarded_reduction(source: GuardedGround) -> dict[str, Any]:
    """Conservative affine row closure, adding guards only when branch effects differ.

    Both branches are closed over all states, including potentially inactive
    ones; exact verification is independent, but this need not be a minimal
    nonlinear quotient. Each new row eliminates a possible hidden dependency.
    """
    p = source.modulus
    basis: list[tuple[int, ...]] = []
    echelon: list[tuple[int, tuple[int, ...]]] = []
    for row in source.observations:
        _add_independent(row, basis, echelon, p)
    passes = 0
    index = 0
    while index < len(basis):
        row = basis[index]
        for action in source.actions:
            for branch in (action.on_true, action.on_false):
                _add_independent(_rm(row, branch.matrix, p), basis, echelon, p)
        index += 1
    # Adding a guard can reveal new dependencies under the branch transitions.
    while True:
        changed = False
        current = tuple(basis)
        for action in source.actions:
            true_effect = (tuple(_rm(row, action.on_true.matrix, p) for row in current),
                           _mv(current, action.on_true.offset, p))
            false_effect = (tuple(_rm(row, action.on_false.matrix, p) for row in current),
                            _mv(current, action.on_false.offset, p))
            if true_effect != false_effect:
                changed |= _add_independent(action.guard, basis, echelon, p)
        while index < len(basis):
            row = basis[index]
            for action in source.actions:
                for branch in (action.on_true, action.on_false):
                    changed |= _add_independent(_rm(row, branch.matrix, p), basis, echelon, p)
            index += 1
        passes += 1
        if not changed:
            break
    B = tuple(basis)
    reduced = []
    for action in source.actions:
        branches = []
        for branch in (action.on_true, action.on_false):
            branches.append({"matrix": [list(_coordinates(_rm(row, branch.matrix, p), B, p)) for row in B],
                             "offset": list(_mv(B, branch.offset, p))})
        different = branches[0] != branches[1]
        guard = list(_coordinates(action.guard, B, p)) if different else None
        reduced.append({"symbol": action.symbol, "guard": guard, "equals": action.equals,
                        "on_true": branches[0], "on_false": branches[1]})
    record = {"schema": CERT_SCHEMA, "source_sha256": source.fingerprint,
              "basis": [list(row) for row in B],
              "observations": [list(_coordinates(row, B, p)) for row in source.observations],
              "observation_bias": list(source.observation_bias), "actions": reduced}
    record["record_sha256"] = _digest(record)
    if len(_canonical(record)) > 1_048_576:
        raise GuardError("certificate exceeds 1 MiB bound")
    return record


@dataclass(frozen=True, slots=True)
class QuotientGuardedAction:
    symbol: str
    guard: tuple[int, ...] | None
    equals: int
    on_true: AffineAction
    on_false: AffineAction

    def choose(self, z: tuple[int, ...], p: int) -> tuple[AffineAction, str]:
        if self.guard is None:
            return self.on_true, "elided"
        good = _dot(self.guard, z, p) == self.equals
        return (self.on_true if good else self.on_false), ("true" if good else "false")


@dataclass(frozen=True, slots=True)
class AdmittedGuardedGround:
    source_sha256: str
    dynamics_sha256: str
    modulus: int
    source_dimension: int
    basis: tuple[tuple[int, ...], ...]
    actions: tuple[QuotientGuardedAction, ...]
    observations: tuple[tuple[int, ...], ...]
    observation_bias: tuple[int, ...]
    certificate_sha256: str

    @property
    def dimension(self) -> int:
        return len(self.basis)

    @property
    def source_states(self) -> int:
        return self.modulus ** self.source_dimension

    @property
    def quotient_states(self) -> int:
        return self.modulus ** self.dimension

    def project(self, x: tuple[int, ...]) -> tuple[int, ...]:
        return _mv(self.basis, _row(x, self.source_dimension, self.modulus, "source state"), self.modulus)

    def observe(self, z: tuple[int, ...]) -> tuple[int, ...]:
        z = _row(z, self.dimension, self.modulus, "quotient state")
        return tuple((v+b) % self.modulus for v, b in zip(_mv(self.observations, z, self.modulus), self.observation_bias))

    def step_with_guard(self, z: tuple[int, ...], symbol: str) -> tuple[tuple[int, ...], str]:
        z = _row(z, self.dimension, self.modulus, "quotient state")
        action = next((a for a in self.actions if a.symbol == symbol), None)
        if action is None:
            raise GuardError("unknown input symbol")
        branch, decision = action.choose(z, self.modulus)
        out = tuple((v+b) % self.modulus for v, b in zip(_mv(branch.matrix, z, self.modulus), branch.offset))
        return out, decision

    def step(self, z: tuple[int, ...], symbol: str) -> tuple[int, ...]:
        return self.step_with_guard(z, symbol)[0]

    def jump_invariant(self, z: tuple[int, ...], symbol: str, steps: int) -> tuple[int, ...]:
        """Exponentiate only when a chosen branch is proved invariant.

        The equal-hyperplane condition is maintained by gT=lambda*g,
        g*t=(1-lambda)c. The complement requires lambda != 0.
        An elided guard can always be skipped because both quotient
        branches have identical affine transitions.
        """
        z = _row(z, self.dimension, self.modulus, "quotient state")
        steps = _int(steps, "steps")
        if steps < 0 or steps.bit_length() > 4096:
            raise GuardError("steps outside bounded range")
        action = next((a for a in self.actions if a.symbol == symbol), None)
        if action is None:
            raise GuardError("unknown input symbol")
        branch, decision = action.choose(z, self.modulus)
        if action.guard is not None and steps > 1:
            g, p = action.guard, self.modulus
            # A zero guard represents a constant predicate, even when the
            # constant is impossible (0 != equals); it never changes.
            pivot = next((i for i, v in enumerate(g) if v), None)
            if pivot is not None:
                gT = _rm(g, branch.matrix, p)
                lam = gT[pivot] * pow(g[pivot], -1, p) % p
                if gT != tuple(lam * v % p for v in g):
                    raise GuardError("guard hyperplane is not invariant")
                if (_dot(g, branch.offset, p) + lam * action.equals) % p != action.equals:
                    raise GuardError("guard hyperplane is not invariant")
                if decision == "false" and lam == 0:
                    raise GuardError("guard complement is not invariant")
        # Reuse the admitted affine fast-forward primitive once every step
        # is known to use the same projected affine branch.
        affine = AdmittedSymbolicGround(self.source_sha256, self.modulus, self.source_dimension,
            self.basis, (AffineAction(symbol, branch.matrix, branch.offset),),
            self.observations, self.observation_bias, self.certificate_sha256)
        return affine.jump(z, symbol, steps)


def admit_guarded_reduction(source: GuardedGround,
                             certificate: bytes | str | Mapping[str, Any]) -> AdmittedGuardedGround:
    """Independent exact checking of branch commutation and observable guards."""
    obj = _keys(_decode(certificate), {"schema", "source_sha256", "basis", "observations",
                                       "observation_bias", "actions", "record_sha256"}, "certificate")
    if obj["schema"] != CERT_SCHEMA or obj["source_sha256"] != source.fingerprint:
        raise GuardError("source or schema mismatch")
    digest = obj["record_sha256"]
    if type(digest) is not str or _digest({k: v for k, v in obj.items() if k != "record_sha256"}) != digest:
        raise GuardError("certificate digest mismatch")
    p, n = source.modulus, source.dimension
    if type(obj["basis"]) is not list or len(obj["basis"]) > n:
        raise GuardError("invalid basis")
    B = _matrix(obj["basis"], n, p, "basis")
    r = len(B)
    if _rank(B, p) != r:
        raise GuardError("dependent basis")
    if type(obj["observations"]) is not list:
        raise GuardError("invalid output map")
    D = _matrix(obj["observations"], r, p, "output map", expected_rows=len(source.observations))
    h = _row(obj["observation_bias"], len(source.observations), p, "output bias")
    if _mm(D, B, p, n) != source.observations or h != source.observation_bias:
        raise GuardError("observer output does not factor through quotient")
    if type(obj["actions"]) is not list or len(obj["actions"]) != len(source.actions):
        raise GuardError("incorrect action count")
    verified = []
    for original, entry in zip(source.actions, obj["actions"]):
        entry = _keys(entry, {"symbol", "guard", "equals", "on_true", "on_false"}, "action")
        if entry["symbol"] != original.symbol or entry["equals"] != original.equals:
            raise GuardError("input or predicate changed")
        branches = []
        for name, source_branch in (("on_true", original.on_true), ("on_false", original.on_false)):
            reduced_branch = _keys(entry[name], {"matrix", "offset"}, "branch")
            T = _matrix(reduced_branch["matrix"], r, p, "branch matrix", expected_rows=r)
            t = _row(reduced_branch["offset"], r, p, "branch offset")
            if _mm(T, B, p, n) != _mm(B, source_branch.matrix, p, n):
                raise GuardError("branch fails matrix commutation")
            if t != _mv(B, source_branch.offset, p):
                raise GuardError("branch fails affine-offset commutation")
            branches.append(AffineAction(original.symbol, T, t))
        raw_guard = entry["guard"]
        if raw_guard is None:
            if (branches[0].matrix, branches[0].offset) != (branches[1].matrix, branches[1].offset):
                raise GuardError("guard was elided despite observable branch difference")
            guard = None
        else:
            guard = _row(raw_guard, r, p, "projected guard")
            if _rm(guard, B, p) != original.guard:
                raise GuardError("guard cannot be determined from quotient")
        verified.append(QuotientGuardedAction(original.symbol, guard, original.equals, *branches))
    return AdmittedGuardedGround(source.fingerprint, source.dynamics_fingerprint, p, n,
                                 B, tuple(verified), D, h, digest)


def run_guarded(q: AdmittedGuardedGround, initial: tuple[int, ...],
                inputs: tuple[str, ...]) -> dict[str, Any]:
    """A reproducible trace receipt for execution on certified coordinates."""
    if type(inputs) is not tuple or len(inputs) > MAX_STEPS:
        raise GuardError("process input sequence exceeds bound")
    start = _row(initial, q.dimension, q.modulus, "start")
    state = start
    events = []
    chain = _digest({"source": q.source_sha256, "certificate": q.certificate_sha256,
                     "start": list(start)})
    for symbol in inputs:
        if type(symbol) is not str:
            raise GuardError("inputs must be strings")
        next_state, decision = q.step_with_guard(state, symbol)
        event = {"input": symbol, "before": list(state), "decision": decision,
                 "after": list(next_state), "observation": list(q.observe(next_state))}
        chain = _digest({"previous": chain, "event": event})
        events.append({**event, "chain_sha256": chain})
        state = next_state
    result = {"schema": RECEIPT_SCHEMA, "source_sha256": q.source_sha256,
              "certificate_sha256": q.certificate_sha256, "start": list(start),
              "final": list(state), "events": events, "head_sha256": chain}
    result["receipt_sha256"] = _digest(result)
    if len(_canonical(result)) > 1_048_576:
        raise GuardError("execution receipt exceeds 1 MiB admission bound")
    return result


def verify_guarded_receipt(q: AdmittedGuardedGround, payload: Mapping[str, Any] | bytes | str) -> dict[str, Any]:
    """Replay mathematical receipt; not authentication of originating host."""
    data = _keys(_decode(payload), {"schema", "source_sha256", "certificate_sha256",
                                   "start", "final", "events", "head_sha256", "receipt_sha256"}, "execution receipt")
    if (data["schema"] != RECEIPT_SCHEMA or data["source_sha256"] != q.source_sha256
        or data["certificate_sha256"] != q.certificate_sha256):
        raise GuardError("execution source or certificate changed")
    if _digest({k: v for k, v in data.items() if k != "receipt_sha256"}) != data["receipt_sha256"]:
        raise GuardError("execution receipt digest mismatch")
    if type(data["events"]) is not list or len(data["events"]) > MAX_STEPS:
        raise GuardError("execution events out of range")
    inputs = []
    for item in data["events"]:
        _keys(item, {"input", "before", "decision", "after", "observation", "chain_sha256"}, "event")
        inputs.append(item["input"])
    expected = run_guarded(q, _row(data["start"], q.dimension, q.modulus, "start"), tuple(inputs))
    if data != expected:
        raise GuardError("execution event or chain differs from independent replay")
    return {"status": "VERIFIED", "steps": len(inputs), "final": tuple(expected["final"]),
            "certificate_sha256": q.certificate_sha256, "receipt_sha256": expected["receipt_sha256"]}


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    """Linear observation demand for changing the quotient during execution."""
    probe_rows: tuple[tuple[int, ...], ...]
    new_from_old_and_probes: tuple[tuple[int, ...], ...]

    @property
    def probe_count(self) -> int:
        return len(self.probe_rows)


def plan_migration(old: AdmittedGuardedGround,
                   new: AdmittedGuardedGround) -> MigrationPlan:
    if (old.dynamics_sha256 != new.dynamics_sha256 or old.modulus != new.modulus
        or old.source_dimension != new.source_dimension):
        raise GuardError("migration cannot change machine dynamics")
    p = old.modulus
    combined = list(old.basis)
    probes = []
    for row in new.basis:
        if _coeff(row, tuple(combined), p) is None:
            probes.append(row)
            combined.append(row)
    return MigrationPlan(tuple(probes), tuple(_coordinates(row, tuple(combined), p) for row in new.basis))


def apply_migration(old: AdmittedGuardedGround, new: AdmittedGuardedGround,
                    old_state: tuple[int, ...], probe_values: tuple[int, ...],
                    plan: MigrationPlan) -> tuple[int, ...]:
    """Lift without the complete source state, conditioned on genuine probe values.

    The method validates the entire linear lift rather than trusting a supplied
    plan. Probe authenticity is a separate host/observer authorization obligation.
    """
    expected = plan_migration(old, new)
    if plan != expected:
        raise GuardError("invalid migration plan")
    stacked = old.basis + expected.probe_rows
    if (_rank(stacked, old.modulus) != len(stacked) or
        _mm(expected.new_from_old_and_probes, stacked, old.modulus,
            old.source_dimension) != new.basis):
        raise GuardError("migration map does not preserve required coordinates")
    a = _row(old_state, old.dimension, old.modulus, "old state")
    b = _row(probe_values, expected.probe_count, old.modulus, "probe values")
    return _mv(expected.new_from_old_and_probes, a + b, old.modulus)


def observe_migration_probes(source: GuardedGround, snapshot: tuple[int, ...],
                             new: AdmittedGuardedGround, plan: MigrationPlan) -> tuple[int, ...]:
    if source.dynamics_fingerprint != new.dynamics_sha256:
        raise GuardError("source dynamics differ")
    x = _row(snapshot, source.dimension, source.modulus, "source snapshot")
    return _mv(plan.probe_rows, x, source.modulus)