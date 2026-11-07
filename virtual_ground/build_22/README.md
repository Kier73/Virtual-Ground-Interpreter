# Virtual Layer Response Geometry — Build 22

**Theme:** Active probing, inferred Virtual Grounds, observer-relative identifiability and conservative ground revision.

Build 22 reverses Build 21's supplied-ground workflow. Instead of being handed the transition law, an observer maintains candidate generative models and selects interventions that distinguish them.

## Quick start

```bash
python experiment.py
python -m unittest discover -s tests -v
```

Python standard library only.

## Main files

- `ground_discovery.py` — candidate ground family, probe catalogue, entropy scoring, active/passive identification, behavioural equivalence and ground revision monitor.
- `experiment.py` — 32-model benchmark and report generation.
- `ACTIVE_PROBING.md` — experiment design and results.
- `VIRTUAL_GROUND_IDENTIFICATION.md` — formal identification-to-navigation architecture.
- `IDENTIFIABILITY_AND_VERSIONING.md` — closed-world limits, holdout validation and ground revision.
- `legacy_build_21/` — Build 21 engine and experiment code for regression.
- `legacy_build_21/legacy_build_20/` — Build 20 reversible and partial grounds.
- `Questions_On_the_Virtual_Ground_SOURCE.md` — source document supplied by the user.

## Scope

All Build 22 experiment data are synthetic and deterministic. The candidate family has 32 models and the calibrated probe catalogue contains 324 experiments. The active identification result is conditional on that family and a reset/phase-calibration capability. A held-out test demonstrates that an out-of-family law can mimic the chosen discovery probes. No physical sensor or TAPS data are used.
