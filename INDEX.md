# VL Response Geometry — archive index

This directory contains the complete 30-build "Virtual Layer / response geometry" program, unpacked into isolated, runnable iterations. The pre-Virtual-Ground work lives in `theory_development/` (Builds 01–19); the interpreter core lives in `virtual_ground/` (Builds 20–30). The original ZIPs are preserved unchanged in `archives/`, which is gitignored except for its checksum manifest. Builds **16** and **24** were not shipped as standalone archives: Build 16 is embedded in Build 17, and Build 24 is embedded in Builds 25/26. All other builds have their own directory.

The archive now has two arcs:

1. **Builds 01–15 — response geometry and empirical acoustics.** The program starts with a mathematical question — can an observer's measured response geometry be separated from the algebraic identity of a system? — and ends by testing whether any of that structure survives real acoustic and vibration measurements.
2. **Builds 16–30 — representations and the Virtual Ground interpreter.** Builds 16–19 sharpen the representation-theoretic tools. Builds 20–30 pivot to a separate research program: an operational definition of a "Virtual Ground", then a synthetic pipeline from active ground identification and inductive synthesis to online tracking, partial grounds, event discovery, raw-signal segmentation, and signal-coded computation.

The short answer for the first arc: the early universal invariants did not survive stronger controls, but the empirical layer eventually produced two modest, physically coherent results — corrected room acoustics and paired throat/acoustic speech geometry — while the most ambitious event-level matcher failed its strongest control. The second arc is a methodological program: it builds a bounded, self-falsifying interpreter, but processes no empirical sensor data and makes no physical claim.

## Layout

```
VL_Response_Geometry/
├── archives/                  original build ZIPs + SHA256SUMS.txt (28 archives)
├── theory_development/        Builds 01–19: response geometry and empirical acoustics
│   ├── build_01/ … build_15/  frozen, self-contained build trees
│   ├── build_17/ … build_19/  Build 16 is embedded in build_17
│   └── empirical_results/
│       ├── build_12/
│       │   ├── …              first Rochester RIR run (shipped, onset-bugged)
│       │   └── corrected/     corrected reanalysis + FINDINGS.md
│       └── taps/              held-out TAPS runs for Builds 13–15
├── virtual_ground/            Builds 20–30: the Virtual Ground interpreter
│   ├── build_20/ … build_23/  operational foundations
│   └── build_25/ … build_30/  Build 24 is embedded in build_25/legacy and build_26/notes
├── test_results/
│   ├── build_01.txt … build_15.txt
│   ├── build_17.txt … build_30.txt
│   ├── build_24_30_embedded/  fresh embedded-chain logs + combined summary
│   ├── MANIFEST_VERIFICATION.txt  1,907/1,907 hashes
│   └── SUMMARY.md              765/765 top-level, 177/177 embedded, environment, caveats
├── run_all_tests.py           orchestrates every top-level build's unittest suite
├── INDEX.md                   this file
└── PERSPECTIVE.md             interpretive essay on the whole arc
```

Each build is frozen. Shared code was deliberately **not** refactored across builds: later builds carry forward earlier code so that each archive remains a self-contained record of what was believed and measured at that point. The nested `legacy/`, `notes/` and `verification/` trees are part of that record; they are not duplicates to be deleted. All builds use the Python standard library only.

## Build map

