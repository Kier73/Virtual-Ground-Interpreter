"""Build 29-30 signal stress suite.

The frozen builds use fixed synthetic fixtures.  This module stresses the
same APIs with multiresolution framing, gain/DC/noise/clipping/jitter,
additional calibration traces, pilot mismatch and phase drift.
"""
from __future__ import annotations

import cmath
import math
import random
import statistics

if __package__ in (None, ""):
    from common import rb29_module, rb30_module, sc30_module
else:
    from .common import rb29_module, rb30_module, sc30_module


def _aggregate_f1(metrics_list: list[dict]) -> dict:
    tp = sum(int(x["tp"]) for x in metrics_list)
    fp = sum(int(x["fp"]) for x in metrics_list)
    fn = sum(int(x["fn"]) for x in metrics_list)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def _boundary_f1(rb29, channels, truth_samples, hop: int = 64, frame_size: int = 256, view: str = "combined") -> dict:
    analysis = rb29.analyze_signals(
        channels,
        frame_size=frame_size,
        hop=hop,
        observer_view=view,
    )
    predicted = list(analysis.selected.boundaries if analysis.selected else [])
    truth_frames = [round(x / hop) for x in truth_samples]
    return rb29.match_boundaries(predicted, truth_frames, tolerance=2)


def build29_multiresolution_summary(max_traces: int = 6) -> dict:
    rb29 = rb29_module()
    corpus, _ = rb29.build_corpus()
    configs = [(128, 32), (256, 64), (512, 128)]
    out = {}
    for frame_size, hop in configs:
        metrics = [
            _boundary_f1(
                rb29,
                item["channels"],
                item["truth_boundaries_samples"],
                hop=hop,
                frame_size=frame_size,
            )
            for item in corpus[:max_traces]
        ]
        out[f"frame_{frame_size}_hop_{hop}"] = _aggregate_f1(metrics)
    return {"traces": max_traces, "configs": out}


def _perturb(samples, kind: str, amount, rng: random.Random, fs: int):
    n = len(samples)
    if kind == "gain":
        return tuple(amount * x for x in samples)
    if kind == "dc":
        return tuple(x + amount for x in samples)
    if kind == "noise":
        return tuple(x + rng.gauss(0.0, amount) for x in samples)
    if kind == "clip":
        return tuple(max(-amount, min(amount, x)) for x in samples)
    if kind == "jitter":
        return tuple(samples[min(n - 1, max(0, i + rng.choice((-2, -1, 0, 0, 1, 2))))] for i in range(n))
    if kind == "am":
        return tuple(x * (1.0 + 0.3 * math.sin(2 * math.pi * 0.5 * i / fs)) for i, x in enumerate(samples))
    if kind == "drift_amp":
        return tuple(x * (1.0 + 0.4 * i / max(1, n - 1)) for i, x in enumerate(samples))
    raise ValueError(kind)


def build29_perturbation_summary(max_traces: int = 4) -> dict:
    rb29 = rb29_module()
    corpus, _ = rb29.build_corpus()
    conditions = [
        ("baseline", None, None),
        ("gain_low", "gain", 0.35),
        ("gain_high", "gain", 2.5),
        ("dc_offset", "dc", 0.08),
        ("noise_0.01", "noise", 0.01),
        ("noise_0.03", "noise", 0.03),
        ("clip_0.8", "clip", 0.8),
        ("jitter", "jitter", None),
        ("amplitude_modulation", "am", None),
        ("amplitude_drift", "drift_amp", None),
    ]
    out = {}
    for name, kind, amount in conditions:
        metrics = []
        for item in corpus[:max_traces]:
            if kind is None:
                channels = item["channels"]
            else:
                rng = random.Random(1000 + len(name) * 17)
                channels = [
                    rb29.SignalChannel(
                        c.name,
                        c.sample_rate,
                        _perturb(c.samples, kind, amount, rng, c.sample_rate),
                    )
                    for c in item["channels"]
                ]
            metrics.append(
                _boundary_f1(rb29, channels, item["truth_boundaries_samples"])
            )
        out[name] = _aggregate_f1(metrics)
    return {"traces": max_traces, "conditions": out}


