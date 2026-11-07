# Build 12 — Empirical cross-modal response geometry

## Why this is next

Build 11 establishes a reproducible path from real sensor observations to response features, with provenance and measurement caveats retained. It contains one real smartphone G-Force recording excerpt only. Build 12 should add real acoustic impulse-response measurements and broaden the vibration sample across recordings, while preserving sensor and room metadata.

## Candidate acoustic sources

### Preferred first candidate: University of Rochester Room Impulse Response Dataset

The current dataset catalogue record describes 14 rooms, with room-specific IRs in 48 kHz, 32-bit mono WAV, plus room layouts and acoustic plots. It is listed as CC BY 4.0. The repository page also asks users to complete a usage form; check the current landing page and terms before access/redistribution. The dataset supports between-room response diversity without requiring a synthetic room generator.

- Dataset page: https://rochester.figshare.com/articles/dataset/University_of_Rochester_room_impulse_response_dataset/26801089
- Dataset catalogue description: https://datasetcatalog.nlm.nih.gov/dataset?q=0002388342
- Associated paper: https://doi.org/10.1121/10.0032367

### Second candidate: Queen Mary / C4DM Room Impulse Response Dataset

The Isophonics page describes real measurements in the Great Hall, Octagon and a classroom using swept-sine excitation, an omnidirectional DPA microphone and a B-format microphone. Its stated license is Creative Commons Attribution-Noncommercial-Share-Alike. The page documents 96 kHz / 32-bit WAV files; the audeering distribution of the omnidirectional subset is documented as 96 kHz / 24-bit. These may be different packaged versions, so inspect the actual selected archive and preserve its metadata rather than assuming one bit depth.

- Source page: https://isophonics.net/content/room-impulse-response-data-set
- Alternate packaged subset description: https://audeering.github.io/datasets/datasets/ir-c4dm.html

### Third candidate: Théâtre Acoustique RIR Library

The library page states that the stereo IR files are 48 kHz / 24-bit WAV and CC BY-NC 4.0. It is available for research and experimentation with attribution; commercial use requires separate permission. This is suitable for a non-commercial study if the current terms are respected.

- Source page: https://www.lieuxperdus.com/convolver/download/

## Proposed experimental design

- Analyze multiple room impulse responses and structural vibration recordings separately first.
- Estimate channel noise floors and impulse-response energy decay; keep microphone/sensor response distinct from the source/room or plant response.
- Extract matched response summaries: decay/persistence, modal peaks, spectral centroid/bandwidth, temporal envelope, cross-channel coherence, modulation and nonlinear indicators where the input level and metadata permit.
- Use calibration or repeated source/microphone configurations when available; otherwise mark unknown transfer paths explicitly.
- Compare RDMs within each domain before any cross-domain alignment.
- Hold out entire rooms, microphones, sensors, and vibration recordings; never split adjacent windows from one file across train/test.
- Include feature-marginal and temporal-shuffle controls, plus random-feature and calibration-only controls.
- Revisit active probe selection only where the archived source contains known excitation or where a controlled re-probe is possible. Do not imply that archived passive recordings constitute live active measurement.

## Key falsification questions

1. Do acoustic and mechanical response neighborhoods align above marginal-preserving null controls when no frequencies or damping ratios are matched by construction?
2. Does alignment survive held-out room and sensor identities?
3. Which response features are stable under gain, unit conversion, bandwidth limitation, and channel mixing?
4. Are apparent shared modes attributable to common acquisition bandwidth or analysis filters?
5. Can a codon-described probe suite predict the most discriminative next measurement without being optimized on the held-out recording?

## Guardrails

- No emotional labels unless a dataset independently includes validated observer ratings.
- No universal claims from a small number of rooms or recordings.
- Do not infer material properties from a microphone recording without a known excitation and calibration model.
- Keep raw data separate from derived features and generated labels.
- Preserve licenses and provenance; the candidate libraries have different CC BY, CC BY-NC, and CC BY-NC-SA conditions.
