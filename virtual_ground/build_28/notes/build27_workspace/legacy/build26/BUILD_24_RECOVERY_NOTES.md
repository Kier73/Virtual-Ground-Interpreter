# Build 24 Recovery Notes — Embedded for Continuity

Build 26 includes the complete Build 24 source, tests, reports, specifications, documentation and original ZIP archive. This note is the short orientation layer; the exact original artifacts are preserved under `notes/build24_recovery/`, with an executable copy under `legacy/build24/`.

## 1. What Build 24 established

Build 24 removed the explicit hidden phase/mode label from the learner's input. The learner received only action/output traces through a deterministic resettable interface. It inferred the minimal predictive context machine supported by the supplied action alphabet, output channels and finite conformance horizon.

The hidden generator was a deterministic Mealy-style process:

\[
z_{t+1}=\delta(z_t,a_t),\qquad y_t=\lambda(z_t,a_t)
\]

The learner did not receive `z`, its cardinality, or a list of candidate hidden states.

## 2. Predictive equivalence

Two histories were treated as equivalent when every future action word produced the same future output sequence:

\[
h_1\equiv h_2\iff\forall w\in A^*,\quad
Y(h_1w)_{>|h_1|}=Y(h_2w)_{>|h_2|}
\]

The learned states therefore represented observer-relative predictive equivalence classes, not a claim about the physical ontology of hidden states.

The learner used an L*-style observation table with access prefixes `S`, distinguishing suffixes `E`, and rows:

\[
\operatorname{row}(s)(e)=\operatorname{output}(se)[|s|:]
\]

It refined the table through closedness, transition consistency, and counterexamples. A counterexample contributed the suffix beginning at the first mismatching output.

## 3. Verified observer quotients

| Fixture | Hidden modes in test oracle only | Learned predictive contexts |
|---|---:|---:|
| Coupled six / parity sensor | 6 | 2 |
| Coupled six / residue-3 sensor | 6 | 3 |
| Coupled six / joint sensors | 6 | 6 |
| Delayed six | 6 | 6 after refinement |
| Aliased six | 6 | 3 |
| Unobservable eight | 8 | 1 |
| Partial four | 4 | 4 |

The parity and modulo-three sensors observe different quotients. Their joint observation distinguishes all six modes because residues modulo 2 and 3 jointly identify a value modulo 6. Six physical modes can also collapse to three or one predictive contexts when the available observer cannot distinguish them.

## 4. Evidence horizon and delayed counterexample

For the delayed-six fixture, a one-context model passes all conformance tests through depth five. At depth six, the word `HOLD^5 PROBE_A` exposes a delayed signal and becomes a counterexample. The learner then refines the predictive state partition to six contexts.

A finite conformance depth is an explicit evidence limit, not a proof of global equivalence.

## 5. Active probes and compilation

Build 24 included a cost-aware distinguishing-probe selector and adaptive diagnostic tree. It also tested whether a learned action induces a single cycle over the learned contexts. If every action is a constant stride in that phase coordinate, the compiler emits a modular phase program:

\[
z'=(z+\Delta(a))\bmod n
\]

Otherwise, it retains a finite predictive automaton. Invertibility is tested, never presumed.

## 6. Exact limitations to retain

Build 24 assumed:

- a finite known action alphabet (`HOLD`, `PROBE_A`, `PROBE_B`);
- selected observation channels supplied by the interface;
- deterministic exact outputs;
- reproducible reset to a fixed hidden initial context;
- a finite bounded-state teacher for these experiments;
- a finite conformance horizon and bounded learner budgets.

It did **not** infer arbitrary raw sensor segmentation, unknown action alphabets, continuous latent variables, stochastic dynamics, nonstationarity, or the true physical hidden-state count when modes were observationally equivalent. Its active probe score was a bounded empirical information heuristic, not a globally optimal risk-sensitive controller.

## 7. Build 24 to 25 to 26 continuity

- **Build 24:** resettable latent-context discovery; predictive quotient learning; delayed counterexample refinement; modular-phase or finite-automaton compilation.
- **Build 25:** consumes the Build 24 predictive machine and tracks an unknown initial predictive context online. It supports partial/asynchronous sensor channels, per-source clocks, explicit event identity, safe-probe suggestions, contradiction quarantine, bounded memory and ground-version proposals. It does not learn a new transition law online.
- **Build 26:** removes the requirement for a precompiled complete machine at ingestion time. It incrementally builds a partial predictive transition structure from a continuing stream. Unknown edges remain unknown; collisions may force a longer history horizon; contradictions and budget exhaustion remain visible.

## 8. How to rerun the preserved Build 24 work

From the Build 26 package root:

```bash
python legacy/build24/run_build24.py
python -m unittest discover -s legacy/build24/tests -v
```

The Build 24 original ZIP is also preserved at:

`notes/build24_recovery/BUILD_24_ORIGINAL_ARCHIVE.zip`

For complete original documents, reports and source, inspect:

`notes/build24_recovery/`

The exact source is also staged for the legacy regression path at:

`legacy/build24/`
