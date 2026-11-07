# Build 18 experiment notes

## SU(2) / Hopf quotient

For a normalized quaternion `q`, the implementation uses:

- `U(q) = [[a+ib, c+id],[-c+id,a-ib]]`;
- `D^(n/2)(q) = Sym^n(U(q))`;
- `π(q) = q i q^{-1}`;
- fibre action `q -> q exp(iβ)`.

The numerical projection averages the representation matrix over 256 uniformly spaced fibre phases. This is not used as a replacement for the exact representation-theoretic derivation; it is a finite numerical check of the zero-weight selection rule.

Results:

| n | spin j | sector dimension | zero-weight rank | fibre-average norm |
|---:|---:|---:|---:|---:|
| 0 | 0 | 1 | 1 | 1.0 |
| 1 | 1/2 | 2 | 0 | about 3.33e-16 |
| 2 | 1 | 3 | 1 | about 1.0 |
| 3 | 3/2 | 4 | 0 | about 1.76e-16 |
| 4 | 2 | 5 | 1 | about 1.0 |
| 5 | 5/2 | 6 | 0 | about 2.78e-16 |

The maximum Schur orthogonality residual in one seeded 30,000-point Haar Monte-Carlo run for spin 1/2 was about `5.45e-3`. The 18,000-point seeded regression test stayed below `8e-3`. These are integration sampling errors; exact Schur orthogonality is a theorem.

## Observer compatibility

A second representation is constructed by unitary conjugation `ρ_b(g)=Tρ_a(g)T*`. The resulting intertwiner residual was about `8.24e-16`; Gram-matrix error was about `5.96e-15`. This demonstrates the algebraic compatibility condition under a known unitary transform. It does not discover an unknown relation between real observers.

## Path signatures

The low-order piecewise-linear signature implementation verifies:

- segmentation invariance for a fixed polygonal path;
- orientation sensitivity;
- a straight out-and-back tree-like excursion has trivial signature through degree 4;
- a clock-free state path is unchanged when only elapsed-time scale changes;
- augmenting the path with explicit elapsed-time coordinates makes that scale change visible.

A finite truncation is not a complete path identifier. The full bounded-variation signature theorem identifies paths only up to tree-like equivalence under its hypotheses.

## Scope

All values in this note come from deterministic or seeded mathematical fixtures. No physical measurement, TAPS audio, human identity, emotion, or real-world system was inferred.
