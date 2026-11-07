"""Build 12 pre-roll onset regression fixture and correction prototype.

The frozen Build 12 onset rule fires on the first sample whose absolute value
is at least 0.001 * peak.  The shipped unit tests use impulses that begin at
sample 0, so they cannot see the Rochester pre-roll failure.  This module adds
a golden fixture with one second of low-level noise before the direct sound.
It records two facts:

* the frozen detector starts well before the direct-sound peak; and
* a validation-layer prototype that trims at the direct-sound peak recovers
  physically ordinary decay metrics.

The prototype lives here, not in the frozen build, so the historical record is
unchanged.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

if __package__ in (None, ""):
    from common import build12_module
else:
    from .common import build12_module


def make_preroll_rir(
    seed: int = 2699,
    fs: int = 48000,
    preroll_s: float = 1.0,
    tail_s: float = 2.0,
    tau: float = 0.05,
    noise_amp: float = 0.20,
) -> tuple[list[float], int, int]:
    """Return a RIR-like signal with noise before a direct-sound impulse.

    The noise is deliberately strong enough to resemble the Rochester pre-roll
    energy fraction, while the direct sound remains the peak.
    """
    rng = random.Random(seed)
    preroll = int(fs * preroll_s)
    tail = int(fs * tail_s)
    x = [rng.uniform(-noise_amp, noise_amp) for _ in range(preroll)]
    x.extend(math.exp(-(i / fs) / tau) for i in range(tail))
    return x, fs, preroll


def corrected_decay_metrics(x: list[float], fs: int, peak_index: int) -> dict:
    """Prototype correction: move t=0 to the direct-sound peak.

    This is a validation-layer wrapper around the frozen feature code.  It is
    not a patch to the frozen build.
    """
    build12 = build12_module()
    trimmed = x[peak_index:]
    return build12._decay_metrics(trimmed, fs)


def diagnose_preroll(
    seed: int = 2699,
    fs: int = 48000,
    preroll_s: float = 1.0,
    tau: float = 0.05,
    noise_amp: float = 0.20,
) -> dict:
    build12 = build12_module()
    x, fs, true_peak = make_preroll_rir(seed, fs, preroll_s, 2.0, tau, noise_amp)
    frozen = build12._decay_metrics(x, fs)
    corrected = corrected_decay_metrics(x, fs, true_peak)
    total_energy = sum(v * v for v in x)
    pre_energy = sum(v * v for v in x[:true_peak])
    return {
        "seed": seed,
        "sample_rate": fs,
        "true_peak_index": true_peak,
        "frozen_onset_index": frozen["onset_index"],
        "frozen_peak_index": frozen["peak_index"],
        "frozen_edt_s": frozen["edt_s"],
        "frozen_t20_s": frozen["t20_s"],
        "pre_peak_energy_fraction": pre_energy / total_energy if total_energy else 0.0,
        "onset_to_peak_ms_frozen": (frozen["peak_index"] - frozen["onset_index"]) * 1000.0 / fs,
        "corrected_edt_s": corrected["edt_s"],
        "corrected_t20_s": corrected["t20_s"],
        "corrected_onset_index": corrected["onset_index"],
        "corrected_peak_index": corrected["peak_index"],
        "signal_length": len(x),
    }


def summarize_preroll(seeds: tuple[int, ...] = (2699, 2700, 2701)) -> list[dict]:
    return [diagnose_preroll(seed) for seed in seeds]


def fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent / "validation"
