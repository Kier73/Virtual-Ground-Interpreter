# Build 27 — Fresh Extraction Verification

The Build 27 ZIP was extracted into a separate directory and verified from that copy.

## Fresh-extraction results

| Check | Result |
|---|---:|
| Top-level package manifest | 228 / 228 entries verified in the first fresh extraction |
| Embedded Build 26 manifest | All listed entries verified |
| Embedded original Build 24 manifest | All listed entries verified |
| Build 27 unit suite | 30 / 30 passed |
| Build 26 regression suite | 27 / 27 passed |
| Build 25 regression suite | 34 / 34 passed |
| Build 24 regression suite | 17 / 17 passed |
| Combined test count | **108 / 108 passed** |
| Build 27 experiment runner | Completed successfully |

The verification logs are preserved under `verification/`.

## Reproduce

From the extracted Build 27 root:

```bash
sha256sum -c MANIFEST.sha256
python run_build27.py
python run_all_regressions.py
```

`run_all_regressions.py` executes the Build 27 suite plus the inherited Build 26, Build 25 and Build 24 suites from their own package roots.

## Evidence boundary

Passing tests establish the behavior of the included fixtures and software contracts. They do not prove that a discovered operation is causal, globally valid, or the unique description of an external physical system.
