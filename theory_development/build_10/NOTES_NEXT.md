# Build 11 — Empirical response geometry and sensor calibration

## Why this follows Build 10

Build 10 showed that the near-perfect Build 09 cross-domain alignment depended on deliberately matched second-order dynamics. With independent mode counts, coupled mechanical states, non-proportional damping, anti-resonance-like readouts, and nonlinear responses, the unpaired geometry summaries were not more similar than the feature-shuffled control.

Build 10 also showed that sensor bandwidth and sample rate can alter measured geometry. The next build should distinguish:

\[
\text{plant response} \quad\text{from}\quad \text{sensor transfer} \quad\text{from}\quad \text{observer features}
\]

## Proposed empirical datasets

### A. Structural dynamics — ETH Zurich / Politecnico di Milano

**Experimental Campaign for Dynamic Characterization of a Laboratory-Scale Structure** (Zenodo DOI `10.5281/zenodo.15516419`). The record describes a four-story shear-type laboratory structure, impact-hammer modal tests sampled at 100 Hz, and random shaker tests with accelerometer and optical-displacement channels at 500 Hz and 200 Hz. It includes baseline and bolt-loosened states, 32 impact tests, sensor metadata, and an overview guide. The published archive is approximately 497 MB.

- Dataset record: https://zenodo.org/records/15516419
- ETH research group announcement: https://chatzi.ibk.ethz.ch/smm-news/2025/07/new-open-access-dataset-on-lab-scale-structural-dynamics.html
- **Rights check:** the Zenodo landing page exposes an open dataset record, but the licence field is not clearly populated in the retrieved metadata. Inspect the accompanying data guide and record terms before redistributing or using the files beyond permitted research use.

### B. Acoustic response — Théâtre Acoustique Room Impulse Response Library

The library provides stereo room impulse responses at 48 kHz / 24-bit and states a Creative Commons Attribution-NonCommercial 4.0 International licence.

- Library and download page: https://www.lieuxperdus.com/convolver/download/
- Research and experimentation are permitted under its stated terms with attribution; commercial use requires separate permission. Verify each file's provenance and retain the required attribution.

### C. Optional nonlinear structural benchmark

**TRChallenge — experimental results 2022** (DaRUS DOI `10.18419/DARUS-4484`) is explicitly marked CC BY 4.0. It contains linear modal data and nonlinear phase-resonance, response-controlled, and excitation-controlled tests using 17 vibrometer positions. However, the four configuration archives total tens of gigabytes, so this is an optional later extension rather than the first ingestion target.

- Dataset: https://darus.uni-stuttgart.de/dataset.xhtml?persistentId=doi:10.18419/DARUS-4484

## Build 11 experiments

1. Import a carefully selected subset of actual structural impact and random-excitation measurements.
2. Import a small, attributed set of real room impulse responses.
3. Preserve raw signals and metadata; do not normalize away physical units before recording them.
4. Estimate sensor response separately where calibration data or channel metadata permit it.
5. Compare response signatures across sample rates, sensor layouts, and preprocessing settings.
6. Use active observation only among probes/channels actually present or permitted by the experimental setup.
7. Hold out an entire structure configuration or room/site for evaluation.
8. Compare RDMs only for genuinely paired or repeated measurements. For independent datasets, use unpaired geometry summaries and clearly stated null controls.

## Acceptance criteria

- Every imported signal has source, licence, sample rate, units, channel/sensor metadata, and preprocessing provenance.
- Repeated measurements from the same plant are not split across training and test in a way that leaks plant identity.
- Sensor transfer and plant dynamics are not silently conflated.
- Synthetic and experimental results remain separately labelled.
- The experiment reports failures and null results, not only positive alignments.

## Main question

Do any response relationships observed in Build 10 survive when the response is measured from actual physical systems, with real sensor configurations, noise, and calibration uncertainty?
