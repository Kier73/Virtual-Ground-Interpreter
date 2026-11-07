# Build 12 empirical run — onset bug and corrected results

**Status:** the frozen Build 12 code is unchanged. The shipped `theory_development/empirical_results/build_12/` run is retained as the record of what the unmodified pipeline produced, but its EDT and C50/C80/D50 values are not valid room measurements. A reanalysis that moves `t = 0` to the direct-sound peak is provided in this folder.

- Reanalysis script: `reanalyze_corrected.py`
- Corrected file-level data: `rir_file_features_corrected.csv`
- Corrected room medians: `room_features_corrected.csv`
- Corrected RDMs: `rdm_*_corrected.csv`
- Side-by-side correlations: `rdm_view_correlations_comparison.csv`
- Full report: `build_12_report_corrected.json`

## 1. What went wrong

Build 12 finds the response onset with:

```python
onset_threshold = peak * 0.001  # -60 dB amplitude threshold
onset = next((i for i, v in enumerate(x) if abs(v) >= onset_threshold), 0)
```

This assumes the file begins at, or very near, the impulse. The Rochester corpus does not. Every one of the 90 WAVs contains a **1.000 s pre-roll of low-level noise** before the direct sound. The noise crosses the −60 dB threshold almost immediately, so the detector fires at a median of **968.8 ms before the direct-sound peak** (range 416–1000 ms).

The consequences:

- the Schroeder energy integral starts in the pre-roll, so its first 10 dB are dominated by noise and the EDT fit spans most of the 1 s pre-roll;
- the 50 ms and 80 ms “early” windows cover pre-roll noise rather than the direct sound and early reflections;
- late-energy fraction is ≈ 1 for every file;
- C50, C80, D50, Ts and the temporal view inherit the same misplaced origin.

Pre-peak energy is not negligible. Across the 90 files it is **0.85%–41.0% of total energy, median 10.6%**. Two files peak at sample 47980 and 48106; the other 88 peak at exactly sample 48000 (1000 ms at 48 kHz). The corpus is explicitly aligned so that the direct sound sits at 1.000 s.

### Why the synthetic tests missed it

The Build 12 unit tests generate signals that start at the impulse. In that regime the onset rule is correct. The bug is an interaction between a reasonable default and a corpus-level preprocessing convention, not an error the synthetic fixtures could expose. This is exactly the class of failure that an empirical run is for.

### Why T20 looked plausible while EDT did not

The T20 fit uses the −5 to −25 dB portion of the energy-decay curve. Even with the misplaced origin, that portion falls on the real decay after the direct sound, so T20 is largely unaffected. Across the 15 rooms, shipped and corrected T20 have Pearson **0.99996** and Spearman **1.0**. EDT fits 0 to −10 dB and therefore absorbs the pre-roll plateau, producing 4–60 s values. This internal dissociation — stable T20, impossible EDT — is itself diagnostic of an origin error rather than a bad decay estimator.

## 2. The correction

Each channel is trimmed at its direct-sound peak and the **unmodified** Build 12 `analyze_channel` is run on `x[peak_index:]`. No Build 12 source file, test, manifest, or shipped output was edited. Moving the origin to the peak is justified here because the corpus is aligned to that peak; the general fix for an arbitrary RIR would be an envelope/noise-floor onset detector, not a hard-coded 1 s trim.

Caveat: starting at the maximum sample discards the leading edge of the direct sound (sub-millisecond at 48 kHz, up to 2.2 ms in the two non-48000 files). This is negligible for octave-band EDT/T20 and C50, but it is a convention worth stating.

## 3. Corrected room results

`EDT` and `T20` in seconds; `C50` in dB; `pre` is the pre-peak energy fraction. Values are medians of six files per room.

