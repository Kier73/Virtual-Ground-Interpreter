# Build 12 empirical outputs

This directory contains **two analyses of the same 90-file Rochester RIR corpus**:

| Directory | What it is | Use it? |
|---|---|---|
| `./` | The first run of the unmodified Build 12 pipeline. | For the bug record only. EDT, C50, C80, D50 and Ts are invalid. |
| `./corrected/` | The same frozen feature functions applied after trimming each file at its direct-sound peak. | Yes, for room-acoustic interpretation. |

## Why there are two

Every Rochester WAV has a 1.000 s pre-roll of low-level noise. Build 12's onset rule (`first |x| >= 0.001 * peak`) fires in that noise at a median of 968.8 ms before the direct sound. The shipped run therefore reports EDT of 6.6–44.2 s and C50 of −54 to −41 dB. Those numbers are a record of the bug, not room measurements. T20/T30 happen to survive because their fit range lands on the real decay; shipped and corrected T20 correlate at 0.99996.

The correction trims at the direct-sound peak and reruns the **unmodified** `theory_development/build_12/build_12.py` functions. No frozen build file was edited. Full explanation: `corrected/FINDINGS.md`.

## Key corrected values

- 90 WAVs, 15 room folders (14 rooms; Room 2 is split into with/without-windows variants), all 48 kHz / 32-bit IEEE float / mono, 2.972 s.
- EDT: 0.23–3.10 s (median 0.62 s).
- T20: 0.28–3.16 s.
- C50: −2.8 to +13.7 dB.
- D50: 0.34–0.96.
- Corrected view correlations: decay ↔ early_late 0.631, decay ↔ temporal 0.666, early_late ↔ temporal 0.737; spectral and level remain comparatively separate.

## Files

First run (invalid early-time metrics):

- `build_12_report.json`
- `rir_file_features.csv`
- `room_features.csv`
- `rdm_*.csv`
- `rdm_view_correlations.csv`

Corrected run:

- `corrected/build_12_report_corrected.json`
- `corrected/rir_file_features_corrected.csv`
- `corrected/room_features_corrected.csv`
- `corrected/room_correction_comparison.csv`
- `corrected/rdm_*_corrected.csv`
- `corrected/rdm_view_correlations_comparison.csv`
- `corrected/FINDINGS.md`
- `corrected/reanalyze_corrected.py`

## Reproduce

The corpus is not redistributed here. It was downloaded with
`theory_development/build_12/scripts/fetch_rochester_figshare.py` to
`C:\Users\kross\AppData\Local\Temp\opencode\vl_data\rochester\wavs`.
Then:

```powershell
python theory_development\empirical_results\build_12\corrected\reanalyze_corrected.py
```

Source: University of Rochester room impulse response dataset, DOI `10.60593/ur.d.26801089.v3`, CC BY 4.0. Pipeline: `theory_development/build_12/build_12.py`.
