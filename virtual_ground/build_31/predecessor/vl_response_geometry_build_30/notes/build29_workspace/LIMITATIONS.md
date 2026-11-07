# Build 29 Limitations and Validation Boundaries

- Main corpus and controls are synthetic. No TAPS audio was downloaded or analyzed.
- Signal channels must share sample rate, sample count and alignment for max-pool fusion.
- Frame size and hop are fixed per run; multiresolution frame search is future work.
- Phase-only event boundaries are only partially recovered (4/7 in the fixture).
- The event vocabulary uses greedy nearest-prototype clustering and is order/tolerance dependent.
- The selected nominal parse is a working view, not a uniquely true event ontology.
- Threshold settings are not calibrated p-values or false-discovery guarantees.
- A recurrent signal motif is not evidence of a state-changing operation; effects require independent checkpoints or controlled interventions.
- Different sensor transfer functions may change the representation; calibration and cross-observer metric alignment are future work.
- Continuous raw sensor event detection can be task-dependent. The same waveform can be segmented differently under harmonic, temporal and combined observers.
