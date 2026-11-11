# Verified execution orbits and logical-time navigation

## Purpose

This experiment connects retained execution, independent semantic verification, policy-gated partial Ground construction, and direct navigation to a logical-time coordinate.

It adapts the strongest relevant E-CPU ideas to VGI:

- an observed trajectory is evidence, not automatically a law;
- an admitted Ground is a versioned transition description, not a stored enumeration of every possible state;
- the trajectory's ordinal/logical coordinate is distinct from elapsed physical time;
- inverse or future navigation is justified by a verified generator, not by guessing a state.

The first implementation is deliberately finite. It compiles one deterministic state-to-action policy over a partial VGI Ground, discovers a closed cycle only when every traversed edge is known and single-valued, and uses the proven cycle to answer distant logical-time queries without replaying every intermediate step.

The architectural reference is E-CPU's [observed-orbit pipeline](https://github.com/Kier73/E-CPU/blob/main/mailcpu/observed_orbit_pipeline.py), its [observer-relative orbit navigator](https://github.com/Kier73/E-CPU/blob/main/mailcpu/observer_orbit.py), and its [temporal coordinate model](https://github.com/Kier73/E-CPU/blob/main/mailcpu/temporal.py). VGI does not import E-CPU runtime code. It adapts the separation between observed path, admitted generator, coordinate navigation, and receiver-side realization to VGI's partial Ground and evidence model.

## What is meant by an orbit?

Let a Ground be \(G=(S,A,O)\), where \(S\) is the finite predictive-state vocabulary, \(A\) is the action vocabulary, and \(O\) maps a known state/action pair to one successor and an output.

A deterministic policy chooses one action for each state:

\[
\pi:S\rightarrow A.
\]

The induced partial state evolution is

\[
s_{t+1}=T_G(s_t,\pi(s_t)).
\]

The output at that step is

\[
o_t=\lambda_G(s_t,\pi(s_t)).
\]

The pair \((G,\pi)\), not Ground alone, defines this particular orbit. A different policy can create a different trajectory through the same transition system.

For a finite Ground, if the policy is defined and every selected transition is known and single-valued, the state sequence must eventually repeat. If \(s_\mu=s_{\mu+p}\), then deterministic continuation establishes

\[
s_{\mu+k}=s_{\mu+p+k}
\quad\text{for all }k\geq0.
\]

Here \(\mu\) is the transient-prefix length and \(p\) is the cycle period. Once that closed path is validated, any logical-time query \(n\geq\mu\) reduces to

\[
r=\mu+((n-\mu)\bmod p).
\]

The navigator returns the state at requested coordinate \(n\) using the retained representative at coordinate \(r\). This is an exact logical-time jump within the fixed Ground and policy, not an approximation or a physical time-travel claim.

## Observation, semantic effect, and evidence

ExecutionOrbitAdapter consumes:

1. a Signal8ExecutionTrace;
2. its corresponding ReferenceExecutionReport.

The report must be match and must bind the exact trace, Program, and machine Ground fingerprints. This avoids turning an internally consistent but semantically wrong runtime trace into an observation of the intended instruction semantics.

All traces within one ingestion must share the same Program, machine Ground, and initial runtime-state digest. Multiple captures therefore corroborate one origin/context; they are not silently treated as separate origins on a common time axis. A different initial condition requires a separate ingestion and logical clock until a multi-origin Ground composition contract is added.

The adapter preserves each raw event inside the original trace and Encounter. It separately derives a semantic-effect token for transition outputs. The token excludes occurrence-only fields (step, pc_before, and opcode); the action descriptor already binds the instruction address/opcode, and the source trace retains the complete original record. It retains pc_after, branch evidence, writes, and write values.

This distinction is essential. Two identical operations at different points in a loop have different occurrence indices but the same semantic effect. Treating the occurrence index as the output would make deterministic recurrence appear contradictory.

The semantic-effect codebook assigns stable integer tokens and represents them in base-eight output channels. These are categorical labels for observed event effects; they are not a claim that arbitrary event payloads are native Signal8 symbols or that the original event has been semantically compressed without loss. The full event, digest, Encounter, and message remain available.

## Delivery disorder and partial knowledge

The adapter can model delivery order separately from the instruction order. The delivery_orders argument allows a test harness to present frames in another order, repeat a sequence (duplicate), or omit sequences.

The resulting FrameDeliveryRecord distinguishes:

- accepted transition observation;
- retained failed attempt;
- duplicate delivery;
- missing frame.

The logical tick is derived from the trace's original instruction-attempt sequence, not from arrival index. Thus reordering changes delivery history but does not rewrite the original event coordinate. Arrival index is only an ordinal in the adapter's delivery sequence; it is not a measured network delay or duration. Delayed delivery can be represented as a later arrival position, but physical transport latency requires a separately calibrated monotonic-time measurement.

For example, with base tick 0, instruction frame 3 is anchored at logical tick 2 even when it arrives first (arrival index 0). The state after that instruction, if successful, is at tick 3. A missing frame leaves its transition unknown; it does not cause later frames to be renumbered.

A missing frame contributes no transition evidence. If a later frame is present, its own retained state_before_digest still identifies the state from which that later operation was observed; this does not reconstruct the missing transition. A failed instruction is retained as an attempted operation but is not projected as a committed state transition because execution failure rolls back atomically.

Every successful, delivered frame is normalized into a TransitionEvidence record bound to its original Encounter, ChannelMessage, transport receipt, payload digest, source, and machine Ground fingerprint. The evidence ledger still enforces its source policy and quorum. A reference match does not authenticate a source; the receipt is an integrity binding to the retained message, not a cryptographic source signature. The dedicated conflict control injects a synthetic competing-source claim to exercise refusal; it is not evidence from an actual independent sensor or host.

