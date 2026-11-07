# Build 11 — Empirical vibration response geometry

**Status:** pilot complete  
**Data mode:** real measured sensor excerpt, not synthetic  
**Runtime:** Python standard library only

## 1. Purpose

Build 11 moves the response-geometry programme from entirely synthetic systems to an empirical sensor record. The immediate objective is modest: characterize how a real three-axis motion-sensor stream changes around a source-declared variance-change interval, while keeping acquisition metadata, measurement behaviour, observer features, and interpretation separate.

This is not an emotional-response study. The source annotation marks a change in vibration variance; it supplies no emotion labels, voice recordings, acoustic room responses, or calibrated reference excitation.

## 2. Source and provenance

The pilot uses measurement 01 from Justyna Witulska's *Vibration measurements with observer-declared variance change points*, version 1.0.0, dated 2026-09-19, CC BY 4.0. The repository documents nine smartphone motion-sensor recordings from person, motorbike, and car contexts. Measurement 01 is a person/gait-motion-change recording containing a single three-axis G-Force channel, with 8,157 processed rows and a documented duration of 83.74 s. The observer-declared interval is 66–68 s, with midpoint 67 s.

Source: <https://github.com/witulska/vibration-changepoint-dataset>.  
Annotation table: <https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/documentation/change_points.csv>.  
Machine-readable metadata: <https://raw.githubusercontent.com/witulska/vibration-changepoint-dataset/main/metadata/metadata.json>.

The repository documents a nominal G-Force Meter range of ±4 g and a nominal maximum of 100 Hz. It defines `time_s` as elapsed seconds from recording start. The repository warns that interleaved multi-sensor files may contain duplicate timestamps; this pilot chooses measurement 01, which is G-Force only. The dataset README identifies a version-specific DOI as pending Zenodo deposition; no DOI is asserted by this package.

Related publication: Witulska, J. & Wyłomańska, A. (2022), “Identification of the structure break point for data with changing variance,” *Mathematica Applicanda*, 50(1), 65–106. https://doi.org/10.14708/ma.v50i1.7155.

## 3. Exact scope of the analyzed data

The included excerpt contains **411 rows in eight source-contiguous windows**. Each row retains its source CSV line number. The selected source-line ranges are recorded in `source_data/source_manifest.json`.

The full 8,157-row recording was **not fetched or analyzed in this execution environment**. The package therefore reports excerpt-level results only. A downloader and full-recording analysis utility are included for network-enabled reproduction.

Time gaps between excerpt windows are not interpolated. One excerpt window also contains a large internal timestamp gap; the feature report retains its maximum observed interval rather than hiding it. Windows that overlap or straddle the observer annotation are excluded from strict pre/event/post group summaries.

## 4. Feature extraction

For each window, the engine calculates:

- sample count, start/end/duration, median timestamp interval, interval MAD and maximum gap;
- per-axis mean and standard deviation;
- median-centred vector RMS, SD, and 95th percentile;
- raw mean vector magnitude;
- eigenvalues and normalized fractions of the three-axis covariance matrix;
- cross-axis correlations;
- difference-per-sample RMS and time-normalized derivative RMS;
- lag-1/lag-2 magnitude autocorrelation, zero-crossing rate and magnitude kurtosis;
- fraction of axis samples with absolute value at least 3.98 g, labelled possible range-limit proximity.

Four response views are generated: amplitude, direction/covariance, temporal, and sensor/timestamp. Each view is robustly standardized across the eight windows before Euclidean pairwise distances are calculated. Spearman correlations between upper-triangle RDM entries are descriptive only.

## 5. Results from the included excerpt

### 5.1 Window-level changes

The two strict pre-interval windows have median-centred vector RMS values of approximately 0.4985 g and 0.5201 g. The two windows wholly inside the 66–68 s observer interval have values of approximately 0.6135 g and 0.9038 g. The two strict post-interval windows have values of approximately 1.7389 g and 1.5147 g.

The time-derivative RMS also increases across these selected windows: approximately 10.88–12.41 g/s before the interval, 18.13–35.95 g/s within it, and 54.42–61.61 g/s in the selected post windows.

These are descriptive contrasts from two windows per group, not inferential estimates. The observer interval is a variance-change annotation, not an independently measured ground-truth mechanism or emotional category.

### 5.2 Cross-view response geometry

For the eight selected windows, the current RDM-view Spearman correlations are:

| Views | Spearman RDM correlation |
|---|---:|
| Amplitude / Direction | 0.230 |
| Amplitude / Temporal | 0.386 |
| Amplitude / Sensor | -0.090 |
| Direction / Temporal | 0.556 |
| Direction / Sensor | -0.173 |
| Temporal / Sensor | -0.285 |

These numbers describe this particular excerpt and feature selection. The small number of windows and their shared origin within one recording mean they should not be interpreted as stable population-level relationships.

### 5.3 Possible sensor-limit proximity

Three selected windows contain one or more axis samples at or above 3.98 g in absolute value. This is a conservative warning near the documented ±4 g nominal range. It is not proof of ADC clipping or hard saturation; those would require raw acquisition characteristics and calibration evidence.

### 5.4 Unit scaling

The RDM check after converting g-scaled feature magnitudes by standard gravity (9.80665 m/s² per g) has a maximum distance discrepancy of approximately 8.9e-16 in the tested standardized representation. This checks a common multiplicative unit conversion in this pipeline; it does not calibrate the phone sensor.

## 6. Codonic layer

A small local arithmetic subset is included to keep operation nomenclature separate from the operations themselves. Aliases `ad`/`plus`, `mx`/`times`, and related arithmetic forms resolve to the same local operation implementation. This pilot uses the codonic layer for arithmetic identity and does not claim that the accelerometer itself executes codons or that the recorded signal is a native Virtual Layer state.

## 7. What this build does not establish

1. It does not establish a universal tone metric.
2. It does not compare measured acoustic and mechanical systems; this build contains only one real G-Force recording excerpt.
3. It does not identify the sensor transfer function; there is no calibrated reference input.
4. It does not prove that near-4g values are clipped.
5. It does not infer emotion, intention, or a biological interpretation from the variance-change annotation.
6. It does not establish cross-recording invariants from eight windows of one recording.
7. It does not analyze an empirical room impulse response.

## 8. Next experiment

Build 12 should add a real acoustic measurement, preferably room impulse responses with documented sample rate, bit depth, channel geometry, excitation, room metadata, and license. It should also expand the vibration side to additional recordings and require calibration/channel documentation before combining signals. A cross-modal result should be held out by recording, room, and sensor configuration rather than by randomly splitting windows from the same file.

## 9. Reproduction

```bash
python build_11.py --out .
python -m unittest discover -s tests -v
python scripts/fetch_full_recording.py --out downloaded_source
python scripts/analyze_full_recording.py downloaded_source/measurement_01.csv --out full_run --window 1.0
```

The first two commands run offline against the included excerpt. The latter two require network access.
