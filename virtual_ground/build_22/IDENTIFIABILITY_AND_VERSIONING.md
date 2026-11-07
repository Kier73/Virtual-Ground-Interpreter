# Identifiability, Validation and Ground Versioning

## Three distinct claims

1. **Candidate separation:** the available probe catalogue distinguishes the models in the current candidate family.
2. **Candidate identification:** the observations leave one model in that family.
3. **Ground adequacy:** the selected model predicts independent observations and preserves the task-relevant system behaviour.

Claim 1 does not imply claim 3. Claim 2 is conditional on a closed candidate family.

## Build 22 evidence

The 32 main candidate models form 32 distinct behavioural equivalence classes under the full 324-probe catalogue. The greedy adaptive experiment selects two probes for each true in-family model and leaves one candidate.

However, an out-of-family constant-inflow law mimics the selected candidate on the two adaptive probes. A held-out phase-1 experiment distinguishes it. This is the package's central model-selection warning.

## Behavioural equivalence

Given a probe set \(\mathcal E\), two hypotheses are observationally equivalent when:

\[
h_1\sim_{\mathcal E}h_2
\iff
\forall e\in\mathcal E,\quad \hat y_{h_1}(e)=\hat y_{h_2}(e)
\]

This equivalence depends on the observer and probe set. Enlarging the probe set can split an equivalence class. Changing the observer can also split or merge what can be distinguished.

## Ground revision monitor

Build 22 demonstrates:

- single conflict -> quarantine;
- subsequent consistency with current model -> clear the conflict;
- two distinct conflicts jointly explained by a common revised hypothesis -> propose ground version change.

No automatic commit is performed.

A production detector would need probabilistic likelihoods, noise calibration, sequential testing, confidence intervals, persistence windows, multiple competing change explanations and safe rollback/migration.

## Versioning policy

A new observation is not automatically a ground revision. It may simply reveal a state previously hidden from the observer. A resource budget or sensor change likewise need not alter the ground. A revised capacity, operation rule, transition law, or environmental law may require a new version if it changes the generative transition semantics.

Version transition should preserve:

- old ground identifier and checksum;
- new ground identifier and checksum;
- changed rule set;
- compatibility mapping for states;
- unmappable states and affected invariants;
- validation probes for the revised ground;
- explicit approval before use.
