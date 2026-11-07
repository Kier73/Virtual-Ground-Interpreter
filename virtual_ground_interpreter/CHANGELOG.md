# Changelog

## 0.1.0 — initial interpreter baseline

- Bounded signal-state interpreter over finite `Z/8Z` in four 8-PSK observer coordinates.
- Typed task-expression compiler lowering a constrained DSL to validated control-flow IR.
- Persistent signal-valued memory, registers, instruction trace, checkpoints, reset and journal-based undo.
- Three-valued equality/identity guards with atomic trap behavior on indeterminate conditions.
- Exhaustive finite verification over the declared Ground.

Verification baseline:

- 42 unit tests pass.
- `vgi verify` reports 4,772 finite cases with zero errors.
- Ground: `virtual-ground.signal-state.z8`
- Fingerprint: `4ba599c21ec7e446572dad61b2a66ecb9c0844fd3dee406e4d947e04db56c43b`
