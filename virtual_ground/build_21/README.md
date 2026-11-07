# Virtual Layer Response Geometry — Build 21

**Theme:** Controlled variables, endogenous flow, exogenous environment and versioned Virtual Grounds.

This package extends Build 20's reversible Rotor-4 and irreversible Support-9 grounds with an environment-coupled discrete dynamical system. It demonstrates mass-balance invariants, observer refinement, belief-state navigation, resource Pareto routes, controlled viability and ground migration.

## Quick start

```bash
python experiment.py
python -m unittest discover -s tests -v
```

Python standard library only.

## Main files

- `flow_ground.py` — rules, state transitions, observers, partition refinement, belief planning, policy verification, Pareto navigation, viability and migration.
- `VIRTUAL_GROUND_COMPILER_DESIGN.md` — compiler stage and certificate contract.
- `experiment.py` — reproducible experiments and reports.
- `BUILD_21.md` — results and interpretation.
- `VIRTUAL_GROUND_DYNAMICS.md` — mathematical formalization.
- `OBSERVER_AND_BELIEF_NAVIGATION.md` — observation adequacy and belief controllers.
- `RESOURCE_AND_VIABILITY.md` — resource costs and safe-set control.
- `GROUND_VERSIONING_AND_MIGRATION.md` — ground shifts and migration.
- `legacy_build_20/` — source modules retained for regression checks.
- `Questions_On_the_Virtual_Ground_SOURCE.md` — source document supplied by the user.

## Scope

The flow fixture is synthetic and deterministic. It is not a hydraulic simulator. The Build 20 source modules are included to keep prior finite-ground results reproducible.
