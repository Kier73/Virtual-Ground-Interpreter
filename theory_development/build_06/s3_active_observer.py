"""Build 06: active observation over Hopf-fibre / S^3 codonic geometry.

This standalone research prototype combines:
- configurable codon aliases for scalar algebra;
- Hamilton quaternion multiplication compiled into codonic instructions;
- horizontal lifts of closed S^2 paths into S^3;
- observer-specific measurement families;
- intention-conditioned expected-information-gain probe selection;
- explicit unresolved outcomes when the available observer cannot distinguish
  the requested target.

It is a finite synthetic experiment, not a full Virtual Layer implementation
or a claim that the Hopf bundle models universal meaning.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from math import acos, atan2, cos, exp, isfinite, log, log2, pi, sin, sqrt
from random import Random
from typing import Callable, Mapping, Sequence

Quat = tuple[float, float, float, float]  # (w, x, y, z)
Vec3 = tuple[float, float, float]


# ---------------------------------------------------------------------------
# Minimal configurable codon algebra and compiled Hamilton product
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodonRegistry:
    add: str = "ad"
    sub: str = "su"
    mul: str = "mx"
    div: str = "dv"
    sqrt: str = "sr"

    def __post_init__(self) -> None:
        aliases = (self.add, self.sub, self.mul, self.div, self.sqrt)
        if any(not isinstance(a, str) or not a.strip() for a in aliases):
            raise ValueError("codon aliases must be nonempty strings")
        if len(set(aliases)) != len(aliases):
            raise ValueError("codon aliases must be distinct")

    def apply(self, codon: str, a: float, b: float | None = None) -> float:
        if codon == self.add:
            if b is None:
                raise ValueError("addition requires two operands")
            out = a + b
        elif codon == self.sub:
            if b is None:
                raise ValueError("subtraction requires two operands")
            out = a - b
        elif codon == self.mul:
            if b is None:
                raise ValueError("multiplication requires two operands")
            out = a * b
        elif codon == self.div:
            if b is None or abs(b) < 1e-300:
                raise ValueError("division requires a nonzero divisor")
            out = a / b
        elif codon == self.sqrt:
            if b is not None or a < 0:
                raise ValueError("square root requires one nonnegative operand")
            out = sqrt(a)
        else:
            raise ValueError(f"unknown codon {codon!r}")
        if not isfinite(out):
            raise ValueError("codon operation produced a non-finite value")
        return out


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
    inputs: tuple[str, ...]
    registry: CodonRegistry

    def execute(self, values: Mapping[str, float]) -> tuple[float, ...]:
        regs = {k: float(v) for k, v in values.items()}
        missing = [name for name in self.inputs if name not in regs]
        if missing:
            raise ValueError(f"missing program inputs: {missing}")

        def get(value: str | float | None) -> float:
            if value is None:
                raise ValueError("missing instruction operand")
            if isinstance(value, str):
                if value not in regs:
                    raise ValueError(f"uninitialized register {value!r}")
                return regs[value]
            return float(value)

        for ins in self.instructions:
            a = get(ins.left)
            b = get(ins.right) if ins.right is not None else None
            regs[ins.target] = self.registry.apply(ins.codon, a, b)
        return tuple(regs[name] for name in self.outputs)


def compile_hamilton_product(registry: CodonRegistry = CodonRegistry()) -> Program:
    """Compile qmul using only registry scalar add/subtract/multiply codons."""
    R = registry
    # q = a*b in Hamilton convention, for coordinates (w,x,y,z).
    rows = {
        "ow": (("a0", "b0", 1), ("a1", "b1", -1), ("a2", "b2", -1), ("a3", "b3", -1)),
        "ox": (("a0", "b1", 1), ("a1", "b0", 1), ("a2", "b3", 1), ("a3", "b2", -1)),
        "oy": (("a0", "b2", 1), ("a1", "b3", -1), ("a2", "b0", 1), ("a3", "b1", 1)),
        "oz": (("a0", "b3", 1), ("a1", "b2", 1), ("a2", "b1", -1), ("a3", "b0", 1)),
    }
    code: list[Instruction] = []
    for output, terms in rows.items():
        products: list[tuple[str, int]] = []
        for i, (left, right, sign) in enumerate(terms):
            reg = f"{output}_p{i}"
            code.append(Instruction(R.mul, reg, left, right))
            products.append((reg, sign))
        acc, _ = products[0]
        for i, (reg, sign) in enumerate(products[1:], start=1):
            target = output if i == 3 else f"{output}_s{i}"
            code.append(Instruction(R.add if sign > 0 else R.sub, target, acc, reg))
            acc = target
    return Program(tuple(code), ("ow", "ox", "oy", "oz"),
                   tuple(f"a{i}" for i in range(4)) + tuple(f"b{i}" for i in range(4)), R)


@dataclass
class QuaternionAlgebra:
    registry: CodonRegistry = CodonRegistry()

    def __post_init__(self) -> None:
        self.product_program = compile_hamilton_product(self.registry)

    def qmul(self, a: Quat, b: Quat) -> Quat:
        values = {f"a{i}": a[i] for i in range(4)}
        values.update({f"b{i}": b[i] for i in range(4)})
        return self.product_program.execute(values)  # type: ignore[return-value]

    def qconj(self, q: Quat) -> Quat:
        return (q[0], self.registry.apply(self.registry.sub, 0.0, q[1]),
                self.registry.apply(self.registry.sub, 0.0, q[2]),
                self.registry.apply(self.registry.sub, 0.0, q[3]))

    def norm_sq(self, q: Quat) -> float:
        R = self.registry
        squares = [R.apply(R.mul, x, x) for x in q]
        a = R.apply(R.add, squares[0], squares[1])
        b = R.apply(R.add, squares[2], squares[3])
        return R.apply(R.add, a, b)

    def normalize(self, q: Quat) -> Quat:
        R = self.registry
        n2 = self.norm_sq(q)
        if n2 <= 1e-300:
            raise ValueError("cannot normalize the zero quaternion")
        n = R.apply(R.sqrt, n2)
        return tuple(R.apply(R.div, x, n) for x in q)  # type: ignore[return-value]

    def rotate(self, q: Quat, v: Vec3) -> Vec3:
        pure: Quat = (0.0, v[0], v[1], v[2])
        out = self.qmul(self.qmul(self.normalize(q), pure), self.qconj(self.normalize(q)))
        return (out[1], out[2], out[3])


# ---------------------------------------------------------------------------
# S^2 paths, S^3 horizontal lifts, and geometric measurements
# ---------------------------------------------------------------------------

IDENTITY: Quat = (1.0, 0.0, 0.0, 0.0)
K_AXIS: Vec3 = (0.0, 0.0, 1.0)
DEFAULT_ALG = QuaternionAlgebra()


def dot3(a: Vec3, b: Vec3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def norm3(v: Vec3) -> float:
    return sqrt(dot3(v, v))


def normalize3(v: Vec3) -> Vec3:
    n = norm3(v)
    if n < 1e-14:
        raise ValueError("cannot normalize zero vector")
    return (v[0]/n, v[1]/n, v[2]/n)


def cross3(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def hopf_project(q: Quat, alg: QuaternionAlgebra = DEFAULT_ALG) -> Vec3:
    """Hopf map q -> q k q^{-1}; unit-quaternion q is required up to normalization."""
    return alg.rotate(alg.normalize(q), K_AXIS)


def minimal_rotor(a: Vec3, b: Vec3, alg: QuaternionAlgebra = DEFAULT_ALG) -> Quat:
    """Shortest rotor taking unit vector a to b by quaternion conjugation."""
    a, b = normalize3(a), normalize3(b)
    d = max(-1.0, min(1.0, dot3(a, b)))
    if d < -1.0 + 1e-12:
        trial = (1.0, 0.0, 0.0) if abs(a[0]) < 0.8 else (0.0, 1.0, 0.0)
        axis = normalize3(cross3(a, trial))
        return (0.0, axis[0], axis[1], axis[2])
    c = cross3(a, b)
    return alg.normalize((1.0 + d, c[0], c[1], c[2]))


def cap_loop(theta: float, direction: int = 1,
             meridian_steps: int = 48, latitude_steps: int = 480) -> tuple[Vec3, ...]:
    """North -> latitude(theta) -> one azimuthal turn -> north."""
    if not (0.0 < theta < pi) or direction not in (-1, 1):
        raise ValueError("theta must be in (0,pi) and direction must be +/-1")
    if meridian_steps < 2 or latitude_steps < 16:
        raise ValueError("insufficient path resolution")
    path: list[Vec3] = []
    for i in range(meridian_steps + 1):
        colat = theta * i / meridian_steps
        path.append((sin(colat), 0.0, cos(colat)))
    for j in range(1, latitude_steps + 1):
        phi = direction * 2.0 * pi * j / latitude_steps
        path.append((sin(theta)*cos(phi), sin(theta)*sin(phi), cos(theta)))
    for i in range(meridian_steps - 1, -1, -1):
        colat = theta * i / meridian_steps
        path.append((sin(colat), 0.0, cos(colat)))
    return tuple(path)


def horizontal_lift(base_path: Sequence[Vec3], q0: Quat = IDENTITY,
                    alg: QuaternionAlgebra = DEFAULT_ALG) -> tuple[Quat, ...]:
    """Lift a sampled S² path using successive minimal rotors (horizontal convention)."""
    if len(base_path) < 2:
        raise ValueError("base path requires at least two points")
    path = tuple(normalize3(v) for v in base_path)
    q = alg.normalize(q0)
    start_error = norm3(tuple(a-b for a, b in zip(hopf_project(q, alg), path[0])))
    if start_error > 1e-8:
        raise ValueError(f"q0 does not project to path start (error={start_error})")
    lifted = [q]
    for n0, n1 in zip(path[:-1], path[1:]):
        rotor = minimal_rotor(n0, n1, alg)
        q = alg.normalize(alg.qmul(rotor, q))
        lifted.append(q)
    return tuple(lifted)


def fibre_phase(q0: Quat, q1: Quat, alg: QuaternionAlgebra = DEFAULT_ALG) -> tuple[float, float]:
    """Relative U(1) phase and off-fibre residual, q0^-1*q1 = (w,0,0,z)."""
    rel = alg.qmul(alg.qconj(alg.normalize(q0)), alg.normalize(q1))
    phase = atan2(rel[3], rel[0])
    residual = sqrt(rel[1]*rel[1] + rel[2]*rel[2])
    return phase, residual


def unwrap_azimuth(path: Sequence[Vec3]) -> tuple[float, ...]:
    result: list[float] = []
    previous = 0.0
    for i, (x, y, _z) in enumerate(path):
        if sqrt(x*x + y*y) < 1e-10:
            phi = previous if result else 0.0
        else:
            raw = atan2(y, x)
            phi = raw + 2.0*pi*round((previous - raw)/(2.0*pi)) if result else raw
            while phi - previous > pi:
                phi -= 2.0*pi
            while phi - previous < -pi:
                phi += 2.0*pi
        result.append(phi)
        previous = phi
    return tuple(result)


def signed_solid_angle(path: Sequence[Vec3]) -> float:
    """North-gauge line integral ∮(1-cos(theta)) d(phi), trapezoidal on samples."""
    if len(path) < 3:
        raise ValueError("closed path requires at least three points")
    phis = unwrap_azimuth(path)
    integrand = [1.0 - max(-1.0, min(1.0, v[2])) for v in path]
    area = 0.0
    for i in range(len(path)-1):
        area += 0.5*(integrand[i] + integrand[i+1])*(phis[i+1]-phis[i])
    return area


def wrap_pi(angle: float) -> float:
    out = (angle + pi) % (2.0*pi) - pi
    # Adopt +pi for the exactly antipodal boundary, avoiding sign ambiguity.
    return pi if abs(out + pi) < 1e-12 else out


def s3_phase_absolute(q: Quat, alg: QuaternionAlgebra = DEFAULT_ALG) -> float:
    """Fibre phase relative to the fixed identity reference; not gauge-invariant."""
    qn = alg.normalize(q)
    return atan2(qn[3], qn[0])


def so3_signed_k_angle(q: Quat, alg: QuaternionAlgebra = DEFAULT_ALG) -> float:
    """SO(3) signed rotation about k; invariant under q -> -q."""
    return wrap_pi(2.0 * s3_phase_absolute(q, alg))


def s3_distance(a: Quat, b: Quat) -> float:
    aa, bb = DEFAULT_ALG.normalize(a), DEFAULT_ALG.normalize(b)
    return acos(max(-1.0, min(1.0, sum(x*y for x, y in zip(aa, bb)))))


def so3_distance(a: Quat, b: Quat) -> float:
    aa, bb = DEFAULT_ALG.normalize(a), DEFAULT_ALG.normalize(b)
    return 2.0*acos(max(-1.0, min(1.0, abs(sum(x*y for x, y in zip(aa, bb))))))


@dataclass(frozen=True)
class Candidate:
    name: str
    theta: float
    direction: int
    base_path: tuple[Vec3, ...]
    lift: tuple[Quat, ...]
    q_final: Quat


def make_candidates(theta_small: float = 0.62, theta_large: float = 0.98,
                    meridian_steps: int = 48, latitude_steps: int = 480,
                    alg: QuaternionAlgebra = DEFAULT_ALG) -> tuple[Candidate, ...]:
    out: list[Candidate] = []
    for size, theta in (("small", theta_small), ("large", theta_large)):
        for direction, suffix in ((1, "forward"), (-1, "reverse")):
            path = cap_loop(theta, direction, meridian_steps, latitude_steps)
            lift = horizontal_lift(path, alg=alg)
            out.append(Candidate(f"{size}_{suffix}", theta, direction, path, lift, lift[-1]))
    return tuple(out)


# ---------------------------------------------------------------------------
# Observer measurements, intention targets and active information gain
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Probe:
    name: str
    cost: float
    noise_std: float
    measurement: str

    def __post_init__(self) -> None:
        if self.cost <= 0.0 or self.noise_std <= 0.0:
            raise ValueError("probe cost and noise must be positive")


PROBES: Mapping[str, Probe] = {
    "base_endpoint": Probe("base_endpoint", 0.10, 0.010, "base_endpoint_z"),
    "base_apex": Probe("base_apex", 0.55, 0.030, "maximum_colatitude"),
    "base_area": Probe("base_area", 0.80, 0.080, "oriented_base_solid_angle"),
    "so3_angle": Probe("so3_angle", 0.70, 0.050, "signed_SO3_k_rotation"),
    "s3_phase": Probe("s3_phase", 0.90, 0.040, "signed_S3_fibre_phase"),
}


@dataclass(frozen=True)
class Observer:
    name: str
    available_probes: tuple[str, ...]
    noise_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if not self.available_probes or any(p not in PROBES for p in self.available_probes):
            raise ValueError("observer references an unknown or empty probe set")
        if self.noise_multiplier <= 0:
            raise ValueError("noise multiplier must be positive")


OBSERVERS: Mapping[str, Observer] = {
    "endpoint_only": Observer("endpoint_only", ("base_endpoint",)),
    "base_path": Observer("base_path_observer", ("base_endpoint", "base_apex", "base_area")),
    "so3": Observer("so3_rotation_observer", ("base_endpoint", "so3_angle")),
    "s3_lift": Observer("s3_lift_observer", ("base_endpoint", "base_apex", "so3_angle", "s3_phase")),
    "hybrid": Observer("hybrid_observer", tuple(PROBES.keys())),
}


@dataclass(frozen=True)
class Intent:
    name: str
    labels: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.labels:
            raise ValueError("intent requires target labels")


REGULAR_INTENTS: Mapping[str, Intent] = {
    "same_base_endpoint": Intent("same_base_endpoint", {h: "same" for h in
        ("small_forward", "small_reverse", "large_forward", "large_reverse")}),
    "cap_size": Intent("cap_size", {
        "small_forward": "small", "small_reverse": "small",
        "large_forward": "large", "large_reverse": "large"}),
    "loop_orientation": Intent("loop_orientation", {
        "small_forward": "forward", "large_forward": "forward",
        "small_reverse": "reverse", "large_reverse": "reverse"}),
    "full_path": Intent("full_path", {h: h for h in
        ("small_forward", "small_reverse", "large_forward", "large_reverse")}),
}


def measurement(candidate: Candidate, probe: Probe) -> float:
    if probe.measurement == "base_endpoint_z":
        return hopf_project(candidate.q_final)[2]
    if probe.measurement == "maximum_colatitude":
        return max(atan2(sqrt(x*x+y*y), z) for x, y, z in candidate.base_path)
    if probe.measurement == "oriented_base_solid_angle":
        return signed_solid_angle(candidate.base_path)
    if probe.measurement == "signed_SO3_k_rotation":
        return so3_signed_k_angle(candidate.q_final)
    if probe.measurement == "signed_S3_fibre_phase":
        return s3_phase_absolute(candidate.q_final)
    raise ValueError(f"unknown measurement {probe.measurement}")


def _normal_logpdf(y: float, mean: float, sigma: float) -> float:
    z = (y-mean)/sigma
    return -0.5*log(2*pi) - log(sigma) - 0.5*z*z


def _logsumexp(values: Sequence[float]) -> float:
    m = max(values)
    if m == float("-inf"):
        return m
    return m + log(sum(exp(v-m) for v in values))


# Gauss-Hermite nodes/weights for E[f(Z)] where Z~N(0,1), 5 point.
_GH_NODES = (-2.8569700138728056, -1.355626179974266, 0.0,
             1.355626179974266, 2.8569700138728056)
_GH_WEIGHTS = (0.0112574113277207, 0.2220759220056126, 0.5333333333333333,
               0.2220759220056126, 0.0112574113277207)


def normalized_prior(prior: Mapping[str, float], candidates: Sequence[Candidate]) -> dict[str, float]:
    names = [c.name for c in candidates]
    if set(prior) != set(names) or any(v < 0 for v in prior.values()):
        raise ValueError("prior must contain nonnegative mass for exactly all candidates")
    z = sum(prior.values())
    if z <= 0:
        raise ValueError("prior has zero total mass")
    return {name: prior[name]/z for name in names}


def expected_information_gain(probe: Probe, observer: Observer, intent: Intent,
                              prior: Mapping[str, float], candidates: Sequence[Candidate],
                              noise_scale: float = 1.0) -> float:
    """I(target label; scalar observation | probe), in bits, via Gaussian-mixture quadrature."""
    p = normalized_prior(prior, candidates)
    sigma = probe.noise_std * observer.noise_multiplier * noise_scale
    labels = {c.name: intent.labels[c.name] for c in candidates}
    classes = sorted(set(labels.values()))
    p_class = {z: sum(p[c.name] for c in candidates if labels[c.name] == z) for z in classes}
    means = {c.name: measurement(c, probe) for c in candidates}
    conditional: dict[str, dict[str, float]] = {}
    for z in classes:
        conditional[z] = {
            c.name: (p[c.name]/p_class[z] if labels[c.name] == z and p_class[z] > 0 else 0.0)
            for c in candidates
        }
    eig = 0.0
    for z in classes:
        if p_class[z] <= 0:
            continue
        for c in candidates:
            wh = conditional[z][c.name]
            if wh <= 0:
                continue
            mu = means[c.name]
            for node, weight in zip(_GH_NODES, _GH_WEIGHTS):
                y = mu + sigma*node
                log_p_y_given_z = _logsumexp([
                    log(w) + _normal_logpdf(y, means[c2.name], sigma)
                    for c2 in candidates if (w := conditional[z][c2.name]) > 0
                ])
                log_p_y = _logsumexp([
                    log(p_class[z2]) + _logsumexp([
                        log(w) + _normal_logpdf(y, means[c2.name], sigma)
                        for c2 in candidates if (w := conditional[z2][c2.name]) > 0
                    ]) for z2 in classes if p_class[z2] > 0
                ])
                eig += p_class[z]*wh*weight*(log_p_y_given_z-log_p_y)/log(2.0)
    return max(0.0, eig)


def target_posterior(prior: Mapping[str, float], intent: Intent,
                     candidates: Sequence[Candidate]) -> dict[str, float]:
    p = normalized_prior(prior, candidates)
    result: dict[str, float] = {}
    for c in candidates:
        label = intent.labels[c.name]
        result[label] = result.get(label, 0.0) + p[c.name]
    return result


def choose_probe(observer: Observer, intent: Intent, prior: Mapping[str, float],
                 candidates: Sequence[Candidate], noise_scales: Sequence[float] = (1.0, 1.5)) -> dict | None:
    """Robust EIG/cost selector. Returns None when available probes cannot resolve intent."""
    scores = []
    for name in observer.available_probes:
        probe = PROBES[name]
        eigs = [expected_information_gain(probe, observer, intent, prior, candidates, s)
                for s in noise_scales]
        robust = min(eigs)
        scores.append({"probe": name, "eig_bits": eigs[0], "robust_eig_bits": robust,
                       "cost": probe.cost, "utility": robust/probe.cost})
    scores.sort(key=lambda s: (-s["utility"], s["probe"]))
    if not scores or scores[0]["robust_eig_bits"] <= 1e-10:
        return None
    return scores[0]


def bayesian_update(prior: Mapping[str, float], probe: Probe, observer: Observer,
                    observed: float, candidates: Sequence[Candidate],
                    noise_scale: float = 1.0) -> dict[str, float]:
    p = normalized_prior(prior, candidates)
    sigma = probe.noise_std*observer.noise_multiplier*noise_scale
    logs = []
    for c in candidates:
        if p[c.name] <= 0:
            logs.append(float("-inf"))
        else:
            logs.append(log(p[c.name]) + _normal_logpdf(observed, measurement(c, probe), sigma))
    z = _logsumexp(logs)
    return {c.name: (exp(lw-z) if lw != float("-inf") else 0.0)
            for c, lw in zip(candidates, logs)}


def active_episode(true_candidate: Candidate, observer: Observer, intent: Intent,
                   candidates: Sequence[Candidate], rng: Random, max_steps: int = 3,
                   noise_scale: float = 1.0, confidence_threshold: float = 0.995) -> dict:
    prior = {c.name: 1.0/len(candidates) for c in candidates}
    labels = {intent.labels[c.name] for c in candidates}
    history: list[dict] = []
    if len(labels) == 1:
        return {"status": "already_resolved", "reason": "all candidates share the requested target label",
                "steps": 0, "total_cost": 0.0, "posterior": prior,
                "target_posterior": {next(iter(labels)): 1.0}, "history": history,
                "predicted_target": next(iter(labels)), "true_target": next(iter(labels)),
                "correct": True}

    status = "unresolved"
    reason = "probe budget exhausted"
    for step in range(max_steps):
        score = choose_probe(observer, intent, prior, candidates)
        if score is None:
            reason = "no available probe distinguishes the remaining target classes"
            break
        probe = PROBES[score["probe"]]
        mean = measurement(true_candidate, probe)
        sigma = probe.noise_std*observer.noise_multiplier*noise_scale
        observed = mean + rng.gauss(0.0, sigma)
        prior = bayesian_update(prior, probe, observer, observed, candidates, noise_scale)
        target_post = target_posterior(prior, intent, candidates)
        history.append({"step": step+1, "probe": probe.name, "measurement": probe.measurement,
                        "observation": observed, "expected_mean": mean,
                        "posterior": dict(prior), "target_posterior": target_post,
                        "robust_eig_bits_before": score["robust_eig_bits"],
                        "cost": probe.cost})
        if max(target_post.values()) >= confidence_threshold:
            status = "resolved"
            reason = "target posterior reached confidence threshold"
            break

    target_post = target_posterior(prior, intent, candidates)
    predicted = max(target_post, key=target_post.get)
    true_label = intent.labels[true_candidate.name]
    return {"status": status, "reason": reason, "steps": len(history),
            "total_cost": sum(h["cost"] for h in history), "posterior": prior,
            "target_posterior": target_post, "history": history,
            "predicted_target": predicted, "true_target": true_label,
            "correct": predicted == true_label if status == "resolved" else None}


def antipodal_pair(candidate: Candidate) -> tuple[Candidate, Candidate]:
    """Two S^3 representatives with the same base and SO(3) state: q and -q."""
    q = candidate.q_final
    qm: Quat = tuple(-x for x in q)  # type: ignore[assignment]
    return (replace(candidate, name="representative_q"),
            replace(candidate, name="representative_minus_q", q_final=qm))



def observable_equivalence_classes(observer: Observer, candidates: Sequence[Candidate],
                                   tolerance: float = 1e-8) -> list[list[str]]:
    """Partition candidates by their complete available observation-mean signatures.

    With the same Gaussian noise law for each candidate, equal signatures imply
    identical observation distributions for every currently admissible probe.
    This is the finite-model observable quotient for this observer.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    signatures = {c.name: tuple(measurement(c, PROBES[p])
                                for p in observer.available_probes)
                  for c in candidates}
    groups: list[list[str]] = []
    representatives: list[tuple[float, ...]] = []
    for c in candidates:
        sig = signatures[c.name]
        placed = False
        for i, rep in enumerate(representatives):
            if len(sig) == len(rep) and all(abs(x-y) <= tolerance for x,y in zip(sig, rep)):
                groups[i].append(c.name)
                placed = True
                break
        if not placed:
            representatives.append(sig)
            groups.append([c.name])
    return groups

