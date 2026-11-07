# Active Probing and Ground Identification

## Objective

Build 22 reverses the supplied-ground problem from Build 21. Instead of receiving a Virtual Ground and compiling a navigation policy, an observer receives a finite candidate family and selects experiments that discriminate among candidate generative laws.

The experiments in this package are synthetic, deterministic and finite. They do not establish that a real-world ground can always be uniquely identified.

## Identification object

A candidate ground is indexed by five structural parameters:

\[
\theta=(C,I,D,Q,P)
\]

where:

- \(C\): storage capacity, 2 or 3;
- \(I\): inflow schedule, one of two four-phase sequences;
- \(D\): demand schedule, one of two four-phase sequences;
- \(Q\): gate transfer quantum, 1 or 2;
- \(P\): environmental phase stride, 1 or 2.

The candidate family contains:

\[
|\mathcal H|=2^5=32
\]

All 32 parameter combinations are included with equal prior weight.

## Probe object

A probe is a calibrated reset state, an operation and a selected sensor:

\[
e=(s_0,u,O)
\]

The resettable initial reservoir levels are 0, 1 or 2, and the experimenter can wait for or identify one of four phases. The action is HOLD, A_TO_B or B_TO_A. The sensor is TOTAL, LEVELS or FULL.

The complete catalogue contains:

\[
3\cdot3\cdot4\cdot3\cdot3=324
\]

probes.

This assumes reset and phase calibration are experimentally available. Those capabilities are explicitly costed; they are not free or universal assumptions.

## Prediction and update

Every candidate predicts a deterministic observation:

\[
\hat y_h(e)=O(T_h(s_0,u))
\]

After observing \(y\), the exact, uniform-prior candidate set is:

\[
\mathcal H' = \{h\in\mathcal H: \hat y_h(e)=y\}
\]

The true candidate is never removed in the in-family experiment. If the set becomes empty, the current family is rejected for that observation rather than repaired silently.

## Probe selection

For the uniform deterministic case, the information gain of a probe equals the entropy of its predicted output partition:

\[
IG(e)=H(Y_e)=-\sum_y p(y)\log_2p(y)
\]

The greedy selection rule is:

\[
e^*=\arg\max_e\frac{IG(e)}{c(e)}
\]

with:

\[
c(e)=c_{reset}+c_{action}(u)+c_{sensor}(O)
\]

This is a cost-aware heuristic, not a proof of globally optimal adaptive experiment design. The implementation uses equal prior weights and does not yet model probabilistic observation noise.

## Passive comparator

The passive comparator performs a fixed 12-step uninterrupted HOLD trajectory from state (1,1,0), observing FULL after every step. It does not reset the reservoirs or actuate the transfer gate.

Because the transfer gate is never exercised, transfer quantum cannot be identified from this passive run. The mean residual candidate count is 2.

## Active result

Across each of the 32 possible true candidate grounds, greedy active probing reaches a singleton candidate set in two calibrated probes. Mean probe cost is 6.375 units; the minimum is 6.0 and maximum is 7.5.

The first probe under the default cost profile is:

- initial: (2,0,3)
- action: A_TO_B
- sensor: FULL
- information gain: 3.75 bits
- cost: 4.0
- predicted outcome classes: 14

The second probe is selected after observing the first outcome and distinguishing the remaining candidates.

## Observer/resource dependence

When FULL sensing becomes expensive (cost 20), the first selected probe changes to a LEVELS observation using HOLD from (1,2,3). Its information gain is 2 bits at a cost of 1.75, giving a larger information-gain-per-cost score than the default full-sensor probe under that alternative price profile.

This shows that the selected experiment depends on the observer's measurement capabilities and resource prices, not only on the underlying ground. Under the alternative profile all 32 in-family models are still identified, but the greedy method takes four probes on average at a mean cost of 26.6875 units.

## Open-world validation

The learner can identify a model only conditionally on the declared candidate family and the experiments performed. An out-of-family constant-inflow law can mimic the selected candidate on the two adaptive discovery probes. A held-out phase-1 probe distinguishes them.

Therefore a singleton posterior inside a closed family is not a universal proof of ground identity. Independent validation interventions are required. Candidate expansion must remain possible.

## Ground revision monitor

The monitor distinguishes:

1. one contradictory observation: quarantine it as a possible sensor anomaly;
2. a later observation consistent with the current ground: clear the conflict streak;
3. two distinct contradictory probes explained by a common revised model: propose a ground revision candidate.

The monitor never commits a new ground automatically. Human or higher-level policy approval and migration checks remain separate operations.

## Limitations

- finite, closed candidate family for the main identification benchmark;
- deterministic exact observations;
- known/calibrated phase at each active reset;
- reset capability assumed and costed;
- greedy information-gain-per-cost, not globally optimal design;
- one-outlier quarantine and two-conflict revision rule are illustrative safeguards, not a statistically calibrated change detector;
- no physical TAPS data or external sensor measurements used.
