# Sources and provenance

## Code lineage

- Build 18 `relational_atlas.py` and Build 18 tests are included as the inherited mathematical core and regression baseline.
- Build 19 adds deterministic quaternion path fixtures, observer-specific feature maps, finite harmonic endpoint features, Gram kernels, and comparison tests.

## Mathematical foundations

The package uses the established mathematical identities already stated and qualified in Build 18:

- Peter–Weyl decomposition and matrix-coefficient orthogonality for compact groups such as SU(2).
- SU(2) representation homomorphism and the central-element parity rule.
- Compact-subgroup averaging as projection to invariant subspaces.
- Chen's identity for path-signature concatenation and the tree-like equivalence of full bounded-variation signatures.
- Positive semidefiniteness of feature-map Gram kernels and nonnegative sums of such kernels.

Build 19's new measurements are calculated locally from deterministic synthetic trajectories. There are no external empirical data sources, no audio, and no physical sensor records in this package.
