# Licensing and data handling

## Build 13 code

The original code in this package is released under the MIT License (see `LICENSE`).

## TAPS dataset

The Hugging Face dataset card for `yskim3271/Throat_and_Acoustic_Pairing_Speech_Dataset` identifies the dataset as CC-BY-4.0. The Zenodo record is the authoritative file-based release; its current data-level terms should be checked on the record before copying or redistributing any audio. The package includes a downloader but does not bundle the recordings.

The associated Scientific Data article is CC BY-NC-ND 4.0. This is the article's license, not automatically the license for the audio archive.

## Privacy

The dataset contains consented human voice recordings. Build 13 does not attempt speaker identification, does not export transcripts or demographics, and only uses speaker IDs internally to form within-speaker comparisons. Pair hashes use an ephemeral process-local salt. Aggregate outputs are the default. Do not publish raw recordings or derived per-utterance voice features without checking the dataset terms and research ethics requirements.
