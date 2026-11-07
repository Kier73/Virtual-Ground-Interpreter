# Build 14 — Cross-domain test of paired response geometry

## What Build 13 establishes

Build 13 provides a standard-library engine for paired acoustic-microphone and accelerometer-based throat-microphone records. It analyzes the TAPS held-out test split speaker-by-speaker, compares within-speaker acoustic and throat RDMs, estimates residual timing, and uses within-speaker shuffled-pair controls. It suppresses transcripts, demographic fields and raw speaker IDs in outputs.

The TAPS audio archive was not downloaded in this environment. Build 13's empirical status is pending local retrieval; only synthetic fixtures were processed for tests.

## Next experiments

1. Run the TAPS test split (10 unseen speakers, 1,000 utterances) and record real RDM/view correlations and residual timing distributions.
2. Compare the common-band response geometry (80-3500 Hz) with the acoustic-only high-frequency band as a separate observation, not as a common feature.
3. Evaluate whether within-speaker RDM agreement persists under feature dropout, small gain changes, common-band limits and alternate normalization choices.
4. Compare global-shift, residual per-utterance alignment diagnostics and no-extra-shift analyses without silently rewriting source samples.
5. Use an independent microphone/accelerometer mechanical plate dataset as a second paired sensor domain, keeping it separate from TAPS. Test whether only generic response descriptors transfer, or whether any deeper relational structure remains after nuisance controls.

## Falsification / guardrails

- If paired RDM alignment does not exceed within-speaker shuffled-pair nulls, do not claim shared relational geometry.
- If alignment only appears after high-dimensional normalization but not in raw/common-band feature views, report the normalization dependency.
- If microphone high-frequency energy has no throat counterpart, treat this as missing/attenuated information, not proof that the sensors occupy the same signal space.
- No emotion interpretation is permitted without an appropriate emotion-annotated dataset and a separate validation design.

## Longer direction

A later build may add active probe selection only where an acquisition can vary the actual stimulus in a documented way. The fixed TAPS recordings support post-hoc observation selection, not adaptive physical excitation.
