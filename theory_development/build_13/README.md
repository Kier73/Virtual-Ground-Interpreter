# Virtual Layer — Build 13

Paired acoustic / throat-vibration response geometry using the TAPS corpus.

## Status

- Analysis engine: implemented.
- Synthetic pipeline tests: 13 passing.
- TAPS metadata: verified from the public Zenodo and Hugging Face dataset records.
- Empirical audio analysis in this build environment: **not performed** (external network access unavailable).
- No audio or participant transcripts are included.

## Install

Core analysis has no third-party Python dependencies. Python 3.10+ is recommended.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Retrieve the held-out test split

The default test split archive is about 452 MB. The full corpus is about 2.7 GB.

```bash
python scripts/fetch_taps.py --split test --output data/raw
```

The script resolves the download link from the Zenodo record API, verifies the published MD5 as an integrity check (not a cryptographic authenticity guarantee), then safely extracts the archive. It does not download the entire training corpus by default.

## Analyze the held-out speakers

```bash
python scripts/analyze_taps.py \
  --root data/raw/TAPS_data_test/test \
  --split test \
  --output reports/taps_test \
  --max-speakers 10 \
  --max-utterances-per-speaker 100 \
  --permutations 99
```

For a quick subset, lower `--max-utterances-per-speaker` (for example, 20). The analysis writes aggregate results only by default. `--write-pair-features` optionally writes anonymized per-utterance derived features; keep that file local.

## Outputs

- `build_13_report.json`: dataset counts, channel sample rates, residual alignment summaries and observer RDM results.
- `alignment_summary.csv`: aggregate residual timing diagnostics.
- `rdm_view_summary.csv`: per-view acoustic/throat RDM correlations, speaker-bootstrap intervals and within-speaker shuffled-pair nulls.
- `pair_features_anonymized.csv`: optional derived features, not written by default.

## Important interpretation

TAPS contains paired speech signals, not emotion labels. This build studies acoustic and throat-vibration response geometry, not emotion recognition, speaker identification, or psychological state. The synthetic smoke-test report is not an empirical finding.

See `BUILD_13.md`, `SOURCES.md` and `LICENSES.md` before interpreting or redistributing outputs.
