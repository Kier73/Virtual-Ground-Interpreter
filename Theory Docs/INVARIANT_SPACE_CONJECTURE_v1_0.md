# Invariant Space
## Central Conjecture, Mathematical Core, and Research Program

**Document type:** Research conjecture and working specification  
**Revision:** 1.0 — consolidated through the v1.3 formal-core work  
**Date:** 28 October 2026  
**Status:** Hypothesis-led; core generic Lean statements are drafted but have not yet been kernel-checked in the authoring environment.

---

## Executive statement

The project aims to discover a useful invariant structure for things that can be described—objects, states, processes, rules, observations, observers, transformations, and histories—without choosing a final coordinate system or a single universal distance in advance.

The central intuition is that **the space is not primarily a container filled with points. It is the invariant structure of distinctions and relationships that remains when representations change.** Coordinates are finite descriptions of those relationships. Distances, paths, folds, and topology are derived instruments for different questions, not assumptions that must all be reduced to one geometry at the outset.

The proposed method is iterative:

1. declare what is being observed and what must be preserved;
2. construct equivalence classes of states that the current observations cannot distinguish;
3. encode those classes with sufficient summaries;
4. preserve all alternatives that remain consistent with incomplete or noisy evidence;
5. use transformations, paths, and costs to investigate movement through the structure;
6. choose new measurements that separate competing explanations;
7. refine the representation only when a new context demonstrates that it is insufficient;
8. prove local preservation and global reconstruction where the assumptions permit it.

The intended result is a **hierarchy of context-indexed representations**, with an explicit account of what each layer preserves, what it discards, how it can be refined, and what is still unknown.

This is a research conjecture, not a claim that a universal semantic metric or a unique final geometry has already been found.

## 1. The intuition to retain

Several intuitions from the conversation have become useful hypotheses when translated into testable language.

### 1.1 The space itself may be the invariant relational structure

Instead of imagining a pre-existing Euclidean container, begin with the relationships that survive admissible changes of description. A representation may change its spelling, coordinate system, internal state labels, or computational organization while preserving the relevant observations.

What remains invariant under those changes is a candidate description of the space's structure.

This does **not** mean every relationship is invariant under every transformation. The admissible transformations and the preserved properties must be declared. A transformation that preserves behavior may fail to preserve textual similarity; a transformation that preserves a metric may change the coordinate values.

### 1.2 Knots and folds may be observational phenomena

A sensor projects a potentially rich state into a smaller observation. Different states may produce the same output. This is a *fold* of that observation map, not necessarily a knot or singularity in the underlying space.

A fold can be resolved when another sensor or a future experiment distinguishes the states. If no allowed observation distinguishes them, they belong to the same equivalence class for the current observational purpose.

Thus, the same pair of states can be equivalent to one sensor and distinguishable to another. This is not inconsistency; it is a statement about the scope of observation.

### 1.3 Time may belong to the state, the path, or the observation protocol

A changing system can be studied through states and transitions. The same state can occur at different times, and the same observed value can arise from different internal states.

We should distinguish:

- **state:** the information needed to characterize the system at a stage;
- **event:** an occurrence, represented for example by `(state, time)`;
- **trajectory:** an ordered sequence or continuous path of states;
- **time-dependent law:** a transition rule whose behavior depends on time or phase;
- **observation history:** the sequence of outputs exposed by a sensor.

Absolute time should not be included as a coordinate automatically. It is required when it changes the predictions or distinctions the model must preserve.

### 1.4 Empty space is unresolved possibility, not a blank known to be nothing

A region can be unoccupied by known objects but compatible with all current constraints. It can also be unreachable under a selected operation system, unresolved due to noisy or incomplete observations, or forbidden by the model's constraints. These are different statuses.

The map should preserve the distinction between:

- observed/occupied states;
- feasible but not yet observed states;
- unresolved sets of possible states;
- states unreachable under a specified set of operations;
- states ruled out by explicit constraints.

A feasible candidate is not proof that a corresponding semantic object exists in reality. It means only that the current evidence has not ruled that candidate out.

---

## 2. The central conjecture

### Conjecture IS-0 — A refinable invariant relational atlas

For a useful class of describable systems, there exists a progressively refinable family of representations indexed by declared observation contexts such that:

