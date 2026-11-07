"""Build 03: codonic connection geometry.

A small, dependency-free research prototype. The default experimental registry
uses `ad` for addition and `mx` for multiplication, as specified in the
project conversation. Codon spellings are configurable and are not treated as
canonical registry commitments.

The program models invertible 2-D shears as short codon programs, composes them
into a rotation, and compares (1) a radial observer that identifies all states
with equal norm and (2) a full-state observer. The ordered product of edge
transport maps is called a discrete holonomy analogue. It is not claimed to be
a complete principal-bundle connection implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, isfinite, sin, sqrt, tan, pi
from typing import Union, Iterable

Scalar = Union[float, int]
Operand = Union[str, Scalar]
Vector = tuple[float, float]
Matrix = tuple[tuple[float, float], tuple[float, float]]


class CodonExecutionError(ValueError):
    """Raised for invalid codon programs or missing registers."""


@dataclass(frozen=True)
class Registry:
    """Configurable operation nomenclature for the experiment."""
    add: str = "ad"
    multiply: str = "mx"

    def operation(self, codon: str) -> str:
        table = {self.add: "add", self.multiply: "multiply"}
        try:
            return table[codon]
        except KeyError as exc:
            raise CodonExecutionError(f"Unknown codon in this registry profile: {codon}") from exc


@dataclass(frozen=True)
class Instruction:
    codon: str
    target: str
    left: Operand
    right: Operand


@dataclass(frozen=True)
class CodonProgram:
    instructions: tuple[Instruction, ...]
    registry: Registry
    label: str = ""

    def execute(self, x: float, y: float) -> Vector:
        regs: dict[str, float] = {"x": float(x), "y": float(y)}

        def resolve(value: Operand) -> float:
            if isinstance(value, str):
                if value not in regs:
                    raise CodonExecutionError(f"Register not initialized: {value}")
                return regs[value]
            return float(value)

        for ins in self.instructions:
            op = self.registry.operation(ins.codon)
            a, b = resolve(ins.left), resolve(ins.right)
            if op == "add":
                value = a + b
            elif op == "multiply":
                value = a * b
            else:  # defensive; Registry currently exposes only two operations
                raise CodonExecutionError(f"Unsupported operation: {op}")
            if not isfinite(value):
                raise CodonExecutionError("Non-finite intermediate value")
            regs[ins.target] = value
        return regs["x"], regs["y"]

    def matrix(self) -> Matrix:
        """Return the linear map by applying the program to the basis vectors."""
        c0 = self.execute(1.0, 0.0)
        c1 = self.execute(0.0, 1.0)
        return ((c0[0], c1[0]), (c0[1], c1[1]))


@dataclass(frozen=True)
class Shear:
    axis: str
    coefficient: float
    codon_program: CodonProgram

    def matrix(self) -> Matrix:
        # The transport map is derived from the executable codon program, not
        # from a parallel hard-coded matrix implementation.
        return self.codon_program.matrix()

    def apply(self, state: Vector) -> Vector:
        return self.codon_program.execute(*state)


@dataclass(frozen=True)
class Observer:
    name: str
    kind: str

    def observe(self, state: Vector) -> tuple[float, ...]:
        x, y = state
        if self.kind == "radius":
            return (hypot(x, y),)
        if self.kind == "squared_radius":
            return (x * x + y * y,)
        if self.kind == "full":
            return (x, y)
        if self.kind == "x_only":
            return (x,)
        raise ValueError(f"Unknown observer kind: {self.kind}")


RADIAL_OBSERVER = Observer("radial", "radius")
FULL_OBSERVER = Observer("full-state", "full")


def matmul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2))
        for i in range(2)
    )  # type: ignore[return-value]


def matvec(a: Matrix, v: Vector) -> Vector:
    return (
        a[0][0] * v[0] + a[0][1] * v[1],
        a[1][0] * v[0] + a[1][1] * v[1],
    )


def determinant(a: Matrix) -> float:
    return a[0][0] * a[1][1] - a[0][1] * a[1][0]


def inverse(a: Matrix) -> Matrix:
    det = determinant(a)
    if abs(det) < 1e-14:
        raise ValueError("Matrix is singular")
    return ((a[1][1] / det, -a[0][1] / det),
            (-a[1][0] / det, a[0][0] / det))


def transpose(a: Matrix) -> Matrix:
    return ((a[0][0], a[1][0]), (a[0][1], a[1][1]))


def identity() -> Matrix:
    return ((1.0, 0.0), (0.0, 1.0))


def max_abs_matrix_delta(a: Matrix, b: Matrix) -> float:
    return max(abs(a[i][j] - b[i][j]) for i in range(2) for j in range(2))


def _make_shear(axis: str, k: float, registry: Registry, index: int) -> Shear:
    if axis == "x":
        # tmp = mx(k, y); x = ad(x, tmp)
        instructions = (
            Instruction(registry.multiply, f"tmp{index}", k, "y"),
            Instruction(registry.add, "x", "x", f"tmp{index}"),
        )
    elif axis == "y":
        # tmp = mx(k, x); y = ad(y, tmp)
        instructions = (
            Instruction(registry.multiply, f"tmp{index}", k, "x"),
            Instruction(registry.add, "y", "y", f"tmp{index}"),
        )
    else:
        raise ValueError("axis must be 'x' or 'y'")
    program = CodonProgram(instructions, registry, label=f"{axis}-shear-{index}")
    return Shear(axis, float(k), program)


def compile_rotation(theta: float, registry: Registry = Registry()) -> tuple[Shear, Shear, Shear]:
    """Compile a rotation into three shears using ad/mx (or configured aliases).

    Valid for theta in (-pi, pi), excluding a numerical neighborhood of ±pi,
    where tan(theta/2) diverges.
    """
    if not isfinite(theta) or not (-pi < theta < pi):
        raise ValueError("theta must be finite and strictly between -pi and pi")
    if abs(cos(theta / 2.0)) < 1e-10:
        raise ValueError("theta is too close to ±pi for a stable three-shear form")
    a = -tan(theta / 2.0)
    b = sin(theta)
    return (
        _make_shear("x", a, registry, 1),
        _make_shear("y", b, registry, 2),
        _make_shear("x", a, registry, 3),
    )


def transport_matrix(path: Iterable[Shear]) -> Matrix:
    """Ordered product for chronological application of path edges."""
    total = identity()
    for edge in path:
        total = matmul(edge.matrix(), total)
    return total


def trace_path(path: Iterable[Shear], initial: Vector = (1.0, 0.0)) -> list[Vector]:
    states = [tuple(map(float, initial))]
    state = states[0]
    for edge in path:
        state = edge.apply(state)
        states.append(state)
    return states


def observer_closed(observer: Observer, initial: Vector, final: Vector, tol: float = 1e-10) -> bool:
    a, b = observer.observe(initial), observer.observe(final)
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


def oriented_phase(initial: Vector, final: Vector) -> float:
    """Signed angle from initial to final, in (-pi, pi]."""
    cross = initial[0] * final[1] - initial[1] * final[0]
    dot = initial[0] * final[0] + initial[1] * final[1]
    return atan2(cross, dot)


def reverse_path(path: tuple[Shear, ...]) -> tuple[Shear, ...]:
    """Construct inverse shears in reverse order."""
    out: list[Shear] = []
    for i, edge in enumerate(reversed(path), start=1):
        out.append(_make_shear(edge.axis, -edge.coefficient, edge.codon_program.registry, i))
    return tuple(out)


def conjugate(a: Matrix, basis: Matrix) -> Matrix:
    """Coordinate change T -> B T B^-1."""
    return matmul(matmul(basis, a), inverse(basis))


def trace(a: Matrix) -> float:
    return a[0][0] + a[1][1]


def rotation_error(a: Matrix, theta: float) -> float:
    target: Matrix = ((cos(theta), -sin(theta)), (sin(theta), cos(theta)))
    return max_abs_matrix_delta(a, target)


def path_samples(
    theta: float,
    segment_durations: tuple[float, float, float],
    samples_per_segment: int = 40,
    registry: Registry = Registry(),
    initial: Vector = (1.0, 0.0),
) -> list[dict[str, float]]:
    """Sample continuously interpolated shears under a time schedule.

    Each segment follows the same coefficient ramp 0 -> k. Segment durations
    alter timing but not the ordered endpoint transport or net holonomy.
    """
    if any(d <= 0 or not isfinite(d) for d in segment_durations):
        raise ValueError("segment durations must be positive and finite")
    if samples_per_segment < 2:
        raise ValueError("samples_per_segment must be >= 2")
    path = compile_rotation(theta, registry)
    rows: list[dict[str, float]] = []
    state_before: Vector = tuple(map(float, initial))
    time_offset = 0.0
    sample_idx = 0
    for edge, duration in zip(path, segment_durations):
        for j in range(samples_per_segment + 1):
            if sample_idx and j == 0:
                continue
            lam = j / samples_per_segment
            partial = _make_shear(edge.axis, edge.coefficient * lam, registry, 99)
            state = partial.apply(state_before)
            t = time_offset + lam * duration
            rows.append({
                "sample": float(sample_idx),
                "time": t,
                "segment": float(len(rows) // samples_per_segment),
                "progress": lam,
                "x": state[0],
                "y": state[1],
                "radius": hypot(*state),
                "angle": atan2(state[1], state[0]),
            })
            sample_idx += 1
        state_before = edge.apply(state_before)
        time_offset += duration
    return rows


def finite_difference_rms(rows: list[dict[str, float]], field: str) -> float:
    rates: list[float] = []
    for a, b in zip(rows, rows[1:]):
        dt = b["time"] - a["time"]
        if dt <= 0:
            continue
        rates.append((b[field] - a[field]) / dt)
    if not rates:
        return 0.0
    return sqrt(sum(v * v for v in rates) / len(rates))


def summarize(theta: float, registry: Registry = Registry()) -> dict[str, object]:
    path = compile_rotation(theta, registry)
    h = transport_matrix(path)
    initial = (1.0, 0.0)
    final = matvec(h, initial)
    states = trace_path(path, initial)
    radial_nodes = [RADIAL_OBSERVER.observe(s)[0] for s in states]
    phase = oriented_phase(initial, final)
    return {
        "theta_requested_rad": theta,
        "codon_profile": {"addition": registry.add, "multiplication": registry.multiply},
        "codon_chains": [
            [f"{registry.multiply}(k, {edge.axis == 'x' and 'y' or 'x'})", f"{registry.add}({edge.axis}, tmp)"]
            for edge in path
        ],
        "edge_axes": [edge.axis for edge in path],
        "edge_coefficients": [edge.coefficient for edge in path],
        "transport_matrix": [list(row) for row in h],
        "determinant": determinant(h),
        "trace": trace(h),
        "rotation_matrix_max_abs_error": rotation_error(h, theta),
        "holonomy_phase_rad": phase,
        "radial_observer_initial": radial_nodes[0],
        "radial_observer_final": radial_nodes[-1],
        "radial_observer_closed": observer_closed(RADIAL_OBSERVER, initial, final),
        "full_observer_closed": observer_closed(FULL_OBSERVER, initial, final),
        "radial_observer_path": radial_nodes,
        "full_state_path": [list(s) for s in states],
        "signed_orientation_changed": abs(phase) > 1e-10,
        "interpretation": "nontrivial lifted transport with closure only under the radial observer",
    }