| # | Theme | Main move | Outcome |
|---|---|---|---|
| 01 | Observer-dependent response geometry | Algebraic identity, fixed probes, four response coefficients → point on S³; AR(2) resonance | Implementable, internally testable prototype. No universal tone space or cross-modal claim. 15 tests. |
| 02 | Shape, movement, observer, geometric phase | Same ellipse at different speeds; rank-deficient observer; limit cycle | Geometric phase is invariant under monotone reparameterization, while temporal signatures change; projection can erase phase. 10 tests. |
| 03 | Codonic connection geometry | Shear transports around closed walks; observer quotient | Three shears compose to a rotation; transport is path-dependent and non-commutative. 16 tests. |
| 04 | Hopf fibration and holonomy | Horizontal transport of S³ paths over S² loops | Fibre phase behaves correctly under reversal, representative shifts, non-circular loops and sampling refinement. 19 tests. |
| 05 | Active observation | Intention-conditioned probe selection | Probes can be chosen for a target variable; performance degrades gracefully with noise. 17 tests. |
| 06 | Active observation on S³ | Observer families, finite observable quotients, antipodal control | Observer-specific equivalence classes and probe policies are computable on the Hopf geometry. 31 tests. |
| 07 | Cross-observer invariant discovery | RDM correlations, nearest-neighbour overlap, block-aware permutations | Strong result: base shape ↔ local transition **ρ = 0.693**, empirical p = 0.011 (Holm 0.022). Framed as a candidate, not a universal invariant. 22 tests. |
| 08 | Generalization and perturbation | 40 randomized path families, degradation sweeps, substrate controls | The Build 07 signal weakens to **ρ = 0.272** (bootstrap CI 0.208–0.464; 5-NN Jaccard 0.143). Shape ↔ temporal is 0.095 (n.s.). The earlier value depended substantially on the designed path library. 17 tests. |
| 09 | Matched cross-modal positive control | Acoustic-like and mechanical oscillators with the same second-order pole structure | Spectral/phase/temporal RDMs align at **ρ ≈ 0.9999999**. A pipeline validation, explicitly not a universal cross-modal invariant. 24 tests. |
| 10 | Heterogeneous systems and active probing | Independently drawn multi-modal acoustic and mechanical systems; shuffled nulls | **Negative result:** no cross-domain geometry beyond the column-shuffled control (MST-edge gap 0.0719 vs null mean 0.0533). Build 09's near-identity does not generalize. 25 tests. |
| 11 | First empirical vibration excerpt | 411 rows / 8 source-contiguous windows from a real smartphone G-Force recording | Descriptive pre/event/post contrasts (median-centred RMS ≈ 0.50–0.52 g before, 0.61–0.90 g inside, 1.51–1.74 g after), but only eight windows from one recording. No cross-modal claim. 17 tests. |
| 12 | Rochester room-impulse-response geometry | Standard-library WAV ingestion; decay, early/late, spectral, temporal and level views; room RDMs | First real acoustic corpus: 90 WAVs, 15 room folders (14 rooms; Room 2 is split into with/without-windows variants). The shipped run has a **pre-roll onset bug** (EDT 6.6–44.2 s, C50 ≈ −54 to −41 dB). Corrected: EDT **0.23–3.10 s**, T20 **0.28–3.16 s**, C50 **−2.8 to +13.7 dB**; decay/early-late/temporal views align at 0.63–0.74. 17 tests. |
| 13 | TAPS paired throat/acoustic speech | Same utterance recorded by accelerometer throat microphone and acoustic microphone; within-speaker RDMs, shuffled-pair null, speaker bootstrap | Held-out TAPS test split: **1,000 / 1,000 pairs, 0 skipped**; within-speaker RDM **ρ = 0.233** shared spectral, **0.293** temporal, **0.488** periodicity, **0.359** combined; all p = 0.01 against shuffled-pair nulls (99 permutations). 18 tests. |
| 14 | Temporal emission | Event landmarks from short-time RMS envelopes; normalized interval shape vs absolute rate; normalization and leave-one-feature-out diagnostics | Temporal layer added to Build 13. Held-out TAPS: **temporal_emission ρ = 0.120**, **temporal_rate ρ = 0.189**, both p = 0.01; stable across robust/z-score/rank normalization; no single feature dominates. 27 tests. |
| 15 | Local-clock event graphs | Monotone DP alignment on within-stream mark ranks and normalized interval shape; successor, recurrence and inferred-correspondence graph; affine clock fit only after matching | Synthetic 30-trial stress test: precision 0.917, recall 0.948, F1 0.932. Held-out TAPS: 1000/1000 pairs, median 34 matched events, coverage 0.91/0.86, frozen combined matched-interval **ρ = 0.122**, clock residual 0.183 s. External controls show combined ρ ≈ 0.107 vs mismatch 0.085–0.094 and shuffled marks 0.101; interval-only reaches **0.439**, but same-utterance gap-order shuffling leaves 0.356, so the order-specific increment is about 0.083. 44 tests. |
| 16 | Falsifying event correspondence; harmonic representations | Matcher ablations, independent B-mark and event-order shuffles, quadratic clock drift, unitary DFT and graph-Fourier prototypes | The combined matcher does **not** beat mark-only on the synthetic benchmark (F1 0.926 vs 0.932); mark ranks dominate, and shuffling event order collapses F1 to 0.043. DFT/Parseval and graph-spectrum checks are at roundoff. 24 new tests; embedded in Build 17. |
| 17 | Temporal representations under clock symmetries | Fourier magnitude, circular STFT, undecimated Haar-like energies, log-time Mellin magnitude, event-graph Laplacian under translation, dilation and nonlinear drift | Each representation exposes a different invariant or covariance; there is no universal transform. Fourier magnitude is shift-invariant but fixed-bin dilation-mismatched; Mellin is scale-invariant on the periodic log grid; graph spectra depend strongly on the motif threshold. 83 tests (including Builds 14–16). |
| 18 | SU(2)/S³ relational atlas | Symmetric-power representations, Hopf map and fibre subgroup, antipodal parity, numerical Schur orthogonality, intertwiners, truncated path signatures | The Hopf quotient makes observer loss algebraic: all odd half-integer-spin modes vanish, integer spins retain one zero-weight direction. Antipodal/fibre checks are at roundoff; Monte Carlo Schur residual ≈ 5.45e-3. Mathematical fixtures only. 21 tests. |
| 19 | Endpoint, path and observer equivalence | Seven deterministic quaternion paths; endpoint harmonics, path signatures and observer-specific Gram kernels | Endpoint harmonics cannot distinguish different paths with the same endpoint; signatures separate them from degree 2. Observer quotients produce the predicted loss hierarchy. **Endpoint features are redundant** given a known start and signature level one. Synthetic. 39 tests. |
| 20 | Virtual Ground and compositional navigation | Formalize the "Virtual Ground"; Rotor-4 reversible group fixture and Support-9 irreversible symbolic fixture | A Virtual Ground is the generative operational logic, not the materialized state space. All 648 Rotor-4 states are reachable (diameter 8); Support-9 has 232 reachable stable states; a layer-count observer is not transition-congruent. 43 tests. |
| 21 | Controlled variables, endogenous flow, ground revision | Deterministic two-reservoir canal; observation/action partition refinement; belief policies; viability; resource trade-offs; versioning | 64 states / 136 transitions with exact mass balance. No selected coarse observation is memoryless; sensor value is task-relative (LEVELS beats TOTAL_PHASE for one intention). Controlled viability kernel 35 states vs 0 for HOLD-only. 32 tests. |
| 22 | Active discovery of Virtual Grounds | 32 candidate grounds, 324 probes, passive comparator, open-world holdout, revision monitor | All 32 in-family grounds identified in at most two probes (mean cost 6.375); passive 12-step HOLD identifies none. An out-of-family constant-inflow law mimics the selected model until a holdout probe. Revisions are proposals only. 47 tests. |
| 23 | Inductive synthesis of grounds | Bounded symbolic grammar; five synthetic grounds; executable program specifications; grammar refinement | 1,930 training and 521 held-out transitions predicted exactly, plus exhaustive finite-domain exactness. A mod-3 learner fails a mod-4 ground until the grammar is expanded. Capacity is sometimes only a lower bound. 21 tests. |
| 24 | Latent context discovery | L*-style observation table; hidden phase removed; delayed counterexample; compile to modular phase or finite automaton | Observer quotients of 2/3/6 contexts; eight physical modes collapse to one under a constant sensor. A one-context model passes depth 5 and fails at depth 6. Non-bijective HOLD stays an automaton. 17 tests; embedded in Builds 25/26. |
| 25 | Non-resettable online tracking | Belief over predictive contexts; asynchronous partial channels; contradiction quarantine; per-source clocks; risk-aware probes; bounded memory | Unknown-start tracking works on a synthetic stream; two anchors are required for an affine clock fit; one contradiction is quarantined and persistent conflicts only produce a revision proposal. 34 tests. |
| 26 | Incremental partial Virtual Ground | No precompiled machine; unknown edges remain unknown; horizon refinement; bounded stream memory; executable partial ground | Partial predictive quotients recovered; delayed distinction appears at the sixth event; a 200-event stream with a 64-event retention cap stays bounded. Unknown transitions fail closed. 27 tests. |
| 27 | Competing explanations and operation discovery | Nine explanation candidates from noise to regime change; opaque event signatures; ordinal evidence; discriminating probes | Two recurring operation signatures recovered, with 6/6 held-out predictions. A deliberate out-of-family counterexample is correctly rejected. Evidence scores are ordinal, not probabilities; revision is never automatic. 30 tests. |
| 28 | Boundary discovery from event streams | Exact contiguous n-gram motifs, nested-motif audit, ordered-shuffle maximum-statistic null, sparse-checkpoint effect equations | Four motifs discovered; synthetic boundary precision/recall/F1 = 1.000; 24/24 held-out checkpoint deltas correct. Shuffled control: 42 raw candidates → 0 after the null screen. Ambiguous parses are retained. 21 tests. |
| 29 | Continuous measurements to observer-relative events | Frame features, persistent change score, three threshold hypotheses, harmonic/temporal/combined token views; WAV ingestion | Synthetic 108/108 boundaries and token purity 1.000. Harmonic view is perfect on frequency-coded events but collapses amplitude-coded events; temporal view is better there (F1 0.750). Phase-only remains partial (4/7). Stationary tone/noise produce zero selected boundaries. 24 tests. |
| 30 | Adaptive observers and signal-coded computation | Nine observer profiles selected on calibration traces; FSK control plus 8-PSK operand phasors for Z/8 arithmetic | Held-out boundary F1 0.770/0.748/0.839 and token accuracy 1.000/1.000/0.969 across three task families. All 128 noiseless modular operations correct; 90.63% at noise σ = 2. A numerical prototype, not a physical analog computer or performance claim. 24 tests. |

