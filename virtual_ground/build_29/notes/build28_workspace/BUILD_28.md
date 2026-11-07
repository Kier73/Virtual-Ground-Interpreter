# Build 28 — Boundary Discovery from Continuous Event Streams

**Research prototype · Python 3.10+ · standard library only**

## Objective

Build 27 could discover recurring operations from opaque event signatures, but the acquisition interface still supplied observation-window boundaries. Build 28 removes that assumption.

The learner receives:

- continuous ordered sequences of opaque event tokens;
- trace start and end;
- sparse state checkpoints at token offsets that are not defined as operation boundaries.

It does **not** receive operation boundaries, semantic operation names, or the hidden generator's operation catalogue. Hidden boundaries and labels exist only in the synthetic evaluator so that segmentation can be scored.

## Results

| Measurement | Result |
|---|---:|
| Training streams | 12 |
| Training tokens | 1,140 |
| Held-out streams | 5 |
| Held-out tokens | 465 |
| Recurrent motif candidates after family-wise null screen | 4 |
| Nested submotifs excluded from double counting | 4 |
| Training + held-out boundary precision | 1.000 |
| Training + held-out boundary recall | 1.000 |
| Training + held-out boundary F1 | 1.000 |
| Sparse checkpoint effect equations | 57 |
| Internal checkpoints | 179 total; 49 coincided with hidden operation boundaries |
| Held-out checkpoint deltas correct | 24 / 24 |
| Shuffled-control candidates before null screen | 42 |
| Shuffled-control candidates after null screen | 0 |
| Deliberately ambiguous segmentation fixture | Retained as ambiguous |
| Build 28 tests | 21 / 21 |
| Inherited Builds 24–27 tests | 108 / 108 |

All results are from controlled synthetic streams. They validate the finite algorithmic fixture, not natural-language understanding, arbitrary raw-sensor segmentation, or universal operation discovery.

## Method

### 1. Recurrent motif mining

Enumerate exact contiguous n-grams of lengths 2–4. A candidate must recur at least five times and across at least three traces. Ordered token identity is retained.

### 2. Nested-motif audit

A shorter motif whose every occurrence is embedded in a longer frequent motif is recorded as a nested submotif and excluded from segmentation. This prevents counting `pulse,edge` and `edge,tail` as separate operations when all observed occurrences belong to `pulse,edge,tail`.

### 3. Boundary inference

For every stream, locate occurrences of learned motifs and solve a weighted non-overlapping interval problem. Background tokens can remain unassigned. A top-k dynamic program preserves alternative parses. If the top two parses have sufficiently similar scores, the stream is marked ambiguous; it is not silently forced into one segmentation.

### 4. Ordered-shuffle negative control

Raw recurrence is not sufficient. Frequent tokens can create accidental frequent n-grams after shuffling. Build 28 permutes tokens independently within each trace, preserving each trace's token inventory and length while destroying local order.

A candidate survives only when its observed occurrence count exceeds the maximum count of **all candidate motifs** across all sampled null permutations. The true motifs survived with 39–89 occurrences, compared with a family-wise null maximum of 12. The separate shuffled corpus generated 42 raw candidates, but none survived its own screen (family-wise null maximum 37). This is a conservative finite maximum-statistic screen, not a general guarantee against all false discoveries; the empirical tail fraction is resolution-limited by the 31 permutations.

### 5. Effect attribution from sparse checkpoints

For each adjacent checkpoint pair, count fully contained inferred motif segments. If a checkpoint bisects a candidate segment, that interval is excluded rather than misattributed.

The observed vector change is modelled as:

\[
\Delta x_k=\sum_j n_{kj}\,\beta_j
\]

where `n_kj` is the number of occurrences of motif `j` in checkpoint interval `k`, and `beta_j` is its unknown effect vector.

Build 28 solves this small system using exact rational row reduction. Effects are compiled only if each output dimension is uniquely determined and yields integer coefficients. Underdetermined or inconsistent systems remain unresolved.

### 6. Partial executable ground

The JSON ground contains recurrent signatures, support counts, inferred effect vectors, evidence scope, and a structural fingerprint. Unknown signatures return `unknown_operation`. An effect supported by the finite training observations is still labelled `inductive_candidate`, not a universal law. Recurrent motifs with zero measured effect are preserved as `recurrent_zero_effect_motif`, not promoted into state-changing operations.

## Discovered synthetic motifs

| Opaque signature | Inferred vector effect | Classification |
|---|---:|---|
| `pulse, bend, tail` | `[-1, +1]` | Candidate operation |
| `pulse, edge, tail` | `[+1, 0]` | Candidate operation |
| `ramp, tick` | `[0, +2]` | Candidate operation |
| `hum, click` | `[0, 0]` | Recurrent zero-effect motif |

The four exact signatures were discovered from continuous streams. There were no action names or operation boundaries in the learner input. Of 179 internal sparse checkpoints, 49 (27.4%) coincided with a hidden operation boundary in the evaluator; the remaining 130 did not. The learner received only checkpoint offsets and state vectors, never the hidden boundary labels.

## Ambiguity and negative controls

A separate fixture contains recurrent `a,b` and `a,b,c` patterns. In a target stream `a,b,c`, the learner retains the alternative parses `ABC` versus `AB + background C`, and marks the segmentation ambiguous. Its checkpoint effect is not used for learning.

The shuffled control produces 42 raw frequent candidates, illustrating why support count alone is unreliable. After the same maximum-statistic permutation filter, none remain.

A token insertion inside a known exact motif prevents exact matching. This is intentional conservative behaviour in this build; approximate edit-distance motif discovery remains future work.

## Important limitations

1. Tokenization is supplied. This build does not discover symbols from raw voltage, audio, vibration or images.
2. Trace start/end are supplied. Segment boundaries *inside* each trace are inferred.
3. Motif discovery uses exact contiguous n-grams up to length four, not arbitrary context-free or neural grammars.
4. Exact motif matching is brittle to inserted, deleted or substituted tokens.
5. The checkpoint/effect model is additive and finite-dimensional. Nonlinear interactions and state-conditioned operation laws may require a richer equation grammar.
6. Checkpoint intervals that intersect a candidate segment boundary are excluded, which is safe but can reduce available evidence.
7. Repeated temporal association is not proof of causation. Interventions, ablations or controlled replay are still needed.
8. The synthetic evaluator knows the hidden boundaries; the learner does not. The perfect scores are limited to this controlled fixture.
9. No physical sensor recordings or TAPS audio were processed.

## Interpretation

Build 28 demonstrates a finite but important transition: the interpreter no longer needs operation boundaries to be supplied. It can identify recurrent ordered motifs, propose their boundaries, retain ambiguous segmentations, infer effects from sparse asynchronous checkpoints, and compile the result into a partial executable ground.

It does not yet discover the raw event tokenization itself. That is the next layer.
