"""Build 07: cross-observer invariant discovery over codonic Hopf paths.

Standalone standard-library research prototype.

The experiment constructs a finite library of closed paths on S^2, horizontally
lifts them to S^3, and compares observer-specific representational
dissimilarity matrices (RDMs). It includes reparameterization, alias-renaming,
resolution, and shuffled-correspondence controls.

This is a synthetic finite experiment, not a full Virtual Layer implementation
and not evidence for a universal geometry of meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, atan2, cos, exp, log, pi, sin, sqrt
from random import Random
from statistics import mean, pstdev
from typing import Iterable, Sequence

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]


# ---------------------------------------------------------------------------
# Configurable codon algebra and quaternion execution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodonRegistry:
    add: str = "ad"
    sub: str = "su"
    mul: str = "mx"
    div: str = "dv"
    sqrt: str = "sr"

    def __post_init__(self) -> None:
        values = (self.add, self.sub, self.mul, self.div, self.sqrt)
        if any(not isinstance(x, str) or not x.strip() for x in values):
            raise ValueError("codon aliases must be nonempty strings")
        if len(set(values)) != len(values):
            raise ValueError("codon aliases must be unique")

    def apply(self, codon: str, a: float, b: float | None = None) -> float:
        if codon == self.add:
            if b is None: raise ValueError("ad requires two operands")
            value = a + b
        elif codon == self.sub:
            if b is None: raise ValueError("su requires two operands")
            value = a - b
        elif codon == self.mul:
            if b is None: raise ValueError("mx requires two operands")
            value = a * b
        elif codon == self.div:
            if b is None or abs(b) < 1e-300: raise ValueError("dv requires nonzero divisor")
            value = a / b
        elif codon == self.sqrt:
            if b is not None or a < 0: raise ValueError("sr requires one nonnegative operand")
            value = sqrt(a)
        else:
            raise ValueError(f"unknown codon: {codon}")
        if not (float("-inf") < value < float("inf")):
            raise ValueError("non-finite result")
        return value


@dataclass(frozen=True)
class Instr:
    op: str
    out: str
    a: str
    b: str | None = None


@dataclass(frozen=True)
class CodonProgram:
    code: tuple[Instr, ...]
    outputs: tuple[str, ...]
    registry: CodonRegistry

    def run(self, inputs: dict[str, float]) -> tuple[float, ...]:
        r = dict(inputs)
        for ins in self.code:
            if ins.a not in r or (ins.b is not None and ins.b not in r):
                raise ValueError("uninitialized register")
            r[ins.out] = self.registry.apply(
                ins.op, r[ins.a], None if ins.b is None else r[ins.b])
        return tuple(r[x] for x in self.outputs)


def compile_qmul(reg: CodonRegistry) -> CodonProgram:
    # Hamilton product, compiled as scalar multiplications and signed additions.
    rows = {
        "w": ((0, 0, 1), (1, 1, -1), (2, 2, -1), (3, 3, -1)),
        "x": ((0, 1, 1), (1, 0, 1), (2, 3, 1), (3, 2, -1)),
        "y": ((0, 2, 1), (1, 3, -1), (2, 0, 1), (3, 1, 1)),
        "z": ((0, 3, 1), (1, 2, 1), (2, 1, -1), (3, 0, 1)),
    }
    code: list[Instr] = []
    for out, terms in rows.items():
        products = []
        for i, (ai, bi, sign) in enumerate(terms):
            p = f"{out}_p{i}"
            code.append(Instr(reg.mul, p, f"a{ai}", f"b{bi}"))
            products.append((p, sign))
        acc = products[0][0]
        for i, (p, sign) in enumerate(products[1:], 1):
            nxt = out if i == 3 else f"{out}_s{i}"
            code.append(Instr(reg.add if sign > 0 else reg.sub, nxt, acc, p))
            acc = nxt
    return CodonProgram(tuple(code), ("w", "x", "y", "z"), reg)


class QuaternionOps:
    def __init__(self, registry: CodonRegistry = CodonRegistry()):
        self.registry = registry
        self.program = compile_qmul(registry)

    def mul(self, a: Quat, b: Quat) -> Quat:
        d = {f"a{i}": a[i] for i in range(4)}
        d.update({f"b{i}": b[i] for i in range(4)})
        return self.program.run(d)  # type: ignore[return-value]

    def conj(self, q: Quat) -> Quat:
        return (q[0], -q[1], -q[2], -q[3])

    def norm(self, q: Quat) -> float:
        return sqrt(sum(x*x for x in q))

    def normalize(self, q: Quat) -> Quat:
        n = self.norm(q)
        if n < 1e-14: raise ValueError("zero quaternion")
        return tuple(x/n for x in q)  # type: ignore[return-value]

    def rotate(self, q: Quat, v: Vec3) -> Vec3:
        q = self.normalize(q)
        p = (0.0, *v)
        z = self.mul(self.mul(q, p), self.conj(q))
        return (z[1], z[2], z[3])


IDENTITY: Quat = (1.0, 0.0, 0.0, 0.0)
NORTH: Vec3 = (0.0, 0.0, 1.0)


def dot(a: Vec3, b: Vec3) -> float:
    return sum(x*y for x, y in zip(a, b))


def norm(v: Vec3) -> float:
    return sqrt(dot(v, v))


def unit(v: Vec3) -> Vec3:
    n = norm(v)
    if n < 1e-14: raise ValueError("zero vector")
    return tuple(x/n for x in v)  # type: ignore[return-value]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def geodesic_s2(a: Vec3, b: Vec3) -> float:
    return acos(max(-1.0, min(1.0, dot(unit(a), unit(b)))))


def geodesic_s3(a: Quat, b: Quat) -> float:
    aa, bb = DEFAULT_Q.normalize(a), DEFAULT_Q.normalize(b)
    return acos(max(-1.0, min(1.0, sum(x*y for x, y in zip(aa, bb)))))


def wrap_pi(x: float) -> float:
    y = (x + pi) % (2*pi) - pi
    return pi if abs(y + pi) < 1e-12 else y


def minimal_rotor(a: Vec3, b: Vec3, qops: QuaternionOps) -> Quat:
    a, b = unit(a), unit(b)
    d = max(-1.0, min(1.0, dot(a, b)))
    if d < -1 + 1e-12:
        trial = (1.0, 0.0, 0.0) if abs(a[0]) < 0.8 else (0.0, 1.0, 0.0)
        axis = unit(cross(a, trial))
        return (0.0, axis[0], axis[1], axis[2])
    c = cross(a, b)
    return qops.normalize((1+d, c[0], c[1], c[2]))


DEFAULT_Q = QuaternionOps()


# ---------------------------------------------------------------------------
# Candidate paths: smooth spherical loops, reverse paths, and time warps
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShapeSpec:
    shape_id: str
    theta: float
    amplitude: float
    harmonic: int
    phase: float


@dataclass(frozen=True)
class PathCandidate:
    name: str
    shape_id: str
    direction: int
    warp_gamma: float
    path: tuple[Vec3, ...]          # geometric polyline, independent of time parameterization
    temporal_path: tuple[Vec3, ...] # same polyline sampled as a time series
    lift: tuple[Quat, ...]
    phase: float
    area: float


def raw_spherical_polyline(spec: ShapeSpec, direction: int, n_boundary: int = 720,
                           n_meridian: int = 72) -> tuple[Vec3, ...]:
    if direction not in (-1, 1): raise ValueError("direction must be +/-1")
    # Meridian from north to the boundary start.
    theta_start = spec.theta + spec.amplitude*cos(spec.phase)
    if not (0.05 < theta_start < pi-0.05): raise ValueError("invalid boundary start")
    pts: list[Vec3] = []
    for i in range(n_meridian + 1):
        t = theta_start*i/n_meridian
        pts.append((sin(t), 0.0, cos(t)))
    # A star-shaped loop. All harmonics are integer so the boundary closes.
    for j in range(1, n_boundary + 1):
        u = j/n_boundary
        phi = 2*pi*u
        theta = spec.theta + spec.amplitude*cos(spec.harmonic*phi + spec.phase)
        pts.append((sin(theta)*cos(phi), sin(theta)*sin(phi), cos(theta)))
    # Return along the same meridian.
    for i in range(n_meridian - 1, -1, -1):
        t = theta_start*i/n_meridian
        pts.append((sin(t), 0.0, cos(t)))
    forward = tuple(unit(p) for p in pts)
    # Reverse the complete same geometric loop. This preserves the locus exactly
    # and changes only traversal orientation.
    return forward if direction > 0 else tuple(reversed(forward))


def cumulative_lengths(path: Sequence[Vec3]) -> tuple[list[float], float]:
    c = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        c.append(c[-1] + geodesic_s2(a, b))
    return c, c[-1]


def interp_s2(a: Vec3, b: Vec3, t: float) -> Vec3:
    # Normalized chord interpolation is stable for the short sampled segments.
    return unit(tuple((1-t)*x+t*y for x, y in zip(a, b)))  # type: ignore[arg-type]


def resample_by_fraction(path: Sequence[Vec3], fractions: Sequence[float]) -> tuple[Vec3, ...]:
    c, total = cumulative_lengths(path)
    if total <= 1e-14: raise ValueError("zero-length path")
    out = []
    j = 0
    for f in fractions:
        target = max(0.0, min(1.0, f))*total
        while j < len(c)-2 and c[j+1] < target:
            j += 1
        den = c[j+1]-c[j]
        local = 0.0 if den < 1e-14 else (target-c[j])/den
        out.append(interp_s2(path[j], path[j+1], local))
    return tuple(out)


def horizontal_lift(path: Sequence[Vec3], qops: QuaternionOps) -> tuple[Quat, ...]:
    q: Quat = IDENTITY
    out = [q]
    for a, b in zip(path[:-1], path[1:]):
        q = qops.normalize(qops.mul(minimal_rotor(a, b, qops), q))
        out.append(q)
    return tuple(out)


def signed_solid_angle(path: Sequence[Vec3]) -> float:
    # For the north gauge, integrate (1-z) d(phi); unwrap azimuth.
    phis: list[float] = []
    prev = 0.0
    for i, (x, y, _z) in enumerate(path):
        if x*x+y*y < 1e-18:
            p = prev if phis else 0.0
        else:
            raw = atan2(y, x)
            p = raw if not phis else raw + 2*pi*round((prev-raw)/(2*pi))
            while p-prev > pi: p -= 2*pi
            while p-prev < -pi: p += 2*pi
        phis.append(p); prev = p
    vals = [1.0-p[2] for p in path]
    area = sum(0.5*(vals[i]+vals[i+1])*(phis[i+1]-phis[i]) for i in range(len(path)-1))
    return area


def build_candidate(spec: ShapeSpec, direction: int, warp_gamma: float,
                    sample_count: int = 640, qops: QuaternionOps = DEFAULT_Q,
                    boundary_steps: int = 720, meridian_steps: int = 72) -> PathCandidate:
    # Keep one canonical geometric polyline. Time warping changes only the
    # observation schedule, never the underlying curve used for geometry/lift.
    path = raw_spherical_polyline(spec, direction, boundary_steps, meridian_steps)
    fractions = [(i/(sample_count-1))**warp_gamma for i in range(sample_count)]
    temporal_path = resample_by_fraction(path, fractions)
    lift = horizontal_lift(path, qops)
    phase, residual = fibre_phase(lift[0], lift[-1], qops)
    if residual > 2e-5:
        raise AssertionError(f"lift did not close onto a fibre: residual={residual}")
    area = signed_solid_angle(path)
    return PathCandidate(f"{spec.shape_id}_{'fwd' if direction>0 else 'rev'}_g{warp_gamma:g}",
                         spec.shape_id, direction, warp_gamma, path, temporal_path, lift, phase, area)


def fibre_phase(q0: Quat, q1: Quat, qops: QuaternionOps) -> tuple[float, float]:
    rel = qops.mul(qops.conj(qops.normalize(q0)), qops.normalize(q1))
    return atan2(rel[3], rel[0]), sqrt(rel[1]*rel[1]+rel[2]*rel[2])


SHAPES = (
    ShapeSpec("cap_055", 0.55, 0.000, 0, 0.0),
    ShapeSpec("cap_072", 0.72, 0.000, 0, 0.0),
    ShapeSpec("cap_092", 0.92, 0.000, 0, 0.0),
    ShapeSpec("wave2_a", 0.73, 0.075, 2, 0.0),
    ShapeSpec("wave2_b", 0.73, 0.075, 2, 0.65),
    ShapeSpec("wave3_a", 0.82, 0.060, 3, 0.15),
    ShapeSpec("wave3_b", 0.82, 0.060, 3, 0.85),
    ShapeSpec("wave4", 0.94, 0.040, 4, 0.35),
)


def build_library(sample_count: int = 640, qops: QuaternionOps = DEFAULT_Q) -> tuple[PathCandidate, ...]:
    result = []
    for spec in SHAPES:
        for direction in (1, -1):
            result.append(build_candidate(spec, direction, 1.0, sample_count, qops))
            # Add one time-warped representation of the same directed geometry.
            result.append(build_candidate(spec, direction, 1.7 if direction > 0 else 0.62,
                                          sample_count, qops))
    return tuple(result)


# ---------------------------------------------------------------------------
# Observer signatures and RDMs
# ---------------------------------------------------------------------------

def arclength_path(candidate: PathCandidate, n: int = 256) -> tuple[Vec3, ...]:
    return resample_by_fraction(candidate.path, [i/(n-1) for i in range(n)])


def trajectory_length(path: Sequence[Vec3]) -> float:
    return sum(geodesic_s2(a, b) for a, b in zip(path[:-1], path[1:]))


def mean_sd(values: Sequence[float]) -> tuple[float, float]:
    return mean(values), pstdev(values)


def dft_coefficients(values: Sequence[float], max_k: int = 8) -> tuple[float, ...]:
    n = len(values)
    out = []
    for k in range(1, max_k+1):
        re = sum(v*cos(2*pi*k*j/n) for j, v in enumerate(values))/n
        im = -sum(v*sin(2*pi*k*j/n) for j, v in enumerate(values))/n
        out.extend((re, im))
    return tuple(out)


def turning_angles(path: Sequence[Vec3]) -> tuple[float, ...]:
    """Geodesic turning magnitude using both tangent directions at the vertex.

    The incoming tangent is projected from the previous point into T_p(S^2);
    the outgoing tangent is projected from the next point into the same tangent
    plane. Subtracting their angle from pi makes a straight geodesic continue
    with zero turn. This is reversal-invariant up to discretization.
    """
    vals = []
    for i in range(1, len(path)-1):
        p, prev, nxt = path[i], path[i-1], path[i+1]
        incoming = unit(tuple(prev[j] - p[j]*dot(p, prev) for j in range(3)))
        outgoing = unit(tuple(nxt[j] - p[j]*dot(p, nxt) for j in range(3)))
        angle = acos(max(-1.0, min(1.0, dot(incoming, outgoing))))
        vals.append(pi - angle)
    return tuple(vals)

def signature_base_shape(c: PathCandidate) -> tuple[float, ...]:
    p = arclength_path(c, 256)
    theta = [atan2(sqrt(x*x+y*y), z) for x, y, z in p]
    z = [v[2] for v in p]
    m1, s1 = mean_sd(theta)
    m2, s2 = mean_sd(z)
    sorted_theta = sorted(theta)
    qs = [sorted_theta[int(q*(len(sorted_theta)-1))] for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
    # Direction-insensitive geometric descriptor; deliberately excludes signed area.
    return (trajectory_length(p), m1, s1, m2, s2, *qs)


def signature_holonomy(c: PathCandidate) -> tuple[float, ...]:
    # Fibre phase is circle-valued. Distance is measured with circular distance,
    # not Euclidean distance on its raw angle representation.
    return (c.phase,)


def signature_temporal(c: PathCandidate) -> tuple[float, ...]:
    p = c.temporal_path
    xs, ys, zs = ([v[k] for v in p] for k in range(3))
    # Low-frequency complex DFT coefficients encode the time-parametrized signal.
    # Signed phase is preserved here; time reversal / warping can change it.
    feat = list(dft_coefficients(xs, 8) + dft_coefficients(ys, 8) + dft_coefficients(zs, 8))
    # Add temporal speed statistics and signed projected area rate.
    steps = [geodesic_s2(a, b) for a, b in zip(p[:-1], p[1:])]
    sm, ss = mean_sd(steps)
    feat.extend((sm, ss, c.direction * 1.0))
    return tuple(feat)


def signature_local_transition(c: PathCandidate) -> tuple[float, ...]:
    p = arclength_path(c, 384)
    turns = turning_angles(p)
    ss = sorted(turns)
    qs = [ss[int(q*(len(ss)-1))] for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
    tm, ts = mean_sd(turns)
    # Curvature magnitude distribution is insensitive to path orientation.
    return (tm, ts, *qs)


def circular_distance(a: float, b: float) -> float:
    return abs(wrap_pi(a-b))


def standardize_columns(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    cols = list(zip(*rows))
    params = []
    for col in cols:
        m, s = mean_sd(col)
        params.append((m, s if s > 1e-12 else 1.0))
    return [[(x-m)/s for x, (m, s) in zip(row, params)] for row in rows]


def euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def build_rdm(candidates: Sequence[PathCandidate], observer: str) -> list[list[float]]:
    if observer == "base_shape":
        rows = standardize_columns([signature_base_shape(c) for c in candidates])
        return [[euclidean(a, b) for b in rows] for a in rows]
    if observer == "holonomy":
        vals = [signature_holonomy(c)[0] for c in candidates]
        return [[circular_distance(a, b) for b in vals] for a in vals]
    if observer == "temporal":
        rows = standardize_columns([signature_temporal(c) for c in candidates])
        return [[euclidean(a, b) for b in rows] for a in rows]
    if observer == "local_transition":
        rows = standardize_columns([signature_local_transition(c) for c in candidates])
        return [[euclidean(a, b) for b in rows] for a in rows]
    raise ValueError(f"unknown observer {observer}")


def upper_triangle(rdm: Sequence[Sequence[float]]) -> list[float]:
    return [rdm[i][j] for i in range(len(rdm)) for j in range(i+1, len(rdm))]


def rankdata(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0]*len(values)
    i = 0
    while i < len(order):
        j = i+1
        while j < len(order) and abs(values[order[j]]-values[order[i]]) <= 1e-12:
            j += 1
        rank = 0.5*(i+j-1)+1.0
        for k in range(i, j): ranks[order[k]] = rank
        i = j
    return ranks


def pearson(a: Sequence[float], b: Sequence[float]) -> float:
    ma, mb = mean(a), mean(b)
    da, db = [x-ma for x in a], [x-mb for x in b]
    den = sqrt(sum(x*x for x in da)*sum(y*y for y in db))
    return 0.0 if den < 1e-15 else sum(x*y for x, y in zip(da, db))/den


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    return pearson(rankdata(a), rankdata(b))


def rdms_correlations(rdms: dict[str, list[list[float]]]) -> dict[str, float]:
    names = list(rdms)
    out = {}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            out[f"{a}__{b}"] = spearman(upper_triangle(rdms[a]), upper_triangle(rdms[b]))
    return out


# ---------------------------------------------------------------------------
# Neighborhood, H0 persistence, and graph spectrum
# ---------------------------------------------------------------------------

def knn(rdm: Sequence[Sequence[float]], k: int = 3) -> list[set[int]]:
    return [set(sorted((j for j in range(len(rdm)) if j != i), key=lambda j: rdm[i][j])[:k])
            for i in range(len(rdm))]


def mean_neighbor_jaccard(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]], k: int = 3) -> float:
    na, nb = knn(a, k), knn(b, k)
    vals = []
    for x, y in zip(na, nb):
        union = x | y
        vals.append(1.0 if not union else len(x & y)/len(union))
    return mean(vals)


def prim_mst_edges(rdm: Sequence[Sequence[float]]) -> list[tuple[int, int, float]]:
    n = len(rdm)
    used = {0}
    edges = []
    while len(used) < n:
        best = None
        for i in used:
            for j in range(n):
                if j not in used:
                    cand = (rdm[i][j], i, j)
                    if best is None or cand < best: best = cand
        assert best is not None
        w, i, j = best
        used.add(j); edges.append((i, j, w))
    return edges


def h0_death_curve(rdm: Sequence[Sequence[float]]) -> list[float]:
    # For a finite metric space under the single-linkage / Vietoris-Rips
    # filtration, finite H0 death times are the MST edge weights.
    return sorted(w for _, _, w in prim_mst_edges(rdm))


def betti0_curve(rdm: Sequence[Sequence[float]], thresholds: Sequence[float]) -> list[int]:
    n = len(rdm)
    out = []
    for eps in thresholds:
        parent = list(range(n))
        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for i in range(n):
            for j in range(i+1, n):
                if rdm[i][j] <= eps:
                    a, b = find(i), find(j)
                    if a != b: parent[a] = b
        out.append(len({find(i) for i in range(n)}))
    return out


def jacobi_eigenvalues(matrix: Sequence[Sequence[float]], tol: float = 1e-10,
                       max_iter: int = 100000) -> list[float]:
    a = [list(row) for row in matrix]
    n = len(a)
    for _ in range(max_iter):
        p, q, largest = 0, 1, 0.0
        for i in range(n):
            for j in range(i+1, n):
                if abs(a[i][j]) > largest:
                    p, q, largest = i, j, abs(a[i][j])
        if largest < tol: break
        if abs(a[p][q]) < tol: continue
        tau = (a[q][q]-a[p][p])/(2*a[p][q])
        t = (1.0 if tau >= 0 else -1.0)/(abs(tau)+sqrt(1+tau*tau))
        c = 1/sqrt(1+t*t); s = t*c
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = app-t*apq; a[q][q] = aqq+t*apq
        a[p][q] = a[q][p] = 0.0
        for k in range(n):
            if k not in (p, q):
                akp, akq = a[k][p], a[k][q]
                a[k][p] = a[p][k] = c*akp-s*akq
                a[k][q] = a[q][k] = s*akp+c*akq
    else:
        raise RuntimeError("Jacobi eigensolver did not converge")
    return sorted(a[i][i] for i in range(n))


def graph_laplacian_spectrum(rdm: Sequence[Sequence[float]]) -> list[float]:
    n = len(rdm)
    vals = sorted(upper_triangle(rdm))
    sigma = vals[len(vals)//2] or 1.0
    w = [[0.0]*n for _ in range(n)]
    deg = [0.0]*n
    for i in range(n):
        for j in range(i+1, n):
            wij = exp(-(rdm[i][j]**2)/(2*sigma*sigma))
            w[i][j] = w[j][i] = wij
            deg[i] += wij; deg[j] += wij
    lap = [[0.0]*n for _ in range(n)]
    for i in range(n):
        lap[i][i] = 1.0
        for j in range(n):
            if i != j and deg[i] > 0 and deg[j] > 0:
                lap[i][j] = -w[i][j]/sqrt(deg[i]*deg[j])
    return jacobi_eigenvalues(lap)


# ---------------------------------------------------------------------------
# Controls and analysis
# ---------------------------------------------------------------------------

def permute_rdm(rdm: Sequence[Sequence[float]], permutation: Sequence[int]) -> list[list[float]]:
    return [[rdm[permutation[i]][permutation[j]] for j in range(len(permutation))]
            for i in range(len(permutation))]


def permutation_control(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]],
                        trials: int = 199, seed: int = 20261104) -> dict:
    observed = spearman(upper_triangle(a), upper_triangle(b))
    rng = Random(seed)
    n = len(a)
    null = []
    for _ in range(trials):
        p = list(range(n)); rng.shuffle(p)
        bp = permute_rdm(b, p)
        null.append(spearman(upper_triangle(a), upper_triangle(bp)))
    pvalue = (1 + sum(x >= observed for x in null))/(trials+1)
    return {"observed_spearman": observed, "null_mean": mean(null),
            "null_sd": pstdev(null), "null_q95": sorted(null)[int(0.95*(trials-1))],
            "permutation_trials": trials, "one_sided_p_ge": pvalue,
            "null_correlations": null}



def block_permutation_control(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]],
                               block_size: int = 4, trials: int = 999,
                               seed: int = 20261107) -> dict:
    """Permute whole shape-family blocks while preserving within-family roles.

    Four entries per shape are ordered as forward/uniform, forward/warped,
    reverse/uniform, reverse/warped. Shuffling whole blocks preserves this
    repeated-measures structure and is a stricter null than unrestricted label
    shuffling for the present designed library.
    """
    n = len(a)
    if n != len(b) or n % block_size:
        raise ValueError("RDM sizes must match and divide evenly into blocks")
    observed = spearman(upper_triangle(a), upper_triangle(b))
    rng = Random(seed)
    n_blocks = n//block_size
    null = []
    for _ in range(trials):
        order = list(range(n_blocks)); rng.shuffle(order)
        perm = [order[block]*block_size + slot
                for block in range(n_blocks) for slot in range(block_size)]
        bp = permute_rdm(b, perm)
        null.append(spearman(upper_triangle(a), upper_triangle(bp)))
    pvalue = (1 + sum(x >= observed for x in null))/(trials+1)
    return {"observed_spearman": observed, "null_mean": mean(null),
            "null_sd": pstdev(null), "null_q95": sorted(null)[int(0.95*(trials-1))],
            "permutation_trials": trials, "block_size": block_size,
            "block_count": n_blocks, "one_sided_p_ge": pvalue,
            "null_correlations": null}


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down family-wise adjustment for a small predeclared test set."""
    ordered = sorted(pvalues.items(), key=lambda x: x[1])
    m = len(ordered)
    out: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        adjusted = min(1.0, (m-i)*p)
        running = max(running, adjusted)
        out[name] = running
    return out

