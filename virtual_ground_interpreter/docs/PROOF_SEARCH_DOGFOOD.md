# Proof-search dogfooding: finite theorem-shaped workloads

## Purpose and status

This experiment applies the current VGI Ground, observer, and partial predictive
relation interfaces to three structures that occur in mathematical proof and
algorithm search:

1. Boolean-cube influence, a finite subfamily of the Aaronson–Ambainis setting;
2. bounded CNF prefix search, with an intentionally missing transition;
3. finite \(k\)-Clique extension search.

The workloads are deliberately finite. They test VGI's current state/action
abstraction, equivalence refinement, witness/blocker semantics, and compression
of future behavior. They do not prove the general theorems, establish
asymptotic algorithms, or replace a proof assistant's kernel.

Run the reproducible package example from this directory:

~~~bash
python examples/run_proof_search_dogfood.py
~~~

The experiment was designed after reviewing the November 2026 Aaronson–Ambainis
proof, the November 2026 \(k\)-Clique hypothesis refutation, and the October
2026 ETH claim. The example uses no data or proof artifact from those
manuscripts; it extracts small structures VGI can represent.

## Results to expect

### Boolean-cube influence

The script enumerates every Boolean truth table on the three-dimensional cube,
computes its exact Walsh/Fourier degree, selects the 68 nonconstant functions
of degree at most two, and constructs a Ground with eight vertices and three
coordinate-flip actions. The observed edge output is the absolute discrete
derivative (zero or one).

For this finite family, all selected functions have a nonzero coordinate
influence. VGI computes observer-relative refinements of the edge-output
behavior through horizons one and two. This is a direct representation of
the cube graph and local influence observations, but not the global weighted
inequalities, routing lemmas, arbitrary dimension, or bounded real-valued
polynomials required by the theorem.

### CNF prefix search

The five-variable example models each assignment prefix as a state. SET0 and
SET1 extend the prefix; a clause violation leads to an UNSAT sink, while a
complete satisfying assignment leads to SAT. The solution count is computed
independently by brute force.

The script restricts the Ground to states reachable from the empty prefix,
then compares their future output behavior through horizon five. It also
removes the empty-prefix SET1 transition and compares the empty prefix with
the prefix "0": the pair is equivalent at horizon zero, unresolved at horizon
one with a structured missing-edge blocker, and distinguishable at horizon
two when a known continuation supplies a witness.

This is a small but important demonstration of the three-valued relation:
missing evidence is not a negative result, and a concrete distinguishing
witness can resolve a pair even when a different action remains unknown.

### \(k\)-Clique extension search

The script constructs a deterministic eight-vertex graph and represents each
reachable clique candidate as a state. Actions attempt to append a vertex.
An incompatible extension enters a DEAD sink; a completed four-clique enters
FOUND. The number of four-cliques is also counted independently.

The predictive quotient identifies states with the same future behavior
under the declared candidate-vertex actions and one observed output channel.
The subset states are explicitly enumerated, so this is a redundancy and
representation experiment, not a better \(k\)-Clique algorithm.

## What the experiments reveal about VGI

### 1. Behavioral compression is directly useful for search histories

Different prefixes, partial assignments, or partial graph constructions can
have identical future observable behavior under a fixed action alphabet.
VGI's horizon-indexed quotient identifies those redundancies without requiring
all histories to remain separate.

The equivalence is always observer- and horizon-relative. A pair that looks
equivalent under a short horizon can become distinguishable after another
action or a longer continuation. It must not be treated as an unconditional
identity between the underlying mathematical objects.

### 2. Missing evidence has operational value

The CNF experiment shows that unresolved is not a synonym for false. A missing
tactic result, unrun branch, timeout, or unobserved proof obligation should
not be recorded as a failed proof. A later concrete witness may distinguish
two states without inventing the missing transition.

### 3. Complete and partial Grounds have very different costs

Inspection of the current implementation shows two distinct refinement
paths:

- The complete-Ground refinement computes a signature for each state from its
  selected action outputs and successor classes. Its expected work per horizon
  is \(O(|S||A|)\) with hash-table signatures.
- The partial-Ground refinement compares unordered state pairs so it can
  preserve equivalent, distinguishable, or unresolved statuses plus blockers
  and witnesses. Its work is \(O(H|S|^2|A|)\) through horizon \(H\), and
  retaining each horizon's pair statuses can require \(O(H|S|^2)\) memory.

