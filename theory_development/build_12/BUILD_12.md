# Build 12 — Empirical room-impulse-response geometry

**Status:** Analysis pipeline implemented and tested; Rochester acoustic archive metadata verified; raw acoustic archive not retrieved in this execution environment.

## 1. Dataset verified

The University of Rochester Figshare page identifies version 3 (2024-10-17), DOI `10.60593/ur.d.26801089.v3`, CC BY 4.0, 14 rooms, and 48 kHz / 32-bit / mono WAV impulse responses. It lists room layouts and acoustic plots and a 94.65 MB “Download all” archive.

The archive itself was not downloaded here because the execution container has no external DNS/network route. Accordingly:

- no Rochester WAV file was decoded in this build;
- no empirical RT/EDT, C50/C80, band energy, or room RDM result is asserted;
- synthetic WAVs are used only as unit-test fixtures.

The public Figshare API downloader is provided at `scripts/fetch_rochester_figshare.py`.

## 2. Why room impulse responses

An impulse response is a measured response to a short excitation. It contains a time-varying decay and a frequency-dependent response. The dataset offers a set of 14 real rooms, allowing room-level response neighborhoods to be reconstructed without designing the rooms' simulated dynamics ourselves.

The associated Rutowski et al. paper is especially relevant to the broader direction. It studies structural vibration of an elastic panel under incident acoustic waves and reports wake-word DOA recordings in eight spaces with RT60 values from 0.27 to 3.00 s. Its abstract reports DOA reliability within ±5° of 95.00% in the least reverberant space and 78.33% in the most reverberant space. These are source-reported results, not Build 12 computations.

## 3. Analysis architecture

For every WAV file, the implementation records header metadata and extracts:

- absolute peak, RMS, energy and crest factor (kept as a separate level view);
- onset estimate, peak delay and zero-crossing rate;
- C50, C80, D50 and energy-centroid time Ts;
- broadband EDT, T20 and T30 estimates, decay slope and fit residual;
- six octave-centred analysis-band energy shares (125, 250, 500, 1000, 2000, 4000 Hz, subject to Nyquist checks);
- band-centred T20 estimates, spectral band centroid and log-energy slope.

Room summaries aggregate multiple recordings by median. Separate RDMs are generated for decay, early/late balance, spectral shape, temporal character and absolute level. RDMs are compared only within the acoustic domain.

## 4. Method caveats

1. Source/microphone/preamp gain affects absolute levels. Level features are deliberately not mixed into normalized decay and spectral views.
2. T20/T30 estimate a 60 dB decay time by extrapolating the -5 to -25 dB or -5 to -35 dB energy-decay interval. A valid estimate requires adequate dynamic range and a sufficiently linear decay segment.
3. The compact second-order octave filters in this package are pragmatic analysis filters, not a certified ISO 3382 implementation.
4. RIRs with multiple source/receiver configurations within a room are aggregated by median, while file-level results remain available.
5. The Figshare page documents 32-bit WAVs; the analyzer inspects the actual WAV header and supports PCM 8/16/24/32-bit and IEEE float 32/64-bit encoding.
6. Build 11's smartphone G-Force movement excerpt is not paired with the Rochester RIR trials. No direct cross-modal RDM correlation is calculated. The implementation includes `paired_cross_domain_rdm_correlation`, which requires explicit shared pair IDs and rejects unpaired records.

## 5. Build 11 literature bridge

The strongest direct acoustic/structural connection is not a post-hoc comparison of unrelated data. It is a paired experiment in which incident sound excites a structural panel, and the panel's bending modes shape its measured vibration. Rutowski et al. (2024) report that reverberation can reduce DOA reliability. This supports a future controlled paired-sensor study, but it does not mean the separate Build 11 walking recording is a matched counterpart to room impulse responses.

## 6. Codonic operation descriptions

`codon_schema.json` records candidate algebraic decompositions for energy, RMS, Schroeder decay, clarity and band-energy normalization. It is a descriptive schema in this build; numerical calculations currently use the Python reference implementation rather than dispatching through a codon VM. This avoids implying a degree of codonic execution that has not yet been implemented.

## 7. Verification

The standard-library test suite validates:

- WAV PCM and IEEE-float decoding;
- 16- and 24-bit sample decoding;
- exponential energy-decay fitting;
- gain invariance of normalized decay features;
- room median aggregation and symmetric RDM construction;
- end-to-end report generation from synthetic WAV fixtures;
- explicit no-data behaviour when a room archive is absent.

Run `python -m unittest discover -s tests -v`.

## 8. Next stage

Build 13 should prioritize truly paired acoustic and structural recordings under the same excitation, trial ID, room and source configuration. Only then can cross-modal RDM alignment test a shared physical response geometry without confounding the result with unpaired datasets.
