# Build 25 — Non-Resettable Online Virtual Ground Tracking

## Result

Build 25 adds a continuous-stream runtime to the predictive Virtual Ground learned in Build 24. The running system is not reset to a known initial state. The tracker begins with a belief over every predictive context in the compiled machine, refines that belief using incoming actions and partial sensor observations, and preserves contradictions rather than silently restarting.

**Primary suite:** 28 / 28 tests passed.  
**Inherited Build 24 suite:** 17 / 17 tests passed.  
**Evidence class:** synthetic deterministic finite-state streams and calibrated-clock fixtures. No physical sensor or TAPS recordings were processed.

## What is new

1. Unknown initial context: `B_0 = Q` unless an externally justified prior is supplied.
2. Streaming update: actions advance all live hypotheses; observed output channels filter them.
3. Asynchronous sensor delivery: channel observations may arrive before or after their action record and out of order across action steps. Hypotheses retain expected outputs until the corresponding step is complete.
4. Contradiction quarantine: if no live history explains an observation, the tracker freezes and records evidence. It does not reset its belief automatically.
5. Risk-aware probe selection: one-step output partition information is scored against action cost and side-effect risk.
6. Local-clock discipline: each source retains its own sequence and timestamp. Cross-source joining uses explicit step/event identity; raw timestamps are never treated as a shared clock.
7. Bounded online memory: pending histories, completed-event cache, audit ring, source-event ring and clock-anchor window are bounded.
8. Ground version monitor: independent contradictions can create a revision proposal, never an automatic commit.

## Belief update

For a deterministic predictive Mealy ground `M=(Q,A,Y,δ,λ)`, the initial belief is:

\[
B_0 = Q
\]

For a fully observed event `(a_t,y_t)`:

\[
B_{t+1}=\{\delta(q,a_t):q\in B_t\land\lambda(q,a_t)=y_t\}
\]

For a partial channel observation on channels `J`:

\[
B_{t+1}=\{\delta(q,a_t):q\in B_t\land\lambda(q,a_t)|_J=y_t^J\}
\]

As sensor channels can arrive late, the implementation maintains path hypotheses:

\[
H_t = \{(q_t,\{(k,\hat y_k): k\in P_t\})\}
\]

where `P_t` is the set of action steps with incomplete observations. A late reading filters the prediction stored for its step, then all surviving paths retain their current successor state. Once all declared channels for a step arrive, that step's prediction is removed and equivalent hypotheses merge.

## Online experiment

The Build 24 `coupled_six` joint-observer predictive machine contains six observable contexts. The online test starts with all six as possible; the synthetic teacher's actual starting context is kept only in the test harness.

- Initial candidate belief: 6 contexts.
- One channel of the first action output: 2 contexts remain.
- Second sensor channel: 1 context remains.
- A second action and its asynchronously delivered sensor output preserve a single consistent context.

The test uses two action steps and deliberately delivers sensor channels out of order. The tracker requires no reset interface and has no teacher reference.

## Local clocks

Each source `s` has a local clock. An affine map may be fitted only with at least two distinct paired anchors:

\[
t_{ref}=\alpha_s+\beta_s t_s
\]

One anchor establishes neither drift nor a safe affine mapping; it is reported as `offset_only_drift_unresolved`, and conversion is refused. With paired anchors, the synthetic fixture recovers:

- sensor A: slope 1.0, intercept -10.0;
- sensor B: slope 0.5, intercept -50.0.

Events are joined by explicit action-step identity. Equal raw timestamps from unrelated local clocks do not establish correspondence.

## Probing

For each action, the scheduler partitions the current belief by predicted immediate output. Its score is:

\[
Score(a)=\frac{H(Y_a\mid B)}{c(a)+\lambda r(a)}
\]

where `c` is declared cost, `r` declared risk, and `λ` the risk penalty. Actions above a configured risk ceiling are excluded. If no safe action produces information, the scheduler declines to probe.

This is deliberately a one-step heuristic, not an optimal partially observable controller. Future information, multi-step side effects, viability constraints and uncertainty in risk estimates remain open.

## Contradiction and versioning

When no live path matches an observation:

- status becomes `contradicted`;
- the last consistent hypothesis set is preserved;
- the contradictory observation and possible outputs are retained;
- future tracking actions are rejected until an explicit review/recovery procedure is applied.

A separate monitor proposes a ground revision after a configured number of contradictions across distinct steps and actions. This is a heuristic alert, not a proof that the transition law changed. Sensor corruption, missing events, clock misalignment or an unmodelled initial mode can produce similar residuals. No revision is committed automatically.

## Memory discipline

Defaults:

- maximum 256 unresolved/prefetched action steps;
- last 128 completed steps cached for duplicate detection;
- last 256 audit records retained;
- last 512 source events and 256 unmatched events retained by the local-clock registry;
- last 64 calibration anchors retained per source.

Lifetime counters are retained separately. Older sensor events outside the duplicate window are marked stale rather than replayed as new evidence. The finite-state hypothesis count remains bounded by the predictive machine's initial candidate count in this deterministic implementation.

## Evidence boundary and limitations

Build 25 consumes a Build 24 predictive machine. It solves unknown current-context tracking after the ground exists; it does not yet learn a new transition law online without reset. The action alphabet and output-channel schema are known. Dynamics are deterministic. Sensor values are exact integers. Channel count is fixed. Timestamp calibration assumes an affine relationship over the retained anchor window. No live distributed system has been connected.

The work establishes a bounded online belief tracker and evidence discipline, not a general asynchronous sensor fusion engine or unrestricted self-learning interpreter.

## Running

```bash
python run_build25.py
python -m unittest discover -s tests -v
python -m unittest discover -s legacy/build24/tests -v
```

Standard library only; Python 3.10+.
