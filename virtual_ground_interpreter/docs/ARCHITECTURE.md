# Virtual Ground Interpreter — Architecture

## Runtime path

```text
Task / external request
        |
        v
[Typed task-expression compiler]    bounded DSL implemented
        |
        |                             natural-language planner not implemented
        v
Validated Program IR
        |
        v
Ground contract check  <---- GroundSpec + fingerprint
        |
        v
Virtual Ground Interpreter
        |
        +---- Register file
        +---- Persistent signal memory
        +---- Signal8Backend
        |       +---- I/Q ingress / pilot calibration
        |       +---- ADD / SUB
        |       +---- observer reframing
        |       +---- robust equality / identity
        |       +---- I/Q egress
        +---- Conditional transition engine
        +---- Instruction trace / checkpoint / undo
        |
        v
Signal-valued outputs
        |
        v
Explicit observer / output adapter
```

## Component ownership

### GroundSpec

Declares the value domain, observer family, instruction set, ambiguity policy, assumptions, and evidence boundary. It carries a stable fingerprint. It is the authority for what the interpreter is entitled to execute.

### Backend

Owns the representation-specific algebra. The interpreter does not assume that every domain is a cyclic phase space. The current `Signal8Backend` is one concrete backend and the only implementation supplied here.

### Task expression compiler and Program IR

The constrained task DSL describes input references, arithmetic expressions, observer reframing, identity/equality guards, conditional expressions and named outputs. Its compiler emits a small validated control-flow language. It does not infer an algorithm from free-form text. The IR describes transitions but does not dictate how values are represented.

### Machine

Owns mutable execution state: program counter, registers, persistent memory, outputs, trace, and undo history. Its transition function is deterministic for a fixed program, initial memory, backend and Ground contract, except that invalid or indeterminate conditions trap.

### Verification

Checks algebraic laws, observer interchange, operation composition, and conditional paths. Verification is a separate module so runtime behavior does not depend on test-only semantic decoding.

## Why signal values are objects rather than integer tags

If the runtime stores the semantic residue alongside the phasor, accidental decoding can happen invisibly and invalidate the experiment. `SignalValue` stores only the calibrated phasor, observer coordinate and error bound. Terminal observation is a separate backend call. Tests patch that call to fail during machine execution.

## Conditional transitions are observer-invariant

The phase distance between two states is computed after mapping them into one observer coordinate. Equality and identity remain meaningful under all four automorphisms. An arbitrary numeric ordering of the labels 0–7 would not; it is therefore excluded from this Ground.

## State continuity

Memory cells retain signal values after each instruction. A snapshot stores the initial and current memory, program counter, registers, outputs and trace. A state digest detects checkpoint changes; program and Ground fingerprints prevent a checkpoint from being interpreted under a modified program or a different Ground. The restore operation does not reconstruct earlier undo snapshots.

## Extending the interpreter without binding it to 8-PSK

A future `ValueBackend` protocol should define:

- a domain identifier and observer-profile set;
- value validation and serialization;
- explicit ingress/egress;
- compatible observer conversion;
- operation implementations;
- relation/guard evaluation returning TRUE, FALSE or INDETERMINATE;
- propagation of uncertainty or confidence metadata.

A new backend must prove its own laws. It must not inherit the `Z/8Z` assumptions by accident.


## Predictive transition compilation

The predictive state-transition object is maintained separately from the signal backend. It supplies direct reference semantics and preserves known, unknown, and ambiguous transition evidence. The bounded TransitionCompiler lowers only complete deterministic grounds into the Signal8 IR. The compiled path uses runtime action slots, persistent signal-valued state, guarded dispatch, and explicit semantic emissions. Direct and compiled state/output traces are compared. See the formal specification and delayed-six example.


## Encounter memory before interpretation

The EncounterLedger sits upstream of observer-specific interpretation. It retains caller-supplied payloads, provenance, and context without assigning a required domain, action, channel, or state label. The records are immutable; append produces a new ledger snapshot with a canonical fingerprint.

The AssociationLedger is separate. A hypothesis may connect encounters from unrelated sources and contexts, but must provide a proposed relationship, rationale, experiment, and falsifier. Assessments append supporting, contradicting, or inconclusive results and cite encounter evidence. A supporting or contradicting assessment requires at least one encounter not used in the original hypothesis basis.

Neither layer mutates a predictive Ground. Any future conversion from an association into formal state/transition structure must pass through a separate construction and verification step. The ledgers preserve history; they do not authenticate external sources or infer a universal semantic space.


## Duplex channels and addressable perception

An observation channel and an addressable channel are different capabilities. The ChannelContract has a shared protocol identifier, plus independent observation, request, and response schema identifiers. A contract is addressable only when both request and response schemas are declared. A sensor's ability to emit a message does not imply that it accepts commands or can reply.

ChannelMessage separates observation, request, and reply directions. ChannelExchangeLedger validates protocol identity, unique message IDs, and replies correlated to earlier requests. Only inbound observations and replies can be materialized as Encounters; outbound request intents remain actions proposed by the observer.

PredictiveGroundAdapter provides a bounded internal example: a client sends a state/action query through the declared protocol and receives a correlated response. Known transitions return their target/output; unknown cells remain unknown; ambiguous cells return all represented alternatives. This is a dialogue with the model's declared structure, not communication with a physical environment. A real sensor or actuator requires a source-specific, authorized adapter.


## Evidence admission and reconstructability

The evidence layer preserves three different claims: a message has been received and retained as an Encounter; a transition claim has been admitted under a declared source/quorum policy; and a complete Ground has been replayed through compiled VGI over an explicit finite witness corpus.

Transition evidence binds the Encounter to message ID, source, channel, protocol, a transport-frame receipt, exact message digest, Ground identity, and context digest. A source counts once per state/action event; same-source contradictions, ties, dissent, missing sources, and unknown/ambiguous observations remain visible. Event closure is explicit and immutable.

Only AUTHORIZED finalizations contribute transitions to a Ground. Other events remain absent and therefore unknown. This process establishes a transition only relative to the declared policy and retained evidence; it does not establish external physical truth.

GroundReconstructionVerifier uses the existing TransitionCompiler and differential verifier. Its certificate binds the exact Ground/context and finite action sequences tested. It demonstrates replay agreement only for those witnesses, not universal reconstruction of the modeled environment.


## Runtime execution as a source of encounters

The active Signal8 machine is now an instrumented source in its own right.
`Signal8ExecutionAdapter` observes the actual `step()` boundary rather than
reconstructing instruction events from a completed Ground. Each committed
event retains the exact instruction and ExecutionEvent, signal-valued writes,
branch decision intervals, program/Ground identities, pre/post operational
state digests, and a local frame receipt. Failed instruction attempts are also
retained after atomic rollback, but are not treated as successful transitions.

The derived transition projection is deliberately downstream and weaker than
the raw trace. It groups only observed successful source/action/successor
tuples. It does not complete a state/action product, decide what an unseen
instruction would do, or admit a transition into a Ground. Repeated executions
are occurrences in the captured corpus, not independent source corroboration.

A trace can be replayed using the retained program and initial signal-valued
memory. Agreement checks reproducibility under the same runtime and Ground;
it is not an independent oracle or an external completeness claim.

    SignalStateMachine
      -> ExecutionEvent + before/after operational snapshots
      -> observation-only ChannelMessage
      -> TransportFrameReceipt + Encounter
      -> observed transition projection
      -> separately interpreted evidence claim
      -> explicit admission policy
      -> Ground

The local execution adapter is an in-process observation source. Its frame
receipt is integrity metadata, not host authentication, a network receipt, or
a cryptographic signature.
