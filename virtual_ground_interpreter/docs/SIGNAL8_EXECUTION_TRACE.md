# Signal8 execution trace as observation evidence

Signal8 emits an instruction-level `ExecutionEvent` after each successful
machine step. The adapter connects those events to VGI's Encounter, Channel,
and Evidence layers without changing instruction semantics.

Run:

```bash
python examples/run_signal8_execution_trace.py
python -m unittest discover -s tests -p 'test_signal8_trace.py' -v
```

## Capture boundary

`Signal8ExecutionAdapter.capture(machine, run_id=..., max_steps=...)` steps
an existing `SignalStateMachine` and retains the full before/after runtime
configuration, stable IDs for those configurations, exact instruction
identity, and raw `ExecutionEvent`. The capture retains the complete program
and Ground definitions, initial/final configuration, and machine trace. Each
event is bound to a ChannelMessage, Encounter, TransportFrameReceipt, and
concrete step-level TransitionEvidence claim.

The runtime projection contains program/Ground fingerprints, PC, halt status,
initial/current memory, registers, and outputs. It excludes trace journal and
undo stack so equivalent configurations in different runs share an ID. Full
snapshots remain attached to observations, allowing consumers to recompute
IDs and inspect the signal-valued data that produced each transition.

## Context versus run provenance

The context digest binds adapter version, Ground identity/fingerprint, program
fingerprint, and initial runtime configuration. It excludes run ID, allowing
equivalent runs to be compared. Run ID remains in messages and source refs.
The in-process transport ID is scoped by run ID because sequence numbers restart
for each capture. Thus independently retained captures cannot collide on
transport/source/channel/sequence identity.

## What is observed

A successful step is a `known` transition claim for one concrete runtime
configuration and instruction. The target is the post-step configuration ID.
The abstract output tuple is empty: the adapter does not decode phasors into
semantic Z/8Z integers. Raw events and full configurations preserve branch
measurements, writes, and signal values.

These records provide replay material, not a replay certificate. The adapter
does not create a policy, finalize events, admit transitions, or mutate a
Ground. Repeating the same capture does not create independent source votes.

## Faults and incomplete runs

Failed instructions are rolled back by the machine. The adapter retains a
generic `execution_fault` observation with the exception, attempted
instruction when available, and full pre-step configuration; it has no
transition status. Reaching `max_steps` before HALT yields `step_limit`.
Only HALT produces `halted`.

## Trust boundary

The channel is observation-only. Frame receipts bind exact payload digests
but are not cryptographic signatures, source authentication, an independent
process boundary, or proof of physical signal transport.

## Dataflow

```text
SignalStateMachine.step()
        |
        v
full before/after configuration + ExecutionEvent
        |
        v
ChannelMessage -> EncounterLedger
        |
        +-> run-scoped TransportFrameReceipt
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