| Room | EDT old | EDT corrected | T20 old | T20 corrected | C50 old | C50 corrected | pre |
|---|---:|---:|---:|---:|---:|---:|---:|
| Room1 | 39.59 | 0.451 | 0.262 | 0.281 | −40.83 | 9.05 | 0.162 |
| Room2a | 28.49 | 0.243 | 0.559 | 0.572 | −49.50 | 11.52 | 0.090 |
| Room2b | 28.63 | 0.228 | 0.395 | 0.405 | −47.70 | 13.73 | 0.075 |
| Room3 | 44.17 | 0.280 | 0.356 | 0.369 | −46.03 | 10.55 | 0.262 |
| Room4 | 32.93 | 0.489 | 0.475 | 0.483 | −53.92 | 5.17 | 0.030 |
| Room5 | 29.80 | 0.410 | 0.548 | 0.553 | −48.85 | 7.21 | 0.083 |
| Room6 | 28.12 | 0.491 | 0.498 | 0.491 | −53.16 | 4.65 | 0.112 |
| Room7 | 17.92 | 0.561 | 0.869 | 0.873 | −49.83 | 4.86 | 0.092 |
| Room8 | 16.96 | 0.892 | 1.008 | 1.012 | −50.18 | 2.95 | 0.129 |
| Room9 | 14.45 | 0.922 | 1.554 | 1.570 | −48.70 | 7.47 | 0.071 |
| Room10 | 19.06 | 0.921 | 1.103 | 1.113 | −45.54 | 1.01 | 0.066 |
| Room11 | 13.25 | 1.135 | 2.117 | 2.147 | −43.86 | 6.61 | 0.170 |
| Room12 | 9.86 | 1.412 | 2.153 | 2.165 | −51.44 | 4.77 | 0.134 |
| Room13 | 12.77 | 1.902 | 2.108 | 2.119 | −53.90 | −2.83 | 0.106 |
| Room14 | 6.63 | 3.099 | 3.154 | 3.161 | −47.25 | 0.07 | 0.122 |

Ranges after correction:

- EDT: **0.23–3.10 s** (shipped: 6.63–44.17 s)
- T20: **0.28–3.16 s** (shipped: 0.26–3.15 s)
- C50: **−2.8 to +13.7 dB** (shipped: −53.9 to −40.8 dB)
- D50: **0.34–0.96** (shipped: 4×10⁻⁶ to 2.8×10⁻⁴)

These are ordinary room-acoustic values. The corrected EDT ordering is also physically sensible: the small rooms (Room2a/b, Room3) are near 0.23–0.28 s, while the large/reverberant rooms (Room11–14) are 1.1–3.1 s. The shipped EDT ordering was **negatively** correlated with the corrected ordering (Spearman −0.89) because rooms with more pre-roll noise accumulated longer spurious EDTs.

## 4. What happens to the view geometry

Build 12 compares room RDMs for five feature views. The corrected correlations are:

| View pair | Shipped | Corrected | Δ |
|---|---:|---:|---:|
| decay ↔ early_late | 0.099 | **0.631** | +0.532 |
| decay ↔ temporal | 0.338 | **0.666** | +0.328 |
| early_late ↔ temporal | 0.714 | **0.737** | +0.024 |
| decay ↔ spectral | 0.154 | 0.099 | −0.055 |
| decay ↔ level | 0.271 | 0.222 | −0.049 |
| early_late ↔ spectral | 0.087 | 0.284 | +0.197 |
| early_late ↔ level | 0.182 | 0.318 | +0.136 |
| spectral ↔ temporal | 0.114 | 0.265 | +0.151 |
| spectral ↔ level | 0.083 | 0.082 | −0.001 |
| temporal ↔ level | 0.155 | 0.321 | +0.166 |

The corrected pattern is much more coherent and much more interesting than the shipped one:

- **Decay, early/late balance and temporal character now form a strongly aligned block** (0.63–0.74). This is the expected physical coupling: rooms that hold energy longer have weaker early-to-late ratios and different temporal envelopes.
- **Spectral shape stays comparatively independent** (0.08–0.28 with the other views). Absorption is frequency-dependent, so some coupling is expected, but spectral character is not just a restatement of RT.
- **Absolute level remains weakly related** to the other views (0.08–0.32), consistent with the build's decision to keep acquisition gain out of the normalized descriptors.

The shipped run's apparent early/late ↔ temporal relation (0.714) happened to survive, but for the wrong reason: both were dominated by pre-roll noise. The decay↔early/late relation, which should have been the strongest, was destroyed (0.099). A corrected analysis turns a noisy correlation matrix into a physically interpretable one. This is a good example of why the empirical loop matters: the synthetic suite verified the code paths, not the measurement convention.

## 5. Reproduction

```powershell
python theory_development\empirical_results\build_12\corrected\reanalyze_corrected.py
```

The script reads the extracted corpus at
`C:\Users\kross\AppData\Local\Temp\opencode\vl_data\rochester\wavs` (90 WAVs, 15 room folders), imports the frozen `theory_development/build_12/build_12.py`, and writes all outputs to this directory. Runtime is about one minute on the current machine (Python 3.14, standard library only). The run had zero failures.

## 6. Recommendation

Do not cite the shipped Build 12 EDT/C50/D50 numbers. Cite T20/T30 if needed, with the caveat that they were validated by the correction rather than invalidated by it. For any future Build 12 rerun, replace the threshold-onset rule with a direct-sound/envelope onset detector and add a regression test built from a signal with a long noise pre-roll. The frozen iteration remains frozen; this folder is the correction record.
