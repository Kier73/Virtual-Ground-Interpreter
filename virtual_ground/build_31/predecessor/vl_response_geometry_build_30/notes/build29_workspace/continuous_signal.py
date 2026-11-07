"""Build 29: continuous measurements to observer-relative event candidates.

Standard-library only. No ground-truth boundaries are used by the learner.
This module intentionally separates signal features, boundary hypotheses,
event descriptors, opaque event tokens, and downstream motif discovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence
import cmath
import json
import math
import statistics
import struct
import wave


class SignalError(ValueError):
    pass


@dataclass(frozen=True)
class SignalChannel:
    name: str
    sample_rate: int
    samples: tuple[float, ...]
    original_nyquist_hz: float | None = None

    def __post_init__(self) -> None:
        if not self.name or self.sample_rate <= 0 or not self.samples:
            raise SignalError("channel requires name, positive sample rate and samples")
        if any(not math.isfinite(float(x)) for x in self.samples):
            raise SignalError("samples must be finite")
        if self.original_nyquist_hz is not None and not (0 < self.original_nyquist_hz <= self.sample_rate / 2 + 1e-9):
            raise SignalError("original Nyquist must be positive and no greater than current Nyquist")


@dataclass(frozen=True)
class FrameFeature:
    channel: str
    index: int
    start_sample: int
    time_s: float
    values: Mapping[str, float]


@dataclass(frozen=True)
class BoundaryCandidate:
    frame_index: int
    sample_index: int
    time_s: float
    score: float
    channels_supporting: tuple[str, ...]
    feature_evidence: Mapping[str, float]
    status: str


@dataclass(frozen=True)
class EventSegment:
    start_frame: int
    end_frame: int
    start_sample: int
    end_sample: int
    duration_s: float
    token: str
    descriptor: tuple[float, ...]
    confidence: float


@dataclass
class SegmentationHypothesis:
    threshold_name: str
    boundaries: tuple[int, ...]
    segments: list[EventSegment]
    score: float
    status: str


@dataclass
class SignalAnalysis:
    channels: dict[str, list[FrameFeature]]
    fused_scores: list[float]
    candidates: list[BoundaryCandidate]
    hypotheses: list[SegmentationHypothesis]
    selected: SegmentationHypothesis | None
    vocabulary: dict[str, list[float]]
    diagnostics: dict[str, Any]


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def _fft(values: Sequence[complex]) -> list[complex]:
    n = len(values)
    if n == 0 or n & (n - 1):
        raise SignalError("FFT input length must be a positive power of two")
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
        angle = -2.0 * math.pi / length
        wlen = complex(math.cos(angle), math.sin(angle))
        half = length // 2
        for start in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(start, start + half):
                u, v = a[k], a[k + half] * w
                a[k], a[k + half] = u + v, u - v
                w *= wlen
        length *= 2
    return a


def read_wav_channels(path: str) -> tuple[int, list[SignalChannel]]:
    """Read PCM 8/16/24/32 or IEEE float 32/64 WAV, preserving channels."""
    with open(path, "rb") as f:
        head = f.read(12)
        if len(head) != 12 or head[:4] not in (b"RIFF", b"RF64") or head[8:12] != b"WAVE":
            raise SignalError("not a RIFF/RF64 WAVE file")
        fmt = data = None
        while True:
            h = f.read(8)
            if not h:
                break
            if len(h) != 8:
                raise SignalError("malformed WAV chunk header")
            cid, size = h[:4], struct.unpack("<I", h[4:])[0]
            payload = f.read(size)
            if len(payload) != size:
                raise SignalError("truncated WAV chunk")
            if size & 1:
                f.read(1)
            if cid == b"fmt ":
                fmt = payload
            elif cid == b"data":
                data = payload
        if fmt is None or data is None or len(fmt) < 16:
            raise SignalError("WAV missing fmt/data")
        af, channels, fs, _, block_align, bits = struct.unpack("<HHIIHH", fmt[:16])
        if af == 0xFFFE and len(fmt) >= 40:
            af = struct.unpack("<H", fmt[24:26])[0]
        bps = (bits + 7) // 8
        if channels < 1 or block_align != channels * bps or len(data) % block_align:
            raise SignalError("invalid channel/block alignment")
        frames = len(data) // block_align
        samples: list[list[float]] = [[] for _ in range(channels)]
        if af == 1 and bits == 8:
            for i in range(frames):
                for c in range(channels):
                    samples[c].append((data[i*block_align+c]-128)/128.0)
        elif af == 1 and bits == 16:
            vals = struct.unpack("<" + "h"*(frames*channels), data)
            for i, v in enumerate(vals): samples[i % channels].append(v/32768.0)
        elif af == 1 and bits == 24:
            for i in range(frames*channels):
                b = data[i*3:(i+1)*3]
                v = int.from_bytes(b, "little", signed=False)
                if v & 0x800000: v -= 1 << 24
                samples[i % channels].append(v/float(1 << 23))
        elif af == 1 and bits == 32:
            vals = struct.unpack("<" + "i"*(frames*channels), data)
            for i, v in enumerate(vals): samples[i % channels].append(v/float(1 << 31))
        elif af == 3 and bits in (32, 64):
            code = "f" if bits == 32 else "d"
            vals = struct.unpack("<" + code*(frames*channels), data)
            for i, v in enumerate(vals): samples[i % channels].append(float(v))
        else:
            raise SignalError(f"unsupported WAV encoding format={af} bits={bits}")
        out = [SignalChannel(f"channel_{c}", fs, tuple(samples[c])) for c in range(channels)]
        return fs, out


def write_wav_channels(path: str, sample_rate: int, channels: Sequence[Sequence[float]], bits: int = 16) -> None:
    if not channels or sample_rate <= 0 or bits not in (16, 24, 32):
        raise SignalError("invalid WAV output configuration")
    n = len(channels[0])
    if n == 0 or any(len(c) != n for c in channels):
        raise SignalError("channels must have equal nonzero lengths")
    with wave.open(path, "wb") as w:
        w.setnchannels(len(channels)); w.setsampwidth(bits // 8); w.setframerate(sample_rate)
        raw = bytearray()
        for i in range(n):
            for ch in channels:
                x = max(-1.0, min(1.0, float(ch[i])))
                if bits == 16:
                    raw.extend(struct.pack("<h", int(round(x * 32767))))
                elif bits == 24:
                    v = int(round(x * ((1 << 23) - 1)))
                    raw.extend(v.to_bytes(3, "little", signed=True))
                else:
                    raw.extend(struct.pack("<i", int(round(x * ((1 << 31) - 1)))))
        w.writeframes(bytes(raw))


def _haar_energy(frame: Sequence[float], max_level: int = 4) -> list[float]:
    x = list(frame)
    out: list[float] = []
    for level in range(max_level):
        if len(x) < 4:
            break
        approx, detail = [], []
        for i in range(0, len(x)-1, 2):
            a, b = x[i], x[i+1]
            approx.append((a+b)/math.sqrt(2.0))
            detail.append((a-b)/math.sqrt(2.0))
        out.append(sum(v*v for v in detail)/max(1, len(detail)))
        x = approx
    total = sum(out) + 1e-20
    return [v/total for v in out]


def _frame_features(channel: SignalChannel, frame_size: int, hop: int) -> list[FrameFeature]:
    x, fs = channel.samples, channel.sample_rate
    if frame_size < 32 or frame_size & (frame_size-1) or hop < 1:
        raise SignalError("frame_size must be power of two >=32 and hop positive")
    if len(x) < frame_size:
        raise SignalError("signal shorter than one analysis frame")
    starts = list(range(0, len(x)-frame_size+1, hop))
    out: list[FrameFeature] = []
    prev_power: list[float] | None = None
    prev_phase: float | None = None
    prev_dom: int | None = None
    win = [0.5 - 0.5*math.cos(2*math.pi*i/(frame_size-1)) for i in range(frame_size)]
    for fi, start in enumerate(starts):
        raw = x[start:start+frame_size]
        mean = sum(raw)/len(raw)
        centered = [v-mean for v in raw]
        rms = math.sqrt(sum(v*v for v in centered)/len(centered))
        peak = max(abs(v) for v in centered)
        zcr = sum((a < 0 <= b) or (b < 0 <= a) for a,b in zip(centered, centered[1:])) / max(1, len(centered)-1)
        windowed = [complex(centered[i]*win[i], 0.0) for i in range(frame_size)]
        spec = _fft(windowed)[:frame_size//2+1]
        power = [z.real*z.real+z.imag*z.imag for z in spec]
        total = sum(power)+1e-20
        probs = [v/total for v in power]
        centroid = sum((i/(frame_size/2))*p for i,p in enumerate(probs))
        flatness = math.exp(sum(math.log(max(p,1e-30)) for p in probs)/len(probs)) / (sum(probs)/len(probs)+1e-20)
        bands = []
        for lo, hi in ((0.0,.08),(.08,.16),(.16,.28),(.28,.40),(.40,.50)):
            i0=max(0,int(lo*frame_size)); i1=min(len(power),max(i0+1,int(hi*frame_size)))
            bands.append(sum(power[i0:i1])/total)
        flux = 0.0 if prev_power is None else 0.5*sum(abs(a-b) for a,b in zip(probs, prev_power))
        prev_power = probs
        # Relative dominant-bin phase advance is retained as a separate, low-trust cue.
        dom = max(range(1,len(spec)), key=lambda i: abs(spec[i])) if len(spec)>1 else 0
        phase = cmath.phase(spec[dom]) if dom else 0.0
        phase_reliability = abs(spec[dom]) / (math.sqrt(total)+1e-20) if dom else 0.0
        if prev_phase is None or prev_dom is None or dom != prev_dom:
            phase_innovation = 0.0
        else:
            # Remove the deterministic phase advance of a stationary Fourier bin.
            delta = phase - prev_phase + 2.0*math.pi*dom*hop/frame_size
            phase_innovation = math.atan2(math.sin(delta), math.cos(delta))/math.pi
        prev_phase, prev_dom = phase, dom
        haar = _haar_energy(centered)
        values = {
            "log_rms": math.log(max(rms,1e-12)), "peak_rms": peak/max(rms,1e-12),
            "zcr": zcr, "centroid_nyquist": centroid, "spectral_flatness": flatness,
            "spectral_flux": flux, "phase_innovation": phase_innovation,
            "phase_reliability": phase_reliability, "dominant_bin": float(dom),
        }
        for i,v in enumerate(bands): values[f"band_{i}"] = v
        for i,v in enumerate(haar): values[f"haar_{i}"] = v
        out.append(FrameFeature(channel.name,fi,start,start/fs,values))
    return out


def _median_abs_dev(vals: Sequence[float]) -> float:
    if not vals: return 0.0
    m = statistics.median(vals)
    return statistics.median(abs(v-m) for v in vals)


def _feature_distance(a: Mapping[str,float], b: Mapping[str,float], keys: Sequence[str], scales: Mapping[str,float]) -> tuple[float,dict[str,float]]:
    ev={}
    for k in keys:
        den=max(scales.get(k,1.0),1e-3)
        if k == "dominant_phase":
            delta=abs(a[k]-b[k]); delta=min(delta,2*math.pi-delta)/math.pi
        else:
            delta=abs(a[k]-b[k])/den
        ev[k]=min(5.0,delta)
    return math.sqrt(sum(v*v for v in ev.values())/max(1,len(ev))), ev


def _js_divergence(a: Sequence[float], b: Sequence[float]) -> float:
    """Jensen-Shannon divergence in nats for normalized nonnegative vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    sa=sum(max(0.0,x) for x in a)+1e-20
    sb=sum(max(0.0,x) for x in b)+1e-20
    pa=[max(0.0,x)/sa for x in a]; pb=[max(0.0,x)/sb for x in b]
    m=[(x+y)/2 for x,y in zip(pa,pb)]
    return 0.5*sum(x*math.log(x/y) for x,y in zip(pa,m) if x>0) + 0.5*sum(y*math.log(y/z) for y,z in zip(pb,m) if y>0)


