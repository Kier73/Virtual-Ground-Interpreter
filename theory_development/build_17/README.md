# Refractive / Virtual Layer response geometry — Build 17

Build 17 compares symmetry-adapted temporal representations under circular translation, positive time dilation and nonlinear monotone clock drift.

## Main findings

- Finite Fourier magnitude is circular-shift invariant to numerical precision.
- STFT is covariant to frame-aligned shifts: its frame columns move.
- Pooled undecimated Haar-like detail energies are circular-shift invariant and redistribute under dilation.
- Mellin magnitude is dilation-invariant on a finite periodic log-time grid.
- The chosen event-graph Laplacian signature is invariant under affine clock maps and node relabeling; nonlinear drift changes it when recurrence motifs are represented.
- The graph motif threshold materially changes what the graph contains and is treated as a parameter, not a universal constant.

All Build 17 data are synthetic. No participant or physical sensor recordings were processed.

## Reproduce

```bash
python -m unittest discover -s tests -v
python build_17.py --output reports
```

Python standard library only.

## Key files

- `BUILD_17.md` — methodology, numerical results, limitations.
- `PERSPECTIVE_PATHS.md` — route from the conversation's perspectives to candidate representation families.
- `REPRESENTATION_MAP.md` — expanded representation catalogue from Build 16.
- `temporal_representations.py` — implementations of the Build 17 transforms and diagnostics.
- `reports/temporal_representation_comparison.json` — complete fixture-level results.
- `representation_action_matrix.csv` — compact symmetry/representation matrix.

## Scope

The finite DFT/STFT use circular boundary conventions; the Mellin case uses a periodic finite log-time grid; the Haar-like descriptor is redundant rather than an orthonormal DWT; graph spectra are incomplete graph invariants. These results test implementation properties only.
