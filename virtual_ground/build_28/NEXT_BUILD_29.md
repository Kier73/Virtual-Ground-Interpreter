# Next Investigation — Build 29

## From token streams to observable events

Build 28 begins with opaque event tokens. The next step should investigate whether the interpreter can produce those tokens from continuous multichannel measurements.

Candidate work:

1. Convert raw sampled signals into observer-relative feature trajectories.
2. Detect candidate event boundaries from changes in temporal, spectral, phase and envelope structure.
3. Compare Fourier/STFT/wavelet and event-graph representations under controlled shifts, scaling and drift.
4. Preserve multiple candidate tokenizations when the evidence is ambiguous.
5. Feed candidate token streams into Build 28's motif and operation discovery.
6. Test with synthetic signals first, then a properly licensed paired sensor corpus if data bytes can be obtained.

The central question is whether event tokenization can itself be treated as a learned observer representation rather than a fixed preprocessing step.

Do not infer semantic operation labels or causal effects from signal recurrence alone. Keep tokenization, segmentation, operation-effect inference and causal validation as separate stages.
