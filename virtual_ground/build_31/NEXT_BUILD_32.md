# Next — Build 32: Signal-State Machine and Conditional Transitions

Build 31 establishes finite compositional signal arithmetic and observer-coordinate interchange. The next prudent step is to test whether these transitions can form an explicit state machine.

## Proposed objectives

1. **Persistent signal state:** retain a phase-coded state across multiple instructions, with declared update and reset semantics.
2. **Control selection:** carry operation selection in a distinct control stream and dispatch only after validating its instruction framing.
3. **Conditional transitions:** define a small predicate over observed signal state and select one of two successor operations.
4. **Branch provenance:** retain the predicate result or branch token when an inverse path is required; do not assume a many-to-one branch is reversible.
5. **Observer switching:** permit state to move between compatible observer coordinates during a program.
6. **Execution trace:** record each transition's input-state digest, observer coordinate, opcode, calibration summary, output-state digest and verification result.
7. **Composition proof:** define reusable transition contracts and verify a complete program by composing those contracts.

## Minimum acceptance criteria

- A deterministic finite instruction sequence executes with all intermediate payloads remaining signal states.
- A two-way conditional selects the correct branch from a signal-domain predicate.
- Repeated state updates agree with an independent symbolic oracle.
- Where branch history is retained, the reversible subset recovers the previous state.
- Corrupted or incomplete control frames are rejected rather than silently dispatched.
- Noise, calibration drift, execution cost and failure modes are measured against a conventional state-machine baseline.

The goal is a small, inspectable programmable signal-state machine. It is not yet a universal machine, and it should not be called one unless computational completeness is established separately.
