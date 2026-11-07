# Virtual Layer Response Geometry — Build 19

Build 19 tests the joint use of endpoint SU(2) harmonics, observer-specific path signatures and Gram kernels on deterministic synthetic quaternion trajectories.

## Run

```bash
python -m pip install -r requirements.txt
python build_19.py
python -m unittest discover -s tests -v
```

The test suite includes the 21 Build 18 regression tests and 18 new Build 19 tests.

## Key files

- `BUILD_19.md` — experiment and numerical findings.
- `CONJECTURE_UPDATE.md` — formal conjecture refinement and proof obligations.
- `REPRESENTATION_COMPARISON.md` — observer/representation comparison table.
- `build_19.py` — experiment implementation.
- `relational_atlas.py` — inherited quaternion, SU(2), Hopf and path-signature core.
- `reports/build_19_results.json` — deterministic output.
- `tests/` — inherited and new regression suite.

All numerical results are synthetic. No TAPS audio or physical sensor recording is included or processed.