## What held up, and what did not

### First arc (Builds 01–15)

**Held up (within their stated models):**

- The Build 01–06 mechanisms: codonic arithmetic, observer projections, shear holonomy, Hopf transport and probe selection all behave as specified. These are mathematical demonstrations, not empirical discoveries.
- The Build 08 methodological correction: stronger randomization and explicit perturbation matter, and they reduced a striking Build 07 correlation by more than half.
- The Build 10 negative result: independently parameterized acoustic and mechanical systems do **not** reproduce the Build 09 near-identity. This is the program's most important self-correction.
- The corrected Build 12 acoustic structure: after fixing the onset, decay, early/late balance and temporal character form a coherent block, while spectral shape and absolute level remain comparatively separate. This is a real, physically interpretable within-corpus result, not a universal invariant.
- The Build 13/14 TAPS cross-modal RDM geometry: on the full held-out split, periodicity (**ρ = 0.488**), combined common features (0.359), temporal descriptors (0.293) and shared spectral shape (0.233) all exceed shuffled-pair nulls. The clock-invariant temporal-emission view is positive but modest (0.120). This is the program's first positive paired-sensor result, though TAPS is already globally aligned and the result is not a universal invariant.
- Build 15's external controls recover a real utterance-specific interval signal: interval-only matching reaches **0.439** against a 0.085–0.094 mismatched-pair null. The order-shuffled same-utterance control at 0.356 shows that part of that number is matcher selection, leaving an order-specific increment of about 0.083. This is consistent with the Build 14 temporal-emission result and survives a stronger null than the frozen build used, but it is a modest signal.
- Build 11's descriptive window contrasts are consistent with a real recording, but the sample is too small and too localized for a population claim.

