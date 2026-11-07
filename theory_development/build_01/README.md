# Virtual Layer — Observer-Dependent Response Geometry

**Prototype:** 0.1  
**Status:** exploratory instrument, not a validated Virtual Layer implementation  
**Dependencies:** Python 3.10+ standard library only

## Purpose

Test a separation between:

1. **Algebraic identity:** a canonical codonic expression and deterministic SHA-256 identifier.
2. **Observer response:** outputs measured under a fixed family of probes.
3. **Response geometry:** a point on the unit 3-sphere derived from four observer-weighted response coefficients.

The crucial rule is that the hash address is *not* used as a distance metric. Cryptographic hashes are identifiers, not semantic embeddings.

## Local codon map

This prototype uses an editable local registry and follows the user's stated current example `ad = addition`, `mx = multiplication`. That is not an assertion that all prior Virtual Layer registry versions use those assignments. The registry also defines `su`, `dv`, `sq`, `ng`, `sn`, and `cs` for the test fixtures.

## Response features

Expressions are evaluated over a fixed grid of 129 inputs on `[-1, 1]`. Their output vector is projected onto four orthonormal probe directions:

- `dc`: constant / mean response;
- `linear`: response aligned with input;
- `curvature`: response aligned with the quadratic probe after orthogonalization;
- `oscillatory`: response aligned with a sine probe after orthogonalization.

The remaining unexplained output energy is retained as `residual_rms`. It is not silently discarded.

An observer is represented by a 4x4 matrix `W_O`:

```text
z_O = W_O features
amplitude_O = ||z_O||
q_resp_O = z_O / ||z_O||
```

`q_resp` lies on `S^3`. Its geodesic distance is:

```text
d_S3(q1, q2) = acos(clamp(dot(q1, q2), -1, 1))
```

This prototype **does not identify** `q` with `-q`. They encode opposite response directions. This differs from the double-cover convention used when unit quaternions represent 3D rotations in `SO(3)`.

Amplitude and residual are kept in the augmented response distance because normalization to the sphere otherwise discards magnitude and out-of-basis structure.

## Reproduction

From this directory:

```bash
python -m unittest -v
python vl_response_geometry.py > demo_report.json
```

The report contains the three observer-specific response geometries and rank correlations between their representational dissimilarity matrices (RDMs).

## What the prototype can test

- Exact canonical equivalence under a small, explicit set of algebraic rewrites.
- Whether equivalent expressions receive the same canonical identity.
- Whether a seed and its negated function produce antipodal response directions under a balanced observer.
- Whether changing observer sensitivities changes pairwise geometric distances.
- Whether response amplitude and residual structure remain visible outside the normalized `S^3` direction.

## What it cannot establish

- It does not establish a universal tone space.
- It does not establish emotional or biological correspondence.
- It does not test the current SHA-256/RNS/CRT/Feistel quaternion-address machinery.
- Four hand-selected response modes are not a complete description of a function.
- A high RDM correlation is not proof of a common underlying ontology.
- Algebraic canonicalization is only as sound as the declared rewrite rules and domain assumptions.

## Next builds

1. Replace the scalar-expression fixture with typed codon DAGs and explicit input/output types.
2. Add time-dependent stateful codons and AR / pole-response signatures.
3. Add an S³ seed-address adapter as a separate, auditable map; compare it against response-derived geometry rather than conflating the two.
4. Add multiple probe families and held-out probes to test generalization.
5. Add bootstrap confidence intervals and permutation tests for RDM similarity.
6. Add cross-substrate and randomized-label controls.
7. Only after those tests, investigate graph-Laplacian / spectral geometry on the measured response neighborhoods.
