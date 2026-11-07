# Build 15 — Local-clock event graphs

## Status

- Build 14's paired WAV reader and RMS-envelope event detector are carried forward.
- New event matcher: monotone dynamic-programming alignment across independent observer clocks.
- New event graph: observer-local successor edges, recurring interval-motif edges, and inferred cross-observer correspondence edges.
- Clock offset and scale are fitted *after* matching; no cross-clock timestamp differences are used by the matching objective.
- Test suite: 44 passing tests.
- Synthetic stress test: 30 trials, 50 latent events per trial, 10% event dropout, five false events per second-observer stream, independent affine clock and amplitude transformations, and small measurement noise.
- Mean synthetic precision 0.917, recall 0.948, F1 0.932. These are software validation metrics against generated ground truth, not empirical sensor findings.
- No TAPS audio was available in this runtime; no empirical TAPS event graphs or correlations are claimed.

## 1. Working conjecture

A system may expose temporal relationships through the event trace observed along its evolution. Distinct observers need not share a common clock coordinate to compare some of those relationships. They may preserve event order, recurrence structure, and locally normalized interval patterns; inferred event correspondence can then support a post-hoc estimate of clock offset and rate.

This is an operational hypothesis about observable event streams. It does not claim that time is a physical substance emitted by states, or that an envelope landmark is a true latent-state transition.

## 2. Local event-stream model

For observer A and observer B:

\[
E_A=\{(\tau_i,a_i)\}_{i=1}^{n},\qquad
E_B=\{(\sigma_j,b_j)\}_{j=1}^{m}.
\]

Here \(\tau_i\) and \(\sigma_j\) are local timestamps, and \(a_i,b_j\) are measured event marks. The coordinate systems are independent. The matcher does not assume or require a known transformation between them.

Within each stream, marks are mapped to average empirical ranks \(r_i\in[0,1]\). Intervals are normalized by their own median and log-transformed:

\[
\delta_i=\tau_{i+1}-\tau_i,\qquad
\ell_i=\log\left(\frac{\delta_i}{\operatorname{median}(\delta)}\right).
\]

Each event receives a local feature formed from its mark rank and adjacent interval context. This removes the arbitrary time origin and positive uniform clock scale while preserving event order. It intentionally discards absolute rate at the matching stage.

## 3. Monotone sequence alignment

The current event-pair cost is:

\[
c(i,j)=0.78|r_i-r_j|+0.22\min\left(\frac{|\ell_i-\ell_j|}{2},1\right).
\]

The weights sum to one. The dynamic-programming recurrence is:

\[
D(i,j)=\min\begin{cases}
D(i-1,j-1)+c(i,j) & \text{match},\\
D(i-1,j)+g & \text{skip A},\\
D(i,j-1)+g & \text{skip B},
\end{cases}
\qquad g=0.36.
\]

The traceback yields ordered correspondence edges plus skipped events. Alignment cost and `1 - pair_cost` are ranking diagnostics, **not calibrated probabilities**. The algorithm is order-preserving; it does not handle arbitrary reordering of events.

Matching depends on measured mark ranks and normalized interval context. It is not guaranteed to recover the correct correspondences when those features are uninformative, heavily distorted, or extracted under incompatible observer rules.

## 4. Event graph

The coupled graph is

\[
G=(V_A\cup V_B,\ E_{succ}\cup E_{rec}\cup E_{corr}).
\]

- **Successor edges** preserve the local event order of each observer and carry the within-stream interval divided by its median.
- **Recurrence edges** link similar two-interval motifs within one observer. The current Euclidean motif tolerance is 0.18 in log-normalized interval coordinates; this is a transparent exploratory threshold, not a learned or empirically optimized value.
- **Correspondence edges** connect event nodes inferred to represent matching landmarks across observers.

There are deliberately no cross-observer edges that encode raw timestamp differences. The graph contains local timestamps for inspection, but matching is driven by normalized features and sequence order.

## 5. Recovering the clock relation after matching

Given matched event pairs, a robust Theil–Sen fit estimates:

\[
\tau \approx \alpha+\beta\sigma.
\]

The median of pairwise slopes estimates \(\beta\); the median residual intercept estimates \(\alpha\). Median and maximum absolute residuals are reported. The fit is downstream of the correspondence calculation. It is a diagnostic of how well a simple affine local-clock relation explains the inferred matches, not evidence that the clocks were physically synchronized.

If the underlying process has non-affine clock drift, dropped events, sensor latency changes, or true tempo variation, this affine fit may fail even when some event-graph relationships remain useful.

## 6. Synthetic stress test

`reports/synthetic_local_clock_stress.json` contains all 30 trial results and aggregate metrics.

| Measure | Mean across trials |
|---|---:|
| Precision | 0.917 |
| Recall | 0.948 |
| F1 | 0.932 |
| Left-stream event coverage | 0.939 |
| Right-stream event coverage | 0.932 |
| Median absolute post-match clock-fit residual (median across trials) | ~0.0008 s |

Scenario: 50 latent events per trial; observer B has a clock `17 + 2.75 × latent_time`, Gaussian time jitter (SD 3 ms), and marks transformed as `1.7 + 3.1 × latent_mark` with Gaussian noise (SD 0.01). Ten percent of true events are dropped from B and five additional false events are inserted. Matching uses neither the known clock mapping nor latent event IDs; IDs are retained only by the test harness for precision/recall scoring.

These values are not a speech result. The synthetic event marks are relatively informative and the noise model is controlled. Real sensor landmarks can differ more substantially.

## 7. TAPS integration

`build_15.py` uses the inherited Build 14 WAV reader and event detector. `scripts/analyze_taps_graphs.py` processes the held-out TAPS test split after it has been downloaded and extracted:

```bash
python scripts/fetch_taps.py --split test --output data/raw
python scripts/analyze_taps_graphs.py \\
  --root data/raw/TAPS_data_test/test \\
  --split test \\
  --output reports/taps_test_build15
```

Default outputs are aggregate-only. Internal speaker grouping supports speaker-level bootstrap summaries; raw speaker identifiers, utterance identifiers, transcripts, demographic fields, raw audio and per-utterance results are not exported. The inherited TAPS license/redistribution notes in `LICENSES.md` still apply.

TAPS has no known hidden-state event correspondences for evaluating event-level match precision. Its cross-modal graph statistics can therefore measure consistency/coverage, not prove that matched landmarks are physically identical state transitions. A labelled or independently instrumented event corpus would be needed for that validation. In addition, the released TAPS files were resampled and globally aligned by the dataset preparation pipeline. TAPS can test whether the matcher recovers event correspondence without consuming the shared timestamps, but it cannot by itself validate an acquisition system whose hardware clocks were never synchronized.

## 8. Falsification and limitations

The local-clock hypothesis should be weakened or rejected for a data domain when:

- correspondence collapses under mild independent clock offset/scale changes;
- matching is no better than shuffled-mark or shuffled-order controls;
- event extraction thresholds cause unstable graph structure;
- inferred affine clock fits have large residuals when the instrument clock is known to be affine;
- event correspondences fail to generalize to held-out speakers or a separately calibrated sensor domain.

Additional controls should compare (1) marks only, (2) interval context only, (3) the combined cost, (4) shuffled marks, (5) shuffled event order, and (6) altered event detector thresholds. Current Build 15 tests affine invariance and known synthetic correspondences but does not yet claim all these empirical controls.

## 9. Privacy and scope

No speaker identification, emotion inference or psychological-state inference is performed. The pipeline writes aggregate metrics only. The synthetic report includes synthetic trial-level diagnostics, not participant information.
