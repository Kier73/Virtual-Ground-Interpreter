# Research Lineage and Integration Boundary

The Virtual Ground Interpreter consolidates several earlier strands of work. The earlier experiments are evidence and design inputs; they are not all runtime modules in this package.

## Predictive grounds and executable descriptions

The earlier finite-ground work represented an observed system as a deterministic predictive Mealy machine:

\[
M=(Q,A,Y,\delta,\lambda,q_0).
\]

Here `Q` is the observer's predictive context set, `A` the action alphabet, `Y` the observed output alphabet, `delta` the successor map, and `lambda` the output map.

The earlier compiler tested whether one action induces a cycle over all predictive states and whether other actions correspond to constant strides in that cyclic coordinate. When those conditions held, it emitted a modular-phase program. Otherwise it retained a general finite predictive automaton. This distinction is preserved as a design rule: use a compact algebraic Ground only when its transition laws are supported; otherwise keep the more general transition system.

## Observer-relative grounds

A Ground is relative to an observation contract: available actions, output channels, measurement domains, reset/continuation behavior, and probe constraints. Indistinguishable physical states may belong to the same observable quotient. The interpreter should therefore claim only what its declared observer can distinguish.

The earlier self-construction proposal used the loop:

\[
\text{trace evidence}
\to\text{predictive distinctions}
\to\text{latent context machine}
\to\text{executable Ground}
\to\text{counterexample refinement}.
\]

That Ground-construction loop is not yet implemented in this runtime. The present package consumes an explicit GroundSpec.

## Opaque streams and signal-derived events

The continuous-stream work investigated event boundaries, recurrent motifs, observer-relative tokenization and sparse checkpoint alignment. It supports a future adapter from raw sensor streams to event/state observations. Those event hypotheses must remain observer-relative and must not be silently promoted to semantic facts.

## Signal computation and observer interchange

The signal arithmetic work established a finite phasor representation for `Z/8Z`. Composition tests and observer-coordinate transformations supplied the immediate data-plane laws used by the current Signal8 backend.

The current Ground adopts the four automorphisms of `Z/8Z` as its observer family. It checks that semantic operations commute with observer changes. This is a specific finite result, not a claim that arbitrary signal, model-weight, sensor, or symbolic spaces are automatically isomorphic.

## What is newly integrated here

The present package joins those ideas into one executable boundary:

1. a versioned Ground contract declares what is valid;
2. a typed IR specifies a conditional computation;
3. a signal backend implements domain operations;
4. a machine executes persistent state transitions;
5. a trace records branch evidence and state changes;
6. fingerprints and checkpoints bind execution to its specification;
7. finite verification checks the declared algebra and machine behavior.

The first constrained task-expression compiler now lowers typed expression trees into the IR, including conditional branches. The missing high-level piece remains significant: translate a richer task/intent contract into an appropriate Ground-relative program, selecting among algebraic, automaton, signal, symbolic and other execution strategies. That is the larger interpreter capability this runtime is intended to make possible, not something this first executable core claims to have solved.


## Predictive transition-system bridge

The active interpreter now has a first-class predictive transition contract. It can import the archived Build 24 VG-PredictiveMealy-1 format, preserve missing pairs as unknown, represent conflicting alternatives as ambiguous, and compile complete finite grounds to the Signal8 IR. The direct transition semantics remains independent from the compiler and serves as the differential reference. The current lowering is deliberately bounded to eight states/actions and Z/8Z output values; it is not the Build 24 learner and does not yet import Build 26 online partial-ground histories.
