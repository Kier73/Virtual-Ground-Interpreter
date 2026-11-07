# Virtual Response Geometry — Build 30

Build 30 explores adaptive signal observers and signal-coded computation.

## Run

```bash
python run_build30.py
python -m unittest discover -s tests -v
python run_all_regressions.py
```

Dependencies: Python standard library only, plus the preserved Build 29 source workspace bundled under `notes/build29_workspace`.

## Key files

- `adaptive_observer.py` — task-calibrated observer-profile selection.
- `signal_code.py` — FSK control coding, 8-PSK operand coding and modular phase arithmetic.
- `run_build30.py` — generates results and inspectable WAV fixtures.
- `tests/test_build30.py` — Build 30 unit and integration tests.
- `reports/` — numeric outputs.
- `fixtures/` — generated WAV files.
- `notes/BUILD_29_ORIGINAL_ARCHIVE.zip` and `notes/build29_workspace/` — full prior build recovery.

All reported Build 30 experiments use synthetic data. No physical sensor or TAPS recording is included or processed.

## Main result

Build 30 demonstrates a task-calibrated observer over three signal families and a finite signal-coded program: FSK opcodes select ADD8/SUB8; 8-PSK phasors carry operands; phase multiplication/conjugate multiplication performs modular arithmetic over Z/8Z. This is not a universal signal computer or a physical hardware demonstration.

Verification: 24 Build 30 tests and 153 inherited tests, 177 total. See `FRESH_EXTRACTION_VERIFICATION.md`.