1. each representation preserves exactly the distinctions required by its declared contexts;
2. adding contexts can refine, but never merge, distinctions already established;
3. a target property can be reconstructed from a representation whenever it is constant on that representation's equivalence classes;
4. local summaries can reconstruct a global result when every factor is computable from the summaries in its declared dependency scope;
5. incomplete observations preserve a feasible set or distribution of candidate states rather than forcing an unsupported point estimate;
6. new observations can be selected by their ability to distinguish remaining candidates;
7. the relational structure can be compared across domains through explicit structure-preserving maps, without requiring their raw coordinates or sensor formats to match.

The ambition is that these representations can form an *invariant relational atlas*: a hierarchy of overlapping, task-relevant coordinate systems whose compatibility relations are explicit and whose refinement is driven by counterexamples and new measurements.

**Scope warning:** IS-0 is not established. Items 1–3 are straightforward abstract results once definitions and assumptions are supplied. Item 4 requires locality and factorization assumptions. Item 5 requires a clear uncertainty model. Item 6 depends on a declared decision criterion. Item 7 is the difficult cross-domain hypothesis. The conjecture's nontrivial content is whether this architecture remains useful and compact for rich real-world domains, not whether one can always encode a finite set with unique labels.

### Falsifiable form

The practical conjecture is weakened or refuted for a target domain if repeated experiments show that:

- the useful relationships cannot be captured by any stable declared family of contexts;
- compact summaries consistently fail on held-out contexts and refinement approaches full raw-state enumeration without compensating benefit;
- no meaningful structure-preserving maps transfer between domains beyond trivial relabelling;
- active observations cannot improve candidate discrimination under any justified query-cost model;
- the proposed geometric or topological features are unstable under admissible changes of representation.

A trivial encoding that stores the entire original object is always available for finite data. It does not count as success unless it gives useful preservation, generalization, organization, or computational leverage.

---

## 3. Core mathematical objects

### 3.1 State domain

Let `X` be the domain of states or objects under study. It may be a finite set, a countable set of descriptions, a state space of a dynamical system, or a domain built from products of local components.

The present theory should not assume that every describable thing has a unique intrinsic encoding. An object may have many descriptions, and a description may omit facts about its referent.

### 3.2 Observation contexts

Let `C` be a family of contexts. A context can be a sensor, query, experiment, transformation, task, test input, observer protocol, or relation that interrogates a state.

For a deterministic context `c`, define its observation function

\[
o_c:X\to Y_c.
\]

For partial observations, an observation may be absent. Absence must be represented as missing data, not silently identified with a real output such as zero. A typed form is

\[
o_c:X\to \operatorname{Option}(Y_c).
\]

For bounded uncertainty, observations can be represented as sets of compatible outputs or intervals. For stochastic sensors, use a likelihood or conditional distribution `P(y | x,c)`. These semantics are not interchangeable and must be selected explicitly.

Let `A ⊆ C` be the active context family for a particular task.

### 3.3 Contextual equivalence

For deterministic, fully observed contexts, define

\[
x\sim_A y
\iff
\forall c\in A,\; o_c(x)=o_c(y).
\]

This says that `x` and `y` are indistinguishable under the declared active contexts. It does not assert that they are identical in every possible sense.

The relation is an equivalence relation:

- reflexive: `x ~A x`;
- symmetric: `x ~A y` implies `y ~A x`;
- transitive: `x ~A y` and `y ~A z` imply `x ~A z`.

The equivalence classes form the quotient `X / ~A`, which is the canonical representation of distinctions observable under `A`.

If `A ⊆ B`, then

\[
x\sim_B y\implies x\sim_A y.
\]

More contexts may split a class but cannot merge states that were already distinguishable. The partitions form a refinement hierarchy ordered by context inclusion.

### 3.4 Observation signatures

The signature of a state relative to `A` is

\[
\sigma_A(x)=\big(o_c(x)\big)_{c\in A}.
\]

Equality of signatures is equivalent to contextual equivalence:

\[
\sigma_A(x)=\sigma_A(y)\iff x\sim_A y.
\]

The signature is an exact code for the declared observational quotient. It may be expensive or infinite if `A` is large. It is a specification baseline, not necessarily a practical compressed representation.

### 3.5 Summary and sufficiency

A summary is an encoding

\[
q:X\to Q.
\]

The summary is sufficient for contexts `A` if