**Did not hold up:**

- Build 07's shape ↔ local-transition invariant as a general property of observer geometry (weakened by Build 08).
- Build 09's near-perfect cross-modal alignment as evidence of a shared acoustic/mechanical geometry (falsified by Build 10).
- Build 12's shipped EDT/C50/D50 values (invalidated by the Rochester pre-roll; see the correction note).
- Build 15's synthetic-validated combined matcher as a general event matcher. On TAPS its matched-interval ρ is 0.107–0.122, barely above the 0.085–0.094 mismatched-pair null and indistinguishable from the shuffled-mark control. The 0.78 mark weight was tuned on informative synthetic marks and crowds out the interval evidence.
- Build 15's event-level clock recovery. The post-match residual is 0.183 s under the frozen matcher and 0.117 s under interval-only matching, despite TAPS being globally aligned. The affine fit is a diagnostic, not evidence of synchronization.

### Second arc (Builds 16–30)

**Held up (within synthetic, bounded scopes):**

- Build 16's correction of Build 15: on its benchmark the combined matcher does not beat mark-only, and the mark cue is what the synthetic fixture actually supplies. Reporting this demotion is the point.
- Build 17's representation-specific invariances: Fourier magnitude under circular shift, Mellin magnitude under positive dilation on the log grid, pooled Haar-like energy under shift, and graph spectra under node relabeling. These are correct implementation properties, not universal signal laws.
- Builds 18–19's quotient hierarchy: S³ sees the antipodal and fibre distinctions, SO(3) identifies antipodes, and the Hopf base identifies the whole right-U(1) fibre. The endpoint-redundancy discovery is a genuine information audit.
- Builds 20–23's bounded Virtual Ground pipeline: an operational definition tested on reversible and irreversible systems, active identification inside a closed family, and inductive synthesis of executable programs within a declared grammar.
- Builds 24–26's online line: observer-relative predictive contexts, delayed-counterexample refinement, unknown-start belief tracking, asynchronous channels, explicit contradiction quarantine, and partial grounds that preserve unknowns instead of inventing edges.
- Build 28's motif/boundary pipeline under an ordered-shuffle maximum-statistic null, and Build 29's raw-signal event bridge, are structurally careful synthetic methods. Build 30's signal-domain Z/8 arithmetic is exact in the noiseless model.

