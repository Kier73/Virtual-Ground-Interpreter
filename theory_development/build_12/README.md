# Virtual Layer — Build 12

**Empirical room-impulse-response geometry**

This package analyzes measured room impulse responses from the University of Rochester Room Impulse Response Dataset (Figshare article 26801089, version 3; DOI 10.60593/ur.d.26801089.v3; CC BY 4.0). The dataset landing page describes 14 rooms and 48 kHz, 32-bit, mono WAV recordings.

## Important execution status

The current assistant execution environment could verify the Figshare landing page and dataset metadata, but could not retrieve the 94.65 MB binary archive. Consequently, **no Rochester WAV waveform has been analyzed in the packaged results**. The included WAV fixtures exist only inside unit tests. They are synthetic and are never described as empirical room measurements.

## Requirements

- Python 3.10+
- Standard library only
- Network access only for `scripts/fetch_rochester_figshare.py`

## Retrieve and unpack the source dataset

```bash
python scripts/fetch_rochester_figshare.py --out data/rochester
python scripts/unpack_dataset.py data/rochester/rochester_rir_v3.zip --out data/rochester/extracted
```

The downloader requests the public Figshare API metadata for article 26801089, version 3, then streams the versioned archive. It writes `figshare_metadata.json` and `download_manifest.json` with byte count and SHA-256. Default maximum download size is 200 MB; raise `--max-mb` only after checking the source metadata.

## Analyze

```bash
python build_12.py --rir-root data/rochester/extracted --outdir outputs
```

Outputs include per-file features, room-level median aggregates, separate representational dissimilarity matrices (RDMs) for decay, early/late balance, spectrum, temporal character and absolute level, and cross-view RDM correlations.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Interpretation rules

- Absolute level is kept separate because it depends on the source, microphone, preamplifier and acquisition gain.
- Decay metrics are regressions/extrapolations over the recorded decay range. They are not guaranteed direct 60 dB observations.
- The octave filters are compact second-order analysis filters, not a certified ISO 3382 implementation.
- Room-level values aggregate files with a median; file-level data remain available for audit.
- **No cross-modal RDM correlation is calculated against Build 11's smartphone motion excerpt.** Those observations are not paired by common excitation, room, device or trial, so their distance matrices cannot be meaningfully correlated as if they described matched systems.
- The associated Rutowski et al. paper reports a separate experiment relating elastic-panel vibration to acoustic direction of arrival in eight spaces. Those results are cited as literature context, not imported into this dataset's raw measurement table.

## Provenance

See `SOURCES.md`, `LICENSES.md`, and `source_data/vibration_source_manifest.json`. Keep raw downloaded files separate from derived output. The Rochester dataset is CC BY 4.0; retain attribution and the dataset DOI when redistributing derived work.
