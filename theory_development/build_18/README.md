# Virtual Layer Response Geometry — Build 18

Build 18 develops the **Relational Invariant Atlas** conjecture and implements a low-order SU(2)/S3 harmonic test harness, Hopf-fibre quotient, unitary intertwiner check, and truncated path signature.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Core files

- `FORMAL_CONJECTURE.md` — statement, definitions, theorem-level facts and open questions.
- `REPRESENTATION_ATLAS.md` — cross-perspective symmetry/representation map.
- `relational_atlas.py` — executable core.
- `tests/test_build18.py` — tests.
- `reports/build_18_results.json` — numerical outputs.

All generated data are mathematical fixtures. No empirical speech or physical sensor recordings are included.
