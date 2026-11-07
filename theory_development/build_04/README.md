# Virtual Layer Research — Build 04

## S³ Codonic Path Navigation and Hopf-Fibre Holonomy

A dependency-free Python experiment exploring quaternion path navigation, observer projections, and accumulated phase on the Hopf fibration.

### Run

```bash
python -m unittest discover -s tests -v
python run_experiment.py
```

Python 3.10+; standard library only.

### Contents

- `s3_codonic_navigation.py` — quaternion arithmetic compiled into scalar codonic instructions, S³/SO(3) metrics, SLERP, Hopf projection, horizontal lift, and loop generators.
- `tests/test_s3_codonic_navigation.py` — independent numerical and algebraic checks.
- `run_experiment.py` — reproduces JSON results and CSV traces.
- `BUILD_04.md` — mathematical model, results, interpretations, limitations, and next steps.
- `SOURCES.md` — research references and their relevance.
- `reports/build_04_report.json` — machine-readable experiment output.
- `data/*.csv` — sampled base paths and quaternion lifts.
- `test_run.txt` — captured test log.

This build is a mathematical prototype. It does not claim that the current Virtual Layer address substrate naturally forms a Hopf bundle, nor that the response phase is a universal semantic or emotional tone.
