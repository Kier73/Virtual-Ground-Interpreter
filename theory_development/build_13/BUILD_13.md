# Build 13 — Paired voice / throat-vibration response geometry

**Status:** Paired-sensor analysis engine implemented and tested. TAPS metadata verified. Empirical audio has **not** been downloaded or analyzed in this execution environment; only synthetic fixtures were used for pipeline verification.

## 1. Why the research direction changed

Build 12's planned PMA plate experiment was a useful route to paired acoustic pressure and mechanical vibration. A closer match to the original tone question emerged in the TAPS dataset: the same utterance was simultaneously recorded by an accelerometer-based throat microphone and an acoustic microphone. This directly places a tissue-conducted vibration signal beside its airborne acoustic counterpart.

TAPS contains 6,000 utterances from 60 native Korean speakers, split into train/dev/test groups with no speaker overlap. The held-out test split has 10 speakers and 1,000 utterances (about 2.6 h). The Zenodo test archive is about 452 MB. The standard file release stores paired WAVs and per-utterance JSON metadata.

## 2. What the sensors measure

- **Throat channel:** a MEMS accelerometer configured on one axis, originally sampled at 8 kHz and 16-bit, with +/-4 g dynamic range. The paper reports that the original throat signal is upsampled to 16 kHz in the released aligned dataset.
- **Acoustic channel:** a MEMS air microphone sampled at 16 kHz and 24-bit.
- The channels are simultaneously acquired but have different transfer functions, physical meanings and effective bandwidths.

The paper documents a 50 Hz high-pass to remove throat-channel gravity/DC effects, acoustic-channel denoising, trimming and temporal alignment. The final TAPS release applies a global alignment shift of 13 samples at the original 8 kHz throat rate (1.625 ms). Build 13 does not apply those steps again.

## 3. Research question

Do the throat-vibration and acoustic channels preserve similar **within-speaker utterance neighborhoods** when described by shared-band spectral, temporal and periodicity features?

For each speaker independently:

1. Compute a feature vector for every paired utterance in the acoustic channel.
2. Compute the corresponding feature vector for the throat channel.
3. Robust-standardize features within that speaker and channel.
4. Construct an RDM for each channel using the same utterance ordering.
5. Compare the two RDMs with Spearman correlation.
6. Shuffle the throat utterance assignments within speaker to create a pairing null.
7. Bootstrap over speakers, not over individual utterance pairs.

This avoids allowing between-speaker differences to dominate the first comparison. The test split is the default because its speakers are held out from train and dev.

## 4. Feature construction

The primary cross-modal feature view is restricted to **80-3500 Hz**. This is a conservative common band below the throat sensor's original 4 kHz Nyquist limit. It includes spectral centroid, 85% rolloff, spectral flatness, five band-energy shares, F0/periodicity summaries and envelope variability.

The acoustic-only 4000-7800 Hz energy share is retained as a separate descriptor, not inserted into the cross-modal RDM. The feature extractor carries the throat channel's original 4 kHz Nyquist limit forward even though its released WAV is stored at 16 kHz after upsampling; it therefore marks the high-band descriptor invalid for the throat channel rather than measuring interpolation artefacts. Tissue-conducted throat recordings are known to attenuate high-frequency and some voiceless components; the acoustic-only 4000-7800 Hz band is therefore a genuine difference in observation, not an error to be filled in by normalization.

Absolute digital RMS and peak are reported separately. The two microphone channels do not share physical units or calibration, so their raw amplitudes are not directly compared.

## 5. Alignment treatment

The released TAPS waveforms are already globally aligned. Build 13 reports two residual diagnostics without changing the signal samples:

- **Raw waveform correlation:** a short, common low-rate segment is compared over +/-5 ms. The common analysis rate is capped at 4 kHz, giving 0.25 ms lag steps when both source channels are at or above 4 kHz.
- **Envelope correlation:** 20 ms RMS envelopes are compared, giving a coarser timing view.

The positive-lag sign convention is `corr(T[n], A[n+lag])`: positive means the acoustic waveform is later relative to the throat waveform. These estimates are diagnostics only. No additional per-utterance shift is applied. This avoids silently undoing or duplicating the dataset authors' global alignment.

## 6. Data handling and privacy

- The analyzer reads speaker and utterance identifiers only in memory to pair files and group utterances within speaker.
- It does not export transcripts, normalized text, gender or raw speaker IDs.
- Pair keys are salted with an ephemeral random salt and are not stable across runs.
- By default, only aggregate alignment and RDM summaries are written. Per-pair derived features require an explicit `--write-pair-features` flag and should be kept local.
- No original audio is bundled in this package.
- The dataset has no documented emotion annotations in its schema. Build 13 does not infer emotional states, classify speakers, or perform speaker identification. It measures sensor-response properties only.

## 7. Empirical status and limitations

The 2.7 GB Zenodo record could not be downloaded from this environment because external DNS/network access is unavailable. A network-enabled downloader is included and defaults to the held-out test archive. The archive MD5 is used as an accidental-corruption/integrity check, not as a cryptographic authenticity guarantee. Therefore:

- no TAPS utterance was decoded in this run;
- no real acoustic/throat RDM correlation is reported;
- no claim about emotional response is made;
- the included smoke-test metrics are synthetic and are clearly labelled as such.

Additional limitations:

1. The common-band RDM is a deliberately restricted projection, not a full equivalence between the sensors.
2. TAPS consists of read speech in a controlled recording environment; it is not an emotional-prosody dataset.
3. High-frequency and unvoiced information can be absent or attenuated in the throat channel. The two channels should not be expected to be identical.
4. The residual alignment estimator is a diagnostic, not a replacement for the paper's preprocessing procedure.
5. The permutation null tests utterance pairing within a speaker; it does not establish a universal cross-modal invariant.

## 8. Reproduction

```bash
python -m unittest discover -s tests -v
python scripts/fetch_taps.py --split test --output data/raw
python scripts/analyze_taps.py \
  --root data/raw/TAPS_data_test/test \
  --split test \
  --output reports/taps_test \
  --max-speakers 10 \
  --max-utterances-per-speaker 100 \
  --permutations 99
```

The test archive is approximately 452 MB. The full record is approximately 2.7 GB. The downloader checks the published MD5 before extraction and rejects archive paths that escape the destination directory.

## 9. Build 14 direction

After the held-out TAPS results are available, compare the resulting throat/acoustic response signatures with a genuinely paired mechanical plate/microphone experiment such as the PMA monitoring recordings. Keep these physical domains separate, compare their relational structures only after calibration and pair provenance are established, and retain explicit shuffled-pair controls. Emotional labels, if ever studied, require a separate dataset with appropriate annotations; they cannot be inferred from this corpus.
