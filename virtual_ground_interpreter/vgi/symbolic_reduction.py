"""VLD-002B: exact symbolic observer quotients for finite-field affine systems.

Find and certify the complete observation row-orbit of a switched affine
system without enumerating its p**dimension states.  Independent admission
checks algebraic commutation and explicit distinguishing-word witnesses;
only admitted quotients can be executed or exponentiated here.

Scope: all possible initial states of a fully known affine finite-field
machine, with Moore-style observations of the current state.  A machine with
one designated initial state can have a smaller reachable quotient.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "VGI-SymbolicAffineGround-1"
CERT_SCHEMA = "VGI-SymbolicObserverQuotient-1"
MAX_DIMENSION = 128
MAX_INPUTS = 12
MAX_OUTPUTS = 64
MAX_CERT_BYTES = 1_048_576


class SymbolicReductionError(ValueError):
    """A malformed Ground or invalid observer-quotient certificate."""


def _int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise SymbolicReductionError(f"{label} must be an integer (not bool)")
    return value


def _field(p: Any) -> int:
    p = _int(p, "field modulus")
    if not 2 <= p <= 251:
        raise SymbolicReductionError("finite-field modulus must be a prime in [2,251]")
    for d in range(2, int(p ** .5) + 1):
        if p % d == 0:
            raise SymbolicReductionError("the field modulus must be prime")
    return p


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise SymbolicReductionError("record is not canonical finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _row(values: Any, length: int, p: int, label: str) -> tuple[int, ...]:
    if not isinstance(values, (tuple, list)) or len(values) != length:
        raise SymbolicReductionError(f"{label} must contain {length} elements")
    out = tuple(_int(x, label) for x in values)
    if any(x < 0 or x >= p for x in out):
        raise SymbolicReductionError(f"{label} values must be canonical residues")
    return out


def _matrix(values: Any, columns: int, p: int, label: str,
            *, expected_rows: int | None = None) -> tuple[tuple[int, ...], ...]:
    if not isinstance(values, (tuple, list)):
        raise SymbolicReductionError(f"{label} must be a matrix")
    if expected_rows is not None and len(values) != expected_rows:
        raise SymbolicReductionError(f"{label} has the wrong number of rows")
    return tuple(_row(v, columns, p, label) for v in values)


def _label(value: Any) -> str:
    if type(value) is not str or not value or len(value) > 64:
        raise SymbolicReductionError("input symbols must be nonempty short strings")
    return value


def _keys(value: Any, required: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != required:
        raise SymbolicReductionError(f"{name} requires exactly {sorted(required)}")
    return value


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise SymbolicReductionError("duplicate JSON field")
        out[k] = v
    return out


def _no_constant(_: str) -> None:
    raise SymbolicReductionError("non-finite JSON constant")


def _decode(record: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(record, Mapping):
        data = _canonical(dict(record))
    elif type(record) is str:
        data = record.encode("utf-8")
    elif type(record) is bytes:
        data = record
    else:
        raise SymbolicReductionError("record must be JSON or a mapping")
    if len(data) > MAX_CERT_BYTES:
        raise SymbolicReductionError("record exceeds admission byte limit")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs_unique,
                           parse_constant=_no_constant)
    except SymbolicReductionError:
        raise
    except (ValueError, UnicodeError, OverflowError, RecursionError) as exc:
        raise SymbolicReductionError("malformed JSON record") from exc
    if type(value) is not dict:
        raise SymbolicReductionError("expected a JSON object")
    return value


def _mv(matrix: tuple[tuple[int, ...], ...], v: tuple[int, ...], p: int) -> tuple[int, ...]:
    return tuple(sum(a*b for a, b in zip(row, v)) % p for row in matrix)


def _rm(row: tuple[int, ...], matrix: tuple[tuple[int, ...], ...], p: int) -> tuple[int, ...]:
    n = len(matrix[0]) if matrix else len(row)
    return tuple(sum(x * matrix[i][j] for i, x in enumerate(row)) % p for j in range(n))


def _mm(left: tuple[tuple[int, ...], ...], right: tuple[tuple[int, ...], ...],
        p: int, right_cols: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(sum(left_row[k]*right[k][j] for k in range(len(right))) % p
                       for j in range(right_cols)) for left_row in left)


def _rank(rows: tuple[tuple[int, ...], ...], p: int) -> int:
    """Independent verifier's full Gaussian elimination (no synthesis helpers)."""
    if not rows:
        return 0
    work = [list(row) for row in rows]
    rank = 0
    n = len(work[0])
    for col in range(n):
        pivot = next((k for k in range(rank, len(work)) if work[k][col] % p), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        inv = pow(work[rank][col], -1, p)
        work[rank] = [(v * inv) % p for v in work[rank]]
        for i in range(len(work)):
            if i != rank:
                mul = work[i][col]
                if mul:
                    work[i] = [(x - mul * y) % p for x, y in zip(work[i], work[rank])]
        rank += 1
        if rank == len(work):
            break
    return rank


@dataclass(frozen=True, slots=True)
class AffineAction:
    symbol: str
    matrix: tuple[tuple[int, ...], ...]
    offset: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"symbol": self.symbol, "matrix": [list(row) for row in self.matrix],
                "offset": list(self.offset)}


