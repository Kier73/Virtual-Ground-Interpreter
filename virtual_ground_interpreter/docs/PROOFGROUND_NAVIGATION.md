# ProofGround navigation primitives

## Scope

This increment connects four capabilities that were previously separate:
sparse three-valued predictive refinement, cell-specific active attention,
exact rational/polynomial observables, and proof-search hyper-transitions.
The Lean adapter imports a normalized proof-state trace; it does not execute
Lean or independently validate kernel proof terms.

## Sparse partial refinement

The existing eager partial comparison remains unchanged. The sparse interface
builds only the definite-equivalence partition for each horizon.

At horizon zero all distinct states are equivalent under an empty observation
word. At the next horizon, a state with all selected outgoing cells known is
assigned a deterministic signature consisting of projected outputs and the
previous horizon's successor-class identifiers. Two fully observed states
share a signature exactly when they are equivalent at that horizon.

A state with a missing or ambiguous selected outgoing cell is isolated in
the definite-equivalence partition. It is not merged with another state
merely because both have similarly named blockers. Such pairs are then
resolved lazily: a concrete output or successor witness proves
distinguishability; otherwise missing, ambiguous, or unresolved-successor
blockers preserve the unresolved result.

Building the partitions takes expected \(O(HSA)\) time and \(O(S)\) working
memory per horizon, where \(S\) is the state count, \(A\) is the observer
action count, and \(H\) is the horizon. A requested pair decision costs at
most \(O(HA)\) absent cache reuse. Querying all pairs still costs quadratic
work: sparse construction makes no promise to make an all-pairs census
subquadratic.

API:
- sparse_partial_refinement_series(system, observer, max_horizon)
- SparsePartialComparison.status(left, right)
- SparsePartialComparison.witness(left, right)
- SparsePartialComparison.blockers(left, right)

## Cell-specific active attention

A TransitionProbe describes one exact state/action cell that is currently
unknown or ambiguous. Each ProbeScenario proposes a possible resolved
successor and complete output tuple. VGI builds a counterfactual Ground for
each scenario, changes only that cell, and re-evaluates comparisons involving
the source state. Pairs not containing that source state cannot be affected
by that cell, so only \(S-1\) pair decisions are needed per scenario.

If the caller supplies positive exact Fraction weights summing to one,
the scorer returns an exact expected count of unresolved pairs resolved and
an exact gain-per-cost value. If weights are absent, it reports minimum and
maximum scenario effects only. It never estimates probabilities from
observation counts, missingness, or model intuition.

These are counterfactual scores, not actual measurements and not proof that
a proposed scenario set is exhaustive. A real observation must enter the
normal evidence-admission pipeline before it can change the actual Ground.

API:
- TransitionProbe(state, action, scenarios, cost=...)
- score_partial_probe(system, observer, probe, horizon)
- rank_partial_probes(system, observer, probes, horizon)

Costs and scenario weights use exact integers or Fraction values. Floats
are rejected so binary floating-point approximations are not silently
presented as exact probabilities or costs.

## Exact typed observables

RationalValue stores normalized exact rational scalars.
ExactPolynomial stores sparse multivariate polynomials with exact rational
coefficients. Both support exact arithmetic; polynomial evaluation accepts
exact values and returns a rational result.

ExactObservableFrame attaches a named set of exact measurements to a state,
logical clock, tick and Ground fingerprint. This channel is deliberately
separate from Signal8 output tuples. Finite categorical observations keep
their existing representation; exact mathematical invariants are not
rounded, quantized or forced into \(Z/8Z\).

Available exact aggregates include sum, mean, population/sample variance and
weighted sum. Weighted expectations require explicit weights.

## AND/OR proof obligations

A ProofObligation is identified by a canonical fingerprint over:
- a structured goal expression (not a surface goal string);
- local context and assumptions;
- metavariables;
- assistant/version;
- environment, imports and options fingerprints.

A ProofHyperTransition represents one tactic application. Its subgoal IDs
are an AND-bundle: every listed obligation must be discharged. Different
hyper-transitions for the same source are alternative OR routes. Attempt
statuses distinguish candidate, elaborated, timed out and rejected tactics;
an unrecorded transition is unattempted, not a failed proof.

This is intentionally separate from GroundTransitionSystem, whose
single-successor and ambiguous-alternative model is not a proof hypergraph.

## Normalized Lean trace format

The adapter expects VGI-LeanProofTrace-1, a normalized JSON document with
one environment descriptor, keyed proof obligations, and tactic transitions.
A minimal shape is:

~~~json
{
  "format": "VGI-LeanProofTrace-1",
  "environment": {
    "assistant": "Lean",
    "assistant_version": "4.15.0",
    "environment_fingerprint": "environment digest",
    "imports_fingerprint": "imports digest",
    "options_fingerprint": "options digest"
  },
  "obligations": [
    {
      "key": "root",
      "goal": {"kind": "forallE", "type": {"kind": "const", "name": "Nat"} },
      "local_context": [],
      "metavariables": {},
      "assumptions": []
    },
    {
      "key": "base",
      "goal": {"kind": "application", "name": "base_case"}
    },
    {
      "key": "step",
      "goal": {"kind": "application", "name": "induction_step"}
    }
  ],
  "transitions": [
    {
      "source": "root",
      "tactic": "induction n",
      "subgoals": ["base", "step"],
      "attempt_status": "elaborated",
      "evidence_ref": "trace-frame-12"
    }
  ],
  "kernel_claims": ["root"]
}
~~~

The JSON expression structure is an adapter contract, not a claim that this
minimal example is a complete Lean Expr serialization. A producer must
export the full expression tree, binder/local context, metavariable state,
imports and options in a stable form. Surface strings alone are rejected as
goal identities.

Raw kernel claims in the trace are retained under an explicitly untrusted
field for audit. They do not change kernel_status. Only a separate
VerifiedKernelReceipt supplied by an upstream Lean/kernel integration can
produce kernel_accepted or kernel_rejected. The receipt is bound to an exact
obligation ID and environment fingerprint, and includes a proof-term
fingerprint, checker identity/version and verification reference.

The receipt object is a trust boundary: this package checks consistency and
binding, but does not cryptographically authenticate the upstream checker
or run Lean. A production adapter must validate the receipt against the
actual checker result (and ideally its authenticated log/signature) before
constructing the object. A claimed kernel success is never inferred from a
tactic name, an empty subgoal list, an elaborated status, or a JSON boolean.

## Deliberate limitations and next work

- This increment does not run Lean, synthesize tactics, or accept theorems.
- It does not yet implement a proof-DAG scheduler, cycle handling, proof-term
  serialization or authenticated kernel receipt verification.
- It does not collapse contextually similar proof obligations. The identity
  currently uses exact environment/context/metavariable fingerprints; any
  looser quotient must prove scope and substitution compatibility.
- Partial attention relies on a caller-supplied finite scenario set. Without
  calibrated weights it gives scenario bounds, not probability.
- Sparse partition construction reduces eager memory and work, but a caller
  requesting every pair still pays quadratic cost.
- Exact polynomials are sparse and exact, but there is not yet a symbolic
  simplifier, Gröbner basis engine, theorem prover or arbitrary expression IR.

The next useful integration is a real Lean trace exporter and authenticated
kernel receipt adapter, followed by a scheduler that chooses proof obligations
using sparse relations and partial-aware attention.
