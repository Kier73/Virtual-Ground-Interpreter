# TAPS held-out test split — empirical results

This directory records the first real paired-sensor run of the program: all 1,000
utterance pairs in the TAPS test split, analysed with Builds 13, 14 and 15. The
frozen builds themselves contain only synthetic smoke tests; everything here was
produced after unpacking the public archive. The source audio is not redistributed.

## 1. Dataset and integrity

| Item | Value |
|---|---|
| Corpus | TAPS Throat and Acoustic Paired Speech Dataset |
| Split | `test` |
| Archive | `TAPS_data_test.zip` |
| Archive size | 452,052,788 bytes |
| Archive MD5 | `7793d1272a4a0a3957a44014db283cbb` (verified) |
| Extracted members | 4,011 |
| Speakers | 10 (`p00`, `p02`, `p04`, `p21`, `p24`, `p26`, `p32`, `p38`, `p41`, `p56`) |
| Paired utterances | 1,000 (100 per speaker) |
| WAV files | 2,000 (throat + acoustic for every pair) |
| File format | 16 kHz, mono, PCM 16-bit, both channels |
| Pair metadata | `features.json` sampling rate 16,000 and matching `num_samples` |

The release is documented as 24-bit in some acoustic descriptions, but the test
archive actually contains 16-bit PCM. Both channels are already globally aligned
by the dataset preparation pipeline; the zero-lag residual is therefore expected
and is not independent evidence of sensor synchronization.

## 2. Build 13 — cross-modal RDM geometry

Command:

```powershell
python theory_development\build_13\scripts\analyze_taps.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_13_test `
  --max-speakers 10 --max-utterances-per-speaker 100 --permutations 99
```

Coverage and alignment:

- 1,000 / 1,000 pairs analysed, 0 skipped.
- Median residual envelope lag: **0 ms** (IQR 0).
- Median raw-waveform best normalized correlation: **0.622** at 4 kHz analysis rate.
- Median envelope correlation: **0.728** at zero extra shift.

Within-speaker RDM correlations (10 speakers, 100 utterances each; 99
within-speaker pair permutations):

| View | Median RDM Spearman | Speaker bootstrap 95% CI | Permuted null median | Null 95th pct | p |
|---|---:|---:|---:|---:|---:|
| `shared_spectral` | **0.233** | 0.153–0.327 | 0.002 | 0.031 | 0.01 |
| `temporal` | **0.293** | 0.198–0.373 | −0.003 | 0.028 | 0.01 |
| `periodicity` | **0.488** | 0.450–0.517 | −0.003 | 0.030 | 0.01 |
| `combined_common` | **0.359** | 0.347–0.428 | 0.001 | 0.031 | 0.01 |

The periodicity view is the strongest. This is physically plausible: both
sensors are recording the same voicing process, and the common-band F0 and
periodicity descriptors survive the very different transfer functions. The
shared spectral view is weaker but still positive. The combined view sits
between the spectral and periodicity views, as expected if it aggregates
partly redundant descriptors.

## 3. Build 14 — temporal emission and absolute rate

Command:

```powershell
python theory_development\build_14\scripts\analyze_taps_build14.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_14_test `
  --max-speakers 10 --max-utterances-per-speaker 100 --permutations 99
```

Build 14 reproduces the Build 13 views and adds two event-based views:

| View | Median RDM Spearman | Speaker bootstrap 95% CI | Permuted null median | p | Robust / z-score / rank |
|---|---:|---:|---:|---:|---|
| `temporal_emission` | **0.120** | 0.085–0.174 | 0.001 | 0.01 | 0.120 / 0.127 / 0.078 |
| `temporal_rate` | **0.189** | 0.124–0.303 | 0.000 | 0.01 | 0.189 / 0.174 / 0.167 |

The clock-invariant normalized interval-shape view (`temporal_emission`) is
positive and survives the within-speaker shuffled-pair null, but it is the
weakest of the six views. Absolute rate (`temporal_rate`) is somewhat stronger,
which is expected because it retains duration and speaking-rate information that
the normalized shape view deliberately discards. Neither event view approaches
the periodicity view.

