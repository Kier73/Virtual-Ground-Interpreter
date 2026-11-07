# Build 22 — Active Discovery of Virtual Grounds

## Summary

Build 22 reverses the Build 21 compiler problem. It asks whether an observer can infer a generative operational ground by selecting observations and interventions that reveal the underlying transition logic.

- Candidate grounds: 32.
- Candidate probe catalogue: 324.
- Active identification: all 32 in-family candidates reduced to one in two calibrated probes.
- Mean active probe cost: 6.375.
- Passive comparator: 12-step HOLD trajectory; no candidate fully identified; mean residual candidates: 2.
- Ground revision: one anomaly quarantined; two independent contradictions explained by a common revised model produce a revision proposal, never automatic commit.
- Regression suite: Build 20 and Build 21 retained.

All results are synthetic and deterministic.

## 1. Why reverse the problem?

Build 21 supplied a Virtual Ground, observer and intention, then compiled a verified navigation policy. Build 22 instead asks the observer to infer the ground's rules from the behaviour it can observe.

This is closer to a general Virtual Layer interpreter: it must discover which generative description is useful, instead of merely executing a provided description.

## 2. Candidate model family

The ground hypotheses vary across five binary parameters:

| Parameter | Alternatives |
|---|---|
| Capacity | 2, 3 |
| Inflow law | (1,0,0,1), (0,1,1,0) |
| Demand law | (0,1,0,0), (1,0,0,1) |
| Transfer quantum | 1, 2 |
| Phase stride | 1, 2 |

Therefore the candidate family contains 32 grounds.

A state is \(s=(a,b,p)\). A probe chooses a calibrated reset state, one of HOLD/A_TO_B/B_TO_A and one of TOTAL/LEVELS/FULL sensors. The catalogue contains 324 probes.

## 3. Active probing result

The learner scores each probe by expected information gain divided by resource cost. Under equal priors and deterministic predictions, the information gain is the entropy of the predicted observation partition.

Across all 32 possible true candidate grounds, the greedy adaptive method identifies the correct candidate within two probes. The mean total probe cost is 6.375 units, with range 6.0–7.5. The first probe's expected information gain is 3.75 bits. In an individual branch, realized entropy reduction can differ from expected gain: the example trace reduces the 32-model family to 2 candidates (4 realized bits), then to 1 (1 realized bit).

Default first probe:

- reset state: (2,0,3)
- action: A_TO_B
- sensor: FULL
- information gain: 3.75 bits
- probe cost: 4.0
- predicted outcomes: 14

The second probe is selected adaptively after the first observation.

## 4. Passive comparison

The passive observer receives 12 consecutive FULL observations while the system runs HOLD from (1,1,0). The mean remaining hypothesis count is 2 and no candidate is fully identified. The transfer quantum remains unknown because the transfer operation is never exercised.

Active probing does not merely gather more observations. It chooses interventions that expose otherwise dormant rules.

## 5. Observer and resource dependence

When FULL measurement cost rises to 20 units, the selected first probe changes from a full-state gate action to a lower-cost LEVELS measurement under HOLD. The experiment chosen depends on the observer's measurement price and available resources. Under this alternative profile, all 32 candidates remain identifiable, but require four probes on average at a mean cost of 26.6875 units.

## 6. Critical open-world counterexample

A constant-inflow law, excluded from the 32-model candidate family, can mimic the selected in-family model on the two adaptive discovery probes. A separate phase-1 holdout probe distinguishes them.

Thus two claims must stay separate:

- identified within the declared family;
- validated as an adequate ground for the actual system.

A singleton candidate set is not proof that the candidate family is complete. Held-out probes and hypothesis-family expansion are essential.

## 7. Ground revision

A single contradictory measurement is quarantined. A subsequent measurement consistent with the existing ground clears the conflict. Two different probes, jointly explained by one revised ground version, result in a revision candidate. Nothing is committed automatically.

This is an illustrative safeguard, not a statistically calibrated change-point detector.

## 8. Mathematical framing

Let \(\mathcal H\) be a candidate family, \(e\) a probe and \(Y_e\) its predicted observation. The posterior candidate set for exact deterministic observations is:

\[
\mathcal H' = \{h\in\mathcal H:\hat y_h(e)=y\}
\]

For a uniform prior, the implemented information gain is:

\[
IG(e)=H(Y_e)
\]

The greedy selection rule is:

\[
e^*=\arg\max_e\frac{IG(e)}{c(e)}
\]

A general implementation should support nonuniform priors, stochastic transitions, noisy observations, hidden initial states, non-resettable systems and open-world model generation.

## 9. Limitations

- synthetic, finite, deterministic test domain;
- candidate family is deliberately closed for the 32-model benchmark;
- reset and phase calibration are available and costed;
- exact candidate elimination assumes noise-free observations;
- greedy scoring is not globally optimal adaptive experiment design;
- two-conflict ground revision rule is illustrative only;
- not a physical fluid model and not an empirical sensor result.

## 10. Main conclusion

Build 22 supports a bounded claim: within a known finite model family, active interventions can reveal the transition laws that passive observation leaves hidden, and probe selection changes with observer resources. It also demonstrates why a Virtual Ground learner must retain uncertainty and validate against held-out interventions before treating an inferred ground as adequate.
