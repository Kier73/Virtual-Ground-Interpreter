# Sources and Provenance

## Project source

`legacy/build24/` contains the complete Build 24 source package, which supplies the predictive machine consumed by the Build 25 online tracker. Build 24's own source and evidence limitations are documented in `legacy/build24/BUILD_24.md` and `legacy/build24/LEARNER_LIMITS.md`.

## Build 25 experiments

All Build 25 experiments are generated locally from the serialized Build 24 fixtures. They are synthetic and deterministic. No external dataset, TAPS recording or physical sensor is used.

## Mathematical basis

The implementation uses finite-state deterministic Mealy-machine belief filtering, set-valued state estimation, least-squares affine clock fitting from paired anchors, and Shannon entropy of predicted output partitions. The operational equations and assumptions are included in the technical documents. No claim of universal hidden-state recovery is made.