def _mean_feature(frames: Sequence[FrameFeature], key: str) -> float:
    return statistics.fmean(f.values[key] for f in frames) if frames else 0.0


def _within_js(frames: Sequence[FrameFeature], keys: Sequence[str]) -> float:
    rows=[[f.values[k] for k in keys] for f in frames]
    vals=[_js_divergence(rows[i],rows[i+1]) for i in range(len(rows)-1)]
    return statistics.fmean(vals) if vals else 0.0


def _phase_transition_score(samples: Sequence[float], boundary: int, dominant_bin: float,
                            frame_size: int, fs: int) -> float:
    """Detect a localized phase discontinuity using a local sinusoid recurrence.

    The dominant left-window Fourier bin defines x[n]=2cos(w)x[n-1]-x[n-2].
    A phase jump creates a prediction residual at the proposed boundary. The
    residual is normalized against the recent pre-boundary residual distribution.
    """
    b=int(boundary); k=int(round(dominant_bin))
    if k<=0 or b<40 or b>=len(samples)-1:
        return 0.0
    omega=2.0*math.pi*k/frame_size
    coeff=2.0*math.cos(omega)
    resid=[]
    for n in range(max(2,b-32),b):
        resid.append(abs(float(samples[n])-coeff*float(samples[n-1])+float(samples[n-2])))
    if len(resid)<8:
        return 0.0
    med=statistics.median(resid)
    mad=statistics.median(abs(x-med) for x in resid)
    local_rms=math.sqrt(statistics.fmean(float(samples[n])**2 for n in range(max(0,b-32),b))+1e-20)
    current=abs(float(samples[b])-coeff*float(samples[b-1])+float(samples[b-2]))
    z=(current-med)/(1.4826*mad+0.015*local_rms+1e-12)
    return max(0.0,min(1.0,(z-3.0)/12.0))


