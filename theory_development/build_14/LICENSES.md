# Build 14 — Licenses and data handling

## Build 14 code

The inherited project code license is included in `LICENSE`. Review its terms before reuse.

## TAPS source materials

The public dataset card identifies the Hugging Face dataset release as CC BY 4.0. The accompanying journal article is published under CC BY-NC-ND 4.0. These are distinct statements about different materials; do not assume the article license automatically governs every dataset file or third-party item. Check the current Zenodo record and dataset card before redistribution or commercial reuse.

## Participant data handling

The TAPS corpus contains human voice recordings. Build 14 uses speaker identifiers only internally to form within-speaker paired comparisons. Transcripts, raw speaker identifiers and demographics are not written to aggregate outputs. Pair keys use an ephemeral process-local salt. Aggregate output is the default. Optional derived per-utterance features should remain local unless the dataset terms and applicable research ethics requirements have been reviewed. This package contains no participant audio.
