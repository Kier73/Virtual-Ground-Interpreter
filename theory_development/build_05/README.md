# Build 05 — Active Observation and Intention-Conditioned Probe Selection

A dependency-free Python research prototype for choosing measurements based on an observer's capabilities and the question it is trying to answer.

## Run

```bash
python -m unittest discover -s tests -v
python active_observer.py
```

The report is written to `reports/build_05_report.json`.

## Model

A candidate structure is a 2×2 linear operator. A probe loads a unit input vector. The operator acts on that vector through a small configurable scalar codon interpreter (`mx` and `ad`); the observer then selects one or more output channels. Gaussian measurement noise is applied to the retained channels.

The observer selects a probe using robust expected information gain about an intention-defined target, divided by the probe's relative cost.

This package is a controlled finite experiment. It is not yet integrated with the full Virtual Layer address space, SHA-256 substrate, RNS/CRT pipeline, or S³/Hopf transport implementation.

## Package contents

- `active_observer.py` — implementation, inference, probe selection and report generation.
- `tests/` — unit and invariant tests.
- `reports/build_05_report.json` — detailed deterministic report.
- `codon_schema.json` — local codon-operation semantics.
- `data/probe_rankings.csv` — observer/intent/probe ranking table.
- `data/policy_accuracy.csv` — policy performance by noise scale.
- `data/active_episode.json` — one active observation trace.
- `test_run.txt` — test execution log.
- `run_output.txt` — concise report-generation output.
- `SOURCES.md` — research references.
- `BUILD_05.md` — mathematical description, results and limitations.
- `NOTES_NEXT.md` — Build 06 direction.

All experiments use fixed random seeds. The Monte Carlo counts and Wilson intervals are recorded in the JSON report.
