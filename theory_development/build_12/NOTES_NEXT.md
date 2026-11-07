# Build 13 — Matched acoustic / structural observation

## What Build 12 establishes

Build 12 supplies a standard-library-only ingestion and analysis pipeline for the 14-room University of Rochester RIR dataset. It separates raw recording level, early/late energy, decay, spectral band distribution and temporal signature. It builds within-acoustic-domain room RDMs after aggregating multiple RIR files per room by median.

The current execution environment could verify Figshare article metadata but could not retrieve its 94.65 MB archive. Therefore no acoustic waveform metrics or room-level RDM results are claimed by Build 12. The package contains a public Figshare API downloader; execute it on a network-enabled machine to produce the first empirical room results.

## Key conceptual correction

Build 11's smartphone G-Force excerpt is a person-in-motion signal. The Rochester collection is room impulse responses. They do not share a controlled excitation or paired trial. A direct cross-domain RDM correlation between the two would be invalid as evidence of cross-modal invariance. Build 12 therefore keeps their domains separate.

A more promising physical bridge exists in the associated Rutowski et al. (2024) work: an elastic panel's structural vibration responds to incident acoustic waves, and the study measured wake-word direction-of-arrival performance across eight reverberant spaces. The abstract reports RT60 from 0.27 to 3.00 s and DOA reliability within ±5° declining from 95.00% in the least reverberant space to 78.33% in the most reverberant space. These published findings are context only; they are not raw paired records in the Figshare archive.

## Build 13 target

Obtain genuinely paired acoustic and structural-vibration recordings under the same excitation, source direction, room and trial. Prefer the panel-microphone experiment's own data if available under suitable terms, or design a controlled acquisition protocol with synchronized microphone and contact/structural sensor channels.

For each paired trial:

1. Preserve raw acoustic and structural channels with shared trial IDs, clocks, calibration, source and location metadata.
2. Estimate channel transfer separately; retain calibrated and uncalibrated views.
3. Extract comparable time-frequency and response features without forcing equal coordinate dimensions.
4. Compare within-domain RDMs, then test cross-domain alignment on paired conditions only.
5. Hold out entire rooms and source directions.
6. Test gain, bandwidth, timing, sensor-placement and noise controls.
7. Use active probe selection only when the excitation can be changed in a documented controlled manner.

## Falsification criteria

- If alignment disappears after calibration or held-out-room testing, classify the earlier match as measurement-chain dependent.
- If cross-domain alignment is not higher than marginal-preserving shuffled-pair controls, do not claim shared geometry.
- If only RT60 or broad spectral slope explains the relation, report the low-dimensional physical correlate rather than a generalized tone invariant.
- If multiple distinct features survive controls, investigate them as a response signature, not automatically as emotion or meaning.

## Future extension

Once paired records exist, test whether codonic response descriptors can predict the next most informative excitation or measurement channel. That is the appropriate point to bring Build 05's active observer back into the empirical pipeline.
