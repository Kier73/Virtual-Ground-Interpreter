# Non-Resettable Streams and Local Clocks

## Non-resettable operation

The learner begins at an unknown point in the predictive context machine. There is no request to restart the live system and no hidden initial state is supplied. If the observer cannot distinguish candidate contexts, the ambiguity remains in the belief set.

## Asynchronous observations

An action step has a local sequence identifier. Each sensor event can carry:

- source identifier;
- source-local sequence number;
- source-local timestamp;
- output channel index;
- measured value;
- shared action-step identity, when available.

The step identity is the primary correspondence key in this build. If it is absent, the event is retained as unmatched rather than fused by timestamp coincidence.

## Affine clock calibration

For source `s`, an optional mapping is fitted:

\[
t_{ref}=\alpha_s+\beta_s t_s
\]

At least two paired anchors with distinct source-local timestamps are required to estimate both offset and rate. One anchor only gives an offset under an unverified unit-rate assumption; Build 25 refuses to use that as a calibrated time mapping.

Affine calibration can fail when clocks drift nonlinearly, reset, jump or change rate. In those conditions, retain source-local sequence order and treat cross-source temporal alignment as unresolved.

## What is not claimed

This does not recover a universal physical time coordinate. It preserves local event order, explicit event correspondences and calibrated mappings where paired anchors support them.
