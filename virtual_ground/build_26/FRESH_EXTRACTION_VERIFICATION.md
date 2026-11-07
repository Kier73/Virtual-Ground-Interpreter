# Fresh Extraction Verification

The final package was extracted into a new directory and verified independently of the working source tree.

| Check | Result |
|---|---:|
| Build 26 package manifest entries | 169 / 169 verified |
| Embedded original Build 24 manifest entries | 39 / 39 verified |
| Build 24 tests | 17 / 17 passed |
| Build 25 tests | 34 / 34 passed |
| Build 26 tests | 27 / 27 passed |
| Build 24 experiment runner | Exit 0 |
| Build 25 experiment runner | Exit 0 |
| Build 26 experiment runner | Exit 0 |

Total test cases executed: **78 / 78 passed**.

The exact logs are in `verification/`. The Build 24 original manifest is verified relative to `notes/build24_recovery/`. The original Build 24 ZIP is preserved at `notes/build24_recovery/BUILD_24_ORIGINAL_ARCHIVE.zip`.
