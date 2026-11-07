# Build 04 — S³ Codonic Path Navigation and Hopf-Fibre Holonomy

**Research stage:** geometric transport prototype  
**Dependencies:** Python standard library only  
**Verification:** 19 unit tests passed in the captured run  
**Scope:** finite-dimensional quaternion experiment; not yet the full Virtual Layer address geometry.

## 1. Research question

Can we represent a path through a lower-dimensional observer space while retaining an internal quaternion state that accumulates a path-dependent transformation?

More concretely:

1. Can scalar codonic operations implement quaternion transport?
2. Can two paths have the same observed base endpoint but different lifted S³ endpoints?
3. Can the accumulated difference be related to a known geometric quantity?
4. Can we distinguish S³ antipodality from the SO(3) equivalence of antipodal quaternions?
5. Which quantities survive changes of fibre representative, path reversal, and discretization?

## 2. Model choice: the Hopf fibration

Use unit quaternions as S³:

\[
S^3=\{q\in\mathbb H:\|q\|=1\}.
\]

Fix the imaginary unit \(k\), and define the projection:

\[
\pi:S^3\to S^2,\qquad \pi(q)=qkq^{-1}.
\]

The result is a unit imaginary quaternion, identified with a point on S².

Right multiplication by a fibre element preserves the projection:

\[
\pi(qe^{k\beta})
=qe^{k\beta}k e^{-k\beta}q^{-1}
=qkq^{-1}
=\pi(q),
\]

because \(e^{k\beta}\) commutes with \(k\).

Thus the fibre over one base point is a circle of S³ states. The base observer sees the point on S², but does not retain the fibre coordinate.

This is a deliberately selected, mathematically standard observer map. It is not asserted to be the map used by every Virtual Layer observer.

## 3. Codonic quaternion multiplication

The Hamilton product is implemented through a compiled scalar instruction program. The default registry aliases are:

| Codon | Scalar operation |
|---|---|
| `ad` | addition |
| `su` | subtraction |
| `mx` | multiplication |
| `dv` | division |
| `sr` | square root |

The quaternion product is expressed using 16 scalar multiplications and 12 additions/subtractions: 28 instructions total.

For \(a=(a_0,a_1,a_2,a_3)\) and \(b=(b_0,b_1,b_2,b_3)\):

\[
\begin{aligned}
(ab)_0&=a_0b_0-a_1b_1-a_2b_2-a_3b_3,\\
(ab)_1&=a_0b_1+a_1b_0+a_2b_3-a_3b_2,\\
(ab)_2&=a_0b_2-a_1b_3+a_2b_0+a_3b_1,\\
(ab)_3&=a_0b_3+a_1b_2-a_2b_1+a_3b_0.
\end{aligned}
\]

The registry aliases can be changed without changing the computed algebraic result. The tests verify this with a second alias profile (`plus`, `minus`, `times`, `over`, `root`).

This is an operation-level demonstration: it verifies the quaternion multiplication macro's reduction to registered scalar primitives. It does not encode every geometric path-generation step as a codon program.

## 4. S³ and SO(3) are different metric spaces

For unit quaternions \(q_1,q_2\), the standard unit-sphere distance is:

\[
d_{S^3}(q_1,q_2)=\arccos(\langle q_1,q_2\rangle).
\]

This treats antipodal points as distinct, maximally separated points:

\[
d_{S^3}(q,-q)=\pi.
\]

But the map from unit quaternions to 3D rotations is a double cover. The quaternions \(q\) and \(-q\) induce the same rotation. A corresponding SO(3) angular distance is:

\[
d_{SO(3)}(q_1,q_2)=2\arccos\left(|\langle q_1,q_2\rangle|\right),
\]

which gives:

\[
d_{SO(3)}(q,-q)=0.
\]

This distinction must be preserved in the Virtual Layer. Antipodality in S³ is not the same as distinct physical orientation in SO(3).

The implementation includes separate S³ and SO(3) distance functions and separate interpolation functions:

- `slerp_s3`: interpolation between actual S³ points, without sign folding.
- `slerp_so3`: shortest interpolation in the rotation quotient, choosing the closer antipodal representative.

An exact S³ geodesic between antipodal endpoints is non-unique. The implementation raises an error rather than silently choosing an arbitrary axis.

## 5. Horizontal transport along a base path

For adjacent unit vectors \(n_i,n_{i+1}\in S^2\), construct the minimal unit quaternion rotor \(r_i\) that maps one to the other:

\[
r_i=\operatorname{normalize}\left(1+\langle n_i,n_{i+1}\rangle,
 n_i\times n_{i+1}\right).
\]

Away from antipodal adjacent points, this is the minimal rotation taking \(n_i\) to \(n_{i+1}\).

Given a lift \(q_i\), update it by left multiplication:

\[
q_{i+1}=r_iq_i.
\]

The rotation axis of \(r_i\) is perpendicular to \(n_i\). Under the chosen Hopf projection, this is the discrete horizontal-transport convention used here.

The code verifies that the lifted quaternion projects to each next base sample, up to floating-point tolerance.

## 6. Closed base loop and accumulated fibre phase

The experiment constructs a loop on S²:

1. Start at the north pole.
2. Move down a meridian to colatitude \(\theta\).
3. Traverse a constant-colatitude circle once.
4. Return to the north pole along the original meridian.

The loop encloses the spherical cap area:

\[
\Omega=2\pi(1-\cos\theta).
\]

The horizontal lift starts at \(q_0=1\) and ends at \(q_f\). Since the base loop closes:

\[
\pi(q_f)=\pi(q_0).
\]

Therefore the relative quaternion lies in the fibre subgroup:

