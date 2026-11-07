# Ground Versioning and Contradiction Handling

A contradiction means the current predictive ground cannot explain the observed event under its live belief. It does not by itself prove the ground has changed.

Possible causes include:

- a genuine transition/output law change;
- an unknown context omitted from the ground;
- missing or reordered action records;
- sensor corruption or calibration error;
- an incorrectly joined asynchronous observation;
- a changed observer/output schema.

Build 25 freezes the tracker on the first contradiction and preserves the current ground fingerprint, action, observation, possible outputs and source. A separate monitor may propose a revision after independent conflicts across distinct steps and actions. It never commits a revision.

The threshold is a transparent deterministic heuristic. It is not a statistically calibrated change-point test and must not be interpreted as causal proof.
