# Build 08 — Generalization and perturbation study

## Motivation

Build 07 found two shared relational patterns in a small designed library:

- base-shape ↔ local-transition: Spearman ρ ≈ 0.693; mean 3-NN Jaccard = 1.0;
- holonomy ↔ temporal: Spearman ρ ≈ 0.382; mean 3-NN Jaccard ≈ 0.188.

These are exploratory. The next build should test whether they persist when the library and observers are no longer arranged around the same small set of hand-designed families.

## Proposed work

1. Generate a substantially larger library from randomized but bounded spherical paths, including multiple loops, self-approaches, non-star-shaped paths and concatenated paths.
2. Keep geometry and time parameterization in separate data fields, preserving the Build 07 correction.
3. Introduce explicit observer perturbations: feature dropout, coordinate projection, noise, sampling jitter, sensor bandwidth and observer-specific thresholds.
4. Compare RDMs using Spearman/Kendall rank statistics, neighborhood overlap and block-aware permutation tests.
5. Add bootstrap intervals over geometric families, not over the repeated time-warp records alone.
6. Compute H1 persistence with a tested implementation or carefully bounded Vietoris–Rips complexes; compare diagrams with an appropriate diagram metric rather than only sorted H0 death times.
7. Test whether candidate clusters persist across distance thresholds and parameter changes.
8. Repeat under codon alias changes and alternative codonic decompositions of the same transformations.
9. Add an independent substrate control so hash-derived addresses do not silently define the observer geometry.
10. Only after these controls, introduce a small acoustic/material proxy signal set to test whether the same observer framework transfers beyond geometric paths.

## Falsification conditions

- Shared RDM relationships disappear under modest changes to observer feature definitions.
- Observed similarities are no stronger than block-permuted or randomized-geometry controls.
- Neighborhood structure depends on one arbitrary threshold or sampling resolution.
- Apparent invariance is explained entirely by shared input features or by the Hopf area/holonomy identity.
- Codon alias changes alter results despite preserving the operation semantics.

## Exit criterion

Build 08 should produce either a robust family of cross-observer relations with quantified uncertainty, or a clear negative result showing that Build 07's apparent relationships were specific to its constructed library. Both outcomes are useful.
