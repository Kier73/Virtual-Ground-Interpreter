# Virtual Layer — Build 08

Generalization and perturbation study for observer-dependent geometry.

## Contents

- `cross_observer_generalization.py` — standalone experiment implementation.
- `tests/test_build_08.py` — unit tests.
- `reports/build_08_report.json` — complete numerical report.
- `data/` — family manifest, observer RDMs, hash-substrate RDMs, robustness data, persistence summaries, and comparison tables.
- `BUILD_08.md` — methods, results, interpretation, and limitations.
- `NOTES_NEXT.md` — proposed Build 09 direction.
- `SOURCES.md` — selected research references.
- `MANIFEST.sha256` — file integrity manifest.

## Requirements

Python 3.10 or later. Standard library only.

## Run

```bash
python -m unittest discover -s tests -v
python cross_observer_generalization.py --out .
```

The default experiment uses deterministic seed `81008`, 40 independent path families, 400 family-bootstrap replicates, 399 permutation trials, and six repeats per observer-robustness setting.

This is a synthetic research prototype, not a complete Virtual Layer implementation. See `BUILD_08.md` for scope and caveats.
