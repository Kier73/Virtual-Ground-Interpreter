# Sources and Provenance

## Earlier project artifacts incorporated

- Build 13: WAV decoding, FFT and acoustic/throat-vibration feature methodology. Its TAPS recordings were not available in the current runtime.
- Build 17: Fourier, STFT, stationary Haar-like detail-energy and Mellin/temporal representation comparisons.
- Build 28: exact event-motif mining and held-out segmentation engine; used directly for Build 29 signal-derived token streams.
- Build 24–27: predictive context discovery, online tracking, partial-ground construction, competing explanations and operation discovery. Preserved through the embedded Build 28 workspace/archive.

## Current Build 29 provenance

All results in `reports/` are generated from deterministic synthetic signal fixtures. Hidden event classes and boundaries are written separately to `synthetic_truth_only.json` for evaluation and are not passed to the learner.

The stereo WAV in `fixtures/` is synthetic and included only to verify raw WAV ingestion.