**Did not hold up, or remains unestablished:**

- There is no universal representation (Build 17) and no uniquely identified observer (Build 30). Selection is task- and calibration-dependent.
- Endpoint harmonics are not independent evidence once the start and first path-signature level are known (Build 19).
- Build 16's combined event matcher is not supported by its own synthetic benchmark; mark-only is as good or better.
- Build 22's singleton identification is only identification **within the declared candidate family**; an out-of-family law can mimic it until a holdout probe.
- Build 24's bounded conformance is not equivalence: a model that passes depth 5 can fail at depth 6.
- Build 27's explanation scores are ordinal, not calibrated probabilities; hidden deterministic variables and stochastic transitions can remain observationally equivalent.
- Build 28's perfect boundary F1 is a controlled-fixture result with supplied tokenization; it is not natural-language or raw-sensor segmentation.
- Build 29's phase-only segmentation is incomplete, and harmonic versus temporal views fail on each other's event families by design.
- Build 30 demonstrates a finite signal-domain group computation, not a universal signal computer, physical analog processor, or efficiency advantage.
- **No build from 16 to 30 processed empirical sensor data.** These are synthetic and deterministic experiments. The empirical legs remain Builds 12 and 13/14.

## Empirical layer

- **Build 11:** one real smartphone recording excerpt, included in the build. Reproducible offline.
- **Build 12:** the 92.8 MB Rochester RIR archive was downloaded and all 90 WAVs / 15 room folders were analyzed. The corpus itself is not redistributed here; the pipeline and the derived feature tables are. The first run exposed the onset bug. The corrected run is in `theory_development/empirical_results/build_12/corrected/`.
- **Builds 13/14:** the 452 MB TAPS test archive was downloaded, MD5-verified, and all 1,000 pairs / 10 speakers were analysed. Results are in `theory_development/empirical_results/taps/`. The shipped packages still contain only synthetic smoke results; all empirical outputs were produced after unpacking.
- **Build 15:** the frozen local-clock graph runner and an external control script were run on the same 1,000 pairs. The controls add mark-only, interval-only, shuffled-mark, shuffled-interval-order and within-speaker mismatched-pair conditions plus a detector sweep. Results and caveats are in `theory_development/empirical_results/taps/README.md`.
- **Builds 16–30:** no physical sensor corpus was processed. Build 29's WAV reader and Build 30's signal program were exercised on synthetic WAVs/signals only.

## Verification

