# Build 20 — Virtual Ground and Compositional Navigation

## Status

- **43/43 tests pass** using Python's standard library only.
- Exhaustive finite-state verification completed.
- 648 valid states, all reachable in the base ground.
- 5,832 directed state/action edges materialized for verification.
- A second, orientation-locked ground reaches only 24 states from the same initial state.
- All experiment outputs are generated from the included deterministic toy system.
- No physical puzzle, Jenga structure, sensor recording, or TAPS audio was measured.

## Core question

Can a compact generative description provide a navigable coordinate for a system's possible transformations, while allowing different observers and resource profiles to use different but compatible grounds?

Build 20 turns the user's Virtual Ground notes into an executable finite example. A ground specifies valid states, operations, transition laws, invariants, observers, intentions and costs. It can generate the state graph procedurally rather than storing the graph as its definition.

## Run

```bash
python -m unittest discover -s tests -v
python experiment.py
```

No third-party packages are required.

## Package contents

- `virtual_ground.py` — state algebra, transformations, observers, quotients, planners and cost model.
- `partial_ground.py` — symbolic Jenga-like support logic with partial, irreversible actions.
- `experiment.py` — deterministic exhaustive experiment and report generation.
- `tests/test_build20.py` — 33 rotor-ground unit/integration tests.
- `tests/test_partial_ground.py` — 10 partial-ground tests.
- `VIRTUAL_GROUND_FORMALIZATION.md` — proposed formal definition and proof obligations.
- `VIRTUAL_GROUND_COMPILER.md` — proposed observer/intention/resource-driven compiler architecture.
- `REPRESENTATION_GROUNDS.md` — primitive, coordinate, explicit-graph, macro and observer grounds.
- `PARTIAL_GROUND_COMPARISON.md` — irreversible support-logic ground and the Jenga-like example.
- `CONJECTURE_SCORECARD.md` — verified finite properties versus open conjectures.
- `EXPERIMENT_PROTOCOL.md` — complete experiment design and limitations.
- `Questions_On_the_Virtual_Ground_SOURCE.md` — supplied source document, included unchanged.
- `reports/build_20_results.json` — numerical results.
- `reports/support_ground_results.json` — partial/irreversible support-ground experiment.
- `reports/state_navigation_catalog.csv` — exact and factorized distance for every state.
- `reports/materialized_transition_graph.json` — the graph generated from the ground rules.
- `reports/shortest_policy_table.json` — precomputed exact unit-cost policy for all Rotor-4 states.
- `ground_schema.json`, `support_ground_schema.json`, `observer_schema.csv`, `cost_schema.csv` — machine-readable schemas.
- `INVARIANT_LEDGER.csv` — tested invariants and open claims.
- `MANIFEST.sha256` — package integrity manifest.

## Important interpretation

The four-module rotor puzzle is an original finite algebraic fixture inspired by twisty puzzles. It is **not** a mechanical model of a full Rubik's Cube. Its value is that its full legal state space is small enough to enumerate, test and prove exactly.

The experiment demonstrates finite soundness, reachability, coordinate equivalence, observer-dependent information loss, task-specific quotient navigation, macro expansion and ground revision. It does **not** establish that arbitrary systems have finite, computable, constant-time Virtual Grounds.
