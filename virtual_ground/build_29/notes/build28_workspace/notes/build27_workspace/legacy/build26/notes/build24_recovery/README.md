# Build 24 — Latent Context Discovery

A standard-library-only prototype that learns a deterministic predictive Virtual Ground from action/output traces while keeping the teacher's latent context hidden.

## Run

```bash
python run_build24.py
python -m unittest discover -s tests -v
```

The experiment writes reports under `reports/`. Learned executable specifications are JSON files named `ground_spec_*.json`.

## Main modules

- `latent_ground.py` — resettable hidden-context teacher, observation-table learner, bounded conformance checking, active probe tree, phase detection and compiler.
- `run_build24.py` — complete synthetic fixture suite and report generation.
- `tests/test_build24.py` — 17 regression and property tests.
- `legacy/build23_ground_synthesis.py` — Build 23 regression source.

## Requirements

Python 3.10+; standard library only.

## Evidence boundary

All experiments are synthetic, deterministic and finite. The teacher has a reproducible reset and the action alphabet is supplied. The learner returns a minimal predictive quotient under the observer, not the hidden system's physical ontology. Conformance is bounded by the explicit input-word depth.