def build30_adaptive_stress_summary(
    calibration_count: int = 6,
    heldout_count: int = 6,
    n_events: int = 7,
) -> dict:
    rb30 = rb30_module()
    out = {}
    for task, seed0 in (("frequency", 7000), ("amplitude", 8000), ("mixed", 9000)):
        calibration = [rb30.make_signal_trace(task, seed0 + i, n_events=n_events) for i in range(calibration_count)]
        heldout = [rb30.make_signal_trace(task, seed0 + 100 + i, n_events=n_events) for i in range(heldout_count)]
        selection = rb30.select_observer(calibration, boundary_weight=0.7, token_weight=0.3, ambiguity_epsilon=0.015)
        profile = selection["selected_profile"]
        held = rb30.evaluate_on_heldout(profile, heldout, boundary_weight=0.7, token_weight=0.3)
        out[task] = {
            "calibration_count": len(calibration),
            "heldout_count": len(heldout),
            "selected_profile": profile.profile_id,
            "boundary_view": profile.boundary_view,
            "token_view": profile.token_view,
            "ambiguous_selection": bool(selection["ambiguous_selection"]),
            "plausible_profile_count": len(selection["plausible_profiles"]),
            "heldout_boundary_f1": held.boundary_f1,
            "heldout_token_pairwise_accuracy": held.token_pairwise_accuracy,
            "heldout_utility": held.utility,
        }
    return out


def _phase_errors(sc30, *, noise_sigma: float = 0.0, pilot_shift: float = 0.0, roll: int = 0, drift: float = 0.0) -> int:
    errors = 0
    total = 0
    for opcode in ("ADD8", "SUB8"):
        for a in range(8):
            for b in range(8):
                total += 1
                pa = sc30.encode_phase_operand(a, sample_count=128, gain=0.7, phase_offset=0.31 * a, noise_sigma=noise_sigma, seed=300 + a)
                pb = sc30.encode_phase_operand(b, sample_count=128, gain=1.2, phase_offset=-0.17 * b, noise_sigma=noise_sigma, seed=400 + b)
                if pilot_shift:
                    pa = sc30.PhaseOperand(pa.signal, tuple(p * cmath.exp(1j * pilot_shift) for p in pa.pilot))
                if roll:
                    rolled = pa.signal[-roll:] + pa.signal[:-roll]
                    pa = sc30.PhaseOperand(tuple(rolled), pa.pilot)
                if drift:
                    drifted = tuple(x * cmath.exp(1j * drift * i) for i, x in enumerate(pa.signal))
                    pa = sc30.PhaseOperand(drifted, pa.pilot)
                got = sc30.decode_phase_symbol(sc30.phase_domain_execute(opcode, pa, pb))
                want = (a + b) % 8 if opcode == "ADD8" else (a - b) % 8
                errors += int(got != want)
    return errors


def build30_phase_robustness_summary() -> dict:
    sc30 = sc30_module()
    return {
        "noise_sigma": {
            str(sigma): _phase_errors(sc30, noise_sigma=sigma)
            for sigma in (0.0, 0.02, 0.1, 0.5)
        },
        "pilot_shift_pi_over_4_errors": _phase_errors(sc30, noise_sigma=0.02, pilot_shift=math.pi / 4),
        "one_sample_roll_errors": _phase_errors(sc30, noise_sigma=0.02, roll=1),
        "phase_drift_errors": _phase_errors(sc30, noise_sigma=0.02, drift=0.01),
        "total_operations": 128,
        "interpretation": (
            "Pilot calibration is part of the computation. Phase-domain "
            "arithmetic is exact in the noiseless fixture but not robust to "
            "uncalibrated pilot phase, drift or large noise."
        ),
    }


def signal_stress_summary() -> dict:
    return {
        "build29_multiresolution": build29_multiresolution_summary(),
        "build29_perturbations": build29_perturbation_summary(),
        "build30_adaptive": build30_adaptive_stress_summary(),
        "build30_phase": build30_phase_robustness_summary(),
    }
