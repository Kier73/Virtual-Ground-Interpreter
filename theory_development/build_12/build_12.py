#!/usr/bin/env python3
"""Build 12: Empirical room-impulse-response geometry.

Standard-library-only WAV ingestion and analysis. Raw recordings are never
silently normalized or overwritten. Absolute level, normalized decay, spectral
shape, and temporal response are stored as separate views.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import struct
import wave
from array import array
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

BANDS_HZ = (125, 250, 500, 1000, 2000, 4000)
FEATURE_VIEWS = {
    "decay": ["edt_s", "t20_s", "t30_s", "decay_rmse_db", "t20_band_median_s"],
    "early_late": ["c50_db", "c80_db", "d50", "ts_s", "early_50ms_fraction", "early_80ms_fraction"],
    "spectral": [f"band_{f}_share" for f in BANDS_HZ] + ["band_centroid_hz", "spectral_slope"],
    "temporal": ["onset_to_peak_ms", "peak_to_rms", "zero_crossing_rate", "late_energy_fraction", "decay_rmse_db"],
    "level": ["peak_abs", "rms", "crest_factor", "energy"],
}


def _parse_fmt(fmt: bytes) -> Tuple[int, int, int, int, int]:
    if len(fmt) < 16:
        raise ValueError("WAV fmt chunk is shorter than 16 bytes")
    tag, channels, fs, byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", fmt, 0)
    if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE
        if len(fmt) < 40:
            raise ValueError("WAVE_FORMAT_EXTENSIBLE fmt chunk is incomplete")
        # GUID begins at byte 24. First 16 bits identify PCM (1) or IEEE float (3).
        subformat_tag = struct.unpack_from("<H", fmt, 24)[0]
        if subformat_tag not in (1, 3):
            raise ValueError(f"Unsupported extensible WAV subtype: {subformat_tag}")
        tag = subformat_tag
    if channels < 1 or fs < 1 or bits not in (8, 16, 24, 32, 64):
        raise ValueError(f"Unsupported WAV format: channels={channels}, fs={fs}, bits={bits}")
    if tag not in (1, 3):
        raise ValueError(f"Unsupported WAV encoding tag: {tag}")
    if tag == 3 and bits not in (32, 64):
        raise ValueError("IEEE-float WAV must use 32- or 64-bit samples")
    if block_align < channels * ((bits + 7) // 8):
        raise ValueError("Invalid WAV block alignment")
    return tag, channels, fs, block_align, bits


def read_wav(path: Path) -> Tuple[int, List[List[float]], dict]:
    """Read PCM or IEEE-float WAV; returns fs, channel-major samples, metadata."""
    raw = path.read_bytes()
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError(f"Not a supported RIFF/RF64 WAVE file: {path}")
    pos = 12
    fmt = None
    data = None
    while pos + 8 <= len(raw):
        chunk_id = raw[pos:pos + 4]
        chunk_size = struct.unpack_from("<I", raw, pos + 4)[0]
        start = pos + 8
        end = start + chunk_size
        if end > len(raw):
            raise ValueError(f"WAV chunk {chunk_id!r} exceeds file size")
        if chunk_id == b"fmt ":
            fmt = raw[start:end]
        elif chunk_id == b"data":
            data = raw[start:end]
        pos = end + (chunk_size & 1)
    if fmt is None or data is None:
        raise ValueError("WAV file must contain fmt and data chunks")
    tag, channels, fs, block_align, bits = _parse_fmt(fmt)
    bytes_per_sample = (bits + 7) // 8
    frame_count = len(data) // block_align
    if frame_count == 0:
        raise ValueError("WAV contains no complete audio frames")
    out = [[] for _ in range(channels)]
    p = 0
    for _ in range(frame_count):
        frame = data[p:p + block_align]
        for ch in range(channels):
            b = frame[ch * bytes_per_sample:(ch + 1) * bytes_per_sample]
            if tag == 3:
                value = struct.unpack("<f" if bits == 32 else "<d", b)[0]
            elif bits == 8:
                value = (b[0] - 128) / 128.0
            elif bits == 16:
                value = struct.unpack("<h", b)[0] / 32768.0
            elif bits == 24:
                iv = int.from_bytes(b, "little", signed=False)
                if iv & 0x800000:
                    iv -= 1 << 24
                value = iv / 8388608.0
            elif bits == 32:
                value = struct.unpack("<i", b)[0] / 2147483648.0
            else:
                raise ValueError("64-bit integer PCM is not supported")
            if not math.isfinite(value):
                raise ValueError("WAV contains NaN or infinite samples")
            out[ch].append(float(value))
        p += block_align
    meta = {"encoding": "pcm" if tag == 1 else "ieee_float", "channels": channels,
            "bits_per_sample": bits, "sample_rate_hz": fs, "frames": frame_count,
            "duration_s": frame_count / fs}
    return fs, out, meta


def mean(xs: Sequence[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _linear_fit(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float, float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return float("nan"), float("nan"), float("nan")
    mx, my = mean(xs), mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 1e-24:
        return float("nan"), float("nan"), float("nan")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    intercept = my - slope * mx
    rmse = math.sqrt(mean([(y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys)]))
    return slope, intercept, rmse


def _decay_metrics(x: Sequence[float], fs: int) -> dict:
    n = len(x)
    peak = max((abs(v) for v in x), default=0.0)
    if peak <= 1e-15:
        return {"edt_s": float("nan"), "t20_s": float("nan"), "t30_s": float("nan"),
                "decay_rmse_db": float("nan"), "decay_slope_db_s": float("nan"),
                "onset_index": 0, "peak_index": 0}
    onset_threshold = peak * 0.001  # -60 dB amplitude threshold
    onset = next((i for i, v in enumerate(x) if abs(v) >= onset_threshold), 0)
    peak_index = max(range(onset, n), key=lambda i: abs(x[i]))
    seg = x[onset:]
    if len(seg) < 16:
        raise ValueError("RIR is too short for decay estimation")
    energy = [v * v for v in seg]
    edc = [0.0] * len(energy)
    acc = 0.0
    for i in range(len(energy) - 1, -1, -1):
        acc += energy[i]
        edc[i] = acc
    total = edc[0]
    db = [10.0 * math.log10(max(v / total, 1e-30)) for v in edc]
    t = [i / fs for i in range(len(db))]

    def fit_range(low: float, high: float) -> Tuple[float, float]:
        ids = [i for i, value in enumerate(db) if high <= value <= low]
        if len(ids) < max(10, int(fs * 0.005)):
            return float("nan"), float("nan")
        slope, _, rmse = _linear_fit([t[i] for i in ids], [db[i] for i in ids])
        if not math.isfinite(slope) or slope >= -1e-9:
            return float("nan"), rmse
        return -60.0 / slope, rmse

    edt, rmse_edt = fit_range(0.0, -10.0)
    t20, rmse20 = fit_range(-5.0, -25.0)
    t30, rmse30 = fit_range(-5.0, -35.0)
    valid_rmse = [v for v in (rmse_edt, rmse20, rmse30) if math.isfinite(v)]
    slopes = []
    for lo, hi in ((0.0, -10.0), (-5.0, -25.0), (-5.0, -35.0)):
        ids = [i for i, value in enumerate(db) if hi <= value <= lo]
        if len(ids) >= 10:
            slope, _, _ = _linear_fit([t[i] for i in ids], [db[i] for i in ids])
            if math.isfinite(slope):
                slopes.append(slope)
    return {"edt_s": edt, "t20_s": t20, "t30_s": t30,
            "decay_rmse_db": mean(valid_rmse) if valid_rmse else float("nan"),
            "decay_slope_db_s": mean(slopes) if slopes else float("nan"),
            "onset_index": onset, "peak_index": peak_index,
            "dynamic_range_db": -min(db) if db else 0.0}


def _biquad_bandpass(x: Sequence[float], fs: int, fc: float, q: float = math.sqrt(2.0)) -> List[float]:
    w0 = 2.0 * math.pi * fc / fs
    c, s = math.cos(w0), math.sin(w0)
    alpha = s / (2.0 * q)
    a0 = 1.0 + alpha
    b0, b1, b2 = alpha / a0, 0.0, -alpha / a0
    a1, a2 = -2.0 * c / a0, (1.0 - alpha) / a0
    x1 = x2 = y1 = y2 = 0.0
    out = []
    for value in x:
        y = b0 * value + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out.append(y)
        x2, x1 = x1, value
        y2, y1 = y1, y
    return out


def _safe_ratio(a: float, b: float) -> float:
    return a / b if b > 1e-30 else 0.0


def analyze_channel(x: Sequence[float], fs: int) -> dict:
    if fs < 8000:
        raise ValueError("Sampling rate below 8 kHz is not accepted for this response analysis")
    if len(x) < max(128, int(fs * 0.05)):
        raise ValueError("Impulse response is too short")
    n = len(x)
    peak_abs = max(abs(v) for v in x)
    energy = sum(v * v for v in x)
    rms = math.sqrt(energy / n)
    if peak_abs <= 1e-14 or energy <= 1e-28:
        raise ValueError("Impulse response is effectively silent")
    decay = _decay_metrics(x, fs)
    onset, peak_i = decay["onset_index"], decay["peak_index"]
    rel = x[onset:]
    rel_energy = [v * v for v in rel]
    total_energy = sum(rel_energy)
    time_s = [i / fs for i in range(len(rel_energy))]
    early50 = sum(rel_energy[:min(len(rel_energy), int(0.050 * fs))])
    early80 = sum(rel_energy[:min(len(rel_energy), int(0.080 * fs))])
    late50 = max(0.0, total_energy - early50)
    late80 = max(0.0, total_energy - early80)
    ts = _safe_ratio(sum(t * e for t, e in zip(time_s, rel_energy)), total_energy)
    c50 = 10 * math.log10(max(_safe_ratio(early50, late50), 1e-30))
    c80 = 10 * math.log10(max(_safe_ratio(early80, late80), 1e-30))
    zcr = sum(1 for i in range(1, n) if (x[i] >= 0) != (x[i - 1] >= 0)) / max(1, n - 1)
    band_energy = {}
    band_decay = {}
    for fc in BANDS_HZ:
        if fc >= 0.42 * fs:
            continue
        filtered = _biquad_bandpass(x, fs, fc)
        be = sum(v * v for v in filtered)
        band_energy[str(fc)] = be
        bd = _decay_metrics(filtered, fs)
        band_decay[str(fc)] = {k: bd[k] for k in ("edt_s", "t20_s", "t30_s", "decay_rmse_db", "dynamic_range_db")}
    total_band = sum(band_energy.values())
    band_shares = {f"band_{fc}_share": _safe_ratio(band_energy[str(fc)], total_band)
                   for fc in BANDS_HZ if str(fc) in band_energy}
    usable = [(fc, band_energy[str(fc)]) for fc in BANDS_HZ if str(fc) in band_energy]
    band_centroid = _safe_ratio(sum(fc * e for fc, e in usable), sum(e for _, e in usable))
    # Log-log slope of octave-band energy; descriptive, not a calibrated transfer estimate.
    log_pairs = [(math.log(fc), math.log(max(e, 1e-30))) for fc, e in usable]
    spectral_slope = _linear_fit([p[0] for p in log_pairs], [p[1] for p in log_pairs])[0] if len(log_pairs) >= 3 else float("nan")
    band_rt = [v["t20_s"] for v in band_decay.values() if math.isfinite(v["t20_s"])]
    onset_to_peak_ms = max(0, peak_i - onset) * 1000.0 / fs
    late_energy_fraction = _safe_ratio(sum(rel_energy[int(0.080 * fs):]), total_energy)
    result = {
        "sample_rate_hz": fs, "n_samples": n, "duration_s": n / fs,
        "peak_abs": peak_abs, "rms": rms, "energy": energy,
        "crest_factor": _safe_ratio(peak_abs, rms),
        "onset_index": onset, "peak_index": peak_i,
        "onset_to_peak_ms": onset_to_peak_ms,
        "c50_db": c50, "c80_db": c80,
        "d50": _safe_ratio(early50, total_energy),
        "early_50ms_fraction": _safe_ratio(early50, total_energy),
        "early_80ms_fraction": _safe_ratio(early80, total_energy),
        "ts_s": ts, "late_energy_fraction": late_energy_fraction,
        "zero_crossing_rate": zcr,
        "edt_s": decay["edt_s"], "t20_s": decay["t20_s"], "t30_s": decay["t30_s"],
        "decay_rmse_db": decay["decay_rmse_db"],
        "decay_slope_db_s": decay["decay_slope_db_s"],
        "dynamic_range_db": decay["dynamic_range_db"],
        "t20_band_median_s": statistics.median(band_rt) if band_rt else float("nan"),
        "band_centroid_hz": band_centroid, "spectral_slope": spectral_slope,
        **band_shares,
        "band_decay_json": json.dumps(band_decay, sort_keys=True, allow_nan=True),
    }
    return result


def rankdata(xs: Sequence[float]) -> List[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    p = 0
    while p < len(order):
        q = p + 1
        while q < len(order) and xs[order[q]] == xs[order[p]]:
            q += 1
        rank = (p + 1 + q) / 2.0
        for j in range(p, q):
            ranks[order[j]] = rank
        p = q
    return ranks


def corr(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 3:
        return float("nan")
    mx, my = mean(x), mean(y)
    sx = math.sqrt(mean([(v - mx) ** 2 for v in x]))
    sy = math.sqrt(mean([(v - my) ** 2 for v in y]))
    if sx <= 1e-15 or sy <= 1e-15:
        return float("nan")
    return mean([(a - mx) * (b - my) for a, b in zip(x, y)]) / (sx * sy)


def _median(xs: Sequence[float]) -> float:
    ys = [float(v) for v in xs if math.isfinite(float(v))]
    return statistics.median(ys) if ys else float("nan")


def aggregate_rooms(file_features: Sequence[dict]) -> Dict[str, dict]:
    grouped: Dict[str, List[dict]] = {}
    for row in file_features:
        grouped.setdefault(row["room_id"], []).append(row)
    aggregate = {}
    for room, rows in sorted(grouped.items()):
        all_keys = sorted(set.intersection(*(set(r.keys()) for r in rows)) - {"room_id", "file", "band_decay_json", "sample_rate_hz", "n_samples", "onset_index", "peak_index"})
        features = {}
        for key in all_keys:
            values = [r[key] for r in rows if isinstance(r.get(key), (int, float)) and math.isfinite(float(r[key]))]
            if values:
                features[key] = statistics.median(values)
        features.update({"room_id": room, "rir_count": len(rows),
                         "sample_rates_hz": sorted({int(r["sample_rate_hz"]) for r in rows if "sample_rate_hz" in r})})
        aggregate[room] = features
    return aggregate


def _robust_z(rooms: Dict[str, dict], columns: Sequence[str]) -> Dict[str, List[float]]:
    names = list(rooms)
    vals = {c: [float(rooms[n].get(c, float("nan"))) for n in names] for c in columns}
    result = {}
    for c, xs in vals.items():
        finite = [v for v in xs if math.isfinite(v)]
        center = statistics.median(finite) if finite else 0.0
        mad = statistics.median([abs(v - center) for v in finite]) if finite else 0.0
        sd = statistics.pstdev(finite) if len(finite) > 1 else 0.0
        scale = 1.4826 * mad if mad > 1e-12 else (sd if sd > 1e-12 else 1.0)
        result[c] = [(v - center) / scale if math.isfinite(v) else 0.0 for v in xs]
    return {name: [result[c][i] for c in columns] for i, name in enumerate(names)}


def make_rdm(rooms: Dict[str, dict], columns: Sequence[str]) -> Tuple[List[str], List[List[float]]]:
    names = list(rooms)
    z = _robust_z(rooms, columns)
    matrix = [[0.0] * len(names) for _ in names]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(z[names[i]], z[names[j]])))
            matrix[i][j] = matrix[j][i] = d
    return names, matrix


def paired_cross_domain_rdm_correlation(
    domain_a: Sequence[dict], domain_b: Sequence[dict],
    feature_columns_a: Sequence[str], feature_columns_b: Sequence[str],
    pair_id_key: str = "pair_id",
) -> float:
    """Compare cross-domain RDMs only when observations have explicit paired IDs.

    Pair IDs must identify a shared acquisition condition (for example room +
    source position + receiver position + excitation + trial), not merely a
    convenient row number. Unpaired domains are rejected rather than silently
    matched by order.
    """
    if any(pair_id_key not in row for row in domain_a) or any(pair_id_key not in row for row in domain_b):
        raise ValueError(f"Every record must contain an explicit {pair_id_key!r}")
    map_a = {str(row[pair_id_key]): row for row in domain_a}
    map_b = {str(row[pair_id_key]): row for row in domain_b}
    if len(map_a) != len(domain_a) or len(map_b) != len(domain_b):
        raise ValueError("Pair IDs must be unique within each domain")
    if set(map_a) != set(map_b):
        missing_a = sorted(set(map_b) - set(map_a))
        missing_b = sorted(set(map_a) - set(map_b))
        raise ValueError(f"Domains are not paired; missing in A={missing_a}, missing in B={missing_b}")
    if len(map_a) < 4:
        raise ValueError("At least four paired conditions are required for an exploratory RDM comparison")
    a = {key: map_a[key] for key in sorted(map_a)}
    b = {key: map_b[key] for key in sorted(map_b)}
    _, rdm_a = make_rdm(a, feature_columns_a)
    _, rdm_b = make_rdm(b, feature_columns_b)
    return rdm_spearman(rdm_a, rdm_b)


def rdm_spearman(a: List[List[float]], b: List[List[float]]) -> float:
    if len(a) != len(b) or not a:
        return float("nan")
    va, vb = [], []
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            va.append(a[i][j]); vb.append(b[i][j])
    if len(va) < 3:
        return float("nan")
    return corr(rankdata(va), rankdata(vb))


def write_csv(path: Path, rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze_tree(rir_root: Path) -> Tuple[List[dict], List[dict], dict]:
    wavs = sorted(p for p in rir_root.rglob("*") if p.is_file() and p.suffix.lower() == ".wav")
    files, failures = [], []
    for path in wavs:
        try:
            fs, channels, meta = read_wav(path)
            # Rochester dataset is documented as mono. If a later version is
            # multichannel, analyze each channel separately rather than downmix.
            for ch_idx, samples in enumerate(channels):
                features = analyze_channel(samples, fs)
                room_id = path.parent.name if path.parent != rir_root else path.stem.split("_")[0]
                row = {"room_id": room_id, "file": str(path.relative_to(rir_root)),
                       "channel": ch_idx, **meta, **features}
                files.append(row)
        except Exception as exc:
            failures.append({"file": str(path.relative_to(rir_root)), "error": f"{type(exc).__name__}: {exc}"})
    rooms = aggregate_rooms(files)
    summary = {"wav_files_found": len(wavs), "channel_records_analyzed": len(files),
               "rooms_detected": len(rooms), "failures": failures,
               "status": "analyzed" if files else "no_usable_wavs"}
    return files, [{"room_id": rid, **features} for rid, features in rooms.items()], summary


def build_outputs(rir_root: Path, outdir: Path) -> dict:
    files, room_rows, summary = analyze_tree(rir_root)
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "rir_file_features.csv", files)
    write_csv(outdir / "room_features.csv", room_rows)
    rooms = {r["room_id"]: r for r in room_rows}
    views = {"decay": FEATURE_VIEWS["decay"], "early_late": FEATURE_VIEWS["early_late"],
             "spectral": FEATURE_VIEWS["spectral"], "temporal": FEATURE_VIEWS["temporal"],
             "level": FEATURE_VIEWS["level"]}
    rdms = {}
    rdm_names = None
    for view, columns in views.items():
        available = [c for c in columns if any(c in r and math.isfinite(float(r[c])) for r in room_rows)]
        if len(available) < 2 or len(rooms) < 3:
            continue
        names, mat = make_rdm(rooms, available)
        rdm_names = names
        rows = [{"room_id": names[i], **{names[j]: mat[i][j] for j in range(len(names))}} for i in range(len(names))]
        write_csv(outdir / f"rdm_{view}.csv", rows)
        rdms[view] = mat
    pairs = []
    names = list(rdms)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs.append({"view_a": names[i], "view_b": names[j],
                          "rdm_spearman": rdm_spearman(rdms[names[i]], rdms[names[j]])})
    write_csv(outdir / "rdm_view_correlations.csv", pairs)
    report = {"build": "12", "dataset": "University of Rochester room impulse response dataset",
              "dataset_doi": "10.60593/ur.d.26801089.v3", "license": "CC BY 4.0",
              "analysis_status": summary["status"], "source_summary": summary,
              "rooms": [r["room_id"] for r in room_rows], "rdm_view_correlations": pairs,
              "interpretation": "These are within-acoustic-domain room comparisons. No cross-modal RDM correlation with the Build 11 smartphone movement excerpt is calculated because the recordings are not paired by shared excitation, room, device, or trial.",
              "measurement_cautions": ["RIR amplitude depends on source, microphone and acquisition gain; level features are kept separate.",
                  "RT/EDT estimates are regression extrapolations from the recorded decay range, not necessarily direct 60 dB measurements.",
                  "The documented 48 kHz / 32-bit / mono format is source metadata; each file's actual WAV header is inspected.",
                  "Octave-band filters are compact second-order analysis filters, not a certified ISO 3382 implementation."]}
    (outdir / "build_12_report.json").write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze measured room impulse responses for Build 12")
    ap.add_argument("--rir-root", type=Path, required=True, help="Root directory containing extracted room folders and WAV files")
    ap.add_argument("--outdir", type=Path, default=Path("build_12_outputs"))
    args = ap.parse_args()
    report = build_outputs(args.rir_root, args.outdir)
    print(json.dumps({"status": report["analysis_status"], "rooms": len(report["rooms"]),
                      "pairs": len(report["rdm_view_correlations"])}, indent=2))
    return 0 if report["analysis_status"] == "analyzed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
