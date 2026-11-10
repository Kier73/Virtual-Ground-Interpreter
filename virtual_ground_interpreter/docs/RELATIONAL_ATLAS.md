# Observer-relative relational atlas

## Purpose

This experiment turns the observer-relative ideas in the development throughline into a finite, executable contract.

A system does not need a complete map of every possible state before it can be navigated. It needs a declared set of distinctions, a way to ask questions of the system, and a transition rule that says what follows from each permitted question. The resulting map is deliberately partial in scope: it describes what the current observer can distinguish over a declared horizon.

The experiment uses **predictive contexts** rather than asserting that its states are physical hidden states. A predictive context is a state of the model sufficient to predict the selected outputs under the selected actions.

## 1. Observer contract

For a deterministic finite transition system

\[
\mathcal T=(Q,A,C,\delta,\lambda),
\]

an observer context is

\[
O=(A_O,C_O),
\]

where \(A_O\subseteq A\) is the set of actions the observer can use as probes and \(C_O\subseteq C\) is the set of output channels the observer can perceive.

The observer projection is part of the mathematical input, not an informal afterthought. Two observers may examine the same Ground and induce different valid equivalence relations. An omitted action is not silently treated as a failed action; it is outside that observer's contract. An unknown or ambiguous selected transition remains an error and is never filled in.

The current implementation accepts deterministic, known transitions for every state/action pair selected by the observer. It can operate on an otherwise partial Ground when the selected action subset is complete.

## 2. Horizon-indexed equivalence

Let \(P_h(q)\) be the predictive signature of state \(q\) at horizon \(h\). The base case has no observations:

\[
P_0(q)=\star.
\]

For the next horizon:

\[
P_{h+1}(q)=
\left(
\left(
\pi_{C_O}(\lambda(q,a)),
P_h(\delta(q,a))
\right)
\right)_{a\in A_O}.
\]

Here \(\pi_{C_O}\) projects the output vector onto the channels visible to the observer. The action order is fixed by the observer contract.

Define

\[
q\equiv_{O,h}r
\iff P_h(q)=P_h(r),
\qquad
Q_{O,h}=Q/\!\equiv_{O,h}.
\]

This is exact bounded predictive equivalence: two contexts are in one class precisely when no selected action sequence of length at most \(h\) distinguishes their selected output traces.

The construction is iterative partition refinement. Every new horizon can split an existing class but cannot merge two existing classes:

\[
q\equiv_{O,h+1}r
\Rightarrow q\equiv_{O,h}r.
\]

For a finite system with \(|Q|=n\), there can be at most \(n-1\) strict refinements after the initial one-class partition. Once a partition is unchanged at one step, it is stable for all later horizons under the same deterministic observer contract. A discrete partition with one class per declared predictive context is immediately stable because it cannot be refined further.

This gives the atlas a useful operational interpretation: it is not a precomputed universal coordinate system. It is a family of progressively finer maps, indexed by what is sensed and how far ahead the observer asks.

## 3. Quotient maps and transitions

For \(H\ge h\), the finer quotient has a canonical projection:

\[
\pi_{H\to h}:Q_{O,H}\rightarrow Q_{O,h}.
\]

The implementation constructs this map and verifies that each finer class lies wholly inside one coarser class.

A transition can be represented between adjacent quotient layers:

\[
([q]_{h+1},a)
\mapsto
\left(
\pi_{C_O}(\lambda(q,a)),
[\delta(q,a)]_h
\right).
\]

The signature recurrence guarantees that the projected output and target class do not depend on which representative \(q\) is chosen from \([q]_{h+1}\). This is a finite, testable structure-preservation property. It is weaker than asserting that all quotient layers are isomorphic or that they share one global geometry.

The stable quotient is especially useful: when \(Q_{O,h+1}=Q_{O,h}\), the adjacent-layer transition map becomes an ordinary transition system on the stabilized predictive classes.

## 4. Behavioral distance profile

The module also defines a distance parameterized by the same observer, an action distribution, a horizon, and a discount:

\[
D_{H,O,\mu,\gamma}(q,r)=
\frac{1}{Z_H}
\mathbb E_{w\sim\mu^H}
\left[
\sum_{t=0}^{H-1}\gamma^t
d_C(y_t(q,w),y_t(r,w))
\right],
\qquad
Z_H=\sum_{t=0}^{H-1}\gamma^t.
\]

The same action word \(w\) is applied to both contexts. The current Signal8 experiment uses the normalized cyclic metric on each selected \(\mathbb Z/8\mathbb Z\) output channel and averages over channels.

