# Build 20 Experiment Protocol

## Purpose

Test whether a stored generative specification can procedurally recreate a complete finite state space, support multiple equivalent navigation representations, select observer-specific quotients from intention, compose operations, and distinguish a state transition from a ground revision.

## Fixture

An original four-module rotor puzzle:

- four distinguishable pieces;
- each piece has a modular orientation in \(\mathbb Z_3\);
- legal states have orientation sum zero modulo three;
- primitive operations are three adjacent swaps and three independent pair-twists, each with inverse.

This is a mathematical toy inspired by twisty puzzles, not a model of full Rubik's Cube mechanics or a physical object.

## Procedure

1. Generate the valid state set from the invariant definition.
2. Generate nine primitive operations from the ground rule.
3. Exhaustively traverse from the solved state.
4. Compare generated reachability with the full valid state set.
5. Verify state-coordinate bijection and transition commutation for every state/action pair.
6. Verify inverse, composition, identity and sampled associativity.
7. Compute exact unit-cost shortest paths.
8. Generate a two-stage factorized macro plan for every target and replay each primitive expansion.
9. Compare macro command count, primitive expansion length and shortest primitive distance.
10. Build observer quotients for full state, layout only and orientation only; verify transition congruence before navigating on them.
11. Change operation costs and verify the optimal route can change without changing the underlying legal state system.
12. Revise the ground by removing orientation operations; measure the new reachable region.
13. Test stable-observation consensus under a configurable dwell threshold.

## Companion fixture: Support-9

A second symbolic fixture prevents the ground formalization from assuming reversibility:

- nine blocks arranged in three levels of three;
- an explicit support graph between adjacent levels;
- state = nine-bit occupancy mask;
- an elevated remaining block must retain at least one support below;
- removing a block is legal only when the resulting state remains stable;
- removal is irreversible and strictly decreases the number of present blocks.

The full initial ground has 232 reachable stable masks and 774 directed edges. Exhaustive enumeration over all 512 occupancy masks confirms that every mask satisfying the stability predicate is reachable. Revising block 6's supports from `(3, 4)` to `(3,)` creates ground version 2 with 200 reachable stable masks and 646 edges. A level-count observer is not transition-congruent: identical counts can hide different support identities and legal actions.

This is a symbolic constraint model, not a physical mechanics simulation.

## Expected invariants

- Permutation remains bijective.
- Each orientation remains in \(\mathbb Z_3\).
- Total orientation remains zero modulo three.
- Every primitive operation is invertible in the Rotor-4 base ground.
- Every Support-9 removal action preserves its declared stability predicate and reduces occupancy by one.
- The generator set reaches every valid state.
- Coordinate encoding is one-to-one and onto for the fixed finite fixture.
- Coordinate transitions commute with encoded state transitions.
- Every macro expansion reaches its declared target.
- The observer quotient is transition-congruent for its declared operation labels.
- Ground revisions change the legal operation set or support predicate and may reduce reachability.

## Reproducibility

```bash
python -m unittest discover -s tests -v
python experiment.py
```

All experiments are deterministic. No third-party dependencies, internet access, external data or physical instruments are required.

## Limitations

- The state space is deliberately tiny and finite.
- Rotor-4 base operations are deterministic and reversible; Support-9 removal actions are deterministic and irreversible.
- The macro decomposition is constructive but is not guaranteed to minimize primitive operations.
- The observer quotients are exact only for their explicit projection maps.
- The consensus test uses repeated identical observations and does not model sensor noise or multiple independent observers.
- No general constant-time shortest-path theorem is inferred.
