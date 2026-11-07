# Virtual Ground Compiler — Proposed Computational Architecture

## Purpose

Translate a declared logic and an intention into a task-adequate representation and a verifiable navigation program. This is a proposed architecture inferred from the Virtual Ground notes and the Build 20 experiments; it is not yet implemented as a general compiler.

## Inputs

\[
(\mathfrak G, O, J, C, s_{\rm current})
\]

- \(\mathfrak G\): ground specification (state constraints, legal operations, transition laws, invariants and version).
- \(O\): observer capability and available measurements.
- \(J\): intention or desired state/predicate.
- \(C\): resource and cost profile.
- \(s_{\rm current}\): retained current state or its observer-supported estimate.

## Outputs

\[
(\rho,\pi,\kappa)
\]

- \(\rho\): selected representation / coordinate system.
- \(\pi\): high-level navigation program.
- \(\kappa\): verification certificate containing the expanded operations, replay result, invariant checks and cost accounting.

## Proposed compilation stages

### 1. Ground validation

Check state constraints, action preconditions, transition semantics, invariants and ground version. Reject or mark unknown any rule that lacks evidence.

### 2. Intention resolution

Convert intention into a task predicate, objective, constraints and schedule. Determine which distinctions are necessary to decide task success.

### 3. Observer adequacy

Construct or select an observation map. Verify that its equivalence classes preserve goal distinctions and are transition-congruent for the operations used. If not, refine the observer state with additional variables.

### 4. Algebra and symmetry recognition

Determine whether the operation system is best represented as:

- a group (reversible transformations and relative elements);
- a monoid or semigroup (composable operations without universal inverses);
- a partial transition system (state-dependent legal actions);
- a hybrid of these, possibly with environment state.

Select a compatible representation: coordinates, group representations, harmonic coefficients, path signatures, event graphs, symbolic rewrite rules, or a materialized local graph.

### 5. Relative navigation

For a group ground, compute the transformation relating current and target states rather than replaying the history that produced the current state. In Build 20's execution-order composition convention:

\[
\Delta(s,t)=g_s^{-1}\odot g_t,
\qquad s\xrightarrow{\Delta}t.
\]

For partial/irreversible grounds, use directed search, constraint propagation or another planner that respects state-dependent preconditions. Do not invent an inverse where none exists.

### 6. Cost-aware plan selection

Minimize the declared cost vector or select a point on its Pareto frontier. A macro may be preferable because it reduces planning depth, memory or communication even when its primitive expansion is longer. Only count it as reduced execution when the target supports a native macro action.

### 7. Expansion and verification

Expand high-level operations when required. Replay from the current state and verify:

\[
\operatorname{Replay}(\mathfrak G,s_{\rm current},\operatorname{Expand}(\pi))\models J.
\]

Check legality and required invariants at every transition. If replay fails, do not render the result as verified.

### 8. Rendering and memory

Render the requested state or output through the selected representation. Retain the ground, selected coordinates, reusable macros, version, observer configuration and useful cache entries. Generate unrequested regions of state space only when intention requires them.

### 9. Ground revision

If observation indicates that the transition logic, variables, environment contract or invariants have changed, create a new ground version. Derive and verify a migration map before treating old coordinates or policies as valid under the new ground.

## The 2D-chart / 3D-observer analogy

A higher-level observer may describe a family of sequential trajectories through a smaller number of structural coordinates. It can then navigate between two states without replaying the conventional route used to discover either state. In Build 20, the relative group element and the two-stage macro are small finite analogues.

The analogy becomes a computational result only when the projection, retained variables, action correspondence and verification conditions are explicit. A shorter chart description does not prove shorter physical execution.

## A possible correctness contract

A compiled navigation result is valid only if:

1. the current state is represented consistently with the ground version;
2. the selected observer retains every distinction required by the intention;
3. all macro expansions are legal in order;
4. replay reaches a state satisfying the goal predicate;
5. every claimed invariant is checked under the transitions where it is meant to hold;
6. cost is reported in the units actually measured;
7. any ground revision invalidates or revalidates dependent policies and caches.

## Why this may matter for Virtual Layer

This architecture treats Virtual Ground as the reusable generative substrate, while representations and navigation programs become task/observer/resource-specific artifacts. A Virtual Layer-native interpreter could, in principle, recognize the operational algebra, compile a suitable coordinate system, derive a direct relative transformation or macro, verify it, and render only the requested state.

The unresolved work is learning or discovering the appropriate ground and symmetry from incomplete observations, then proving that the compiled representation preserves task-relevant semantics in unfamiliar systems.
