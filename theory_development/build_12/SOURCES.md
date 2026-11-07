# Build 12 — Sources

## Primary acoustic dataset

Rutowski, Jenna; DiPassio, Tre; Thompson, Benjamin R.; Heilemann, Michael C.; Bocko, Mark F. (2024). **University of Rochester room impulse response dataset** (Version 3). University of Rochester, Figshare. DOI: https://doi.org/10.60593/ur.d.26801089.v3

Landing page: https://rochester.figshare.com/articles/dataset/University_of_Rochester_room_impulse_response_dataset/26801089

The current landing page identifies version 3 (2024-10-17), CC BY 4.0, 14 rooms, 48 kHz, 32-bit mono WAV files, room layouts and acoustic plots. It lists a 94.65 MB “Download all” archive.

## Associated acoustic/structural sensing paper

Rutowski, J., DiPassio, T., Thompson, B. R., Bocko, M. F., & Heilemann, M. C. (2024). Estimating direction of arrival in reverberant environments for wake-word detection using a single structural vibration sensor. *Journal of the Acoustical Society of America*, 156(4), 2619–2629. https://doi.org/10.1121/10.0032367

PubMed abstract: https://pubmed.ncbi.nlm.nih.gov/39417654/

The abstract reports that elastic-panel vibration depends on incident acoustic direction relative to panel bending modes. It reports wake-word DOA recordings in eight spaces with RT60 from 0.27 to 3.00 s, and ±5° DOA reliability of 95.00% in the least reverberant space versus 78.33% in the most reverberant space. These are findings from the paper's experiment, not measurements computed by Build 12.

## Room-acoustic measurement methods

Kuttruff et al. / tutorial reference: **Assessing the Acoustic Characteristics of Rooms: A Tutorial with Examples**. https://pmc.ncbi.nlm.nih.gov/articles/PMC6375510/

The source explains RT60, EDT, clarity, and T20/T30 as decay-time estimates from portions of the energy-decay curve; it notes that T20 extrapolates a measured 20 dB interval to 60 dB and requires suitable signal-to-noise conditions.

## Prior mechanical-sensor baseline

Witulska, J. & Wyłomańska, A. (2022). Identification of the structure break point for data with changing variance. *Mathematica Applicanda*, 50(1), 65–106. https://doi.org/10.14708/ma.v50i1.7155

Dataset: Witulska, J. (2026). Vibration measurements with observer-declared variance change points, Version 1.0.0. Repository: https://github.com/witulska/vibration-changepoint-dataset. Repository version-specific DOI status must be checked before formal citation; the copied manifest records no asserted dataset DOI.

## API / retrieval

Figshare API v2 documentation: https://docs.figshare.com/v2/

Public article details and download endpoints are used by `scripts/fetch_rochester_figshare.py`.