def reparameterization_checks(candidates: Sequence[PathCandidate]) -> dict:
    byname = {c.name: c for c in candidates}
    comparisons = []
    for c in candidates:
        if abs(c.warp_gamma-1.0) < 1e-12:
            warped = byname[f"{c.shape_id}_{'fwd' if c.direction>0 else 'rev'}_g{(1.7 if c.direction>0 else 0.62):g}"]
            comparisons.append({
                "shape_id": c.shape_id,
                "direction": c.direction,
                "base_shape_signature_max_abs": max(abs(a-b) for a,b in zip(signature_base_shape(c), signature_base_shape(warped))),
                "holonomy_phase_abs_wrapped": circular_distance(c.phase, warped.phase),
                "temporal_signature_l2": euclidean(signature_temporal(c), signature_temporal(warped)),
                "s3_endpoint_distance": geodesic_s3(c.lift[-1], warped.lift[-1]),
            })
    return {"pairs": comparisons,
            "max_base_shape_signature_error": max(x["base_shape_signature_max_abs"] for x in comparisons),
            "max_holonomy_phase_error": max(x["holonomy_phase_abs_wrapped"] for x in comparisons),
            "max_s3_endpoint_error": max(x["s3_endpoint_distance"] for x in comparisons),
            "min_temporal_signature_change": min(x["temporal_signature_l2"] for x in comparisons)}


