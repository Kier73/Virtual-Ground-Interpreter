# Build 26 Recovery and Continuity Index

This package is designed to be a durable handoff for the self-constructing Virtual Ground sequence.

## Build 24 — complete recovery set

- Summary and instructions: `BUILD_24_RECOVERY_NOTES.md`
- Original full archive: `notes/build24_recovery/BUILD_24_ORIGINAL_ARCHIVE.zip`
- Original source/docs/reports/tests: `notes/build24_recovery/`
- Executable copy used by regression: `legacy/build24/`

## Build 25 — online tracking predecessor

- Online tracker: `legacy/build25/online_ground.py`
- Runner: `legacy/build25/run_build25.py`
- Tests: `legacy/build25/tests/`
- Build 24 dependency: `legacy/build25/legacy/build24/`

## Build 26 — incremental induction

- Engine: `incremental_ground.py`
- Runner: `run_build26.py`
- Tests: `tests/test_build26.py`
- Formal design: `INCREMENTAL_GROUND_INDUCTION.md`
- Evidence limits: `UNKNOWN_TRANSITIONS_AND_PROOFS.md`

## Reproduction commands

From the package root:

```bash
python legacy/build24/run_build24.py
python -m unittest discover -s legacy/build24/tests -v
python legacy/build25/run_build25.py
python -m unittest discover -s legacy/build25/tests -v
python run_build26.py
python -m unittest discover -s tests -v
```

The `legacy/build25/run_build25.py` script can be run from its own directory or with its directory on the Python import path; its relative Build 24 dependency is embedded alongside it.
