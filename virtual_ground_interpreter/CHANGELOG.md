# Changelog

## 0.2.0 — predictive transition-system integration

- Added first-class predictive transition grounds with known, unknown, and ambiguous edge states, support counts, and evidence references.
- Added an importer for the archived Build 24 VG-PredictiveMealy-1 format.
- Added a bounded compiler from complete finite grounds to the existing Signal8 IR, with runtime action slots and persistent state updates.
- Added direct-versus-compiled semantic trace verification and a delayed-six regression fixture.
- Unknown or ambiguous grounds are rejected by the compiler rather than completed with guessed transitions.
- Terminal symbol observation now refuses ambiguous decoding when phase uncertainty overlaps multiple 8-PSK decision regions.
- Added development continuity and research frontier documents. No universal-space, general synthesis, physical hardware, or speed/energy claim is made.

Verification note: the new test suite and example are included in this increment. They must be run in the repository environment before treating this release as validated.


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
