# Next research notes

## Build 19 target

Test the compatibility of endpoint harmonics and path signatures on one common quaternion trajectory library.

Question: when do representation coefficients of the endpoint fail to distinguish two paths, and which path-level signatures or holonomy measurements restore the distinction?

Required negative controls:
- same endpoint, different paths;
- same Hopf base, different fibre phases;
- same path up to increasing reparameterization;
- paths differing by tree-like excursions;
- truncated-signature collisions;
- additive sensor noise and partial coordinate observation.

Do not assume that adding more features always improves generalization. Measure stability, calibration sensitivity, and cost per recovered distinction.

## Later branches

- Koopman spectral analysis of observed state evolution, with measure-preserving and dissipative cases kept separate.
- RNS/NTT: exact transform existence and invertibility conditions for each modulus; do not call modular invertibility a Hilbert-space unitary property.
- Weight-space programming: identify explicit symmetries that preserve the represented model function, then quotient the parameter space by those symmetries before attempting harmonic coordinates.
- Codonic algebra: define typed operations, identity, inverse, composition and action first; only then select group/monoid representations.