def _analyze_channel(frames: Sequence[FrameFeature], observer_view: str = "combined",
                     samples: Sequence[float] | None = None, fs: int = 1,
                     frame_size: int = 256, hop: int = 64) -> tuple[list[float], list[dict[str,float]], dict[str,float]]:
    """Persistent change score, not adjacent-frame novelty.

    Compare short windows on either side of a candidate boundary. This rejects
    much of the frame-to-frame fluctuation produced by stationary broadband
    noise, while retaining persistent spectral/envelope changes.
    """
    if observer_view not in ("harmonic", "temporal", "combined"):
        raise SignalError("observer_view must be harmonic, temporal or combined")
    n=len(frames); width=3
    keys=[f"band_{i}" for i in range(5)]+["log_rms","zcr","centroid_nyquist"]
    scales={k:max(1.4826*_median_abs_dev([f.values[k] for f in frames]),0.03) for k in keys}
    scores=[0.0]*n; evidence=[{} for _ in range(n)]
    for i in range(1,n):
        left=frames[max(0,i-width):i]
        right=frames[i:min(n,i+width)]
        if len(left)<2 or len(right)<2:
            continue
        bands=[f"band_{j}" for j in range(5)]
        lb=[_mean_feature(left,k) for k in bands]
        rb=[_mean_feature(right,k) for k in bands]
        spectral_js=_js_divergence(lb,rb)
        spectral_within=.5*(_within_js(left,bands)+_within_js(right,bands))
        spectral_contrast=max(0.0,spectral_js-spectral_within)
        lh=[_mean_feature(left,f"haar_{j}") for j in range(4)]
        rh=[_mean_feature(right,f"haar_{j}") for j in range(4)]
        haar_keys=[f"haar_{j}" for j in range(4)]
        wavelet_js=_js_divergence(lh,rh)
        wavelet_within=.5*(_within_js(left,haar_keys)+_within_js(right,haar_keys))
        wavelet_contrast=max(0.0,wavelet_js-wavelet_within)
        env_delta=abs(_mean_feature(right,"log_rms")-_mean_feature(left,"log_rms"))
        env_noise=.5*((statistics.pstdev([f.values["log_rms"] for f in left]) if len(left)>1 else 0.0)+
                      (statistics.pstdev([f.values["log_rms"] for f in right]) if len(right)>1 else 0.0))
        env_contrast=max(0.0,env_delta-1.5*env_noise)
        env_score=min(1.0,env_contrast/0.25)
        zcr_delta=abs(_mean_feature(right,"zcr")-_mean_feature(left,"zcr"))
        zcr_noise=.5*((statistics.pstdev([f.values["zcr"] for f in left]) if len(left)>1 else 0.0)+
                      (statistics.pstdev([f.values["zcr"] for f in right]) if len(right)>1 else 0.0))
        zcr_score=min(1.0,max(0.0,zcr_delta-1.5*zcr_noise)/max(scales["zcr"],0.04))
        centroid_delta=abs(_mean_feature(right,"centroid_nyquist")-_mean_feature(left,"centroid_nyquist"))
        centroid_score=min(1.0,centroid_delta*4.0)
        phase_window=frames[max(1,i-2):min(n,i+2)]
        phase_jump=max((abs(f.values["phase_innovation"]) for f in phase_window
                        if f.values["phase_reliability"]>.35),default=0.0)
        phase_residual=0.0
        if samples is not None and frames[i-1].values["phase_reliability"]>.35:
            phase_residual=_phase_transition_score(samples,frames[i].start_sample,
                frames[i-1].values["dominant_bin"],frame_size,fs)
        phase_score=max(min(1.0,phase_jump),phase_residual)
        harmonic=.60*min(1.0,spectral_contrast/math.log(2))+ .10*min(1.0,wavelet_contrast/math.log(2)) + .07*centroid_score + .23*phase_score
        temporal=.72*env_score+.18*zcr_score+.10*min(1.0,wavelet_contrast/math.log(2))
        if observer_view=="harmonic": score=harmonic
        elif observer_view=="temporal": score=temporal
        else: score=.78*harmonic+.22*temporal
        scores[i]=score
        evidence[i]={"spectral_js":spectral_js,"spectral_within_js":spectral_within,"spectral_contrast":spectral_contrast,
                     "wavelet_js":wavelet_js,"wavelet_within_js":wavelet_within,"wavelet_contrast":wavelet_contrast,"envelope_change":env_delta,
                     "envelope_score":env_score,"zcr_change":zcr_delta,"centroid_change":centroid_delta,"phase_jump":phase_jump,"phase_residual_score":phase_residual,
                     "harmonic_score":harmonic,"temporal_score":temporal}
    return scores,evidence,scales


