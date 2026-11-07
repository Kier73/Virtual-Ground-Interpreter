# Build 28 — Raw Event Segmentation and Operation Grammar

## Proposed objective

Build 27 still receives observation-window boundaries and tokenized low-level events. Build 28 should reduce that assumption by learning candidate event boundaries and recurring motifs from a continuous symbolic or discretized sensor stream.

## Suggested stages

1. **Boundary proposals:** identify candidate segmentation points from changes in event density, symbol transitions, signal novelty or response timing.
2. **Motif mining:** discover recurring ordered subsequences and compare them with exact-window signatures.
3. **Effect attribution:** associate a motif with observed state deltas only when its temporal location and repeated context support the association.
4. **Negative controls:** shuffle motif order, shift boundaries, insert decoy events and test whether candidate operation effects survive.
5. **Intervention:** repeat or suppress a candidate motif where safe and allowed; distinguish causal operation from correlated sensor pattern.
6. **Ground compilation:** retain multiple segmentations when evidence does not select one; do not force a single token grammar.

## Primary question

Can the interpreter discover a stable alphabet of operational motifs from continuous event streams without being given the event boundaries or action labels?

## Caution

A recurring motif is not automatically a causal operation. Timing, common causes, sensor artifacts and overlapping event boundaries can produce spurious associations. The next build should preserve candidate segmentations and test their stability under perturbation.
