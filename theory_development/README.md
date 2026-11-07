# Theory development — Builds 01–19

This folder holds the pre-Virtual-Ground arc: the mathematical response-geometry program, its falsification studies, and the empirical acoustics work. Each build is frozen and self-contained; later builds carry earlier code forward rather than importing across directories.

## Contents

- `build_01/` … `build_15/` — the original response-geometry builds, from the S³ response representation through the paired-sensor TAPS frontier.
- `build_17/` … `build_19/` — representation and equivalence work. **Build 16 is embedded in `build_17/`**, where its 24 tests are included in that suite.
- `empirical_results/` — work produced after unpacking, outside the frozen packages:
  - `build_12/` — the shipped Rochester RIR run plus `corrected/`, which fixes the onset convention and reruns the unmodified Build 12 feature functions.
  - `taps/` — held-out TAPS runs for Builds 13–15 and the external Build 15 matcher controls.

## Arc summary

| Builds | Theme | Outcome |
|---|---|---|
| 01–06 | Algebraic response geometry, geometric phase, shear transport, Hopf fibration, active probes | Mathematical mechanisms behave as specified; no empirical invariant claimed. |
| 07–10 | Designed path libraries, randomized controls, cross-modal resonators, heterogeneous systems | Build 07's strong correlation weakens under Build 08; Build 09's near-identity does not generalize in Build 10. |
| 11–12 | Smartphone vibration recording; Rochester room impulse responses | Build 11 is descriptive only. Build 12's shipped EDT/C50 values are invalid because of a pre-roll onset bug; the corrected reanalysis recovers a physically coherent decay/early-late/temporal geometry. |
| 13–15 | TAPS paired throat/acoustic sensor; temporal-emission layer; local-clock event graphs | The cross-modal RDM geometry survives shuffled-pair nulls. The event-level matcher and clock recovery do not survive the external controls. |
| 16–19 | Matcher falsification; clock-symmetric representations; SU(2)/S³ atlas; endpoint/path/observer equivalence | Build 16 demotes the combined matcher; the later builds map which distinctions each representation preserves. Synthetic fixtures only. |

The detailed build table, per-build outcomes and caveats are in [`../INDEX.md`](../INDEX.md). The interpretive essay is [`../PERSPECTIVE.md`](../PERSPECTIVE.md).

## Run

From the repository root:

```powershell
python run_all_tests.py --builds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 17 18 19
```

Or run a single build from its directory:

```powershell
cd theory_development\build_15
python -m unittest discover -s tests -v
```

The empirical scripts have additional requirements: the Rochester RIR corpus for `empirical_results/build_12/corrected/reanalyze_corrected.py`, and the extracted TAPS test split for the scripts under `empirical_results/taps/`. The corpora are not redistributed here.

## Notes

- Build 12's correction is deliberately kept beside the frozen build, not patched into it. The shipped run remains the record of what the original pipeline produced.
- The pre-Virtual-Ground builds are standard-library Python only. See [`../test_results/SUMMARY.md`](../test_results/SUMMARY.md) for counts and environment.
