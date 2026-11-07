# Build 09 — Cross-modal response geometry

## Why this follows Build 08

Build 08 weakened two Build 07 cross-observer relationships when hand-designed shapes were replaced by independently randomized path families. It also showed that observer robustness and persistence summaries depend on the selected measurement representation.

The next useful test should leave pure geometry and introduce controlled signals that can be measured in more than one way.

## Proposed experiment

Construct a small, controlled library of response-generating systems in two domains:

1. **Acoustic-like signals:** tones, chirps, amplitude modulation, beating, broadband noise, filtered noise, and short event sequences.
2. **Mechanical/material-like responses:** damped oscillators, coupled oscillators, impulse responses, and nonlinear saturating systems.

These are initially synthetic signal generators, not actual human emotional judgments or material touch measurements.

### Shared probes

Apply matched families of probes where mathematically meaningful:

- impulse and step response;
- frequency sweep;
- amplitude scaling;
- time reparameterization;
- additive noise;
- channel dropout;
- controlled nonlinear distortion.

### Candidate representations

- spectral response / transfer function;
- temporal persistence and decay;
- roughness / modulation statistics;
- phase and coherence;
- observer-conditioned response signature;
- codonic description of the generator and probe sequence.

### Main questions

1. Can different generators from different domains share response signatures without sharing the same physical mechanism?
2. Which relations are preserved under unit changes, sampling rates, and observer projections?
3. Does a response-based RDM align across modalities more reliably than a static-feature RDM?
4. Can active observation choose probes that distinguish systems whose initial response profiles overlap?
5. Which candidate similarities are driven by the shared probe design rather than by deeper structure?

## Required controls

- Randomized generator parameters and held-out generator families.
- Independent feature definitions for each domain before alignment.
- Shared-probe and domain-specific-probe conditions.
- Noise, bandwidth, and sampling-rate sweeps.
- Bootstrap over generator families, not pairwise RDM entries.
- Label and generator-parameter permutation controls.
- A no-alignment baseline and a shuffled cross-modal alignment baseline.
- Explicit separation of signal identity, signal response, and observer interpretation.

## Expected output

A cross-modal response-geometry benchmark with reproducible signal generators, codon descriptions, response signatures, RDM comparisons, and clear negative results where shared structure does not generalize.

## Guardrail

Do not label synthetic acoustic or mechanical response as emotional tone. Emotion requires a separate empirical observer study with validated stimuli, consent, and appropriately designed ratings. The first Build 09 experiment should remain a mathematical measurement study.
