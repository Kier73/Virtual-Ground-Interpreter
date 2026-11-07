# Virtual Ground Identification

## From supplied ground to inferred ground

Build 21 demonstrated navigation when the ground's rules are given. Build 22 reverses the direction: infer a useful operational description from controlled interventions and observations.

The proposed object is not a compressed snapshot of the observed trajectory. It is a candidate generative rule set whose predictions can be challenged by further observations.

## Ground hypothesis

A ground hypothesis contains structural rules and parameters sufficient to predict state transitions:

\[
G_h=(S_h,A_h,T_h,I_h,E_h)
\]

where \(S_h\) is its state domain, \(A_h\) the available operations, \(T_h\) its transition rule, \(I_h\) its invariants and \(E_h\) its exogenous forcing law.

For the Flow-2 discovery fixture, the hidden parameter vector is:

\[
\theta=(C,I,D,Q,P)
\]

The ground also specifies how the state is observed under a chosen observer:

\[
y=O(s)
\]

## Identification versus navigation

These are distinct compiler tasks:

\[
\operatorname{Identify}(O,\mathcal H,\mathcal E)
\rightarrow (\hat G,\mathcal U,\kappa_I)
\]

\[
\operatorname{Navigate}(\hat G,O,J,C,s)
\rightarrow (\pi,\kappa_N)
\]

Identification proposes a ground and uncertainty record. Navigation uses a selected ground, observer, intention and resource profile to synthesize a policy.

A useful end-to-end Virtual Layer interpreter would need both, plus a validation stage that can reject or revise the inferred ground.

## Active experiment loop

1. Maintain a candidate set or posterior over ground hypotheses.
2. Generate candidate probes from controllable initial conditions, operations and sensors.
3. Predict each candidate's observable result.
4. Score probes by expected information gain and resource cost.
5. Execute the selected probe against the system.
6. Eliminate or reweight candidates according to the observation.
7. Stop only when task-relevant distinctions are resolved and independent validation succeeds, or report unresolved ambiguity.

## Information gain

For hypotheses \(H\), probe \(e\) and observation \(Y_e\):

\[
IG(e)=H(H)-\mathbb E_{Y_e}[H(H\mid Y_e)]
\]

The implemented exact deterministic/equal-prior case simplifies to the entropy of the output partition. Future versions should support nonuniform posterior weights, stochastic transitions and noisy sensors.

## The Virtual Ground as a productive description

This operational interpretation retains the source document's emphasis on a generative, task-dependent description rather than minimum-size compression. A useful ground should generate the transformations needed for an intention, preserve the invariants that validate them and expose enough information for an observer to navigate.

A ground should therefore carry more than a prediction score. It should provide:

- state and operation semantics;
- invariants and admissibility constraints;
- environmental and controlled variable classifications;
- observer maps and observability limits;
- resource-aware probe design;
- version identity and migration rules;
- independent validation evidence.

## Inference limits

A finite candidate set can be exhaustively separated without proving it contains the real system. An alternative model may agree on all observed probes and diverge elsewhere. This is why held-out interventions and open-world hypothesis expansion are essential.

A single anomalous observation must not automatically trigger a new ground version. Sensor error, hidden state, delayed effects, model misspecification and actual law revision can produce similar residuals. Build 22 uses a deliberately conservative illustrative rule: quarantine one conflict and require two distinct probes that a common revised model explains before proposing a version shift. This is not a statistically calibrated detector.
