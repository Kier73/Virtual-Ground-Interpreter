# Virtual Ground Interpreter

A frozen, self-contained research archive for the **Virtual Ground** program: a 30-build investigation into observer-relative response geometry, empirical acoustics, and a bounded interpreter that infers predictive operational structure from streams.

The repository is split into two arcs:

| Folder | Builds | Subject |
|---|---|---|
| `theory_development/` | 01–19 | Mathematical response geometry, falsification studies, and empirical acoustics (Rochester RIR, TAPS) |
| `virtual_ground/` | 20–30 | The Virtual Ground interpreter: active identification, inductive synthesis, latent contexts, online partial grounds, event and motif discovery, continuous signals, and signal-coded computation |

Every build is frozen in the state it was published. Later builds carry earlier code forward; nothing is refactored across build boundaries. All Python is standard-library only.

## What a Virtual Ground is

Build 20 defines a Virtual Ground as the **generative operational logic** of a system — the rules that generate valid states, actions, transitions, invariants and observer quotients — rather than the materialized state space itself. The later builds test that definition inside bounded synthetic domains: identifying a ground by intervention, synthesizing one from a declared grammar, tracking one online with an unknown start and partial channels, keeping multiple explanations alive, discovering event motifs and boundaries, and finally operating directly on continuous signals.

This is a methods program. It does **not** establish a universal observer, general program synthesis, or a physical signal computer. Its high synthetic scores are implementation checks on controlled fixtures, not empirical claims.

## Verification

Verified on Windows with Python 3.14.0 on 2026-11-06:

- **765 / 765** top-level tests pass across 28 unpacked build trees.
- **177 / 177** embedded Build 24–30 regression tests pass.
- **1,907 / 1,907** manifest hashes match across 22 builds.
- **28 / 28** original archive checksums match (`archives/SHA256SUMS.txt`).

Full record: [`test_results/SUMMARY.md`](test_results/SUMMARY.md) and [`test_results/MANIFEST_VERIFICATION.txt`](test_results/MANIFEST_VERIFICATION.txt).

## Quick start

```powershell
# Run every top-level build's unittest suite
python run_all_tests.py

# Run the embedded Build 24–30 regression chain
python virtual_ground\build_30\run_all_regressions.py
```

Run a single build from its own directory:

```powershell
cd virtual_ground\build_30
python run_build30.py
python -m unittest discover -s tests -v
```

No third-party packages are required. Python 3.13+ is sufficient; the verification run used 3.14.0. Set `PYTHONDONTWRITEBYTECODE=1` when checking the shipped Build 27/30 manifests, which include Python 3.13 `.pyc` files.

## Repository layout

```
VL_Response_Geometry/
├── archives/                  original build ZIPs + SHA256SUMS.txt (28 archives)
├── theory_development/        Builds 01–19: response geometry and empirical acoustics
│   ├── build_01/ … build_15/  frozen, self-contained build trees
│   ├── build_17/ … build_19/  Build 16 is embedded in build_17
│   └── empirical_results/     corrected Rochester RIR analysis and held-out TAPS runs
├── virtual_ground/            Builds 20–30: the Virtual Ground interpreter
│   ├── build_20/ … build_23/  operational foundations
│   └── build_25/ … build_30/  Build 24 is embedded in build_25/legacy and build_26/notes
├── test_results/              per-build logs, manifest verification, test summary
├── validation/                post-freeze validation tests and benchmarks
├── run_all_tests.py           orchestrates every top-level build's unittest suite
├── INDEX.md                   build map, outcomes, and reproducing commands
└── PERSPECTIVE.md             interpretive essay on both arcs
```

Each build keeps its own tests, reports, schemas, manifests and documentation. The nested `legacy/`, `notes/` and `verification/` trees are part of that record; they are not duplicates to be deleted.

## Where to read

1. [`INDEX.md`](INDEX.md) — the full build map, what held up and what did not, and reproducing commands.
2. [`Questions On the Virtual Ground.md`](Questions%20On%20the%20Virtual%20Ground.md) — the source questions that motivate the Virtual Ground concept.
3. [`PERSPECTIVE.md`](PERSPECTIVE.md) — an interpretive essay on the program and its self-corrections.
4. [`theory_development/README.md`](theory_development/README.md) — Builds 01–19.
5. [`virtual_ground/README.md`](virtual_ground/README.md) — Builds 20–30.
6. [`test_results/SUMMARY.md`](test_results/SUMMARY.md) — the test and manifest record.
7. [`validation/README.md`](validation/README.md) — post-freeze validation tests and benchmarks.

A suggested sequence through the primary documents:

1. `theory_development/build_07/BUILD_07.md` → `build_08/BUILD_08.md` → `build_09/BUILD_09.md` → `build_10/BUILD_10.md` — the central positive-to-negative sequence.
2. `theory_development/empirical_results/build_12/corrected/FINDINGS.md` — the real-data onset bug and the corrected acoustic result.
3. `theory_development/build_13/BUILD_13.md`, `build_14/BUILD_14.md`, `build_15/BUILD_15.md` — the paired-sensor and local-clock frontier.
4. `theory_development/build_17/BUILD_16.md` → `BUILD_17.md` → `build_18/BUILD_18.md` → `build_19/BUILD_19.md` — falsification and the representation bridge.
5. `virtual_ground/build_20/BUILD_20.md` → `build_21/BUILD_21.md` → `build_22/BUILD_22.md` → `build_23/BUILD_23.md` — the Virtual Ground foundations.
6. `virtual_ground/build_25/legacy/build24/BUILD_24.md` → `build_25/BUILD_25.md` → `build_26/BUILD_26.md` → `build_27/BUILD_27.md` → `build_28/BUILD_28.md` → `build_29/BUILD_29.md` → `build_30/BUILD_30.md` — latent contexts, online partial grounds, and the path from operations to raw signals.
7. `theory_development/empirical_results/taps/README.md` — the held-out TAPS results and the Build 15 controls.

## Archive and reproducibility notes

- Builds **16** and **24** were never shipped as standalone archives. Build 16 survives inside Build 17; Build 24 survives inside Builds 25 and 26. Their tests are included in the embedded regression chain.
- The original binary ZIPs are **not** committed. `archives/SHA256SUMS.txt` records all 28 checksums so an existing copy can be verified; the unpacked trees and their manifests are the working record.
- The Rochester RIR and TAPS corpora are also not redistributed. Derived tables, scripts, logs and findings are included under `theory_development/empirical_results/`.
- Build 30's `run_all_regressions.py` rewrites nine `verification/` files that its own manifest covers. Fresh logs from that run are preserved in `test_results/build_24_30_embedded/`; the frozen files were restored afterward.
- Builds 27 and 30 ship Python 3.13 `.pyc` files listed in their manifests. They are preserved as part of the frozen record.

## License

MIT. See [`LICENSE`](LICENSE).
