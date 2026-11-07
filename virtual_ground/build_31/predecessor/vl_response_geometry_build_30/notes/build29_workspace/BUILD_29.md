# Build 29 — Continuous Measurements to Observer-Relative Events

**Research prototype · Python 3.10+ · standard library only**

## Objective

Build 28 began with opaque event tokens and inferred recurring operation motifs without supplied operation boundaries. Build 29 moves one layer lower: it begins with continuous sampled measurements and proposes candidate event boundaries and opaque event tokens.

The learner receives only sampled signal channels, sample rates, frame configuration and observer-view choices. Synthetic hidden boundary positions and event classes are held separately for evaluation; they are never passed to `analyze_signals`.

## Main method

For channel `c`, frame `t`, window `w[n]`, and frame length `N`:

\[
X_{c,t}[k]=\sum_{n=0}^{N-1}x_c[tH+n]w[n]e^{-2\pi i kn/N}
\]

The frame representation contains:

- log-RMS and peak/RMS envelope features;
- zero-crossing rate;
- normalized spectral centroid and flatness;
- five normalized harmonic-band energy shares;
- spectral flux;
- four normalized Haar-like detail-energy shares;
- dominant-bin phase innovation and a local sinusoidal recurrence residual.

These are distinct views, not interchangeable invariants. Harmonic tokenization is largely gain invariant; temporal tokenization retains relative envelope information.

### Persistent change score

Rather than treating every adjacent-frame difference as a boundary, the detector compares short windows immediately before and after a candidate position. It combines between-window Jensen–Shannon divergence with within-window variability. This helps distinguish a persistent structural change from frame-to-frame fluctuation in stationary noise.

The main scores are:

\[
S_H=.60J_S+.10J_W+.07C+.23P
\]

\[
S_T=.72E+.18Z+.10J_W
\]

\[
S_C=.78S_H+.22S_T
\]

where `J_S` and `J_W` are within-window-corrected spectral and wavelet divergences, `C` is normalized centroid change, `P` is the local phase-discontinuity score, `E` is persistent envelope change, and `Z` is persistent zero-crossing change. The implementation clips component scores to bounded ranges.

A fused multi-observer score is the maximum channel score at each aligned frame. This is an OR-style fusion: one sensor may expose a change hidden by another. It can also admit sensor-specific false positives; channel-level evidence is retained.

### Boundary hypotheses

Three thresholds produce independent segmentations:

- sensitive: lower threshold floor 0.025;
- nominal: lower threshold floor 0.075;
- conservative: lower threshold floor 0.16.

A selected nominal segmentation is provided as a working representation, but alternatives remain in the result. A boundary is not an intrinsic fact merely because one threshold selected it.

### Event tokenization

Each segment receives a descriptor. Supported token views:

- `harmonic`: normalized spectral-band shape, wavelet detail profile, centroid and ZCR;
- `temporal`: baseline-relative log-RMS, within-segment RMS variation, peak/RMS and ZCR;
- `combined`: concatenation of the above.

A deterministic online nearest-prototype clusterer assigns opaque identifiers such as `evt_001`. These labels have no semantic meaning.

### Build 28 integration

The first ten signal-derived token streams are used to mine motifs with the actual Build 28 `mine_motifs` implementation. The final two streams are held out and segmented with those motifs. Ground truth event classes and boundaries are evaluator-only and are never passed to the motif miner.

## Controlled synthetic results

| Measurement | Result |
|---|---:|
| Synthetic continuous traces | 12 |
| Hidden event boundaries | 108 |
| Boundary TP / FP / FN | 108 / 0 / 0 |
| Boundary F1, ±2 frames | 1.000 |
| Pairwise token-class agreement | 1.000 |
| Discovered Build 28 motifs | 14 |
| Build 28 motif training / held-out traces | 10 / 2 |
| Stationary-tone selected boundaries | 0 |
| Stationary-noise selected boundaries | 0 |
| Gain-scaled harmonic boundary sets identical | Yes |

All results are synthetic and limited to the generated test distributions. They are implementation checks, not empirical sensor findings.

