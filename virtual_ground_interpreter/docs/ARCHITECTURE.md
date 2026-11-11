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


## Signal8 execution observation adapter

`Signal8ExecutionAdapter` wraps the existing `SignalStateMachine.step()`
boundary. It does not alter instruction execution. For each successful step
it fingerprints a future-relevant runtime-configuration projection before and
after the instruction, serializes the original `ExecutionEvent`, and records
an observation-only ChannelMessage. The channel is materialized into the
EncounterLedger and linked to a TransportFrameReceipt before the message is
normalized into a concrete-step TransitionEvidence claim.

The runtime-state projection includes program and Ground fingerprints, PC,
halt state, initial/current memory, registers, and outputs. It excludes the
execution journal and undo stack so equivalent configurations in separate
runs can share an identifier. The adapter does not integer-decode phasors:
the typed transition output tuple is empty, while the raw event retains
serialized signal values and branch evidence.

Faults are retained as generic observations without a transition status.
Step-limited captures remain incomplete. The resulting evidence is not
automatically admitted, and the adapter's own reports are not independent
corroboration of the machine. The evidence policy and Ground-construction
stages remain explicit downstream operations.


## Signal8 execution traces and replay

The canonical `vgi/execution.py` path captures a Program and initial
SignalValue memory by stepping the existing Signal8 machine. It retains raw
instruction events, pre/post operational-state digests, Program/Ground
definitions and fingerprints, ChannelMessages, Encounters, and transport-frame
receipts. Failed attempts remain distinct from committed transitions.

`Signal8ExecutionAdapter.replay` rebuilds the declared Program and initial
memory in the selected VGI interpreter. `verify_execution_replay` compares
each frame's sequence, instruction and event digests, and pre/post state
digests, while ignoring transport identity and capture timestamps. Trace
construction also validates contiguous frame/step numbering, one-to-one
message and Encounter lineage, a continuous state-digest chain, and final
state closure.

This is same-runtime reproducibility, not an independent semantic oracle or a
claim that the Ground exhausts an external system. The previous in-progress
machine adapter remains available as `LegacySignal8ExecutionAdapter` for
compatibility; new code should use the canonical API.