def resolution_check(sample_counts: Sequence[int] = (180, 360, 720)) -> dict:
    spec = SHAPES[4]
    rows = []
    reference_phase = None
    reference_area = None
    for count in sample_counts:
        c = build_candidate(spec, 1, 1.0, 640, DEFAULT_Q, count, max(18, count//10))
        if reference_phase is None:
            reference_phase, reference_area = c.phase, c.area
        rows.append({"sample_count": count, "phase": c.phase, "solid_angle": c.area,
                     "phase_half_area_error": abs(c.phase-0.5*c.area),
                     "phase_from_first_error": abs(wrap_pi(c.phase-reference_phase))})
    return {"samples": rows, "final_phase_change": abs(wrap_pi(rows[-1]["phase"]-rows[-2]["phase"]))}


def alias_renaming_check() -> dict:
    default = QuaternionOps(CodonRegistry())
    renamed = QuaternionOps(CodonRegistry(add="plus", sub="minus", mul="times", div="over", sqrt="root"))
    pairs = [((0.2, 0.3, -0.1, 0.9), (0.4, -0.2, 0.7, 0.1)),
             ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0))]
    errors = []
    for a, b in pairs:
        x, y = default.mul(a, b), renamed.mul(a, b)
        errors.append(max(abs(i-j) for i, j in zip(x, y)))
    return {"max_abs_error": max(errors), "passed": max(errors) < 1e-14}


