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
