# Cell-specific minimax probe policies

## Purpose

Cell-specific partial attention currently scores one unknown or ambiguous
state/action cell against a finite set of counterfactual outcomes. The score is
local: it estimates the pairwise effect of resolving that cell while holding
the other cells unchanged.

That is useful for ranking, but a sequence of measurements can have structure
that a local score cannot see. Two cells can each have zero immediate
resolution value and still be jointly sufficient to classify an unresolved
pair. The minimax policy planner searches this finite composition.

## Policy structure

A policy node has two roles:

- **OR choice:** choose one candidate probe (one state/action cell, with an
  explicit method label, exact cost and declared scenario set).
- **AND branches:** preserve one child policy for every declared outcome of
  that probe.

A selected cell is measured at most once on any path. Multiple methods for
the same cell may compete, but once one method is selected all other methods
for that cell are excluded from that path. This prevents a policy from
pretending that measuring the same transition twice creates two independent
Ground facts.

The solver only accepts cells whose current status is `unknown`. A cell
already marked `ambiguous` is refused: a counterfactual singleton must not
erase existing alternatives. A new actual observation must use the normal
evidence path and ambiguity-preserving Ground revision operation.

## Objective

For Ground (G), observer (O), horizon (H), and policy (pi), let
(U(G,O,H)) count all state pairs classified as unresolved by the sparse
three-valued comparison. Equivalent pairs and distinguishable pairs are both
classified; neither is counted as unresolved.

The policy objective is lexicographic:

[
min_{pi}
left(
max_{omegainOmega(pi)} U(G_{pi,omega},O,H),
quad
max_{omegainOmega(pi)} C(pi,omega),
quad
max_{omegainOmega(pi)} N(pi,omega)
ight)
]

where:

- (Omega(pi)) is the set of declared outcome paths through the policy;
- (G_{pi,omega}) is the counterfactual Ground at the end of path (omega);
- (C) is the exact sum of selected probe costs along that path;
- (N) is the number of probes on that path.

The first coordinate minimizes the worst-branch unresolved-pair count. The
second breaks ties by minimizing worst-case exact cost. The third minimizes
the maximum number of measurements. Remaining ties use deterministic
candidate ordering.

Costs and budgets use integers or exact `Fraction` values. No floating-point
approximation is admitted. A budget constrains the cumulative cost on every
branch. Scenario weights are preserved as metadata but ignored by the
worst-case objective; this planner does not infer an expected information gain
or a likelihood model.

## Complementary-cell control

The regression fixture has two states, `a` and `b`, one observed action
`X` that produces the same output from both states, and one selected action
`Y` whose cells are both unknown.

The only unresolved state pair is `(a,b)`. A candidate probe of `(a,Y)`
alone leaves `(a,b)` unresolved because `(b,Y)` is still missing. The
candidate probe of `(b,Y)` alone has the same problem. Thus each local
single-cell score has zero guaranteed pair resolution.

The two-step policy can nevertheless measure one cell, branch on its actual
outcome, then measure the other. Once both cells are known, the pair is
classified as equivalent or distinguishable at the declared horizon. The
policy tree retains those outcomes as separate branches; it does not average
them or choose a nearest branch.

## API

```python
from fractions import Fraction
from vgi import plan_partial_probe_policy

plan = plan_partial_probe_policy(
    system,
    observer,
    candidate_probes,
    horizon=4,
    budget=Fraction(50),
    max_probes=8,
    max_states=10_000,
)

first = plan.first_probe
print(plan.worst_case_unresolved_pairs)
print(plan.worst_case_cost)
print(plan.maximum_probes_on_path)
artifact = plan.to_dict()  # includes a deterministic policy digest
```

The plan contains an immutable root node. Every nonterminal node contains a
selected `TransitionProbe` and one child branch per declared scenario.
Terminal reasons distinguish resolved, candidate-pool exhaustion, budget
exhaustion, probe-limit exhaustion, and a deliberate stop selected as optimal.
`to_dict()` preserves Ground fingerprints, exact costs, scenario metadata,
the objective and optimality scope.

The public `counterfactual_probe_ground(system, probe, outcome)` helper
constructs a new hypothetical Ground value for one declared scenario. It
never mutates the input Ground or records the outcome as evidence.

## Exactness and limits

The dynamic program memoizes by counterfactual Ground fingerprint, measured
cell set, and remaining exact budget. It explores the supplied finite
candidate methods and their declared branches. The default maximum policy
depth is 16 probes and the default exact-search state cap is 10,000. A search
that exceeds the state cap raises `PartialProbePolicyError`; it does not
return a partial result labeled optimal.

The finite search is exact over that model, not over an unenumerated physical
system. The caller's scenario set may omit real outcomes. No probability,
scenario exhaustiveness, measurement completion, receiver admission, evidence
authority, or Ground revision is inferred from this plan.

The first probe is a proposal. An execution adapter must carry it through the
ordinary dispatch, receiver-admission, raw-return, authority, application and
optional sender-acknowledgement stages. The actual interpretation must match a
declared scenario before the corresponding branch may be followed. An
out-of-set observation is model mismatch, not a nearest-neighbour branch.

## Tests

`tests/test_partial_policy.py` covers zero-local-gain composition, exact
method-cost choice, one-measurement-per-cell path constraints, branch and
weight semantics, budget and search bounds, ambiguous-cell rejection,
duplicate candidate definitions, and empty candidate pools.
