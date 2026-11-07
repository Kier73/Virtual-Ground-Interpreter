# Build 13 — Sources

## Dataset

**Kim, Yunsik; Song, Yonghun; Chung, Yoonyoung (2026).** *TAPS: Throat and Acoustic Paired Speech Dataset (Korean).* Zenodo record 18324208, DOI: [10.5281/zenodo.18324208](https://doi.org/10.5281/zenodo.18324208).

- Dataset record: https://zenodo.org/records/18324208
- Hugging Face data release: https://huggingface.co/datasets/yskim3271/Throat_and_Acoustic_Pairing_Speech_Dataset
- Record reports 60 speakers, 6,000 utterances, approx. 15.3 h, and separate train/dev/test speaker sets.
- File-based release contains paired `throat_microphone.wav`, `acoustic_microphone.wav`, and `features.json` per utterance.

## Dataset description paper

**Kim, Y.; Song, Y.; Chung, Y. (2026).** *Throat and acoustic paired speech dataset for deep learning-based speech enhancement.* Scientific Data 13, Article 911. DOI: [10.1038/s41597-026-07268-2](https://doi.org/10.1038/s41597-026-07268-2).

Useful documented facts:

- TAPS pairs an accelerometer-based throat microphone with an acoustic microphone.
- Throat accelerometer: original 8 kHz, 16-bit, +/-4 g, one recorded axis; acoustic microphone: 16 kHz, 24-bit.
- The final release is described as already preprocessed and globally aligned; the authors report a final global shift of 13 samples at the original 8 kHz throat rate (1.625 ms).
- Timing mismatch varies with microphone distance, speaker/vocal-tract characteristics and phoneme content.
- The article reports high-frequency and voiceless components are attenuated or absent in throat-microphone recordings.
- The paper documents informed consent for release of voice recordings and coded speaker IDs without direct personal identifiers.
- The documented dataset schema contains text/audio/metadata but does not define an emotion label.

## License/source notices

- Hugging Face dataset card labels the dataset release `cc-by-4.0`.
- The Scientific Data article is licensed CC BY-NC-ND 4.0. That article license should not be confused with the separate dataset release terms.
- The Zenodo record's rendered page did not expose a complete readable data-license label in the inspected view; verify current data-level terms before redistribution.
- No audio files, transcripts, article images or original paper text are bundled in this package.

## Research-method references

- The TAPS paper describes cross-correlation for per-utterance timing mismatch, and compares per-utterance, per-speaker mean and global mean corrections. Build 13 uses cross-correlation only as a residual diagnostic; it does not replace the published preprocessing.
- RDM comparison and rank correlation are used here as exploratory representational-geometry tools, not as proof of a universal invariant.
