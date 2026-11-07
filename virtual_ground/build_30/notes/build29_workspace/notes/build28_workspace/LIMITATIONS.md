# Build 28 Limitations

- Tokenization is assumed; raw waveform segmentation is not performed.
- Exact contiguous n-grams only; no edit-tolerant or arbitrary grammar induction.
- Start/end of each trace supplied.
- Finite synthetic token vocabulary and integer state observations.
- Additive effects inferred from sparse checkpoints; nonlinear interaction discovery is not included.
- Checkpoint intervals crossing motif boundaries are discarded.
- Motif recurrence does not prove causality.
- The finite permutation screen is a heuristic negative control, not a general probability calibration.
- Perfect synthetic segmentation does not imply perfect segmentation on natural streams.
- No real TAPS or physical sensor data processed.
