# Raw-to-Event Model

## Separation of layers

1. **Measurement** — samples, units, sample rate, channels, known sensor bandwidth.
2. **Frame representation** — STFT harmonic distribution, envelope, temporal marks, wavelet detail and phase cues.
3. **Boundary evidence** — persistent between-window changes with within-window variability correction.
4. **Segmentation hypotheses** — sensitive, nominal and conservative candidate parses.
5. **Event descriptors** — pooled feature summaries within each candidate segment.
6. **Opaque event tokens** — observer-specific clusters, not semantic action names.
7. **Operation motifs** — Build 28's recurrent ordered event sequences.
8. **Effect inference** — remains a separate stage requiring checkpoint or intervention evidence.

No stage is allowed to silently skip the preceding stage. A recurring signal token is not itself proof of an operation, and an operation-effect association is not causal proof.

## Harmonic and temporal views

Let `p_b(t)` be normalized energy in harmonic band `b` and `r(t)` a local RMS envelope. A harmonic observer compares spectral shape; a temporal observer compares envelope structure; a combined observer uses both. For gain transformation `x -> a x`, normalized spectral shares and the relative log-RMS descriptor are invariant to a constant positive `a`, while absolute RMS is not.

The amplitude-only fixture demonstrates an observer quotient: under the harmonic view, four amplitude states collapse to one token; under the temporal view, they remain four. Neither quotient is universally correct. Task intention determines whether the distinction matters.

## Event boundaries as hypotheses

For candidate frame `t`, compare feature distributions from windows `L_t` and `R_t`. A raw between-window divergence is not enough; subtract a within-window stability term. This makes the score closer to a change-point contrast than a raw novelty score.

The threshold family is retained rather than reduced to a single segmentation. When sensitive and conservative parses differ, the difference is evidence about observer resolution and uncertainty.

## Connection to the Virtual Ground

A signal-derived event vocabulary is an observer representation. It is not automatically the ground itself. The Virtual Ground is the generative logic that can explain how observed event patterns and state changes arise. Build 29 creates candidate observation units that Build 28 can use to discover recurring motifs; later builds must determine whether those motifs correspond to stable, compositional transformations.
