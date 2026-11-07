# Second paired-sensor corpus — availability and limitation manifest

## Status

A second paired-sensor corpus is **not included** in this repository.

The existing paired corpus is TAPS (throat microphone + acoustic microphone). It is also **not redistributed**; the repository contains derived tables, scripts, logs and findings under `theory_development/empirical_results/taps/`, not the raw audio corpus.

## Why no second corpus is attached

No additional paired-sensor corpus is present in this repository, and no licensed redistributable download was performed for this commit. Adding a corpus would require:

1. a corpus with simultaneous paired channels,
2. speaker and sentence grouping available in memory,
3. license terms that permit local research processing and aggregate reporting,
4. a documented split and provenance record,
5. aggregate-only outputs with no raw speaker IDs or transcripts.

If those conditions are met, the same seeded validation path can be used:

```powershell
python validation\run_taps_cv.py --root <EXTERNAL_PAIRED_CORPUS_ROOT> --split test --seed 13
```

## Adapter requirement

Builds 13–15 expect `throat_microphone.wav` and `acoustic_microphone.wav` pairs plus `features.json` metadata. A second corpus with a different layout needs a small adapter that produces the same in-memory pairing structure. The seeded wrapper binds the explicit salt before analysis and writes `seeded_salt_provenance.json`.

## Machine-readable record

See `second_paired_corpus_manifest.json` for the JSON availability/limitation record. `validation/salt_cv.py:corpus_status` returns `not_run` when no external root is supplied.
