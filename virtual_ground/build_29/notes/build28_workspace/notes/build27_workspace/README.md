# Build 27 — Competing Explanations and Operation Discovery

Build 27 extends the incremental Virtual Ground work with an evidence-ranked diagnosis layer and discovery of recurring operations from opaque event signatures.

## Run

```bash
python run_build27.py
python -m unittest discover -s tests -v
```

Python 3.10+, standard library only.

## Inherited recovery and regression

The full Build 26 package is preserved under `legacy/build26/`. It contains the Build 26 implementation and tests, Build 25 online tracker and tests, Build 24 latent-ground learner and tests, plus the Build 24 recovery archive and notes.

From `legacy/build26/` run:

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s legacy/build24/tests -v
python -m unittest discover -s legacy/build25/tests -v
```

Build 27's fresh-extraction verification reproduces all three inherited suites.

## What Build 27 adds

- Competing explanations for anomalies: measurement noise, sensor remapping, insufficient history, hidden predictive variables, stochastic or unmodelled context, new observed states, regime change, and new operation candidates.
- A transparent evidence-ranking system. Scores are ordinal heuristics, not calibrated probabilities.
- Independent reference-channel checks before calling a persistent sensor offset a calibration shift.
- A persistent multi-context/multi-operation and multi-sensor condition before proposing a ground-regime revision.
- An event-signature miner. It receives observation windows and opaque low-level event tokens, not semantic action names or a supplied action catalogue.
- A partial executable ground compiled from recurring event signatures and their observed effects.
- A discriminating-probe selector that maximizes information gain over an explicit competing-hypothesis set under cost/risk limits.
- A bounded online wrapper with structural versioning; repeated support does not create a new ground version when the rule structure is unchanged.

## Evidence class

All Build 27 experiments are synthetic finite integer-vector transition windows and hand-constructed diagnostic cases. No physical sensor data was processed.

## Critical boundaries

- Observation-window segmentation is supplied by the acquisition interface. Raw waveform boundary discovery is not implemented.
- Event tokens are opaque; semantic operation names are not supplied or inferred.
- The miner currently discovers recurring exact event-window signatures, not arbitrary subsequence grammars.
- State observations are finite integer vectors; continuous latent-variable discovery is not implemented.
- Hidden deterministic context and stochastic transitions may remain observationally equivalent.
- Sensor remapping and a real state change remain ambiguous without independent calibration references.
- Ground revisions are proposals only. This build never commits a new ground automatically.
- Constant-delta extrapolation is a hypothesis validated on finite held-out examples, not a proof outside the observed domain.
