# Virtual Ground Research — Build 28

Boundary discovery from continuous opaque-token streams.

## Run

```bash
python run_build28.py
python -m unittest discover -s tests -v
python run_all_regressions.py
```

Python 3.10+, standard library only.

## Re-run inherited Build 24–27 regression suites

```bash
(The root `run_all_regressions.py` extracts the preserved Build 27 archive into a temporary directory and reruns Builds 24–27 without modifying the embedded recovery copy.)
```

See `BUILD_28.md`, `BOUNDARY_DISCOVERY.md` and `CHECKPOINT_INFERENCE.md` for method, results and limits. `notes/BUILD_27_ORIGINAL_ARCHIVE.zip` and `notes/build27_workspace/` preserve the complete preceding handoff, including Build 24 recovery material.

All Build 28 main results are synthetic. The learner receives continuous token streams and sparse checkpoints, but no hidden operation boundaries or semantic operation names. The evaluator-only truth file is explicitly marked as such.