## Observer-view comparisons

The frequency-coded test favours harmonic and combined views. The amplitude-coded test is deliberately different: the carrier remains constant while the event class is encoded by envelope level. Harmonic tokenization collapses those events into one equivalence class, while temporal tokenization yields four classes. This is an intended observer-relative distinction, not a failure of Fourier analysis.

The phase-only test remains incomplete: the harmonic observer identifies 4 of 7 phase boundaries within tolerance, with no false positives. The current local phase residual is therefore a useful but incomplete cue, and phase-only event parsing remains open.

A weak amplitude-change fixture preserves multiple threshold alternatives. The sensitive and nominal views retain all seven boundaries; the conservative view retains only two. This illustrates how threshold choice expresses an observer's willingness to preserve weak distinctions.

## Raw WAV interface

`read_wav_channels` reads RIFF/RF64 PCM 8/16/24/32-bit and IEEE float 32/64-bit files, preserving interleaved channels. `analyze_wav.py` is the command-line entry point. Multi-channel fusion in this build requires channels to be already aligned, equal-length and at the same sample rate. Independent local-clock alignment is not inferred here; Build 25 contains the earlier clock-tracking work.

Example:

```bash
python analyze_wav.py fixtures/synthetic_dual_sensor.wav --view combined --token-view harmonic --output analysis.json
```

## Tests

Build 29 includes 23 unit tests for WAV parsing/round trips, sample and channel validation, observer-view behaviour, gain invariance, stationary noise/tone controls, threshold alternatives, phase limits, and finite feature outputs.

The combined regression runner also invokes the preserved Build 28 suite and its inherited Build 24–27 tests.

## Limitations

1. The controlled results are synthetic; no TAPS or other physical sensor recordings were processed.
2. The analysis uses fixed frame and hop sizes, although segmentation thresholds remain multiple hypotheses.
3. The detector assumes equal-length, aligned channels at a common sample rate. Asynchronous sensor-clock fusion is not implemented here.
4. Exact motif token clustering uses a finite greedy nearest-prototype rule and is order dependent.
5. Phase-only segmentation is partial (4/7 on the deliberately phase-only fixture).
6. Fused max pooling can allow one observer to dominate; this is recorded as channel evidence but not yet calibrated across real sensor transfer functions.
7. The three threshold settings are explicit engineering settings, not universal statistical significance levels.
8. Opaque event similarity and recurrence do not establish semantic meaning or causality.
9. Event boundaries are observer-relative hypotheses. A different feature view, frame size, sensor or intention may induce a different valid segmentation.

## Interpretation

Build 29 demonstrates a finite raw-measurement-to-event path. It computes harmonic, temporal and wavelet-derived frame descriptions, proposes event boundaries under multiple thresholds, assigns observer-relative opaque event tokens, and feeds those tokens into Build 28's motif discovery while keeping later traces held out.

The next challenge is not simply to lower thresholds. It is to learn which feature view, scale, observer fusion and boundary policy best preserve the distinctions needed by a particular task, and to do so without converting noise or sensor changes into false operations.

## Additional observer and control results

| Fixture | Observer | Result |
|---|---|---|
| Frequency-coded events | Harmonic | F1 1.000 (108/108 boundaries) |
| Frequency-coded events | Combined | F1 1.000 (108/108 boundaries) |
| Frequency-coded events | Temporal only | F1 0.201 |
| Amplitude-coded events | Temporal only | F1 0.750 |
| Amplitude-coded events | Harmonic only | No selected boundaries; four amplitudes collapse to one token |
| Phase-only events | Harmonic | F1 0.727 (4/7 boundaries; partial recall) |
| Stationary noise | Harmonic | Zero selected boundaries |
| Stationary tone | Harmonic | Zero selected boundaries |

The weak-amplitude fixture retained seven boundaries under sensitive and nominal thresholds, but only two under the conservative threshold. This is an explicit example of alternative observer segmentations.

The raw-WAV command-line path was exercised on a synthetic stereo PCM16 file: two channels, 8,192 Hz, 6,336 samples per channel and nine selected boundaries.
