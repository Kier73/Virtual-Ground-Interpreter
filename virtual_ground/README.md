# Virtual Ground — Builds 20–30

This folder holds the Virtual Ground interpreter arc. A Virtual Ground is the **generative operational logic** of a system: the rules that generate valid states, actions, transitions, invariants and observer quotients, rather than a materialized state graph. The builds test that idea inside bounded, deterministic, synthetic domains.

All builds are frozen and self-contained. Builds 25 and 26 embed Build 24 under `legacy/`; there is no standalone Build 24 directory.

## Build chain

| Build | Main move |
|---|---|
| 20 | Formalizes the Virtual Ground; Rotor-4 reversible and Support-9 irreversible fixtures; exact state navigation. |
| 21 | Controlled, endogenous and exogenous variables; observation/action partitions; viability; resource trade-offs; ground revision. |
| 22 | Active identification by intervention; in-family candidates, passive comparator, out-of-family holdout, revision monitor. |
| 23 | Inductive synthesis of executable ground programs within a declared grammar; grammar refinement. |
| 24 | Latent predictive contexts from action/output traces; L*-style observation table; compile to phase program or finite automaton. Embedded in 25/26. |
| 25 | Online tracking from an unknown start; beliefs over contexts; asynchronous partial channels; contradiction quarantine; per-source clocks. |
| 26 | Incremental partial ground; unknown edges stay unknown; horizon refinement; bounded stream memory; fail-closed transitions. |
| 27 | Competing explanations from noise to regime change; opaque operation signatures; ordinal evidence; discriminating probes. |
| 28 | Boundary discovery from event streams; exact contiguous motifs; ordered-shuffle maximum-statistic null; sparse-checkpoint effect equations. |
| 29 | Continuous measurements to observer-relative events; persistent change scores; harmonic, temporal and combined token views; WAV ingestion. |
| 30 | Adaptive observer-profile selection and signal-coded computation: FSK opcodes plus 8-PSK operand phasors for modular phase arithmetic. |

The full outcome table, including exact figures and limitations, is in [`../INDEX.md`](../INDEX.md).

## Run

From this folder:

```powershell
# A single build
cd build_30
python run_build30.py
python -m unittest discover -s tests -v
```

From the repository root:

```powershell
# All top-level builds, including this arc
python run_all_tests.py

# Embedded Build 24–30 regression chain
python virtual_ground\build_30\run_all_regressions.py
```

## Verification

The top-level Build 20–30 suites (excluding the embedded Build 24) contribute part of the **765 / 765** top-level tests. The embedded Build 24–30 chain passes **177 / 177** tests: Build 24 contributes 17 distinct tests, and the rest are inherited suites rerun in their preserved workspaces. See [`../test_results/SUMMARY.md`](../test_results/SUMMARY.md) and the per-build logs plus [`combined_regression_summary.json`](../test_results/build_24_30_embedded/combined_regression_summary.json).

## Scope

Everything in this folder is synthetic. The builds process no physical sensor data, make no physical hardware claim, and do not establish general program synthesis or a universal observer. The perfect scores on controlled fixtures are implementation checks. The design intention is the opposite of a universal claim: keep unknowns visible, prefer discriminating probes, and report deliberate held-out failures rather than silently repairing the law.

Build 30's `run_all_regressions.py` mutates nine `verification/` files covered by its own manifest. Fresh logs are stored under `test_results/build_24_30_embedded/`; the frozen files were restored after verification. Use `PYTHONDONTWRITEBYTECODE=1` when checking the Build 27/30 manifests because they include Python 3.13 `.pyc` files.
