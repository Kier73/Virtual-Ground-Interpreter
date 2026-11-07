# Virtual Ground Compiler — Build 21 executable stage

## Scope

Build 21 implements a bounded compiler stage for a finite deterministic ground. It is not yet a general Virtual Layer interpreter or a constant-time compiler.

## Input

`compile_navigation_task(ground, observer, initial_observation, goal, max_depth)`

The inputs are:

- a versioned generative ground;
- an observer function / sensor profile;
- one current observation;
- an intention represented as a goal predicate;
- a planning horizon.

## Compilation pipeline

1. **Ground validation.** Confirm the state, action and transition rules are internally valid. Verify the conservation ledger.
2. **Observation inversion.** Generate the finite belief set of all full states compatible with the supplied observation.
3. **Predictive sufficiency check.** Refine the observation partition under action-labelled transitions. If the sensor partition is not transition-congruent, do not treat it as a memoryless abstract state.
4. **Belief-policy synthesis.** Select only actions legal in every state in the current belief. Apply the action to all possibilities, partition successors by the next observation, and recursively solve every branch.
5. **Certificate verification.** Independently replay the policy tree. Check action legality in every possible state, full coverage of next observations, terminal satisfaction of the intention, and declared worst-case depth.
6. **Resource selection.** Compare nondominated route costs and select a feasible route/policy under the current resource profile.
7. **Ground-version guard.** If structural laws changed, do not silently reuse compiled policies. Check the old-to-new state migration and recompile against the new ground.

## Output

On success:

- ground version;
- observer and initial observation;
- initial belief size;
- policy tree, indexed by future observations;
- worst-case number of transitions;
- independent verification certificate.

On failure, the compiler reports whether the observation is inconsistent with the ground or no robust policy exists within the requested horizon.

## Certificate meaning

A successful certificate proves only that the policy reaches the declared goal from every state in the supplied finite belief, under the exact deterministic ground and observer model. It does not prove that the model matches a physical environment, that observations are noise-free in reality, or that the policy is optimal under unmodeled costs.

## Architectural implication

This supports a staged Virtual Ground interpreter:

`ground rules + observer + intention + resource profile`

`→ admissible representation / belief`

`→ policy or macro`

`→ invariant and reachability certificate`

The representation is selected because it is adequate for a declared task, not because it is universally smallest or universally complete.
