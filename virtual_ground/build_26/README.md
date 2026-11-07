# Build 26 — Incremental Online Virtual Ground Induction

Build 26 constructs a partial predictive ground from an ongoing stream without reset and without requiring a complete prelearned machine.

## Run

```bash
python run_build26.py
python -m unittest discover -s tests -v
python -m unittest discover -s legacy/build24/tests -v
python -m unittest discover -s legacy/build25/tests -v
```

Python 3.10+, standard library only.

Current verification: 27 Build 26 tests, 17 Build 24 tests and 34 Build 25 tests pass (78 total).

## Main files

- `incremental_ground.py` — asynchronous stream ingestion, finite-horizon context discovery, partial transition induction, quotient refinement, executable partial ground, evidence replay, known-edge probe scoring and safe novelty-based exploration of unknown edges.
- `run_build26.py` — synthetic observer quotient, delayed-context, asynchronous-ingestion and bounded-memory experiments.
- `tests/test_build26.py` — Build 26 tests.
- `legacy/build24/` — preserved Build 24 source and executable regression suite.
- `legacy/build25/` — preserved Build 25 source and executable regression suite.
- `notes/build24_recovery/` — full Build 24 notes, reports, tests, source and original archive.
- `reports/` — numerical results and executable partial specification.

## What changed

Build 24 learns from resettable queries. Build 25 tracks a hidden current context using an existing predictive machine. Build 26 incrementally induces a partial predictive model from a continuing non-resettable stream. Unknown transitions remain unknown, context collisions may increase the retained history horizon, and model revisions are recorded rather than silently applied.

## Evidence boundary

All Build 26 results are synthetic deterministic finite-state tests using Build 24's fixture generators as hidden test oracles. The Build 26 learner receives only action names and selected output channels. It does not receive hidden mode IDs. No physical sensor data or TAPS recording was processed. It does not infer arbitrary raw sensor boundaries, stochastic laws, continuous latent variables or an unknown action alphabet.
