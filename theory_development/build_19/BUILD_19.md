# Build 19 — Endpoint, path and observer equivalence

## Status

- 39/39 tests pass (21 inherited Build 18 tests + 18 Build 19 tests).
- The package was verified from a fresh ZIP extraction.
- All Build 19 numerical experiments use deterministic synthetic quaternion paths.
- No empirical TAPS audio or physical sensor data were processed.

## Question

Can endpoint harmonics, path signatures and observer kernels be combined to preserve distinctions that are lost by any one representation, while explicitly preserving observer-induced equivalence classes?

The experiment uses seven deterministic path cases in `S^3 ~= SU(2)`:

1. `reference`: a two-segment piecewise-geodesic path.
2. `alternate_same_endpoint`: a different path with the same initial and final quaternions.
3. `fibre_shifted`: a time-varying right-`U(1)` shift of the reference path, with identical Hopf projection at every sampled parameter value.
4. `reparameterized`: the same sampled geometric path with different time labels.
5. `tree_like_excursion`: the reference path with an exact forward/reverse excursion inserted at an existing vertex.
6. `antipodal_lift`: the pointwise antipodal path `-q(t)`.
7. `timed_path`: the same state path with alternative temporal labels.

## Representations

### 1. Endpoint harmonics

For a unit quaternion `q`, let `D_n(q)` be the spin `n/2` irreducible representation of `SU(2)` implemented as `Sym^n(C^2)`.

The finite `S^3` endpoint feature is the direct sum of normalized matrix coefficients for `n=1,...,N`:

`Phi_S3(q) = direct_sum_n D_n(q) / sqrt(n+1)`.

The code flattens the real and imaginary parts and applies equal sector weighting. The chosen maximum is `N=4`.

Observer quotients are implemented by restricting the harmonic sectors:

- `S3`: all `n=1,...,4`, including half-integer spin sectors.
- `SO3`: even `n` only, so the feature is invariant under `q -> -q`.
- `Hopf`: even `n` and the right zero-weight column only, implementing the selected right-`U(1)` fibre quotient.

These are finite feature maps. Omitting sectors can omit task-relevant distinctions.

### 2. Path signatures

For an ambient path `X`, the truncated signature is:

`S_{<=m}(X) = (1, integral dX, integral dX tensor dX, ..., integral dX^tensor m)`.

The feature vector includes levels `1..m`, with each degree divided by `sqrt(k!)`; degree zero is omitted. The selected depth is `m=3`, with depth sweeps from 1 through 4 for one control pair.

The path embeddings are observer-specific:

- `S3`: quaternion coordinates in `R^4`.
- `SO3`: the adjoint rotation matrix, flattened to `R^9`.
- `Hopf`: the Hopf base point in `R^3`.

The signatures are ambient Euclidean signatures of these embeddings. They are not claimed to be intrinsic manifold signatures on `S^3`, `SO(3)` or `S^2`.

For the `S3` and `SO3` branches, sampled points assumed to lie on a piecewise shortest-geodesic `S3` path are simplified and re-sampled at a fixed density before signature calculation. This prevents a changed sampling density from silently changing the piecewise-linear approximation. The `Hopf` branch uses its observed projected samples directly so that pointwise fibre-equivalent traces remain equal. Consequently, finite-sampling sensitivity remains a limitation of the Hopf branch.

### 3. Observer kernels

For each observer, endpoint and path features induce Gram kernels:

`K_end(i,j) = <Phi(q_i(T)), Phi(q_j(T))>`

`K_path(i,j) = <Psi_O(gamma_i), Psi_O(gamma_j)>`.

Each component kernel is scaled to mean diagonal one, then combined:

`K_joint = 0.5 K_end + 0.5 K_path`.

A nonnegative sum of positive-semidefinite Gram kernels remains positive semidefinite. The kernel-induced distance is:

`d_K(i,j) = sqrt(K_ii + K_jj - 2 K_ij)`.

The observer kernel is a relational geometry induced by a feature map. It is not a third independent sensor or source of information.

## Results

### Endpoint versus path separation

For `reference` and `alternate_same_endpoint`, the endpoint harmonic distance is zero because the final quaternion is identical. The path-signature distance is positive. The finite signature separation by degree is:

| Highest degree | Signature distance |
|---:|---:|
| 1 | `4.44e-16` |
| 2 | `1.08577` |
| 3 | `1.15083` |
| 4 | `1.15688` |

Degree one is endpoint displacement. It cannot distinguish two paths with the same start and end. Degree two already separates this selected pair through higher-order path structure.

### Observer-dependent distinctions

Kernel-induced distances from the reference path:

