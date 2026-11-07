# Learner Limits and Required Assumptions

## Supplied by the interface

- The finite action alphabet `HOLD`, `PROBE_A`, `PROBE_B`.
- The selected observation channel(s).
- Deterministic outputs and a reproducible reset to the same hidden initial context.
- A bounded finite-state teacher for these experiments.
- A finite probe-cost model for active selection.

These are deliberate experimental conditions, not claims that an arbitrary live system provides them.

## Inferred from observed input/output behaviour

- The minimal predictive context partition supported by the observation table.
- Distinguishing suffixes for histories that previously appeared equivalent.
- Whether a selected action induces a cycle over learned contexts.
- Constant action strides, if the cycle representation fits.
- Otherwise, a finite predictive transition/output automaton.

## Not inferred

- The actual number or meaning of physical hidden states when states are observationally equivalent.
- An unknown action alphabet or raw sensor segmentation.
- Continuous latent variables, stochastic transitions or nonstationary rules.
- The true state of a system without a reliable reset/access protocol.
- Universal equivalence beyond the conformance horizon.

## Evidence rules

A model that passes depth `d` is only bounded-equivalent through depth `d`. The delayed-six test demonstrates why this qualification matters: a one-state model passes through depth five and fails at depth six.

The learned quotient describes what this observer can predict. It should not be reinterpreted as the ontology of the underlying system.