def _local_maxima(scores: Sequence[float], min_gap: int) -> list[int]:
    out=[]; last=-10**9
    for i in range(1,len(scores)-1):
        if scores[i] >= scores[i-1] and scores[i] > scores[i+1] and i-last>=min_gap:
            out.append(i); last=i
    return out


def _threshold_hypotheses(scores: Sequence[float], evidence: Sequence[Mapping[str,float]],
                          channels: Sequence[str], frame_size: int, hop: int, fs: int,
                          thresholds: Sequence[tuple[str,float]], min_gap: int=2) -> tuple[list[BoundaryCandidate],list[tuple[str,tuple[int,...],float]]]:
    peaks=_local_maxima(scores,min_gap)
    med=statistics.median(scores[1:]) if len(scores)>1 else 0.0
    mad=_median_abs_dev(scores[1:]) if len(scores)>1 else 0.0
    nominal_mult=next((m for name,m in thresholds if name=="nominal"),0.75)
    nominal_threshold=max(0.075,med+nominal_mult*max(mad,0.02))
    candidates=[]
    for i in peaks:
        ev=dict(evidence[i])
        score=scores[i]
        support=[]
        for ch in channels:
            ch_score=max(ev.get(f"{ch}.harmonic_score",0.0),ev.get(f"{ch}.temporal_score",0.0))
            if ch_score >= max(0.06,nominal_threshold*0.65): support.append(ch)
        status="supported_candidate" if score>=nominal_threshold else "subthreshold_candidate"
        candidates.append(BoundaryCandidate(i,i*hop,i*hop/fs,score,tuple(support),ev,status))
    hyps=[]
    for name,mult in thresholds:
        floor={"sensitive":0.025,"nominal":0.075,"conservative":0.16}.get(name,0.075)
        threshold=max(floor,med+mult*max(mad,0.02))
        selected=tuple(i for i in peaks if scores[i]>=threshold)
        hyps.append((name,selected,threshold))
    return candidates,hyps