Leave-one-feature-out medians stay close to the full-view values (0.106 for
`temporal_emission`, 0.176 for `temporal_rate`), so no single descriptor explains
the result. The minimum leave-one-out correlation can fall near zero, which is a
caution about feature redundancy rather than evidence of a hidden single cause.

## 4. Build 15 — local-clock event graphs

Command:

```powershell
python theory_development\build_15\scripts\analyze_taps_graphs.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_15_test `
  --max-speakers 10 --max-utterances-per-speaker 100
```

Frozen-build aggregate result (1,000 pairs, 0 skipped):

| Metric | Median | Speaker bootstrap 95% CI |
|---|---:|---:|
| Matched events per pair | 34.0 | — |
| Throat event coverage | 0.912 | 0.891–0.929 |
| Acoustic event coverage | 0.860 | 0.836–0.875 |
| Matched mark-rank Spearman | 0.705 | — |
| Matched interval Spearman | **0.122** | — |
| Median interval log error | 0.524 | — |
| Post-match clock scale | 0.991 | — |
| Post-match clock offset | −0.033 s | — |
| Post-match clock residual | **0.183 s** | — |

The headline number — 0.122 — is only slightly above the within-speaker
mismatched-pair null reported below. The near-unity clock scale and near-zero
offset are consistent with TAPS having been globally aligned, but a 0.183 s
median residual is far too large to claim event-level clock recovery: the
matched landmarks are not the same physical events to within a frame.

## 5. Build 15 external controls

The frozen build does not ship these controls. `build_15_controls.py` imports the
unmodified build and compares the frozen combined matcher with:

- **mark-only** matching (`mark_weight=1.0`, `interval_weight=0.0`);
- **interval-only** matching (`mark_weight=0.0`, `interval_weight=1.0`);
- **shuffled marks** within each stream (same times and mark distribution,
  wrong mark-to-event assignment);
- **shuffled interval order** within each stream (same first event time, gap
  multiset, event count, mark sequence and total duration; wrong gap order),
  under both the frozen combined weights and interval-only matching;
- **mismatched pairs** within speaker at cyclic shifts 1, 37 and 73 (same
  speaker, language and approximate duration; different utterance).

All values are medians of within-speaker medians over 10 speakers; brackets are
2,000-resample speaker bootstrap intervals.

| Condition | Matched events | Throat / acoustic coverage | Matched interval ρ | Clock residual (s) |
|---|---:|---:|---:|---:|
| True, combined (frozen) | 33.3 | 0.912 / 0.860 | **0.107** [0.097, 0.139] | 0.190 |
| True, mark-only | 32.0 | 0.885 / 0.831 | 0.019 [0.003, 0.037] | 0.209 |
| True, interval-only | 34.5 | 0.946 / 0.893 | **0.439** [0.418, 0.464] | **0.117** |
| True, shuffled marks | 33.3 | 0.910 / 0.850 | 0.101 [0.082, 0.114] | 0.177 |
| True, shuffled interval order | 33.5 | 0.914 / 0.855 | 0.064 [0.035, 0.072] | 0.226 |
| True, shuffled interval order (interval-only) | 34.0 | 0.930 / 0.870 | **0.356** [0.347, 0.366] | 0.198 |
| Mismatched, shift 1 | 31.5 | 0.908 / 0.846 | 0.094 [0.078, 0.103] | 0.225 |
| Mismatched, shift 37 | 31.5 | 0.911 / 0.847 | 0.085 [0.052, 0.103] | 0.224 |
| Mismatched, shift 73 | 31.5 | 0.899 / 0.848 | 0.091 [0.067, 0.102] | 0.227 |

Three things follow. (The 0.107 here versus 0.122 in the frozen report is the
difference between a median of within-speaker medians and a raw median over all
pairs; both are close to the null band.)

1. **The frozen combined matcher is dominated by mark rank.** Its interval
   correlation (0.107) is barely above the mismatched null (0.085–0.094) and is
   essentially the same as the shuffled-mark condition (0.101). Shuffling the
   gap order reduces it further, to 0.064, so the combined matcher does use some
   interval-order information; but the interval signal is small and the 0.78 mark
   weight was tuned on synthetic streams with informative, near-linearly related
   marks. On TAPS it crowds out the interval evidence.
2. **There is an utterance-specific interval signal, but the interval-only
   number is optimistic.** Interval-only matching reaches **0.439**, far above
   the mismatched-utterance null (0.085–0.094), so same-utterance throat and
   acoustic event sequences share normalized interval shape more than different
   utterances from the same speaker. That is consistent with the positive
   `temporal_emission` RDM result in Build 14. However, permuting the gap order
   within each same utterance's streams leaves **0.356**: the DP matcher can
   select and order similar interval contexts from the same marginals, and the
   reported Spearman is computed on pairs chosen with that same feature. The
   order-specific increment is therefore about 0.083, not the full 0.439. This is
   evidence for shared temporal structure and timing information, not proof of
   one-to-one event identity.
3. **Event-level clock recovery is not demonstrated.** Even the best condition
   leaves a 0.117 s median residual. TAPS is already globally aligned, so a true
   landmark correspondence should be much tighter. The affine clock fit is a
   diagnostic of alignment quality, not evidence of synchronization.

The frozen report's `matched_mark_rank_spearman = 0.705` should not be read as
independent evidence: the matcher selects pairs by mark rank, and the
shuffled-mark control still produces 0.708. The same caution applies to coverage
and median match cost, which are largely consequences of the monotone alignment
and the gap penalty.

### Detector sweep

`build_15_controls.py --mode sweep` re-ran the frozen combined matcher on 200
pairs (10 speakers × 20 utterances) under five detector settings:

| Frame (ms) | Min gap (ms) | Events (throat / acoustic) | Matched interval ρ | Clock residual (s) |
|---:|---:|---:|---:|---:|
| 10 | 80 | 46.3 / 48.3 | 0.088 | 0.170 |
| 20 | 40 | 49.5 / 50.0 | 0.158 | 0.192 |
| 20 | 80 | 41.3 / 42.8 | 0.127 | 0.186 |
| 20 | 160 | 26.8 / 30.3 | 0.055 | 0.184 |
| 40 | 80 | 33.5 / 35.5 | 0.130 | 0.214 |

The interval correlation is detector-dependent (0.055–0.158) and never becomes
strong under the frozen weights. The clock residual is stable at roughly
0.17–0.21 s. This is not the signature of a robust event-level correspondence.

## 6. What the TAPS results support

**Supported:**

- The same utterance produces genuinely similar cross-sensor response geometry
  at the RDM level. The effect is strongest for periodicity (ρ = 0.488), then
  combined common features (0.359), temporal descriptors (0.293) and shared
  spectral shape (0.233). All exceed within-speaker shuffled-pair nulls by a
  wide margin.
- Normalized event-interval shape carries a modest but real utterance-specific
  signal (Build 14 `temporal_emission` ρ = 0.120; Build 15 interval-only
  matching ρ = 0.439 against a 0.085–0.094 mismatch null, with an order-shuffled
  same-utterance control at 0.356 that limits how much of that value can be
  attributed to temporal order).
- The result is stable across robust, z-score and rank normalization, and no
  single feature drives the temporal-emission view.
- TAPS is an easy case for alignment (0 ms residual envelope lag, 0.728 envelope
  correlation), so the positive RDM result is not a re-alignment artifact.

**Not supported:**

- That Build 15's frozen combined matcher recovers event correspondences. Its
  interval correlation is near the mismatch null and the shuffled-mark control.
  Even the stronger interval-only result is partly a matcher-selection effect:
  same-utterance gap-order shuffling leaves 0.356, and matched pairs are chosen
  using the interval features used in the evaluation.
- That the affine clock fit identifies synchronized clocks. The residual is
  ~0.18 s under the frozen matcher and ~0.12 s under interval-only matching,
  despite the released files being globally aligned.
- That the result is a universal cross-modal invariant. This is one corpus, one
  sensor pair, ten speakers and a single held-out split.
- That the result identifies emotion, intention or hidden psychological state.
  TAPS has no emotion labels in the documented schema and none were inferred.

## 7. Relation to the rest of the program

This is the first empirical result in the archive that is both cross-sensor and
positive. It is weaker than the corrected Build 12 room result in absolute
effect size for the decay block, but it answers a different question: whether two
different physical sensors observing the same event preserve a shared response
geometry. At the RDM level, they do.

The result also reproduces the program's central pattern. A method that looked
strong in synthetic validation (Build 15's combined matcher, F1 = 0.932) met a
real domain where one of its assumptions — informative mark ranks — was weaker
than expected. The correct response is not to declare the local-clock idea
false, but to separate the validated part (interval-shape information survives
at the RDM level and as a modest order-specific event signal) from the
unvalidated part (the frozen matcher recovers the right events and the clock
fit is meaningful).

## 8. Caveats

- **One corpus, one split.** Ten speakers, 100 utterances each, test split only.
- **TAPS is preprocessed.** The files are resampled and globally aligned. The
  zero-lag result cannot test hardware-clock synchronization.
- **No event-level ground truth.** TAPS has no labelled latent-state event
  correspondences. Interval-only matching can exploit shared rhythm without
  matching the same physical landmark.
- **RDM dependence.** The 100 utterances per speaker are not independent draws;
  the bootstrap resamples speakers, not utterances, which is the conservative
  choice but still only ten units.
- **Multiple views.** Six views were examined. The periodicity result is large
  enough that multiple-comparison correction would not remove it, but the
  temporal-emission result is modest and should be treated as exploratory.
- **Detector dependence.** Build 15's event-level interval correlation varies
  from 0.055 to 0.158 across detector settings; the Build 14 RDM result uses a
  fixed 20 ms / 80 ms detector.
- **Null coverage.** The controls use within-speaker mismatched pairs, shuffled
  marks and shuffled interval order. Shuffling the interval order within the
  same utterance leaves an interval-only correlation of 0.356, so the matcher can
  find similar interval contexts without the true temporal sequence. The
  order-specific signal is the difference from that control, not the full
  interval-only value.
- **Privacy.** All outputs are aggregate-only. Speaker IDs, utterance IDs,
  transcripts, demographics and per-utterance rows are not exported.

## 9. Reproduction

```powershell
# Build 13: RDM geometry
python theory_development\build_13\scripts\analyze_taps.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_13_test `
  --max-speakers 10 --max-utterances-per-speaker 100 --permutations 99

# Build 14: temporal emission and rate
python theory_development\build_14\scripts\analyze_taps_build14.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_14_test `
  --max-speakers 10 --max-utterances-per-speaker 100 --permutations 99