\[
q(x)=q(y)\implies x\sim_A y.
\]

Equivalently, equal summary codes may never merge states that an active context distinguishes. A summary may distinguish more states than the contexts require; sufficiency alone does not imply minimality or compression.

Given any existing summary `q`, define its context refinement as

\[
q'(x)=\big(q(x),\sigma_A(x)\big).
\]

This retains all distinctions already carried by `q` and adds the distinctions required by the active contexts. It is the minimal refinement of `q` with respect to those contexts in the sense of the induced partition—not necessarily the shortest code in bits or the cheapest code to compute.

### 3.6 Exact reconstruction theorem

Let `F:X→Z` be a target property. It is reconstructible from `q` precisely when it is constant on every fibre of `q`:

\[
q(x)=q(y)\implies F(x)=F(y).
\]

Then there exists a decoder `d:Q→Z` such that

\[
F(x)=d(q(x))
\]

for every represented state `x` (decoder values for unattained codes are irrelevant or explicitly defaulted).

This is the cleanest general statement of the project's compression requirement: **a representation need not preserve everything; it must preserve everything required by the declared target.**

---

## 4. Local-to-global reconstruction

A global structure may be composed from local components and relations. Let a configuration be

\[
X=(X_1,\ldots,X_n),
\]

and let each factor `f_j` depend only on a declared scope `S_j ⊆ {1,…,n}`. The scopes form a hypergraph: variables are vertices and factor scopes are hyperedges.

For each component `i`, let `q_i(X_i)` be a local summary. A sufficient local summary for a factor must preserve that factor's output under every combination of other scope variables that the model permits.

If each factor can be reconstructed exactly from the summaries within its scope, then a deterministic aggregate of those factors can also be reconstructed exactly, provided the aggregation operation is itself specified and compatible with the summaries.

Abstractly, if

\[
f_j(X_{S_j})=\tilde f_j(q_i(X_i):i\in S_j)
\]

for every admissible local configuration, and the global target is

\[
F(X)=G\big(f_1(X_{S_1}),\ldots,f_m(X_{S_m})\big),
\]

then

\[
F(X)=G\big(\tilde f_1(q_{S_1}),\ldots,\tilde f_m(q_{S_m})\big).
\]

This is an exact local-to-global reconstruction statement. The assumptions matter: undeclared dependencies, stateful side effects, stochastic correlations, or factors that depend on omitted context can break it.

### Computational consequence

A factor's result should be cached under the summaries of the variables in its actual dependency scope, not the entire global summary tuple. This allows reuse when unrelated parts of the configuration change. Cache keys must include all information that genuinely affects the factor, including relevant time, context, parameters, and uncertainty protocol.

Correctness and speed are separate objectives. A sufficient summary can still yield no computational savings if the quotient is nearly as large as the raw state space, if the factor scopes are global, or if cache overhead dominates.

---

## 5. Distance, trajectories, and geometry

The project should not define one universal semantic distance until experiments reveal a justified candidate. Maintain distinct measurement families first.

### 5.1 Distance profiles

Given anchors `A={a_1,…,a_n}` and a declared distance `d`, a point's profile is

\[
\Phi_A(x)=\big(d(x,a_1),\ldots,d(x,a_n)\big).
\]

Profiles encode relationships to reference points rather than assuming axes. A finite anchor set can fail to distinguish two states. More anchors may refine the representation.

For a genuine metric `d`, the full distance profile `x ↦ d(x,·)` preserves the metric under the supremum norm. This is a standard metric-geometry construction, not a claim that semantic distance itself has already been found.

For a one-point extension of a metric space with anchors `a_i`, a proposed profile `r_i=d(x,a_i)` must satisfy

\[
|r_i-r_j|\le d(a_i,a_j)\le r_i+r_j.
\]

Such constraints describe feasible positions; they do not prove that every feasible position corresponds to an existing object.

### 5.2 Keep different notions of distance separate

Possible measurements include:

- observation discrepancy under a selected sensor;
- edit or description cost;
- behavioral difference under input sequences;
- shortest transformation path cost;
- time or resource cost;
- a family/vector of sensor discrepancies;
- uncertainty between feasible state regions.

They can disagree legitimately. Keep a profile

\[
\mathbf D(x,y)=(d_1(x,y),\ldots,d_k(x,y))
\]

until a calibrated scalar combination is justified by a task, data, or theorem.

