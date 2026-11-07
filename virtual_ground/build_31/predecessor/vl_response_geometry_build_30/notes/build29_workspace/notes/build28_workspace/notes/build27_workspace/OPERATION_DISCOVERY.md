# Operation Discovery from Opaque Event Signatures

## Input contract

The observation interface provides a sequence of windows. Each window has a before vector, an ordered list of low-level event tokens observed during the interval, and an after vector. The token strings are uninterpreted symbols. They are not semantic operation names.

The window boundary is still supplied by the acquisition interface. Raw waveform segmentation is an explicit future task.

## Discovery

For each recurring exact event signature, compare observed vector deltas:

\[
\Delta x=x_{after}-x_{before}
\]

The effect is classified as:

- constant vector delta, only when the same delta is seen at two or more distinct pre-states;
- pre-state-conditioned table, when each pre-state has a consistent effect but effects differ across pre-states;
- single-prestate table, when support comes from only one pre-state;
- ambiguous, when the same signature at the same pre-state produces conflicting deltas.

The compiler will not infer a global law from one repeated observation at one pre-state.

## Why exact signatures first?

This version prefers precision over coverage. Arbitrary subsequence mining risks associating an event fragment with an effect caused by a larger event sequence. Exact observation-window signatures are a conservative baseline. The next build can add motif mining with negative controls and causal/interventional tests.

## Causal boundary

A recurring signature with a reproducible effect is an operation candidate, not proof that the token sequence caused the effect. A controlled repeat, independent contexts, event ablation or intervention is needed to strengthen causal interpretation.