For a fixed deterministic Ground and fixed observer, action distribution, output metric, horizon, and discount, this construction is a **pseudometric**: it is non-negative, symmetric, and satisfies the triangle inequality, but distinct states may have distance zero. With positive probability for every selected action, zero distance agrees with equality of the selected output traces through the horizon. If some actions receive zero weight, the distance deliberately ignores distinctions that require them.

There is therefore no context-free scalar called semantic distance in this implementation. The meaningful object is a family of profiles with its observer, horizon, probe distribution, metric, and resource assumptions attached.

## 5. Three finite experiments

### Delayed-six predictive Ground

The Build 24 fixture is examined under two observers.

- The full observer can use HOLD, PROBE_A, and PROBE_B and can see the declared output channel. The expected partition counts are 1, 2, 3, 4, 5, and 6 from horizons zero through five. In particular, q0 and q1 remain equivalent at horizon four and split at horizon five.
- The restricted observer cannot use PROBE_A. It cannot expose the delayed positive output, so the quotient remains one class even as the requested horizon grows.

The transition model is unchanged in both cases. The difference is the observer's available probe.

### Cyclic recurrence

A four-state cyclic recurrence is evaluated with and without its phase output channel. A channel-blind observer sees one predictive class; the phase-aware observer distinguishes the four states at horizon one. The action law is identical.

### Non-bijective automaton

A three-state automaton maps left, right, and sink to sink under ERASE. A coarse output channel collapses all three contexts; a detail channel distinguishes them. The transition is many-to-one, so this is not merely a coordinate relabelling of a bijection.

Together these fixtures test temporal discrimination, observer projection, and non-bijective transition structure. They do not establish a universal atlas across arbitrary domains.

## 6. Relationship to attention and intention

In this model, attention is represented by the observer contract: which interventions are admissible, which channels are read, how observations are weighted, and how far ahead consequences are evaluated. Intention can be represented by a target predicate or a task contract that selects which distinctions matter.

A description can therefore create a *formal possibility space*: it names states or predictive contexts, permitted transformations, observations, and success conditions. The implementation can then construct and navigate that space. This is a precise computational reading of “describe what you want, and it exists.”

It is not a claim that describing an object creates its physical substrate. Whether a formal Ground corresponds to an external process remains an empirical question, answered by observations, calibration, and independent verification. The useful meta-contract is to separate (1) what the model makes representable, (2) what the observer can actually distinguish, and (3) what the external system supports.

## 7. Next experiment: active attention allocation

The next natural extension is to choose the next probe rather than merely accept a fixed observer profile. A finite policy could rank candidate actions or channels by expected reduction in unresolved state-pair ambiguity per unit cost:

\[
a^*=
\arg\max_{a\in A_{\mathrm{candidate}}}
\frac{\mathbb E[\Delta\,\text{distinguishability}\mid a]}
{C(a)}.
\]

A deterministic development version can use the number or weighted mass of state pairs split by a probe. A probabilistic version must first declare priors and calibrated observation likelihoods; it must not invent confidence from support counts alone.

A successful active-attention policy should be tested against exhaustive probe schedules on small finite grounds, with held-out contexts and costs. It should show when a probe is informative, when it is redundant, and when no available observation can resolve the current ambiguity.

## 8. Boundaries

- This module currently operates on finite deterministic predictive Grounds.
- Only selected, known transitions are used; unknown and ambiguous evidence is preserved as a hard boundary.
- Output values are currently the finite Signal8 symbols in \(\mathbb Z/8\mathbb Z\).
- The distance uses a declared metric and shared action distribution; changing either changes the profile.
- The quotient is observer- and horizon-relative, not physical hidden-state identity.
- No universal coordinate space, unrestricted task synthesis, physical signal computer, speedup, or energy advantage is claimed.
- The new tests and example runner are included as executable research artifacts; they must be run in the repository environment before their expectations are reported as passed.


## Active attention and complementary probes

The first active-attention module ranks candidate action probes and output channels by reduction in unresolved predictive-state pairs per caller-declared cost unit. It includes a greedy planner and an exhaustive subset planner for small candidate pools.

The delayed-six control shows the case where one probe is independently informative: adding PROBE_A resolves the horizon-five partition. A second two-state control shows non-additive value: an additional action and an additional channel each have zero marginal gain alone, but their combination exposes a distinguishing observation. This is a concrete reason not to assume local information gain is sufficient.

See [ACTIVE_ATTENTION.md](ACTIVE_ATTENTION.md) for the formal objective, the counterexample, and the next bounded-lookahead direction. The score is deterministic; it is not Bayesian expected information gain.