A path-cost model may be directed and may assign infinite cost to unreachable states. A symmetric metric has stronger axioms. Do not force directed operational cost to behave like symmetric semantic similarity.

### 5.3 Folds and trajectories

Let the system dynamics be

\[
x_{t+1}=T_{u_t}(x_t),\qquad y_t=h(x_t),
\]

where `u_t` is an input, `x_t` the internal state and `y_t` the observation.

A sensor fold occurs when `h(x)=h(y)` for distinct states. A history signature over a chosen horizon records outputs under an input protocol. Additional time steps or alternative inputs may distinguish the states.

For continuous dynamics, state-coordinate changes should transform the dynamics, sensor, and any metric together. An unchanged coordinate-independent relationship—not an unchanged numerical coordinate—is the desired invariant.

Treat an event as `(state,time)` only when temporal occurrence itself matters. For time-varying laws, augment the state by phase/time or use an explicitly non-autonomous transition model.

### 5.4 Topology and empty regions

Topology should be inferred from stable neighborhoods and reachability rather than drawn by hand. Candidate feasible regions, disconnected components, holes, and boundaries are measurements to test, not decorations.

Distinguish an unoccupied feasible region from a forbidden state, a state unreachable by a chosen operation library, and a state never probed. Under finite measurements, the absence of an observation does not establish absence of a state.

---

## 6. Uncertainty and active measurement

### 6.1 Feasible sets

Given data `D` and a model class `M`, define

\[
\Omega(D)=\{m\in M:m\text{ is compatible with all observations in }D\}.
\]

For interval observations, compatibility is defined by the interval constraints. Missing data adds no constraint. Inconsistent observations yield an empty feasible set; the system should report the conflict rather than invent a compromise unless an explicit noise model calls for one.

A feasible set is the correct output when evidence does not identify one state. The set's structure can itself be informative.

### 6.2 Choose a measurement

A query `h` partitions the currently feasible candidates according to its possible outcomes. Two criteria should be kept distinct.

**Worst-case reduction** chooses a query to minimize the largest surviving candidate set:

\[
h^*\in\arg\min_h\max_y |\Omega_{h,y}|,
\]

where `Ω_{h,y}` is the compatible subset after outcome `y`. Query cost can be added explicitly when known.

**Expected information gain** is appropriate only when a probability model over candidates and sensor outcomes is justified:

\[
I(M;Y\mid h)=H(M)-\mathbb E_Y[H(M\mid Y,h)].
\]

Candidate counts are not automatically Shannon entropy. Without a defensible prior, report set sizes and worst-case guarantees instead of inventing probabilities.

For noisy sensors, the query model must include observation likelihoods or bounded outcome sets. A query that is best under exact observation may not be best under noise.

---

## 7. Information theory and compression

Several information-theoretic tools apply, but they measure different things.

- **Shannon information** quantifies uncertainty relative to a probability distribution.
- **Algorithmic information** studies description/program length for individual objects.
- **Minimum Description Length** balances model complexity against residual description length.
- **Rate-distortion theory** studies the trade-off between encoding rate and a declared distortion measure.
- **Contextual quotient size** counts distinguishable classes under a chosen observation family.

Do not collapse these into one quantity without an explicit model.

A fixed finite-bit code cannot losslessly represent arbitrarily many states. An address is not automatically a compression. The practical target is a finite and stable *coordinate schema* whose codes can grow in precision or complexity when needed.

One possible engineering objective is

\[
\min_q\; L(q)+\lambda C(q)+\mu R(q)
\]

subject to the summary being sufficient for a declared context family. Here `L(q)` is code length, `C(q)` is construction/inference cost, and `R(q)` is a stated robustness or uncertainty penalty. The terms and weights are design choices, not universal constants. In experiments, report the individual dimensions before selecting any combined objective.

Shared summaries and interpolation may lower the cost of exact global evaluation in particular algebraic systems. They do not imply a universal speedup: the summary must preserve every needed dependency, the transformation must satisfy its degree/structure constraints, and interpolation or reconstruction must remain affordable.

---

## 8. Proposed order of operations

This order is intended to prevent circular modelling and preserve falsifiability.

### Phase 0 — Declare the question

State the target property or task. “Preserve meaning” is too broad by itself. Write down what would count as two states behaving equivalently for this experiment.