\[
q_0^{-1}q_f=e^{k\alpha}.
\]

The measured phase is:

\[
\alpha=\operatorname{atan2}((q_0^{-1}q_f)_k,(q_0^{-1}q_f)_0).
\]

For the chosen orientation and projection convention, the expected relation is:

\[
\boxed{\alpha=\frac{\Omega}{2}=\pi(1-\cos\theta).}
\]

The sign of a geometric phase depends on orientation and convention. The tests fix the convention explicitly: the loop is traversed with increasing azimuth and the Hopf map is \(qkq^{-1}\).

## 7. Main numerical results

At the default path resolution (120 meridian steps, 720 latitude steps):

| Quantity | Loop A | Loop B |
|---|---:|---:|
| Colatitude | 0.62 rad | 0.98 rad |
| Solid angle | 1.1694361464 sr | 2.7833094256 sr |
| Expected fibre phase | 0.5847180732 rad | 1.3916547128 rad |
| Measured fibre phase | 0.5847125952 rad | 1.3916470530 rad |
| Absolute phase error | 5.48×10⁻⁶ rad | 7.66×10⁻⁶ rad |
| Base endpoint error | 2.25×10⁻¹⁵ | 1.83×10⁻¹⁵ |
| Off-fibre residual | 1.12×10⁻¹⁵ | 9.07×10⁻¹⁶ |

Both loops begin and end at the north pole in S². Their base endpoints agree to numerical precision, but their lifted S³ endpoints differ by approximately:

\[
|\alpha_B-\alpha_A|\approx0.80693446\text{ rad}.
\]

Thus a base observer identifies the endpoints, while a full S³ observer distinguishes them.

The SO(3) observer also distinguishes these two particular lifts because their fibre phase is not an antipodal sign change. However, it identifies \(q\) and \(-q\), unlike the full S³ observer.

## 8. Additional invariance checks

### 8.1 Path reversal

Reversing the closed base path reverses the sign of the phase:

\[
\alpha[\gamma^{-1}]=-\alpha[\gamma].
\]

In the default run the sum of forward and reverse phases is zero within numerical precision.

### 8.2 Fibre representative shift

Change the starting representative by:

\[
q_0'=q_0e^{k\beta}.
\]

The base point is unchanged. The measured loop phase also remains unchanged (difference approximately \(3.4\times10^{-15}\) rad in the default run).

This is a useful gauge-like invariance for this U(1) fibre action. It does not yet implement a general gauge field over a graph.

### 8.3 Non-circular loop

A second, wavy closed loop changes colatitude as a function of azimuth. Its enclosed area is evaluated by:

\[
\Omega=\int_0^{2\pi}(1-\cos\theta(\varphi))\,d\varphi.
\]

The lifted phase is compared with \(\Omega/2\), providing a check beyond a constant-latitude circle.

### 8.4 Sampling refinement

A coarse and a fine path discretization are compared against the analytical cap phase. The fine path must reduce the absolute error.

## 9. Observer interpretation

| Observer | What it retains | What it identifies |
|---|---|---|
| Hopf-base observer | \(\pi(q)\in S^2\) | All quaternions in one fibre |
| Full S³ observer | Complete unit quaternion | Only identical S³ points |
| SO(3) observer | Induced 3D rotation | \(q\) and \(-q\) |

This is a controlled example of observer-relative equivalence. Each observer induces a different equivalence relation and therefore a different notion of endpoint closure.

Intention is not yet modelled as a learned or active policy. The observer map is selected in advance. Build 05 should allow the observer to choose probes based on uncertainty or task requirements.

## 10. Verification

The test suite contains 19 tests covering:

- Quaternion algebra and non-commutativity.
- Scalar codon compilation and configurable aliases.
- Unit normalization.
- S³ versus SO(3) antipodal metrics.
- S³ and SO(3) interpolation.
- Hopf fibre invariance.
- Base closure with lifted non-closure.
- Half-solid-angle relation for circular and wavy loops.
- Sampling refinement.
- Reversed-loop sign.
- Starting fibre representative invariance.
- Distinct paths with the same base endpoint and different lifted endpoints.

Captured result: 19 tests passed.

## 11. What this establishes and what it does not

### Established by this model

- Quaternion multiplication can be compiled into the selected scalar codonic primitives.
- The Hopf projection forgets a circle-valued fibre coordinate.
- Horizontal transport around a closed base loop can return to the same base point with a different S³ endpoint.
- The accumulated fibre phase agrees numerically with half the enclosed solid angle for the tested loops and convention.
- Reversing the loop reverses its phase.
- A constant initial fibre shift does not change the measured holonomy.
- S³ antipodality and SO(3) orientation equivalence are mathematically distinct.

### Not established

- That the Virtual Layer's SHA-derived seed geometry naturally carries this Hopf fibration.
- That its current quaternion address is already a globally defined principal-bundle connection.
- That arbitrary codon chains produce nontrivial holonomy.
- That the measured phase is emotional tone, semantic meaning, or a universal vibration.
- That all observers share the same topology or preserve the same invariants.
- That the current `S³` representation used in the newer implementation uses this specific Hopf projection.

## 12. Next build: active observation and intention

Build 05 should add a probe-selection policy. The observer should be able to choose among transformations based on the uncertainty between candidate structural explanations.

Candidate objectives:

1. Maximize separation between competing models.
2. Minimize expected posterior uncertainty.
3. Prefer probes that are stable under registry renaming.
4. Penalize probes whose result is dominated by measurement noise.
5. Preserve the distinction between identity, observer equivalence, and hidden holonomy.

Only after that is working should we attempt invariant discovery across multiple independently chosen observer geometries.
