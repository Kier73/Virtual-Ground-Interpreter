# Multi-digit finite Ground compiler verification

Date: 2026-11-16 America/Toronto. Baseline:
`e6e1900782aeede18a4de9046511bbba234dbc6e`.

The compiler's eight-state/eight-action rejection was a single-cell encoding
restriction. The new path composes existing Signal8 cells into little-endian
base-eight identities, keeping output channels and primitive laws unchanged.
Every state/action digit must match before successor writes are emitted.

## Executed local results

Windows, Python 3.14:

- `python -m unittest discover -s tests -v`: **325 passed**.
- `python -m vgi verify`: **4,772 cases, PASS, zero errors**.
- With the package on `PYTHONPATH`, `python examples/run_delayed_six.py`:
  **10 differential cases, PASS**; six-step state/output traces agree.
- Compared the pinned old compiler with the new compiler for alphabet sizes
  1, 2 and 8 and word lengths 0, 1 and 3: **nine exact matches** of generated
  program dictionaries and initial memory. This checks v1 compatibility.

The 12 new tests include all 81 edges of a nine-state/nine-action Ground;
8/64 encoding thresholds; independent state/action widths; a 65-action
alphabet; empty words; observer reframing; unused state/action encodings;
uncertain high digits; execution budgets; and reconstruction-certificate
version/context rejection. The former nine-state rejection test now checks
the full nine-step cycle against direct semantics.

Reconstruction certificates retain compiler version 1 for width-one programs
and identify compiler version 2 for wider alphabets. The existing verifier
replays the finite witness corpus and refuses mismatched versions/contexts.
The Signal8 Ground fingerprint remains
`4ba599c21ec7e446572dad61b2a66ecb9c0844fd3dee406e4d947e04db56c43b`.

## Remaining goals

This expands finite table compilation. It does not change its table/word-size
cost, admit partial transitions, widen output-channel semantics, provide an
external source authority or prove an untested model. A typed backend and
compact law-based lowering remain separate work. Hosted CI and additional
platforms are not claimed by these local results.