def _aggregate_descriptor(frames: Sequence[FrameFeature], start: int, end: int,
                          token_view: str = "harmonic", baseline_log_rms: float = 0.0) -> tuple[float,...]:
    # Discard edge frames that may straddle an inferred boundary.
    middle=[f for f in frames[start:end] if start < f.index < end-1]
    if not middle: middle=list(frames[start:end])
    harmonic_keys=[f"band_{i}" for i in range(5)]+[f"haar_{i}" for i in range(4)]+["centroid_nyquist","zcr"]
    harmonic=[statistics.fmean(f.values.get(k,0.0) for f in middle) for k in harmonic_keys]
    lr=[f.values["log_rms"]-baseline_log_rms for f in middle]
    temporal=[statistics.fmean(lr), statistics.pstdev(lr) if len(lr)>1 else 0.0,
              statistics.fmean(f.values["peak_rms"] for f in middle),
              statistics.fmean(f.values["zcr"] for f in middle)]
    if token_view=="harmonic": return tuple(harmonic)
    if token_view=="temporal": return tuple(temporal)
    if token_view=="combined": return tuple(harmonic+temporal)
    raise SignalError("token_view must be harmonic, temporal or combined")


def _cluster_descriptors(descriptors: Sequence[tuple[float,...]], tolerance: float=0.12) -> tuple[list[str],dict[str,list[float]]]:
    prototypes: list[list[float]]=[]; counts: list[int]=[]; labels=[]
    for d in descriptors:
        best=None; best_dist=float("inf")
        for i,p in enumerate(prototypes):
            # Euclidean distance; descriptor components are energy fractions / normalized centroid.
            dist=math.sqrt(sum((x-y)**2 for x,y in zip(d,p))/len(d))
            if dist<best_dist: best_dist=dist; best=i
        if best is None or best_dist>tolerance:
            prototypes.append(list(d)); counts.append(1); labels.append(f"evt_{len(prototypes):03d}")
        else:
            counts[best]+=1
            # Online centroid update, deterministic in stream order.
            prototypes[best]=[(p*(counts[best]-1)+x)/counts[best] for p,x in zip(prototypes[best],d)]
            labels.append(f"evt_{best+1:03d}")
    return labels,{f"evt_{i+1:03d}":p for i,p in enumerate(prototypes)}


