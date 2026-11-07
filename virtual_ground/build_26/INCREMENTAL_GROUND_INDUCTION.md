# Incremental Virtual Ground Induction

## Objective

Build 26 extends the Build 25 online tracking architecture so the running observer can construct a partial predictive ground while a non-resettable stream continues.

Unlike Build 24, Build 26 does not use a resettable membership-query teacher. Unlike Build 25, it does not require a complete precompiled predictive machine before processing events.

## Event interface

The connector supplies:
- finite action names;
- selected sensor-channel identifiers;
- action-step identity;
- integer-valued channel observations.

Actions are registered in contiguous order. Sensor channels may arrive asynchronously, before or after action registration, and out of order across steps. An event commits only when all selected channels have arrived; committed events remain in step order.

Two observation contracts are explicit:

- `observation`: the output vector is a post-action observation of the resulting state;
- `mealy`: the output vector is an action-conditioned response; the action/output pair enters the predictive-history signature.

These are not interchangeable. A connector must declare which contract it implements.

## Predictive history contexts

For a finite history horizon `h`, the context key is the suffix of the last `h` event marks. Event marks are output vectors in observation mode and action/output pairs in Mealy mode.

For event `i`, let `c_i` be its pre-event context and `c_{i+1}` its successor context. Every committed event contributes a partial transition observation:

\[
(c_i,a_i)\mapsto(y_i,c_{i+1})
\]

A pair is marked known only when all retained evidence for that context/action agrees. Unobserved pairs remain unknown. Conflicting alternatives remain ambiguous until a longer history horizon separates them or the maximum horizon is reached.

## Horizon refinement

If a context/action pair has multiple observed output/successor alternatives, the learner increases the history horizon and rebuilds the partial model from the retained event window. A refined model is still a bounded predictive history description, not proof of physical hidden state.

If collisions persist at the configured maximum, the learner reports `unresolved_context_collision`; it does not invent a stochastic law or silently select an alternative.

## Quotient minimization

The learner merges history contexts only when they have matching observed-action coverage and their known outputs and successor partition classes agree. Unknown transitions are not treated as identity operations and are not silently generalized across different coverage patterns.

The result is a quotient of the currently observed partial machine. It can over-split under sparse evidence; it is not claimed to be the globally minimal predictive machine.

## Compilation

The current compiler emits `VG-IncrementalPartialGround-1`. Each state/action pair is explicitly one of:
- `known`: exactly one observed output and successor class;
- `ambiguous`: multiple conflicting observed alternatives;
- `unknown`: no evidence.

`PartialExecutableGround.step` executes only known edges. Attempting an unknown edge raises `UnknownTransitionError`.

A replay certificate checks the retained observations against the compiled partial specification. It explicitly does not prove unseen transitions.

A separate exploration selector can choose a safe unknown edge using declared cost/risk. It explicitly reports `information_gain_estimate: null`: because the transition is unknown, the learner cannot honestly calculate its output entropy in advance. This is novelty-per-cost exploration, not an information-gain estimator.

## Resource and version discipline

- pending action/observation steps are bounded;
- retained event history is bounded;
- a truncated left boundary is not reintroduced as a learned transition;
- completed duplicate cache and audit history are bounded;
- context count has a configured budget;
- structural fingerprints exclude mere support-count changes;
- version lineage records structural changes and horizon refinements;
- conflict history is capped at 64 records and version history at 128 entries, with lifetime version counters retained.

## Build 26 limits

This implementation assumes deterministic, exact integer observations; a supplied finite action alphabet; supplied channel identities; and a declared observation-vs-Mealy contract. It does not learn stochastic likelihoods, arbitrary raw signal segmentation, continuous state variables, unknown action alphabets or general symbolic source code. A single non-resettable stream may not exercise every action from every predictive context; unobserved transitions must remain unknown.
