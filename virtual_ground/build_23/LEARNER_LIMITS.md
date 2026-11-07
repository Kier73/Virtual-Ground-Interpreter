# Learner Limits and Evidence Conditions

## Declared by the interface

- The state has fields `a`, `b` and `phase`.
- The three action labels are known.
- Values are nonnegative integers.
- A/B transfers are symmetric and share the learned quantum rule.
- Environmental inflow affects A; demand affects B.
- The environmental phase is observed.
- Update order is transfer, inflow, spill, demand, phase advance.

These are inductive biases. They make the synthesis tractable, but they are not inferred from arbitrary raw observations in Build 23.

## Identified from records when evidence exists

- State-domain capacity (exact only with positive-inflow saturation evidence).
- Phase count/coverage and deterministic phase successor mapping.
- Inflow and demand values by phase.
- Transfer quantum by phase and source-level residue.
- Exact transition program over the finite domain.

## Not identified without additional probes

- Transfer law when A_TO_B operations are absent or always resource-censored.
- True capacity when no boundary saturation is observed.
- Missing phase schedule entries when a phase is never visited.
- Hidden variables absent from the state/observation schema.
- Asymmetric action logic under a symmetric-actuator grammar.
- Stochastic laws from a deterministic exact-fit model.

## Evidence discipline

The learner rejects missing or inconsistent coverage rather than selecting arbitrary values. A program that fits training data is not considered adequate until held-out transitions have been predicted. Exact finite-domain coverage in this package is evaluated against a hidden synthetic generator used only as a test oracle.