### Phase 1 — Define the domain and observation contract

Specify states, admissible inputs, sensors/contexts, output types, missing-data semantics, and uncertainty assumptions. Keep representations distinct from referents when necessary.

### Phase 2 — Build the exact observational quotient

For small finite domains, compute signatures and equivalence classes exhaustively. This gives a ground-truth baseline for that declared context family.

### Phase 3 — Search for sufficient summaries

Find compact encodings that preserve the quotient's distinctions. Measure class count, bit length, computation cost, and dependency scope separately.

### Phase 4 — Challenge the summary

Hold out contexts, generate adversarial states, and search for pairs merged by the summary but separated by a declared or newly discovered relation. Keep the smallest counterexample.

### Phase 5 — Refine minimally

Add only the signature components needed to split the conflicting states. Re-test old contexts to ensure previously preserved relationships remain preserved.

### Phase 6 — Establish local-to-global conditions

Represent dependency scopes explicitly. Prove or test that each local factor is reconstructible from its scope summaries before asserting that the global result is reconstructible.

### Phase 7 — Add trajectories, costs, and distances

Once the observations are stable enough, define operational transitions and costs. Test directedness, triangle inequalities, isometry under coordinate changes, path sensitivity, and sensor disagreement. Do not assume one scalar metric must explain all observations.

### Phase 8 — Map feasible and empty regions

For noisy or partial evidence, retain compatible sets. Distinguish feasible, unobserved, inaccessible-under-current-operations, and constraint-violating states.

### Phase 9 — Select the next observation

Use minimax query selection by default when only a candidate set is justified. Use expected information gain only with an explicit probability model. Include query cost and noise where known.

### Phase 10 — Test cross-domain transfer

Apply the same proof architecture to different domains (for example, polynomials, finite-state systems, continuous dynamics, and relational factor graphs). The raw encodings need not match; test whether the invariant statements, refinement rules, and reconstruction conditions transfer.

### Phase 11 — Formalize the stable core

Encode definitions and general theorems in Lean. Keep machine-checked theorems distinct from finite program tests, simulations, empirical findings, and conjectures. Store assumptions and dependencies next to each result.

---

## 9. Proposed conjectures and proof obligations

### Conjecture IS-1 — Context hierarchy

For every declared context family, observational equivalence induces a quotient; larger context families induce refinements. The quotient/signature construction is the correct baseline against which all compressed representations should be tested.

**Status:** Elementary theorem under the deterministic observation definitions. Generic Lean proof source drafted; machine-check status pending.

### Conjecture IS-2 — Sufficient representation criterion

A summary supports exact reconstruction of a target property if and only if that property is constant over the summary's fibres.

**Status:** Elementary set-theoretic result. Included in the formal-core draft; Lean check pending.

### Conjecture IS-3 — Contextual refinement is a controlled repair

If a summary fails on a new context, augmenting it with the necessary observed signature yields a sufficient refinement while preserving its old distinctions. A minimum class refinement is possible; minimum bit-length encoding is a separate optimization problem.

**Status:** Defined and tested on finite examples. The general statement and code-length optimization should remain distinct.

### Conjecture IS-4 — Local summaries support exact global reconstruction

For a relational system whose factors have known scopes, if every factor is exactly reconstructible from the summaries on its scope, then the specified global aggregate is reconstructible from those summaries.

**Status:** Conditional theorem target. Requires exact scope declarations, deterministic or explicitly probabilistic semantics, and a specified aggregation rule.

### Conjecture IS-5 — Active refinement can control ambiguity

Given a finite feasible model set and a collection of queries with known outcome maps, selecting a query by worst-case partition size can reduce worst-case ambiguity. Under an explicit prior and noise channel, expected information gain supplies a complementary criterion.

**Status:** Exact finite query calculations tested. No universal claim that a greedy query is globally optimal over multi-step policies.

### Conjecture IS-6 — A useful invariant atlas transfers across domains

Some domains may admit a hierarchy of compact context-indexed summaries, structure-preserving mappings, and local-to-global reconstruction rules that remain useful across more than one representation domain.

**Status:** Open research hypothesis. This is the deepest claim in the program. It needs independent domains, held-out evaluations, adversarial tests, and explicit criteria for what counts as useful transfer.

---

## 10. What would count as progress?

A result should be labelled according to its evidence class:

