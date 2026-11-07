# Virtual Ground Research — Build 23

Build 23 demonstrates bounded inductive synthesis of finite Virtual Grounds from transition records.

- `ground_synthesis.py`: hidden fixture generator, expression grammar, inducer, compiler and verification helpers.
- `run_build23.py`: reproducible experiment runner.
- `tests/`: synthesis and Build 20–22 regression tests.
- `reports/`: inferred programs, datasets, held-out scores, version comparison and uncertainty records.
- `virtual_ground.py`, `partial_ground.py`, `flow_ground.py`, `ground_discovery.py`: selected previous-generation reference engines.

Run:

```bash
python run_build23.py
python -m unittest discover -s tests -v
```

Standard-library only. All Build 23 data are synthetic finite deterministic fixtures. Read `BUILD_23.md` and `SYMBOLIC_RULE_GRAMMAR.md` for scope and limitations.
