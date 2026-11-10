# Active attention planning

## Purpose

The relational atlas describes what a declared observer can distinguish. Active attention asks a different question:

> Given a current observer, a finite set of possible new observations, their costs, and a task horizon, which capabilities should be acquired next?

The first implementation is deterministic and finite. It chooses between two candidate kinds:

- adding an action that can be used as a probe;
- revealing another output channel.

Candidate costs are caller-supplied relative units. They are not interpreted as measured latency, energy, risk, or money.

## 1. The ambiguity objective

Let \(Q_{O,H}\) be the horizon-\(H\) predictive quotient for observer \(O\). The unresolved pair count is

\[
U(O,H)=\sum_{B\in Q_{O,H}}\binom{|B|}{2}.
\]

Each pair in the same quotient class is indistinguishable under the selected probes and channels, through the selected horizon. Every pair is initially weighted equally. A future version may accept an explicit prior over state pairs, but support counts are not treated as probabilities.

For a candidate capability \(p\), define the marginal reduction

\[
\Delta(p\mid O,H)=U(O,H)-U(O\oplus p,H),
\]

and its cost efficiency

\[
\eta(p\mid O,H)=\frac{\Delta(p\mid O,H)}{c(p)}.
\]

This is a deterministic reduction in unresolved pairs, not an expected information gain. An expectation would require a probability model over observations or candidate states, calibrated likelihoods, and a declared prior.

## 2. Greedy and exhaustive planning

The greedy planner repeatedly selects the currently available candidate with maximum \(\eta\), subject to a total cost budget. It stops when no affordable candidate has positive marginal reduction.

For a small candidate pool, the exhaustive planner evaluates every feasible subset and solves

\[
\min_{S\subseteq P} U(O\oplus S,H)
\quad\text{subject to}\quad
\sum_{p\in S}c(p)\le B.
\]

Ties prefer lower cost and then deterministic lexical ordering. The implementation caps exact search at 16 candidates by default; this is a reference baseline, not an unbounded solver.

## 3. Complementarity: why local attention can fail

The crucial counterexample has two predictive contexts, two actions \(A,B\), and two channels \(x,y\). The initial observer can use only \(A\) and see only \(x\). Both contexts produce the same value through that pair.

- Adding action \(B\) while still observing only \(x\) reveals no distinction.
- Adding channel \(y\) while still using only \(A\) reveals no distinction.
- Adding both reveals that the \((B,y)\) observation differs between the contexts.

Thus

\[
\Delta(B\mid O,H)=0,
\qquad
\Delta(y\mid O,H)=0,
\]

but

\[
\Delta(y\mid O\oplus B,H)>0.
\]

The marginal value of \(y\) increases after adding \(B\). This violates the diminishing-returns property required by standard monotone-submodular greedy guarantees. A purely local policy can therefore stop at the initial observer even when a jointly informative, affordable observation set exists.

This is not a bug in the quotient construction. It is a structural property of the observation interface: the useful signal lives at the intersection of an action and a channel. Attention is sometimes compositional rather than additive.

## 4. Positive control: delayed-six

The Build 24 delayed-six Ground provides the complementary case. With HOLD and PROBE_B visible, all six predictive contexts remain in one class. Adding PROBE_A splits them progressively by the fifth observation horizon. Here one candidate has a large positive marginal gain, so greedy and exhaustive planning agree.

The pair of controls is important:
- delayed-six demonstrates a strong individually informative probe;
- the complementary fixture demonstrates a probe interaction that defeats myopic selection.

A policy should be tested against both, not optimized on one convenient example.

## 5. Architectural consequences

The result argues against committing to greedy information gain as the universal attention mechanism. A more defensible architecture has distinct layers:

1. **Candidate generation:** enumerate actions, sensors, channels, or transformations that could be acquired.
2. **Local valuation:** calculate marginal pair separation and cost efficiency.
3. **Interaction detection:** retain zero-gain candidates when they may combine with other capabilities.
4. **Bounded lookahead:** use exhaustive search on tiny spaces, beam search or bounded-width search for larger candidate pools.
5. **Execution and verification:** acquire the selected observations, update the Ground with actual evidence, and recompute the quotient.
6. **Counterexample retention:** preserve failed predictions and revise the candidate space, not just the current score.

This separates the *attention policy* from the *perception substrate*. A sensor or intervention can be valuable only in combination with another; the planner must be able to represent that possibility.

The next computational step is a bounded beam planner with explicit interaction retention and an anytime certificate: current best objective, cost spent, explored subset count, and a valid lower bound or clearly labelled unknown optimality gap.

## 6. What this does not establish

- The objective currently counts deterministic unresolved state pairs equally.
- Costs are declared relative units, not measured latency or energy.
- Unknown or ambiguous selected transitions remain errors; they are not guessed.
- No Bayesian prior, observation likelihood, or calibrated expected information gain is inferred.
- Exact search is exponential in the number of candidate capabilities.
- The model's predictive contexts are observer-relative, not physical hidden-state identities.
- No universal intelligence, universal metric, or performance advantage is claimed.


## Joint navigation across perception and predictive spaces

The next planner treats an observer configuration and its induced predictive quotient as one search node. It expands action/channel capabilities even when their immediate marginal reduction is zero, then records the route through perception space alongside changes in the predictive quotient.

See [the joint navigation experiment](JOINT_NAVIGATION.md). The complementary-probe control is the key regression: the beam must retain both single-capability configurations and discover the two-step route to a fully separating quotient. The beam is bounded and its pruning is reported; no general optimality guarantee is claimed.
