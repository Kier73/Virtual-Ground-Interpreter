# Build 06 — Active Observation on S³ / Hopf Geometry

A standalone, dependency-free mathematical prototype combining configurable codonic arithmetic, quaternion transport, Hopf-fibre geometry, observer-specific measurement families, and intention-conditioned probe selection.

## Run

Requirements: Python 3.10 or later. No third-party packages.

```bash
./run_build.sh
```

The script runs the test suite and regenerates the JSON and CSV reports.

## Main files

- `s3_active_observer.py` — codon interpreter, compiled Hamilton product, Hopf paths/lifts, observation models, information-gain scoring, active episodes, and report construction.
- `tests/test_s3_active_observer.py` — 31 numerical and behavioural tests.
- `generate_artifacts.py` — deterministic report and CSV generation.
- `BUILD_06.md` — mathematics, findings, interpretation, and limitations.
- `NOTES_NEXT.md` — proposed Build 07.
- `SOURCES.md` — references and research context.
- `reports/build_06_report.json` — full results.
- `reports/antipodal_control.json` — focused S³/SO(3) comparison.
- `reports/summary.txt` — brief run summary.
- `data/regular_hopf_paths.csv` — sampled base paths and quaternion lifts.
- `data/geometry_summary.csv` — compact geometric measurements.
- `data/probe_rankings.csv` — expected-information-gain scores by observer and intention.
- `data/antipodal_control.csv` — q versus -q measurement comparison.

## Scope

This is a finite synthetic experiment, not the complete Virtual Layer address substrate. The quaternion Hamilton product is executed through a locally compiled scalar codon program (`mx`, `ad`, `su`). The experiment does not use SHA-256-derived coordinates as semantic distances, and it makes no claim about emotional tone or physical vibration.
