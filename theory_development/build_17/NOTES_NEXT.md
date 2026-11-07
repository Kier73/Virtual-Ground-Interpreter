# Next investigations

## Build 18 — SU(2) / S³ harmonic structure

Implement low-order SU(2) matrix coefficients (Wigner-D functions) or equivalent S³ hyperspherical harmonics. Test:

- orthogonality under normalized Haar measure;
- left and right multiplication actions;
- antipodal parity and the distinction between q and -q on S³;
- projection under the Hopf map and what phase information the base observer loses;
- basis changes within repeated irreducible components.

Keep SU(2) distinct from SO(3): q and -q are distinct points in S³ but represent the same rotation in SO(3).

## Build 19 — codonic symmetry and exact transforms

Identify invertible transformations in the codonic registry. Construct the actual finite group/subgroup only after closure, identity and inverse are verified. Implement a group DFT on a small finite group, then an NTT only for moduli with a suitable primitive root and invertible transform length. Analyze noninvertible codons as semigroup actions/operators rather than forcing group structure.

## Build 20 — observer-response intertwiners

Build response Gram matrices from common probes; test kernel/RDM invariants; attempt maps satisfying `T rho_A(g) = rho_B(g) T`. Separate exact algebraic preservation from empirical statistical agreement.

## Later temporal branch — reparameterization invariants

Compare iterated-integral path signatures against fitted dynamic time warping / diffeomorphic registration. A signature is not a magic complete identifier: test truncation, tree-like equivalence, sampling, noise, path dimension and loss of temporal rate. Registration is a fitted correspondence, not an intrinsic invariant.

## Required controls

- event-mark shuffles and order shuffles;
- transformations inside and outside the assumed symmetry group;
- phase removal and retention;
- basis sign changes and rotations within repeated eigenspaces;
- graph motif-threshold sweeps;
- noise, dropout, bandwidth and event-threshold perturbations;
- held-out observers/sensors with calibration where available.

Do not treat synthetic success as sensor validation.