- **765 / 765 top-level tests pass** across 28 unpacked suites (Python 3.14.0). Details: `test_results/SUMMARY.md`.
- **177 / 177 embedded tests pass** in the Build 24–30 chain. The only additional distinct suite is Build 24's 17 tests; Build 16's 24 new tests are already inside Build 17's 83.
- **1,907 / 1,907 manifest hashes** match across the 22 builds that ship `MANIFEST.sha256` (Builds 07–15, 17–23 and 25–30).
- The 28 original ZIPs are checksummed in `archives/SHA256SUMS.txt`.
- Builds 01–11 regenerate deterministically within floating-point tolerance. Python 3.14 vs the author's 3.13 causes last-bit drift; one Build 08 correlation is materially affected by a numerically unstable turning-angle calculation (0.4635 shipped vs 0.5280 regenerated).
- Builds 13–15 use `secrets.token_bytes(32)` for pair salt, so shuffled-null and bootstrap decimals differ between runs even with fixed seeds. Structural conclusions are stable; exact values are not.
- The Build 15 frozen run and the external controls are deterministic for a fixed pair ordering, but that ordering is salted. The control's cyclic mismatch shifts depend on the sorted pair order; the three shifts sample different null pairings.
- **Build 30's `run_all_regressions.py` rewrites nine `verification/` files that its own manifest covers.** Running it invalidates those hashes until the frozen files are restored. Fresh logs from this run are in `test_results/build_24_30_embedded/`; the shipped files were restored afterward.
- **Builds 27 and 30 ship Python 3.13 `.pyc` files listed in their manifests.** Bytecode-writing runs can overwrite them; the verification runs here used `PYTHONDONTWRITEBYTECODE=1`.

## Reproducing

```powershell
# Every top-level build's test suite (28 unpacked trees)
python run_all_tests.py

# Embedded Build 24–30 regression chain
python virtual_ground\build_30\run_all_regressions.py

# Build 12 correction (requires the extracted Rochester corpus)
python theory_development\empirical_results\build_12\corrected\reanalyze_corrected.py

# TAPS held-out runs and controls (requires the extracted TAPS test split)
python theory_development\build_13\scripts\analyze_taps.py --root <TAPS>\test --split test `
  --output theory_development\empirical_results\taps\build_13_test --permutations 99
python theory_development\build_14\scripts\analyze_taps_build14.py --root <TAPS>\test --split test `
  --output theory_development\empirical_results\taps\build_14_test --permutations 99
python theory_development\build_15\scripts\analyze_taps_graphs.py --root <TAPS>\test --split test `
  --output theory_development\empirical_results\taps\build_15_test
python theory_development\empirical_results\taps\build_15_controls.py --root <TAPS>\test --split test `
  --output theory_development\empirical_results\taps\build_15_controls --null-shifts 1 37 73
```

Individual builds are run from their own directories; each `README.md` documents its entry point. The test runner writes fresh logs only with `--write-logs`. Set `PYTHONDONTWRITEBYTECODE=1` when checking manifests on Builds 27/30.

## Reading order

1. `PERSPECTIVE.md` — why the first arc matters, what it found, and what it cost; plus an addendum on the second arc.
2. `test_results/SUMMARY.md` — the verification record.
3. `theory_development/build_07/BUILD_07.md` → `build_08/BUILD_08.md` → `build_09/BUILD_09.md` → `build_10/BUILD_10.md` — the central positive-to-negative sequence.
4. `theory_development/empirical_results/build_12/corrected/FINDINGS.md` — the real-data bug and corrected acoustic result.
5. `theory_development/build_13/BUILD_13.md`, `build_14/BUILD_14.md` and `build_15/BUILD_15.md` — the paired-sensor and local-clock frontier.
6. `theory_development/build_17/BUILD_16.md` → `BUILD_17.md` → `build_18/BUILD_18.md` → `build_19/BUILD_19.md` — the falsification and representation bridge.
7. `virtual_ground/build_20/BUILD_20.md` → `build_21/BUILD_21.md` → `build_22/BUILD_22.md` → `build_23/BUILD_23.md` — the Virtual Ground foundations.
8. `virtual_ground/build_25/legacy/build24/BUILD_24.md` → `build_25/BUILD_25.md` → `build_26/BUILD_26.md` → `build_27/BUILD_27.md` → `build_28/BUILD_28.md` → `build_29/BUILD_29.md` → `build_30/BUILD_30.md` — latent contexts, online partial grounds, and the path from operations to raw signals.
9. `theory_development/empirical_results/taps/README.md` — the full held-out TAPS results and the Build 15 controls.
