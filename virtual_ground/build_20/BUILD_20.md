# Build 20 — Virtual Ground and Compositional Navigation

## Summary

Build 20 converts the user's “Questions On the Virtual Ground” document into a proposed operational definition, then tests it in two small but structurally different systems:

1. **Rotor-4:** a finite reversible transformation system with group structure, exact shortest paths, multiple coordinates, observer quotients and macro navigation.
2. **Support-9:** a symbolic Jenga-like system with partial, state-dependent and irreversible operations, stability constraints and ground revisions.

The second fixture is important. It prevents the initial formalization from treating all logic as a group of reversible transformations.

## Verification

**43/43 tests pass.**

- All 648 Rotor-4 valid states are reachable from the canonical ground.
- Its 9 primitive operations generate 5,832 directed state/action edges.
- The graph diameter is 8; exact mean shortest distance from solved is 4.6451 operations.
- A two-stage macro decomposition reaches every target. It averages 5 primitive operations and differs from the shortest path for 230 targets. Its mean macro command count is 1.9213 (at most two), but each macro expands into primitive operations.
- A precomputed group-relative policy answers a start-to-target query by computing the relative transformation and looking up its route, without reconstructing the start state's full history. The table has 648 entries; this is fixed-domain precomputation, not a general constant-time theorem.
- Full/layout/orientation observers induce 648/24/27 equivalence classes.
- A layout-only intention can be satisfied without resolving orientation; a full-state intention cannot.
- Changing operation costs changes the chosen path.
- Removing twist operations changes the Rotor-4 ground and shrinks reachable states from 648 to 24.
- Support-9 has 232 reachable stable states and 774 directed removal edges; exhaustive enumeration confirms that every stable mask is reachable from the initial state.
- A revised support rule changes Support-9 reachability from 232 states to 200, again matching the complete set of stable masks.
- A layer-count-only observer is not transition-congruent in Support-9: equal layer counts can hide different legal moves.

All tests and results are deterministic and use the Python standard library. No physical puzzle, sensor, or TAPS recording was measured.

## Key interpretation

The best-supported distinction is:

**A Virtual Ground is not the materialized state space. It is the generative operational logic from which task-relevant state spaces, coordinates, observer quotients, and navigation procedures can be derived.**

Different grounds can trade memory, planning effort, command depth and information retention. A representation is adequate only relative to its observer and intention.

A higher-level macro can skip intermediate planning descriptions, but unless the target system supports the macro natively, it does not erase the primitive operations in its expansion. In the reversible fixture, group-relative navigation computes the transformation from current state to target directly; in the irreversible fixture, there is no group inverse, so navigation must respect the directed support constraints.

## Reproducibility

```bash
python -m unittest discover -s tests -v
python experiment.py
```

See `CONJECTURE_SCORECARD.md` for established versus open claims, and `VIRTUAL_GROUND_FORMALIZATION.md` for the mathematical framework.