@dataclass(frozen=True, slots=True)
class AffineGround:
    modulus: int
    dimension: int
    actions: tuple[AffineAction, ...]
    observations: tuple[tuple[int, ...], ...]
    observation_bias: tuple[int, ...]

    def __post_init__(self) -> None:
        p = _field(self.modulus)
        n = _int(self.dimension, "dimension")
        if not 1 <= n <= MAX_DIMENSION:
            raise SymbolicReductionError("dimension outside supported range")
        if type(self.actions) is not tuple or not 1 <= len(self.actions) <= MAX_INPUTS:
            raise SymbolicReductionError("at least one and at most 12 inputs required")
        symbols = []
        for act in self.actions:
            if not isinstance(act, AffineAction):
                raise SymbolicReductionError("expected typed affine actions")
            if (type(act.matrix) is not tuple or any(type(row) is not tuple for row in act.matrix)
                or type(act.offset) is not tuple):
                raise SymbolicReductionError("typed affine actions must be immutable tuples")
            symbols.append(_label(act.symbol))
            _matrix(act.matrix, n, p, "transition matrix", expected_rows=n)
            _row(act.offset, n, p, "transition offset")
        if tuple(symbols) != tuple(sorted(set(symbols))):
            raise SymbolicReductionError("input symbols must be unique and sorted")
        if (type(self.observations) is not tuple or
            any(type(row) is not tuple for row in self.observations) or
            type(self.observation_bias) is not tuple or len(self.observations) > MAX_OUTPUTS):
            raise SymbolicReductionError("too many observation rows")
        _matrix(self.observations, n, p, "observations")
        _row(self.observation_bias, len(self.observations), p, "observation bias")

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "modulus": self.modulus, "dimension": self.dimension,
                "actions": [act.to_dict() for act in self.actions],
                "observations": [list(row) for row in self.observations],
                "observation_bias": list(self.observation_bias)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, record: Any) -> "AffineGround":
        r = _keys(record, {"schema", "modulus", "dimension", "actions", "observations",
                           "observation_bias"}, "affine ground")
        if r["schema"] != SCHEMA or type(r["actions"]) is not list:
            raise SymbolicReductionError("unsupported affine ground schema")
        n, p = _int(r["dimension"], "dimension"), _field(r["modulus"])
        if not 1 <= n <= MAX_DIMENSION or len(r["actions"]) > MAX_INPUTS:
            raise SymbolicReductionError("affine ground exceeds limits")
        acts = []
        for item in r["actions"]:
            a = _keys(item, {"symbol", "matrix", "offset"}, "affine action")
            acts.append(AffineAction(_label(a["symbol"]),
                                     _matrix(a["matrix"], n, p, "matrix", expected_rows=n),
                                     _row(a["offset"], n, p, "offset")))
        if type(r["observations"]) is not list or len(r["observations"]) > MAX_OUTPUTS:
            raise SymbolicReductionError("invalid observation matrix")
        obs = _matrix(r["observations"], n, p, "observations")
        return cls(p, n, tuple(acts), obs,
                   _row(r["observation_bias"], len(obs), p, "observation bias"))

    def step(self, state: tuple[int, ...], symbol: str) -> tuple[int, ...]:
        state = _row(state, self.dimension, self.modulus, "source state")
        act = next((x for x in self.actions if x.symbol == symbol), None)
        if act is None:
            raise SymbolicReductionError("unknown input symbol")
        vector = _mv(act.matrix, state, self.modulus)
        return tuple((v+b) % self.modulus for v, b in zip(vector, act.offset))

    def observe(self, state: tuple[int, ...]) -> tuple[int, ...]:
        state = _row(state, self.dimension, self.modulus, "source state")
        return tuple((v+b) % self.modulus for v, b in
                     zip(_mv(self.observations, state, self.modulus), self.observation_bias))


