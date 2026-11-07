# Next research checkpoint after Build 14

## Current state

Build 14 separates temporal shape from absolute rate. Its time-origin and clock-scale properties are mathematically verified for a fixed event sequence, and its event extraction implementation is covered by synthetic tests. It does not yet show that TAPS recordings preserve this geometry.

The current event landmarks are RMS-envelope local maxima. They are intentionally modest proxies, not ground-truth state transitions.

## Next experiments

1. Retrieve and analyze the TAPS held-out test split; do not substitute synthetic values for empirical results.
2. Compare `temporal_emission` and `temporal_rate` against spectral, ordinary temporal and periodicity RDMs.
3. Repeat with event thresholds and minimum-gap settings varied in a predeclared grid; treat observer sensitivity as a result rather than silently selecting the best setting.
4. Report robustness across robust-MAD, z-score and rank scaling, plus leave-one-feature-out sensitivity.
5. Compare residual timing diagnostics without altering the source recordings.
6. Test a second paired sensor domain separately after calibration.

## Refined conjecture

A structure's temporal relations may be represented by the event/dwell trace observed along its trajectory. The trace has at least two separable parts:

- shape of recurrence/interval relationships;
- absolute tempo and persistence.

A local observer need not share a global clock with other observers. Cross-observer relations could instead be inferred from matched event structure plus explicit calibration of each observer's time base. This is a hypothesis, not yet an implemented distributed-clock protocol.

## Guardrails

- Do not equate envelope peaks with latent state transitions without labels or independent validation.
- Do not infer that time itself is literally radiated by a system.
- Do not infer a universal invariant from one dataset or a synthetic fixture.
- Do not export raw participant IDs, transcripts or raw audio.
- Do not infer emotion, identity or psychological state.
