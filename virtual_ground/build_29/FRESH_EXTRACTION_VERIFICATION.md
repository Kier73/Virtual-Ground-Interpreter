# Build 29 Fresh-Extraction Verification

## Package check

- The Build 29 ZIP was extracted into a separate directory.
- All 324 entries in the pre-final `MANIFEST.sha256` verified against the extracted package.
- The ZIP archive passed `unzip -t` with no compressed-data errors.

## Executable checks from the extracted copy

| Suite | Tests | Result |
|---|---:|---|
| Build 29 | 24 | Passed |
| Build 28 | 21 | Passed |
| Build 27 | 30 | Passed |
| Build 26 | 27 | Passed |
| Build 24 | 17 | Passed |
| Build 25 | 34 | Passed |
| **Combined** | **153** | **Passed** |

Build 28's own inherited regression runner was invoked from the extracted Build 29 package. It re-extracted the original Build 28 archive and reran the Build 24–27 chain.

## Embedded recovery checks

- The inspectable Build 28 workspace manifest verified all 289 listed files.
- The embedded original Build 28 ZIP passed archive integrity testing.
- A separate extraction of the embedded original Build 28 ZIP verified all 289 entries in its original manifest.
- The Build 28 regression runner completed successfully from the embedded original archive.

## Raw-WAV CLI check

The extracted `analyze_wav.py` successfully processed the bundled synthetic stereo PCM16 fixture:

- sample rate: 8,192 Hz;
- channels: 2;
- samples per channel: 6,336;
- selected nominal boundaries: 9;
- opaque event tokens: 10.

## Scope

All checks use synthetic signal fixtures. No TAPS or physical sensor recordings were analyzed. The final Build 29 package manifest is regenerated after this verification note is included; its file count is recorded in the final handoff.