def _add_independent(row: tuple[int, ...], basis: list[tuple[int, ...]],
                     echelon: list[tuple[int, tuple[int, ...]]], p: int) -> bool:
    value = list(row)
    for pivot, leader in echelon:
        k = value[pivot]
        if k:
            value = [(a-k*b) % p for a, b in zip(value, leader)]
    pivot = next((i for i, x in enumerate(value) if x), None)
    if pivot is None:
        return False
    inv = pow(value[pivot], -1, p)
    echelon.append((pivot, tuple((v*inv) % p for v in value)))
    basis.append(row)
    return True


def _coordinates(row: tuple[int, ...], basis: tuple[tuple[int, ...], ...],
                 p: int) -> tuple[int, ...]:
    """Represent a row as a combination of the independent *original* basis rows."""
    echelon: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = []
    rank = len(basis)
    for j, raw in enumerate(basis):
        v = list(raw)
        expression = [int(k == j) for k in range(rank)]
        for pivot, leader, coeff in echelon:
            k = v[pivot]
            if k:
                v = [(a-k*b) % p for a, b in zip(v, leader)]
                expression = [(a-k*b) % p for a, b in zip(expression, coeff)]
        pivot = next((i for i, x in enumerate(v) if x), None)
        if pivot is None:
            raise SymbolicReductionError("discovery basis was dependent")
        inverse = pow(v[pivot], -1, p)
        echelon.append((pivot, tuple(x*inverse % p for x in v),
                        tuple(x*inverse % p for x in expression)))
    remainder = list(row)
    alpha = [0] * rank
    for pivot, leader, expr in echelon:
        k = remainder[pivot]
        if k:
            remainder = [(a-k*b) % p for a, b in zip(remainder, leader)]
            alpha = [(a+k*b) % p for a, b in zip(alpha, expr)]
    if any(remainder):
        raise SymbolicReductionError("row orbit closure failed")
    return tuple(alpha)


def discover_symbolic_reduction(source: AffineGround) -> dict[str, Any]:
    """Compute the least invariant observation row span, carrying word witnesses."""
    p = source.modulus
    basis: list[tuple[int, ...]] = []
    echelon: list[tuple[int, tuple[int, ...]]] = []
    witnesses: list[tuple[int, tuple[str, ...]]] = []
    for output_index, row in enumerate(source.observations):
        if _add_independent(row, basis, echelon, p):
            witnesses.append((output_index, ()))
    index = 0
    while index < len(basis):
        original, word = witnesses[index]
        for action in source.actions:
            next_row = _rm(basis[index], action.matrix, p)
            if _add_independent(next_row, basis, echelon, p):
                witnesses.append((original, (action.symbol,) + word))
        index += 1
    B = tuple(basis)
    r = len(B)
    reduced_actions = []
    for action in source.actions:
        reduced_actions.append({"symbol": action.symbol,
            "matrix": [list(_coordinates(_rm(row, action.matrix, p), B, p)) for row in B],
            "offset": list(_mv(B, action.offset, p))})
    output_map = [list(_coordinates(row, B, p)) for row in source.observations]
    payload: dict[str, Any] = {"schema": CERT_SCHEMA,
        "source_sha256": source.fingerprint,
        "basis": [list(row) for row in B],
        "witnesses": [{"output": i, "word": list(word)} for i, word in witnesses],
        "actions": reduced_actions,
        "output_matrix": output_map,
        "output_bias": list(source.observation_bias)}
    payload["record_sha256"] = _digest(payload)
    if len(_canonical(payload)) > MAX_CERT_BYTES:
        raise SymbolicReductionError("constructed certificate is over size limit")
    return payload