def analyze_signals(channels: Sequence[SignalChannel], *, frame_size: int=256, hop: int=64,
                    thresholds: Sequence[tuple[str,float]]=(("sensitive",0.25),("nominal",0.75),("conservative",1.5)),
                    min_gap_frames: int=4, token_tolerance: float=0.12,
                    observer_view: str="combined", token_view: str="harmonic") -> SignalAnalysis:
    if not channels: raise SignalError("at least one signal channel is required")
    rates={c.sample_rate for c in channels}
    if len(rates)!=1: raise SignalError("channels must share sample rate; resample explicitly before fusion")
    if any(len(c.samples)!=len(channels[0].samples) for c in channels):
        raise SignalError("channels must be aligned to equal sample lengths for this build")
    fs=channels[0].sample_rate
    per_channel={}; per_score={}; per_evidence={}; scales={}
    for c in channels:
        fr=_frame_features(c,frame_size,hop); per_channel[c.name]=fr
        s,e,sc=_analyze_channel(fr,observer_view,c.samples,c.sample_rate,frame_size,hop); per_score[c.name]=s; per_evidence[c.name]=e; scales[c.name]=sc
    n=min(len(x) for x in per_score.values())
    # Max-pool across observers: one channel can expose an event hidden by another's transfer function.
    fused=[max(per_score[c.name][i] for c in channels) for i in range(n)]
    fused_ev=[]
    for i in range(n):
        fused_ev.append({f"{c.name}.{k}":v for c in channels for k,v in per_evidence[c.name][i].items()})
    candidates, raw_hyps=_threshold_hypotheses(fused,fused_ev,[c.name for c in channels],frame_size,hop,fs,thresholds,min_gap_frames)
    results=[]
    for name,bounds,threshold in raw_hyps:
        edges=(0,)+bounds+(n,)
        spans=[(a,b) for a,b in zip(edges,edges[1:]) if b-a>=1]
        # Preserve each observer's feature coordinates as a separate block in the joint descriptor.
        # Baseline-centering is channel-specific so constant sensor gain is not mistaken for event identity.
        baselines={c.name:statistics.median(f.values["log_rms"] for f in per_channel[c.name]) for c in channels}
        desc=[]
        for a,b in spans:
            joint=[]
            for c in channels:
                joint.extend(_aggregate_descriptor(per_channel[c.name],a,b,token_view,baselines[c.name]))
            desc.append(tuple(joint))
        labels,vocab=_cluster_descriptors(desc,token_tolerance)
        segs=[]
        for (a,b),d,label in zip(spans,desc,labels):
            conf=statistics.fmean(fused[a:b]) if b>a else 0.0
            start_sample=min(len(channels[0].samples),a*hop)
            end_sample=min(len(channels[0].samples),b*hop)
            segs.append(EventSegment(a,b,start_sample,end_sample,(end_sample-start_sample)/fs, label,d,conf))
        # Penalize excessive segmentation; retain each threshold as a separate hypothesis.
        objective=sum(fused[i] for i in bounds)-0.15*len(bounds)
        results.append(SegmentationHypothesis(name,bounds,segs,objective,"candidate"))
    # Nominal is selected only as a working view; alternatives remain available.
    selected=next((h for h in results if h.threshold_name=="nominal"),results[0] if results else None)
    # Joint vocabulary uses nominal descriptors only, labels remain opaque.
    vocabulary={}
    if selected:
        vocabulary={}
        for seg in selected.segments:
            vocabulary.setdefault(seg.token,list(seg.descriptor))
    diag={
        "sample_rate_hz":fs,"sample_count":len(channels[0].samples),"frame_size":frame_size,"hop":hop,
        "observer_view":observer_view,"token_view":token_view,
        "frame_count":n,"channels":[c.name for c in channels],"feature_views":["envelope","STFT_harmonic_bands","spectral_flux","Haar_detail_energy","dominant_phase_reliability"],
        "channel_scales":scales,"threshold_hypotheses":{h.threshold_name:{"boundary_count":len(h.boundaries),"objective":h.score} for h in results},
        "selected_threshold":"nominal" if selected else None,
        "boundary_evidence_is_ground_truth_free":True,
    }
    return SignalAnalysis(per_channel,fused,candidates,results,selected,vocabulary,diag)


def event_tokens_for_build28(analysis: SignalAnalysis, trace_id: str="signal") -> list[str]:
    if analysis.selected is None: return []
    return [seg.token for seg in analysis.selected.segments]


def analysis_to_dict(analysis: SignalAnalysis) -> dict[str,Any]:
    return {
        "diagnostics":analysis.diagnostics,
        "candidates":[{"frame_index":c.frame_index,"sample_index":c.sample_index,"time_s":c.time_s,"score":c.score,"channels_supporting":list(c.channels_supporting),"feature_evidence":dict(c.feature_evidence),"status":c.status} for c in analysis.candidates],
        "hypotheses":[{"threshold":h.threshold_name,"boundaries":list(h.boundaries),"score":h.score,"segments":[{"start_frame":s.start_frame,"end_frame":s.end_frame,"start_sample":s.start_sample,"end_sample":s.end_sample,"duration_s":s.duration_s,"token":s.token,"descriptor":list(s.descriptor),"confidence":s.confidence} for s in h.segments]} for h in analysis.hypotheses],
        "selected_token_stream":event_tokens_for_build28(analysis),"vocabulary":analysis.vocabulary,
    }
