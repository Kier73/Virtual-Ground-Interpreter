# Next research directions

## Build 21 — Partial, irreversible and environment-coupled grounds

Build 20's toy has a finite, deterministic, reversible operation group. A more demanding Virtual Ground must handle partial transitions and irreversible changes.

A Jenga-like abstract system is a useful candidate, but should initially be a symbolic stability model rather than a physical mechanics simulator:

- a state describes block occupancy, support relations and stability constraints;
- an operation removes or relocates one block;
- legality depends on the current support graph;
- some operations reduce future reachability;
- an observation may hide internal support relations;
- intention selects stability, height, or another task predicate;
- ground revision occurs if rules, available components or material properties change.

## Further proof obligations

1. Prove transition congruence for observer quotients rather than assuming it.
2. Compare strong bisimulation, weak/macro equivalence and task-specific equivalence.
3. Add partial actions and irreversible transitions.
4. Model resource-dependent grounds and Pareto-optimal navigation across time, memory, computation and execution costs.
5. Compare rule regeneration with cached state graphs as the state space scales.
6. Separate a true native macro action from a macro program that expands into primitive actions.
7. Study whether path signatures, group representations and observer kernels can compile into reusable procedural transformation operators.
8. Test whether a ground can be refined from observations without silently changing the target system's rules.
9. Separate controlled variables (the “banks”) from endogenous/environment-driven variables (the “flow”) and test when this partition changes with observer capability.
10. Define explicit migration maps for irreversible ground shifts and measure information lost across versions.

## Current checkpoint

Build 20 supports a finite operational formalization and demonstrates multiple representations of one small transformation system. It does not yet establish generality to all logical systems, continuous physical systems, chaotic dynamics, arbitrary software or constant-time navigation.
