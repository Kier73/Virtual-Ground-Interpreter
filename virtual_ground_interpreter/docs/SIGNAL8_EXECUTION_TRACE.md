# Signal8 execution trace as observation evidence

## Purpose

Signal8 already emits an instruction-level `ExecutionEvent` after every
successful machine step. The adapter makes those events available to VGI's
Encounter, Channel, and Evidence layers without changing instruction semantics
or treating the machine's own observations as independent corroboration.

Run:

```bash
python examples/run_signal8_execution_trace.py
python -m unittest discover -s tests -p 'test_signal8_trace.py' -v
```

## Capture boundary

`Signal8ExecutionAdapter.capture(machine, run_id=..., max_steps=...)` advances
an existing `SignalStateMachine` one instruction at a time. Each successful
step captures before/after runtime-configuration identifiers, exact instruction
identity, and the complete raw `ExecutionEvent`. It retains a ChannelMessage,
Encounter, TransportFrameReceipt, and concrete-step TransitionEvidence claim.

The runtime-configuration projection includes program and Ground fingerprints,
PC, halt state, initial/current memory, registers, and outputs. It excludes the
trace journal and undo stack so equivalent configurations reached in separate
runs can share an ID. Action identifiers bind PC, opcode, and the exact
instruction fingerprint. Runtime IDs use the `signal8-runtime/1:` prefix.

## What is observed

A successful step is recorded as a `known` transition claim for that one
concrete runtime configuration and instruction. Its target is the post-step
runtime-configuration ID.

The abstract transition output tuple is empty: this adapter does not decode
`SignalValue` phasors into semantic Z/8Z integers. The complete raw event,
including branch measurements, write locations, and serialized signal-valued
writes, remains in the ChannelMessage and Encounter.

The adapter does not create a policy, finalize an event, admit a transition,
or mutate a Ground. One machine reporting its own execution is not independent
source corroboration.

## Faults and incomplete runs

A failed instruction is rolled back by the existing machine. The adapter
retains a generic `execution_fault` observation containing the exception type,
message, program counter, and pre-step runtime-state ID. It has no transition
status and cannot be mistaken for a successful transition claim.

If `max_steps` is reached before HALT, capture status is `step_limit`. The
partial trace is retained and is not reported as completed. Reaching HALT
produces `halted`. Capture can begin from a machine that has already executed
some instructions; the run context binds the current starting configuration.

## Provenance and trust boundary

The adapter uses an observation-only ChannelContract and an in-process
transport identifier. The frame receipt binds each retained message to its
exact serialized payload. This is integrity metadata, not a cryptographic
signature, source authentication, independent process boundary, or proof of
physical signal transport.

## Resulting path

```text
SignalStateMachine.step()
        |
        v
ExecutionEvent + before/after runtime configuration
        |
        v
Observation-only ChannelMessage
        |
        +----> EncounterLedger
        |
        +----> TransportFrameReceipt
                    |
                    v
             TransitionEvidence
                    |
                    v
        [policy admission remains separate]
                    |
                    v
        [Ground construction remains separate]
```

This creates an auditable bridge from actual VGI execution into its
observation and evidence structures. It does not establish that Signal8
exhausts an external system or that this trace is a physical measurement.
