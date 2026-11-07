# Build 25 — Non-Resettable Online Virtual Ground Tracking

Build 25 extends a Build 24 learned predictive machine to a continuing stream with an unknown initial context. It supports belief tracking, late/out-of-order partial sensor observations, per-source local clocks, explicit event correspondence, risk-aware probe suggestions, contradiction quarantine and bounded online memory.

## Run

```bash
python run_build25.py
python -m unittest discover -s tests -v
python -m unittest discover -s legacy/build24/tests -v
```

Python 3.10+, standard library only.

## Main files

- `online_ground.py` — online belief tracker, conflict monitor, probe scheduler and local-clock registry.
- `run_build25.py` — deterministic experiment and report generation.
- `tests/test_build25.py` — 34 Build 25 tests.
- `legacy/build24/tests/` — 17 inherited Build 24 regression tests.
- `legacy/build24/` — complete Build 24 source and regression suite.
- `reports/` — online traces, clock results, probe decisions and summary metrics.

## Evidence boundary

All results are synthetic finite-state fixtures. Build 25 receives a previously learned Build 24 predictive machine; it removes the reset requirement from runtime tracking, not from the earlier training process. No physical system or sensor stream has been connected.
