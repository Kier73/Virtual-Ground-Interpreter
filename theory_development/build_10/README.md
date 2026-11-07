# Virtual Layer — Build 10

Heterogeneous system-response geometry and active probing.

## Contents

- `build_10.py` — synthetic modal-network and coupled-mechanical simulator, feature extraction, unpaired geometry metrics, active observer, and nuisance sweeps.
- `tests/test_build_10.py` — 25 standard-library unit tests.
- `feature_schema.csv` — the 33 response feature definitions.
- `codon_schema.json` — local codon schema reference.
- `data/` — domain RDMs, system parameter manifest, active probe traces, probe information rankings, noise and nuisance sweeps.
- `reports/` — complete numerical report and condensed key results.
- `BUILD_10.md` — complete mathematical and experimental note.
- `NOTES_NEXT.md` — proposed Build 11 direction.
- `SOURCES.md` — research and dataset sources.
- `MANIFEST.sha256` — file integrity manifest.

## Requirements

Python 3.10 or newer. No third-party packages are required.

## Reproduce

From this directory:

```bash
python build_10.py --out . --seed 20261105
python -m unittest discover -s tests -v
```

The benchmark writes the complete JSON report and CSV data under `reports/` and `data/`.

## Scope and limitations

All systems and responses in this build are synthetic. The acoustic-like modal network is a digital model, not a recording of sound or a model of human hearing. The mechanical two-degree-of-freedom model is a numerical system, not an experimental structure. The response features are engineering descriptors, not measurements of emotional tone.

The active observer's expected-information score uses a small deterministic approximation. Cross-domain geometry is compared as an *unpaired distributional summary*; the build deliberately does not assert a one-to-one mapping between independently generated systems.
