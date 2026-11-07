# Virtual Layer — Build 14

Paired acoustic / throat-vibration response geometry with a temporal-emission layer.

## Status

- Core analysis: Python standard library only.
- Tests: 27 passing.
- Synthetic smoke: 30/30 synthetic pairs processed.
- TAPS corpus metadata: verified from the public Zenodo and Hugging Face records.
- Empirical TAPS audio: **not processed in this runtime**; external DNS resolution failed during retrieval.
- No audio or participant text is included.

## Install

Python 3.10+ is recommended. The core engine has no third-party package dependencies.

## Verify

```bash
./run_tests.sh
python scripts/run_synthetic_smoke.py
```

The synthetic smoke report is `reports/synthetic_smoke_test_build14.json`. It is only a software-path check, not an empirical observation.

## Retrieve held-out TAPS test data

```bash
python scripts/fetch_taps.py --split test --output data/raw
```

The downloader resolves the current file URL from the Zenodo record, checks the published MD5 as a transfer-integrity check (not an authenticity guarantee), and safely extracts the archive. The held-out test archive is approximately 452 MB.

## Analyze TAPS

```bash
python scripts/analyze_taps_build14.py \
  --root data/raw/TAPS_data_test/test \
  --split test \
  --output reports/taps_test_build14 \
  --max-speakers 10 \
  --max-utterances-per-speaker 100 \
  --permutations 199
```

Aggregate output is the default. `--write-pair-features` writes an optional anonymized per-utterance feature file; keep it local and review dataset terms before sharing it.

## Main outputs

- `build_14_report.json`: aggregate counts, channel rates, alignment diagnostics and cross-modal RDMs.
- `alignment_summary.csv`: aggregate residual alignment diagnostics.
- `rdm_view_summary.csv`: per-view RDM results, permutation nulls, bootstrap intervals, normalization sensitivity and leave-one-feature-out summaries.

See `BUILD_14.md`, `SOURCES.md` and `LICENSES.md` for definitions, limitations, source notes and reuse cautions.
