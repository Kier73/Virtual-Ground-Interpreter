# Virtual Ground Research — Build 29

Continuous measurements to observer-relative event hypotheses.

## Requirements

- Python 3.10+
- Python standard library only

## Run

```bash
python run_build29.py
python -m unittest discover -s tests -v
python analyze_wav.py fixtures/synthetic_dual_sensor.wav --view combined --token-view harmonic --output analysis.json
python run_all_regressions.py
```

`run_build29.py` generates controlled synthetic signals, evaluates boundaries against evaluator-only truth, and feeds the first ten signal-derived opaque token streams into Build 28 motif mining. The final two streams remain held out during motif discovery.

`analyze_wav.py` accepts a WAV file. Channel fusion currently requires equal sample rate, equal length and alignment. The build does not infer asynchronous local-clock mappings.

See `BUILD_29.md`, `RAW_TO_EVENT_MODEL.md`, `OBSERVER_RELATIVE_TOKENIZATION.md`, and `LIMITATIONS.md`.

All published Build 29 measurements are synthetic. No physical sensor or TAPS recording was processed.

## Reproducibility summary

The current regression summary is in `verification/combined_regression_summary.json`. The package contains 24 Build 29 tests and reruns the 129 tests preserved in the Build 28 lineage (Builds 24–28), for 153 combined passing tests.
