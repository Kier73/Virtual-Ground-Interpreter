# Conjecture scorecard — what is established, tested, or still open

## Established mathematical results used as foundations

- Plancherel/Peter–Weyl harmonic decomposition for compact groups, including SU(2).
- Schur orthogonality of inequivalent irreducible representation matrix coefficients.
- SU(2) centre parity: the `n`th symmetric-power sector responds to `-I` by `(-1)^n`.
- Averaging over a compact subgroup projects onto its invariant subspace; for the selected Hopf U(1), this is the right zero-weight subspace.
- Full bounded-variation path signatures characterize paths up to tree-like equivalence under the theorem's hypotheses.
- Koopman composition operators act linearly on observables; unitarity requires suitable measure-preserving invertible dynamics.

## Numerically verified in Build 18

- Quaternion multiplication and the SU(2) matrix representation agree with composition.
- Low-order symmetric-power SU(2) matrices are unitary and satisfy the representation law.
- Antipodal parity holds through `n=5` to numerical precision.
- The Hopf map is constant on the selected right U(1) fibres.
- Numerical fibre averaging removes half-integer sectors and retains exactly the zero-weight column in integer-spin sectors.
- A constructed unitary intertwiner preserves the Gram matrix to numerical precision.
- Low-order path signatures pass subdivision, orientation and tree-like backtracking tests.
- Adding elapsed time as a path coordinate makes a duration rescaling visible; excluding it leaves the state path signature unchanged.

## Not established

- That arbitrary observer pairs admit an intertwiner.
- That a finite set of sectors separates all task-relevant states.
- That a particular harmonic tone profile is universal or observer-independent.
- That spectral energy alone preserves phase, path orientation or semantic distinctions.
- That a finite path-signature truncation is complete.
- That the atlas is computationally cheaper than direct computation for a real workload.
- That the system can outperform hardware processing.
- That the TAPS dataset has shown empirical cross-modal invariance; its recordings were not processed in these builds.

## Conditions needed for a meaningful positive result

The next experiments must specify a target task and show:

1. The equivalence relation induced by transformations and observation.
2. Separation of distinct quotient classes by the joint observer signature.
3. Intertwiner or kernel compatibility across observer charts.
4. Stability under measurement noise, calibration error, clock drift and spectral truncation.
5. Correct composition of encoded transformations.
6. Lower measured cost or improved accuracy/robustness relative to a direct baseline.
