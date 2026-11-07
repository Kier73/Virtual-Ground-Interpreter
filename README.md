# Virtual Ground Interpreter

This repository now has two layers:

1. **Active project:** `virtual_ground_interpreter/` — a versioned, executable signal-state interpreter. This is the code path for iterative improvement.
2. **Frozen research archive:** `theory_development/` and `virtual_ground/` — the numbered Builds 01–31. These are preserved as historical records and are not refactored.

The active package is the bounded interpreter core described in
`virtual_ground_interpreter/README.md`. It runs typed task expressions and a
small instruction IR against persistent signal-valued state on the finite
`Z/8Z` Ground, with observer-coordinate changes and three-valued equality /
identity guards.

## Quick start

```powershell
cd virtual_ground_interpreter
python -m unittest discover -s tests -v
python -m vgi verify
python -m vgi run examples/conditional_select.task.json --input input.a=3@1 --input input.b=5@3
```

The frozen archive suites can still be run from the repository root:

```powershell
python run_all_tests.py
```

## Development orientation

Iterative improvement happens in `virtual_ground_interpreter/`. The frozen
builds are evidence and lineage, not the development branch. See
`virtual_ground_interpreter/DEVELOPMENT.md` for the iteration loop, quality
gates and release checklist, and `virtual_ground_interpreter/CHANGELOG.md` for
version notes.