def build_antipodal_intent() -> Intent:
    return Intent("s3_representative", {
        "representative_q": "q", "representative_minus_q": "minus_q"})


# ---------------------------------------------------------------------------
# Experiment reports and policy evaluation
# ---------------------------------------------------------------------------

def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total < 1:
        raise ValueError("total must be positive")
    p = successes/total
    den = 1.0 + z*z/total
    center = (p + z*z/(2*total))/den
    half = z*sqrt(p*(1-p)/total + z*z/(4*total*total))/den
    return max(0.0, center-half), min(1.0, center+half)


def sequential_policy_episode(candidate: Candidate, observer: Observer, intent: Intent,
                               candidates: Sequence[Candidate], rng: Random, policy: str,
                               max_steps: int = 2, noise_scale: float = 1.0,
                               confidence_threshold: float = 0.995) -> dict:
    """Run active, random-without-replacement, or fixed-initial-probe policies."""
    if policy not in ("active", "random", "fixed_initial"):
        raise ValueError("unknown policy")
    prior = {c.name: 1.0/len(candidates) for c in candidates}
    if len({intent.labels[c.name] for c in candidates}) == 1:
        return {"status": "already_resolved", "correct": True, "steps": 0,
                "cost": 0.0, "probes": []}
    fixed_score = choose_probe(observer, intent, prior, candidates) if policy == "fixed_initial" else None
    fixed_probe = PROBES[fixed_score["probe"]] if fixed_score else None
    unused = list(observer.available_probes)
    history = []
    status = "unresolved"
    for _ in range(max_steps):
        if policy == "active":
            score = choose_probe(observer, intent, prior, candidates)
            selected = PROBES[score["probe"]] if score else None
        elif policy == "fixed_initial":
            selected = fixed_probe
        else:
            if not unused:
                selected = None
            else:
                selected_name = unused.pop(rng.randrange(len(unused)))
                selected = PROBES[selected_name]
        if selected is None:
            break
        mean = measurement(candidate, selected)
        sigma = selected.noise_std*observer.noise_multiplier*noise_scale
        observed = mean + rng.gauss(0.0, sigma)
        prior = bayesian_update(prior, selected, observer, observed, candidates, noise_scale)
        target_post = target_posterior(prior, intent, candidates)
        history.append({"probe": selected.name, "observation": observed,
                        "posterior_target": target_post, "cost": selected.cost})
        if max(target_post.values()) >= confidence_threshold:
            status = "resolved"
            break
    target_post = target_posterior(prior, intent, candidates)
    predicted = max(target_post, key=target_post.get)
    true = intent.labels[candidate.name]
    return {"status": status, "correct": (predicted == true) if status == "resolved" else None,
            "steps": len(history), "cost": sum(h["cost"] for h in history),
            "probes": [h["probe"] for h in history], "target_posterior": target_post}


