# Build 27 — Competing Explanations and Operation Discovery

<small>Research prototype · Python 3.10+ · standard library only</small>

## 1. Objective

Build 27 addresses a crucial ambiguity in online Virtual Ground construction:

> When a current ground fails to explain an observation, did the system change, did the observer miss a relevant variable, did the sensor change, was the history too short, was the action effect unknown, or was the observation noisy?

It also begins removing the assumption that semantic operation labels are provided. Recurring low-level event signatures are discovered from observation windows and their measured effects.

Build 27 does not claim universal discovery. It produces explicit competing explanations, candidate operations, partial executable grounds and discriminating next experiments.

## 2. Main results

| Measurement | Result |
|---|---:|
| Build 27 tests | 30 / 30 passed |
| Build 26 inherited tests | 27 / 27 passed |
| Build 25 inherited tests | 34 / 34 passed |
| Build 24 inherited tests | 17 / 17 passed |
| **Combined regression suite** | **108 / 108 passed** |
| Recurrent opaque operation signatures recovered | 2 |
| Held-out operation predictions | 6 / 6 correct |
| Held-out counterexample outside the inferred constant-delta law | Correctly rejected |

All results use included synthetic integer-vector transition windows and diagnostic fixtures. No physical sensor records were processed.

## 3. Competing explanations

A conflict is not automatically a new state or ground version. Build 27 evaluates explicit candidates:

- measurement noise;
- sensor calibration shift;
- sensor remapping versus physical system change;
- insufficient observation history;
- hidden predictive variable;
- stochastic or unmodelled transition context;
- new predictive state;
- ground regime change;
- new operation candidate.

The explanation engine ranks candidates using ordinal evidence scores. These are **not probabilities**. Each candidate includes supporting evidence and a discriminating next experiment. Ground revision is never automatically committed.

### Results from diagnostic fixtures

| Fixture | Diagnostic result |
|---|---|
| One isolated spike, immediate recovery, independent channel stable | Measurement noise candidate |
| Persistent one-channel offset, calibrated reference stable | Sensor calibration shift candidate |
| Same offset without reference channel | Sensor remap vs system change unresolved |
| Collision resolved by a longer history suffix | Insufficient history |
| Collision remains at maximum tested history | Hidden predictive variable vs stochastic/unmodelled context unresolved |
| Novel observation repeated 4 times, independently corroborated, stable transition profile | New predictive state candidate |
| Persistent conflicts across 3 context-operation pairs and 2 sensors | Ground-regime revision candidate |

A longer history can yield a candidate *observed predictive factor* (such as a particular prior observation lag). This does not assert that the factor corresponds to a separate physical variable.

## 4. Discovering operations without semantic action labels

The event interface supplies an observation window and the opaque low-level event tokens recorded between the before and after observations. It does **not** supply semantic action names or a candidate action catalogue.

For each recurring exact token sequence \(m\), the learner compares:

\[
\Delta x=x_{after}-x_{before}
\]

The candidate operation effect is classified as:

| Mode | Rule |
|---|---|
| `constant_vector_delta` | Identical delta at two or more distinct pre-states |
| `state_conditioned_table` | Effects vary by pre-state, but each observed pre-state is consistent |
| `single_prestate_table` | Repeated support occurs at only one pre-state; no global law is inferred |
| `ambiguous_effect` | Same signature and same pre-state yield conflicting deltas |

Event order is retained: `("a","b")` and `("b","a")` are separate signatures. One-off signatures are not promoted to operations.

### Synthetic operation discovery

Two recurring event sequences were inferred:

- `("edge_04", "pulse_12")` → constant delta `(+1)`;
- `("ring_09",)` → constant delta `(+3)`.

The learner received 14 training windows across pre-states 0–6. Six withheld windows at pre-states 7–9 were predicted correctly. This is finite validation of these examples, not proof that the rule generalizes over all states.

A deliberately out-of-family held-out observation at state 6 contradicted a learned `+1` rule. The report records `held_out_correct: false` and recommends retaining a counterexample. This is an intended validation failure: the system must not silently change the ground to make a failed prediction disappear.

## 5. Partial executable ground

The compiled representation contains:

- observed state vectors;
- discovered opaque event signatures;
- effect mode and supporting observations;
- an observed pre-state transition table where required;
- explicit ambiguous operations;
- a structural fingerprint;
- an explicit evidence-scope declaration.

Unknown event signatures return `unknown_operation`. A contextual rule applied to an unobserved pre-state returns `unknown_precondition`. Ambiguous rules are not executable.

A constant-delta rule is only proposed after it has support at multiple distinct pre-states. Even then, it remains an inductive candidate rather than a universal law.

The structural fingerprint excludes support counts and evidence-step identifiers. Repeated confirmation of an unchanged operation therefore strengthens evidence without forcing a new ground version.

## 6. Discriminating probes

The probe selector accepts a finite set of competing hypotheses, predicted outcomes for candidate probes, and declared cost/risk profiles.

For a prior over the declared hypothesis set:

\[
IG(e)=H(H)-\mathbb E_{o\sim e}[H(H\mid o)]
\]

It ranks `IG / (cost + risk penalty)` and declines when all probes exceed the risk threshold or all candidates predict the same outcome.

The selected probe is conditional on the explicit hypothesis set. It is not a claim that the set is exhaustive or that the information gain is a world-level probability.

## 7. Critical boundaries

1. Observation-window boundaries are supplied by the acquisition interface. Raw waveform boundary discovery is not implemented.
2. Event tokens are opaque symbols, but tokenization itself is supplied.
3. The current miner groups recurring exact event-window signatures. It does not yet infer arbitrary subsequence grammars or semantic operation names.
4. State observations are finite integer vectors. Continuous latent-variable discovery is not implemented.
5. A hidden deterministic variable and stochastic transition can remain observationally equivalent.
6. A sensor remapping and a real physical state change can remain observationally equivalent without an independent calibration reference.
7. Ordinal evidence scores are not calibrated probabilities.
8. The constant-delta model can fail outside its observed region; the included held-out counterexample demonstrates this.
9. Ground revision is proposal-only. This build never automatically commits a revised ground.
10. No physical sensor data or TAPS recordings were processed.

## 8. Interpretation

Build 27's advance is a disciplined intermediate capability:

**The interpreter can keep multiple explanations alive, decide what experiment would distinguish them, identify recurring operations from uninterpreted event signatures, compile only sufficiently supported effects, and preserve unknowns when evidence is inadequate.**

This is a step toward a self-constructing Virtual Ground, not yet a general-purpose one. The remaining major gap is raw stream structure discovery: the next stage should infer event boundaries, motifs and latent variables rather than receive observation windows from its connector.
