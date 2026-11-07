# Signals, Representations and Invariants

## Working thesis

Signals may be unusually effective as a common descriptive medium because many systems expose themselves through changing observable quantities: amplitude, frequency, phase, timing, recurrence, spectral distribution and cross-channel relationships.

But raw signals are not automatically invariant. A waveform depends on its observer, sensor transfer function, gain, phase reference, bandwidth, sampling rate and noise.

A more precise target is:

**A signal representation whose relational structure remains stable under a declared family of observer and channel transformations.**

## Invariance hierarchy

| Transformation | Potentially stable quantity | Required qualification |
|---|---|---|
| Positive gain | Normalized spectral shape / relative phase | Nonzero signal and adequate SNR |
| Carrier phase offset | Pilot-referenced relative phase | Correct pilot calibration |
| Time translation | Fourier magnitude | Windowing and boundary conventions |
| Time dilation | Mellin magnitude under log-time translation | Correct transform measure and signal domain |
| Increasing path reparameterization | Full path signature | Bounded-variation path and tree-like equivalence |
| Observer projection | Quotient invariant | Only distinctions visible under that projection |
| Sensor remapping | Calibrated cross-channel feature | Identifiable transfer function and reference data |

No single transform preserves every useful property. The observer should select a representation based on the intended task and retain alternative views when their utility is close.

## Relation to Build 30

The frequency task chooses a harmonic token view; amplitude coding chooses a temporal token view; the mixed task chooses a combined boundary view and temporal token view. This supports task-relative representation selection.

The 8-PSK arithmetic experiment uses a representation whose phase multiplication exactly preserves the cyclic group operation on \(\mathbb Z/8\mathbb Z\). This is a more direct connection between signal form and computational logic.

The broader conjecture is not that every signal has one universal meaning. Rather, a system's useful identity may be expressed through compatible invariant relationships across several signal coordinate systems.
