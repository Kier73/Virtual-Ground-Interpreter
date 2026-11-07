# Build 01 — Observer-Dependent Response Geometry

**Project:** Virtual Layer / Codonic algebra / S³  
**Build:** 0.1 exploratory instruments  
**Status:** two reproducible synthetic experiments; 15 unit tests passing  
**Runtime:** Python 3.10+; standard library only

---

## Executive finding

A useful experiment can be built by keeping three objects separate:

\[
\text{algebraic identity}\qquad\text{observer response}\qquad\text{geometric representation}
\]

The first prototype gives a deterministic algebraic identity to a codonic expression, measures its response under a fixed family of probes, and maps four response coefficients to an observer-specific point on \(S^3\).

A second prototype represents a stable AR(2) dynamical law as a codonic expression and measures its frequency response. Its peak frequency tracks the law's pole angle, while damping changes its peak strength and width.

These experiments establish that the proposed measurements are implementable and internally testable. They do **not** establish a universal tone space, emotional semantics, cross-modal invariants, or a new computational advantage.

## Why this architecture

The Virtual Layer v3.0 reference describes codonic chains, a SHA-256-derived algorithm coordinate, RNS/CRT, Feistel fetch, NTT, quaternion orientation and observer-dependent measurement. The exploratory notes also report algorithm-neighborhood and antipodal findings, while acknowledging that these may depend on the chosen cryptographic substrate.

The experiment therefore separates identity from geometry:

- A normalized codonic expression receives a SHA-256 digest for identity and reproducibility.
- The digest is not used to calculate response distance.
- An observer measures the algebraic law under explicitly defined probes.
- A separate response signature is derived from those measurements.

This prevents hash avalanche behavior from being mistaken for semantic locality. Cryptographic identifiers can be stable and useful without being meaningful metric embeddings.

## Experiment A — Static algebraic response on S³

### A1. Editable local codon registry

The prototype uses a small real-valued expression language. The local assignments follow the user's explicit example for this experiment:

| Codon | Operation |
|---|---|
| `ad` | addition |
| `mx` | multiplication |
| `su` | subtraction |
| `dv` | division |
| `sq` | square |
| `ng` | negation |
| `sn` | sine |
| `cs` | cosine |

This is an editable experimental mapping, not a claim that every historical or uploaded registry version uses the same assignments. In particular, the v3.0 reference is a snapshot and its nomenclature can be changed independently of the algebra.

The expression tree is typed only as a scalar real-valued expression in this first build. It is not yet a complete typed codon DAG or a general multi-input virtual instruction set.

### A2. Conservative canonicalization

Applied rewrites are deliberately limited:

- reorder arguments of operations explicitly marked commutative;
- `ad(x, 0) -> x`;
- `mx(x, 1) -> x`;
- `su(x, 0) -> x`;
- `dv(x, 1) -> x`.

No approximate equality, distributivity, or floating-point reassociation is assumed. This avoids declaring two expressions equivalent merely because a finite sample happened to produce similar outputs.

The canonical expression is serialized and hashed. The digest is an identity label only.

### A3. Fixed probe family

Each expression is evaluated on 129 evenly spaced inputs on \([-1,1]\). Its output vector is projected onto four orthonormal probe directions:

1. DC / constant response;
2. linear response;
3. quadratic curvature response;
4. oscillatory response based on a sine probe.

Let the resulting coefficient vector for expression \(s\) be:

\[
c(s)=(c_0,c_1,c_2,c_3)\in\mathbb R^4
\]

The unexplained residual RMS is retained separately so that energy outside the four selected modes is visible.

### A4. Observer transform and S³ direction

An observer is represented by a 4-by-4 matrix \(W_O\):

\[
z_O(s)=W_Oc(s)
\]

\[
a_O(s)=\|z_O(s)\|_2,\qquad
q_O(s)=\frac{z_O(s)}{\|z_O(s)\|_2}\in S^3
\]

The S³ geodesic is:

