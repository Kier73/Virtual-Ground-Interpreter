# Test summary

**Environment:** Windows, Python 3.14.0, standard library only (the builds declare no third-party runtime dependencies).
**Run:** all 29 unpacked top-level suites plus the embedded Build 24–30 regression chain, 2026-11-07.
**Result:** **785 / 785 top-level tests passed** across 29 suites; **177 / 177 embedded tests passed** across Builds 24–30. No failures or errors.

Per-build logs are in `build_01.txt` … `build_15.txt` and `build_17.txt` … `build_31.txt`; these are the raw `unittest -v` captures. Builds **16** and **24** have no standalone ZIP or top-level directory:

- Build 16's source and 24 tests are embedded in `theory_development/build_17/` and are included in that suite's 83 tests.
- Build 24's 17 tests are embedded in `virtual_ground/build_25/legacy/build24/` and `virtual_ground/build_26/legacy/build24/`; the fresh run is preserved in `build_24_30_embedded/`.

Re-run everything with:

```powershell
python run_all_tests.py
python virtual_ground\build_30\run_all_regressions.py   # embedded Build 24–30 chain
```

Use `python run_all_tests.py --write-logs` to refresh the logs and `--builds 12 13 14` for a subset.

| Build | Tests | Time (s) | Result |
|---|---:|---:|---|
| 01 | 15 | 0.04 | OK |
| 02 | 10 | 0.04 | OK |
| 03 | 16 | 0.01 | OK |
| 04 | 19 | 0.30 | OK |
| 05 | 17 | 0.08 | OK |
| 06 | 31 | 0.21 | OK |
| 07 | 22 | 16.21 | OK |
| 08 | 17 | 2.52 | OK |
| 09 | 24 | 0.65 | OK |
| 10 | 25 | 22.61 | OK |
| 11 | 17 | 0.05 | OK |
| 12 | 17 | 1.80 | OK |
| 13 | 18 | 2.81 | OK |
| 14 | 27 | 2.79 | OK |
| 15 | 44 | 4.67 | OK |
| 17 | 83 | 10.22 | OK |
| 18 | 21 | 0.66 | OK |
| 19 | 39 | 1.62 | OK |
| 20 | 43 | 2.34 | OK |
| 21 | 32 | 0.10 | OK |
| 22 | 47 | 0.82 | OK |
| 23 | 21 | 0.12 | OK |
| 25 | 34 | 0.01 | OK |
| 26 | 27 | 0.28 | OK |
| 27 | 30 | 0.003 | OK |
| 28 | 21 | 0.27 | OK |
| 29 | 24 | 11.03 | OK |
| 30 | 24 | 76.01 | OK |
| 31 | 20 | 1.29 | OK |
| **Top-level total** | **785** | **158.27** | **OK** |

## Embedded Build 24–30 chain

`virtual_ground/build_30/run_all_regressions.py` runs each preserved suite once in its nested workspace:

| Build | Tests | Result |
|---|---:|---|
| 24 | 17 | OK |
| 25 | 34 | OK |
| 26 | 27 | OK |
| 27 | 30 | OK |
| 28 | 21 | OK |
| 29 | 24 | OK |
| 30 | 24 | OK |
| **Total** | **177** | **OK** |

The Build 25–30 counts duplicate their top-level suites; the only additional distinct suite is Build 24's 17 tests. Build 16's 24 new tests are already inside Build 17's 83.

## What the suites establish

- WAV ingestion (PCM 8/16/24/32-bit, IEEE float 32/64-bit, extensible headers) and rejection of malformed/unsafe input.
- RDM construction, symmetry, Spearman rank correlation, paired-ID enforcement and shuffled controls.
- Decay fitting, gain invariance, feature-view separation, room-median aggregation and end-to-end report writing.
- Codonic arithmetic equivalence and observer/probe bookkeeping in Builds 01–06.
- Randomized-path generalization and perturbation machinery in Build 08.
- Paired synthetic positive controls in Build 09 and heterogeneous null controls in Build 10.
- Real excerpt integrity and window handling in Build 11.
- Paired throat/acoustic analysis, alignment diagnostics and event-time invariants in Builds 13–14.
- Local-clock event correspondence in Build 15: monotone DP matching on rank/interval-shape descriptors, affine clock recovery after matching, graph construction, and aggregate-only reporting.
- Build 16–17: matcher ablations and negative controls; finite DFT, STFT, Haar-like, Mellin and graph-Laplacian representation invariances/covariances under synthetic clock transformations.
- Build 18–19: SU(2)/S³ harmonics, antipodal and Hopf quotients, Schur/intertwiner checks, path signatures, and observer-specific kernel geometries.
- Build 20–23: operational Virtual Ground definition, reversible and irreversible navigation fixtures, active ground identification, and bounded inductive synthesis of executable ground programs.
- Build 24–26: latent predictive-context learning, non-resettable online belief tracking, asynchronous partial observations, local clocks, contradiction quarantine, and incremental partial-ground construction.
- Build 27–30: competing explanations and opaque-operation discovery, continuous-token boundary discovery, raw-signal event segmentation, observer-profile selection, and signal-domain modular arithmetic.

## What they do not establish

- **They are not empirical validation.** Most fixtures are synthetic. Build 12's tests use impulses that begin at sample 0, so they cannot catch the Rochester pre-roll onset bug. That bug was found only by running the pipeline on the real 90-file corpus; see `../theory_development/empirical_results/build_12/corrected/FINDINGS.md`.
- **Builds 16–30 processed no empirical sensor data.** Their exact scores (including Build 28's boundary F1 1.000 and Build 29's 108/108 synthetic boundaries) are checks on controlled fixtures. Build 29's WAV path was exercised on a synthetic WAV; Build 30's signal computer is a numerical prototype, not a physical analog processor.
- **Builds 13–15 outputs are not bit-reproducible run-to-run** even with a fixed seed: `_PAIR_SALT = secrets.token_bytes(32)` randomizes pair ordering and therefore the shuffled-null, bootstrap and control draws. The structural results are stable; exact decimal values are not.
- **Build 08 is deterministic in a fixed environment but not across Python versions.** The shipped `local_clean__temporal_clean` correlation is 0.4635; a Python 3.14 regeneration gives 0.5280. The cause is a numerically unstable turning-angle calculation in `local_signature`, not a test failure. Treat last digits as environment-dependent.
- **Inherited suites overlap.** Build 14 carries Build 13 forward almost verbatim. Build 15 carries Build 14 forward. Build 17's 83 tests include inherited Build 14–16 coverage. Builds 27–30's combined regression totals include nested copies of earlier builds. A passing total is not a count of independent claims.
- **Build 30's regression runner mutates its own manifest inputs.** `virtual_ground/build_30/run_all_regressions.py` rewrites nine files under `verification/` that Build 30's `MANIFEST.sha256` covers, so running it invalidates those hashes until the frozen files are restored. The fresh logs are preserved under `build_24_30_embedded/`; the frozen copies were restored after this run.
- **Builds 27 and 30 ship Python 3.13 `.pyc` files inside their manifests.** Running with bytecode writing enabled can overwrite those files and break the manifest. The verification runs here used `PYTHONDONTWRITEBYTECODE=1`.

## Manifest verification

All 22 shipped `MANIFEST.sha256` files were checked after extraction and again after testing: **1,907 hashes, 0 mismatches, 0 missing**.

- Builds 07–15: 225 hashes.
- Builds 17–23 and 25–30: 1,682 hashes.
- Builds 01–06 did not ship manifests; their file sets were preserved as extracted.
- Builds 16 and 24 have no standalone manifest; they are embedded recovery snapshots.
