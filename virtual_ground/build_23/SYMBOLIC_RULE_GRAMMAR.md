# Symbolic Rule Grammar

## Sequence expressions

For finite phase domain `p ∈ {0,...,n-1}`, the exact sequence learner searches:

1. `c`
2. `a + b*p`
3. `a + b*(p mod m)`
4. a repeating motif whose length divides `n`;
5. an exact finite lookup table;
6. a modular phase stride `(p+s) mod n` when phase succession is a cyclic permutation.

The simplest exact expression within this grammar is selected. This is a grammar-relative simplification, not a claim of globally minimal description.

## Transfer expressions

The transfer law is inferred as a phase-by-source-residue table:

\[
Q(p,z),\quad z=\text{source level}\bmod m
\]

The learner tries the smallest modulus `m` for which all phase/residue contexts are observed and have a consistent uncensored transfer quantum.

The actual transfer is resource-limited:

\[
t=\min(Q(p,z),\text{source},C-\text{destination})
\]

This separates an operation's requested quantum from the amount actually executable at a particular state.

## Counterexample-driven extension

If no `m≤3` yields a consistent complete law, the result is `InductionError`, not a guessed constant. The Build 23 final fixture contains an operation rule depending on source level modulo 4. The initial grammar rejects it; an explicit expansion to `m≤4` discovers the new law.

## What a future grammar should add

Candidate extensions, to be justified by counterexamples:

- source-level thresholds and piecewise-affine rules;
- action-specific/asymmetric laws;
- interactions between multiple state variables;
- boolean guards and invariants;
- latent context/phase variables;
- nondeterministic or probabilistic transitions;
- symbolic integer / modular / finite-field operations;
- compositional codonic operations and graph rewrites.

Grammar expansion should be versioned and accompanied by regression tests. A larger grammar increases expressivity but also raises ambiguity, search cost and overfitting risk.
