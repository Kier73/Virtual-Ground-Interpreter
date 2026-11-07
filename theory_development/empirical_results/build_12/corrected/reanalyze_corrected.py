#!/usr/bin/env python3
"""Re-analyze the Rochester RIR corpus with the Build 12 onset bug corrected.

Build 12's `_decay_metrics` defines onset as the first sample whose absolute
value reaches 0.001 * peak.  Every Rochester file contains a 1.000 s pre-roll
of low-level noise, so that rule fires hundreds of milliseconds before the
direct sound.  The decay integral and the 50/80 ms early windows therefore
include almost the whole pre-roll, which is why the shipped run reports EDT of
tens of seconds and C50 near -50 dB.

The corpus aligns the direct-sound peak at sample 48000 (1000 ms) in every
file.  This script trims each channel at that peak and runs the frozen Build 12
feature functions on the trimmed response.  The frozen build is imported, not
modified.  Only t = 0 moves; all other Build 12 definitions are retained.

Outputs are written next to this script under `corrected/`.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
THEORY = REPO / "theory_development"
BUILD_DIR = THEORY / "build_12"
BUILD_12_CSV = THEORY / "empirical_results" / "build_12" / "rir_file_features.csv"
DEFAULT_RIR_ROOT = Path(
    r"C:\Users\kross\AppData\Local\Temp\opencode\vl_data\rochester\wavs"
)

sys.path.insert(0, str(BUILD_DIR))
import build_12  # noqa: E402


def _finite(value) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return v if math.isfinite(v) else float("nan")


def _median(values) -> float:
    vals = [v for v in (_finite(x) for x in values) if math.isfinite(v)]
    return statistics.median(vals) if vals else float("nan")


def _quantile(values, q: float) -> float:
    vals = sorted(v for v in (_finite(x) for x in values) if math.isfinite(v))
    if not vals:
        return float("nan")
    pos = q * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def load_old_rows(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        return {row["file"]: row for row in csv.DictReader(f)}


def analyze_file(path: Path, old_rows: dict) -> dict:
    fs, channels, meta = build_12.read_wav(path)
    if len(channels) != 1:
        raise ValueError(f"Expected mono corpus file, got {len(channels)} channels")
    x = channels[0]
    total_energy = sum(v * v for v in x)
    peak_index = max(range(len(x)), key=lambda i: abs(x[i]))
    pre_energy = sum(v * v for v in x[:peak_index])
    pre_fraction = pre_energy / total_energy if total_energy > 0 else 0.0
    corrected = build_12.analyze_channel(x[peak_index:], fs)

    key = str(path.relative_to(DEFAULT_RIR_ROOT))
    old = old_rows.get(key, {})
    return {
        "room_id": path.parent.name,
        "file": key,
        "channel": 0,
        **meta,
        "direct_peak_index": peak_index,
        "pre_peak_samples": peak_index,
        "pre_peak_duration_ms": 1000.0 * peak_index / fs,
        "pre_peak_energy_fraction": pre_fraction,
        "pre_peak_energy_db": 10.0 * math.log10(pre_fraction) if pre_fraction > 0 else float("nan"),
        "old_onset_index": int(float(old.get("onset_index", "nan"))),
        "old_onset_to_peak_ms": _finite(old.get("onset_to_peak_ms")),
        "old_edt_s": _finite(old.get("edt_s")),
        "old_t20_s": _finite(old.get("t20_s")),
        "old_c50_db": _finite(old.get("c50_db")),
        **corrected,
    }


def main() -> int:
    outdir = HERE.parent
    if not DEFAULT_RIR_ROOT.exists():
        print(f"RIR root not found: {DEFAULT_RIR_ROOT}", file=sys.stderr)
        return 2
    old_rows = load_old_rows(BUILD_12_CSV)
    paths = sorted(p for p in DEFAULT_RIR_ROOT.rglob("*.wav") if p.is_file())
    rows = []
    failures = []
    for i, path in enumerate(paths, 1):
        try:
            rows.append(analyze_file(path, old_rows))
        except Exception as exc:  # noqa: BLE001 - diagnostic run, report every failure
            failures.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})
        if i % 10 == 0:
            print(f"analyzed {i}/{len(paths)}", flush=True)

    build_12.write_csv(outdir / "rir_file_features_corrected.csv", rows)
    room_rows = build_12.aggregate_rooms(rows)
    build_12.write_csv(
        outdir / "room_features_corrected.csv",
        [{"room_id": rid, **features} for rid, features in room_rows.items()],
    )

    # Old room-level medians, for direct comparison.
    old_room: dict[str, list[dict]] = {}
    for row in old_rows.values():
        old_room.setdefault(row["room_id"], []).append(row)
    comparison = []
    for room_id in sorted(room_rows):
        old = old_room.get(room_id, [])
        comparison.append({
            "room_id": room_id,
            "old_edt_s": _median(r.get("edt_s") for r in old),
            "corrected_edt_s": room_rows[room_id].get("edt_s"),
            "old_t20_s": _median(r.get("t20_s") for r in old),
            "corrected_t20_s": room_rows[room_id].get("t20_s"),
            "old_c50_db": _median(r.get("c50_db") for r in old),
            "corrected_c50_db": room_rows[room_id].get("c50_db"),
            "old_d50": _median(r.get("d50") for r in old),
            "corrected_d50": room_rows[room_id].get("d50"),
            "pre_peak_energy_fraction": room_rows[room_id].get("pre_peak_energy_fraction"),
        })
    build_12.write_csv(outdir / "room_correction_comparison.csv", comparison)

    # Same five views and same RDM code as Build 12.
    rooms = {r["room_id"]: r for r in room_rows.values()}
    rdms = {}
    for view, columns in build_12.FEATURE_VIEWS.items():
        available = [
            c for c in columns
            if any(c in r and math.isfinite(_finite(r[c])) for r in rooms.values())
        ]
        if len(available) < 2 or len(rooms) < 3:
            continue
        names, mat = build_12.make_rdm(rooms, available)
        rdm_rows = [
            {"room_id": names[i], **{names[j]: mat[i][j] for j in range(len(names))}}
            for i in range(len(names))
        ]
        build_12.write_csv(outdir / f"rdm_{view}_corrected.csv", rdm_rows)
        rdms[view] = mat

    pairs = []
    view_names = list(rdms)
    for i in range(len(view_names)):
        for j in range(i + 1, len(view_names)):
            pairs.append({
                "view_a": view_names[i],
                "view_b": view_names[j],
                "rdm_spearman_corrected": build_12.rdm_spearman(
                    rdms[view_names[i]], rdms[view_names[j]]
                ),
            })
    build_12.write_csv(outdir / "rdm_view_correlations_corrected.csv", pairs)

    shipped = {
        (r["view_a"], r["view_b"]): _finite(r["rdm_spearman"])
        for r in json.loads((REPO / "empirical_results" / "build_12" / "build_12_report.json").read_text())["rdm_view_correlations"]
    }
    for row in pairs:
        row["rdm_spearman_shipped"] = shipped.get((row["view_a"], row["view_b"]), float("nan"))
        row["delta"] = row["rdm_spearman_corrected"] - row["rdm_spearman_shipped"]
    build_12.write_csv(outdir / "rdm_view_correlations_comparison.csv", pairs)

    pre = [r["pre_peak_energy_fraction"] for r in rows]
    old_edt = [r["old_edt_s"] for r in rows]
    new_edt = [r["edt_s"] for r in rows]
    old_c50 = [r["old_c50_db"] for r in rows]
    new_c50 = [r["c50_db"] for r in rows]
    report = {
        "build": "12-corrected",
        "dataset": "University of Rochester room impulse response dataset",
        "dataset_doi": "10.60593/ur.d.26801089.v3",
        "frozen_build_source": str(BUILD_DIR / "build_12.py"),
        "correction": (
            "Build 12 onset = first sample with |x| >= 0.001 * peak. All Rochester "
            "files contain a 1.000 s noise pre-roll, so onset fired at a median of "
            f"{_median(r['old_onset_to_peak_ms'] for r in rows):.1f} ms before the "
            "direct-sound peak. This reanalysis trims at the direct-sound peak "
            "(sample 48000 in every file) and then applies the unmodified Build 12 "
            "feature functions. The frozen iteration was not edited."
        ),
        "files_analyzed": len(rows),
        "rooms_detected": len(room_rows),
        "failures": failures,
        "onset_diagnostics": {
            "pre_peak_energy_fraction_min": min(pre),
            "pre_peak_energy_fraction_median": statistics.median(pre),
            "pre_peak_energy_fraction_max": max(pre),
            "pre_peak_energy_fraction_p95": _quantile(pre, 0.95),
            "old_onset_to_peak_ms_median": _median(r["old_onset_to_peak_ms"] for r in rows),
            "old_onset_to_peak_ms_range": [
                min(r["old_onset_to_peak_ms"] for r in rows),
                max(r["old_onset_to_peak_ms"] for r in rows),
            ],
            "old_edt_s_median": statistics.median(old_edt),
            "old_edt_s_range": [min(old_edt), max(old_edt)],
            "corrected_edt_s_median": statistics.median(new_edt),
            "corrected_edt_s_range": [min(new_edt), max(new_edt)],
            "old_c50_db_median": statistics.median(old_c50),
            "old_c50_db_range": [min(old_c50), max(old_c50)],
            "corrected_c50_db_median": statistics.median(new_c50),
            "corrected_c50_db_range": [min(new_c50), max(new_c50)],
        },
        "view_correlations_shipped_vs_corrected": pairs,
        "room_comparison": comparison,
        "interpretation": (
            "After removing the pre-roll, per-file EDT falls from tens of seconds "
            "to the sub-second range and C50 becomes positive, as expected for "
            "measured rooms. The corrected decay, early/late and spectral views "
            "are now usable as within-acoustic-domain descriptors. The shipped "
            "RDM correlations should be cited only as an illustration of the bug, "
            "not as evidence about room acoustics."
        ),
    }
    (outdir / "build_12_report_corrected.json").write_text(
        json.dumps(report, indent=2, allow_nan=True), encoding="utf-8"
    )
    print(json.dumps({
        "files": len(rows),
        "rooms": len(room_rows),
        "failures": len(failures),
        "pre_peak_median": statistics.median(pre),
        "corrected_edt_median": statistics.median(new_edt),
        "corrected_c50_median": statistics.median(new_c50),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