def evaluate_sequential(observer: Observer, intent: Intent, candidates: Sequence[Candidate],
                        n_per_candidate: int = 60, max_steps: int = 2,
                        noise_scale: float = 1.0, seed: int = 1234) -> dict:
    """Compare active selection with random and one-probe-plan repetition."""
    result: dict[str, dict] = {}
    for offset, policy in enumerate(("active", "random", "fixed_initial")):
        rng = Random(seed + offset)
        rows = [sequential_policy_episode(c, observer, intent, candidates, rng,
                                          policy, max_steps, noise_scale)
                for c in candidates for _ in range(n_per_candidate)]
        resolved = [r for r in rows if r["status"] == "resolved"]
        correct = sum(1 for r in resolved if r["correct"])
        lo, hi = wilson_interval(correct, len(resolved)) if resolved else (0.0, 0.0)
        result[policy] = {
            "trials": len(rows), "resolved_trials": len(resolved),
            "resolution_rate": len(resolved)/len(rows),
            "resolved_accuracy": correct/len(resolved) if resolved else None,
            "resolved_accuracy_wilson_95": [lo, hi],
            "mean_probe_cost": sum(r["cost"] for r in rows)/len(rows),
            "mean_probe_count": sum(r["steps"] for r in rows)/len(rows),
        }
    return result