| Comparison | S3 path distance | SO(3) path distance | Hopf path distance |
|---|---:|---:|---:|
| Alternate path, same endpoint | 0.8653 | 1.2568 | 1.0131 |
| Fibre-shifted path | 0.8323 | 1.1150 | 0 |
| Antipodal lift | 1.5743 | 0 | 0 |
| Reparameterized path | 0 | 0 | 0 |
| Tree-like excursion | 0 | approx. `1.49e-8` | 0 |

These are fixture-specific distances under the selected normalized kernels, not universal scales.

The endpoint quotient controls independently verified:

- `S3` endpoint feature distance between `q` and `-q`: `sqrt(2)`.
- `SO3` endpoint feature distance between `q` and `-q`: `0`.
- Hopf endpoint feature distance between `q` and `q exp(i beta)`: approximately `1.13e-17`.
- Maximum pointwise Hopf projection error between the reference and fibre-shifted paths: approximately `2.29e-16`.

This confirms the intended loss hierarchy for these representations: the `S3` lift sees the antipodal and fibre distinctions; `SO3` identifies antipodes but retains the other rotation information; the Hopf base identifies the entire selected right-`U(1)` fibre.

### Time and path geometry

The state-path signature distance under a change of time labels is `0`. The time-augmented signature distance is `0.28961`.

This separates geometry-only path structure from a representation that deliberately includes elapsed-time coordinates.

### Kernel checks

- Kernel-induced distance agrees with the direct feature-space Euclidean distance to approximately `1.33e-15`.
- Maximum observed negative-eigenvalue violation across the endpoint, path and joint Gram matrices is on the order of `1e-15`, consistent with floating-point roundoff.
- Simultaneous common left/right `SU(2)` action changes the three `S3` kernel matrices by at most approximately `4.32e-15`.

The last check is *joint-action invariance*: applying the same group action to every sample preserves all Gram relationships. It does not mean that a transformed path has zero distance from its original path. Constructing a true orbit metric would require averaging or minimizing over the group action.

### Perturbation probe

For normalized, noisy quaternion samples projected back to `S3`, the reference signature feature distances were:

| Ambient noise sigma | Feature distance |
|---:|---:|
| `1e-4` | `0.000113` |
| `1e-3` | `0.002328` |
| `1e-2` | `0.035042` |

This is a small controlled perturbation probe, not a statistical robustness guarantee.

## Important discovery: endpoint redundancy

For a path with known starting point `q(0)`, the first signature level satisfies:

`S^1(X) = q(T) - q(0)`.

Thus `q(T) = q(0) + S^1(X)`. In the fixed-start fixture, endpoint reconstruction error is exactly zero in floating-point arithmetic, and the endpoint harmonic feature can be reconstructed from that recovered endpoint.

Therefore, endpoint harmonics do not add new exact information to the *full* path signature when the start is known. They remain useful as symmetry-adapted, compact endpoint coordinates and as a distinct metric contribution. When the start is not known, the endpoint representation can act as an anchor together with the degree-one increment.

This is why the joint kernel should not be described as adding independent evidence. In this fixture it changes the geometry and combines perspectives; its endpoint branch is informationally redundant given known `q(0)` and signature level one.

## What the experiment supports

1. Endpoint harmonics cannot distinguish different paths with the same endpoint.
2. Higher signature levels can distinguish the selected same-endpoint paths.
3. Observer quotients produce explicit, predictable losses of distinctions.
4. Tree-like excursions are intentionally identified by path signatures.
5. Time augmentation restores duration-sensitive information intentionally excluded by a clock-free path signature.
6. Observer kernels create a positive-semidefinite relational geometry from a declared feature map.
7. The joint representation can combine endpoint and path metrics, but exact information redundancy must be audited.

## What it does not establish

- Completeness of a finite endpoint harmonic band or finite path-signature depth.
- That the selected observer maps capture all task-relevant distinctions.
- That the same results hold on real sensor trajectories or TAPS audio.
- That the chosen joint kernel is optimal, universal or computationally cheaper.
- That a kernel automatically quotients by a transformation group.
- That finite sampled paths accurately recover arbitrary continuous curves.

## Next proof obligations

1. Test Chen composition under path concatenation and `D_n(q_1 q_2)=D_n(q_1)D_n(q_2)` in a shared compositional experiment.
2. Construct pairs that agree through signature degree `m` but differ at `m+1`; measure the minimal separating degree.
3. Add noise, dropout and observer-projection perturbations with confidence intervals rather than single fixtures.
4. Compare direct feature distances, orbit-averaged kernels and task-specific quotient distances.
5. Measure memory and runtime against direct representations before claiming computational advantage.
