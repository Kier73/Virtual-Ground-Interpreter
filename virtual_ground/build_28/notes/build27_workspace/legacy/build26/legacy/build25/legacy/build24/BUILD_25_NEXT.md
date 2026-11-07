# Proposed Build 25 — Non-Resettable Online Ground Discovery

Build 24's strongest remaining assumption is reproducible reset to a known initial hidden context. A physical distributed system, sensor stream, software service or ongoing process may not be resettable.

Build 25 should therefore move from membership queries that start at reset to online inference over a continuing trace.

## Proposed capabilities

1. **Unknown initial context:** begin with a belief set over all predictive contexts compatible with current observations.
2. **Streaming updates:** process one input/output event at a time without replaying the complete history.
3. **Belief-state refinement:** narrow or expand possible contexts as new observations arrive.
4. **Active probe scheduling:** choose a probe only when the current belief is insufficient for the intention, and include its execution risk and side effects in the cost.
5. **Local clocks:** preserve per-source timestamps and infer correspondence without assuming one shared wall clock.
6. **Version/change detection:** distinguish an unexpected output, a previously unrepresented context, and a persistent change in the transition law.

## Central model

For a learned predictive machine with state set `Q`, an online observer maintains:

\[
B_t\subseteq Q
\]

After action `a_t` and observed output `y_t`:

\[
B_{t+1}=\{\delta(q,a_t):q\in B_t\land\lambda(q,a_t)=y_t\}
\]

If `B_{t+1}` is empty, the current ground contradicts the observation under the model's deterministic semantics. The system should preserve the counterexample and consider model revision; it must not silently reset its belief.

## Important boundary

Without reset access, the learner may be unable to distinguish histories whose future behaviour is identical under all available actions. It should represent that ambiguity rather than claim to know the hidden starting mode.

A probe that changes the physical system can also alter the very context being inferred. The belief update must therefore include the transition caused by the probe, not treat observation as passive.

## Suggested tests

- Start at an unknown mode and track a set-valued belief.
- Recover a phase coordinate only after enough temporal observations.
- Compare passive stream updates with safe active probes.
- Introduce a persistent transition-law change and verify ground-version proposal.
- Add local timestamp offsets/drift while preserving event ordering.
- Confirm that unidentifiable latent modes remain merged.

This is the next step toward using the interpreter on continuous distributed computation and sensor streams rather than only resettable finite fixtures.