def make_report(candidates: Sequence[Candidate]) -> dict:
    names = [c.name for c in candidates]
    uniform = {n: 1.0/len(names) for n in names}
    selection: dict[str, dict[str, dict | None]] = {}
    selection_status: dict[str, dict[str, str]] = {}
    for obs_name, observer in OBSERVERS.items():
        selection[obs_name] = {}
        selection_status[obs_name] = {}
        for intent_name, intent in REGULAR_INTENTS.items():
            score = choose_probe(observer, intent, uniform, candidates)
            selection[obs_name][intent_name] = score
            if len(set(intent.labels[c.name] for c in candidates)) == 1:
                selection_status[obs_name][intent_name] = "no_probe_needed_target_constant"
            elif score is None:
                selection_status[obs_name][intent_name] = "unresolved_no_discriminating_probe"
            else:
                selection_status[obs_name][intent_name] = "probe_selected"

    antipode_base = candidates[0]
    antipodes = antipodal_pair(antipode_base)
    anti_intent = build_antipodal_intent()
    anti_observers = {
        "endpoint_only": OBSERVERS["endpoint_only"],
        "base_path": OBSERVERS["base_path"],
        "so3": OBSERVERS["so3"],
        "s3_lift": OBSERVERS["s3_lift"],
    }
    anti_selection = {}
    anti_candidate_metrics = {
        "hopf_base_distance": norm3(tuple(a-b for a, b in zip(
            hopf_project(antipodes[0].q_final), hopf_project(antipodes[1].q_final)))),
        "s3_distance_rad": s3_distance(antipodes[0].q_final, antipodes[1].q_final),
        "so3_distance_rad": so3_distance(antipodes[0].q_final, antipodes[1].q_final),
        "s3_phase_q": s3_phase_absolute(antipodes[0].q_final),
        "s3_phase_minus_q": s3_phase_absolute(antipodes[1].q_final),
        "so3_angle_q": so3_signed_k_angle(antipodes[0].q_final),
        "so3_angle_minus_q": so3_signed_k_angle(antipodes[1].q_final),
    }
    anti_prior = {c.name: 0.5 for c in antipodes}
    for obs_name, observer in anti_observers.items():
        anti_selection[obs_name] = choose_probe(observer, anti_intent, anti_prior, antipodes)

    geometry_rows = []
    for c in candidates:
        phase, residual = fibre_phase(IDENTITY, c.q_final)
        geometry_rows.append({
            "name": c.name, "theta_rad": c.theta, "direction": c.direction,
            "base_endpoint": list(hopf_project(c.q_final)),
            "base_signed_area_sr": signed_solid_angle(c.base_path),
            "expected_s3_phase_half_area_rad": 0.5*signed_solid_angle(c.base_path),
            "measured_s3_phase_rad": phase,
            "phase_error_rad": abs(phase - 0.5*signed_solid_angle(c.base_path)),
            "off_fibre_residual": residual,
            "so3_signed_k_angle_rad": so3_signed_k_angle(c.q_final),
        })

    # Monte Carlo: active versus random, one probe, under two observation families.
    policy_eval = {
        "base_path_full_path": evaluate_sequential(OBSERVERS["base_path"], REGULAR_INTENTS["full_path"],
                                                   candidates, n_per_candidate=60, max_steps=2, noise_scale=1.0),
        "s3_lift_antipodal": evaluate_sequential(OBSERVERS["s3_lift"], anti_intent,
                                                  antipodes, n_per_candidate=100, max_steps=2, noise_scale=1.0),
    }
    active_traces = {
        "base_path_full_path": active_episode(
            next(c for c in candidates if c.name == "large_reverse"), OBSERVERS["base_path"],
            REGULAR_INTENTS["full_path"], candidates, Random(21), max_steps=3),
        "endpoint_only_full_path": active_episode(
            candidates[0], OBSERVERS["endpoint_only"], REGULAR_INTENTS["full_path"],
            candidates, Random(22), max_steps=3),
        "same_endpoint_intention": active_episode(
            candidates[0], OBSERVERS["endpoint_only"], REGULAR_INTENTS["same_base_endpoint"],
            candidates, Random(23), max_steps=3),
        "s3_lift_antipodal": active_episode(
            antipodes[1], OBSERVERS["s3_lift"], anti_intent, antipodes, Random(24), max_steps=3),
    }
    regular_partitions = {name: observable_equivalence_classes(observer, candidates)
                          for name, observer in OBSERVERS.items()}
    antipodal_partitions = {name: observable_equivalence_classes(observer, antipodes)
                            for name, observer in anti_observers.items()}

    endpoint_impossibility = {
        "observer": "endpoint_only", "intent": "full_path",
        "selection": selection["endpoint_only"]["full_path"],
        "interpretation": "All available endpoint measurements are equal within numerical tolerance; no active policy can infer the path class from endpoint-only data.",
    }
    return {
        "build": "06",
        "title": "Active Observation on S3 / Hopf Geometry",
        "scope": "Finite synthetic Hopf-bundle experiment. Not the full Virtual Layer address space.",
        "codon_registry": {"default": {"add": "ad", "sub": "su", "mul": "mx", "div": "dv", "sqrt": "sr"},
                           "alias_test": {"add": "plus", "sub": "minus", "mul": "times", "div": "over", "sqrt": "root"}},
        "compiled_hamilton_product_instructions": len(DEFAULT_ALG.product_program.instructions),
        "regular_path_hypotheses": geometry_rows,
        "observer_intention_probe_selection": selection,
        "observer_intention_selection_status": selection_status,
        "observable_quotient_partitions": {
            "regular_paths": regular_partitions,
            "antipodal_pair": antipodal_partitions,
            "interpretation": "Candidates in the same class have equal observation means for every probe available to that observer; with the common noise law, their observation distributions are identical within tolerance."
        },
        "endpoint_only_nonidentifiability": endpoint_impossibility,
        "antipodal_quotient_control": {
            "candidate_names": [c.name for c in antipodes],
            "metrics": anti_candidate_metrics,
            "observer_intention_probe_selection": anti_selection,
            "interpretation": "Hopf base and SO(3) identify q with -q; S3 retains the antipodal distinction.",
        },
        "sequential_policy_evaluation": policy_eval,
        "active_episode_traces": active_traces,
        "constraints": [
            "Probe costs and noise levels are synthetic relative units.",
            "The base-path area probe assumes the observer can retain the full projected trajectory and knows the chosen connection convention.",
            "Endpoint-only observers do not receive path-history or fibre-phase data.",
            "The S3 phase probe uses a fixed reference representative; it is not invariant to arbitrary fibre gauge changes.",
            "The SO3 probe measures the signed rotation about the known k-axis and identifies q with -q.",
            "No emotional or biological tone labels are inferred.",
        ],
    }


