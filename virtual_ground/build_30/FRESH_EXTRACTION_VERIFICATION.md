# Build 30 Fresh Extraction Verification

## Result

A clean copy of `vl_response_geometry_build_30.zip` was extracted into a separate directory and checked independently.

- Build 30 package manifest: 386 entries verified.
- Embedded Build 29 workspace manifest: 341 entries verified.
- Builds 24–30 direct test suites: 177/177 passed.
- Build 30 experiment rerun from the extracted copy: completed.
- `reports/build_30_results.json` from the extracted run matched the packaged result byte-for-byte.
- The FSK control waveform's Build 29 temporal event-boundary audit retained F1 0.9655 (14/15 symbol boundaries).
- The finite phase-arithmetic sweep completed all 128 `ADD8` / `SUB8` operand pairs with zero noiseless errors.

## Regression counts

| Build | Tests | Result |
|---|---:|---|
| 24 | 17 | PASS |
| 25 | 34 | PASS |
| 26 | 27 | PASS |
| 27 | 30 | PASS |
| 28 | 21 | PASS |
| 29 | 24 | PASS |
| 30 | 24 | PASS |
| **Total** | **177** | **PASS** |

The regression runner executes each preserved suite once, avoiding repeated recursive runs of the same earlier builds.

## Integrity note

The Build 30 archive contains both the original Build 29 archive and an inspectable Build 29 working copy. The working-copy manifest was refreshed after its regression logs were updated; the original Build 29 archive remains embedded unchanged.

All Build 30 numerical experiments are synthetic. No physical signal hardware, empirical recordings or universal signal-computing capability were demonstrated.
