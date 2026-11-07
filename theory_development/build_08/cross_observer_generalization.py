"""Build 08: generalization and perturbation study for observer-dependent geometry.

Standard-library-only research prototype. It generates independent random closed
paths on S^2, constructs four observer-specific representations, evaluates
cross-observer representational geometry, bootstraps over independent path
families, adds feature-noise/projection/bandwidth perturbations, performs exact
Vietoris-Rips H0/H1 persistence on family-level RDMs, and compares independent
cryptographic address substrates as negative controls.

This is a synthetic methods experiment, not a full Virtual Layer implementation
or evidence for a universal geometry of meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256, blake2b, blake2s
from itertools import combinations
from math import acos, atan2, cos, exp, pi, sin, sqrt
from random import Random
from statistics import mean, pstdev
from typing import Callable, Iterable, Sequence
import json

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]

# ------------------------ basic geometry ------------------------

def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x*y for x, y in zip(a, b))


def norm(v: Sequence[float]) -> float:
    return sqrt(dot(v, v))


def unit(v: Sequence[float]) -> Vec3:
    n = norm(v)
    if n < 1e-12:
        raise ValueError("cannot normalize near-zero vector")
    return tuple(x/n for x in v)  # type: ignore[return-value]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def s2_dist(a: Vec3, b: Vec3) -> float:
    return acos(max(-1.0, min(1.0, dot(unit(a), unit(b)))))


def slerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    a, b = unit(a), unit(b)
    d = max(-1.0, min(1.0, dot(a, b)))
    if d < -0.9995:
        raise ValueError("near-antipodal segment; choose a different vertex")
    if d > 0.9995:
        return unit(tuple((1-t)*x+t*y for x, y in zip(a, b)))
    theta = acos(d)
    den = sin(theta)
    return unit(tuple((sin((1-t)*theta)*x + sin(t*theta)*y)/den
                       for x, y in zip(a, b)))


def random_unit(rng: Random) -> Vec3:
    z = rng.uniform(-1.0, 1.0)
    a = rng.uniform(0.0, 2*pi)
    r = sqrt(max(0.0, 1-z*z))
    return (r*cos(a), r*sin(a), z)


def random_closed_polygon(rng: Random, family_index: int,
                          min_petals: int = 1, max_petals: int = 3,
                          arc_subdivisions: int = 7) -> tuple[tuple[Vec3, ...], int]:
    """Generate a random closed path as 1-3 concatenated spherical petals.

    Petals share a root and are concatenated into one closed walk. Independent
    random vertices allow self-approaches and non-star-shaped paths. All edges
    are geodesically interpolated and rejected if nearly antipodal.
    """
    root = random_unit(rng)
    petals = rng.randint(min_petals, max_petals)
    path: list[Vec3] = [root]
    for _ in range(petals):
        count = rng.randint(3, 6)
        vertices = [root]
        for _j in range(count):
            accepted = None
            for _attempt in range(200):
                p = random_unit(rng)
                if dot(vertices[-1], p) > -0.92 and dot(p, root) > -0.92:
                    accepted = p
                    break
            if accepted is None:
                raise RuntimeError("could not sample a non-antipodal polygon edge")
            vertices.append(accepted)
        vertices.append(root)
        for a, b in zip(vertices[:-1], vertices[1:]):
            for k in range(1, arc_subdivisions+1):
                path.append(slerp(a, b, k/arc_subdivisions))
    # The final point is root (within numerical precision).
    path[-1] = path[0]
    if len(path) < 10:
        raise AssertionError("path unexpectedly short")
    return tuple(path), petals


def cumulative_lengths(path: Sequence[Vec3]) -> tuple[list[float], float]:
    c = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        c.append(c[-1] + s2_dist(a, b))
    return c, c[-1]


def resample_arclength(path: Sequence[Vec3], fractions: Sequence[float]) -> tuple[Vec3, ...]:
    c, total = cumulative_lengths(path)
    if total <= 1e-12:
        raise ValueError("zero path length")
    out: list[Vec3] = []
    j = 0
    for f in fractions:
        target = max(0.0, min(1.0, f))*total
        while j < len(c)-2 and c[j+1] < target:
            j += 1
        den = c[j+1]-c[j]
        u = 0.0 if den < 1e-14 else (target-c[j])/den
        out.append(slerp(path[j], path[j+1], u))
    return tuple(out)


def signed_solid_angle(path: Sequence[Vec3]) -> float:
    """Fan-triangulated oriented solid angle, wrapped to (-2pi,2pi]."""
    # Choose a reference point away from the polygon vertices and antipodes.
    center_raw = tuple(sum(p[k] for p in path[:-1]) for k in range(3))
    if norm(center_raw) < 1e-7:
        center = (0.137, -0.421, 0.897)
        center = unit(center)
    else:
        center = unit(center_raw)  # type: ignore[arg-type]
    area = 0.0
    for a, b in zip(path[:-1], path[1:]):
        # Oriented spherical triangle solid angle.
        numerator = dot(center, cross(a, b))
        denominator = 1.0 + dot(center, a) + dot(a, b) + dot(b, center)
        area += 2.0*atan2(numerator, denominator)
    # Choose principal representative; holonomy is circular-valued.
    return (area + 2*pi) % (4*pi) - 2*pi


# ------------------------ quaternion horizontal lift ------------------------

def qmul(a: Quat, b: Quat) -> Quat:
    w,x,y,z = a; W,X,Y,Z = b
    return (w*W-x*X-y*Y-z*Z,
            w*X+x*W+y*Z-z*Y,
            w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W)


def qconj(q: Quat) -> Quat:
    return (q[0], -q[1], -q[2], -q[3])


def qnorm(q: Quat) -> float:
    return sqrt(sum(v*v for v in q))


def qnormalize(q: Quat) -> Quat:
    n = qnorm(q)
    if n < 1e-14:
        raise ValueError("zero quaternion")
    return tuple(v/n for v in q)  # type: ignore[return-value]


def minimal_rotor(a: Vec3, b: Vec3) -> Quat:
    a, b = unit(a), unit(b)
    d = max(-1.0, min(1.0, dot(a,b)))
    if d < -1+1e-10:
        raise ValueError("antipodal step has no unique minimal rotor")
    c = cross(a,b)
    return qnormalize((1+d, c[0], c[1], c[2]))


def horizontal_lift(path: Sequence[Vec3]) -> tuple[Quat, ...]:
    # Initial rotor maps north onto the path's starting point.
    north: Vec3 = (0.0, 0.0, 1.0)
    q0 = minimal_rotor(north, path[0]) if s2_dist(north, path[0]) > 1e-10 else (1.0,0.0,0.0,0.0)
    q = q0
    out = [q]
    for a,b in zip(path[:-1],path[1:]):
        q = qnormalize(qmul(minimal_rotor(a,b), q))
        out.append(q)
    return tuple(out)


def lift_phase(lift: Sequence[Quat]) -> float:
    rel = qmul(qconj(qnormalize(lift[0])), qnormalize(lift[-1]))
    # A closed base path should leave a fibre rotation around k.
    transverse = sqrt(rel[1]*rel[1] + rel[2]*rel[2])
    if transverse > 2e-5:
        raise ArithmeticError(f"lift endpoint not in same Hopf fibre: {transverse}")
    return atan2(rel[3], rel[0])


def wrap_pi(x: float) -> float:
    return (x+pi)%(2*pi)-pi


# ------------------------ codon algebra / normalized descriptions ------------------------

@dataclass(frozen=True)
class Registry:
    add: str = "ad"
    sub: str = "su"
    mul: str = "mx"

    def __post_init__(self) -> None:
        if len({self.add,self.sub,self.mul}) != 3 or any(not x for x in (self.add,self.sub,self.mul)):
            raise ValueError("codon aliases must be unique and nonempty")


def codon_quaternion_product(a: Quat, b: Quat, reg: Registry = Registry(), tree: str = "left") -> Quat:
    """Hamilton product executed via configurable add/sub/multiply codons."""
    mul, add, sub = reg.mul, reg.add, reg.sub
    # Operation dispatch is explicit so alias changes do not alter semantics.
    def op(code: str, x: float, y: float) -> float:
        if code == mul: return x*y
        if code == add: return x+y
        if code == sub: return x-y
        raise ValueError(code)
    w,x,y,z = a; W,X,Y,Z = b
    terms = {
        "w": [(w,W,1),(x,X,-1),(y,Y,-1),(z,Z,-1)],
        "x": [(w,X,1),(x,W,1),(y,Z,1),(z,Y,-1)],
        "y": [(w,Y,1),(x,Z,-1),(y,W,1),(z,X,1)],
        "z": [(w,Z,1),(x,Y,1),(y,X,-1),(z,W,1)],
    }
    out=[]
    for name in ("w","x","y","z"):
        products = [op(mul, aa, bb) for aa,bb,_ in terms[name]]
        signed = [p if sign > 0 else op(sub,0.0,p)
                  for p,(_,_,sign) in zip(products,terms[name])]
        if tree == "left":
            val=signed[0]
            for t in signed[1:]: val=op(add,val,t)
        elif tree == "pairwise":
            val=op(add,op(add,signed[0],signed[1]),op(add,signed[2],signed[3]))
        elif tree == "reverse":
            val=signed[3]
            for t in reversed(signed[:3]): val=op(add,t,val)
        else: raise ValueError("unknown addition tree")
        out.append(val)
    return tuple(out)  # type: ignore[return-value]


def canonical_semantic_ir() -> str:
    # Canonical semantic op graph for Hamilton product, independent of aliases
    # and sum-tree spelling. This is an illustrative normalized IR, not a proof
    # that arbitrary algebraic programs can be canonicalized this way.
    return ("HAMILTON_PRODUCT:v1;terms=(wW,-xX,-yY,-zZ);"
            "(wX,xW,yZ,-zY);(wY,-xZ,yW,zX);(wZ,xY,-yX,zW)")


def path_payload(path: Sequence[Vec3], precision: int = 6) -> bytes:
    rows = [",".join(f"{v:.{precision}f}" for v in p) for p in path[::max(1,len(path)//24)]]
    return ("|".join(rows)).encode("ascii")


def hamming(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        raise ValueError("digest sizes differ")
    return sum((x^y).bit_count() for x,y in zip(a,b))


# ------------------------ observer signatures ------------------------

def mean_sd(xs: Sequence[float]) -> tuple[float,float]:
    return mean(xs), pstdev(xs)


def quantiles(xs: Sequence[float], qs: Sequence[float]) -> tuple[float,...]:
    s=sorted(xs)
    return tuple(s[min(len(s)-1, max(0, int(q*(len(s)-1))))] for q in qs)


def shape_signature(path: Sequence[Vec3]) -> tuple[float,...]:
    p=resample_arclength(path, [i/47 for i in range(48)])
    steps=[s2_dist(a,b) for a,b in zip(p[:-1],p[1:])]
    # Rotation-invariant chord-distance distribution + global shape statistics.
    chords=[s2_dist(p[i],p[j]) for i,j in combinations(range(48),2)]
    sm,ss=mean_sd(steps)
    area=abs(signed_solid_angle(path))
    # Eigenvalue-free rotation-invariant moments of the point cloud.
    centroid_raw=tuple(sum(v[k] for v in p) for k in range(3))
    centroid=unit(centroid_raw) if norm(centroid_raw)>1e-9 else (0.0,0.0,1.0)
    radii=[s2_dist(v,centroid) for v in p]
    return (sum(steps), area, sm, ss, *quantiles(chords,(.05,.15,.3,.5,.7,.85,.95)),
            *quantiles(radii,(.1,.25,.5,.75,.9)))


def local_signature(path: Sequence[Vec3]) -> tuple[float,...]:
    p=resample_arclength(path,[i/95 for i in range(96)])
    turns=[]
    for i in range(1,len(p)-1):
        prev,p0,nxt=p[i-1],p[i],p[i+1]
        vin=unit(tuple(prev[k]-p0[k]*dot(prev,p0) for k in range(3)))
        vout=unit(tuple(nxt[k]-p0[k]*dot(nxt,p0) for k in range(3)))
        turns.append(pi-acos(max(-1.0,min(1.0,dot(vin,vout)))))
    return (*mean_sd(turns), *quantiles(turns,(.05,.1,.25,.5,.75,.9,.95)),
            sum(abs(x) for x in turns)/max(1,len(turns)))


def temporal_signature(path: Sequence[Vec3], gamma: float, reverse: bool=False,
                       samples: int=128, bandwidth: int=8) -> tuple[float,...]:
    base=tuple(reversed(path)) if reverse else path
    fractions=[(i/(samples-1))**gamma for i in range(samples)]
    p=resample_arclength(base,fractions)
    feats=[]
    for axis in range(3):
        vals=[v[axis] for v in p]
        # DFT magnitude avoids arbitrary phase from time origin, but retains
        # speed/reversal effects through temporal ordering and magnitude spectrum.
        for k in range(1,bandwidth+1):
            re=sum(v*cos(2*pi*k*j/samples) for j,v in enumerate(vals))/samples
            im=-sum(v*sin(2*pi*k*j/samples) for j,v in enumerate(vals))/samples
            # Retain phase as well as magnitude: reversal and phase-shifted
            # trajectories should not collapse to the same temporal signature.
            feats.extend((re, im))
    speeds=[s2_dist(a,b)*(samples-1) for a,b in zip(p[:-1],p[1:])]
    feats.extend(mean_sd(speeds))
    feats.extend(quantiles(speeds,(.1,.5,.9)))
    return tuple(feats)


def holonomy_signature(path: Sequence[Vec3]) -> tuple[float,...]:
    lift=horizontal_lift(path)
    phase=lift_phase(lift)
    return (cos(phase),sin(phase))


def standardize(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    cols=list(zip(*rows))
    ms=[]
    for c in cols:
        m,s=mean_sd(c); ms.append((m,s if s>1e-10 else 1.0))
    return [[(x-m)/s for x,(m,s) in zip(row,ms)] for row in rows]


def euclidean(a: Sequence[float],b: Sequence[float]) -> float:
    return sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def make_rdm(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    z=standardize(rows)
    return [[euclidean(a,b) for b in z] for a in z]


def upper(rdm: Sequence[Sequence[float]]) -> list[float]:
    return [rdm[i][j] for i in range(len(rdm)) for j in range(i+1,len(rdm))]


def rankdata(xs: Sequence[float]) -> list[float]:
    order=sorted(range(len(xs)),key=lambda i:xs[i]); ranks=[0.0]*len(xs); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and abs(xs[order[j]]-xs[order[i]])<1e-12: j+=1
        r=(i+j-1)/2+1
        for k in range(i,j): ranks[order[k]]=r
        i=j
    return ranks


def corr(a: Sequence[float],b: Sequence[float]) -> float:
    ma,mb=mean(a),mean(b); da=[x-ma for x in a]; db=[x-mb for x in b]
    den=sqrt(sum(x*x for x in da)*sum(y*y for y in db))
    return sum(x*y for x,y in zip(da,db))/den if den>1e-14 else 0.0


def spearman(a: Sequence[float],b: Sequence[float]) -> float:
    return corr(rankdata(a),rankdata(b))


def knn(rdm: Sequence[Sequence[float]], k: int=5) -> list[set[int]]:
    return [set(sorted((j for j in range(len(rdm)) if j!=i),key=lambda j:rdm[i][j])[:k])
            for i in range(len(rdm))]


def mean_jaccard(a: Sequence[Sequence[float]],b: Sequence[Sequence[float]],k: int=5) -> float:
    aa,bb=knn(a,k),knn(b,k); vals=[]
    for x,y in zip(aa,bb):
        u=x|y; vals.append(len(x&y)/len(u) if u else 1.0)
    return mean(vals)


def noise_project(rows: Sequence[Sequence[float]], keep_fraction: float,
                  noise_sd: float, seed: int, bandwidth: int|None=None) -> list[list[float]]:
    rng=Random(seed); cols=len(rows[0]); keep=max(1,int(cols*keep_fraction))
    chosen=set(rng.sample(range(cols),keep))
    if bandwidth is not None:
        chosen=set(range(min(cols, max(1,bandwidth))))
    out=[]
    for row in rows:
        out.append([row[j]+rng.gauss(0,noise_sd) for j in sorted(chosen)])
    return out


# ------------------------ RDM and resampling statistics ------------------------

def permute_rdm(rdm: Sequence[Sequence[float]], p: Sequence[int]) -> list[list[float]]:
    return [[rdm[p[i]][p[j]] for j in range(len(p))] for i in range(len(p))]


def permutation_test(a: Sequence[Sequence[float]],b: Sequence[Sequence[float]],
                     trials: int=499,seed: int=81008) -> dict:
    observed=spearman(upper(a),upper(b)); rng=Random(seed); null=[]; n=len(a)
    for _ in range(trials):
        p=list(range(n)); rng.shuffle(p)
        null.append(spearman(upper(a),upper(permute_rdm(b,p))))
    pval=(1+sum(x>=observed for x in null))/(trials+1)
    ss=sorted(null)
    return {"observed":observed,"null_mean":mean(null),"null_sd":pstdev(null),
            "null_q95":ss[int(.95*(len(ss)-1))],"p_one_sided":pval,"trials":trials}


def family_bootstrap(a: Sequence[Sequence[float]],b: Sequence[Sequence[float]],
                     trials: int=500,seed: int=81009) -> dict:
    n=len(a); rng=Random(seed); vals=[]
    for _ in range(trials):
        idx=[rng.randrange(n) for _ in range(n)]
        aa=[[a[i][j] for j in idx] for i in idx]
        bb=[[b[i][j] for j in idx] for i in idx]
        vals.append(spearman(upper(aa),upper(bb)))
    ss=sorted(vals)
    return {"mean":mean(vals),"median":ss[len(ss)//2],
            "ci95_low":ss[int(.025*(trials-1))],"ci95_high":ss[int(.975*(trials-1))],
            "trials":trials,"resampling_unit":"independent geometric family"}


# ------------------------ Vietoris-Rips persistence H0 / H1 ------------------------

def _find(parent: list[int], x: int) -> int:
    while parent[x]!=x:
        parent[x]=parent[parent[x]]; x=parent[x]
    return x


def h0_persistence(rdm: Sequence[Sequence[float]]) -> list[tuple[float,float]]:
    n=len(rdm); edges=sorted((rdm[i][j],i,j) for i in range(n) for j in range(i+1,n))
    parent=list(range(n)); intervals=[]
    for d,i,j in edges:
        a,b=_find(parent,i),_find(parent,j)
        if a!=b:
            parent[a]=b; intervals.append((0.0,d))
    return intervals


def vr_h1_persistence(rdm: Sequence[Sequence[float]], max_edge: float|None=None,
                       max_simplices: int=250000) -> dict:
    """Exact Z2 Vietoris-Rips H1 reduction (vertices, edges, triangles).

    Returns finite and right-censored intervals. Complexity grows rapidly with n;
    this build caps the family count and reports the simplex count explicitly.
    """
    n=len(rdm)
    all_edges=[(rdm[i][j],i,j) for i in range(n) for j in range(i+1,n)]
    if max_edge is None:
        ws=sorted(e[0] for e in all_edges); max_edge=ws[int(.72*(len(ws)-1))]
    edges=[e for e in all_edges if e[0] <= max_edge+1e-12]
    simplices: list[tuple[float,int,tuple[int,...]]] = [(0.0,0,(i,)) for i in range(n)]
    edge_lookup: dict[tuple[int,int],float]={(i,j):d for d,i,j in edges}
    for d,i,j in edges: simplices.append((d,1,(i,j)))
    for i,j,k in combinations(range(n),3):
        e1=edge_lookup.get((i,j)); e2=edge_lookup.get((i,k)); e3=edge_lookup.get((j,k))
        if e1 is not None and e2 is not None and e3 is not None:
            simplices.append((max(e1,e2,e3),2,(i,j,k)))
    if len(simplices)>max_simplices:
        raise RuntimeError(f"VR complex too large: {len(simplices)} simplices")
    simplices.sort(key=lambda x:(x[0],x[1],x[2]))
    index={s:i for i,(_,_,s) in enumerate(simplices)}
    reduced: dict[int,int]={}
    births_h1: set[int]=set(); paired_h1: dict[int,float]={}
    for col,(filtration,dim,simplex) in enumerate(simplices):
        if dim==0: boundary=0
        elif dim==1:
            i,j=simplex; boundary=(1<<index[(i,)]) | (1<<index[(j,)])
        else:
            i,j,k=simplex
            boundary=((1<<index[(j,k)]) | (1<<index[(i,k)]) | (1<<index[(i,j)]))
        while boundary:
            low=boundary.bit_length()-1
            prev=reduced.get(low)
            if prev is None: break
            boundary ^= prev
        if boundary==0:
            if dim==1: births_h1.add(col)
        else:
            low=boundary.bit_length()-1
            reduced[low]=boundary
            # A triangle column pivots on an edge row, killing an H1 class.
            if simplices[low][1]==1 and dim==2:
                paired_h1[low]=filtration
    intervals=[]
    for birth_idx in sorted(births_h1):
        b=simplices[birth_idx][0]
        d=paired_h1.get(birth_idx, max_edge)
        intervals.append((b,d,birth_idx not in paired_h1))
    return {"intervals":intervals,"max_edge":max_edge,"simplex_count":len(simplices),
            "vertex_count":n,"edge_count":len(edges),
            "triangle_count":len(simplices)-n-len(edges),
            "censored_count":sum(1 for _b,_d,c in intervals if c)}


def betti_curve(intervals: Sequence[tuple[float,float,bool]], thresholds: Sequence[float]) -> list[int]:
    return [sum(1 for b,d,_c in intervals if b<=t<d) for t in thresholds]


def persistence_summary(rdm: Sequence[Sequence[float]], name: str) -> dict:
    h0=h0_persistence(rdm)
    h1=vr_h1_persistence(rdm)
    finite1=[(b,d) for b,d,c in h1["intervals"] if not c]
    long1=sorted((d-b for b,d in finite1),reverse=True)
    thresholds=[h1["max_edge"]*i/10 for i in range(11)]
    h1_intervals=h1["intervals"]
    positive1=[(b,d) for b,d in finite1 if d-b>1e-9]
    norm_intervals=[(b/h1["max_edge"],d/h1["max_edge"],c) for b,d,c in h1_intervals] if h1["max_edge"]>1e-12 else []
    norm_thresholds=[i/10 for i in range(11)]
    norm_betti=betti_curve(norm_intervals,norm_thresholds)
    life_hist=[0]*10
    for b,d in positive1:
        idx=min(9,int(max(0.0,min(.999999,(d-b)/h1["max_edge"]))*10)) if h1["max_edge"]>1e-12 else 0
        life_hist[idx]+=1
    return {"observer":name,"H0_finite_intervals":len(h0),
            "H0_lifetime_quantiles":quantiles([d-b for b,d in h0],(.1,.5,.9)),
            "H1_finite_intervals_including_zero_bars":len(finite1),
            "H1_positive_intervals":len(positive1),"H1_zero_lifetime_bars":len(finite1)-len(positive1),
            "H1_censored_intervals":h1["censored_count"],
            "H1_top_lifetimes":long1[:10],"H1_lifetime_histogram_normalized":life_hist,
            "H1_betti_curve":betti_curve(h1_intervals,thresholds),
            "H1_betti_curve_normalized":norm_betti,
            "thresholds":thresholds,"simplex_count":h1["simplex_count"],
            "edge_count":h1["edge_count"],"triangle_count":h1["triangle_count"],
            "filtration_max":h1["max_edge"]}


# ------------------------ run study ------------------------

@dataclass(frozen=True)
class Family:
    family_id: str
    path: tuple[Vec3,...]
    petals: int
    signature_shape: tuple[float,...]
    signature_local: tuple[float,...]
    signature_holonomy: tuple[float,...]
    signature_temporal: tuple[float,...]
    payload: bytes


def generate_families(n: int=40,seed: int=81008) -> tuple[Family,...]:
    rng=Random(seed); out=[]
    for i in range(n):
        path,petals=random_closed_polygon(rng,i)
        # temporal profile summarizes multiple parameterizations and directions.
        t1=temporal_signature(path,1.0,False)
        t2=temporal_signature(path,0.68,False)
        t3=temporal_signature(path,1.55,True)
        temporal=tuple(t1) + tuple(t2) + tuple(t3)
        out.append(Family(f"F{i:03d}",path,petals,
                          shape_signature(path),local_signature(path),
                          holonomy_signature(path),temporal,path_payload(path)))
    return tuple(out)


def temporal_low_band_rows(rows: Sequence[Sequence[float]], base_bandwidth: int=8) -> list[list[float]]:
    # Each temporal signature concatenates three observation schedules. Within
    # each schedule, retain low-frequency real/imag pairs for x,y,z plus speed
    # statistics. This is a genuine bandwidth restriction, not a prefix slice.
    one_block = 3*(2*base_bandwidth) + 5
    keep_local=[]
    for axis in range(3):
        offset=axis*2*base_bandwidth
        for k in range(3):
            keep_local.extend((offset+2*k,offset+2*k+1))
    keep_local.extend(range(6*base_bandwidth, one_block))
    indices=[]
    for block in range(3):
        indices.extend(block*one_block+i for i in keep_local)
    return [[row[i] for i in indices] for row in rows]


def make_observer_rdms(families: Sequence[Family],seed: int=81010) -> dict[str,list[list[float]]]:
    base={
        "shape_clean":[f.signature_shape for f in families],
        "local_clean":[f.signature_local for f in families],
        "holonomy_clean":[f.signature_holonomy for f in families],
        "temporal_clean":[f.signature_temporal for f in families],
    }
    out={name:make_rdm(rows) for name,rows in base.items()}
    # Degraded observers: fixed channel projections plus observation noise.
    out["shape_noisy_drop"] = make_rdm(noise_project(standardize(base["shape_clean"]),.62,.20,seed+1))
    out["local_jittered"] = make_rdm(noise_project(standardize(base["local_clean"]),.70,.12,seed+2))
    out["holonomy_noisy"] = make_rdm(noise_project(standardize(base["holonomy_clean"]),1.0,.18,seed+3))
    low=temporal_low_band_rows(standardize(base["temporal_clean"]))
    out["temporal_low_band"] = make_rdm(noise_project(low,1.0,.10,seed+4))
    return out


def robustness_sweep(families: Sequence[Family], seed: int=81020,
                     repeats: int=8) -> dict:
    base={
        "shape":[f.signature_shape for f in families],
        "local":[f.signature_local for f in families],
        "holonomy":[f.signature_holonomy for f in families],
        "temporal":[f.signature_temporal for f in families],
    }
    report={}
    for oi,(name,rows) in enumerate(base.items()):
        z=standardize(rows); clean=make_rdm(rows); levels=[]
        for keep in (1.0,.75,.5,.35):
            for sigma in (0.0,.05,.10,.20,.40):
                rho=[]; overlap=[]
                for rep in range(repeats):
                    noisy=noise_project(z,keep,sigma,seed+oi*1000+rep*37+int(keep*100))
                    rdm=make_rdm(noisy)
                    rho.append(spearman(upper(clean),upper(rdm)))
                    # Avoid computing kNN similarity from matrix diagonal ties incorrectly.
                    overlap.append(mean_jaccard(clean,rdm,5))
                levels.append({"keep_fraction":keep,"noise_sd_in_z_units":sigma,
                               "spearman_mean":mean(rho),"spearman_sd":pstdev(rho),
                               "mean_5nn_jaccard":mean(overlap),"repeats":repeats})
        report[name]=levels
    return report


def substrate_rdms(families: Sequence[Family]) -> dict[str,list[list[float]]]:
    digests={"sha256":[],"blake2b_256":[],"blake2s_256":[]}
    for f in families:
        digests["sha256"].append(sha256(f.payload).digest())
        digests["blake2b_256"].append(blake2b(f.payload,digest_size=32).digest())
        digests["blake2s_256"].append(blake2s(f.payload,digest_size=32).digest())
    return {name:[[hamming(a,b)/256 for b in values] for a in values]
            for name,values in digests.items()}


def holm_adjust(pvalues: dict[str,float]) -> dict[str,float]:
    ordered=sorted(pvalues.items(),key=lambda kv:kv[1]); m=len(ordered)
    adjusted={}; running=0.0
    for i,(name,p) in enumerate(ordered):
        running=max(running,min(1.0,(m-i)*p))
        adjusted[name]=running
    return adjusted


def build_report(n_families: int=40,seed: int=81008,bootstrap_trials: int=400,
                 permutation_trials: int=399) -> tuple[dict,dict[str,list[list[float]]],tuple[Family,...]]:
    fam=generate_families(n_families,seed)
    rdms=make_observer_rdms(fam,seed+2)
    pairs=[("shape_clean","local_clean"),("shape_clean","holonomy_clean"),
           ("shape_clean","temporal_clean"),("holonomy_clean","temporal_clean"),
           ("local_clean","temporal_clean"),("shape_clean","shape_noisy_drop"),
           ("local_clean","local_jittered"),("holonomy_clean","holonomy_noisy"),
           ("temporal_clean","temporal_low_band")]
    pair_results={}
    for i,(a,b) in enumerate(pairs):
        pair_results[f"{a}__{b}"]={
            "spearman":spearman(upper(rdms[a]),upper(rdms[b])),
            "mean_5nn_jaccard":mean_jaccard(rdms[a],rdms[b],5),
            "bootstrap":family_bootstrap(rdms[a],rdms[b],bootstrap_trials,seed+100+i),
            "permutation":permutation_test(rdms[a],rdms[b],permutation_trials,seed+300+i),
        }
    primary_names=["shape_clean__local_clean","shape_clean__holonomy_clean",
                   "shape_clean__temporal_clean","holonomy_clean__temporal_clean",
                   "local_clean__temporal_clean"]
    primary_p={name:pair_results[name]["permutation"]["p_one_sided"] for name in primary_names}
    primary_holm=holm_adjust(primary_p)
    for name,p_adj in primary_holm.items():
        pair_results[name]["permutation"]["holm_adjusted_p_primary_family"]=p_adj
    # address substrate controls versus geometry and one another.
    hashes=substrate_rdms(fam)
    substrate_corr={}
    hash_names=list(hashes)
    for i,a in enumerate(hash_names):
        for b in hash_names[i+1:]:
            substrate_corr[f"{a}__{b}"]=spearman(upper(hashes[a]),upper(hashes[b]))
        substrate_corr[f"{a}__shape"]=spearman(upper(hashes[a]),upper(rdms["shape_clean"]))
        substrate_corr[f"{a}__local"]=spearman(upper(hashes[a]),upper(rdms["local_clean"]))
    # reparameterization invariance: compare canonical path geometry across time warps.
    warp_checks=[]
    for f in fam[:min(12,len(fam))]:
        uniform=resample_arclength(f.path,[i/127 for i in range(128)])
        warped=resample_arclength(f.path,[(i/127)**1.65 for i in range(128)])
        reversed_uniform=resample_arclength(tuple(reversed(f.path)),[i/127 for i in range(128)])
        speed=lambda p: [s2_dist(a,b) for a,b in zip(p[:-1],p[1:])]
        warp_checks.append({"family":f.family_id,
                            "temporal_uniform_vs_warped_l2":euclidean(temporal_signature(f.path,1.0),temporal_signature(f.path,1.65)),
                            "shape_original_vs_reversed_l2":euclidean(shape_signature(f.path),shape_signature(tuple(reversed(f.path)))),
                            "mean_step_uniform":mean(speed(uniform)),"mean_step_warped":mean(speed(warped)),
                            "reversed_path_endpoint_error":s2_dist(reversed_uniform[0],f.path[-1])})
    # persistence for a selected set of clean and perturbed observer geometries.
    persistence={}
    for name in ("shape_clean","local_clean","holonomy_clean","temporal_clean","shape_noisy_drop","temporal_low_band"):
        persistence[name]=persistence_summary(rdms[name],name)
    topo_corr={}
    pnames=list(persistence)
    for i,a in enumerate(pnames):
        for b in pnames[i+1:]:
            topo_corr[f"{a}__{b}"]=corr(persistence[a]["H1_betti_curve_normalized"],
                                        persistence[b]["H1_betti_curve_normalized"])
    robustness=robustness_sweep(fam,seed+900,repeats=6)
    # Codonic decomposition and alias controls.
    q1=(0.41,-0.12,0.53,0.72); q2=(-0.16,0.63,0.24,0.71)
    left=codon_quaternion_product(q1,q2,Registry(),"left")
    alt=codon_quaternion_product(q1,q2,Registry(),"pairwise")
    revtree=codon_quaternion_product(q1,q2,Registry(),"reverse")
    aliases=codon_quaternion_product(q1,q2,Registry(add="plus",sub="minus",mul="times"),"pairwise")
    identity_left=codon_quaternion_product(q1,(1.0,0.0,0.0,0.0),Registry())
    identity_right=codon_quaternion_product((1.0,0.0,0.0,0.0),q2,Registry())
    codon_checks={"pairwise_abs_error":max(abs(a-b) for a,b in zip(left,alt)),
                  "reverse_tree_abs_error":max(abs(a-b) for a,b in zip(left,revtree)),
                  "alias_renaming_abs_error":max(abs(a-b) for a,b in zip(left,aliases)),
                  "left_identity_abs_error":max(abs(a-b) for a,b in zip(q1,identity_left)),
                  "right_identity_abs_error":max(abs(a-b) for a,b in zip(q2,identity_right)),
                  "canonical_ir_hash_sha256":sha256(canonical_semantic_ir().encode()).hexdigest(),
                  "raw_alias_spellings_hash_equal":sha256(b"ad,su,mx").digest()==sha256(b"plus,minus,times").digest()}
    report={
        "build":"08","seed":seed,"family_count":n_families,
        "path_generation":{"description":"random closed spherical polygons formed by 1-3 concatenated petals; geodesic edges; independent family sampling",
                            "family_ids":[f.family_id for f in fam],
                            "path_vertex_count_min":min(len(f.path) for f in fam),
                            "path_vertex_count_max":max(len(f.path) for f in fam),
                            "petal_count_distribution":{str(k):sum(1 for f in fam if f.petals==k) for k in (1,2,3)},
                            "all_closed":all(s2_dist(f.path[0],f.path[-1])<1e-10 for f in fam)},
        "observer_pairs":pair_results,
        "primary_cross_observer_tests":{"predeclared_pairs":primary_names,
                                         "holm_adjusted_p":primary_holm,
                                         "permutation_trials":permutation_trials},
        "address_substrate_controls":{"spearman_correlations":substrate_corr,
                                      "interpretation":"cryptographic digest Hamming geometry is a substrate-specific control, not a semantic metric"},
        "time_warp_checks":warp_checks,
        "persistence":persistence,
        "persistence_profile_correlations":topo_corr,
        "observer_robustness_sweep":robustness,
        "codonic_equivalence":codon_checks,
        "limitations":["Synthetic paths and synthetic observers only.",
                       "Bootstrap resamples independent path families; pairwise RDM entries are not treated as independent observations.",
                       "Permutation tests are exploratory and do not establish a universal invariant.",
                       "Vietoris-Rips persistence is computed exactly over F2 through H1 for finite family-level RDMs; H2 is not included.",
                       "The normalized codon IR example is specific to the Hamilton product; arbitrary program equivalence is undecidable in general.",
                       "SHA-256/BLAKE2 address controls demonstrate digest-substrate dependence, not a comparison of the user's full current VL implementation."]}
    return report,rdms,fam


def main(out_dir: str=".") -> dict:
    report,rdms,fam=build_report()
    import os,csv
    os.makedirs(out_dir,exist_ok=True)
    data=os.path.join(out_dir,"data"); reports=os.path.join(out_dir,"reports")
    os.makedirs(data,exist_ok=True); os.makedirs(reports,exist_ok=True)
    with open(os.path.join(reports,"build_08_report.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,indent=2)
    with open(os.path.join(data,"family_manifest.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["family_id","vertex_count","petals","path_length","signed_solid_angle","holonomy_phase","payload_sha256"])
        for x in fam:
            lift=horizontal_lift(x.path); phase=lift_phase(lift)
            w.writerow([x.family_id,len(x.path),x.petals,sum(s2_dist(a,b) for a,b in zip(x.path[:-1],x.path[1:])),
                        signed_solid_angle(x.path),phase,sha256(x.payload).hexdigest()])
    for name,rdm in rdms.items():
        with open(os.path.join(data,f"rdm_{name}.csv"),"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["family_id"]+[x.family_id for x in fam])
            for x,row in zip(fam,rdm): w.writerow([x.family_id]+row)
    # Persist cryptographic substrate RDMs as separate controls.
    for name,rdm in substrate_rdms(fam).items():
        with open(os.path.join(data,f"rdm_address_{name}.csv"),"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["family_id"]+[x.family_id for x in fam])
            for x,row in zip(fam,rdm): w.writerow([x.family_id]+row)
    with open(os.path.join(data,"observer_pair_summary.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["observer_pair","spearman","knn5_jaccard","bootstrap_ci95_low","bootstrap_ci95_high","permutation_p","holm_adjusted_p_primary"])
        for name,v in report["observer_pairs"].items():
            b=v["bootstrap"]; p=v["permutation"]
            w.writerow([name,v["spearman"],v["mean_5nn_jaccard"],b["ci95_low"],b["ci95_high"],p["p_one_sided"],p.get("holm_adjusted_p_primary_family","")])
    with open(os.path.join(data,"observer_robustness_sweep.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["observer","keep_fraction","noise_sd_z","spearman_mean","spearman_sd","knn5_jaccard_mean","repeats"])
        for observer,levels in report["observer_robustness_sweep"].items():
            for x in levels: w.writerow([observer,x["keep_fraction"],x["noise_sd_in_z_units"],x["spearman_mean"],x["spearman_sd"],x["mean_5nn_jaccard"],x["repeats"]])
    with open(os.path.join(data,"persistence_summary.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["observer","H0_intervals","H1_positive","H1_zero_lifetime","H1_censored","top_lifetime_1","top_lifetime_2","top_lifetime_3"])
        for observer,x in report["persistence"].items():
            top=x["H1_top_lifetimes"]+[""]*3
            w.writerow([observer,x["H0_finite_intervals"],x["H1_positive_intervals"],x["H1_zero_lifetime_bars"],x["H1_censored_intervals"],*top[:3]])
    with open(os.path.join(data,"address_substrate_correlations.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["comparison","spearman"])
        for comp,value in report["address_substrate_controls"]["spearman_correlations"].items(): w.writerow([comp,value])
    with open(os.path.join(data,"persistence_profile_correlations.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["observer_pair","normalized_H1_betti_curve_correlation"])
        for comp,value in report["persistence_profile_correlations"].items(): w.writerow([comp,value])
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--out",default=".")
    args=p.parse_args(); r=main(args.out)
    print(json.dumps({"build":r["build"],"families":r["family_count"],
                      "pairs":{k:round(v["spearman"],3) for k,v in r["observer_pairs"].items()},
                      "persistence":{k:(v["H1_positive_intervals"],v["H1_censored_intervals"]) for k,v in r["persistence"].items()}},indent=2))