def csv_trace(candidates: Sequence[Candidate]) -> str:
    rows = ["candidate,index,nx,ny,nz,qw,qx,qy,qz"]
    for c in candidates:
        for i, (n, q) in enumerate(zip(c.base_path, c.lift)):
            rows.append(",".join([c.name, str(i), *(f"{v:.16g}" for v in n),
                                   *(f"{v:.16g}" for v in q)]))
    return "\n".join(rows) + "\n"


def probe_ranking_csv(candidates: Sequence[Candidate]) -> str:
    rows = ["observer,intent,probe,eig_bits,robust_eig_bits,cost,utility"]
    prior = {c.name: 1.0/len(candidates) for c in candidates}
    for obs_name, observer in OBSERVERS.items():
        for intent_name, intent in REGULAR_INTENTS.items():
            scores = []
            for p_name in observer.available_probes:
                p = PROBES[p_name]
                e1 = expected_information_gain(p, observer, intent, prior, candidates, 1.0)
                e2 = expected_information_gain(p, observer, intent, prior, candidates, 1.5)
                scores.append((p_name, e1, min(e1, e2), p.cost, min(e1, e2)/p.cost))
            for row in sorted(scores, key=lambda x: (-x[4], x[0])):
                rows.append(",".join([obs_name, intent_name, row[0], *(f"{x:.12g}" for x in row[1:])]))
    return "\n".join(rows) + "\n"


def run_episode_trace(candidate: Candidate, observer: Observer, intent: Intent,
                      candidates: Sequence[Candidate], seed: int = 17) -> dict:
    return active_episode(candidate, observer, intent, candidates, Random(seed), max_steps=3)


if __name__ == "__main__":
    import json
    candidates = make_candidates()
    report = make_report(candidates)
    print(json.dumps(report, indent=2, sort_keys=True))
