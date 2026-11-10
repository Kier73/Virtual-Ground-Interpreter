# Joint perception-space and predictive-space navigation

## Purpose

The relational atlas established that an observer configuration induces a predictive quotient. Active attention added candidates and costs. This increment connects them into one bounded search process.

Every search node carries two linked coordinates:

\[
N=(O,Q_{O,H}),
\]

where:
- \(O=(A_O,C_O)\) is the current perception configuration: available action probes and visible output channels;
- \(Q_{O,H}\) is the predictive quotient induced by that configuration at horizon \(H\).

A search edge adds one observation capability and recomputes the quotient. Thus the planner navigates a space of ways to perceive while measuring the resulting structure of the world-model.

## 1. The two spaces

### Perception configuration space

Given a base observer \(O_0\) and a finite candidate set \(P\), each configuration corresponds to a subset \(S\subseteq P\):

\[
O_S=O_0\oplus S.
\]

A candidate can add an action probe or reveal an output channel. Its cost is declared by the caller. The current capability space is a finite subset lattice over the supplied candidates, with cost-admissible edges.

### Predictive quotient space

Every valid configuration induces:

\[
Q_{O_S,H}=Q/\!\equiv_{O_S,H}.
\]

The quotient gives the predictive distinctions visible under that configuration. A more capable observer refines or preserves the quotient; it cannot merge a pair that was already distinguishable.

One perception configuration can lead to the same quotient as another while retaining different future capabilities. This is why search nodes must not be deduplicated by quotient score alone. Their future candidate sets differ.

## 2. Joint navigation

The beam planner uses a node containing:
- observer action and channel selections;
- selected observation capabilities;
- cumulative cost;
- current quotient and unresolved state-pair count;
- the route that produced the configuration;
- the next candidate index, which gives a canonical subset construction order.

At each depth the planner:
1. expands each retained observer configuration with every remaining affordable candidate;
2. derives the new predictive quotient;
3. records the observer and quotient coordinates, including zero-gain expansions;
4. ranks configurations by unresolved state pairs, cumulative cost, route length, and deterministic capability ordering;
5. retains at most the configured beam width.

The best result is selected from every generated node, including a node not retained for further expansion. The search reports all visited configurations and which ones survived the beam. This makes pruning visible rather than silently erasing a possible route.

The planner stops when it reaches a fully separating quotient, exhausts its frontier, or reaches the depth bound. Its zero-ambiguity stop is safe for the current objective because observation costs are strictly positive and zero unresolved pairs is the lower bound.

## 3. Complementary-probe result

On the two-state complementary fixture, the base observer can use action A and see channel x. It has one unresolved pair.

The candidate action B alone still yields one unresolved pair. Revealing channel y alone also yields one unresolved pair. The joint planner nevertheless retains both one-step configurations and reaches:

\[
O_0=(\{A\},\{x\})
\]

\[
O_1=(\{A,B\},\{x\})
\]

\[
O_2=(\{A,B\},\{x,y\})
\]

The associated quotient path is:

\[
1\text{ unresolved pair}
\rightarrow
1\text{ unresolved pair}
\rightarrow
0\text{ unresolved pairs}.
\]

This is the essential shape of the joint search: a move can make no immediate change in the predictive quotient yet be necessary in perception space for a later move to expose a distinction.

The current test uses beam width two so both single-capability configurations survive the first expansion. The search records make this explicit. A beam of width one may or may not preserve the useful branch depending on deterministic tie order; bounded search is not an optimality guarantee.

## 4. Route data

The output includes both a compact final plan and a detailed search record.

Each route step records:
- candidate added;
- complete action/channel observer configuration after the addition;
- unresolved pairs before and after;
- resulting quotient class count;
- cumulative cost.

Each visited configuration records its depth, selected candidates, observer, cost, quotient class count, unresolved pair count, and whether it was retained in the beam.

This is more informative than returning only the final observer. It exposes the actual path through representation space and the induced changes—or lack of changes—in predictive space.

## 5. What the model suggests

This architecture separates two questions that are often conflated:

- *What is the system's predictive structure under the current model?*
- *What changes in our ability to see that structure if we acquire a new observation capability?*

The next observation is not selected only because it immediately improves the current model. It can be selected because it opens a route to a later observation that does.

A further extension could treat candidate generation itself as part of the search: propose new probes or sensors from counterexamples, then evaluate them as new directions in perception space. That would close a loop between model construction, attention planning, and verified observation.

## 6. Limits

- The perception space is finite and defined by caller-supplied candidate capabilities.
- The predictive Ground is deterministic and finite.
- Search uses a bounded beam and may prune a useful configuration.
- The objective counts unresolved state pairs equally; it is not probabilistic information gain.
- Candidate costs are relative declarations, not measured latency, energy, or risk.
- The resulting predictive contexts are observer-relative, not claims about physical hidden-state identity.
- No universal state-space, unrestricted synthesis, or performance advantage is claimed.
