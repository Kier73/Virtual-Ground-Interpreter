# Virtual Ground Compiler

## Input

A learned deterministic predictive Mealy machine:

\[
M=(Q,A,Y,\delta,\lambda,q_0)
\]

where `Q` is the learned predictive context set, `A` the supplied action alphabet, `Y` the observer's output alphabet, `δ` the successor map, `λ` the output map and `q0` the initial predictive context.

## Compilation decision

The compiler checks whether a selected action (in Build 24, `HOLD`) induces one cycle through every predictive state. It then checks whether every other action has a constant stride in that cycle coordinate.

If true:

\[
z'=(z+\Delta(a))\bmod n
\]

and the output is read from a phase/action table. This is emitted as `modular_phase_program`.

If either condition fails, the compiler emits `finite_predictive_automaton` and preserves the full transition/output maps.

## Verification

For a modular phase program, every phase/action pair is compared with the corresponding learned machine transition and output. For a general automaton, every state/action pair is checked directly. Build 24 includes round-trip serialization and exact compiler-execution comparisons.

## Important distinction

A one-state predictive quotient is not evidence of a physical one-state system. The compiler represents no observable latent progression under the current observer. The hidden system may contain more physical states whose future outputs are identical under all available actions.

## Ground version metadata

A compiled specification should carry the observer profile, action alphabet, output channel schema, reset contract, training evidence, distinguishing suffixes, bounded conformance depth, unresolved ambiguities and a stable fingerprint. Changing the observer may change the predictive quotient without changing the physical ground.
