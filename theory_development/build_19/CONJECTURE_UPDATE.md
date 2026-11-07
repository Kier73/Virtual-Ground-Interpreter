# Relational Invariant Atlas — Build 19 update

## Refined statement

For a declared task class, transformation action and observer family, a useful finite representation may be assembled from symmetry-adapted endpoint features and path features such that the induced relational kernel preserves the task-relevant distinctions up to the declared observer equivalence.

This is a conditional, task-relative conjecture. It is not a claim that one finite representation captures all possible systems or meanings.

## Objects

- `S`: state space.
- `G`: transformation group, or a more general monoid/groupoid/semigroup when inverses do not exist.
- `gamma`: an evolving state path.
- `O`: observer and its measurement/projection map `psi_O`.
- `D_pi`: an irreducible or otherwise symmetry-adapted representation.
- `S_{<=m}`: path signature through degree `m`.

A candidate representation is:

`R_{O,N,m}(gamma) = (Phi_{O,N}(gamma(T)), S_{<=m}(psi_O o gamma))`.

The endpoint feature is built from selected harmonic sectors up to band `N`. The path feature records the ordered observed trajectory through degree `m`.

## Induced kernel

A direct-sum kernel can be formed:

`K_O(gamma,gamma') = a K_end,O(gamma(T),gamma'(T)) + b K_path,O(gamma,gamma')`

with nonnegative weights `a,b`. If both component kernels are positive semidefinite, the sum is positive semidefinite.

Its Hilbert feature distance represents pairwise relationships in the selected representation. The kernel does not add observations beyond the features from which it is constructed.

## Observer equivalence

Two paths are indistinguishable to observer `O` under the selected finite representation when:

`R_{O,N,m}(gamma) = R_{O,N,m}(gamma')`.

This induces a finite pseudometric and a representation-dependent equivalence relation. The desired completeness property is stronger:

`d_R(gamma,gamma') = 0` if and only if the paths lie in the task's intended observer/transformation equivalence class.

Build 19 only tests selected synthetic representatives. It does not prove completeness.

## New qualification: redundant and complementary coordinates

If the initial point is known, signature degree one is the endpoint displacement:

`S^1(gamma) = gamma(T)-gamma(0)`.

Thus endpoint coordinates can be reconstructed from the start and degree one. Endpoint harmonics can still provide a compact symmetry-adapted metric and an absolute anchor when the start is unknown, but they do not add independent exact information in the fixed-start case.

The endpoint and path branches should therefore be treated as a potentially redundant direct sum. Their weights should be learned or selected against a declared task, not assumed equal by principle.

## Quotients are observer choices

The same underlying path can have different equivalence classes under different observers:

- `S3` retains the unit-quaternion lift and the selected fibre phase.
- `SO3` identifies `q` and `-q`.
- `S2` under the Hopf map identifies the entire selected right `U(1)` fibre.

Projection changes which states are equivalent to the observer. It does not assert that discarded state variables do not exist.

## Composition as the next mathematical requirement

Two algebraic composition laws align with the proposed atlas:

1. For group representations: `D(g1 g2) = D(g1)D(g2)`.
2. For paths: `S(X * Y) = S(X) tensor S(Y)` (Chen's identity), with tensor algebra truncated consistently at degree `m`.

A strong next experiment should verify both within one task family, including noncommuting transformations and concatenated path segments. This would make the representation useful for codonic composition rather than only static comparison.

## Falsifiable proof obligations

1. **Separation:** distinct task-relevant quotient classes receive nonzero distance.
2. **Equivariance/intertwining:** transformations act compatibly in overlapping observer charts.
3. **Stability:** measured distances change in a bounded way under noise and sampling errors.
4. **Truncation:** an explicit tail or empirical error estimate accompanies finite bands/depths.
5. **Composition:** composing representations agrees with composing the described transformations/paths.
6. **Efficiency:** the representation reduces measured compute, memory or communication cost for a declared workload.

No universal finite cutoff, observer-independent tone, or hardware advantage is asserted.
