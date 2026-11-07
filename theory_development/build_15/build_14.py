#!/usr/bin/env python3
"""Build 14: paired acoustic / throat-vibration response geometry with temporal emission.

Core analysis uses only the Python standard library. It intentionally omits
transcripts, gender and direct speaker identifiers from written outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import secrets
import json
import math
import os
import random
import statistics
import struct
import wave
import temporal_geometry
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SPLIT_NAMES = {"train", "dev", "test"}
_PAIR_SALT = secrets.token_bytes(32)  # ephemeral; never written to disk
COMMON_BANDS = ((80.0, 250.0), (250.0, 500.0), (500.0, 1000.0),
                (1000.0, 2000.0), (2000.0, 3500.0))
FEATURE_VIEWS = {
    "shared_spectral": ("centroid_common_hz", "rolloff85_common_hz",
                        "band_80_250", "band_250_500", "band_500_1000",
                        "band_1000_2000", "band_2000_3500", "flatness_common"),
    "temporal": ("log_rms", "crest_factor", "zcr", "envelope_cv",
                 "envelope_modulation"),
    "periodicity": ("f0_median_hz", "f0_iqr_hz", "voiced_fraction", "periodicity"),
    "combined_common": ("log_rms", "zcr", "centroid_common_hz", "rolloff85_common_hz",
                        "band_80_250", "band_250_500", "band_500_1000",
                        "band_1000_2000", "band_2000_3500", "flatness_common",
                        "f0_median_hz", "voiced_fraction", "periodicity", "envelope_cv"),
    # Affine-clock-invariant event-interval shape descriptors.
    "temporal_emission": ("event_interval_cv", "event_interval_entropy",
                           "event_interval_q10_norm", "event_interval_q25_norm",
                           "event_interval_q75_norm",
                           "event_interval_q90_norm", "event_mark_cv_norm"),
    # Absolute rates are deliberately kept separate from normalized event shape.
    "temporal_rate": ("event_rate_hz", "event_interval_median_s",
                      "envelope_modulation", "envelope_cv"),
}


@dataclass
class WavData:
    sample_rate: int
    samples: list[float]
    channels: int
    encoding: str
    bits_per_sample: int
    frames: int


def _read_exact(f, n: int) -> bytes:
    b = f.read(n)
    if len(b) != n:
        raise ValueError("Unexpected end of WAV file")
    return b


def read_wav(path: str | Path) -> WavData:
    """Read mono PCM 8/16/24/32-bit or IEEE float 32/64-bit WAV."""
    path = Path(path)
    with path.open("rb") as f:
        head = _read_exact(f, 12)
        if head[:4] not in (b"RIFF", b"RF64") or head[8:12] != b"WAVE":
            raise ValueError(f"Not a RIFF/RF64 WAVE file: {path}")
        fmt = None
        data = None
        while True:
            chunk_head = f.read(8)
            if not chunk_head:
                break
            if len(chunk_head) != 8:
                raise ValueError("Malformed WAV chunk header")
            cid, size = chunk_head[:4], struct.unpack("<I", chunk_head[4:])[0]
            chunk = _read_exact(f, size)
            if size & 1:
                f.read(1)
            if cid == b"fmt ":
                if size < 16:
                    raise ValueError("WAV fmt chunk too short")
                fmt = chunk
            elif cid == b"data":
                data = chunk
        if fmt is None or data is None:
            raise ValueError("WAV missing fmt or data chunk")
        audio_format, channels, sample_rate, _, block_align, bits = struct.unpack("<HHIIHH", fmt[:16])
        if audio_format == 0xFFFE and len(fmt) >= 40:
            # WAVE_FORMAT_EXTENSIBLE: first 16 bits of SubFormat GUID identify PCM/float.
            audio_format = struct.unpack("<H", fmt[24:26])[0]
        if channels != 1:
            raise ValueError(f"Expected mono channel, found {channels}: {path}")
        bytes_per_sample = (bits + 7) // 8
        if block_align != bytes_per_sample:
            raise ValueError("Unexpected block alignment for mono WAV")
        frames = len(data) // bytes_per_sample
        if frames <= 0:
            raise ValueError("WAV contains no samples")
        if audio_format == 3 and bits == 32:
            samples = list(struct.unpack("<" + "f" * frames, data[:frames * 4]))
            encoding = "ieee_float"
        elif audio_format == 3 and bits == 64:
            samples = list(struct.unpack("<" + "d" * frames, data[:frames * 8]))
            encoding = "ieee_float"
        elif audio_format == 1 and bits == 8:
            samples = [(v - 128) / 128.0 for v in data[:frames]]
            encoding = "pcm"
        elif audio_format == 1 and bits == 16:
            vals = struct.unpack("<" + "h" * frames, data[:frames * 2])
            samples = [v / 32768.0 for v in vals]
            encoding = "pcm"
        elif audio_format == 1 and bits == 24:
            samples = []
            for i in range(0, frames * 3, 3):
                v = int.from_bytes(data[i:i + 3], "little", signed=False)
                if v & 0x800000:
                    v -= 1 << 24
                samples.append(v / float(1 << 23))
            encoding = "pcm"
        elif audio_format == 1 and bits == 32:
            vals = struct.unpack("<" + "i" * frames, data[:frames * 4])
            samples = [v / float(1 << 31) for v in vals]
            encoding = "pcm"
        else:
            raise ValueError(f"Unsupported WAV encoding format={audio_format}, bits={bits}")
    if not all(math.isfinite(x) for x in samples):
        raise ValueError(f"Non-finite samples in {path}")
    return WavData(sample_rate, samples, channels, encoding, bits, frames)


def _safe_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _channel_meta(meta: dict, key: str) -> dict:
    value = meta.get(key, {}) if isinstance(meta, dict) else {}
    return value if isinstance(value, dict) else {}


def _opaque_key(parts: Sequence[str]) -> str:
    return hashlib.sha256(_PAIR_SALT + "\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def discover_pairs(root: str | Path, split: str = "test") -> list[dict]:
    """Find documented TAPS file-release pairs; omit transcript/demographic data."""
    root = Path(root).resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    throat_files = sorted(root.rglob("throat_microphone.wav"))
    pairs = []
    for throat in throat_files:
        acoustic = throat.with_name("acoustic_microphone.wav")
        if not acoustic.exists():
            continue
        meta = _safe_json(throat.with_name("features.json"))
        # Standard release: <split>/<speaker_id>/<sentence_id>/channel.wav.
        rel = throat.relative_to(root)
        parts = rel.parts
        present_splits = [part for part in parts if part in SPLIT_NAMES]
        if present_splits and present_splits[0] != split:
            continue
        if len(parts) >= 3:
            speaker_raw, utterance_raw = parts[-3], parts[-2]
        elif len(parts) >= 2:
            speaker_raw, utterance_raw = parts[-2], throat.parent.name
        else:
            speaker_raw, utterance_raw = "unknown-speaker", throat.parent.name
        # Keep raw speaker key only in memory for within-speaker RDMs.
        speaker_internal = str(meta.get("speaker_id") or speaker_raw)
        utterance_internal = str(meta.get("sentence_id") or utterance_raw)
        pair_key = _opaque_key([split, speaker_internal, utterance_internal])
        tm = _channel_meta(meta, "throat_microphone")
        am = _channel_meta(meta, "acoustic_microphone")
        pairs.append({
            "pair_key": pair_key,
            "speaker_internal": speaker_internal,
            "utterance_internal": utterance_internal,
            "throat_path": throat,
            "acoustic_path": acoustic,
            "metadata_path": throat.with_name("features.json"),
            "metadata": meta,
            "throat_meta": tm,
            "acoustic_meta": am,
        })
    if not pairs:
        raise FileNotFoundError(
            f"No paired TAPS WAVs found under {root}. Expected */*/throat_microphone.wav "
            "and sibling acoustic_microphone.wav files."
        )
    # Reject duplicate pair keys, which usually indicate repeated or ambiguous files.
    keys = [p["pair_key"] for p in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate speaker/utterance pairs detected")
    return pairs


def next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def fft_inplace(a: list[complex]) -> None:
    """Iterative radix-2 Cooley-Tukey FFT; input length must be a power of two."""
    n = len(a)
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
        half = length >> 1
        for i in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(i, i + half):
                u, v = a[k], a[k + half] * w
                a[k], a[k + half] = u + v, u - v
                w *= wlen
        length <<= 1


def _percentile(values: Sequence[float], p: float) -> float:
    vals = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not vals:
        return 0.0
    if len(vals) == 1:
        return vals[0]
    x = (len(vals) - 1) * p
    lo = int(math.floor(x)); hi = int(math.ceil(x))
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - x) + vals[hi] * (x - lo)


def _median(values: Sequence[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.median(vals) if vals else 0.0


def _autocorr_pitch(frame: Sequence[float], fs: int) -> tuple[float, float]:
    """Return F0 and normalized periodicity from a frame; zeros if unvoiced/uncertain."""
    n = len(frame)
    if n < 64:
        return 0.0, 0.0
    mean = sum(frame) / n
    x = [v - mean for v in frame]
    energy = sum(v * v for v in x)
    if energy <= 1e-12:
        return 0.0, 0.0
    min_lag = max(1, int(fs / 400.0))
    max_lag = min(n // 2, int(fs / 60.0))
    best_lag, best = 0, -1.0
    for lag in range(min_lag, max_lag + 1):
        num = 0.0
        left = 0.0
        right = 0.0
        for i in range(n - lag):
            a, b = x[i], x[i + lag]
            num += a * b
            left += a * a
            right += b * b
        den = math.sqrt(max(left * right, 1e-20))
        corr = num / den
        if corr > best:
            best, best_lag = corr, lag
    if best_lag and best >= 0.35:
        return fs / best_lag, max(0.0, min(1.0, best))
    return 0.0, max(0.0, best)


def _frame_spectrum(frame: Sequence[float], fs: int) -> tuple[list[float], list[float]]:
    nfft = next_power_of_two(max(256, len(frame)))
    windowed = []
    n = len(frame)
    mean = sum(frame) / n
    for i, x in enumerate(frame):
        w = 0.54 - 0.46 * math.cos(2.0 * math.pi * i / max(1, n - 1))
        windowed.append(complex((x - mean) * w, 0.0))
    windowed.extend([0j] * (nfft - n))
    fft_inplace(windowed)
    power = [(z.real * z.real + z.imag * z.imag) for z in windowed[:nfft // 2 + 1]]
    freqs = [i * fs / nfft for i in range(nfft // 2 + 1)]
    return freqs, power


def _spectrum_summary(samples: Sequence[float], fs: int, max_frames: int = 32,
                      valid_nyquist_hz: float | None = None) -> dict:
    frame_len = max(128, int(round(0.025 * fs)))
    hop = max(1, int(round(0.040 * fs)))
    starts = list(range(0, max(1, len(samples) - frame_len + 1), hop))
    if len(starts) > max_frames:
        stride = len(starts) / max_frames
        starts = [starts[min(len(starts)-1, int(i * stride))] for i in range(max_frames)]
    powers = None
    freqs_ref = None
    spectra = []
    f0s, periodicities = [], []
    for frame_no, start in enumerate(starts):
        frame = samples[start:start + frame_len]
        if len(frame) < frame_len:
            continue
        freqs, power = _frame_spectrum(frame, fs)
        if powers is None:
            powers = [0.0] * len(power)
            freqs_ref = freqs
        for i, v in enumerate(power):
            powers[i] += v
        # Pitch is evaluated on every fourth analysis frame to bound cost.
        if frame_no % 4 == 0:
            pitch_frame = frame
            pitch_fs = fs
            if fs >= 16000:
                # Pairwise averaging before 2:1 decimation retains the F0 band.
                pitch_frame = [(frame[i] + frame[i + 1]) * 0.5 for i in range(0, len(frame) - 1, 2)]
                pitch_fs = fs // 2
            f0, periodicity = _autocorr_pitch(pitch_frame, pitch_fs)
            if f0 > 0:
                f0s.append(f0)
            periodicities.append(periodicity)
    if not powers or freqs_ref is None:
        raise ValueError("Signal too short for spectral analysis")
    powers = [v / max(1, len(starts)) for v in powers]
    # Resampling/upsampling does not increase the original sensor bandwidth.
    nyquist = min(fs / 2.0, float(valid_nyquist_hz) if valid_nyquist_hz is not None else fs / 2.0)
    common_max = min(3500.0, nyquist)
    common_idx = [i for i, f in enumerate(freqs_ref) if 80.0 <= f <= common_max]
    full_idx = [i for i, f in enumerate(freqs_ref) if 0.0 < f <= nyquist]
    if not common_idx or not full_idx:
        raise ValueError("No usable spectral bins")
    common_total = sum(powers[i] for i in common_idx) + 1e-20
    full_total = sum(powers[i] for i in full_idx) + 1e-20
    centroid = sum(freqs_ref[i] * powers[i] for i in common_idx) / common_total
    cumulative = 0.0
    rolloff = common_max
    for i in common_idx:
        cumulative += powers[i]
        if cumulative >= 0.85 * common_total:
            rolloff = freqs_ref[i]
            break
    logs = [math.log(max(powers[i], 1e-30)) for i in common_idx]
    flatness = math.exp(sum(logs) / len(logs)) / (common_total / len(common_idx) + 1e-20)
    band_shares = {}
    for lo, hi in COMMON_BANDS:
        hi = min(hi, common_max)
        inds = [i for i, f in enumerate(freqs_ref) if lo <= f < hi]
        name = f"band_{int(lo)}_{int(hi if hi < 3500 else 3500)}"
        band_shares[name] = sum(powers[i] for i in inds) / common_total if inds else 0.0
    # The acoustic-only comparison band begins above the throat sensor's
    # original 4 kHz Nyquist. Upsampled throat samples must not populate it.
    high_inds = [i for i, f in enumerate(freqs_ref) if 4000.0 < f <= min(7800.0, nyquist)]
    high_share = sum(powers[i] for i in high_inds) / full_total if high_inds else 0.0
    return {
        "centroid_common_hz": centroid,
        "rolloff85_common_hz": rolloff,
        "flatness_common": flatness,
        "f0_median_hz": _median(f0s),
        "f0_iqr_hz": _percentile(f0s, 0.75) - _percentile(f0s, 0.25) if f0s else 0.0,
        "voiced_fraction": len(f0s) / max(1, len(periodicities)),
        "periodicity": _median(periodicities),
        "high_4000_7800_share": high_share,
        "valid_nyquist_hz": nyquist,
        "high_band_valid": bool(nyquist > 4000.0),
        **band_shares,
    }


def _envelope(samples: Sequence[float], fs: int, frame_ms: float = 20.0) -> list[float]:
    n = max(1, int(round(fs * frame_ms / 1000.0)))
    out = []
    for start in range(0, len(samples) - n + 1, n):
        frame = samples[start:start + n]
        out.append(math.sqrt(sum(x * x for x in frame) / n))
    return out


def summarize_channel(wav: WavData, original_nyquist_hz: float | None = None) -> tuple[dict, list[float]]:
    x, fs = wav.samples, wav.sample_rate
    n = len(x)
    rms = math.sqrt(sum(v * v for v in x) / n)
    peak = max(abs(v) for v in x)
    mean_x = sum(x) / n
    centered = [v - mean_x for v in x]
    zcr = sum(1 for a, b in zip(centered, centered[1:]) if (a < 0 <= b) or (b < 0 <= a)) / max(1, n - 1)
    env = _envelope(centered, fs)
    env_mean = _median(env)
    env_std = statistics.pstdev(env) if len(env) > 1 else 0.0
    env_diffs = [abs(b - a) for a, b in zip(env, env[1:])]
    spec = _spectrum_summary(centered, fs, valid_nyquist_hz=original_nyquist_hz)
    # Temporal-emission descriptors are derived from the measured amplitude
    # envelope. They represent observable event timing, not hidden state labels.
    temporal = temporal_geometry.summarize_envelope(env, frame_ms=20.0, duration_s=n / fs)
    metrics = {
        "duration_s": n / fs,
        "sample_rate_hz": float(fs),
        "sample_count": float(n),
        "rms": rms,
        "log_rms": math.log(max(rms, 1e-20)),
        "peak_abs": peak,
        "crest_factor": peak / max(rms, 1e-20),
        "zcr": zcr,
        "envelope_cv": env_std / max(env_mean, 1e-20),
        "envelope_modulation": _median(env_diffs) / max(env_mean, 1e-20),
        **temporal,
        **spec,
    }
    return metrics, env


def _resample_for_alignment(samples: Sequence[float], source_fs: int, target_fs: int) -> list[float]:
    if source_fs == target_fs:
        return list(samples)
    if source_fs > target_fs and source_fs % target_fs == 0:
        ratio = source_fs // target_fs
        out = []
        for i in range(0, len(samples) - ratio + 1, ratio):
            out.append(sum(samples[i:i + ratio]) / ratio)
        return out
    target_n = max(1, int(round(len(samples) * target_fs / source_fs)))
    out = []
    for j in range(target_n):
        pos = j * source_fs / target_fs
        left = min(len(samples) - 1, int(pos))
        right = min(len(samples) - 1, left + 1)
        frac = pos - left
        out.append(samples[left] * (1.0 - frac) + samples[right] * frac)
    return out


def estimate_raw_waveform_lag(throat: Sequence[float], throat_fs: int,
                              acoustic: Sequence[float], acoustic_fs: int,
                              max_lag_ms: float = 5.0,
                              window_ms: float = 500.0) -> dict:
    """Estimate residual raw-waveform lag at a common low rate.

    Positive lag means the acoustic waveform is later relative to the throat
    waveform under corr(T[n], A[n + lag]). This is diagnostic only; no shift
    is applied to either recording.
    """
    common_fs = min(throat_fs, acoustic_fs, 4000)
    if common_fs <= 0:
        return {"lag_ms": 0.0, "lag_samples": 0, "correlation": 0.0,
                "zero_lag_correlation": 0.0, "analysis_rate_hz": 0}
    t = _resample_for_alignment(throat, throat_fs, common_fs)
    a = _resample_for_alignment(acoustic, acoustic_fs, common_fs)
    n = min(len(t), len(a))
    win = min(n, max(64, int(round(window_ms * common_fs / 1000.0))))
    if win < 64:
        return {"lag_ms": 0.0, "lag_samples": 0, "correlation": 0.0,
                "zero_lag_correlation": 0.0, "analysis_rate_hz": common_fs}
    step = max(1, win // 4)
    candidates = range(0, max(1, n - win + 1), step)
    # Select a region with substantial energy in both channels.
    start = max(candidates, key=lambda i: sum(v*v for v in t[i:i+win]) + sum(v*v for v in a[i:i+win]))
    tx, ax = t[start:start+win], a[start:start+win]
    max_lag = max(1, int(round(max_lag_ms * common_fs / 1000.0)))
    def corr(lag: int) -> float:
        if lag >= 0:
            x1, x2 = tx[:win-lag], ax[lag:]
        else:
            x1, x2 = tx[-lag:], ax[:win+lag]
        m = min(len(x1), len(x2))
        if m < 32:
            return -1.0
        x1, x2 = x1[:m], x2[:m]
        mu1, mu2 = sum(x1)/m, sum(x2)/m
        num = sum((u-mu1)*(v-mu2) for u,v in zip(x1,x2))
        d1 = sum((u-mu1)**2 for u in x1); d2 = sum((v-mu2)**2 for v in x2)
        return num / math.sqrt(max(d1*d2, 1e-30))
    zero = corr(0)
    best_corr, best_lag = max((corr(k), k) for k in range(-max_lag, max_lag+1))
    return {"lag_ms": best_lag * 1000.0 / common_fs,
            "lag_samples": best_lag, "correlation": best_corr,
            "zero_lag_correlation": zero, "analysis_rate_hz": common_fs}


def estimate_envelope_lag(a: Sequence[float], b: Sequence[float], frame_ms: float = 20.0,
                          max_lag_ms: float = 40.0) -> dict:
    """Estimate residual lag from normalized amplitude-envelope correlation.

    Positive lag means b is shifted later relative to a under the convention
    corr(a[n], b[n+lag]). This is a diagnostic; samples are not modified.
    """
    n = min(len(a), len(b))
    if n < 5:
        return {"lag_ms": 0.0, "correlation": 0.0, "zero_lag_correlation": 0.0}
    aa = list(a[:n]); bb = list(b[:n])
    def corr(lag: int) -> float:
        if lag >= 0:
            x1, x2 = aa[:n-lag or None], bb[lag:]
        else:
            x1, x2 = aa[-lag:], bb[:n+lag]
        m = min(len(x1), len(x2))
        if m < 4:
            return -1.0
        x1, x2 = x1[:m], x2[:m]
        mu1, mu2 = sum(x1)/m, sum(x2)/m
        num = sum((u-mu1)*(v-mu2) for u,v in zip(x1,x2))
        d1 = sum((u-mu1)**2 for u in x1); d2 = sum((v-mu2)**2 for v in x2)
        return num / math.sqrt(max(d1*d2, 1e-30))
    zero = corr(0)
    max_frames = max(1, int(round(max_lag_ms / frame_ms)))
    candidates = [(corr(k), k) for k in range(-max_frames, max_frames + 1)]
    best_corr, best_lag = max(candidates, key=lambda z: z[0])
    return {"lag_ms": best_lag * frame_ms, "correlation": best_corr, "zero_lag_correlation": zero}


def _rank(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = r
        i = j
    return ranks


def _pearson(x: Sequence[float], y: Sequence[float]) -> float:
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    mx, my = sum(x[:n])/n, sum(y[:n])/n
    dx = [v-mx for v in x[:n]]; dy = [v-my for v in y[:n]]
    sx = sum(v*v for v in dx); sy = sum(v*v for v in dy)
    if sx <= 1e-24 or sy <= 1e-24:
        return 0.0
    return sum(a*b for a,b in zip(dx,dy)) / math.sqrt(sx*sy)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 3:
        return 0.0
    return _pearson(_rank(x), _rank(y))


def _robust_standardize(rows: Sequence[dict], features: Sequence[str],
                        mode: str = "robust") -> list[list[float]]:
    """Feature scaling used for RDMs; multiple modes expose normalization dependence."""
    if mode not in {"robust", "zscore", "rank"}:
        raise ValueError(f"Unknown standardization mode: {mode}")
    columns = [[float(row.get(k, 0.0)) for row in rows] for k in features]
    out = [[0.0] * len(features) for _ in rows]
    for j, col in enumerate(columns):
        if mode == "rank":
            ranks = _rank(col)
            denom = max(1, len(col) - 1)
            scaled = [(r - 1.0) / denom for r in ranks]
        elif mode == "zscore":
            mean = statistics.mean(col) if col else 0.0
            scale = statistics.pstdev(col) if len(col) > 1 else 1.0
            if scale < 1e-9:
                scale = 1.0
            scaled = [(v - mean) / scale for v in col]
        else:
            med = _median(col)
            mad = _median([abs(v - med) for v in col])
            scale = 1.4826 * mad
            if scale < 1e-9:
                scale = statistics.pstdev(col) if len(col) > 1 else 1.0
            if scale < 1e-9:
                scale = 1.0
            scaled = [max(-8.0, min(8.0, (v - med) / scale)) for v in col]
        for i, value in enumerate(scaled):
            out[i][j] = value
    return out


def _rdm_upper(rows: Sequence[Sequence[float]]) -> list[float]:
    out = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            out.append(math.sqrt(sum((a-b)**2 for a,b in zip(rows[i], rows[j]))))
    return out


def _bootstrap_ci(values: Sequence[float], seed: int = 13, n_boot: int = 1000) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(len(values))] for _ in values]
        boots.append(statistics.median(sample))
    return _percentile(boots, 0.025), _percentile(boots, 0.975)


def _permutation_null(acoustic_rows: Sequence[dict], throat_rows: Sequence[dict],
                      features: Sequence[str], observed: float,
                      rng: random.Random, n_perm: int = 199) -> list[float]:
    a = _robust_standardize(acoustic_rows, features)
    t0 = _robust_standardize(throat_rows, features)
    a_rdm = _rdm_upper(a)
    null = []
    for _ in range(n_perm):
        perm = list(range(len(t0)))
        rng.shuffle(perm)
        t = [t0[i] for i in perm]
        null.append(spearman(a_rdm, _rdm_upper(t)))
    return null


def analyze_pair(pair: dict) -> dict:
    tw = read_wav(pair["throat_path"])
    aw = read_wav(pair["acoustic_path"])
    if tw.sample_rate <= 0 or aw.sample_rate <= 0:
        raise ValueError("Invalid sample rate")
    for actual, meta, label in ((tw.sample_rate, pair["throat_meta"], "throat"),
                                (aw.sample_rate, pair["acoustic_meta"], "acoustic")):
        expected = meta.get("sampling_rate") if isinstance(meta, dict) else None
        if expected is not None and int(expected) != actual:
            raise ValueError(f"{label} WAV sample rate {actual} disagrees with metadata {expected}")
    # TAPS throat WAVs are Fourier-upsampled from an 8 kHz acquisition.
    # Preserve the original 4 kHz Nyquist limit; upsampling is not new bandwidth.
    tmeta, tenv = summarize_channel(tw, original_nyquist_hz=4000.0)
    ameta, aenv = summarize_channel(aw, original_nyquist_hz=min(aw.sample_rate / 2.0, 7800.0))
    lag = estimate_envelope_lag(tenv, aenv)
    raw_lag = estimate_raw_waveform_lag(tw.samples, tw.sample_rate, aw.samples, aw.sample_rate)
    # No additional alignment is applied. TAPS files are already postprocessed;
    # this is a residual alignment diagnostic only.
    return {
        "pair_key": pair["pair_key"],
        "speaker_internal": pair["speaker_internal"],
        "throat": tmeta,
        "acoustic": ameta,
        "alignment": lag,
        "raw_alignment": raw_lag,
        "source_metadata": {
            "throat_sampling_rate_metadata": pair["throat_meta"].get("sampling_rate"),
            "acoustic_sampling_rate_metadata": pair["acoustic_meta"].get("sampling_rate"),
            "metadata_present": bool(pair["metadata"]),
        },
    }


def summarize_rdm_relationships(pair_features: Sequence[dict], n_perm: int = 99,
                                seed: int = 13) -> dict:
    by_speaker: dict[str, list[dict]] = {}
    for row in pair_features:
        by_speaker.setdefault(row["speaker_internal"], []).append(row)
    view_results = []
    rng = random.Random(seed)
    for view, features in FEATURE_VIEWS.items():
        rhos, utterances_used = [], 0
        normalization_by_mode = {mode: [] for mode in ("robust", "zscore", "rank")}
        loo_rhos: list[float] = []
        null_by_perm: list[list[float]] = [[] for _ in range(n_perm)]
        for speaker, rows in sorted(by_speaker.items()):
            # Stable ordering by ephemeral hashed pair key; no raw IDs are emitted.
            rows = sorted(rows, key=lambda z: z["pair_key"])
            if len(rows) < 8:
                continue
            arows = [r["acoustic"] for r in rows]
            trows = [r["throat"] for r in rows]
            for mode in normalization_by_mode:
                ardm_mode = _rdm_upper(_robust_standardize(arows, features, mode=mode))
                trdm_mode = _rdm_upper(_robust_standardize(trows, features, mode=mode))
                normalization_by_mode[mode].append(spearman(ardm_mode, trdm_mode))
            ardm = _rdm_upper(_robust_standardize(arows, features, mode="robust"))
            trdm = _rdm_upper(_robust_standardize(trows, features, mode="robust"))
            rhos.append(spearman(ardm, trdm))
            utterances_used += len(rows)
            # Leave-one-feature-out: reveal whether one descriptor dominates the view.
            if len(features) > 2:
                for omitted in range(len(features)):
                    reduced = list(features[:omitted]) + list(features[omitted + 1:])
                    ar = _rdm_upper(_robust_standardize(arows, reduced, mode="robust"))
                    tr = _rdm_upper(_robust_standardize(trows, reduced, mode="robust"))
                    loo_rhos.append(spearman(ar, tr))
            null = _permutation_null(arows, trows, features, rhos[-1], rng, n_perm=n_perm)
            for i, value in enumerate(null):
                null_by_perm[i].append(value)
        ci = _bootstrap_ci(rhos, seed=seed + len(view), n_boot=1000)
        null_medians = [_median(row) for row in null_by_perm if row]
        observed = _median(rhos)
        p_value = ((1 + sum(1 for x in null_medians if x >= observed)) /
                   (1 + len(null_medians))) if null_medians else 1.0
        view_results.append({
            "view": view,
            "features": list(features),
            "speakers_analyzed": len(rhos),
            "utterances_analyzed": utterances_used,
            "median_rdm_spearman": observed,
            "speaker_bootstrap_95pct_ci": [ci[0], ci[1]],
            "median_permuted_null": _median(null_medians),
            "permuted_null_95pct": _percentile(null_medians, 0.95) if null_medians else 0.0,
            "empirical_one_sided_permutation_p": p_value,
            "n_permutations": n_perm,
            "normalization_sensitivity_median_rho": {
                mode: _median(vals) for mode, vals in normalization_by_mode.items()
            },
            "leave_one_feature_out_rho_median": _median(loo_rhos),
            "leave_one_feature_out_rho_min": min(loo_rhos) if loo_rhos else None,
            "leave_one_feature_out_cases": len(loo_rhos),
        })
    return {"views": view_results}


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def run_analysis(root: str | Path, output_dir: str | Path, split: str = "test",
                 max_speakers: int | None = None, max_utterances_per_speaker: int | None = None,
                 permutations: int = 99, seed: int = 13,
                 write_pair_features: bool = False,
                 provenance: str = "TAPS_file_release_local") -> dict:
    root, output_dir = Path(root), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pairs = discover_pairs(root, split=split)
    # Limit by speaker after deterministic ordering, then by utterance count.
    speaker_ids = sorted({p["speaker_internal"] for p in pairs})
    if max_speakers is not None:
        speaker_ids = speaker_ids[:max_speakers]
    selected = []
    for speaker in speaker_ids:
        group = sorted([p for p in pairs if p["speaker_internal"] == speaker], key=lambda p: p["utterance_internal"])
        if max_utterances_per_speaker is not None:
            group = group[:max_utterances_per_speaker]
        selected.extend(group)
    features = []
    skipped = 0
    for pair in selected:
        try:
            features.append(analyze_pair(pair))
        except (ValueError, OSError, struct.error, wave.Error):
            skipped += 1
    if not features:
        raise RuntimeError("No valid paired WAV recordings could be analyzed")
    geom = summarize_rdm_relationships(features, n_perm=permutations, seed=seed)
    lags = [r["alignment"]["lag_ms"] for r in features]
    env_corrs = [r["alignment"]["correlation"] for r in features]
    zero_corrs = [r["alignment"]["zero_lag_correlation"] for r in features]
    raw_lags = [r["raw_alignment"]["lag_ms"] for r in features]
    raw_corrs = [r["raw_alignment"]["correlation"] for r in features]
    channel_fs_t = [r["throat"]["sample_rate_hz"] for r in features]
    channel_fs_a = [r["acoustic"]["sample_rate_hz"] for r in features]
    report = {
        "build": 14,
        "analysis_status": ("synthetic_smoke_test_complete" if provenance == "synthetic_fixture" else "empirical_pair_analysis_complete"),
        "dataset": ("Synthetic fixture" if provenance == "synthetic_fixture" else "TAPS Throat and Acoustic Paired Speech Dataset"),
        "data_provenance": provenance,
        "split": split,
        "pairs_discovered": len(pairs),
        "pairs_analyzed": len(features),
        "pairs_skipped": skipped,
        "speakers_analyzed": len({r["speaker_internal"] for r in features}),
        "utterances_per_speaker_cap": max_utterances_per_speaker,
        "sampling_rates_throat_hz": sorted(set(channel_fs_t)),
        "sampling_rates_acoustic_hz": sorted(set(channel_fs_a)),
        "residual_envelope_lag_ms": {
            "median": _median(lags),
            "iqr": _percentile(lags, 0.75) - _percentile(lags, 0.25),
            "median_absolute": _median([abs(v) for v in lags]),
        },
        "raw_waveform_alignment_diagnostic": {
            "median_residual_lag_ms": _median(raw_lags),
            "median_best_normalized_correlation": _median(raw_corrs),
            "analysis_rate_hz": min(int(min(channel_fs_t + channel_fs_a)), 4000),
            "max_search_lag_ms": 5.0,
            "applied_to_samples": False,
        },
        "envelope_correlation": {
            "median_after_source_preprocessing": _median(env_corrs),
            "median_at_zero_extra_shift": _median(zero_corrs),
        },
        "cross_modal_geometry": geom,
        "temporal_emission_model": {
            "definition": "Observer-extracted event-time landmarks from the short-time RMS envelope; event intervals define a temporal response signature.",
            "shape_view": "Normalized event intervals; invariant to time-origin shift and uniform clock scaling under the defined event set.",
            "rate_view": "Absolute event rate and median interval; intentionally changes under clock scaling.",
            "event_rule": "Envelope local maxima above max(P60, median + 0.5*MAD), greedily separated by 80 ms.",
            "state_claim": "Events are measured-signal landmarks, not verified hidden-state transitions.",
        },
        "normalization_sensitivity": "RDMs are recomputed under robust MAD, z-score, and feature-rank scaling; leave-one-feature-out sensitivity is also reported.",
        "interpretation_guardrails": [
            "No emotion labels are present in the documented TAPS schema; no emotion classification is performed.",
            "Speaker IDs and transcripts are used only for within-speaker grouping and are not written to outputs.",
            "The source dataset is already preprocessed and globally aligned; residual lag is diagnostic only.",
            "Throat/acoustic amplitudes have different physical units and are not directly compared.",
            "The acoustic-only high-frequency band is not treated as a missing throat signal that can be recovered without modelling.",
            "Temporal-emission events are envelope maxima used as observable timing landmarks, not labelled phonetic or hidden-state events.",
            "Normalized event-interval shape and absolute event rate are reported separately; uniform clock-scale invariance does not imply duration invariance of the physical process.",
            "Normalization sensitivity and leave-one-feature-out summaries are diagnostics, not independent replications or significance guarantees.",
        ],
    }
    (output_dir / "build_14_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Output only aggregate alignment; never write per-speaker IDs or transcripts.
    _write_csv(output_dir / "alignment_summary.csv", [{
        "pairs_analyzed": len(features),
        "median_residual_lag_ms": _median(lags),
        "iqr_residual_lag_ms": _percentile(lags, 0.75) - _percentile(lags, 0.25),
        "median_envelope_corr": _median(env_corrs),
        "median_zero_lag_corr": _median(zero_corrs),
    }])
    _write_csv(output_dir / "rdm_view_summary.csv", geom["views"])
    if write_pair_features:
        rows = []
        for r in features:
            row = {"pair_key": r["pair_key"], "residual_lag_ms": r["alignment"]["lag_ms"],
                   "envelope_corr": r["alignment"]["correlation"],
                   "raw_waveform_lag_ms": r["raw_alignment"]["lag_ms"],
                   "raw_waveform_corr": r["raw_alignment"]["correlation"]}
            row.update({f"throat_{k}": v for k, v in r["throat"].items() if k != "sample_count"})
            row.update({f"acoustic_{k}": v for k, v in r["acoustic"].items() if k != "sample_count"})
            rows.append(row)
        _write_csv(output_dir / "pair_features_anonymized.csv", rows)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze paired TAPS throat/acoustic WAV recordings with temporal-emission geometry")
    ap.add_argument("--root", required=True, help="Root containing <split>/<speaker>/<utterance>/ paired WAVs")
    ap.add_argument("--split", default="test", choices=sorted(SPLIT_NAMES))
    ap.add_argument("--output", default="reports/empirical_test")
    ap.add_argument("--max-speakers", type=int, default=None)
    ap.add_argument("--max-utterances-per-speaker", type=int, default=None)
    ap.add_argument("--permutations", type=int, default=99)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--write-pair-features", action="store_true")
    args = ap.parse_args()
    report = run_analysis(args.root, args.output, args.split, args.max_speakers,
                          args.max_utterances_per_speaker, args.permutations, args.seed,
                          args.write_pair_features)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
