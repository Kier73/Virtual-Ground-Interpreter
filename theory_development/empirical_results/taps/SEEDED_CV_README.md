# Seeded TAPS cross-validation provenance

The frozen Build 13-15 reports under this folder are historical: when those
builds are run directly, their pair IDs still use the shipped ephemeral salt.

For new empirical runs, use the seeded validation path:

```powershell
python validation\run_seeded_taps.py --build 14 --root <TAPS_ROOT> --output <OUT> --seed 13
python validation\run_taps_cv.py --root <TAPS_ROOT> --split test --seed 13
```

The seeded wrapper binds an explicit salt before calling the frozen code and
writes `seeded_salt_provenance.json`. The companion summary in
`seeded_cv_summary.json` records the seed, salt fingerprint, speaker/sentence
cross-validation medians and the second-corpus availability status. Full fold
rows are in `../../../validation/taps_cv_results.json`.