\[
d_{S^3}(q_1,q_2)=\arccos(\operatorname{clamp}(q_1\cdot q_2,-1,1))
\]

Here, \(q\) and \(-q\) are intentionally distinct: they represent opposite response directions. This response-direction space is not being interpreted as \(SO(3)\) rotation space. When unit quaternions represent rotations, \(q\) and \(-q\) represent the same rotation; that identification must not be silently imported into this measurement.

The prototype retains response amplitude and residual RMS alongside the spherical direction. Its current augmented distance combines angular distance, log-amplitude difference and residual-RMS difference with equal weights. Those weights are provisional and require calibration before the combined distance is used scientifically.

### A5. Results

The initial demonstration covers eight expression fixtures:

- `x`
- `x + 0`
- `x × 1`
- `0 - x`
- `x²`
- `sin(2πx)`
- `x² + 0.4 sin(2πx)`
- `x² - 0.4 sin(2πx)`

Observed checks:

| Check | Result |
|---|---:|
| `x`, `x + 0`, `x × 1` canonical identity | identical |
| Shared 64-bit digest for those aliases | `a66e7c880a55c9b8` |
| Distance between `x` and `-x` response directions | \(\pi\) radians |
| Balanced vs oscillation-sensitive RDM rank correlation | 0.8172 |
| Balanced vs polynomial-sensitive RDM rank correlation | 0.9607 |
| Oscillation-sensitive vs polynomial-sensitive RDM rank correlation | 0.7768 |

For the pair `x² ± 0.4 sin(2πx)`, the response-direction distance changes with observer weighting:

| Observer | S³ angular distance |
|---|---:|
| Balanced | 1.1105 rad |
| Oscillation-sensitive | 2.3221 rad |
| Polynomial-sensitive | 0.2595 rad |

This is the intended mechanism demonstration: the same pair of algebraic laws can have different apparent separation under different observer sensitivities. The RDM correlations are computed on a tiny synthetic fixture set and have no inferential significance.

An orthogonal reparameterization of the four response coordinates leaves S³ pairwise distances unchanged. Anisotropic weighting changes them. Both behaviours are covered by tests.

## Experiment B — Dynamic codonic response / AR(2) resonance

### B1. Codonic law

A stable second-order recurrence is represented as:

\[
x_t=2r\cos(\omega_0)x_{t-1}-r^2x_{t-2}+u_t
\]

with:

\[
0<r<1,\qquad 0<\omega_0<\pi
\]

Its characteristic poles are:

\[
p_{1,2}=r e^{\pm i\omega_0}
\]

The local expression uses `mx` and `ad` to encode multiply-and-accumulate composition, with coefficients retained as seed parameters.

### B2. Probe and measurement

The law is exposed to sinusoidal inputs across a frequency sweep. The analytic transfer function is:

\[
H(e^{i\omega})=
\frac{1}{1-2r\cos(\omega_0)e^{-i\omega}+r^2e^{-2i\omega}}
\]

The prototype records gain and phase. Four orthogonal modes of log-gain are projected into an observer-specific S³ response direction. The full spectral curve remains available in the result object; the four-dimensional projection is not treated as lossless.

### B3. Results

For three stable systems, simulated steady-state gain at the natural frequency matched analytic transfer gain to near floating-point precision:

| Pole radius | Pole angle | Relative gain error |
|---:|---:|---:|
| 0.92 | 0.35 rad | \(7.53\times10^{-16}\) |
| 0.92 | 1.10 rad | \(1.22\times10^{-16}\) |
| 0.92 | 2.20 rad | \(2.21\times10^{-16}\) |

The frequency-sweep peak estimates were approximately 0.339, 1.088 and 2.199 rad/sample respectively, close to the specified angles. A more heavily damped system may peak at or near DC rather than forming a pronounced resonance peak; that is a meaningful response difference, not a failed measurement.

The key result is modest but useful: **for this family of dynamical laws, pole angle and damping create a measurable spectral response signature.** This gives a precise bridge from codonic recurrence to a tone-like mathematical descriptor.

