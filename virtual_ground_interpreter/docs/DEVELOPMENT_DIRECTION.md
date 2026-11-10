# Development Direction — Virtual Ground Interpreter

The work is organized by capabilities and correctness obligations, not numbered builds.

## Current executable capability

The reference runtime now includes a signal-state machine with:

- persistent signal-valued memory and a register store;
- typed instructions for load/store, arithmetic, observer reframing, branching, emission and halt;
- three-valued equality/identity guards (`TRUE`, `FALSE`, `INDETERMINATE`);
- atomic trap behavior for indeterminate guards;
- trace events carrying branch evidence and signal-valued writes;
- pause/resume, reset, checkpoints bound to program/Ground fingerprints, and journal-based undo;
- a typed task-expression compiler that lowers a bounded expression tree to the instruction IR.

This is a control-flow machine whose data plane is signal-native. The instruction dispatcher remains ordinary software. The runtime currently has one concrete backend: finite `Z/8Z` in four 8-PSK observer coordinates.

## Immediate formal priorities

1. **Typed backend contract.** Extract the current implicit `Signal8Backend` methods into a formal backend protocol. Keep domain semantics outside the machine.
2. **Transition contracts.** Give each instruction preconditions, postconditions, read/write sets, reversibility classification, and evidence links.
3. **Proof composition.** Prove or mechanically check primitive transition contracts, then derive correctness for execution traces by induction over instruction count.
4. **Guard library.** Add predicates only when their invariance and uncertainty semantics are explicit. Identity/equality come first; ordered comparisons do not belong to a cyclic group.
5. **Ground versioning and counterexamples.** Store observer profiles, calibration evidence, conformance horizon, ambiguity records and counterexamples with each Ground version.

## Next state-machine extension

The current program-counter machine already executes guarded conditional transitions. The next step is to make the transition system a first-class Ground object rather than only an instruction sequence:

\[
\mathcal T=(Q,V,\Gamma,\Delta,q_0),
\]

where `Q` is control state, `V` is the typed signal-valued store, `Gamma` is a set of three-valued guards, and `Delta` maps a satisfied guard and state to a transition. `INDETERMINATE` must remain a first-class result.

A transition table should declare source state, guard, target state, state updates, read/write footprint, inverse metadata (when available), and evidence. The interpreter should be able to lower this representation into ordinary IR, then compare the lowered execution against a direct transition-system semantics. This supplies a second independent execution path for differential verification.

## Generalization path

### Multiple computational domains

Add a second backend only after identifying a useful common semantic interface. Candidate domains include other finite groups, vector/linear signal spaces, timed event structures, and task-specific weight-space transformations. A backend must declare which relations it preserves.

### Ground construction from observations

Reintroduce the earlier predictive-context workflow as a Ground constructor:

\[
	ext{observations}
ightarrow	ext{predictive distinctions}
ightarrow	ext{candidate transition system}
ightarrow	ext{executable Ground}
ightarrow	ext{counterexample refinement}.
\]

The constructor must distinguish observable equivalence from physical identity and retain unresolved ambiguities. When a cyclic/phase law is not supported, it must emit a general finite automaton rather than force a group structure.

### Adaptive interpretation

The current typed task-expression compiler is a deliberately narrow first translation layer. The long-term interpreter should accept a richer task/intent contract, identify the properties the output must preserve, select compatible observers and operations, estimate cost, and choose an execution path. Natural-language interpretation, algorithm discovery, and resource-aware strategy selection are not implemented in the current runtime.

### Verification

The trusted core should remain small. Candidate architecture:

- a minimal typed IR;
- a small transition semantics kernel;
- primitive contracts for backend operations;
- proof rules for sequencing and guarded branching;
- machine-checkable proof objects or independently replayable certificates;
- differential tests against a transparent reference semantics.

No claim of verified execution should be made until the transition semantics and proof checker are independently checked.

## Decision rule

Prefer the smallest extension that introduces a new, verifiable capability. Do not add a generalized abstraction merely because it might eventually be useful. Preserve direct fallbacks, expose uncertainty, and record where the chosen interpreter strategy loses against a simpler implementation.


## Current integration result

A first-class GroundTransitionSystem now represents predictive states, actions, output channels, known/unknown/ambiguous edges, support counts, and evidence references. A Build 24 VG-PredictiveMealy-1 adapter imports the archived delayed-six model. Complete grounds can be compiled into the existing Signal8 IR for a fixed action-sequence length, with actions supplied as runtime signal-valued inputs. Direct and compiled executions are compared by their semantic state and output traces.

The current compiler is deliberately bounded to eight states, eight actions, and Z/8Z output symbols. It refuses partial or ambiguous grounds. This is the first executable bridge from the predictive-ground archive into the active machine; it does not yet embed the Build 24 learner or the Build 26 online partial-ground learner.

## Immediate next priorities

1. Extract the current backend assumptions into a typed backend protocol and add instruction pre/postconditions, read/write sets, reversibility metadata, and evidence references.
2. Add a second backend with a distinct domain and independent semantic laws. Do not reuse Signal8 assumptions by default.
3. Add an observation-driven constructor for GroundTransitionSystem that imports Build 26 partial evidence while preserving unknown and ambiguous edges.
4. Add intention/resource contracts and compare direct execution, generated rules, and compiled paths against complete cost baselines.
5. Keep physical signal execution and speed/energy work in separately labelled evidence tiers. The current numerical signal path is not physical hardware and has no demonstrated cost advantage.
