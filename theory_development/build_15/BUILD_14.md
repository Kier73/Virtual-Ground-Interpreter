# Build 14 — Temporal emission and observer-dependent response geometry

## Status

- Build 13's paired acoustic/throat-vibration analysis engine is carried forward.
- A temporal-emission layer now extracts event-time landmarks from each channel's short-time RMS envelope.
- Normalized event-interval shape and absolute event rate are measured separately.
- RDM robustness diagnostics now compare robust-MAD, z-score and rank scaling, plus leave-one-feature-out sensitivity.
- Unit tests: 27 passing after the temporal extension.
- Synthetic pipeline smoke test: 30 synthetic pairs across three synthetic groups; all 30 processed.
- **TAPS empirical audio analysis remains pending.** The public test archive is 452.1 MB; the current runtime cannot resolve external hosts, so no real TAPS audio was processed.
- No source audio, transcripts, speaker IDs or demographics are included in this package.

## 1. Working conjecture

A system's temporal relations may be observable as a trace emitted by its evolution: event times, dwell intervals, recurrence, phase and rate. This is an observer-dependent description of a trajectory, not a claim that time is a physical substance radiated by a state.

Build 14 uses one narrow operational proxy: local maxima in a short-time RMS amplitude envelope. These peaks are signal landmarks. They are **not** assumed to be phonemes, labelled state transitions or privileged physical events.

## 2. Formalization

Let a described trajectory be observed by observer/probe configuration \(O\). The observer extracts a marked event sequence:

\[
\mathcal E_O[\gamma]=\{(t_i,m_i)\}_{i=1}^{N},\qquad t_{i+1}>t_i.
\]

Here \(t_i\) is an observed landmark time and \(m_i\) is its normalized envelope mark. The inter-event intervals are

\[
\Delta_i=t_{i+1}-t_i,\qquad
\widetilde{\Delta}_i=\frac{\Delta_i}{\operatorname{median}(\Delta)}.
\]

The current implementation separates two kinds of temporal information:

- **Shape:** interval coefficient of variation, interval entropy, normalized interval quantiles and normalized mark variation.
- **Rate / duration:** event rate \(\lambda=N/T\) and median interval in seconds.

Under an affine change of clock coordinate

\[
t'_i=a+c t_i,\qquad c>0,
\]

we obtain

\[
\widetilde{\Delta}'_i=\widetilde{\Delta}_i,\qquad
\lambda'=\lambda/c,\qquad
\operatorname{median}(\Delta')=c\operatorname{median}(\Delta).
\]

Thus the *normalized interval shape* is invariant to origin and uniform clock scale, conditional on the same event set and consistently scaled observer resolution. Absolute rate and dwell time are intentionally not invariant. This does not imply that the underlying physical process is unchanged when its true duration changes.

The observer \(O\) includes the sensor, sample rate, envelope window, event threshold and minimum event separation. Different observers can extract different event sets from the same underlying trajectory.

## 3. Event extraction rule

1. Convert the channel to a 20 ms non-overlapping RMS envelope.
2. Estimate a threshold as \(\max(P_{60},\operatorname{median}(e)+0.5\operatorname{MAD}(e))\).
3. Select local maxima above threshold.
4. Greedily retain peaks separated by at least 80 ms, preferring the larger peak.
5. Normalize event marks by the largest selected mark; normalize intervals by their median.

This is intentionally a transparent baseline, not a learned segmenter. The rule may miss low-amplitude or closely spaced events. It should be replaced or compared with alternatives only through held-out tests.

## 4. Geometry tests

For each speaker, acoustic and throat features are independently standardized, pairwise distances are formed, and their upper-triangle RDMs are compared by Spearman correlation. Pairing is within speaker; raw speaker identifiers and transcripts are not exported.

Build 14 adds three diagnostics:

- **Normalization sensitivity:** RDMs under robust-MAD, z-score and rank scaling.
- **Feature sensitivity:** leave one feature out at a time; report median and minimum correlation.
- **Temporal separation:** compare `temporal_emission` (normalized interval shape) separately from `temporal_rate` (absolute rate and interval duration).

These are robustness diagnostics, not independent replications. The shuffled-pair permutation null and speaker bootstrap remain in place.

## 5. Current synthetic result

The smoke test processed 30 deliberately paired synthetic signals (three synthetic groups, ten pairs each). The temporal interval-shape RDM correlation was about 0.42; the rate view was about 0.51. Other deliberately shared synthetic views were higher. This only verifies that the new measurement path executes and can distinguish descriptor families. It is **not** a TAPS result, a speech-science result or evidence of a universal invariant.

The event-time mathematical tests passed for translation, uniform clock dilation (with observer time resolution scaled consistently), amplitude-mark gain normalization and the expected rate transformation.

## 6. Empirical TAPS run

Download only the held-out test split (about 452 MB):

```bash
python scripts/fetch_taps.py --split test --output data/raw
```

Run the analysis on the extracted `test` directory:

```bash
python scripts/analyze_taps_build14.py \
  --root data/raw/TAPS_data_test/test \
  --split test \
  --output reports/taps_test_build14 \
  --max-speakers 10 \
  --max-utterances-per-speaker 100 \
  --permutations 199
```

For the full published test split, each of the 10 held-out speakers contributes up to 100 utterances. A smaller cap is useful for an initial local check but should not be presented as full-split evidence.

## 7. Interpretation and falsification

The temporal-emission view earns further attention only if it:

- exceeds within-speaker shuffled-pair controls on held-out speakers;
- remains directionally stable across normalization choices;
- is not dominated by a single feature;
- responds predictably to controlled clock scaling and event-extraction changes;
- replicates in a second paired-sensor domain after sensor calibration.

A result that disappears under small changes to observer resolution, event threshold or feature scaling is evidence of observer dependence, not an invariant. A result that survives one dataset is still not universal.

No emotion inference, speaker identification or psychological-state inference is performed.

## 8. Next empirical step

Run the TAPS test split and compare the temporal-shape and absolute-rate views against the existing spectral, periodicity and temporal views. Then evaluate a separate paired mechanical sensor corpus. Keep the source domains independent; do not pool them before each has been analysed and calibrated on its own terms.
