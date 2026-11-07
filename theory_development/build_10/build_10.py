"""Build 10: heterogeneous dynamical systems and active probing.

Standard-library-only research benchmark. Synthetic acoustic-like modal networks
are compared with independently parameterized two-degree-of-freedom mechanical
systems. The experiment does not model human emotion or biological perception.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from math import cos, exp, log, pi, sin, sqrt, tanh
from hashlib import sha256
from random import Random
from statistics import mean, median
from typing import Callable, Iterable, Sequence
import csv
import json
from pathlib import Path

FS = 256.0
N = 512
DURATION = N / FS
EPS = 1e-12
PROBE_NAMES = ("impulse", "step", "chirp", "multisine", "amplitude_staircase")
FEATURE_NAMES = (
    "log_gain", "crest", "zero_crossing", "spectral_centroid",
    "spectral_bandwidth", "spectral_flatness", "peak_frequency",
    "band_3_10", "band_10_20", "band_20_40", "band_40_64",
    "decay_slope", "late_early_ratio",
    *tuple(f"log_spectral_bin_{i:02d}" for i in range(16)),
    "gain_block_span", "gain_block_slope", "spectral_peak_count", "spectral_notch_depth",
)
ACTIVE_FEATURE_INDICES = tuple(range(13)) + (13,17,21,25,29,30,31,32)


@dataclass(frozen=True)
class CodonRegistry:
    load: str = "ld"
    add: str = "ad"
    sub: str = "su"
    mul: str = "mx"
    div: str = "dv"
    power: str = "pw"
    store: str = "st"

    def __post_init__(self) -> None:
        values = (self.load, self.add, self.sub, self.mul, self.div, self.power, self.store)
        if any(not isinstance(v, str) or not v for v in values) or len(set(values)) != len(values):
            raise ValueError("codon aliases must be unique nonempty strings")


def execute_codon(code: str, *args: float, registry: CodonRegistry = CodonRegistry()) -> float:
    if code in (registry.load, registry.store):
        if len(args) != 1:
            raise ValueError(f"{code} expects one operand")
        return float(args[0])
    if code == registry.power:
        if len(args) != 2 or int(args[1]) != args[1]:
            raise ValueError("power expects base and integer exponent")
        return float(args[0] ** int(args[1]))
    if len(args) != 2:
        raise ValueError(f"{code} expects two operands")
    a, b = args
    if code == registry.add: return a + b
    if code == registry.sub: return a - b
    if code == registry.mul: return a * b
    if code == registry.div:
        if abs(b) < 1e-15: raise ZeroDivisionError("codon division by near-zero")
        return a / b
    raise ValueError(f"unknown codon: {code}")


def fft(values: Sequence[complex]) -> list[complex]:
    n = len(values)
    if n == 0 or n & (n - 1):
        raise ValueError("FFT length must be a positive power of two")
    a = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        ang = -2.0 * pi / length
        wlen = complex(cos(ang), sin(ang))
        half = length // 2
        for start in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(start, start + half):
                u, v = a[k], a[k + half] * w
                a[k], a[k + half] = u + v, u - v
                w *= wlen
        length <<= 1
    return a


def rms(x: Sequence[float]) -> float:
    return sqrt(sum(v*v for v in x) / max(1, len(x)))


def stddev(x: Sequence[float]) -> float:
    if not x: return 0.0
    m = mean(x)
    return sqrt(sum((v-m)**2 for v in x) / len(x))


def solve2(a: tuple[tuple[float,float],tuple[float,float]], b: tuple[float,float]) -> tuple[float,float]:
    det = a[0][0]*a[1][1] - a[0][1]*a[1][0]
    if abs(det) < 1e-12:
        raise ValueError("singular 2x2 mass matrix")
    return ((b[0]*a[1][1]-a[0][1]*b[1])/det,
            (a[0][0]*b[1]-b[0]*a[1][0])/det)


def probe_signals(fs: float = FS, n: int = N) -> dict[str, list[float]]:
    if n & (n-1): raise ValueError("probe length must be power of two")
    dt = 1.0/fs
    impulse = [0.0]*n; impulse[0] = 1.0
    step = [0.08]*n
    chirp: list[float] = []
    multi: list[float] = []
    staircase: list[float] = []
    for i in range(n):
        t = i*dt
        # A tapered sweep; instantaneous frequency rises from 3 to 55 Hz.
        f = 3.0 + 52.0*(i/max(1,n-1))
        phase = 2*pi*(3.0*t + 0.5*(52.0/DURATION)*t*t)
        env = 0.5 - 0.5*cos(2*pi*i/max(1,n-1))
        chirp.append(0.12*env*sin(phase))
        multi.append(0.08*(sin(2*pi*6*t+0.1)+sin(2*pi*13*t+0.7)+sin(2*pi*27*t+1.4)+sin(2*pi*43*t+2.1))/2.0)
        # Four alternating-amplitude blocks at 17 Hz.
        block = min(3, (4*i)//n)
        amp = (0.08, 0.8, 0.12, 1.2)[block]
        staircase.append(amp*sin(2*pi*17*t))
    return {"impulse": impulse, "step": step, "chirp": chirp,
            "multisine": multi, "amplitude_staircase": staircase}


@dataclass(frozen=True)
class AcousticNetwork:
    modes: tuple[tuple[float,float,float,float], ...]  # Hz, zeta, residue, input weight
    coupling: tuple[tuple[float,...], ...]
    notch_hz: float | None
    compression: float
    sensor_gain: float
    sensor_delay: int


@dataclass(frozen=True)
class Mechanical2DOF:
    mass: tuple[tuple[float,float],tuple[float,float]]
    damping: tuple[tuple[float,float],tuple[float,float]]
    stiffness: tuple[tuple[float,float],tuple[float,float]]
    force_vector: tuple[float,float]
    sensor_vector: tuple[float,float]
    cubic: tuple[float,float,float]  # beta1, beta2, beta_coupling
    sensor_gain: float
    sensor_delay: int


def generate_acoustic(rng: Random, class_id: int | None = None) -> AcousticNetwork:
    # Independent draws: not paired with mechanical natural frequencies.
    modes_n = rng.choice((2,3)) if class_id != 1 else 3
    if class_id == 0: modes_n = 2
    if class_id == 2: modes_n = 2
    if class_id == 3: modes_n = rng.choice((2,3))
    freqs: list[float] = []
    for _ in range(modes_n):
        candidate = rng.uniform(5.0, 53.0)
        for _try in range(20):
            if all(abs(candidate-v)>4.0 for v in freqs): break
            candidate = rng.uniform(5.0, 53.0)
        freqs.append(candidate)
    modes = []
    for i, f in enumerate(freqs):
        z = rng.uniform(0.025,0.19)
        residue = rng.uniform(0.45,1.15) * (-1.0 if (class_id == 2 and i == 1) else rng.choice((-1.0,1.0)))
        input_w = rng.uniform(0.55,1.2)
        modes.append((f,z,residue,input_w))
    # Weak directed cross-feed between modal states; keep row sums bounded.
    coupling = [[0.0]*modes_n for _ in range(modes_n)]
    for i in range(modes_n):
        for j in range(modes_n):
            if i != j: coupling[i][j] = rng.uniform(-0.035,0.035)
    notch = rng.uniform(8.0,48.0) if class_id == 2 else (rng.uniform(8,48) if rng.random()<0.18 else None)
    compression = rng.uniform(0.018,0.045) if class_id == 3 else rng.uniform(0.0,0.003)
    gain = rng.uniform(0.7,1.35)
    delay = rng.choice((0,0,0,1,2))
    return AcousticNetwork(tuple(modes), tuple(tuple(r) for r in coupling), notch, compression, gain, delay)


def generate_mechanical(rng: Random, class_id: int | None = None) -> Mechanical2DOF:
    m1, m2 = rng.uniform(0.65,1.55), rng.uniform(0.65,1.55)
    m12 = rng.uniform(-0.07,0.07)*sqrt(m1*m2)
    M = ((m1,m12),(m12,m2))
    f1, f2 = rng.uniform(5.0,24.0), rng.uniform(19.0,54.0)
    k1, k2 = m1*(2*pi*f1)**2, m2*(2*pi*f2)**2
    kc = rng.uniform(0.035,0.19)*sqrt(k1*k2)
    K = ((k1+kc,-kc),(-kc,k2+kc))
    if class_id == 0:
        alpha, beta = rng.uniform(0.015,0.07), rng.uniform(0.000002,0.000018)
        C = ((alpha*M[0][0]+beta*K[0][0], alpha*M[0][1]+beta*K[0][1]),
             (alpha*M[1][0]+beta*K[1][0], alpha*M[1][1]+beta*K[1][1]))
    else:
        c1, c2 = rng.uniform(0.25,2.8), rng.uniform(0.25,3.2)
        c12 = rng.uniform(-0.22,0.22)*sqrt(c1*c2)
        C = ((c1,c12),(c12,c2))
    if class_id == 2:
        sensor = (1.0, rng.uniform(-1.35,-0.5))  # cancellation / antiresonance-prone readout
    else:
        sensor = (1.0, rng.uniform(-0.25,0.8))
    force = (1.0, rng.uniform(-0.15,0.25))
    if class_id == 3:
        cubic = (rng.uniform(0.18,0.55), rng.uniform(0.16,0.52), rng.uniform(0.08,0.32))
    else:
        cubic = (rng.uniform(0.0,0.002), rng.uniform(0.0,0.002), rng.uniform(0.0,0.001))
    gain = rng.uniform(0.75,1.3)
    delay = rng.choice((0,0,0,1,2))
    return Mechanical2DOF(M,C,K,force,sensor,cubic,gain,delay)


def apply_delay_gain(y: Sequence[float], gain: float, delay: int) -> list[float]:
    out = [0.0]*len(y)
    for i,v in enumerate(y):
        j=i+delay
        if j<len(y): out[j]=gain*v
    return out


def simulate_acoustic(p: AcousticNetwork, x: Sequence[float], fs: float=FS,
                      registry: CodonRegistry=CodonRegistry()) -> list[float]:
    nm=len(p.modes)
    y1=[0.0]*nm; y2=[0.0]*nm
    raw=[]
    # Optional stable notch biquad, applied after modal superposition.
    if p.notch_hz is not None:
        w=2*pi*p.notch_hz/fs; r=0.965
        nb0=1.0; nb1=-2*cos(w); nb2=1.0
        na1=-2*r*cos(w); na2=r*r
        # normalize notch numerator/denominator DC ratio to unity
        den0=1.0+na1+na2
        num0=nb0+nb1+nb2
        scale=den0/num0 if abs(num0)>1e-8 else 1.0
        nb0*=scale; nb1*=scale; nb2*=scale
        xn1=xn2=yn1=yn2=0.0
    for sample in x:
        out_modes=[]
        for i,(f,z,residue,input_w) in enumerate(p.modes):
            wn=2*pi*f
            rad=exp(-z*wn/fs)
            wd=wn*sqrt(max(1e-8,1-z*z))
            a1=2*rad*cos(wd/fs); a2=-rad*rad
            drive=input_w*sample
            for j in range(nm):
                drive += p.coupling[i][j]*y1[j]
            b0=1.0-a1-a2
            yy=execute_codon(registry.add,
                    execute_codon(registry.mul,b0,drive,registry=registry),
                    execute_codon(registry.mul,a1,y1[i],registry=registry),registry=registry)
            yy=execute_codon(registry.add,yy,
                    execute_codon(registry.mul,a2,y2[i],registry=registry),registry=registry)
            out_modes.append(yy)
        y2=y1[:]; y1=out_modes[:]
        raw.append(sum(p.modes[i][2]*out_modes[i] for i in range(nm)))
    if p.notch_hz is not None:
        filtered=[]
        for v in raw:
            yy=nb0*v + nb1*xn1 + nb2*xn2 - na1*yn1 - na2*yn2
            filtered.append(yy)
            xn2,xn1=xn1,v; yn2,yn1=yn1,yy
        raw=filtered
    if p.compression>0:
        raw=[tanh(v*p.compression*35.0)/(p.compression*35.0) for v in raw]
    return apply_delay_gain(raw,p.sensor_gain,p.sensor_delay)


def simulate_mechanical(p: Mechanical2DOF, force: Sequence[float], fs: float=FS,
                        substeps: int=4, registry: CodonRegistry=CodonRegistry()) -> list[float]:
    M,C,K=p.mass,p.damping,p.stiffness
    q1=q2=v1=v2=0.0
    dt=1.0/fs/substeps
    out=[]
    def deriv(q1v: float,q2v: float,v1v: float,v2v: float,ff: float) -> tuple[float,float,float,float]:
        d1=C[0][0]*v1v+C[0][1]*v2v+K[0][0]*q1v+K[0][1]*q2v
        d2=C[1][0]*v1v+C[1][1]*v2v+K[1][0]*q1v+K[1][1]*q2v
        qref=1.0e-4
        kref=max(K[0][0],K[1][1],1.0)
        beta_scale=kref/(qref*qref)
        b1=beta_scale*(p.cubic[0]*q1v**3+p.cubic[2]*(q1v-q2v)**3)
        b2=beta_scale*(p.cubic[1]*q2v**3-p.cubic[2]*(q1v-q2v)**3)
        f1=ff*p.force_vector[0]-d1-b1
        f2=ff*p.force_vector[1]-d2-b2
        a1,a2=solve2(M,(f1,f2))
        return v1v,v2v,a1,a2
    for ff in force:
        for _ in range(substeps):
            k1=deriv(q1,q2,v1,v2,ff)
            k2=deriv(q1+0.5*dt*k1[0],q2+0.5*dt*k1[1],v1+0.5*dt*k1[2],v2+0.5*dt*k1[3],ff)
            k3=deriv(q1+0.5*dt*k2[0],q2+0.5*dt*k2[1],v1+0.5*dt*k2[2],v2+0.5*dt*k2[3],ff)
            k4=deriv(q1+dt*k3[0],q2+dt*k3[1],v1+dt*k3[2],v2+dt*k3[3],ff)
            q1 += dt*(k1[0]+2*k2[0]+2*k3[0]+k4[0])/6.0
            q2 += dt*(k1[1]+2*k2[1]+2*k3[1]+k4[1])/6.0
            v1 += dt*(k1[2]+2*k2[2]+2*k3[2]+k4[2])/6.0
            v2 += dt*(k1[3]+2*k2[3]+2*k3[3]+k4[3])/6.0
        out.append(p.sensor_vector[0]*q1+p.sensor_vector[1]*q2)
    return apply_delay_gain(out,p.sensor_gain,p.sensor_delay)


def spectral_features(y: Sequence[float], fs: float) -> tuple[float,float,float,float,list[float],list[float],float,float]:
    n=len(y)
    spec=fft([complex(v,0) for v in y])[:n//2+1]
    mags=[abs(v) for v in spec]
    freqs=[i*fs/n for i in range(len(mags))]
    total=sum(mags)+EPS
    centroid=sum(f*m for f,m in zip(freqs,mags))/total
    bandwidth=sqrt(sum(((f-centroid)**2)*m for f,m in zip(freqs,mags))/total)
    positive=[m for f,m in zip(freqs,mags) if 2.0<=f<=64.0]
    flat=exp(mean(log(m+EPS) for m in positive))/(mean(positive)+EPS) if positive else 0.0
    peak_idx=max(range(1,len(mags)),key=lambda i:mags[i])
    peakf=freqs[peak_idx]
    bins=[]
    for lo,hi in ((3,10),(10,20),(20,40),(40,64)):
        bins.append(sum(m*m for f,m in zip(freqs,mags) if lo<=f<hi)/(sum(m*m for f,m in zip(freqs,mags) if 2<=f<=64)+EPS))
    fine_bins=[]
    total_energy=sum(m*m for f,m in zip(freqs,mags) if 2<=f<66)+EPS
    for bi in range(16):
        lo=2.0+4.0*bi; hi=lo+4.0
        energy=sum(m*m for f,m in zip(freqs,mags) if lo<=f<hi)
        fine_bins.append(log(energy/total_energy+EPS))
    peaks=0
    for i in range(2,len(mags)-2):
        if 2.0<=freqs[i]<=64.0 and mags[i]>mags[i-1] and mags[i]>=mags[i+1] and mags[i]>max(mags)*0.11:
            peaks+=1
    logfine=sorted(fine_bins)
    notch_depth=(median(logfine)-min(logfine)) if logfine else 0.0
    return centroid/64.0,bandwidth/64.0,flat,peakf/64.0,bins,fine_bins,float(peaks),notch_depth


def extract_features(x: Sequence[float], y: Sequence[float], fs: float=FS) -> list[float]:
    if len(x)!=len(y) or not y: raise ValueError("input/output length mismatch or empty trace")
    rx,ry=rms(x),rms(y)
    log_gain=log((ry+EPS)/(rx+EPS))
    crest=max(abs(v) for v in y)/(ry+EPS)
    zc=sum(1 for a,b in zip(y,y[1:]) if a*b<0)/max(1,len(y)-1)
    centroid,bw,flat,peakf,bins,fine_bins,peak_count,notch_depth=spectral_features(y,fs)
    # Windowed envelope decay descriptor; estimate linear slope of log RMS.
    win=max(8,len(y)//16)
    env=[rms(y[i:i+win]) for i in range(0,len(y)-win+1,win)]
    logs=[log(v+EPS) for v in env]
    if len(logs)>1:
        xm=mean(range(len(logs))); ym=mean(logs)
        denom=sum((i-xm)**2 for i in range(len(logs)))+EPS
        slope=sum((i-xm)*(v-ym) for i,v in enumerate(logs))/denom
    else: slope=0.0
    early=rms(y[:max(1,len(y)//4)])
    late=rms(y[-max(1,len(y)//4):])
    late_early=late/(early+EPS)
    block_gains=[]
    for b in range(4):
        lo=b*len(y)//4; hi=(b+1)*len(y)//4
        block_gains.append(log((rms(y[lo:hi])+EPS)/(rms(x[lo:hi])+EPS)))
    gain_span=max(block_gains)-min(block_gains)
    xlevels=[log(rms(x[b*len(x)//4:(b+1)*len(x)//4])+EPS) for b in range(4)]
    mgx=mean(xlevels); mgy=mean(block_gains)
    gain_slope=sum((a-mgx)*(b-mgy) for a,b in zip(xlevels,block_gains))/(sum((a-mgx)**2 for a in xlevels)+EPS)
    return [log_gain,crest,zc,centroid,bw,flat,peakf,*bins,slope,late_early,*fine_bins,gain_span,gain_slope,peak_count,notch_depth]


def simulate_domain(domain: str, model: AcousticNetwork | Mechanical2DOF,
                    probes: dict[str,list[float]], fs: float=FS,
                    registry: CodonRegistry=CodonRegistry()) -> dict[str,list[float]]:
    outputs={}
    for name,x in probes.items():
        if domain=="acoustic": y=simulate_acoustic(model,x,fs,registry)  # type: ignore[arg-type]
        elif domain=="mechanical": y=simulate_mechanical(model,x,fs,registry=registry)  # type: ignore[arg-type]
        else: raise ValueError("domain must be acoustic or mechanical")
        outputs[name]=extract_features(x,y,fs)
    return outputs


def flatten_probe_features(features: dict[str,list[float]]) -> list[float]:
    # Keep all five probe-conditioned signatures; preserves probe-specific response.
    return [v for p in PROBE_NAMES for v in features[p]]


def standardize(rows: Sequence[Sequence[float]]) -> tuple[list[list[float]],list[float],list[float]]:
    if not rows: return [],[],[]
    d=len(rows[0])
    mus=[mean(r[j] for r in rows) for j in range(d)]
    sig=[stddev([r[j] for r in rows]) for j in range(d)]
    sig=[s if s>1e-9 else 1.0 for s in sig]
    return [[(r[j]-mus[j])/sig[j] for j in range(d)] for r in rows],mus,sig


def euclidean(a: Sequence[float],b: Sequence[float]) -> float:
    return sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def rdm(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[0.0 if i==j else euclidean(rows[i],rows[j]) for j in range(len(rows))] for i in range(len(rows))]


def pairwise_upper(mat: Sequence[Sequence[float]]) -> list[float]:
    return [mat[i][j] for i in range(len(mat)) for j in range(i+1,len(mat))]


def quantiles(values: Sequence[float], qs: Sequence[float]=(0.1,0.25,0.5,0.75,0.9)) -> list[float]:
    if not values: return [0.0]*len(qs)
    s=sorted(values); out=[]
    for q in qs:
        pos=q*(len(s)-1); lo=int(pos); hi=min(len(s)-1,lo+1); frac=pos-lo
        out.append(s[lo]*(1-frac)+s[hi]*frac)
    return out


def jacobi_eigenvalues(matrix: Sequence[Sequence[float]], tol: float=1e-10, max_sweeps: int=40) -> list[float]:
    """Cyclic Jacobi eigensolver for small real symmetric matrices.

    A cyclic sweep avoids repeatedly searching for the largest off-diagonal
    entry, which is expensive in the pure-Python null simulations.
    """
    a=[list(row) for row in matrix]; n=len(a)
    if any(len(r)!=n for r in a): raise ValueError("matrix must be square")
    for _ in range(max_sweeps):
        largest=0.0
        for p in range(n-1):
            for q in range(p+1,n):
                apq=a[p][q]
                largest=max(largest,abs(apq))
                if abs(apq)<tol: continue
                tau=(a[q][q]-a[p][p])/(2.0*apq)
                t=(1.0 if tau>=0 else -1.0)/(abs(tau)+sqrt(1.0+tau*tau))
                c=1.0/sqrt(1.0+t*t); sn=t*c
                app,aqq=a[p][p],a[q][q]
                a[p][p]=app-t*apq; a[q][q]=aqq+t*apq
                a[p][q]=a[q][p]=0.0
                for k in range(n):
                    if k==p or k==q: continue
                    akp,akq=a[k][p],a[k][q]
                    a[k][p]=a[p][k]=c*akp-sn*akq
                    a[k][q]=a[q][k]=sn*akp+c*akq
        if largest<tol: break
    return sorted((a[i][i] for i in range(n)),reverse=True)


def covariance_spectrum(rows: Sequence[Sequence[float]]) -> list[float]:
    z,_,_=standardize(rows)
    if not z: return []
    n,d=len(z),len(z[0])
    cov=[[sum(r[i]*r[j] for r in z)/max(1,n-1) for j in range(d)] for i in range(d)]
    eig=jacobi_eigenvalues(cov)
    vals=[max(0.0,v) for v in eig]
    total=sum(vals)+EPS
    return [v/total for v in vals]


def cosine_similarity(a: Sequence[float],b: Sequence[float]) -> float:
    n=min(len(a),len(b)); aa=a[:n]; bb=b[:n]
    den=sqrt(sum(v*v for v in aa)*sum(v*v for v in bb))+EPS
    return sum(x*y for x,y in zip(aa,bb))/den


def wasserstein_1(a: Sequence[float],b: Sequence[float]) -> float:
    if not a or not b: return 0.0
    n=max(len(a),len(b)); qa=quantiles(a,[i/(n-1) for i in range(n)]) if n>1 else [median(a)]
    qb=quantiles(b,[i/(n-1) for i in range(n)]) if n>1 else [median(b)]
    return mean(abs(x-y) for x,y in zip(qa,qb))


def spearman(a: Sequence[float],b: Sequence[float]) -> float:
    if len(a)!=len(b) or len(a)<2: return 0.0
    def ranks(x: Sequence[float]) -> list[float]:
        order=sorted(range(len(x)),key=lambda i:x[i]); out=[0.0]*len(x); i=0
        while i<len(order):
            j=i+1
            while j<len(order) and x[order[j]]==x[order[i]]: j+=1
            r=(i+j-1)/2+1
            for k in range(i,j): out[order[k]]=r
            i=j
        return out
    ra,rb=ranks(a),ranks(b); ma,mb=mean(ra),mean(rb)
    va=sum((x-ma)**2 for x in ra); vb=sum((x-mb)**2 for x in rb)
    return sum((x-ma)*(y-mb) for x,y in zip(ra,rb))/(sqrt(va*vb)+EPS)


def entropy(p: Sequence[float]) -> float:
    return -sum(x*log(x+EPS) for x in p if x>0)


@dataclass
class GaussianProbeModel:
    means: list[list[float]]
    sigmas: list[list[float]]
    scale: list[float]


def fit_probe_models(train: dict[str,dict[int,list[list[float]]]]) -> dict[str,GaussianProbeModel]:
    models={}
    for probe,by_class in train.items():
        selected={cls:[[r[j] for j in ACTIVE_FEATURE_INDICES] for r in rows] for cls,rows in by_class.items()}
        allrows=[r for rs in selected.values() for r in rs]
        global_mean=[mean(r[j] for r in allrows) for j in range(len(ACTIVE_FEATURE_INDICES))]
        _,_,scale=standardize(allrows)
        means=[]; sigmas=[]
        for cls in sorted(selected):
            z=[[(r[j]-global_mean[j])/(scale[j] or 1.0) for j in range(len(r))] for r in selected[cls]]
            means.append([mean(r[j] for r in z) for j in range(len(z[0]))])
            sigmas.append([max(0.18,stddev([r[j] for r in z])) for j in range(len(z[0]))])
        models[probe]=GaussianProbeModel(means,sigmas,scale)
    return models


def log_likelihood(obs: Sequence[float], model: GaussianProbeModel, cls: int, extra_noise: float=0.25) -> float:
    mu,sig=model.means[cls],model.sigmas[cls]
    total=0.0
    for j,(o,m,s) in enumerate(zip(obs,mu,sig)):
        ss=sqrt(s*s+extra_noise*extra_noise)
        total += -0.5*((o-m)/ss)**2-log(ss)
    return total


def posterior_update(prior: Sequence[float], obs: Sequence[float], model: GaussianProbeModel, extra_noise: float=0.25) -> list[float]:
    logs=[log(max(p,EPS))+log_likelihood(obs,model,i,extra_noise) for i,p in enumerate(prior)]
    peak=max(logs); vals=[exp(v-peak) for v in logs]; z=sum(vals)+EPS
    return [v/z for v in vals]


def expected_information_gain(prior: Sequence[float], model: GaussianProbeModel, extra_noise: float=0.25) -> float:
    """Approximate mutual information using a three-point class-conditional rule.

    The single probe feature with the largest between-class mean variance is
    used for the +/- sigma offsets. This is a deliberately transparent EIG
    approximation, not an exact integral over the full multivariate Gaussian.
    """
    base=entropy(prior); expected=0.0; nclass=len(prior)
    if nclass <= 1: return 0.0
    d=len(model.means[0])
    global_means=[mean(m[j] for m in model.means) for j in range(d)]
    axes=sorted(range(d),key=lambda j:sum(prior[c]*(model.means[c][j]-global_means[j])**2 for c in range(nclass)),reverse=True)
    axis=axes[0] if axes else 0
    for c,p in enumerate(prior):
        mu=model.means[c]; sigma=model.sigmas[c]
        samples=[list(mu)]
        for sign in (-1.0,1.0):
            y=list(mu); y[axis]+=sign*0.85*sigma[axis]; samples.append(y)
        h=mean(entropy(posterior_update(prior,y,model,extra_noise)) for y in samples)
        expected += p*h
    return max(0.0,base-expected)


def normalize_feature(raw: Sequence[float], scale: Sequence[float], mean_values: Sequence[float]) -> list[float]:
    return [(x-m)/(s if s>1e-9 else 1.0) for x,m,s in zip(raw,mean_values,scale)]


def make_training(domain: str, seed: int, n_per_class: int=8) -> dict[str,dict[int,list[list[float]]]]:
    rng=Random(seed); probes=probe_signals(); train={p:{} for p in PROBE_NAMES}
    for cls in range(4):
        for _ in range(n_per_class):
            model=generate_acoustic(rng,cls) if domain=="acoustic" else generate_mechanical(rng,cls)
            for pname,x in probes.items():
                y=simulate_acoustic(model,x) if domain=="acoustic" else simulate_mechanical(model,x)
                train[pname].setdefault(cls,[]).append(extract_features(x,y))
    return train


def prepare_test_model(domain: str, cls: int, rng: Random) -> dict[str,list[float]]:
    p=probe_signals(); model=generate_acoustic(rng,cls) if domain=="acoustic" else generate_mechanical(rng,cls)
    return {name:extract_features(x,simulate_acoustic(model,x) if domain=="acoustic" else simulate_mechanical(model,x)) for name,x in p.items()}


def choose_probe(policy: str, available: Sequence[str], posterior: Sequence[float], models: dict[str,GaussianProbeModel], costs: dict[str,float], rng: Random, fixed_order: Sequence[str]) -> str:
    if policy=="random": return rng.choice(list(available))
    if policy=="fixed":
        for p in fixed_order:
            if p in available: return p
    scored=[(expected_information_gain(posterior,models[p])/costs[p],p) for p in available]
    return max(scored)[1]


def wilson_interval(successes: int, n: int, z: float=1.96) -> tuple[float,float]:
    if n <= 0: return (0.0,1.0)
    p=successes/n; den=1.0+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0.0,center-half),min(1.0,center+half)


def evaluate_active_observer(domain: str, seed: int, episodes_per_class: int=10, rounds: int=3,
                             measurement_noise: float=0.28) -> tuple[dict[str,dict[str,float]],list[dict[str,object]]]:
    train=make_training(domain,seed+10,n_per_class=12)
    models=fit_probe_models(train)
    costs={"impulse":1.0,"step":1.0,"chirp":1.45,"multisine":1.3,"amplitude_staircase":1.5}
    # Prior-best static order computed once under a uniform prior.
    prior=[0.25]*4; fixed_order=sorted(PROBE_NAMES,key=lambda p:expected_information_gain(prior,models[p])/costs[p],reverse=True)
    summaries={}; traces=[]
    # Every policy sees the exact same independently generated held-out systems.
    case_rng=Random(seed+90000)
    test_cases={(cls,ep):prepare_test_model(domain,cls,case_rng)
                for cls in range(4) for ep in range(episodes_per_class)}
    # Common feature-noise draws make policy comparisons paired at the
    # (episode, probe) level; policy randomness is used only for probe choice.
    noise_rng=Random(seed+90001)
    noise_draws={(cls,ep,pname):[noise_rng.gauss(0.0,measurement_noise) for _ in ACTIVE_FEATURE_INDICES]
                 for cls in range(4) for ep in range(episodes_per_class) for pname in PROBE_NAMES}
    for policy in ("active","fixed","random"):
        rng=Random(seed+1000+(0 if policy=="active" else 1 if policy=="fixed" else 2))
        n=0; correct=0; brier=0.0; logloss=0.0; used_cost=0.0
        confusion=[[0 for _ in range(4)] for _ in range(4)]
        for cls in range(4):
            for ep in range(episodes_per_class):
                test=test_cases[(cls,ep)]
                case_fingerprint=sha256(json.dumps(test,sort_keys=True,separators=(",",":" )).encode()).hexdigest()[:16]
                posterior=[0.25]*4; available=list(PROBE_NAMES)
                for turn in range(rounds):
                    pname=choose_probe(policy,available,posterior,models,costs,rng,fixed_order)
                    available.remove(pname); used_cost+=costs[pname]
                    base=[test[pname][j] for j in ACTIVE_FEATURE_INDICES]
                    # The model is normalized on training statistics and receives
                    # independent observation noise in feature space.
                    allrows=[[r[j] for j in ACTIVE_FEATURE_INDICES] for rs in train[pname].values() for r in rs]
                    mus=[mean(r[j] for r in allrows) for j in range(len(base))]
                    _,_,scales=standardize(allrows)
                    obs=normalize_feature(base,scales,mus)
                    obs=[v+noise for v,noise in zip(obs,noise_draws[(cls,ep,pname)])]
                    posterior=posterior_update(posterior,obs,models[pname],measurement_noise)
                    traces.append({"domain":domain,"policy":policy,"true_class":cls,"episode":ep,"case_fingerprint":case_fingerprint,"round":turn,"probe":pname,"posterior_max":max(posterior),"posterior":posterior[:]})
                pred=max(range(4),key=lambda i:posterior[i]); correct+=int(pred==cls); n+=1
                confusion[cls][pred]+=1
                brier+=sum((posterior[i]-(1.0 if i==cls else 0.0))**2 for i in range(4))
                logloss-=log(posterior[cls]+EPS)
        ci=wilson_interval(correct,n)
        summaries[policy]={"accuracy":correct/n,"accuracy_wilson_95":[ci[0],ci[1]],"correct":correct,"episodes":n,"brier":brier/n,"log_loss":logloss/n,"mean_probe_cost":used_cost/n,"confusion_matrix":confusion}
    return summaries,traces


def mst_edges(dist: Sequence[Sequence[float]]) -> list[float]:
    n=len(dist)
    if n<2:return []
    used={0}; out=[]
    while len(used)<n:
        best=(float("inf"),-1)
        for i in used:
            for j in range(n):
                if j not in used and dist[i][j]<best[0]: best=(dist[i][j],j)
        out.append(best[0]); used.add(best[1])
    return out


def damping_nonproportionality(p: Mechanical2DOF) -> float:
    """Relative Frobenius residual after best C ~= alpha*M + beta*K fit."""
    # Symmetric-matrix Frobenius weighting: off-diagonal is counted twice.
    pairs=((0,0,1.0),(1,1,1.0),(0,1,sqrt(2.0)))
    xx=[(p.mass[i][j],p.stiffness[i][j],p.damping[i][j]) for i,j,_ in pairs]
    weights=[w for _,_,w in pairs]
    a11=sum(w*w*m*m for (m,k,c),w in zip(xx,weights))
    a12=sum(w*w*m*k for (m,k,c),w in zip(xx,weights))
    a22=sum(w*w*k*k for (m,k,c),w in zip(xx,weights))
    b1=sum(w*w*m*c for (m,k,c),w in zip(xx,weights))
    b2=sum(w*w*k*c for (m,k,c),w in zip(xx,weights))
    det=a11*a22-a12*a12
    if abs(det)<EPS: return 1.0
    alpha=(b1*a22-b2*a12)/det
    beta=(a11*b2-a12*b1)/det
    residual=sum(w*w*(c-alpha*m-beta*k)**2 for (m,k,c),w in zip(xx,weights))
    norm=sum(w*w*c*c for (m,k,c),w in zip(xx,weights))
    return sqrt(residual/(norm+EPS))


def mechanical_modal_frequencies(p: Mechanical2DOF) -> tuple[float,float]:
    # Eigenfrequencies of M^-1 K for a 2x2 generalized eigenproblem.
    col0=solve2(p.mass,(p.stiffness[0][0],p.stiffness[1][0]))
    col1=solve2(p.mass,(p.stiffness[0][1],p.stiffness[1][1]))
    a,b=col0[0],col1[0]; c,d=col0[1],col1[1]
    tr=a+d; det=a*d-b*c
    disc=max(0.0,tr*tr-4.0*det)
    l1=max(0.0,0.5*(tr-sqrt(disc))); l2=max(0.0,0.5*(tr+sqrt(disc)))
    return sqrt(l1)/(2*pi),sqrt(l2)/(2*pi)


def make_system_bank(domain: str, seed: int, count: int=32) -> tuple[list[list[float]],list[dict[str,object]]]:
    rng=Random(seed); p=probe_signals(); rows=[]; meta=[]
    for i in range(count):
        structural_class=rng.randrange(4)
        if domain=="acoustic":
            model=generate_acoustic(rng,structural_class)
            params={"structural_class":structural_class,"mode_count":len(model.modes),
                    "mode_frequencies_hz":[round(m[0],5) for m in model.modes],
                    "notch_hz":model.notch_hz,"compression":model.compression,
                    "sensor_gain":model.sensor_gain,"sensor_delay_samples":model.sensor_delay}
        else:
            model=generate_mechanical(rng,structural_class)
            fmodal=mechanical_modal_frequencies(model)
            params={"structural_class":structural_class,"modal_frequencies_hz":[round(v,5) for v in fmodal],
                    "damping_nonproportionality":damping_nonproportionality(model),
                    "coupling_stiffness":-model.stiffness[0][1],"cubic_coefficients":list(model.cubic),
                    "sensor_vector":list(model.sensor_vector),"sensor_gain":model.sensor_gain,
                    "sensor_delay_samples":model.sensor_delay}
        feats=simulate_domain(domain,model,p)
        rows.append(flatten_probe_features(feats))
        meta.append({"index":i,"domain":domain,"probe_count":len(p),"feature_count":len(rows[-1]),"parameters":json.dumps(params,sort_keys=True)})
    z,_,_=standardize(rows)
    return z,meta


def apply_sensor_response(y: Sequence[float], fs: float, gain: float=1.0,
                          cutoff_hz: float | None=None, delay_seconds: float=0.0) -> list[float]:
    """Apply a separate first-order sensor low-pass, gain and physical delay."""
    out=list(y)
    if cutoff_hz is not None:
        if not (0.0 < cutoff_hz < fs/2): raise ValueError("sensor cutoff must lie below Nyquist")
        alpha=exp(-2.0*pi*cutoff_hz/fs)
        state=0.0; filtered=[]
        for value in out:
            state=alpha*state+(1.0-alpha)*value
            filtered.append(state)
        out=filtered
    delay=max(0,int(round(delay_seconds*fs)))
    shifted=[0.0]*len(out)
    for i,value in enumerate(out):
        if i+delay<len(out): shifted[i+delay]=gain*value
    return shifted


def response_bank_for_rate(domain: str, models: Sequence[AcousticNetwork | Mechanical2DOF],
                           fs: float, sensor_cutoff: float | None=None,
                           sensor_gain: float=1.0, delay_seconds: float=0.0) -> list[list[float]]:
    n=int(round(fs*DURATION))
    if n & (n-1): raise ValueError("sampling rate must make a power-of-two sample count over fixed duration")
    probes_local=probe_signals(fs,n); rows=[]
    for model in models:
        local={}
        for name,x in probes_local.items():
            if domain=="acoustic": y=simulate_acoustic(model,x,fs)  # type: ignore[arg-type]
            else: y=simulate_mechanical(model,x,fs)  # type: ignore[arg-type]
            y=apply_sensor_response(y,fs,sensor_gain,sensor_cutoff,delay_seconds)
            local[name]=extract_features(x,y,fs)
        rows.append(flatten_probe_features(local))
    z,_,_=standardize(rows)
    return z


def nuisance_sweeps(seed: int=6001, count: int=12) -> dict[str,object]:
    """Matched-system nuisance controls; model parameters stay fixed within sweep."""
    rng=Random(seed)
    acoustic_models=[replace(generate_acoustic(rng,rng.randrange(4)),sensor_delay=0) for _ in range(count)]
    mechanical_models=[replace(generate_mechanical(rng,rng.randrange(4)),sensor_delay=0) for _ in range(count)]
    sample_rate_rows=[]; sensor_rows=[]
    for domain,models in (("acoustic",acoustic_models),("mechanical",mechanical_models)):
        refs={fs:response_bank_for_rate(domain,models,fs) for fs in (128.0,256.0,512.0)}
        base_pairs=pairwise_upper(rdm(refs[256.0]))
        for fs in (128.0,512.0):
            sample_rate_rows.append({"domain":domain,"sample_rate_hz":int(fs),
                                     "rdm_rank_retention_vs_256hz":spearman(base_pairs,pairwise_upper(rdm(refs[fs])))})
        base=refs[256.0]
        for cutoff in (24.0,48.0,72.0):
            filtered=response_bank_for_rate(domain,models,256.0,sensor_cutoff=cutoff,
                                             sensor_gain=1.7,delay_seconds=0.008)
            sensor_rows.append({"domain":domain,"sensor_cutoff_hz":cutoff,
                                "sensor_gain":1.7,"delay_seconds":0.008,
                                "rdm_rank_retention":spearman(pairwise_upper(rdm(base)),pairwise_upper(rdm(filtered)))})
    return {"sample_rate_sweep":sample_rate_rows,"sensor_transfer_sweep":sensor_rows,
            "systems_per_domain":count,"physical_duration_s":DURATION}


def cross_domain_unpaired_geometry(acoustic_rows: Sequence[Sequence[float]], mechanical_rows: Sequence[Sequence[float]], seed: int=77, null_reps: int=199) -> dict[str,object]:
    # No one-to-one system pairing is asserted. Compare scale-normalized summaries
    # of within-domain relational geometries and covariance spectra.
    # Full response-conditioned RDMs are separately exported. This comparison
    # uses the same compact aggregate representation on both domains.
    # For covariance-spectrum comparison, aggregate each system's five probe
    # signatures feature-wise. This gives a compact 17-D unpaired geometry
    # summary; the full 65-D response-conditioned RDM remains separately saved.
    geometry_indices=(0,1,2,3,4,5,6,7,8,9,10,11,12,29,30,31,32)
    # Compact 17-D summary: the 13 base dynamics descriptors plus four
    # cross-probe spectral/nonlinear descriptors. Detailed 33-D features remain
    # in the RDM and active-identification experiments.
    def probe_average(rows: Sequence[Sequence[float]]) -> list[list[float]]:
        return [[mean(row[k*len(FEATURE_NAMES)+j] for k in range(len(PROBE_NAMES)))
                 for j in geometry_indices] for row in rows]
    agg_a,agg_m=probe_average(acoustic_rows),probe_average(mechanical_rows)
    da,dm=rdm(agg_a),rdm(agg_m)
    pa,pm=pairwise_upper(da),pairwise_upper(dm)
    ma,mm=mst_edges(da),mst_edges(dm)
    ea,em=covariance_spectrum(agg_a),covariance_spectrum(agg_m)
    # Normalize distance distributions by their own medians to compare shape, not units.
    q_a=quantiles([x/(median(pa)+EPS) for x in pa],tuple(i/10 for i in range(1,10)))
    q_m=quantiles([x/(median(pm)+EPS) for x in pm],tuple(i/10 for i in range(1,10)))
    mst_a=[x/(median(ma)+EPS) for x in ma]; mst_m=[x/(median(mm)+EPS) for x in mm]
    signature_similarity=cosine_similarity(ea,em)
    dist_profile_gap=mean(abs(a-b) for a,b in zip(q_a,q_m))
    mst_profile_gap=wasserstein_1(mst_a,mst_m)
    rng=Random(seed); null_cos=[]; null_dist=[]; null_mst=[]
    n=len(agg_a); d=len(agg_a[0])
    def shuffle_columns(rows: Sequence[Sequence[float]]) -> list[list[float]]:
        cols=[[row[j] for row in rows] for j in range(d)]
        for col in cols: rng.shuffle(col)
        return [[cols[j][i] for j in range(d)] for i in range(n)]
    for _ in range(null_reps):
        ra,rb=shuffle_columns(agg_a),shuffle_columns(agg_m)
        null_cos.append(cosine_similarity(covariance_spectrum(ra),covariance_spectrum(rb)))
        rda,rdb=rdm(ra),rdm(rb)
        pda,pdm=pairwise_upper(rda),pairwise_upper(rdb)
        qa=quantiles([x/(median(pda)+EPS) for x in pda],tuple(i/10 for i in range(1,10)))
        qm=quantiles([x/(median(pdm)+EPS) for x in pdm],tuple(i/10 for i in range(1,10)))
        null_dist.append(mean(abs(x-y) for x,y in zip(qa,qm)))
        nma,nmm=mst_edges(rda),mst_edges(rdb)
        null_mst.append(wasserstein_1([x/(median(nma)+EPS) for x in nma],[x/(median(nmm)+EPS) for x in nmm]))
    p_cos=(1+sum(v>=signature_similarity for v in null_cos))/(1+len(null_cos))
    p_dist=(1+sum(v<=dist_profile_gap for v in null_dist))/(1+len(null_dist))
    p_mst=(1+sum(v<=mst_profile_gap for v in null_mst))/(1+len(null_mst))
    return {
        "paired_rdm_correlation":None,
        "comparison_type":"unpaired distributional geometry; no itemwise cross-domain pairing",
        "covariance_summary_feature_indices":list(geometry_indices),
        "distance_and_mst_comparison":"same 17-D probe-averaged feature summary in each domain; no cross-domain item pairing",
        "normalized_distance_quantiles_acoustic":q_a,
        "normalized_distance_quantiles_mechanical":q_m,
        "distance_profile_mean_abs_gap":dist_profile_gap,
        "mst_profile_wasserstein":mst_profile_gap,
        "covariance_eigen_spectrum_acoustic":ea,
        "covariance_eigen_spectrum_mechanical":em,
        "covariance_spectrum_cosine_similarity":signature_similarity,
        "column_shuffled_null_covariance_cosine_mean":mean(null_cos),
        "column_shuffled_null_covariance_cosine_95pct":quantiles(null_cos,(0.95,))[0],
        "column_shuffled_null_distance_gap_mean":mean(null_dist),
        "column_shuffled_null_distance_gap_05pct":quantiles(null_dist,(0.05,))[0],
        "column_shuffled_null_mst_gap_mean":mean(null_mst),
        "column_shuffled_null_mst_gap_05pct":quantiles(null_mst,(0.05,))[0],
        "null_empirical_p_cosine_upper":p_cos,
        "null_empirical_p_distance_lower":p_dist,
        "null_empirical_p_mst_lower":p_mst,
        "null_replicates":null_reps,
        "acoustic_systems":n,"mechanical_systems":len(mechanical_rows),
    }


def run_benchmark(out_dir: Path, seed: int=20261105) -> dict[str,object]:
    out_dir.mkdir(parents=True,exist_ok=True); data=out_dir/"data"; reports=out_dir/"reports"
    data.mkdir(exist_ok=True); reports.mkdir(exist_ok=True)
    results: dict[str,object]={"build":"10","seed":seed,"fs_hz":FS,"samples":N,"duration_s":DURATION}
    # Heterogeneous response geometry banks: no paired parameters between domains.
    arows,ameta=make_system_bank("acoustic",seed+101,32); print("[build10] acoustic bank",flush=True)
    mrows,mmeta=make_system_bank("mechanical",seed+202,32); print("[build10] mechanical bank",flush=True)
    geometry=cross_domain_unpaired_geometry(arows,mrows,seed+303,199); print("[build10] cross-domain controls",flush=True)
    results["unpaired_cross_domain_geometry"]=geometry
    # Summarize independently drawn structures; no parameters are paired across domains.
    acoustic_parameters=[json.loads(x["parameters"]) for x in ameta]
    mechanical_parameters=[json.loads(x["parameters"]) for x in mmeta]
    results["structural_bank_summary"]={
        "acoustic_class_counts":{str(k):sum(p["structural_class"]==k for p in acoustic_parameters) for k in range(4)},
        "acoustic_mode_count_histogram":{str(k):sum(p["mode_count"]==k for p in acoustic_parameters) for k in (2,3)},
        "acoustic_antiresonance_count":sum(p["notch_hz"] is not None for p in acoustic_parameters),
        "acoustic_compression_range":[min(p["compression"] for p in acoustic_parameters),max(p["compression"] for p in acoustic_parameters)],
        "mechanical_class_counts":{str(k):sum(p["structural_class"]==k for p in mechanical_parameters) for k in range(4)},
        "mechanical_damping_nonproportionality_range":[min(p["damping_nonproportionality"] for p in mechanical_parameters),max(p["damping_nonproportionality"] for p in mechanical_parameters)],
        "mechanical_nonlinear_models":sum(max(p["cubic_coefficients"])>0.05 for p in mechanical_parameters),
    }
    results["nuisance_sweeps"]=nuisance_sweeps(seed+350,12); print("[build10] nuisance sweeps",flush=True)
    for name,rows in (("acoustic",arows),("mechanical",mrows)):
        dist=rdm(rows)
        with (data/f"{name}_rdm.csv").open("w",newline="") as f:
            w=csv.writer(f); w.writerow(["system"]+[f"s{i}" for i in range(len(rows))])
            for i,row in enumerate(dist): w.writerow([i]+row)
    with (data/"system_bank_manifest.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["index","domain","probe_count","feature_count","parameters"]);w.writeheader();w.writerows(ameta+mmeta)
    # Active observer: separately trained and tested within each domain.
    active={}; alltraces=[]
    for domain,sd in (("acoustic",seed+401),("mechanical",seed+402)):
        summary,traces=evaluate_active_observer(domain,sd,episodes_per_class=8,rounds=3,measurement_noise=0.22); print(f"[build10] active observer {domain}",flush=True)
        active[domain]=summary; alltraces.extend(traces)
    results["active_probe_identification"]=active
    with (data/"active_probe_trace.csv").open("w",newline="") as f:
        fields=["domain","policy","true_class","episode","case_fingerprint","round","probe","posterior_max","posterior"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in alltraces:
            r=row.copy();r["posterior"]=json.dumps(r["posterior"]);w.writerow(r)
    # Probe rank by class-separability utility under uniform prior.
    probe_rank=[]
    for domain,sd in (("acoustic",seed+501),("mechanical",seed+502)):
        train=make_training(domain,sd,12); models=fit_probe_models(train); prior=[0.25]*4; print(f"[build10] probe ranking {domain}",flush=True)
        costs={"impulse":1.0,"step":1.0,"chirp":1.45,"multisine":1.3,"amplitude_staircase":1.5}
        for pname,model in models.items():
            probe_rank.append({"domain":domain,"probe":pname,"expected_information_gain":expected_information_gain(prior,model),"cost":costs[pname],"gain_per_cost":expected_information_gain(prior,model)/costs[pname]})
    with (data/"probe_information_ranking.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(probe_rank[0]));w.writeheader();w.writerows(probe_rank)
    results["probe_information_ranking"]=probe_rank
    # Calibration/noise robustness: add independent feature noise to bank rows.
    robustness=[]; rng=Random(seed+601)
    for domain,rows in (("acoustic",arows),("mechanical",mrows)):
        base=rdm(rows); base_pairs=pairwise_upper(base)
        for noise in (0.0,0.1,0.25,0.5):
            for distribution in (("gaussian","laplace","uniform") if noise>0 else ("gaussian",)):
                pert=[]
                for row in rows:
                    values=[]
                    for v in row:
                        if distribution=="gaussian": e=rng.gauss(0,noise)
                        elif distribution=="laplace":
                            u=rng.random()-0.5; e=-(noise/sqrt(2.0))*(1 if u>=0 else -1)*log(max(EPS,1-2*abs(u)))
                        else: e=rng.uniform(-sqrt(3)*noise,sqrt(3)*noise)
                        values.append(v+e)
                    pert.append(values)
                noisy=pairwise_upper(rdm(pert))
                robustness.append({"domain":domain,"distribution":distribution,"feature_noise_z":noise,
                                   "distance_rank_retention":spearman(base_pairs,noisy)})
    with (data/"noise_robustness.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(robustness[0]));w.writeheader();w.writerows(robustness)
    results["noise_robustness"]=robustness; print("[build10] noise controls",flush=True)
    with (data/"sample_rate_sweep.csv").open("w",newline="") as f:
        rows=results["nuisance_sweeps"]["sample_rate_sweep"]
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (data/"sensor_transfer_sweep.csv").open("w",newline="") as f:
        rows=results["nuisance_sweeps"]["sensor_transfer_sweep"]
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # Codon alias-invariance smoke check using a deterministic mechanical trace.
    p=generate_mechanical(Random(seed+701),3); x=probe_signals()["multisine"]
    standard=simulate_mechanical(p,x,registry=CodonRegistry())
    alt=simulate_mechanical(p,x,registry=CodonRegistry("load","plus","minus","times","divide","pow","write"))
    results["codon_alias_max_abs_error"]=max(abs(a-b) for a,b in zip(standard,alt))
    report_path=reports/"build_10_report.json"
    report_path.write_text(json.dumps(results,indent=2,sort_keys=True),encoding="utf-8")
    key={"build":"10","unpaired_geometry":geometry,"active_probe_identification":active,"codon_alias_max_abs_error":results["codon_alias_max_abs_error"]}
    (reports/"key_results.json").write_text(json.dumps(key,indent=2,sort_keys=True),encoding="utf-8")
    return results


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Build 10 heterogeneous system-response geometry benchmark")
    parser.add_argument("--out",default=".")
    parser.add_argument("--seed",type=int,default=20261105)
    args=parser.parse_args()
    result=run_benchmark(Path(args.out),args.seed)
    print(json.dumps({"build":result["build"],"geometry":result["unpaired_cross_domain_geometry"],"active":result["active_probe_identification"]},indent=2))