## Connection to established methods

- **System identification** builds models from measured input-output responses. The dynamic experiment is a minimal controlled instance of this process. See [System Identification Overview](https://www.mathworks.com/help/ident/gs/about-system-identification.html).
- **Representational Similarity Analysis (RSA)** compares representational dissimilarity matrices rather than raw feature coordinates. This is useful when observers or modalities use different internal coordinate systems. See Kriegeskorte, Mur and Bandettini (2008), [Frontiers in Systems Neuroscience](https://www.frontiersin.org/journals/systems-neuroscience/articles/10.3389/neuro.06.004.2008/full).
- **Graph approximations to Laplace–Beltrami operators** provide a later path from measured neighbourhood graphs to spectral geometry. See Burago, Ivanov and Kurylev (2014/2015), [Journal of Spectral Theory](https://ems.press/journals/jst/articles/12892).

These methods support the proposed measurement strategy. They do not establish that the Virtual Layer's full S³ or cryptographic address geometry is a universal representation of meaning.

## Design cautions and open questions

1. **Keep the two S³ constructions distinct.** The existing Virtual Layer `q(f)` is a seed/orientation construction. `q_resp` is a new observer-derived response direction. Their relationship has not been established.
2. **Do not treat a hash as a semantic metric.** SHA-256 is useful for deterministic identity. Its avalanche behaviour means nearby input descriptions should not be expected to have nearby digest coordinates.
3. **A coordinate is not a law.** A codonic seed identifies a described transformation; execution correctness still requires operational semantics, type constraints, state and input.
4. **Four response modes are a measurement choice.** Other observers need other probes, dimensions or adaptive bases. The residual must remain visible.
5. **Observer weighting is currently handcrafted.** It demonstrates how a sensor model can change geometry, not how actual biological observers are calibrated.
6. **S³ is not automatically the right manifold.** The response signatures happen to be represented as four normalized coefficients. More general response spaces may need higher-dimensional spheres, projective spaces, products, graphs or learned manifolds.
7. **Antipodality needs an explicit action.** Bitwise complement, quaternion negation and algebraic inverse are different operations. A mapping between them must be specified and tested.
8. **Resonance is operational, not metaphorical.** Here it means a measurable gain peak or shared response mode. Emotional valence is a separate observer-dependent assessment and is not part of these builds.

## Next build sequence

### Build 02 — Typed codonic algebra

Extend the expression fixture into a typed DAG with declared domains, arities, side-effect classes, identities, inverses, commutative/associative laws and rewrite proof obligations. Compare semantic equivalence separately from response similarity.

### Build 03 — Stateful observer bank

Support multiple inputs and persistent state. Add AR(p), state-space and finite impulse response codonic programs. Measure impulse, step, sinusoidal and randomized probe responses.

### Build 04 — Observer-induced metric

Estimate local sensitivity / Jacobians and construct an observer pullback metric where differentiability is available:

\[
g_O(q)=J_O(q)^T W J_O(q)
\]

Compare this geometry with the response RDM and existing S³ geometry.

### Build 05 — Relational invariance

Compare observer RDMs using Spearman/Kendall rank correlation, Procrustes alignment where appropriate, bootstrap confidence intervals, and permutation tests. Use held-out probes to test generalization.

### Build 06 — Spectral topology

Construct a proximity graph from independently measured response distances. Investigate graph-Laplacian eigenvalues and eigenvectors. Test whether stable neighbourhoods survive observer changes and substrate changes.

### Build 07 — Substrate controls

Compare SHA-derived IDs, alternate deterministic IDs, randomized labels and response-derived geometry. Check whether any discovered structure is carried by the algebra, the observer, the chosen probe family, or the address substrate.

## Current decision

Do not enlarge the algorithm registry yet. First strengthen the operational semantics and response measurement. The most promising immediate direction is a stateful codon DAG with multiple probe families and observer-specific response curves, keeping identity, behaviour and geometry independently auditable.