@dataclass(frozen=True, slots=True)
class AdmittedSymbolicGround:
    """Immutable quotient data returned by independent exact admission."""
    source_sha256: str
    modulus: int
    source_dimension: int
    basis: tuple[tuple[int, ...], ...]
    actions: tuple[AffineAction, ...]
    observation_matrix: tuple[tuple[int, ...], ...]
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

    def project(self, state: tuple[int, ...]) -> tuple[int, ...]:
        x = _row(state, self.source_dimension, self.modulus, "source state")
        return _mv(self.basis, x, self.modulus)

    def observe(self, state: tuple[int, ...]) -> tuple[int, ...]:
        y = _row(state, self.dimension, self.modulus, "reduced state")
        return tuple((a + b) % self.modulus for a, b in
                     zip(_mv(self.observation_matrix, y, self.modulus), self.observation_bias))

    def step(self, state: tuple[int, ...], symbol: str) -> tuple[int, ...]:
        y = _row(state, self.dimension, self.modulus, "reduced state")
        action = next((x for x in self.actions if x.symbol == symbol), None)
        if action is None:
            raise SymbolicReductionError("unknown input symbol")
        return tuple((a+b) % self.modulus for a, b in
                     zip(_mv(action.matrix, y, self.modulus), action.offset))

    def jump(self, state: tuple[int, ...], symbol: str, steps: int) -> tuple[int, ...]:
        """Repeat one input symbol by exact logarithmic affine powering."""
        return self.jump_word(state, (symbol,), steps)

    def jump_word(self, state: tuple[int, ...], word: tuple[str, ...],
                  periods: int) -> tuple[int, ...]:
        """Navigate repeated input *words* with O((len(word)+log periods) r^3).

        E.g. jump_word(y, ('send','ack'), 10**100) realizes the state after
        10**100 repetitions of a two-input macro without iterating periods.
        This is an algebraic fast-forward, not a claim of physical elapsed time.
        """
        state = _row(state, self.dimension, self.modulus, "reduced state")
        periods = _int(periods, "jump periods")
        if periods < 0 or periods.bit_length() > 4096:
            raise SymbolicReductionError("jump periods must be a nonnegative <=4096-bit integer")
        if type(word) is not tuple or len(word) > 4096:
            raise SymbolicReductionError("jump word must be a bounded tuple")
        r, p = self.dimension, self.modulus
        action_map = {action.symbol: action for action in self.actions}
        if any(type(symbol) is not str or symbol not in action_map for symbol in word):
            raise SymbolicReductionError("jump word contains unknown input symbol")

        def compose(f: tuple[Any, Any], g: tuple[Any, Any]) -> tuple[Any, Any]:
            # f(g(y)) = (F G) y + F g_offset + f_offset
            F, f0 = f
            G, g0 = g
            M = _mm(F, G, p, r)
            v = _mv(F, g0, p)
            return M, tuple((x+b) % p for x, b in zip(v, f0))

        identity = (tuple(tuple(int(i==j) for j in range(r)) for i in range(r)),
                    (0,) * r)
        power = identity
        for symbol in word:
            action = action_map[symbol]
            power = compose((action.matrix, action.offset), power)
        result = identity
        while periods:
            if periods & 1:
                result = compose(power, result)
            periods >>= 1
            if periods:
                power = compose(power, power)
        matrix, offset = result
        return tuple((a+b) % p for a, b in zip(_mv(matrix, state, p), offset))