# Build 15: frozen local-clock graphs
python theory_development\build_15\scripts\analyze_taps_graphs.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_15_test `
  --max-speakers 10 --max-utterances-per-speaker 100

# Build 15: external controls and detector sweep
python theory_development\empirical_results\taps\build_15_controls.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_15_controls `
  --max-speakers 10 --max-utterances-per-speaker 100 `
  --null-shifts 1 37 73 --mode controls
python theory_development\empirical_results\taps\build_15_controls.py `
  --root <TAPS_data_test>\test --split test `
  --output theory_development\empirical_results\taps\build_15_controls `
  --max-speakers 10 --max-utterances-per-speaker 20 --mode sweep
```

## 10. Files

| Path | Contents |
|---|---|
| `build_13_test/build_13_report.json` | Build 13 aggregate report |
| `build_13_test/rdm_view_summary.csv` | Build 13 view table |
| `build_13_test/alignment_summary.csv` | Lag and envelope diagnostics |
| `build_14_test/build_14_report.json` | Build 14 aggregate report with temporal views |
| `build_14_test/rdm_view_summary.csv` | Build 14 view table including normalization and LOO |
| `build_15_test/build_15_report.json` | Frozen Build 15 aggregate report |
| `build_15_controls/build_15_controls.json` | Feature-weight, shuffled-mark and mismatched-pair controls |
| `build_15_controls/build_15_detector_sweep.json` | Detector frame/gap sweep |
| `build_15_controls.py` | External control script (does not modify frozen builds) |

The TAPS audio, metadata and derived per-pair features are not included. The
reports contain only aggregate statistics and no speaker or utterance identifiers.
