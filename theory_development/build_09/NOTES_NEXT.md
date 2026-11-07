# Build 10 — Breaking the matched-model assumption

## Why this follows Build 09

Build 09 shows that an acoustic-like digital resonator and a mechanical oscillator produce highly aligned response geometry when their natural frequencies and damping ratios are matched by design. That is a useful positive control, but it risks making the conclusion true by construction.

Build 10 should make the systems less alike and test how much of the response geometry survives.

## Proposed experiments

### 1. Heterogeneous systems

Add families that do not share one pole pair:
- two- and three-mode acoustic resonators;
- coupled two-degree-of-freedom mechanical oscillators;
- non-proportional damping;
- anti-resonances and mode coupling;
- frequency-dependent gains;
- weak and strong nonlinearities.

### 2. Probe selection

Integrate the active observer from Build 05:
- choose impulse, step, chirp, multisine, or amplitude probes;
- estimate uncertainty about mode count, damping, and nonlinear response;
- select the next probe by expected information gain per cost;
- compare active, fixed, and random probe policies.

### 3. Nuisance transformations

Test:
- unit and gain rescaling;
- sampling-rate changes;
- sensor transfer functions;
- missing channels;
- time delays and bandwidth limits;
- noise distributions beyond Gaussian.

### 4. Cross-domain alignment controls

- independent parameter draws rather than paired poles;
- shuffled system identities;
- deliberately mismatched mode count;
- same system under different sensor transfer functions;
- train/test split by generator family, not by individual waveform.

### 5. Empirical bridge

After synthetic controls are reliable, consider openly licensed laboratory impulse-response or modal-analysis data. Record source, units, sensor configuration, sampling rate, and licensing. Keep physical measurements separate from synthetic examples.

## Primary question

Does an observer-independent relational structure remain when the systems no longer share a deliberately matched mathematical form, or does the apparent cross-domain geometry collapse to the common components we explicitly built into them?

## Guardrail

No synthetic response should be described as emotional tone. Human affect requires independent, validated observer research; measured acoustic or mechanical features are only candidate predictors or correlates.
