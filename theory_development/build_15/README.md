# Virtual Layer — Build 15

Local-clock event graphs for comparing observer streams without requiring synchronized timestamps.

## Included

- Build 14 paired-sensor/WAV analysis and event extraction foundation.
- Monotone sequence alignment using within-stream event mark ranks and normalized interval-shape descriptors.
- Two-observer event graph with successor, recurrence and inferred correspondence edges.
- Post-match robust affine clock-relation estimate.
- TAPS aggregate-only runner and synthetic event-correspondence stress test.

## Verify

```bash
./run_tests.sh
python scripts/run_synthetic_smoke.py
```

Tests use only Python's standard library. No source audio is bundled.

## TAPS held-out test split

```bash
python scripts/fetch_taps.py --split test --output data/raw
python scripts/analyze_taps_graphs.py \
  --root data/raw/TAPS_data_test/test \
  --split test \
  --output reports/taps_test_build15
```

The empirical TAPS archive was not available to this runtime during Build 15. No empirical TAPS graph result is included. Synthetic stress metrics are software checks, not observations from human recordings.

See `BUILD_15.md` for equations, matching assumptions, limitations and next falsification tests. See `SOURCES.md` and `LICENSES.md` for inherited data provenance and reuse notes.