def observer_equivalence_pairs(candidates: Sequence[PathCandidate], rdm: Sequence[Sequence[float]],
                                tolerance: float = 1e-7) -> list[list[str]]:
    n = len(candidates)
    parent = list(range(n))
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(n):
        for j in range(i+1, n):
            if rdm[i][j] <= tolerance:
                a, b = find(i), find(j)
                if a != b: parent[a] = b
    groups: dict[int, list[str]] = {}
    for i, c in enumerate(candidates): groups.setdefault(find(i), []).append(c.name)
    return sorted(groups.values(), key=lambda x: (len(x), x[0]))


def run_analysis() -> dict:
    candidates = build_library()
    observer_names = ("base_shape", "holonomy", "temporal", "local_transition")
    rdms = {name: build_rdm(candidates, name) for name in observer_names}
    correlations = rdms_correlations(rdms)
    neighbor_overlap = {}
    h0_correlations = {}
    betti0 = {}
    spectra = {}
    for name, rdm in rdms.items():
        spectra[name] = graph_laplacian_spectrum(rdm)
        betti0[name] = betti0_curve(rdm, [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5])
    for i, a in enumerate(observer_names):
        for b in observer_names[i+1:]:
            key = f"{a}__{b}"
            neighbor_overlap[key] = mean_neighbor_jaccard(rdms[a], rdms[b], 3)
            h0_correlations[key] = spearman(h0_death_curve(rdms[a]), h0_death_curve(rdms[b]))

    control_pairs = {
        "shape_vs_holonomy": ("base_shape", "holonomy"),
        "shape_vs_local_transition": ("base_shape", "local_transition"),
        "holonomy_vs_temporal": ("holonomy", "temporal"),
    }
    controls = {name: permutation_control(rdms[a], rdms[b], seed=20261104+i)
                for i, (name, (a, b)) in enumerate(control_pairs.items())}
    block_controls = {name: block_permutation_control(rdms[a], rdms[b], seed=20261107+i)
                      for i, (name, (a, b)) in enumerate(control_pairs.items())}
    block_holm = holm_adjust({name: result["one_sided_p_ge"]
                              for name, result in block_controls.items()})
    # Common neighborhoods under a consensus rank aggregation of observer RDMs.
    n = len(candidates)
    consensus = [[0.0]*n for _ in range(n)]
    observer_pair_ranks = {name: rankdata(upper_triangle(rdm)) for name, rdm in rdms.items()}
    for i in range(n):
        for j in range(i+1, n):
            pair_idx = _pair_index(i, j, n)
            value = mean(observer_pair_ranks[name][pair_idx] for name in rdms)
            consensus[i][j] = consensus[j][i] = value
    consensus_nbr = knn(consensus, 3)

    # Geometric identity groups: paths with same base shape, direction, different time warps.
    reparam = reparameterization_checks(candidates)
    group_stats = {}
    for shape in SHAPES:
        idx = [i for i, c in enumerate(candidates) if c.shape_id == shape.shape_id]
        group_stats[shape.shape_id] = {
            "candidate_names": [candidates[i].name for i in idx],
            "base_shape_max_distance": max(rdms["base_shape"][i][j] for i in idx for j in idx),
            "holonomy_max_distance": max(rdms["holonomy"][i][j] for i in idx for j in idx),
            "temporal_max_distance": max(rdms["temporal"][i][j] for i in idx for j in idx),
        }

    return {
        "title": "Build 07 — Cross-observer invariant discovery",
        "scope": "Finite synthetic path library on S2 with horizontal Hopf lifts to S3; not the full Virtual Layer address space.",
        "candidate_count": len(candidates),
        "shape_count": len(SHAPES),
        "candidate_names": [c.name for c in candidates],
        "observers": list(observer_names),
        "rdm_spearman": correlations,
        "mean_3nn_jaccard": neighbor_overlap,
        "h0_persistence_death_rank_correlations": h0_correlations,
        "h0_death_curves": {name: h0_death_curve(rdm) for name, rdm in rdms.items()},
        "h0_interpretation_note": (
            "These compare sorted 0D persistence death-time distributions (MST edge lengths), "
            "not matched merge edges or higher-dimensional topology. High correlation is "
            "distributional similarity only and is not, by itself, evidence of a shared invariant."),
        "betti0_curves_at_thresholds": betti0,
        "normalized_graph_laplacian_eigenvalues": spectra,
        "reparameterization_invariance": reparam,
        "same_geometry_different_time_parameterization": group_stats,
        "permutation_controls": controls,
        "block_permutation_controls": block_controls,
        "block_permutation_holm_adjusted_p": block_holm,
        "alias_renaming": alias_renaming_check(),
        "resolution_convergence": resolution_check(),
        "equivalence_class_tolerances": {
            "base_shape": 0.02,
            "holonomy": 5e-5,
            "temporal": 0.1,
            "local_transition": 0.05,
        },
        "equivalence_classes": {name: observer_equivalence_pairs(
            candidates, rdm, {"base_shape": 0.02, "holonomy": 5e-5,
                              "temporal": 0.1, "local_transition": 0.05}[name])
                                 for name, rdm in rdms.items()},
        "consensus_3nn": {candidates[i].name: [candidates[j].name for j in sorted(consensus_nbr[i], key=lambda j: consensus[i][j])]
                          for i in range(n)},
        "rdms": rdms,
        "candidate_metadata": [{"name": c.name, "shape_id": c.shape_id, "direction": c.direction,
                                "warp_gamma": c.warp_gamma, "phase_rad": c.phase,
                                "solid_angle_sr": c.area, "path_length_rad": trajectory_length(c.path)}
                               for c in candidates],
    }


