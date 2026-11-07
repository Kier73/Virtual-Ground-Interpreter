# Next research checkpoint after Build 15

## Current state

Build 15 compares independently timed event streams through monotone correspondence, normalized event marks, interval-shape context, recurrence motifs and local-order graphs. It estimates an affine relation between clocks only after matching. Synthetic controlled performance is strong under a specific model, but no TAPS audio was processed and no empirical invariant is established.

## Next experiments

1. Run the held-out TAPS test split when the archive is available.
2. Compare mark-only, interval-only and combined matching, including shuffled-mark/order controls.
3. Add shuffled-mark and shuffled-event-order controls.
4. Sweep the RMS event detector frame size, threshold and minimum event separation; quantify graph stability, not only best-case alignment.
5. Evaluate a known-clock sensor corpus to test affine clock recovery independently from event matching.
6. Evaluate time-varying clock drift and local tempo changes to identify where a single affine map fails.
7. Compare with a second paired physical sensor domain only after independent calibration.

## Refined conjecture

A stateful structure may expose a temporal trace through the ordered event relations it produces. If observers preserve enough common structure in event marks and relative intervals, correspondence may be recovered without a shared clock coordinate. The matched graph can then support a relative clock model, rather than requiring global time as a prerequisite.

## Guardrails

- Event correspondences are inferred, not ground-truth state identities.
- The confidence score is not calibrated probability.
- Synthetic precision/recall do not predict TAPS performance.
- A successful affine fit after matching does not prove a physical synchronization mechanism.
- Failure may reflect observer event extraction, sensor transfer functions, or true process differences.
- Do not infer universal invariance from one corpus or one synthetic setup.
