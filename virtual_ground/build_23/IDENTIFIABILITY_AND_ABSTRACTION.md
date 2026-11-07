# Identifiability and Abstraction Audit

## Capacity

The maximum observed level is a lower bound. It becomes an exact capacity estimate only when the data include evidence of saturation: a known positive inflow at the observed upper boundary with the next state remaining at that boundary. Without this evidence, the learner labels capacity `lower_bound_only`.

## Operation quantum

The transfer quantum is inferred only from controlled A_TO_B interventions that are uncensored by source amount, destination headroom or unmet demand. If those probes are absent, the learner rejects the data as insufficient.

## Environmental schedule

HOLD transitions are used to separate environmental forcing from operation effects. A phase must have appropriate coverage for inflow, demand and next-phase progression to be inferred.

## Transition congruence

An observer projection is transition-congruent if any two states mapped to the same observation produce the same next observation under the same action. The FULL projection is trivially congruent. LEVELS, TOTAL and TOTAL_PHASE fail this test in the Flow-like fixtures.

A quotient that is not transition-congruent may still be useful for a task predicate. It is not sufficient by itself to serve as a generative transition model. A belief-state controller can retain the hidden alternatives and choose policies robust to them.

## Limits

The phase variable and state fields are explicitly supplied to Build 23. Discovering hidden variables from unlabelled sensor streams, including deciding whether a latent phase exists, is a later task. Similarly, deterministic exact matching is not robust to arbitrary measurement noise.
