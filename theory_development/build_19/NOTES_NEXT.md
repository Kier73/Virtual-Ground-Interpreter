# Next investigation after Build 19

## Build 20 — compositional invariants

Test the same composition at three levels:

1. Quaternion/group composition: `D(g1*g2) = D(g1)D(g2)`.
2. Path concatenation: `S(X*Y) = S(X) tensor S(Y)` (Chen identity).
3. Observer-kernel composition: determine which kernel relations can be updated incrementally and which require global re-embedding or normalization.

Include noncommuting path segments and closed loops. Test order reversal explicitly; do not infer commutativity from equal endpoints or equal norms.

## Further tasks

- Construct path pairs that agree through signature degree `m` but differ at `m+1` to measure minimal separating degree.
- Add confidence intervals for noise/dropout robustness.
- Compare group-averaged orbit kernels with the current jointly invariant Gram kernels.
- Compare endpoint-only, path-only and direct-sum representations on task-level separation and compute cost.
- For Hopf path features, study convergence under denser projected sampling; the current Hopf branch deliberately avoids S3 geodesic canonicalization to preserve pointwise fibre equivalence.

## Stop conditions

Do not claim completeness, universal tone, empirical sensor invariance or hardware advantage from synthetic fixtures alone.
