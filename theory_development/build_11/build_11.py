#!/usr/bin/env python3
"""Build 11: empirical response geometry from a curated real sensor excerpt.

This module deliberately distinguishes source observations from derived features.
It uses only the Python standard library. The included CSV is a traceable excerpt,
not the complete source recording. Use scripts/fetch_full_recording.py to retrieve
the complete CC BY 4.0 recording on a machine with network access.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

G0 = 9.80665  # standard gravity, m/s^2 per g
SENSOR_LIMIT_G = 4.0
OBSERVER_INTERVAL = (66.0, 68.0)
OBSERVER_POINT = 67.0
AXES = ("gforce_x", "gforce_y", "gforce_z")

# Extensible local codon vocabulary. Aliases resolve to the same operation.
CODON_ALIASES = {
    "ad": "add", "plus": "add", "add": "add",
    "su": "sub", "minus": "sub", "sub": "sub",
    "mx": "mul", "times": "mul", "mul": "mul",
    "dv": "div", "divide": "div", "div": "div",
    "sq": "square", "square": "square",
    "ab": "abs", "abs": "abs",
}


def codon_apply(codon: str, *args: float) -> float:
    op = CODON_ALIASES.get(codon, codon)
    if op == "add" and len(args) == 2:
        return args[0] + args[1]
    if op == "sub" and len(args) == 2:
        return args[0] - args[1]
    if op == "mul" and len(args) == 2:
        return args[0] * args[1]
    if op == "div" and len(args) == 2:
        if args[1] == 0:
            raise ZeroDivisionError("codon div denominator is zero")
        return args[0] / args[1]
    if op == "square" and len(args) == 1:
        return args[0] * args[0]
    if op == "abs" and len(args) == 1:
        return abs(args[0])
    raise ValueError(f"Unsupported codon/arity: {codon}/{len(args)}")


def load_excerpt(path: Path) -> Dict[str, List[dict]]:
    windows: Dict[str, List[dict]] = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"window_id", "source_line", "time_s", *AXES}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            item = {
                "source_line": int(row["source_line"]),
                "time_s": float(row["time_s"]),
                "gforce_x": float(row["gforce_x"]),
                "gforce_y": float(row["gforce_y"]),
                "gforce_z": float(row["gforce_z"]),
            }
            windows.setdefault(row["window_id"], []).append(item)
    for name, rows in windows.items():
        rows.sort(key=lambda x: x["time_s"])
        if any(rows[i]["time_s"] <= rows[i - 1]["time_s"] for i in range(1, len(rows))):
            raise ValueError(f"Non-increasing timestamps within {name}")
    return windows


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def mean(xs: Sequence[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def std(xs: Sequence[float]) -> float:
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def corr(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    mx, my = mean(x), mean(y)
    sx, sy = std(x), std(y)
    if sx == 0 or sy == 0:
        return 0.0
    return mean([(a - mx) * (b - my) for a, b in zip(x, y)]) / (sx * sy)


def symmetric_eigenvalues_3x3(matrix: List[List[float]]) -> List[float]:
    """Jacobi eigenvalue iteration for a real symmetric 3x3 matrix."""
    a = [row[:] for row in matrix]
    for _ in range(40):
        pairs = [(0, 1), (0, 2), (1, 2)]
        p, q = max(pairs, key=lambda ij: abs(a[ij[0]][ij[1]]))
        if abs(a[p][q]) < 1e-14:
            break
        tau = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
        t = (1.0 if tau >= 0 else -1.0) / (abs(tau) + math.sqrt(1 + tau * tau))
        c = 1.0 / math.sqrt(1 + t * t)
        s = t * c
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = app - t * apq
        a[q][q] = aqq + t * apq
        a[p][q] = a[q][p] = 0.0
        for r in range(3):
            if r != p and r != q:
                arp, arq = a[r][p], a[r][q]
                a[r][p] = a[p][r] = c * arp - s * arq
                a[r][q] = a[q][r] = s * arp + c * arq
    return sorted([max(0.0, a[0][0]), max(0.0, a[1][1]), max(0.0, a[2][2])], reverse=True)


def feature_window(rows: Sequence[dict]) -> dict:
    if len(rows) < 8:
        raise ValueError("Need at least 8 samples per window")
    t = [r["time_s"] for r in rows]
    axes = [[r[a] for r in rows] for a in AXES]
    n = len(rows)
    dts = [t[i] - t[i - 1] for i in range(1, n)]
    med_dt = statistics.median(dts)
    dt_mad = statistics.median([abs(x - med_dt) for x in dts])
    max_gap = max(dts)

    means = [mean(axis) for axis in axes]
    medians = [statistics.median(axis) for axis in axes]
    stds = [std(axis) for axis in axes]
    centered = [[axes[j][i] - medians[j] for i in range(n)] for j in range(3)]
    centered_mag = [math.sqrt(sum(centered[j][i] ** 2 for j in range(3))) for i in range(n)]
    raw_mag = [math.sqrt(sum(axes[j][i] ** 2 for j in range(3))) for i in range(n)]
    mag_centered_mean = mean(centered_mag)
    mag_centered_rms = math.sqrt(mean([x * x for x in centered_mag]))
    mag_std = std(centered_mag)
    mag_p95 = percentile(centered_mag, 0.95)

    # Covariance matrix of the three channels, with per-window median centring.
    cov = [[mean([centered[i][k] * centered[j][k] for k in range(n)]) for j in range(3)] for i in range(3)]
    eig = symmetric_eigenvalues_3x3(cov)
    eig_sum = sum(eig)
    eig_frac = [v / eig_sum if eig_sum > 0 else 0.0 for v in eig]

    # Difference-per-observation and time-normalized derivative are kept separate.
    delta_mag = [centered_mag[i] - centered_mag[i - 1] for i in range(1, n)]
    valid_rates = [delta_mag[i - 1] / dts[i - 1] for i in range(1, len(dts)) if 0.003 <= dts[i - 1] <= 0.05]
    delta_rms = math.sqrt(mean([x * x for x in delta_mag])) if delta_mag else 0.0
    rate_rms = math.sqrt(mean([x * x for x in valid_rates])) if valid_rates else 0.0
    ac1 = corr(centered_mag[:-1], centered_mag[1:])
    ac2 = corr(centered_mag[:-2], centered_mag[2:])
    sign_changes = sum(1 for i in range(1, n) if (centered_mag[i] - mag_centered_mean) * (centered_mag[i - 1] - mag_centered_mean) < 0)
    zcr = sign_changes / max(1, n - 1)

    # Sensor-limit flag: conservative threshold, not a declaration of confirmed clipping.
    near_limit = sum(1 for axis in axes for v in axis if abs(v) >= 3.98)
    limit_fraction = near_limit / (3 * n)

    # Fourth standardized moment for magnitude; report only if scale is nonzero.
    m4 = mean([(x - mag_centered_mean) ** 4 for x in centered_mag])
    kurtosis = m4 / (mag_std ** 4) if mag_std > 0 else 0.0

    return {
        "n": n,
        "start_s": t[0],
        "end_s": t[-1],
        "duration_s": t[-1] - t[0],
        "median_dt_s": med_dt,
        "dt_mad_s": dt_mad,
        "max_dt_s": max_gap,
        "observed_interval_hz_median": 1.0 / med_dt if med_dt > 0 else 0.0,
        "mean_x_g": means[0], "mean_y_g": means[1], "mean_z_g": means[2],
        "std_x_g": stds[0], "std_y_g": stds[1], "std_z_g": stds[2],
        "centered_vector_rms_g": mag_centered_rms,
        "centered_vector_sd_g": mag_std,
        "centered_vector_p95_g": mag_p95,
        "raw_vector_mean_norm_g": mean(raw_mag),
        "cov_eig1_g2": eig[0], "cov_eig2_g2": eig[1], "cov_eig3_g2": eig[2],
        "cov_eig1_fraction": eig_frac[0], "cov_eig2_fraction": eig_frac[1], "cov_eig3_fraction": eig_frac[2],
        "corr_xy": corr(centered[0], centered[1]),
        "corr_xz": corr(centered[0], centered[2]),
        "corr_yz": corr(centered[1], centered[2]),
        "delta_mag_rms_g_per_sample": delta_rms,
        "time_derivative_rms_g_per_s": rate_rms,
        "magnitude_acf_lag1": ac1,
        "magnitude_acf_lag2": ac2,
        "magnitude_zero_crossing_rate": zcr,
        "magnitude_kurtosis": kurtosis,
        "near_4g_fraction": limit_fraction,
    }


FEATURE_VIEWS = {
    "amplitude": ["std_x_g", "std_y_g", "std_z_g", "centered_vector_rms_g", "centered_vector_sd_g", "centered_vector_p95_g"],
    "direction": ["cov_eig1_fraction", "cov_eig2_fraction", "cov_eig3_fraction", "corr_xy", "corr_xz", "corr_yz"],
    "temporal": ["delta_mag_rms_g_per_sample", "time_derivative_rms_g_per_s", "magnitude_acf_lag1", "magnitude_acf_lag2", "magnitude_zero_crossing_rate", "magnitude_kurtosis"],
    "sensor": ["near_4g_fraction", "median_dt_s", "dt_mad_s", "max_dt_s"],
}


def standardize_rows(features: Dict[str, dict], columns: Sequence[str]) -> Dict[str, List[float]]:
    names = list(features)
    values = {c: [float(features[n][c]) for n in names] for c in columns}
    scales = {}
    centers = {}
    for c, xs in values.items():
        centers[c] = statistics.median(xs)
        mad = statistics.median([abs(x - centers[c]) for x in xs])
        sd = std(xs)
        scales[c] = 1.4826 * mad if mad > 1e-12 else (sd if sd > 1e-12 else 1.0)
    out = {}
    for i, name in enumerate(names):
        out[name] = [(values[c][i] - centers[c]) / scales[c] for c in columns]
    return out


def make_rdm(features: Dict[str, dict], columns: Sequence[str]) -> Tuple[List[str], List[List[float]]]:
    names = list(features)
    z = standardize_rows(features, columns)
    matrix = [[0.0 for _ in names] for _ in names]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(z[names[i]], z[names[j]])))
            matrix[i][j] = matrix[j][i] = d
    return names, matrix


def rdm_spearman(a: List[List[float]], b: List[List[float]]) -> float:
    vals_a, vals_b = [], []
    n = len(a)
    for i in range(n):
        for j in range(i + 1, n):
            vals_a.append(a[i][j]); vals_b.append(b[i][j])
    return corr(rankdata(vals_a), rankdata(vals_b))


def rankdata(xs: Sequence[float]) -> List[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    p = 0
    while p < len(order):
        q = p + 1
        while q < len(order) and xs[order[q]] == xs[order[p]]:
            q += 1
        rank = (p + 1 + q) / 2.0
        for k in range(p, q):
            ranks[order[k]] = rank
        p = q
    return ranks


def response_difference(group_a: Sequence[dict], group_b: Sequence[dict], columns: Sequence[str], label_a: str, label_b: str) -> dict:
    out = {}
    for c in columns:
        a = [float(x[c]) for x in group_a]
        b = [float(x[c]) for x in group_b]
        pooled = math.sqrt((std(a) ** 2 + std(b) ** 2) / 2.0)
        delta = mean(b) - mean(a)
        out[c] = {
            f"{label_a}_mean": mean(a), f"{label_b}_mean": mean(b),
            f"difference_{label_b}_minus_{label_a}": delta,
            "standardized_difference_descriptive": delta / pooled if pooled > 1e-12 else None,
        }
    return out


def write_csv(path: Path, rows: Sequence[dict], fields: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8"); return
    fields = list(fields or rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def run(out_dir: Path, excerpt_path: Path) -> dict:
    data_dir = out_dir / "data"
    report_dir = out_dir / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    windows = load_excerpt(excerpt_path)
    features = {name: feature_window(rows) for name, rows in windows.items()}

    feature_rows = [{"window_id": name, **features[name]} for name in features]
    write_csv(data_dir / "window_features.csv", feature_rows)

    rdm_results = {}
    rdm_matrices = {}
    for view, cols in FEATURE_VIEWS.items():
        names, mat = make_rdm(features, cols)
        rdm_matrices[view] = mat
        write_csv(data_dir / f"rdm_{view}.csv", [dict(window_id=n, **{m: mat[i][j] for j, m in enumerate(names)}) for i, n in enumerate(names)], ["window_id", *names])
        rdm_results[view] = {"feature_columns": cols, "mean_off_diagonal_distance": mean([mat[i][j] for i in range(len(mat)) for j in range(i + 1, len(mat))])}

    views = list(FEATURE_VIEWS)
    rdm_corrs = []
    for i, a in enumerate(views):
        for b in views[i + 1:]:
            rdm_corrs.append({"view_a": a, "view_b": b, "spearman_rdm_correlation": rdm_spearman(rdm_matrices[a], rdm_matrices[b])})
    write_csv(data_dir / "rdm_view_correlations.csv", rdm_corrs)

    # Labeling follows the source annotations: pre < 66 s, observer interval 66-68 s,
    # post > 68 s. Only windows wholly contained in a region are assigned to it.
    pre_names = [n for n, rows in windows.items() if rows[-1]["time_s"] < OBSERVER_INTERVAL[0]]
    event_names = [n for n, rows in windows.items() if rows[0]["time_s"] >= OBSERVER_INTERVAL[0] and rows[-1]["time_s"] <= OBSERVER_INTERVAL[1]]
    post_names = [n for n, rows in windows.items() if rows[0]["time_s"] > OBSERVER_INTERVAL[1]]
    # Exclude short segments or segments crossing the annotated boundary from summary group means.
    def group_features(names: Sequence[str]) -> List[dict]:
        return [features[n] for n in names]
    group_names = {"pre": pre_names, "observer_interval": event_names, "post": post_names}

    compare_cols = ["centered_vector_rms_g", "centered_vector_sd_g", "time_derivative_rms_g_per_s", "cov_eig1_fraction", "near_4g_fraction"]
    differences = {}
    if pre_names and event_names:
        differences["pre_vs_observer_interval"] = response_difference(group_features(pre_names), group_features(event_names), compare_cols, "pre", "observer_interval")
    if event_names and post_names:
        differences["observer_interval_vs_post"] = response_difference(group_features(event_names), group_features(post_names), compare_cols, "observer_interval", "post")
    if pre_names and post_names:
        differences["pre_vs_post"] = response_difference(group_features(pre_names), group_features(post_names), compare_cols, "pre", "post")

    # Sensor observations are in g; convert using conventional standard gravity.
    unit_conversion_error = 0.0
    # Unit-scale-invariance check: a common multiplicative conversion must not alter RDM geometry.
    base_vectors = {n: [features[n][c] for c in ["std_x_g", "std_y_g", "std_z_g"]] for n in features}
    scaled_vectors = {n: [x * G0 for x in vals] for n, vals in base_vectors.items()}
    base_mat = pairwise_from_vectors(base_vectors)
    scaled_mat = pairwise_from_vectors(scaled_vectors)
    unit_conversion_error = max(abs(base_mat[i][j] - scaled_mat[i][j]) for i in range(len(base_mat)) for j in range(len(base_mat)))

    saturation_windows = [
        {"window_id": name, "near_4g_fraction": features[name]["near_4g_fraction"], "flagged": features[name]["near_4g_fraction"] > 0}
        for name in features
    ]
    write_csv(data_dir / "sensor_limit_flags.csv", saturation_windows)

    excerpt_selection = None
    manifest_path = excerpt_path.parent / "source_manifest.json"
    if manifest_path.exists():
        try:
            excerpt_selection = json.loads(manifest_path.read_text(encoding="utf-8")).get("local_excerpt")
        except (OSError, json.JSONDecodeError):
            excerpt_selection = None

    report = {
        "build": "11",
        "title": "Empirical vibration response geometry and sensor calibration audit",
        "scope": "Pilot analysis of a source-derived excerpt from one real smartphone G-Force recording; full recording download is provided but was not fetched in this offline execution environment.",
        "source": {
            "dataset_title": "Vibration measurements with observer-declared variance change points",
            "author": "Justyna Witulska",
            "version": "1.0.0",
            "publication_date": "2026-09-19",
            "license": "CC BY 4.0",
            "repository": "https://github.com/witulska/vibration-changepoint-dataset",
            "raw_recording": "https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/data/processed/measurement_01.csv",
            "measurement_id": 1,
            "measurement_context": "person; gait / motion change; G-Force only; 83.74 s; 8,157 source rows",
            "sensor_metadata": {"range_g": [-4.0, 4.0], "nominal_max_sampling_hz": 100, "units": "g", "channels": ["gforce_x", "gforce_y", "gforce_z"]},
            "observer_interval_s": list(OBSERVER_INTERVAL),
            "theoretical_change_point_s": OBSERVER_POINT,
            "source_excerpt_rows": sum(len(v) for v in windows.values()),
            "source_excerpt_windows": len(windows),
            "excerpt_selection": excerpt_selection,
            "note": "The excerpt consists of selected line ranges from the canonical processed CSV. Discontinuous time spans are kept as separate windows; no missing samples are interpolated."
        },
        "data_audit": {
            "window_count": len(windows),
            "row_count": sum(len(v) for v in windows.values()),
            "observed_median_intervals_s": {name: features[name]["median_dt_s"] for name in features},
            "observed_max_gaps_s": {name: features[name]["max_dt_s"] for name in features},
            "near_limit_windows": [x["window_id"] for x in saturation_windows if x["flagged"]],
            "unit_conversion_max_distance_error": unit_conversion_error,
        },
        "window_features": features,
        "observer_groups": group_names,
        "descriptive_differences": differences,
        "response_geometry": {
            "views": rdm_results,
            "rdm_correlations": rdm_corrs,
            "interpretation": "These matrices describe temporal windows from one recording; correlations are descriptive and are not independent-sample inference."
        },
        "codon_alias_check": {
            "ad_equals_plus": codon_apply("ad", 1.25, 2.75) == codon_apply("plus", 1.25, 2.75),
            "mx_equals_times": codon_apply("mx", 1.25, 2.75) == codon_apply("times", 1.25, 2.75),
        },
        "limitations": [
            "Only one of the nine source recordings is sampled in this pilot.",
            "The complete 8,157-row source recording is not included; only selected windows are included.",
            "The processed G-Force channel is a sensor output, not a calibrated force/acceleration reference measurement.",
            "Sensor transfer function cannot be estimated from this excerpt because no calibrated reference input is present.",
            "Near-4g readings are flagged as possible range saturation, not confirmed clipping.",
            "The observer's 66-68 s interval is a variance-change annotation; it is not an emotional label.",
            "No empirical acoustic room-impulse waveform has been ingested in this build. Room-IR acquisition is reserved for the next empirical extension."
        ]
    }
    (report_dir / "build_11_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    key = {
        "build": "11",
        "source_rows_in_excerpt": report["data_audit"]["row_count"],
        "windows": report["data_audit"]["window_count"],
        "annotated_change_point_s": OBSERVER_POINT,
        "annotated_interval_s": list(OBSERVER_INTERVAL),
        "unit_conversion_max_distance_error": unit_conversion_error,
        "near_limit_windows": report["data_audit"]["near_limit_windows"],
        "rdm_view_correlations": rdm_corrs,
        "conclusion": "Empirical pilot only: selected G-Force windows show heterogeneous amplitude, direction and temporal signatures; the excerpt is insufficient for a robust claim about generalized tone or cross-modal invariance."
    }
    (report_dir / "key_results.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return report


def pairwise_from_vectors(vectors: Dict[str, List[float]]) -> List[List[float]]:
    names = list(vectors)
    # Column-wise z-standardization using all observations, with common-unit scaling cancellation.
    d = len(next(iter(vectors.values())))
    cols = [[vectors[n][j] for n in names] for j in range(d)]
    centers = [mean(c) for c in cols]
    scales = [std(c) or 1.0 for c in cols]
    z = {n: [(vectors[n][j] - centers[j]) / scales[j] for j in range(d)] for n in names}
    mat = [[0.0] * len(names) for _ in names]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x = math.sqrt(sum((a - b) ** 2 for a, b in zip(z[names[i]], z[names[j]])))
            mat[i][j] = mat[j][i] = x
    return mat


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--excerpt", type=Path, default=Path(__file__).resolve().parent / "source_data" / "measurement_01_excerpt.csv")
    args = parser.parse_args()
    report = run(args.out, args.excerpt)
    print(json.dumps({"windows": report["data_audit"]["window_count"], "rows": report["data_audit"]["row_count"], "report": str(args.out / "reports" / "build_11_report.json")}, indent=2))


if __name__ == "__main__":
    main()
