# Build 31 — Compositional Signal Algebra and Observer Interchange

Build 31 extends Build 30's finite signal-domain arithmetic into compositional execution. It adds four equivalent observer-coordinate encodings of `Z/8Z`, transforms between them without integer decoding, tests operation/observer commutation, and measures calibration/noise propagation.

## Run

Python 3.10+; standard library only, plus the unchanged Build 30 `signal_code.py` module copied into this package. The full prior source tree and original archive are preserved under `predecessor/`.

```bash
python -m unittest discover -s tests -v
python run_build31.py
```

`run_build31.py` writes the full results to `reports/build_31_results.json`, CSV summaries for noise/calibration/observer coordinates, a multi-channel I/Q fixture at `fixtures/chain_3_6_2_iq.csv`, and an inspectable no-intermediate-decode execution trace at `reports/example_chain_trace.json`.

## Results

- 20/20 Build 31 unit tests passed.
- 2,048 two-operation executions passed exhaustively with zero errors.
- 512 binary operations passed across four observer coordinates.
- 512 observer/operation commutation cases passed.
- 512 inverse transitions recovered the initial state.
- The measured calibration-drift law matched the analytical phase-error propagation model.
- Noise and software timing diagnostics are included in the report.

Read `BUILD_31.md` for the mathematical contracts, tables, interpretation and limitations. The full Build 30 package and its predecessor chain are preserved under `predecessor/`.

All Build 31 generated data are synthetic. No physical signal hardware or universal computation claim is made.