def _pair_index(i: int, j: int, n: int) -> int:
    if i == j: raise ValueError("diagonal has no upper-triangle index")
    if i > j: i, j = j, i
    # Number of entries before row i + offset within row i.
    return i*n - i*(i+1)//2 + (j-i-1)


def write_csv(path: str, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


if __name__ == "__main__":
    import json
    report = run_analysis()
    with open("reports/build_07_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    names = report["candidate_names"]
    for obs, rdm in report["rdms"].items():
        write_csv(f"data/rdm_{obs}.csv", ["candidate"]+names,
                  [[names[i]]+rdm[i] for i in range(len(names))])
    write_csv("data/candidate_metadata.csv",
              ["name", "shape_id", "direction", "warp_gamma", "phase_rad", "solid_angle_sr", "path_length_rad"],
              [[m[k] for k in ("name", "shape_id", "direction", "warp_gamma", "phase_rad", "solid_angle_sr", "path_length_rad")]
               for m in report["candidate_metadata"]])
    write_csv("data/rdm_correlations.csv", ["observer_pair", "spearman_rho"],
              list(report["rdm_spearman"].items()))
    write_csv("data/neighbor_overlap.csv", ["observer_pair", "mean_3nn_jaccard"],
              list(report["mean_3nn_jaccard"].items()))
    write_csv("data/block_permutation_controls.csv",
              ["observer_pair", "observed_rho", "null_mean", "null_sd", "null_q95", "empirical_p", "holm_adjusted_p"],
              [[name, vals["observed_spearman"], vals["null_mean"], vals["null_sd"],
                vals["null_q95"], vals["one_sided_p_ge"], report["block_permutation_holm_adjusted_p"][name]]
               for name, vals in report["block_permutation_controls"].items()])
    write_csv("data/h0_persistence_deaths.csv", ["observer", "rank", "death_time"],
              [[name, i+1, value] for name, curve in report["h0_death_curves"].items()
               for i, value in enumerate(curve)])
    write_csv("data/graph_laplacian_spectrum.csv", ["observer", "eigenvalue_index", "eigenvalue"],
              [[name, i, value] for name, values in report["normalized_graph_laplacian_eigenvalues"].items()
               for i, value in enumerate(values)])
    write_csv("data/betti0_curves.csv", ["observer", "threshold_index", "threshold", "betti0"],
              [[name, i, threshold, b0] for name, curve in report["betti0_curves_at_thresholds"].items()
               for i, (threshold, b0) in enumerate(zip((0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5), curve))])
    write_csv("data/reparameterization_checks.csv",
              ["shape_id", "direction", "base_shape_signature_max_abs", "holonomy_phase_abs_wrapped", "temporal_signature_l2", "s3_endpoint_distance"],
              [[pair[k] for k in ("shape_id", "direction", "base_shape_signature_max_abs",
                                  "holonomy_phase_abs_wrapped", "temporal_signature_l2", "s3_endpoint_distance")]
               for pair in report["reparameterization_invariance"]["pairs"]])
    key_results = {k: report[k] for k in ("candidate_count", "shape_count", "rdm_spearman",
                    "mean_3nn_jaccard", "block_permutation_controls",
                    "block_permutation_holm_adjusted_p", "reparameterization_invariance",
                    "alias_renaming", "resolution_convergence", "equivalence_classes")}
    with open("reports/key_results.json", "w", encoding="utf-8") as f:
        json.dump(key_results, f, indent=2)
    print(json.dumps({"candidate_count": report["candidate_count"],
                      "rdm_spearman": report["rdm_spearman"],
                      "neighbor_overlap": report["mean_3nn_jaccard"],
                      "h0_correlations": report["h0_persistence_death_rank_correlations"],
                      "reparameterization": report["reparameterization_invariance"],
                      "alias": report["alias_renaming"],
                      "resolution": report["resolution_convergence"]}, indent=2))
