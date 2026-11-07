# Virtual Layer — Build 11: Empirical response geometry

A standard-library-only pilot that analyzes a traceable excerpt from a real smartphone G-Force recording. It keeps source observations, measured sensor properties, derived features, observer views, and interpretation separate.

## What is included

- `source_data/measurement_01_excerpt.csv`: 411 source rows over eight separately identified windows, with original source-line numbers.
- `source_data/source_manifest.json`: dataset attribution, version, license, annotation, source URLs, excerpt ranges, and retrieval status.
- `build_11.py`: per-window feature extraction, response-distance matrices, cross-view comparisons, descriptive pre/event/post contrasts, and unit-scaling check.
- `wav_tools.py`: a small PCM WAV reader and rough Schroeder-decay RT60 diagnostic for later room-IR work. No empirical room-IR waveform is included or analyzed in Build 11.
- `scripts/fetch_full_recording.py`: fetches the complete public source files on a network-enabled machine and checks version/header/row count.
- `scripts/analyze_full_recording.py`: turns the downloaded single-sensor CSV into contiguous fixed-duration analysis windows without interpolation, then runs the same feature pipeline.
- `tests/`: reproducibility, data-integrity, codon alias, RDM, unit-scaling, and WAV parser tests.

## Run the included excerpt (offline)

From this directory:

```bash
python build_11.py --out .
python -m unittest discover -s tests -v
```

No third-party Python packages are needed.

## Fetch and analyze the complete recording (network required)

```bash
python scripts/fetch_full_recording.py --out downloaded_source
python scripts/analyze_full_recording.py downloaded_source/measurement_01.csv --out full_run --window 1.0
```

The downloader expects dataset version 1.0.0, a four-column single-sensor file, and 8,157 data rows. If the upstream version changes, inspect its metadata before using `--allow-row-count-change`.

The full-recording runner uses 1-second non-overlapping windows by default. It does not interpolate or silently bridge time gaps. It preserves source row numbers. Short terminal windows with fewer than eight samples are not included in feature extraction.

## Interpretation safeguards

- The processed channel is a smartphone G-Force Meter output in `g`; it is not a calibrated reference accelerometer or force measurement.
- Nominal range is ±4 g. Values at or above 3.98 g are flagged as possible range-limit proximity, not proven clipping.
- The source-declared interval `[66, 68] s` is a variance-change interval, with theoretical midpoint `67 s`; it is not an emotional label.
- The current excerpt has only eight windows from one recording. RDM correlations are descriptive and not independent-sample inference.
- `1 / median(Δt)` is labelled an observed interval-rate diagnostic, not a certified sample rate. Source documentation gives a nominal per-sensor maximum of 100 Hz and warns about duplicate timestamps in interleaved multi-sensor recordings.
- The full recording was not fetched during this build because network retrieval was unavailable in this environment. Do not describe the excerpt results as full-recording analysis.
- No empirical acoustic room-impulse waveform was ingested. The WAV module is only an adapter for a later build.

## Attribution

Dataset: Justyna Witulska, *Vibration measurements with observer-declared variance change points*, version 1.0.0 (2026-09-19), CC BY 4.0. Repository: <https://github.com/witulska/vibration-changepoint-dataset>.

Related article: Witulska, J. & Wyłomańska, A. (2022), “Identification of the structure break point for data with changing variance,” *Mathematica Applicanda*, 50(1), 65–106. https://doi.org/10.14708/ma.v50i1.7155.

The dataset documentation states that a version-specific Zenodo DOI is to be assigned when a GitHub release is deposited. This package does not invent or assert such a DOI.
