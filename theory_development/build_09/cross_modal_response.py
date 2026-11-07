"""Build 09: cross-modal response geometry.

Standard-library-only synthetic benchmark. It compares discrete acoustic-like
resonators with continuous mechanical oscillators under matched probes. The
experiment is a system-identification / response-geometry study, not a model of
human emotion, biological hearing, or tactile perception.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from math import acos, atan2, cos, exp, log, pi, sin, sqrt, tanh
from random import Random
from statistics import mean
from typing import Callable, Sequence
import csv
import json
from pathlib import Path

FS = 128.0
N = 1024
DURATION = N / FS
FREQS = tuple(3.0 + 0.5 * i for i in range(43))  # 3..24 Hz


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
        names=(self.load,self.add,self.sub,self.mul,self.div,self.power,self.store)
        if any(not x for x in names) or len(set(names)) != len(names):
            raise ValueError("codon aliases must be unique and nonempty")


def execute_codon(code: str, *args: float, registry: CodonRegistry = CodonRegistry()) -> float:
    """Minimal executable arithmetic codon subset used by Build 09."""
    if code == registry.load or code == registry.store:
        if len(args) != 1: raise ValueError(f"{code} expects one operand")
        return args[0]
    if code == registry.power:
        if len(args) != 2: raise ValueError(f"{code} expects base and integer exponent")
        return args[0] ** int(args[1])
    if len(args) != 2: raise ValueError(f"{code} expects two operands")
    a,b=args
    if code == registry.add: return a+b
    if code == registry.sub: return a-b
    if code == registry.mul: return a*b
    if code == registry.div:
        if abs(b) < 1e-15: raise ZeroDivisionError("codon division by near-zero")
        return a/b
    raise ValueError(f"unknown codon: {code}")


@dataclass(frozen=True)
class Params:
    family_id: int
    f0_hz: float
    zeta: float
    gain: float
    mass: float
    nonlinearity: float


@dataclass
class SystemRecord:
    family_id: int
    domain: str
    params: Params
    impulse: list[float]
    step: list[float]
    chirp: list[float]
    chirp_input: list[float]
    low_amp: list[float]
    high_amp: list[float]
    features: dict[str, list[float] | float]


def fft(values: Sequence[complex]) -> list[complex]:
    """Iterative radix-2 FFT."""
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
        angle = -2.0 * pi / length
        wlen = complex(cos(angle), sin(angle))
        half = length // 2
        for start in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(start, start + half):
                u = a[k]
                v = a[k + half] * w
                a[k] = u + v
                a[k + half] = u - v
                w *= wlen
        length <<= 1
    return a


def rms(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sqrt(sum(x*x for x in values) / len(values))


def stddev(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    m = mean(values)
    return sqrt(sum((x-m)*(x-m) for x in values) / len(values))


def standardize_columns(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    if not rows:
        return []
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError("feature rows have inconsistent lengths")
    means = [mean(r[j] for r in rows) for j in range(width)]
    scales = []
    for j in range(width):
        s = stddev([r[j] for r in rows])
        scales.append(s if s > 1e-12 else 1.0)
    return [[(r[j] - means[j]) / scales[j] for j in range(width)] for r in rows]


def acoustic_resonator(params: Params, signal: Sequence[float],
                       fs: float = FS, nonlinear: bool = False,
                       registry: CodonRegistry = CodonRegistry()) -> list[float]:
    """Second-order digital resonator (direct-form recurrence).

    Its poles are parameterized by the same target natural frequency and damping
    ratio as the mechanical oscillator. This is an intentionally different
    realization of a comparable second-order response law.
    """
    wn = 2.0 * pi * params.f0_hz
    wd = wn * sqrt(max(1e-10, 1.0 - params.zeta*params.zeta))
    r = exp(-params.zeta * wn / fs)
    theta = wd / fs
    a1 = 2.0 * r * cos(theta)
    a2 = -(r*r)
    b0 = 1.0 - a1 - a2  # unit DC gain before nonlinear output stage
    y1 = y2 = 0.0
    out: list[float] = []
    for x in signal:
        state_y = execute_codon(registry.add,
                    execute_codon(registry.mul,b0,x,registry=registry),
                    execute_codon(registry.mul,a1,y1,registry=registry),
                    registry=registry)
        state_y = execute_codon(registry.add,state_y,
                    execute_codon(registry.mul,a2,y2,registry=registry),registry=registry)
        observed_y = state_y
        if nonlinear and params.nonlinearity > 0:
            # Smooth output compression; alpha controls strength, not a percept.
            observed_y = observed_y / (1.0 + params.nonlinearity * abs(observed_y) * 35.0)
        out.append(execute_codon(registry.store,params.gain * observed_y,registry=registry))
        y2, y1 = y1, state_y
    return out


def rk4_mechanical(params: Params, force: Sequence[float], fs: float = FS,
                   initial_velocity: float = 0.0,
                   nonlinear: bool = False,
                   registry: CodonRegistry = CodonRegistry()) -> list[float]:
    """Integrate m*x'' + c*x' + k*x + beta*x^3 = F(t) with RK4.

    Four substeps per sample reduce discretization error. The cubic stiffness is
    enabled only for the nonlinear stress probe.
    """
    m = params.mass
    wn = 2.0 * pi * params.f0_hz
    k = m * wn * wn
    c = 2.0 * params.zeta * m * wn
    # Scale cubic stiffness so the nonlinear stress probe is measurable while
    # remaining bounded for the chosen short, low-amplitude test signals.
    beta = (params.nonlinearity * k * 50000.0) if nonlinear else 0.0
    dt = 1.0 / fs
    sub = dt / 4.0
    x = 0.0
    v = initial_velocity / m
    out: list[float] = []

    def deriv(xx: float, vv: float, ff: float) -> tuple[float, float]:
        damping = execute_codon(registry.mul,c,vv,registry=registry)
        stiffness = execute_codon(registry.mul,k,xx,registry=registry)
        residual = execute_codon(registry.sub,ff,damping,registry=registry)
        residual = execute_codon(registry.sub,residual,stiffness,registry=registry)
        if beta:
            cubic = execute_codon(registry.power,xx,3,registry=registry)
            residual = execute_codon(registry.sub,residual,
                        execute_codon(registry.mul,beta,cubic,registry=registry),registry=registry)
        acc = execute_codon(registry.div,residual,m,registry=registry)
        return vv, acc

    for f in force:
        for _ in range(4):
            k1x, k1v = deriv(x, v, f)
            k2x, k2v = deriv(x + 0.5*sub*k1x, v + 0.5*sub*k1v, f)
            k3x, k3v = deriv(x + 0.5*sub*k2x, v + 0.5*sub*k2v, f)
            k4x, k4v = deriv(x + sub*k3x, v + sub*k3v, f)
            x += sub * (k1x + 2*k2x + 2*k3x + k4x) / 6.0
            v += sub * (k1v + 2*k2v + 2*k3v + k4v) / 6.0
        out.append(execute_codon(registry.store,params.gain * x,registry=registry))
    return out


def probes(fs: float = FS, n: int = N) -> dict[str, list[float]]:
    impulse = [0.0] * n
    impulse[0] = 1.0
    step = [0.06] * n
    # 2..24 Hz linear chirp over the full window, with a gentle Hann-like taper
    # to reduce edge transients.
    chirp: list[float] = []
    low: list[float] = []
    high: list[float] = []
    phase = 0.0
    duration = n / fs
    for i in range(n):
        t = i / fs
        f = 2.0 + (24.0 - 2.0) * (t / duration)
        phase += 2.0*pi*f/fs
        envelope = 0.5 - 0.5*cos(2.0*pi*i/(n-1))
        chirp.append(0.08 * envelope * sin(phase))
        low.append(2.5 * sin(2.0*pi*10.0*t))
        high.append(15.0 * sin(2.0*pi*10.0*t))
    return {"impulse": impulse, "step": step, "chirp": chirp,
            "low_amp": low, "high_amp": high}


def nearest_bin(freq_hz: float, fs: float, n: int) -> int:
    return max(1, min(n//2 - 1, round(freq_hz * n / fs)))


def phase_unwrap(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    out = [values[0]]
    offset = 0.0
    prev = values[0]
    for x in values[1:]:
        delta = x - prev
        if delta > pi:
            offset -= 2*pi
        elif delta < -pi:
            offset += 2*pi
        out.append(x + offset)
        prev = x
    return out


def spectral_features(signal: Sequence[float], fs: float = FS) -> tuple[list[float], list[float], list[float]]:
    spec = fft([complex(v, 0.0) for v in signal])
    selected = [nearest_bin(f, fs, len(signal)) for f in FREQS]
    mags = [abs(spec[k]) for k in selected]
    scale = max(mags) if mags else 1.0
    logmag = [20.0*log(max(m/scale, 1e-12), 10) for m in mags]
    phases = phase_unwrap([atan2(spec[k].imag, spec[k].real) for k in selected])
    # Dominant bin across 3..24 Hz.
    kmax = selected[max(range(len(mags)), key=lambda i: mags[i])]
    peak_hz = kmax * fs / len(signal)
    return logmag, phases, [peak_hz]


def decay_signature(signal: Sequence[float], windows: int = 16) -> list[float]:
    chunk = max(1, len(signal)//windows)
    vals = []
    for i in range(windows):
        part = signal[i*chunk:(i+1)*chunk]
        vals.append(log(max(rms(part), 1e-12)))
    return vals


def step_metrics(signal: Sequence[float]) -> list[float]:
    final = mean(signal[-max(8, len(signal)//10):])
    peak = max(signal)
    trough = min(signal)
    denom = max(abs(final), 1e-10)
    overshoot = max(0.0, (peak-final)/denom)
    undershoot = max(0.0, (final-trough)/denom)
    band = 0.02 * denom
    settle = float(len(signal))
    for i in range(len(signal)):
        if all(abs(v-final) <= band for v in signal[i:]):
            settle = float(i)
            break
    # normalized rise time to 90% of final value
    threshold = 0.9 * final
    rise = float(next((i for i,v in enumerate(signal) if v >= threshold), len(signal)-1))
    return [final/max(abs(v) for v in signal), overshoot, undershoot, settle/len(signal), rise/len(signal)]


def modulation_features(signal: Sequence[float], windows: int = 32) -> list[float]:
    # Envelope from local RMS; captures temporal amplitude fluctuation without
    # interpreting it as a human perceptual roughness rating.
    chunk = max(1, len(signal)//windows)
    env = [rms(signal[i*chunk:(i+1)*chunk]) for i in range(windows)]
    env_mean = mean(env)
    env_var = stddev(env)
    diffs = [abs(env[i+1]-env[i]) for i in range(len(env)-1)]
    return [env_mean, env_var, mean(diffs) if diffs else 0.0,
            max(env)-min(env) if env else 0.0]


def features_for_record(impulse: Sequence[float], step: Sequence[float],
                        chirp: Sequence[float], chirp_input: Sequence[float],
                        low_amp: Sequence[float], high_amp: Sequence[float],
                        fs: float = FS) -> dict[str, list[float]]:
    # Gain-normalize the impulse before comparing modal shape. Preserve separate
    # gain and amplitude-response features as distinct channels.
    peak = max(abs(x) for x in impulse) or 1.0
    normalized = [x/peak for x in impulse]
    mag, phase, peakf = spectral_features(normalized, fs)
    temporal = decay_signature(normalized)
    stepf = step_metrics(step)
    mod = modulation_features(chirp)
    # Chirp output/input spectral ratio at the selected bins.
    X = fft([complex(v,0) for v in chirp_input])
    Y = fft([complex(v,0) for v in chirp])
    transfer_mag = []
    transfer_phase = []
    for f in FREQS:
        k = nearest_bin(f, fs, len(chirp))
        ratio = Y[k] / X[k] if abs(X[k]) > 1e-8 else 0j
        transfer_mag.append(20*log(max(abs(ratio),1e-12),10))
        transfer_phase.append(atan2(ratio.imag, ratio.real))
    low_gain = rms(low_amp) / max(2.5/sqrt(2), 1e-12)
    high_gain = rms(high_amp) / max(15.0/sqrt(2), 1e-12)
    amplitude_sensitivity = (high_gain-low_gain)/max(low_gain,1e-12)
    return {
        "spectral": mag,
        "phase": phase,
        "temporal": temporal,
        "step": stepf,
        "modulation": mod,
        "transfer": transfer_mag + transfer_phase,
        "amplitude": [low_gain, high_gain, amplitude_sensitivity],
        "modal": [peakf[0], stepf[3], stepf[1], temporal[-1]-temporal[0]],
    }


def make_family_params(count: int = 40, seed: int = 20261104) -> list[Params]:
    rng = Random(seed)
    result = []
    for i in range(count):
        f0 = rng.uniform(4.5, 20.0)
        zeta = rng.uniform(0.08, 0.42)
        gain = rng.uniform(0.65, 1.45)
        mass = rng.uniform(0.65, 1.8)
        nonlin = rng.uniform(0.001, 0.018)
        result.append(Params(i, f0, zeta, gain, mass, nonlin))
    return result


def simulate_domain(params: Params, domain: str, fs: float = FS,
                    n: int | None = None,
                    registry: CodonRegistry = CodonRegistry()) -> SystemRecord:
    n = n or int(round(DURATION * fs))
    if n & (n - 1):
        raise ValueError("sample count must be a power of two for the FFT")
    p = probes(fs, n)
    if domain == "acoustic":
        impulse = acoustic_resonator(params, p["impulse"], fs, registry=registry)
        step = acoustic_resonator(params, p["step"], fs, registry=registry)
        chirp = acoustic_resonator(params, p["chirp"], fs, registry=registry)
        low = acoustic_resonator(params, p["low_amp"], fs, nonlinear=True, registry=registry)
        high = acoustic_resonator(params, p["high_amp"], fs, nonlinear=True, registry=registry)
    elif domain == "mechanical":
        impulse = rk4_mechanical(params, [0.0]*n, fs, initial_velocity=1.0, registry=registry)
        step = rk4_mechanical(params, p["step"], fs, registry=registry)
        chirp = rk4_mechanical(params, p["chirp"], fs, registry=registry)
        low = rk4_mechanical(params, p["low_amp"], fs, nonlinear=True, registry=registry)
        high = rk4_mechanical(params, p["high_amp"], fs, nonlinear=True, registry=registry)
    else:
        raise ValueError(f"unknown domain: {domain}")
    feats = features_for_record(impulse, step, chirp, p["chirp"], low, high, fs)
    return SystemRecord(params.family_id, domain, params, impulse, step, chirp,
                        p["chirp"], low, high, feats)


def euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vector dimensions differ")
    return sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def rdm(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    scaled = standardize_columns(rows)
    return [[euclidean(scaled[i], scaled[j]) for j in range(len(scaled))]
            for i in range(len(scaled))]


def upper_triangle(matrix: Sequence[Sequence[float]]) -> list[float]:
    return [matrix[i][j] for i in range(len(matrix)) for j in range(i+1,len(matrix))]


def ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0]*len(values)
    k = 0
    while k < len(order):
        j = k+1
        while j < len(order) and values[order[j]] == values[order[k]]:
            j += 1
        rank = (k + 1 + j) / 2.0
        for z in range(k,j):
            out[order[z]] = rank
        k = j
    return out


def pearson(a: Sequence[float], b: Sequence[float]) -> float:
    ma, mb = mean(a), mean(b)
    da = [x-ma for x in a]
    db = [x-mb for x in b]
    den = sqrt(sum(x*x for x in da)*sum(y*y for y in db))
    return sum(x*y for x,y in zip(da,db))/den if den > 1e-15 else 0.0


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    return pearson(ranks(a), ranks(b))


def nearest_partner_accuracy(source_rdm: Sequence[Sequence[float]],
                             target_rdm: Sequence[Sequence[float]]) -> float:
    """Cross-domain partner retrieval using rank profiles, not raw units.

    For each family i, compare its within-domain distance profile to each target
    family's profile. Correct target is same family ID. This is a simple
    relational matching diagnostic; it is not a learned cross-modal embedding.
    """
    n = len(source_rdm)
    # Keep all shared anchors, including the zero self-distance. This makes
    # each row a profile over the same family-ID reference set.
    profiles_a = [ranks(list(source_rdm[i])) for i in range(n)]
    profiles_b = [ranks(list(target_rdm[i])) for i in range(n)]
    correct = 0
    for i in range(n):
        scores = [pearson(profiles_a[i], profiles_b[j]) for j in range(n)]
        if max(range(n), key=lambda j: scores[j]) == i:
            correct += 1
    return correct/n


def bootstrap_rdm_corr(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]],
                       reps: int = 400, seed: int = 123) -> tuple[float,float]:
    rng = Random(seed)
    n = len(a)
    vals=[]
    for _ in range(reps):
        idx=[rng.randrange(n) for _ in range(n)]
        # Remove duplicate-index self pairs; retain distinct sampled observations.
        aa=[]; bb=[]
        for i in range(n):
            for j in range(i+1,n):
                if idx[i] != idx[j]:
                    aa.append(a[idx[i]][idx[j]])
                    bb.append(b[idx[i]][idx[j]])
        if len(aa)>10:
            vals.append(spearman(aa,bb))
    vals.sort()
    if not vals:
        return (0.0,0.0)
    return vals[int(0.025*(len(vals)-1))], vals[int(0.975*(len(vals)-1))]


def permutation_test(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]],
                     reps: int = 499, seed: int = 987) -> tuple[float,float]:
    rng=Random(seed)
    n=len(a)
    observed=spearman(upper_triangle(a),upper_triangle(b))
    null=[]
    base=[list(row) for row in b]
    for _ in range(reps):
        perm=list(range(n)); rng.shuffle(perm)
        bp=[[base[perm[i]][perm[j]] for j in range(n)] for i in range(n)]
        null.append(spearman(upper_triangle(a),upper_triangle(bp)))
    p=(1+sum(v>=observed for v in null))/(reps+1)
    return observed,p



def holm_adjust(p_values: dict[str,float]) -> dict[str,float]:
    """Holm family-wise adjustment for a predeclared set of p-values."""
    items=sorted(p_values.items(),key=lambda item:item[1])
    m=len(items)
    adjusted={}
    running=0.0
    for rank,(name,pv) in enumerate(items):
        value=min(1.0,(m-rank)*pv)
        running=max(running,value)
        adjusted[name]=running
    return adjusted


def add_feature_noise(rows: Sequence[Sequence[float]], sd: float,
                      seed: int) -> list[list[float]]:
    rng=Random(seed)
    standardized=standardize_columns(rows)
    return [[v+rng.gauss(0,sd) for v in row] for row in standardized]


def robustness(rows: Sequence[Sequence[float]], levels: Sequence[float]=(0,0.05,0.1,0.2,0.4),
               reps: int=8) -> list[dict[str,float]]:
    base=rdm(rows)
    out=[]
    for sd in levels:
        vals=[]
        for rep in range(reps):
            noisy=add_feature_noise(rows,sd,seed=10000+rep+int(sd*1000))
            vals.append(spearman(upper_triangle(base),upper_triangle(rdm(noisy))))
        out.append({"noise_sd":sd,"mean_rdm_retention":mean(vals),
                    "min":min(vals),"max":max(vals)})
    return out


def feature_dropout_robustness(rows: Sequence[Sequence[float]],
                               fractions: Sequence[float]=(1.0,0.75,0.5,0.25),
                               reps: int=8) -> list[dict[str,float]]:
    """Drop feature channels consistently across systems and compare RDMs."""
    base=rdm(rows)
    width=len(rows[0])
    out=[]
    for fraction in fractions:
        vals=[]
        keep=max(2,int(round(width*fraction)))
        for rep in range(reps):
            rng=Random(22000+rep+int(fraction*1000))
            cols=sorted(rng.sample(range(width),keep))
            reduced=[[row[j] for j in cols] for row in rows]
            vals.append(spearman(upper_triangle(base),upper_triangle(rdm(reduced))))
        out.append({"retained_fraction":fraction,"mean_rdm_retention":mean(vals),
                    "min":min(vals),"max":max(vals)})
    return out


def codon_alias_equivalence(params: Sequence[Params]) -> dict[str,float]:
    """Execute matched probes with two differently named arithmetic registries."""
    default=CodonRegistry()
    alias=CodonRegistry(load="load",add="plus",sub="minus",mul="times",
                        div="divide",power="pow",store="write")
    samples=list(params[:min(5,len(params))])
    errors=[]
    for p in samples:
        for domain in ("acoustic","mechanical"):
            a=simulate_domain(p,domain,registry=default)
            b=simulate_domain(p,domain,registry=alias)
            for fa,fb in ((a.impulse,b.impulse),(a.step,b.step),(a.chirp,b.chirp)):
                errors.append(max(abs(x-y) for x,y in zip(fa,fb)))
    return {"max_abs_output_difference":max(errors) if errors else 0.0,
            "n_system_domain_cases":len(samples)*2,
            "default_chain_acoustic":"ld · mx · ad · mx · ad · st",
            "default_chain_mechanical":"ld · mx · su · mx · su · dv · st",
            "alias_registry":"load · times · plus · minus · divide · write"}

def nonlinear_effect(records: Sequence[SystemRecord]) -> list[dict[str,float]]:
    """Quantify amplitude-dependent deviation from linear scaling.

    Input amplitude ratio is 6.0. A linear system should preserve that ratio;
    deviation indicates compression or amplitude-dependent plant dynamics.
    """
    out=[]
    for rec in records:
        low=rms(rec.low_amp)
        high=rms(rec.high_amp)
        ratio=high/max(low,1e-12)
        out.append({"family_id":rec.family_id,"gain_ratio":ratio,
                    "deviation_from_linear_ratio":abs(ratio/6.0-1.0),
                    "nonlinearity":rec.params.nonlinearity})
    return out


def sample_rate_invariance(params: Sequence[Params], rates: Sequence[float]=(64.0,128.0,256.0),
                           count: int=12) -> list[dict[str,float]]:
    """Compare within-domain response RDMs across matched physical sampling rates.

    Duration stays fixed at eight seconds and all sample counts remain powers of
    two (512/1024/2048). A stable continuous-time pole pair should be represented
    similarly after accounting for the changed sampling interval.
    """
    out=[]
    subset=list(params[:count])
    for domain in ("acoustic","mechanical"):
        matrices={}
        for fs in rates:
            n=int(round(DURATION*fs))
            recs=[simulate_domain(p,domain,fs,n) for p in subset]
            rows=[r.features["spectral"] for r in recs]
            matrices[fs]=rdm(rows)  # type: ignore[arg-type]
        base=matrices[rates[1]]
        for fs in rates:
            out.append({"domain":domain,"sample_rate_hz":fs,
                        "rdm_correlation_vs_128hz":spearman(upper_triangle(base),
                                                              upper_triangle(matrices[fs]))})
    return out


def unit_scale_invariance(params: Sequence[Params], count: int = 12) -> list[dict[str,float]]:
    """Test coordinated changes of measurement units / mechanical mass units.

    Acoustic outputs are multiplied by a common sensor calibration factor.
    Mechanical mass, damping, stiffness, cubic stiffness, and output calibration
    scale together so the dimensionless dynamics are unchanged. The RDM should
    be preserved for features that are intended to be unit-normalized.
    """
    subset=list(params[:count])
    rows=[]
    for domain in ("acoustic","mechanical"):
        base=[simulate_domain(p,domain) for p in subset]
        if domain == "acoustic":
            scaled_params=[Params(p.family_id,p.f0_hz,p.zeta,p.gain*10.0,p.mass,p.nonlinearity)
                           for p in subset]
        else:
            scaled_params=[Params(p.family_id,p.f0_hz,p.zeta,p.gain*10.0,p.mass*10.0,p.nonlinearity)
                           for p in subset]
        scaled=[simulate_domain(p,domain) for p in scaled_params]
        for feature in ("spectral","phase","temporal","step","transfer"):
            A=rdm([r.features[feature] for r in base])  # type: ignore[arg-type]
            B=rdm([r.features[feature] for r in scaled])  # type: ignore[arg-type]
            rows.append({"domain":domain,"feature":feature,
                         "rdm_correlation_after_unit_rescale":spearman(upper_triangle(A),upper_triangle(B))})
    return rows


def build(seed: int=20261104, count: int=40) -> dict:
    params=make_family_params(count,seed)
    acoustic=[simulate_domain(p,"acoustic") for p in params]
    mechanical=[simulate_domain(p,"mechanical") for p in params]
    observer_names=("spectral","phase","temporal","step","modulation","transfer","amplitude","modal")
    matrices={}
    correlations={}
    for observer in observer_names:
        ar=rdm([r.features[observer] for r in acoustic])  # type: ignore[arg-type]
        mr=rdm([r.features[observer] for r in mechanical])  # type: ignore[arg-type]
        matrices[f"acoustic_{observer}"]=ar
        matrices[f"mechanical_{observer}"]=mr
        corr,p=permutation_test(ar,mr,reps=499,seed=seed+len(observer))
        ci=bootstrap_rdm_corr(ar,mr,reps=400,seed=seed+2*len(observer))
        correlations[observer]={"spearman_rdm":corr,"permutation_p":p,
                                "bootstrap_ci95":[ci[0],ci[1]],
                                "paired_profile_retrieval":nearest_partner_accuracy(ar,mr)}
    adjusted=holm_adjust({k:v["permutation_p"] for k,v in correlations.items()})
    for name in correlations:
        correlations[name]["holm_adjusted_p"] = adjusted[name]
    # Cross-observer/domain comparison: the strongest theoretical question is
    # whether different feature lenses in distinct domains recover related RDMs.
    cross_pairs=[]
    for ao in ("spectral","temporal","transfer","modal"):
        for mo in ("spectral","temporal","transfer","modal"):
            A=matrices[f"acoustic_{ao}"]
            B=matrices[f"mechanical_{mo}"]
            cross_pairs.append({"acoustic_observer":ao,"mechanical_observer":mo,
                                "spearman_rdm":spearman(upper_triangle(A),upper_triangle(B))})
    # Unit and gain invariance check: rescale physical units without changing
    # dimensionless natural frequency and damping. The normalized RDM should
    # remain near-identical when signatures exclude absolute amplitude.
    # Gain is already nuisance-normalized in spectral/modal signatures.
    gain_rows=[[v for v in r.features["spectral"]] for r in acoustic]  # type: ignore[union-attr]
    gain_robust=robustness(gain_rows,levels=(0.0,0.05,0.1,0.2,0.4),reps=8)
    feature_dropout=feature_dropout_robustness(gain_rows,reps=8)
    codon_checks=codon_alias_equivalence(params)
    nonlinear_ac=nonlinear_effect(acoustic)
    nonlinear_me=nonlinear_effect(mechanical)
    rate_sweep=sample_rate_invariance(params, rates=(64.0,128.0,256.0), count=min(12,count))
    unit_sweep=unit_scale_invariance(params,count=min(12,count))
    summary={
        "seed":seed,"n_families":count,"n_systems_per_domain":count,
        "sample_rate_hz":FS,"samples":N,"duration_s":DURATION,
        "frequency_range_hz":[min(FREQS),max(FREQS)],
        "observers":list(observer_names),
        "matched_parameter_design":True,
        "domain_models":{
            "acoustic":"second-order digital resonator with pole radius/angle and optional output compression",
            "mechanical":"continuous mass-spring-damper oscillator integrated with RK4 and optional cubic stiffness"},
        "cross_domain_rdm_correlations":correlations,
        "cross_observer_correlations":cross_pairs,
        "noise_robustness_acoustic_spectral":gain_robust,
        "feature_dropout_acoustic_spectral":feature_dropout,
        "codon_execution":codon_checks,
        "nonlinear_response":{
            "expected_linear_high_low_rms_ratio":6.0,
            "acoustic_mean_high_low_rms_ratio":mean(x["gain_ratio"] for x in nonlinear_ac),
            "mechanical_mean_high_low_rms_ratio":mean(x["gain_ratio"] for x in nonlinear_me),
            "acoustic_mean_deviation_from_linear":mean(x["deviation_from_linear_ratio"] for x in nonlinear_ac),
            "mechanical_mean_deviation_from_linear":mean(x["deviation_from_linear_ratio"] for x in nonlinear_me),
            "interpretation":"domain-specific nonlinear stress probe; not a cross-modal perceptual rating"},
        "sample_rate_invariance":rate_sweep,
        "unit_scale_invariance":unit_sweep,
        "controls":{
            "random_pairing_permutation":"permutation_test permutes the mechanical system labels",
            "observer_feature_noise":"standardized Gaussian measurement noise",
            "unit_scale":"sensor gain and mechanical mass vary independently; normalized spectral/modal features are compared separately from amplitude features",
            "time_scale":"sample-rate sweep at 64/128/256 Hz, fixed physical duration and fixed natural frequencies; temporal sampling effects remain visible in raw signals"},
    }
    return {"summary":summary,"params":[asdict(p) for p in params],"matrices":matrices}


def write_csv(path: Path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)


def write_outputs(root: Path, result: dict) -> None:
    (root/"reports").mkdir(parents=True,exist_ok=True)
    (root/"data").mkdir(parents=True,exist_ok=True)
    summary=result["summary"]
    (root/"reports"/"build_09_report.json").write_text(json.dumps(result["summary"],indent=2),encoding="utf-8")
    (root/"reports"/"key_results.json").write_text(json.dumps({
        "n_families":summary["n_families"],
        "cross_domain_rdm_correlations":summary["cross_domain_rdm_correlations"],
        "strongest_cross_observer_pairs":sorted(summary["cross_observer_correlations"],key=lambda x:abs(x["spearman_rdm"]),reverse=True)[:8],
        "noise_robustness":summary["noise_robustness_acoustic_spectral"],
        "feature_dropout":summary["feature_dropout_acoustic_spectral"],
        "codon_execution":summary["codon_execution"],
        "nonlinear_response":summary["nonlinear_response"],
        "sample_rate_invariance":summary["sample_rate_invariance"],
        "unit_scale_invariance":summary["unit_scale_invariance"]},indent=2),encoding="utf-8")
    with (root/"data"/"family_parameters.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(result["params"][0].keys()));w.writeheader();w.writerows(result["params"])
    corr_rows=[{"observer":k,**v} for k,v in summary["cross_domain_rdm_correlations"].items()]
    write_csv(root/"data"/"matched_domain_rdm_correlations.csv",corr_rows,
              ["observer","spearman_rdm","permutation_p","holm_adjusted_p","bootstrap_ci95","paired_profile_retrieval"])
    write_csv(root/"data"/"cross_observer_correlations.csv",summary["cross_observer_correlations"],
              ["acoustic_observer","mechanical_observer","spearman_rdm"])
    write_csv(root/"data"/"noise_robustness.csv",summary["noise_robustness_acoustic_spectral"],
              ["noise_sd","mean_rdm_retention","min","max"])
    write_csv(root/"data"/"sample_rate_invariance.csv",summary["sample_rate_invariance"],
              ["domain","sample_rate_hz","rdm_correlation_vs_128hz"])
    write_csv(root/"data"/"unit_scale_invariance.csv",summary["unit_scale_invariance"],
              ["domain","feature","rdm_correlation_after_unit_rescale"])
    write_csv(root/"data"/"feature_dropout.csv",summary["feature_dropout_acoustic_spectral"],
              ["retained_fraction","mean_rdm_retention","min","max"])
    write_csv(root/"data"/"nonlinear_response_summary.csv",[summary["nonlinear_response"]],
              list(summary["nonlinear_response"].keys()))
    for name,mat in result["matrices"].items():
        path=root/"data"/f"rdm_{name}.csv"
        with path.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f);w.writerow(["family_id"]+list(range(len(mat))))
            for i,row in enumerate(mat):w.writerow([i]+row)


def main() -> None:
    root=Path(__file__).resolve().parent
    result=build()
    write_outputs(root,result)
    print(json.dumps(result["summary"],indent=2))

if __name__=="__main__":
    main()
