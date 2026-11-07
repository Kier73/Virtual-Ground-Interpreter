# Build 11 sources

## Primary measured dataset

Justyna Witulska, *Vibration measurements with observer-declared variance change points*, version 1.0.0 (2026-09-19), CC BY 4.0.

- Repository and full dataset documentation: https://github.com/witulska/vibration-changepoint-dataset
- Canonical measurement 01 CSV: https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/data/processed/measurement_01.csv
- Observer change-point annotations: https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/documentation/change_points.csv
- Machine-readable metadata: https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/metadata/metadata.json
- License: https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/LICENSE

The repository README states measurement 01 is a person/gait-motion-change recording with G-Force only, 83.74 s, 8,157 rows, and observer-declared interval [66, 68] s (midpoint 67 s). It reports nominal G-Force range ±4 g and acquisition up to 100 Hz. It cautions that interleaved multi-sensor recordings can contain duplicate timestamps. The dataset's own metadata says its version-specific DOI is to be minted by Zenodo on a GitHub release; therefore no version-specific DOI is asserted in this build.

## Related method paper

Witulska, J. & Wyłomańska, A. (2022). Identification of the structure break point for data with changing variance. *Mathematica Applicanda*, 50(1), 65–106. https://doi.org/10.14708/ma.v50i1.7155

## Candidate acoustic datasets for Build 12 (not ingested in Build 11)

### University of Rochester Room Impulse Response Dataset

The NLM dataset catalogue record describes a collection of impulse responses recorded in 14 rooms, in 48 kHz / 32-bit mono WAV, and lists CC BY 4.0. It also points to the Figshare dataset and associated JASA paper. Confirm the current Figshare landing page, download instructions and terms before copying any data into the project.

- Figshare: https://rochester.figshare.com/articles/dataset/University_of_Rochester_room_impulse_response_dataset/26801089
- Catalogue record: https://datasetcatalog.nlm.nih.gov/dataset?q=0002388342
- Associated paper: https://doi.org/10.1121/10.0032367

### Queen Mary / C4DM Room Impulse Response Dataset

The Isophonics page describes measured responses in three spaces using sine-sweep excitation; it states CC BY-NC-SA terms and 96 kHz / 32-bit WAV. The audeering distribution documents a 96 kHz / 24-bit omnidirectional subset. Verify the selected archive and exact terms before use.

- Isophonics: https://isophonics.net/content/room-impulse-response-data-set
- audeering subset: https://audeering.github.io/datasets/datasets/ir-c4dm.html

### Théâtre Acoustique Room Impulse Response Library

The source page states stereo 48 kHz / 24-bit WAV and CC BY-NC 4.0. It permits research/experimentation with attribution and requires separate contact for commercial use.

- https://www.lieuxperdus.com/convolver/download/

No acoustic room-impulse waveform was downloaded or included in Build 11.
