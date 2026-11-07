# Build 05 — Active Observation and Intention

## Motivation

Build 04 selected the observer map and the path in advance. It showed that different observer equivalence relations can distinguish different aspects of the same quaternion path. It did not yet model an observer choosing what to measure.

Build 05 should add an explicit probe-selection policy without changing the underlying codonic state identity.

## Candidate architecture

- **Hypothesis set:** competing structural explanations or candidate codonic models.
- **Probe library:** valid transformations, input perturbations, path segments, observer projections, and algebraic rewrites.
- **Prediction:** each candidate predicts an outcome distribution for each probe.
- **Observation:** measure the actual outcome and update candidate scores.
- **Intention:** a task-specific objective that ranks which uncertainty matters.
- **Selection:** choose the next probe to distinguish hypotheses while controlling noise and cost.

## Candidate objective functions

1. Expected information gain / entropy reduction.
2. Expected separation between predicted response signatures.
3. Robustness under codon registry renaming.
4. Stability under observer coordinate changes.
5. Noise sensitivity and measurement cost.

A generic selection objective could be:

\[
P^*=\arg\max_{P\in\mathcal P}
\left[\lambda_I IG(P)+\lambda_D Sep(P)-\lambda_N Noise(P)-\lambda_C Cost(P)\right].
\]

This is only a design template; the terms and scales need operational definitions before the objective is meaningful.

## Important constraints

- Do not treat a SHA-derived identifier as a semantic metric.
- Do not collapse S³ distance, SO(3) rotation distance, Hopf-base distance, and response-signature distance.
- Track uncertainty and measurement noise separately from model innovation.
- Record the observer map and intention/task with every result.
- Use negative controls and randomized probe order.
- Preserve exact algebraic semantics when changing codon aliases.

## Proposed first experiment

Create a small set of candidate codonic structures with deliberately different hidden fibre states but overlapping Hopf-base observations. Give an active observer a limited probe budget. Compare its selected probes against:

- random probe selection;
- a fixed predetermined probe sequence;
- an oracle that knows the hidden state.

Metrics: correct model discrimination, information gain, number of probes to resolve ambiguity, stability under alias renaming, and sensitivity to injected noise.

## Exit criteria

Build 05 is useful if active selection consistently distinguishes candidates with fewer probes than random selection, without confusing coordinate renaming with structural change. The test must include cases where no available probe can distinguish two candidates; a good observer should report unresolved ambiguity rather than invent certainty.
