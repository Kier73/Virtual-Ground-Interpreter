# Build 23 — Inductive Synthesis of Virtual Grounds

## Purpose

Build 22 selected among a declared finite catalogue of 32 candidate grounds. Build 23 reverses the framing: it receives transition records and synthesizes a generative operational description from them. It does not receive the hidden ground's parameter tuple or a list of candidate models.

The learner discovers, within an explicit bounded grammar:

- the observed state-domain capacity, with an evidence-qualified exactness flag;
- the number of observed environmental phases;
- inflow and demand schedules;
- phase-transition mapping;
- a transfer operation law depending on phase and source-level residue;
- a compositional state-update program;
- candidate variable roles and conservation residuals.

The result is serialized as an executable ground specification, not just a parameter report.

## Main result

Five independently generated synthetic grounds were learned. They include periods 4, 5 and 6; a modular arithmetic inflow schedule; an irregular phase permutation; transfer laws depending on source parity, modulo 3 and modulo 4; and lookup-table environmental schedules.

For all five cases:

- 1,930 training transitions were predicted exactly;
- 521 held-out transitions were predicted exactly;
- each dataset withheld some complete states (10, 20, 12, 17 and 18 unseen states respectively), not just action labels at otherwise observed states;
- exhaustive evaluation over the complete finite state/action domain was exact;
- the inferred mass-balance residual was zero;
- the inferred program could be serialized and reloaded as an executable specification.

| Synthetic ground | Capacity | Phase count | Training | Held out | Completely unseen states |
|---|---:|---:|---:|---:|---:|
| cycle4-constant | 4 | 4 | 235 | 65 | 10 |
| period6-modular-inflow | 5 | 6 | 510 | 138 | 20 |
| irregular-phase-source-parity | 4 | 5 | 296 | 79 | 12 |
| source-mod3-operation | 5 | 5 | 426 | 114 | 17 |
| source-mod4-operation | 6 | 4 | 463 | 125 | 18 |

The fifth ground deliberately requires source-level modulo 4. A learner restricted to modulo 3 rejects it. After the grammar is expanded to modulo 4, the induced program predicts its held-out and entire finite-domain transitions exactly. This is a bounded example of counterexample-driven grammar refinement.

## Generative update program

Let the state be `(a,b,p)`, capacity `C`, inflow `I(p)`, demand `D(p)`, and transfer quantum `Q(p,z)` where `z` is the source reservoir level modulo a discovered modulus.

For `A_TO_B`:

\[
t_{AB}=\min(Q(p,a),a,C-b)
\]

For `B_TO_A`:

\[
t_{BA}=\min(Q(p,b),b,C-a)
\]

The updates are:

\[
a'=\min(C,\max(0,a-t_{AB}+t_{BA}+I(p)))
\]

\[
b'=\min(C,\max(0,b+t_{AB}-t_{BA}-D(p)))
\]

\[
p'=P(p)
\]

The exact order and clipping semantics are part of this finite fixture's ground. The program stores rules, not every state-to-state edge. The five full domains contain 2,451 state/action transitions in total; the inducer receives 1,930 training records and validates 521 withheld transitions.

## Symbolic law grammar

Sequence laws can be represented as:

- constant;
- affine in phase;
- modular ramp;
- repeating periodic motif;
- finite lookup table;
- modular phase stride (for phase progression).

The operation law uses the smallest fully observed source-level residue modulus within the current grammar, producing a phase-by-residue table. The experiment starts with a maximum source residue modulus of 3. A mod-4 counterexample requires the grammar to be expanded to 4.

This is a bounded synthesis grammar, not unrestricted program synthesis. The state schema, action labels, integer domain, broad update family and observed phase variable are provided by the experiment interface.

## What is and is not discovered

**Discovered from transition records:** capacity lower bound, phase schedules, state-dependent transfer law within the grammar, operation response, phase progression and the finite executable update program.

**Provided by the interface:** state fields `a`, `b`, `phase`; action names; discrete nonnegative integer semantics; the two-reservoir update template; and the notion that A/B transfers are symmetric.

**Not solved here:** latent variable discovery from raw signals, arbitrary hidden-state inference, noisy stochastic dynamics, asymmetric actuators, unconstrained equation discovery, general object-centric perception or an unrestricted ground compiler.

Capacity is marked `exact_from_observed_saturation` only when the training evidence includes a state at the inferred upper A boundary, positive inflow and a saturated next value. Otherwise it is only a lower bound.

## Observer quotient audit

A compressed observer view is tested for deterministic transition congruence. Two states may share an observation class only if, under every same action, their next observations agree.

In the first fixture, FULL is congruent; LEVELS, TOTAL and TOTAL_PHASE are not. They may still be adequate for particular tasks, but cannot independently generate all state transitions without hidden-state memory or additional context.

## Resource-aware generativity

A transparent `generated transitions / syntax cost units` figure compares an induced program against an explicit finite transition table. This is a finite-domain generative-yield proxy, not Kolmogorov complexity, a formal compression bound, measured runtime or an asymptotic constant-time claim.

The learner's goal is exact task-relevant generativity under a declared grammar and resource envelope, not minimum description length alone.

## Validation

The test suite has 21 passing tests, including:

- all five induced programs;
- held-out exact prediction;
- exhaustive finite-domain exactness;
- mass-balance invariance;
- mod-3 to mod-4 grammar extension;
- capacity lower-bound handling;
- fail-closed behaviour when interventions are missing;
- transition-congruent versus non-congruent observer projections;
- ground version comparison and executable serialization;
- regression checks for the Build 20 reversible/partial grounds, Build 21 Flow Ground and Build 22 active discovery.

All experiment data are synthetic and deterministic. No physical sensor or TAPS recordings were used.
