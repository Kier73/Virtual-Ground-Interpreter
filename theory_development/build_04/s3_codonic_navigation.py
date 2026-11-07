"""Build 04: codonic quaternion transport and Hopf-fibre holonomy.

Dependency-free reference implementation.

This is a finite-dimensional geometric experiment, not a claim that the full
Virtual Layer address space is already a principal bundle or that an S^3
coordinate has universal semantic meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, atan2, cos, isfinite, pi, sin, sqrt
from typing import Iterable, Sequence

Quat = tuple[float, float, float, float]  # (w, x, y, z)
Vec3 = tuple[float, float, float]


class CodonError(ValueError):
    pass


@dataclass(frozen=True)
class Registry:
    """Configurable aliases for scalar algebraic primitives."""
    add: str = "ad"
    sub: str = "su"
    mul: str = "mx"
    div: str = "dv"
    sqrt: str = "sr"

    def __post_init__(self) -> None:
        aliases = (self.add, self.sub, self.mul, self.div, self.sqrt)
        if any(not a or not a.strip() for a in aliases):
            raise ValueError("codon aliases must be nonempty")
        if len(set(aliases)) != len(aliases):
            raise ValueError("each scalar operation needs a distinct codon alias")

    def apply(self, codon: str, a: float, b: float | None = None) -> float:
        mapping = {
            self.add: "add", self.sub: "sub", self.mul: "mul",
            self.div: "div", self.sqrt: "sqrt",
        }
        if codon not in mapping:
            raise CodonError(f"Unknown codon: {codon}")
        op = mapping[codon]
        if op == "sqrt":
            if b is not None or a < 0:
                raise CodonError("sqrt expects one nonnegative operand")
            value = sqrt(a)
        else:
            if b is None:
                raise CodonError(f"{codon} expects two operands")
            if op == "add": value = a + b
            elif op == "sub": value = a - b
            elif op == "mul": value = a * b
            elif op == "div":
                if abs(b) < 1e-300:
                    raise CodonError("division by zero")
                value = a / b
            else:  # pragma: no cover - exhaustive mapping guard
                raise CodonError(f"Unsupported operation: {op}")
        if not isfinite(value):
            raise CodonError("Non-finite arithmetic result")
        return value


@dataclass(frozen=True)
class Instruction:
    codon: str
    target: str
    left: str | float
    right: str | float | None = None


@dataclass(frozen=True)
class Program:
    instructions: tuple[Instruction, ...]
    outputs: tuple[str, ...]
    registry: Registry
    inputs: tuple[str, ...]
    label: str = ""

    def execute(self, values: dict[str, float]) -> tuple[float, ...]:
        regs = {k: float(v) for k, v in values.items()}
        missing = [name for name in self.inputs if name not in regs]
        if missing:
            raise CodonError(f"Missing inputs: {missing}")

        def resolve(operand: str | float | None) -> float:
            if operand is None:
                raise CodonError("Missing operand")
            if isinstance(operand, str):
                if operand not in regs:
                    raise CodonError(f"Uninitialized register: {operand}")
                return regs[operand]
            return float(operand)

        for ins in self.instructions:
            a = resolve(ins.left)
            b = resolve(ins.right) if ins.right is not None else None
            regs[ins.target] = self.registry.apply(ins.codon, a, b)
        return tuple(regs[name] for name in self.outputs)


def compile_quaternion_multiply(registry: Registry = Registry()) -> Program:
    """Compile Hamilton product using only ad/su/mx scalar codons."""
    R = registry
    code: list[Instruction] = []
    # Each output component is a signed sum of four products.
    terms = {
        "ow": (("a0", "b0", 1), ("a1", "b1", -1), ("a2", "b2", -1), ("a3", "b3", -1)),
        "ox": (("a0", "b1", 1), ("a1", "b0", 1), ("a2", "b3", 1), ("a3", "b2", -1)),
        "oy": (("a0", "b2", 1), ("a1", "b3", -1), ("a2", "b0", 1), ("a3", "b1", 1)),
        "oz": (("a0", "b3", 1), ("a1", "b2", 1), ("a2", "b1", -1), ("a3", "b0", 1)),
    }
    for out, product_terms in terms.items():
        product_regs: list[tuple[str, int]] = []
        for idx, (left, right, sign) in enumerate(product_terms):
            name = f"{out}_p{idx}"
            code.append(Instruction(R.mul, name, left, right))
            product_regs.append((name, sign))
        acc = product_regs[0][0]
        for idx, (name, sign) in enumerate(product_regs[1:], start=1):
            target = out if idx == 3 else f"{out}_s{idx}"
            code.append(Instruction(R.add if sign > 0 else R.sub, target, acc, name))
            acc = target
    return Program(tuple(code), ("ow", "ox", "oy", "oz"), R,
                   tuple([f"a{i}" for i in range(4)] + [f"b{i}" for i in range(4)]),
                   "quaternion_hamilton_product")


@dataclass
class QuaternionAlgebra:
    registry: Registry = Registry()

    def __post_init__(self) -> None:
        self.qmul_program = compile_quaternion_multiply(self.registry)

    def qmul(self, a: Quat, b: Quat) -> Quat:
        result = self.qmul_program.execute({**{f"a{i}": a[i] for i in range(4)},
                                            **{f"b{i}": b[i] for i in range(4)}})
        return result  # type: ignore[return-value]

    def qconj(self, q: Quat) -> Quat:
        return (q[0], self.registry.apply(self.registry.sub, 0.0, q[1]),
                self.registry.apply(self.registry.sub, 0.0, q[2]),
                self.registry.apply(self.registry.sub, 0.0, q[3]))

    def norm_sq(self, q: Quat) -> float:
        products = [self.registry.apply(self.registry.mul, v, v) for v in q]
        a = self.registry.apply(self.registry.add, products[0], products[1])
        b = self.registry.apply(self.registry.add, products[2], products[3])
        return self.registry.apply(self.registry.add, a, b)

    def normalize(self, q: Quat) -> Quat:
        n2 = self.norm_sq(q)
        if n2 <= 1e-300:
            raise ValueError("Cannot normalize zero quaternion")
        n = self.registry.apply(self.registry.sqrt, n2)
        return tuple(self.registry.apply(self.registry.div, v, n) for v in q)  # type: ignore[return-value]

    def inverse_unit(self, q: Quat) -> Quat:
        if abs(self.norm_sq(q) - 1.0) > 1e-9:
            raise ValueError("inverse_unit requires a unit quaternion")
        return self.qconj(q)

    def rotate(self, q: Quat, v: Vec3) -> Vec3:
        pure = (0.0, v[0], v[1], v[2])
        out = self.qmul(self.qmul(q, pure), self.qconj(q))
        return (out[1], out[2], out[3])


ALG = QuaternionAlgebra()
K_AXIS: Vec3 = (0.0, 0.0, 1.0)
IDENTITY: Quat = (1.0, 0.0, 0.0, 0.0)


def vdot(a: Vec3, b: Vec3) -> float:
    return sum(x * y for x, y in zip(a, b))


def vnorm(v: Vec3) -> float:
    return sqrt(vdot(v, v))


def vnormalize(v: Vec3) -> Vec3:
    n = vnorm(v)
    if n < 1e-14:
        raise ValueError("Cannot normalize zero vector")
    return (v[0] / n, v[1] / n, v[2] / n)


def vcross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def qdot(a: Quat, b: Quat) -> float:
    return sum(x * y for x, y in zip(a, b))


def qnormalize(q: Quat, alg: QuaternionAlgebra = ALG) -> Quat:
    return alg.normalize(q)


def qexp_pure(v: Vec3) -> Quat:
    """Quaternion exponential of a pure-imaginary quaternion (0,v)."""
    angle = vnorm(v)
    if angle < 1e-15:
        return IDENTITY
    scale = sin(angle) / angle
    return (cos(angle), v[0] * scale, v[1] * scale, v[2] * scale)


def qlog_unit(q: Quat) -> Vec3:
    q = qnormalize(q)
    v = (q[1], q[2], q[3])
    s = vnorm(v)
    if s < 1e-15:
        if q[0] < 0.0:
            raise ValueError("S^3 logarithm at -1 is non-unique; supply a geodesic axis")
        return (0.0, 0.0, 0.0)
    angle = atan2(s, q[0])
    scale = angle / s
    return (v[0] * scale, v[1] * scale, v[2] * scale)


def q_power_unit(q: Quat, t: float) -> Quat:
    v = qlog_unit(q)
    return qexp_pure((v[0] * t, v[1] * t, v[2] * t))


def s3_distance(a: Quat, b: Quat) -> float:
    """Geodesic distance on S^3; antipodes remain distinct."""
    return acos(max(-1.0, min(1.0, qdot(qnormalize(a), qnormalize(b)))))


def so3_distance(a: Quat, b: Quat) -> float:
    """Rotation-angle distance on SO(3), identifying q and -q."""
    return 2.0 * acos(max(-1.0, min(1.0, abs(qdot(qnormalize(a), qnormalize(b))))))


def slerp_s3(a: Quat, b: Quat, t: float) -> Quat:
    """Shortest S^3 geodesic interpolation without antipodal sign folding."""
    if not 0.0 <= t <= 1.0:
        raise ValueError("t must lie in [0,1]")
    rel = ALG.qmul(ALG.inverse_unit(qnormalize(a)), qnormalize(b))
    step = q_power_unit(rel, t)
    return qnormalize(ALG.qmul(qnormalize(a), step))


def slerp_so3(a: Quat, b: Quat, t: float) -> Quat:
    """Shortest interpolation in SO(3), choosing the closer S^3 representative."""
    if qdot(a, b) < 0.0:
        b = tuple(-x for x in b)  # type: ignore[assignment]
    return slerp_s3(a, b, t)


def hopf_project(q: Quat) -> Vec3:
    """Hopf map q -> q*k*q^-1, a point on the unit 2-sphere."""
    return ALG.rotate(qnormalize(q), K_AXIS)


def fibre_phase(q0: Quat, q1: Quat) -> tuple[float, float]:
    """Return (phase, off-fibre residual) for a closed Hopf-base path."""
    rel = ALG.qmul(ALG.inverse_unit(qnormalize(q0)), qnormalize(q1))
    phase = atan2(rel[3], rel[0])
    residual = sqrt(rel[1] * rel[1] + rel[2] * rel[2])
    return phase, residual


def minimal_rotor(a: Vec3, b: Vec3) -> Quat:
    """Shortest unit quaternion whose conjugation maps a to b."""
    a, b = vnormalize(a), vnormalize(b)
    d = max(-1.0, min(1.0, vdot(a, b)))
    if d < -1.0 + 1e-12:
        trial = (1.0, 0.0, 0.0) if abs(a[0]) < 0.8 else (0.0, 1.0, 0.0)
        axis = vnormalize(vcross(a, trial))
        return (0.0, axis[0], axis[1], axis[2])
    c = vcross(a, b)
    return qnormalize((1.0 + d, c[0], c[1], c[2]))


def horizontal_lift(base_path: Sequence[Vec3], q0: Quat = IDENTITY,
                    alg: QuaternionAlgebra = ALG) -> list[Quat]:
    """Lift a sampled S^2 path to S^3 by successive minimal rotations.

    For the Hopf map h(q)=q*k*q^-1, these minimal left rotors implement the
    horizontal transport convention used in this prototype.
    """
    if len(base_path) < 2:
        raise ValueError("base_path must contain at least two points")
    path = [vnormalize(v) for v in base_path]
    start_error = vnorm(tuple(x - y for x, y in zip(hopf_project(q0), path[0])))
    if start_error > 1e-8:
        raise ValueError(f"q0 does not project to base_path[0] (error={start_error})")
    states = [qnormalize(q0, alg)]
    q = states[0]
    for n0, n1 in zip(path[:-1], path[1:]):
        rotor = minimal_rotor(n0, n1)
        q = alg.normalize(alg.qmul(rotor, q))
        states.append(q)
    return states


def cap_loop(theta: float, meridian_steps: int = 120,
             latitude_steps: int = 720) -> list[Vec3]:
    """Closed S^2 loop: north->latitude, one turn, return to north."""
    if not 0.0 < theta < pi:
        raise ValueError("theta must lie strictly between 0 and pi")
    if meridian_steps < 2 or latitude_steps < 8:
        raise ValueError("insufficient path resolution")
    path: list[Vec3] = []
    for i in range(meridian_steps + 1):
        colat = theta * i / meridian_steps
        path.append((sin(colat), 0.0, cos(colat)))
    for j in range(1, latitude_steps + 1):
        phi = 2.0 * pi * j / latitude_steps
        path.append((sin(theta) * cos(phi), sin(theta) * sin(phi), cos(theta)))
    for i in range(meridian_steps - 1, -1, -1):
        colat = theta * i / meridian_steps
        path.append((sin(colat), 0.0, cos(colat)))
    return path


def reverse_closed_path(path: Sequence[Vec3]) -> list[Vec3]:
    return list(reversed(path))


def wavy_cap_loop(theta0: float, amplitude: float = 0.12, mode: int = 2,
                  meridian_steps: int = 120, latitude_steps: int = 1200) -> list[Vec3]:
    """Closed north-based loop whose colatitude varies during the azimuthal turn."""
    if not (0.0 < theta0 < pi) or amplitude < 0.0 or mode < 1:
        raise ValueError("invalid wavy-cap parameters")
    if theta0 - amplitude <= 0.0 or theta0 + amplitude >= pi:
        raise ValueError("wavy boundary must stay away from the poles")
    path: list[Vec3] = []
    for i in range(meridian_steps + 1):
        colat = theta0 * i / meridian_steps
        path.append((sin(colat), 0.0, cos(colat)))
    for j in range(1, latitude_steps + 1):
        phi = 2.0 * pi * j / latitude_steps
        colat = theta0 + amplitude * sin(mode * phi)
        path.append((sin(colat) * cos(phi), sin(colat) * sin(phi), cos(colat)))
    for i in range(meridian_steps - 1, -1, -1):
        colat = theta0 * i / meridian_steps
        path.append((sin(colat), 0.0, cos(colat)))
    return path


def solid_angle_cap(theta: float) -> float:
    return 2.0 * pi * (1.0 - cos(theta))


def solid_angle_wavy_cap(theta0: float, amplitude: float = 0.12, mode: int = 2,
                         samples: int = 20000) -> float:
    """Area integral int_0^(2pi) (1-cos(theta(phi))) dphi, trapezoid rule."""
    if samples < 100:
        raise ValueError("samples must be >= 100")
    step = 2.0 * pi / samples
    values = [1.0 - cos(theta0 + amplitude * sin(mode * j * step))
              for j in range(samples + 1)]
    return step * (0.5 * values[0] + sum(values[1:-1]) + 0.5 * values[-1])


def spherical_path_report(theta: float, meridian_steps: int = 120,
                           latitude_steps: int = 720,
                           q0: Quat = IDENTITY) -> dict[str, object]:
    base = cap_loop(theta, meridian_steps, latitude_steps)
    lift = horizontal_lift(base, q0)
    qf = lift[-1]
    p0, pf = hopf_project(q0), hopf_project(qf)
    base_closure = vnorm(tuple(x - y for x, y in zip(p0, pf)))
    phase, off_fibre = fibre_phase(q0, qf)
    expected = 0.5 * solid_angle_cap(theta)
    return {
        "theta_colatitude_rad": theta,
        "base_points": len(base),
        "solid_angle_sr": solid_angle_cap(theta),
        "expected_hopf_phase_rad": expected,
        "measured_hopf_phase_rad": phase,
        "phase_abs_error_rad": abs(phase - expected),
        "base_endpoint_error": base_closure,
        "off_fibre_residual": off_fibre,
        "s3_endpoint_distance_rad": s3_distance(q0, qf),
        "so3_endpoint_distance_rad": so3_distance(q0, qf),
        "initial_quaternion": list(q0),
        "final_quaternion": list(qf),
        "relative_quaternion": list(ALG.qmul(ALG.inverse_unit(qnormalize(q0)), qf)),
    }


def gauge_shift(q: Quat, beta: float) -> Quat:
    """Change initial fibre representative by right multiplication exp(k beta)."""
    fibre = (cos(beta), 0.0, 0.0, sin(beta))
    return qnormalize(ALG.qmul(q, fibre))


def vector_error(a: Vec3, b: Vec3) -> float:
    return vnorm(tuple(x - y for x, y in zip(a, b)))


def q_error(a: Quat, b: Quat) -> float:
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def trace_csv(path: Sequence[Vec3], lift: Sequence[Quat]) -> str:
    rows = ["index,nx,ny,nz,qw,qx,qy,qz"]
    for i, (n, q) in enumerate(zip(path, lift)):
        rows.append(",".join([str(i), *(f"{x:.16g}" for x in n), *(f"{x:.16g}" for x in q)]))
    return "\n".join(rows) + "\n"


def build_report() -> dict[str, object]:
    theta_a, theta_b = 0.62, 0.98
    base_a, base_b = cap_loop(theta_a), cap_loop(theta_b)
    lift_a = horizontal_lift(base_a)
    lift_b = horizontal_lift(base_b)
    phase_a, fibre_res_a = fibre_phase(IDENTITY, lift_a[-1])
    phase_b, fibre_res_b = fibre_phase(IDENTITY, lift_b[-1])

    reversed_lift = horizontal_lift(reverse_closed_path(base_a))
    reverse_phase, reverse_residual = fibre_phase(IDENTITY, reversed_lift[-1])

    wavy_params = {"theta0": 0.72, "amplitude": 0.13, "mode": 3}
    wavy_base = wavy_cap_loop(**wavy_params)
    wavy_lift = horizontal_lift(wavy_base)
    wavy_phase, wavy_residual = fibre_phase(IDENTITY, wavy_lift[-1])
    wavy_area = solid_angle_wavy_cap(**wavy_params)

    beta = 0.47
    q0_shifted = gauge_shift(IDENTITY, beta)
    shifted_lift = horizontal_lift(base_a, q0_shifted)
    shifted_phase, shifted_residual = fibre_phase(q0_shifted, shifted_lift[-1])

    antipode = tuple(-x for x in IDENTITY)
    alias_registry = Registry(add="plus", sub="minus", mul="times", div="over", sqrt="root")
    alias_alg = QuaternionAlgebra(alias_registry)
    alias_program = compile_quaternion_multiply(alias_registry)
    sample_a = (0.8, 0.1, -0.2, 0.55)
    sample_b = (0.7, -0.3, 0.4, 0.2)
    default_product = ALG.qmul(sample_a, sample_b)
    alias_product = alias_alg.qmul(sample_a, sample_b)

    path = base_a
    lift = lift_a
    return {
        "build": "04",
        "title": "S3 Codonic Path Navigation and Hopf-Fibre Holonomy",
        "model_scope": "Finite-dimensional mathematical experiment; not the full Virtual Layer address substrate.",
        "registry": {"default": {"add": "ad", "sub": "su", "mul": "mx", "div": "dv", "sqrt": "sr"},
                     "alias": {"add": "plus", "sub": "minus", "mul": "times", "div": "over", "sqrt": "root"}},
        "quaternion_multiply_instruction_count": len(ALG.qmul_program.instructions),
        "quaternion_multiply_uses_only_scalar_primitives": True,
        "main_loop": spherical_path_report(theta_a),
        "second_loop": spherical_path_report(theta_b),
        "observer_views": {
            "hopf_base_endpoint_distance_rad": acos(max(-1.0, min(1.0, vdot(hopf_project(IDENTITY), hopf_project(lift_a[-1]))))),
            "full_s3_endpoint_distance_rad": s3_distance(IDENTITY, lift_a[-1]),
            "so3_rotation_distance_rad": so3_distance(IDENTITY, lift_a[-1]),
            "q_vs_minus_q_s3_distance_rad": s3_distance(IDENTITY, tuple(-x for x in IDENTITY)),
            "q_vs_minus_q_so3_distance_rad": so3_distance(IDENTITY, tuple(-x for x in IDENTITY)),
        },
        "same_base_endpoint_different_holonomy": {
            "base_endpoint_a": list(hopf_project(lift_a[-1])),
            "base_endpoint_b": list(hopf_project(lift_b[-1])),
            "base_endpoint_difference": vector_error(hopf_project(lift_a[-1]), hopf_project(lift_b[-1])),
            "phase_a_rad": phase_a,
            "phase_b_rad": phase_b,
            "phase_difference_rad": abs(phase_a - phase_b),
            "full_s3_endpoint_distance_between_lifts_rad": s3_distance(lift_a[-1], lift_b[-1]),
        },
        "path_reversal": {
            "forward_phase_rad": phase_a,
            "reverse_phase_rad": reverse_phase,
            "sum_rad": phase_a + reverse_phase,
            "off_fibre_residual": max(fibre_res_a, reverse_residual),
        },
        "noncircular_loop": {
            "parameters": wavy_params,
            "solid_angle_sr": wavy_area,
            "expected_hopf_phase_rad": 0.5 * wavy_area,
            "measured_hopf_phase_rad": wavy_phase,
            "phase_abs_error_rad": abs(wavy_phase - 0.5 * wavy_area),
            "off_fibre_residual": wavy_residual,
            "base_endpoint_error": vector_error(hopf_project(IDENTITY), hopf_project(wavy_lift[-1])),
        },
        "fibre_gauge_shift": {
            "initial_fibre_shift_rad": beta,
            "unshifted_holonomy_rad": phase_a,
            "shifted_holonomy_rad": shifted_phase,
            "difference_rad": abs(phase_a - shifted_phase),
            "off_fibre_residual": shifted_residual,
        },
        "antipodal_metric_distinction": {
            "s3_distance_q_to_minus_q_rad": s3_distance(IDENTITY, antipode),
            "so3_distance_q_to_minus_q_rad": so3_distance(IDENTITY, antipode),
        },
        "registry_alias_equivalence": {
            "default_product": list(default_product),
            "alias_product": list(alias_product),
            "max_abs_difference": q_error(default_product, alias_product),
            "alias_instruction_count": len(alias_program.instructions),
        },
        "interpolation": {
            "s3_midpoint_norm": sqrt(ALG.norm_sq(slerp_s3(IDENTITY, lift_a[-1], 0.5))),
            "so3_antipodal_midpoint_distance_to_identity": so3_distance(IDENTITY, slerp_so3(IDENTITY, antipode, 0.5)),
        },
        "trace_csv": trace_csv(path, lift),
    }


if __name__ == "__main__":
    import json
    report = build_report()
    report["trace_csv"] = "<see data/main_loop_trace.csv>"
    print(json.dumps(report, indent=2))