def admit_symbolic_reduction(source: AffineGround,
                             certificate: bytes | str | Mapping[str, Any]) -> AdmittedSymbolicGround:
    """Independent admission: checks the complete algebra, without discovery.

    Soundness: C = D B, B A_a = T_a B and B b_a = t_a imply the
    observation and state diagrams commute after each input, hence for
    every finite word.  Minimality (all initial states): independent rows B
    are certified output-after-word rows, so every distinct quotient pair
    differs on at least one future observation.
    """
    obj = _keys(_decode(certificate), {"schema", "source_sha256", "basis", "witnesses",
                                     "actions", "output_matrix", "output_bias",
                                     "record_sha256"}, "symbolic certificate")
    if obj["schema"] != CERT_SCHEMA or obj["source_sha256"] != source.fingerprint:
        raise SymbolicReductionError("certificate source or version differs")
    bound = obj["record_sha256"]
    if type(bound) is not str or len(bound) != 64 or any(c not in "0123456789abcdef" for c in bound):
        raise SymbolicReductionError("invalid record digest")
    payload = {k: v for k, v in obj.items() if k != "record_sha256"}
    if _digest(payload) != bound:
        raise SymbolicReductionError("certificate content digest mismatch")
    p, n = source.modulus, source.dimension
    if type(obj["basis"]) is not list or len(obj["basis"]) > n:
        raise SymbolicReductionError("invalid basis dimensions")
    B = _matrix(obj["basis"], n, p, "certificate basis")
    r = len(B)
    if _rank(B, p) != r:
        raise SymbolicReductionError("certificate basis is dependent")
    if type(obj["witnesses"]) is not list or len(obj["witnesses"]) != r:
        raise SymbolicReductionError("missing minimality witnesses")
    by_symbol = {action.symbol: action for action in source.actions}
    for i, witness in enumerate(obj["witnesses"]):
        w = _keys(witness, {"output", "word"}, "distinguishing witness")
        oi = _int(w["output"], "output index")
        if not 0 <= oi < len(source.observations):
            raise SymbolicReductionError("witness output index out of range")
        word = w["word"]
        if type(word) is not list or len(word) > n:
            raise SymbolicReductionError("witness input word too long")
        observed_row = source.observations[oi]
        # For chronological input word a,b, C A_b A_a is the final output row.
        for symbol in reversed(word):
            if type(symbol) is not str or symbol not in by_symbol:
                raise SymbolicReductionError("unknown witness input")
            observed_row = _rm(observed_row, by_symbol[symbol].matrix, p)
        if observed_row != B[i]:
            raise SymbolicReductionError("basis row is not its claimed observation word")
    if type(obj["actions"]) is not list or len(obj["actions"]) != len(source.actions):
        raise SymbolicReductionError("candidate changes input alphabet")
    new_actions = []
    for source_action, item in zip(source.actions, obj["actions"]):
        action = _keys(item, {"symbol", "matrix", "offset"}, "reduced action")
        if action["symbol"] != source_action.symbol:
            raise SymbolicReductionError("candidate input symbols changed")
        T = _matrix(action["matrix"], r, p, "reduced transition", expected_rows=r)
        t = _row(action["offset"], r, p, "reduced offset")
        # Independently multiply entire matrices: quotient transition commutes.
        if _mm(T, B, p, n) != _mm(B, source_action.matrix, p, n):
            raise SymbolicReductionError("reduced transition violates commutation")
        if t != _mv(B, source_action.offset, p):
            raise SymbolicReductionError("reduced affine offset is incorrect")
        new_actions.append(AffineAction(source_action.symbol, T, t))
    if type(obj["output_matrix"]) is not list:
        raise SymbolicReductionError("invalid output projection")
    D = _matrix(obj["output_matrix"], r, p, "output map",
                expected_rows=len(source.observations))
    h = _row(obj["output_bias"], len(source.observations), p, "output bias")
    if _mm(D, B, p, n) != source.observations or h != source.observation_bias:
        raise SymbolicReductionError("observer cannot reconstruct original outputs")
    return AdmittedSymbolicGround(source.fingerprint, p, n, B, tuple(new_actions), D, h, bound)