1. **Definition:** establishes vocabulary and scope, not an empirical fact.
2. **Theorem (proved):** follows from stated assumptions with a complete proof.
3. **Machine-checked theorem:** compiled and verified by the specified proof assistant and libraries.
4. **Finite exhaustive result:** holds for every state in a declared finite model class.
5. **Property test:** holds for tested samples, not all possible cases.
6. **Empirical finding:** measured on a stated dataset or observation protocol.
7. **Conjecture:** a falsifiable claim awaiting stronger evidence.
8. **Design hypothesis:** a proposed engineering strategy whose utility remains to be measured.

A good benchmark should include positive and negative results, the raw corpus, random seeds where applicable, counterexamples, runtime and memory, and the exact definitions of all metrics. Passing tests demonstrates that code agrees with the tests; it does not establish the universal conjecture.

### Immediate formal obligations

1. Compile and kernel-check `InvariantSpace/Core.lean` with its declared Lean toolchain.
2. Audit theorem assumptions, especially classical choice/default values and correctness on attained codes.
3. Extend the model to product configurations and explicit local scopes.
4. Prove a local factor-reconstruction lemma and derive a global aggregate theorem.
5. Add a finite certificate format that a small checker can validate independently of the search procedure.

### Immediate experimental obligations

1. Generate relational hypergraphs with known ground-truth contexts.
2. Learn summaries using only training contexts.
3. Evaluate on held-out contexts and unseen configurations.
4. Record counterexamples and minimal refinements.
5. Compare raw enumeration, factorized evaluation, neighborhood caching, and summary-conditioned evaluation separately.
6. Introduce noisy and partial observations only with explicit semantics; never convert missing data to a numeric zero.
7. Replicate the same questions in a structurally different domain before claiming cross-domain invariance.

---

## 11. Key reference implementation patterns

These snippets are schematic Python. They clarify the algorithmic contract; they are not a replacement for the Lean specification.

### Contextual equivalence

```python
def equivalent(x, y, active_contexts, observe):
    for context in active_contexts:
        ox = observe(context, x)
        oy = observe(context, y)
        if ox != oy:
            return False
    return True
```

### Signature refinement

```python
def signature(x, active_contexts, observe):
    return tuple(observe(c, x) for c in active_contexts)

def refine(old_code, x, active_contexts, observe):
    return (old_code(x), signature(x, active_contexts, observe))
```

`None` should mean missing only if the observation contract declares it as missing; if `None` is a legitimate result, use a separate tagged type.

### Feasible set under partial or bounded evidence

```python
def compatible(model, observations):
    for item in observations:
        if item.is_missing:
            continue
        prediction = model.predict(item.context)
        if not item.accepts(prediction):
            return False
    return True

feasible = [m for m in candidate_models if compatible(m, observations)]
```

An empty feasible set is a diagnostic: the data/model assumptions conflict. It should not silently trigger an arbitrary best-fit point.

### Minimax query selection

```python
def worst_case_size(query, feasible_models):
    groups = partition_by_outcome(feasible_models, query)
    return max((len(group) for group in groups.values()), default=0)

best_query = min(queries, key=lambda q: worst_case_size(q, feasible_models))
```

A real implementation should include query cost, stochastic outcomes, and stopping conditions explicitly.

### Scoped caching

```python
def factor_value(factor, full_state, scope, cache):
    local_key = tuple(full_state[i] for i in scope)
    key = (factor.id, factor.parameters, local_key)
    if key not in cache:
        cache[key] = factor.evaluate(local_key)
    return cache[key]
```

The key must contain every dependency and no omitted state variable may influence the result. If time, random state, external resources, or context changes the output, those are dependencies too.

---

## 12. Final working position

The safest present formulation is:

> **Invariant Space is a proposed hierarchy of context-indexed relational representations. It discovers and preserves distinctions through observation, stores unresolved alternatives when the evidence is insufficient, derives paths and distances only under explicit operational assumptions, and uses counterexamples to refine summaries. Its strongest near-term mathematical target is to prove when local summaries preserve global properties; its long-term conjecture is that useful portions of this architecture transfer across domains without a predetermined universal coordinate system.**

The intuition remains that the space might be the invariant structure itself. The disciplined method is to test that idea through equivalence, refinement, reconstruction, topology, and measurable prediction—without claiming that the final shape is already known.
