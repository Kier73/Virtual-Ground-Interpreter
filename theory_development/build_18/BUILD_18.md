# Build 18 — Relational Invariant Atlas and SU(2)/S3 harmonic quotient

## Status

- SU(2) symmetric-power representations implemented for low orders.
- Hopf map and fibre subgroup implemented for unit quaternions.
- Numerical Haar sampling and Schur orthogonality check implemented.
- Antipodal parity and Hopf fibre projection tested.
- Unitary intertwiner / Gram preservation demonstration implemented.
- Truncated piecewise-linear path signature implemented through tensor degree 5.
- 21 tests pass.
- All experiments in this package are mathematical/numerical fixtures. No TAPS audio or physical sensor data were processed.

## Main result

The Hopf quotient makes observer-dependent information loss algebraically explicit.

For the spin-`j=n/2` irreducible representation of SU(2), the centre `-I` acts as `(-1)^n`. The S3-to-SO3 antipodal quotient therefore removes all odd `n` (half-integer spin) modes.

The Hopf map `q -> q i q^-1` identifies a full right U(1) fibre. Fibre averaging projects onto right weight zero. Half-integer spins have no zero weight and vanish; integer spins retain one zero-weight direction. The base S2 observer therefore sees a stricter quotient than the SO3 observer.

This matches the project's observer-relative invariant idea: different vantage points do not merely rotate coordinates; some quotient away degrees of freedom.

## Numerical results

The run is recorded in `reports/build_18_results.json`.

- Antipodal parity residuals through `n=5`: at numerical roundoff.
- Hopf fibre invariance for 17 sampled phases: at numerical roundoff.
- Fibre averaged spin `1/2`, `3/2`, `5/2` representations: norms below `4e-16`.
- Fibre averaging for spin `0`, `1`, `2`: agrees with the exact zero-weight projector to about `3e-15`.
- Monte Carlo Schur orthogonality error for spin `1/2`, 30,000 Haar samples: about `5.45e-3` max entrywise error.
- Constructed unitary intertwiner residual: about `8.24e-16`.
- Gram-matrix preservation error: about `5.96e-15`.
- S3 antipodal geodesic distance `d(q,-q) = π`, while the Hopf base coordinates coincide exactly.
- Clock-free path signatures agree after the tested subdivision/reparameterization; a time-augmented signature detects changed elapsed time.

The Schur test is Monte Carlo and its residual is a sampling error, not a failure of the exact theorem.

## Implementation limits

- Symmetric-power matrices are built with Kronecker powers and a symmetric-subspace basis. This is a transparent reference implementation, not a high-performance Wigner-D kernel. The implementation caps `n` at 6.
- Haar orthogonality is checked numerically using normalized Gaussian points on S3.
- Path signatures are truncated at finite tensor degree; finite truncations are not complete path identifiers.
- No universal observer intertwiner is assumed. The example conjugates one representation by a known unitary matrix, so it is a construction test.

## Tests

`python -m unittest discover -s tests -v`

21 tests cover quaternion group operations, SU(2) unitarity and homomorphism, antipodal parity, Hopf invariance and quotient selection, Schur orthogonality, intertwiners, Gram preservation, and low-order path signature behavior.

## Next falsification step

Build 19 should compare the atlas on a shared family of transformations rather than expand the representation list:

1. Create a set of quaternion paths with known endpoint, fibre phase and path history.
2. Compare endpoint-only SU(2) coefficients, Hopf-projected coefficients and path signatures.
3. Construct trajectories with equal endpoints but distinct holonomy/path signatures.
4. Test whether the combined representation distinguishes the intended quotient classes.
5. Add noisy/partial observations and measure the stability of each chart's Gram kernel.
6. Compare the resulting compute cost with direct path storage and direct quaternion state propagation.
