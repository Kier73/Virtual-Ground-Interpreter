# Post-freeze validation layer

This folder is intentionally **outside** the frozen build trees. It adds tests, benchmarks and cross-validation helpers that exercise the published code without changing any `MANIFEST.sha256` file or rebuilding history.

## What it covers

- `build12_preroll.py` — permanent Build 12 pre-roll onset regression fixture and a peak-trimmed correction prototype.
- `productivity.py` — Builds 20–23 productivity benchmarks against materialized-graph and lookup baselines.
- `random_grounds.py` — deterministic random hidden grounds for Builds 22–23 instead of only fixed catalogues.
- `build24_equivalence.py` — canonical Mealy minimization, distinguishing words and minimal counterexample checks.
- `signal_stress.py` — Build 29–30 multiresolution, drift, noise, jitter, pilot-mismatch and transfer-variation stress tests.
- `salt_cv.py` — audit of run-dependent salts in Builds 13–15, explicit seeded pair hashing, and group cross-validation for a future paired-corpus run.
- `taps_seeded_runner.py` / `run_taps_cv.py` — seeded wrappers around the frozen TAPS analyses plus speaker/sentence group cross-validation; writes `taps_cv_results.json` and logged salt provenance.
- `run_seeded_taps.py` — default single-build seeded runner for Builds 13–15.
- `second_paired_corpus_manifest.json` / `.md` — machine-readable and human-readable availability/limitation manifest for a second paired-sensor corpus.

## Default TAPS execution path

Use the seeded wrapper, not the frozen direct CLI, for new TAPS runs:

```powershell
python validation\run_seeded_taps.py --build 14 --root <TAPS_ROOT> --output <OUT> --seed 13
python validation\run_taps_cv.py --root <TAPS_ROOT> --split test --seed 13
```

The wrapper binds an explicit salt before calling the frozen code and writes
`seeded_salt_provenance.json`. A second paired-sensor corpus is not bundled;
see `second_paired_corpus_manifest.json`.

## Run

```powershell
python -m unittest discover -s validation -v
```

The tests are standard-library only. They are not part of the 765-test frozen suite; they are a post-publication validation layer.