No transition is finalized automatically. Call ExecutionOrbitIngestion.finalize(source_state, action) for the intended state/action observations. Only AUTHORIZED finalizations enter build_ground(). Refused or conflicting claims stay in the evidence ledger; absent or non-admitted pairs remain unknown in the resulting Ground.

## Logical time is not elapsed time

OrbitTimeCoordinate(clock_id, tick) is a non-negative integer state coordinate in one named logical orbit. The initial machine state is at the base tick. A frame for instruction attempt with step index k is anchored at the source-state coordinate base_tick + k; after one successful transition, its successor state is at base_tick + k + 1. A failed attempt is retained at its source-state coordinate and does not create a committed successor.

It is not:

- a wall-clock timestamp;
- a monotonic duration;
- a network transport sequence;
- a vector-clock causal timestamp;
- an estimate of physical computation time.

This follows the E-CPU temporal discipline: event progression, scheduler ticks, causal order, monotonic elapsed duration, and wall time are different coordinate domains. OrbitTimeCoordinate can be mapped to an E-CPU SchedulerReading only when clock_id intentionally identifies the same scheduler and tick has the same declared semantics. It must not be compared with elapsed nanoseconds or wall time.

## Fixed-policy cycle compilation

OrbitPolicy is separate from the transition model:

- OrbitPolicy.from_mapping accepts an explicitly selected action for each state;
- OrbitPolicy.derive selects an action only when exactly one action has been observed for a state;
- multiple observed actions remain a policy ambiguity;
- a selected action whose transition is unknown or ambiguous stops compilation.

OrbitNavigator.compile follows this policy from a chosen start state. Every path edge is checked against the immutable Ground. When a state repeats, the compiler retains the transient prefix, cycle start, and cycle period, and OrbitIndex validates the path and the closing state equality.

The navigator refuses to extrapolate through:
- an unknown transition;
- an ambiguous transition;
- a state with no selected policy action;
- an ambiguous policy;
- an exhausted compilation horizon.

A target absent from a closed orbit can be reported as unreachable_on_closed_orbit. This means absent from this one policy-induced orbit. It does not mean unreachable under every other policy, action sequence, or unrepresented physical process.

## Running the experiment

From the VGI package directory:

    python examples/run_execution_orbit_navigation.py

The example:
1. captures a simple looping Signal8 program;
2. checks the trace with the independent semantic reference;
3. ingests its frames into policy-gated evidence;
4. explicitly finalizes the observed state/action pairs;
5. builds a partial Ground and fixed policy;
6. verifies the finite prefix and closed cycle;
7. looks up a state at logical time \(10^{12}\) using cycle reduction.

The example advances a virtual logical coordinate only. It does not wait for one trillion steps, change the host clock, or mutate an external process.

## Interpreting the user's orbit intuition carefully

The intuition that a concept or logical system is "in motion" is productive when expressed as a transition law plus a path. The past states of a system are the transitions that actually occurred. A captured trace can preserve evidence of those transitions; a Ground can explain and replay them within its declared scope.

The VGI model does not claim that an unobserved state is physically in quantum superposition. Here, unobserved or competing possibilities are represented epistemically:

- unknown: no admitted transition is available;
- ambiguous: more than one retained outcome remains possible;
- unresolved: current observation and horizon do not justify equivalence or distinction;
- known: one transition has been established under the declared evidence policy.

These are not quantum states.

Likewise, observation does not automatically execute the observed system. This architecture keeps acquisition, interpretation, candidate model update, policy admission, navigation, host authorization, and any eventual physical commit as separate operations. A reference match supports a semantic claim about the retained trace; it does not retroactively execute the physical past.

A future virtual jump is justified when a verified transition law supports it. The present implementation proves this for finite deterministic cycles. It does not yet implement general inverse navigation or fast exponentiation of arbitrary affine transformations. Those should be added only with a certificate showing that the shortcut preserves the task-relevant state and outputs.

## Next extensions

1. Build-version lineage: bind each OrbitIndex to the exact Ground, evidence-ledger fingerprint, and policy fingerprint; require re-compilation when any of these change.
2. Partial-orbit refinement: use the existing three-valued partial predictive relations to identify whether the next missing observation blocks cycle closure or whether a competing policy prevents a unique orbit.
3. Certified algebraic jumps: add a separate fast-forward interface for admitted transformation families (for example, modular affine maps) with an independent reference and explicit error/overflow rules. Do not use it as a fallback for an unknown transition.
4. Time-domain bridge: connect logical instruction coordinates to E-CPU scheduler ticks only through an explicit shared scheduler identity, while separately recording measured monotonic duration and receiver admission latency.
5. State-target navigation: allow a target to be a predicate or observer-relative class, not only an exact state digest. The result must report when the predicate has multiple matches or cannot be resolved.

## Proof boundary

A closed-cycle result establishes exact recurrence for the finite Ground and fixed policy that were actually constructed and replayed. It does not prove:
- that the Ground is a complete description of an external system;
- that every possible policy has the same orbit;
- that an unobserved state physically exists;
- that a logical tick corresponds to a physical second;
- that the target is unreachable outside this orbit;
- that the source or transport is cryptographically authenticated;
- that the host has executed or committed an external state change.

The useful achievement is narrower and concrete: after observation, independent checking, policy-gated admission, and finite replay, the interpreter can locate a future state on a verified deterministic orbit without enumerating every intervening logical step.
