# Build 14 — Sources

## TAPS dataset

Kim, Yunsik; Song, Yonghun; Chung, Yoonyoung (2026). “Throat and acoustic paired speech dataset for deep learning-based speech enhancement.” *Scientific Data* 13, Article 911. DOI: <https://doi.org/10.1038/s41597-026-07268-2>.

Dataset record: <https://zenodo.org/records/18324208>, DOI <https://doi.org/10.5281/zenodo.18324208>.

Hugging Face dataset card: <https://huggingface.co/datasets/yskim3271/Throat_and_Acoustic_Pairing_Speech_Dataset>.

The Zenodo record describes 60 Korean speakers and 6,000 paired utterances (~15.3 hours), with speaker-disjoint train (40 speakers / 4,000 utterances), development (10 / 1,000) and test (10 / 1,000) splits. The held-out test ZIP is listed at approximately 452.1 MB. These are dataset-record facts, not results from Build 14 processing.

The paper describes a throat-mounted accelerometer channel and an acoustic microphone channel, sensor-specific signal conditioning, and alignment preprocessing. Build 14 preserves the inherited rule not to reapply those operations to the released files. It treats the 8 kHz original throat bandwidth as Nyquist-limited at 4 kHz even where the released channel is resampled to 16 kHz.

## Method boundary

Build 14's temporal-emission signature is a new operational proposal authored for this project. It is not presented as a method specified by the TAPS paper. The event landmarks are local maxima of the 20 ms RMS envelope using a stated threshold and minimum separation. No hidden state or phoneme labels are available to validate them in this build.

The affine clock transformation result is elementary: for \(t'_i=a+ct_i\), intervals scale by \(c\), normalized interval ratios are invariant, and rate per unit time scales by \(1/c\). The implementation tests that identity numerically.

## Current data-access status

The public dataset metadata and file sizes were accessible through the web index. Direct file retrieval from the local runtime failed because DNS resolution for external hosts was unavailable. No TAPS audio files were downloaded or analyzed by Build 14.
