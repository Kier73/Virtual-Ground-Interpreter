# Risk-Aware Probing

The scheduler scores an action against the current belief by the entropy of its predicted immediate output partition:

\[
I(a)=H(Y_a\mid B)
\]

It ranks eligible actions by:

\[
\frac{I(a)}{c(a)+\lambda r(a)}
\]

`c(a)` is the declared resource cost, `r(a)` is a declared side-effect risk, and `λ` is the observer's risk penalty. An action over the configured maximum risk is not offered.

The scheduler does not execute a probe. It returns a suggestion and its declared cost/risk evidence. The external controller remains responsible for permission and execution.

This one-step criterion can miss an action whose main value is changing the state into a context that becomes informative later. A stronger planner would compare action sequences, include belief-state safety and account for irreversible transitions.
