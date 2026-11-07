# Limitations and Evidence Boundaries — Build 27

- Results are synthetic and deterministic except where a diagnostic fixture explicitly considers stochastic alternatives.
- Observation-window boundaries are supplied.
- Event tokens are opaque, but tokenization itself is supplied.
- The operation miner groups exact repeated token sequences; it does not yet discover arbitrary subsequences or semantic operation names.
- A constant-delta law is inferred only after repeated support across at least two distinct pre-states, but finite evidence cannot prove it globally.
- State-conditioned transitions only predict observed pre-states.
- The diagnostic layer uses explicit evidence fields and ordinal heuristic scores, not probabilistic inference.
- A hidden deterministic variable may be indistinguishable from stochasticity under limited observations.
- A sensor remapping may be indistinguishable from a physical change without calibration references.
- Ground regime changes are proposals, not automatic commits.
- No empirical TAPS, acoustic, vibration or other real-world sensor recordings are included in this build.