The second path is the price of richer partial-evidence semantics in the
current implementation. It is likely to become the limiting factor for large
proof/search Grounds. This is a concrete optimization target: develop a
conservative, partial-aware partition/refinement algorithm or sparse blocker
representation that retains the three-valued guarantees without eagerly
storing every pair.

### 4. Active attention is not yet integrated with incomplete Grounds

The current active-attention planner evaluates the exact contextual quotient,
whose signature builder resolves every selected state/action edge. A missing
or ambiguous transition therefore prevents the current attention scorer from
working directly on a partial Ground. The existing inquiry path also depends
on the complete contextual quotient.

This leaves a gap between VGI's partial relation and its active
measurement-selection tools. A useful next step is a partial-aware attention
planner that ranks specific missing or ambiguous state/action cells by
expected reduction in unresolved pairs per declared measurement cost. The
current AttentionCandidate adds an action or channel globally; it does not
yet express “measure this action at this state”.

### 5. Proof search needs AND/OR and typed semantics

A tactic application can generate several subgoals that must all be proved.
That is an AND-branch or hyper-transition, not simply an ambiguous choice of
one successor. The current TransitionObservation supports one known target or
multiple alternative outcomes, but does not express a bundle of jointly
required successor obligations.

A proof-search Ground should eventually represent:

- a proof state including the complete local context, metavariables,
  environment/import fingerprint, options, and assumptions;
- a tactic/lemma application as an action;
- a complete ordered or canonically normalized bundle of resulting subgoals
  and side conditions;
- distinct evidence statuses for kernel-checked success, a candidate tactic,
  a rejected tactic, timeout, and an unattempted branch;
- an AND/OR proof hypergraph, not merely a deterministic one-successor orbit;
- a final proof certificate checked by Lean or another trusted kernel.

VGI would then manage the search-state space, compare and compress equivalent
obligations, and choose probes. The external proof kernel—not VGI's quotient or
transition interpreter—would remain the authority that accepts a theorem.

## Implications for optimization and complexity

The experiments separate three jobs that are often conflated:

1. Search-space generation: create candidate assignments, partial graphs,
   proof states, or tactic branches.
2. Behavioral reduction: merge states only when their future behavior is
   equivalent under an explicit observer and horizon.
3. Proof or algorithm verification: check a theorem, algorithm, or result
   with an appropriate formal kernel or independent reference.

VGI currently contributes most strongly to the second job. It does not remove
the cost of generating a huge state space, and its partial pairwise refinement
can itself become expensive. The finite clique model illustrates this:
behavioral classes can be far fewer than the generated state candidates, but
the example has already explicitly enumerated the subsets.

The recent ETH and \(k\)-Clique results are about precise asymptotic bounds and
global algorithmic transformations. VGI's present \(\mathbb Z/8\mathbb Z\)
output channels, finite explicit state vocabulary, and one-target transition
model do not express the tensor contractions, interpolation bounds, weighted
graph-pattern sums, or asymptotic quantifiers in those proofs.

Likewise, continuum PDE arguments, functional inequalities, and infinite
dimensional spaces in Navier–Stokes and local smoothing are outside the
current finite Ground contract.

## Recommended next architecture

The strongest next step is not to turn VGI into another Lean. It is to build a
ProofGround adapter and proof-search fabric that can ingest proof states and
proof traces from a trusted assistant, represent AND/OR subgoal structure,
and use VGI's observer-relative refinement and attention to manage the search.

That work should be staged:

1. Import a finite proof-state trace with exact environment/context
   fingerprints and independent kernel result.
2. Add a typed proof-obligation identity and canonical, scope-aware
   normalization; never merge solely by a surface goal string.
3. Add a hyper-transition or AND/OR representation for tactics yielding
   multiple subgoals.
4. Make active attention partial-aware so it can select the next missing
   state/action observation.
5. Reduce repeated proof obligations and retain shortest counterexample or
   tactic witnesses.
6. Export the candidate proof term to Lean and require kernel acceptance.

This uses VGI as a navigation and structural-memory layer around proof
exploration. It does not weaken the distinction between observation, candidate
interpretation, admitted transition, and verified realization.
