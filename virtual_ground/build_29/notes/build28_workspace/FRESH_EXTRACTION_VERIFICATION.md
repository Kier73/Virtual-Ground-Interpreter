# Build 28 Fresh-Extraction Verification

## Package verification

The complete Build 28 directory is hashed in `MANIFEST.sha256`. The original Build 27 archive and its exact extracted workspace are both included. The embedded original Build 27 manifest and its nested Build 26 and Build 24 manifests were checked independently before packaging:

- Build 27 manifest entries verified: 236
- Build 26 manifest entries verified: 169
- Build 24 recovery manifest entries verified: 39

## Regression results

| Suite | Tests | Result |
|---|---:|---|
| Build 28 | 21 | PASS |
| Build 27 | 30 | PASS |
| Build 26 | 27 | PASS |
| Build 25 | 34 | PASS |
| Build 24 | 17 | PASS |
| **Combined** | **129** | **PASS** |

`run_all_regressions.py` runs the Build 28 suite and extracts the preserved Build 27 original ZIP to a temporary directory for inherited regressions. It does not modify the embedded Build 27 workspace.

## Build 28 experiment verification

- 12 synthetic training streams; 1,140 tokens.
- 5 held-out streams; 465 tokens.
- No operation boundaries or semantic operation names supplied to the learner.
- 179 internal sparse checkpoints; only 49 happened to coincide with hidden operation boundaries (27.4%).
- 4 motifs survived the 31-trial family-wise within-trace permutation screen.
- 4 nested submotifs were recorded and excluded from double counting.
- 42 raw frequent motifs in the shuffled control; 0 survived its own family-wise permutation screen.
- Segmentation precision, recall and F1: 1.0 on the controlled synthetic fixtures.
- 57 sparse checkpoint equations yielded unique integer effects.
- Held-out checkpoint predictions: 24 / 24 exact.
- The `a,b,c` ambiguity fixture remained explicitly ambiguous.
- Compiled ground JSON round-trip and fingerprint checks passed.

These are deterministic synthetic results. They do not establish raw-sensor segmentation or performance on natural event streams.

## Reproduction

From the extracted Build 28 root:

```bash
sha256sum -c MANIFEST.sha256
python run_build28.py
python run_all_regressions.py
```

Python 3.10+; standard library only.

## Clean ZIP extraction run

The ZIP was extracted into a separate directory. From that fresh extraction:

- `sha256sum -c MANIFEST.sha256` passed for every listed package file before execution.
- Build 27, Build 26 and Build 24 embedded manifests again verified 236, 169 and 39 entries respectively.
- `python run_build28.py` reproduced the same four motifs, unique integer checkpoint effects, 1.0 synthetic segmentation F1, 24/24 held-out checkpoint predictions and 0 shuffled-control survivors.
- `python run_all_regressions.py` passed all 129 tests (Build 28: 21; inherited Builds 24–27: 108).

Fresh extraction logs are preserved under `verification/fresh_extraction_*`.
