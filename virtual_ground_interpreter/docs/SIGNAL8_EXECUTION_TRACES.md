# Signal8 execution encounters and observed transition projection

## Purpose

The active VGI runtime already exposes an instruction-step boundary through
SignalStateMachine.step(), ExecutionEvent, and a tamper-detecting machine
snapshot. This adapter makes that boundary available to the encounter,
channel, and provenance architecture.

The capture is deliberately interpretation-neutral at the observation layer:
it retains the exact instruction event, program and Ground fingerprints,
signal-valued writes, pre/post operational-state digests, and transport-frame
receipt. It does not call terminal symbol observation.

## Data path

    Program + initial SignalValue memory
      -> SignalStateMachine.step()
      -> ExecutionEvent + pre/post snapshot digests
      -> ChannelMessage (observation)
      -> TransportFrameReceipt
      -> EncounterLedger
      -> observed transition projection
      -> same-runtime replay comparison

Successful instruction events and failed attempts are both retained. A failed
instruction has an atomic rollback in the existing machine; the adapter records
the failed attempt and equal pre/post state digests, but never treats it as a
successful transition.

## Operational-state fingerprint

The adapter fingerprints the machine snapshot after excluding only its trace
history and the snapshot's own digest field. Program identity, Ground identity,
program counter, initial memory, current memory, registers, outputs, and halt
state remain in the state digest.

This choice makes repeated visits to the same operational state comparable.
It also avoids treating the append-only act of recording history as a state
transition. The complete final snapshot and every raw ExecutionEvent remain
available in the retained trace envelope.

## Trace records

Each successful observation carries:

- program and Ground fingerprints;
- zero-based step and program-counter values;
- the exact instruction object and its digest;
- the raw ExecutionEvent, including branch interval evidence and signal-valued
  writes;
- pre- and post-state digests;
- a source reference and payload digest in EncounterProvenance;
- a TransportFrameReceipt binding the channel message ID, source, channel,
  sequence, transport ID, and exact serialized message digest.

A failed attempt retains the attempted instruction, exception type/message,
and atomic pre/post state digests. The frame receipt is integrity metadata,
not cryptographic source authentication.

## Observed transition projection

project_execution_transitions groups only successful records actually present
in supplied traces. Its action descriptor is the instruction position,
opcode, and exact instruction digest. Its state identifiers are operational
snapshot digests. It reports either one observed successor or conflicting
successors for each witnessed source/action pair. The occurrence count counts
records in the supplied traces; it does not represent independent source votes.

It does not enumerate the Cartesian product of observed states and actions.
An absent pair is unqueried, not impossible, and not evidence of a negative
transition. A projection is not a Ground and cannot authorize Ground
transitions. In particular, the runtime's trace is evidence about the
execution that occurred, not proof that the program or Ground completely
describes an external source.

## Replay verification

Signal8ExecutionAdapter.replay reconstructs the Program and initial signal
memory retained by the trace, then executes them in the selected interpreter.
verify_execution_replay compares program/Ground identity, initial operational
state, status, instruction digests, event digests, and pre/post state digests.
It deliberately ignores trace IDs, transport IDs, and capture timestamps.

A match establishes deterministic replay agreement for the supplied program,
initial memory, Ground, and captured instruction sequence. It does not prove
that the Ground exhausts an external system or authenticate the original source.

## Run

From virtual_ground_interpreter/:

    python -m unittest discover -s tests -p 'test_execution.py' -v
    python examples/run_signal8_execution_trace.py
    python -m unittest discover -s tests -v
    python -m vgi verify

The focused tests and runner are included in this increment. Do not report
them as passing until they have been executed in the repository environment.
