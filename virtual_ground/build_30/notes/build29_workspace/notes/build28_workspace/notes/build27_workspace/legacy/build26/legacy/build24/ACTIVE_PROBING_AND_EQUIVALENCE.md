# Active Probing and Predictive Equivalence

## Observation table

Build 24 uses an L*-style observation table for deterministic Mealy behaviour. Access prefixes represent histories that may reach predictive states. Distinguishing suffixes are experiments that test how those histories respond to future actions.

For access prefix `s` and suffix `e`:

\[
T(s,e)=Y(se)_{>|s|}
\]

The row is the collection of those future responses. Identical rows form a provisional predictive equivalence class.

The learner checks:

- **closedness:** every one-action extension is represented by an existing row;
- **consistency:** histories with equal rows have equal one-action outputs and equivalent successors;
- **bounded conformance:** the learned machine is tested against all action words up to a stated depth;
- **counterexample refinement:** the suffix beginning at the first mismatching output is added as a new distinguishing experiment.

## Probe selection

For a current set of candidate access histories `H`, candidate probe `w` partitions those histories by observed future output. The score is:

\[
score(w)=\frac{H(Y_w\mid H)}{c(w)}
\]

where `H` is Shannon entropy over the empirical response partition and `c(w)` is the declared probe cost.

The decision-tree builder applies a chosen probe, extends each candidate history by that probe (because the hidden context changes during the experiment), and selects the next probe separately for each resulting response branch.

## Delayed-six diagnostic policy

The only positive response occurs when `PROBE_A` is applied in one hidden context. The adaptive policy repeats `PROBE_A`, updating the candidate contexts after each output.

- initial predictive contexts: 6;
- worst-case probe cost: 5;
- mean probe cost under a uniform initial-context prior: 20/6 ≈ 3.333;
- ambiguous leaves: 0 within the learned six-context machine.

The learned policy is a synthetic finite fixture result. A physical probe can be irreversible or unsafe; practical probing must include safety, viability and side-effect constraints.

## Active learning versus equivalence access

The prototype uses active membership queries for observation-table cells and a bounded exhaustive conformance suite as a synthetic equivalence oracle. Real systems generally do not provide an oracle that can certify equality for all possible future experiments. In practice, equivalence evidence must be accumulated through tests, monitored predictions, counterexamples, and domain assumptions.

Build 24 reports membership, probe-selection, conformance and certificate query counts separately. Its conformance horizon is always explicit.
