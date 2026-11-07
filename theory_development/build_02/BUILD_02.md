# Build 02 — Shape, Movement, Observer, and Geometric Phase

**Project:** Virtual Layer / Codonic algebra / observer-dependent response geometry  
**Build:** 0.2 exploratory instrument  
**Status:** 10 unit tests passing; deterministic synthetic experiment  
**Runtime:** Python 3.10+; standard library only

## Executive finding

This build tests a distinction that appears central to the current investigation:

1. **Shape:** the oriented path traced in a configuration space.
2. **Movement:** the time-parameterization and dynamics of traversal.
3. **Observer:** the measurement map through which the path is seen.
4. **Intention:** the task-dependent choice of which response coordinates matter.
5. **Tone (provisional):** a time-resolved response signature, not an intrinsic emotional label.

For the same closed ellipse traversed at two different monotone speeds, the geometric phase is numerically unchanged while the temporal phase-rate signature changes. A rank-deficient observer projection collapses the loop and erases the measured area/phase. A stable limit-cycle example shows a transient response converging toward a limiting per-cycle phase.

These are mechanism demonstrations in an intentionally simple model. They do not establish universal semantics, biological equivalence, or the Virtual Layer's full S³ geometry.

## 1. Mathematical model

Take a path \(\gamma(t)=(x(t),y(t))\) in a two-dimensional configuration space. Define a simple connection one-form:

\[
A(x,y)=\left(-\frac{\alpha y}{2},\frac{\beta x}{2}\right),
\qquad
 d\psi=A_x\,dx+A_y\,dy.
\]

The accumulated phase along a path is:

\[
\Gamma[\gamma]=\int_\gamma A\cdot d\gamma.
\]

For \(\alpha=\beta=1\) and a closed planar curve, Green's theorem gives:

\[
\Gamma[\gamma]=\frac12\oint(x\,dy-y\,dx)
=\text{signed enclosed area}.
\]

For an ellipse \(x=a\cos\phi, y=b\sin\phi\):

\[
\Gamma=\pi ab.
\]

The integral is unchanged by an orientation-preserving monotone reparameterization of the same path. Reversing orientation reverses its sign. The instantaneous response rate is different:

\[
\nu(t)=\dot\psi(t)=A(\gamma(t))\cdot\dot\gamma(t).
\]

Thus \(\Gamma\) describes a path-level quantity, while \(\nu(t)\) is a time-indexed response. This is the central shape-versus-tone separation in this build.

**Important scope:** this connection is an illustrative mathematical choice. It is not derived from a particular physical organism, bicycle, codon law or existing Virtual Layer quaternion construction.

## 2. Observer and intention

An observer is represented by a projection \(C_O\) and a connection parameterized by \((\alpha,\beta)\):

\[
\tilde\gamma(t)=C_O\gamma(t).
\]

The phase is measured over the observed path rather than the latent path. A full-rank linear projection changes area by its determinant; an area-preserving map preserves it; a rank-deficient map can collapse a loop to a line and remove enclosed area.

An intention does not modify the raw path or measurements. It selects a weighted subset of the response signature for a task-specific comparison. The implementation contains separate examples for shape-focused and temporal-tone-focused comparison.

This separation avoids treating one observer's geometry or one task's priorities as universal.

## 3. Dynamics and transverse stability

A simple stable limit-cycle neighbourhood is represented in elliptical coordinates by:

\[
\rho(t)=1+\delta e^{-\kappa t},\qquad
\theta(t)=\omega t,\]

\[
x(t)=a\rho(t)\cos\theta(t),\qquad
y(t)=b\rho(t)\sin\theta(t).
\]

The limiting cycle is \(\rho=1\). The transverse displacement obeys:

\[
\dot\eta=-\kappa\eta,\qquad \eta(t)=\eta(0)e^{-\kappa t}.
\]

The phase direction is neutral in this idealized autonomous oscillator; the orbit is transversely attracting, not a fixed point attracting in every direction. The prototype estimates \(\kappa\) from the slope of \(\log|\rho(t)-1|\).

## 4. Experiments and results

### A. Same shape, different speed

Ellipse: \(a=1.2\), \(b=0.7\), 4,096 path segments.

| Descriptor | Uniform traversal | Warped traversal |
|---|---:|---:|
| Signed area | 2.63893679 | 2.63893648 |
| Geometric phase | 2.63893679 | 2.63893648 |
| Path length | 6.07282256 | 6.07282240 |
| Phase-rate RMS | 2.63893679 | 2.76931185 |
| Phase-rate coefficient of variation | ~0 | 0.31819779 |

The shape-focused intention distance was approximately \(7.62\times10^{-8}\). The temporal-tone-focused distance was 0.22967. This is the intended result: essentially the same path signature but a different temporal response signature.

### B. Observer projection

| Observer | Projection determinant | Measured phase |
|---|---:|---:|
| Identity | 1.0 | 2.63893679 |
| Area-preserving stretch | 1.0 | 2.63893679 |
| Rotation | 1.0 | 2.63893679 |
| Y contraction by 1/2 | 0.5 | 1.31946840 |
| Rank-one projection | 0.0 | 0.0 |

The observer can preserve, rescale or erase this particular measured geometric quantity. This does not mean all observations are equally valid; it makes the information discarded by a projection visible.

### C. Stable limiting cycle

The model used \(\kappa=0.7\). Regression on the log radial error recovered \(0.7000000000000001\). Per-cycle phase accumulation approached the limiting value \(\pi(1)(0.8)=2.51327412\) from above as the transient decayed.

### D. Filtering trade-off

A 25-sample moving average was applied to a synthetic mixture containing 2 cycles of a desired low-frequency component and 80 cycles of a high-frequency component across the same observation interval.

- MSE to the low-frequency target fell from 0.125 to 0.000424.
- The same filter retained only about 5.1% of the high-frequency component's RMS amplitude.

This is why "filter any degree of noise" needs qualification: a filter can suppress noise when there are usable assumptions about its frequency, structure or statistics. It cannot know whether an overlapping component is noise or meaningful signal without additional information. The same filter that removes high-frequency noise can erase high-frequency content.

## 5. Connection to the user's bicycle analogy

A bicycle is a rich dynamical example, but not because a simple geometric shape stays upright by itself. Canonical Whipple–Carvallo bicycle models analyze coupled lean and steer dynamics, nonholonomic constraints, and speed-dependent eigenvalues. Some benchmark configurations exhibit self-stability over certain speed ranges even without rider steering input; actual behavior also depends on geometry, mass distribution, tires, frame compliance, rider posture and control.

The useful analogy is therefore **dynamic stability of a coupled system**, not a universal claim that motion automatically stabilizes every shape.

## 6. Research connection

A direct, closely related body of mathematics is geometric mechanics / geometric phase:

- Kelly (1995), *Geometric phases and robotic locomotion*, studies locomotion generated by cyclic shape changes using differential geometry and geometric phase: https://doi.org/10.1002/rob.4620120607
- Rieser et al. (2024), *Geometric phase predicts locomotion performance in undulating living systems across scales*, applies the framework across living systems: https://www.pnas.org/doi/10.1073/pnas.2320517121
- Htet & Ishimoto (2026), *Data-driven geometric phase in biological locomotion*, published 30 October 2026, uses a theory-guided Koopman approach to recover limit cycles and geometric phase from noisy, sparse and weakly periodic biological data, and introduces a phase-sensitivity function: https://doi.org/10.1103/qlj7-1kvn
- Meijaard et al. (2013), *Linearized dynamics equations for the balance and steer of a bicycle*, provides benchmark bicycle equations and eigenvalue-based self-stability analysis: https://doi.org/10.20537/nd1302010

These works motivate the mathematics, but the toy experiment here does not reproduce their biological or mechanical models.

## 7. Proposed relation to the Virtual Layer

A next-stage abstraction could describe:

\[
\mathcal M=\text{state / shape space},\qquad
\gamma:[0,T]\to\mathcal M,
\]

\[
\omega_O=\text{observer-specific response 1-form},\qquad
\Gamma_O[\gamma]=\int_\gamma\omega_O,
\]

\[
\nu_O(t)=\omega_O(\gamma(t))(\dot\gamma(t)),\qquad
\mathcal I=\text{intention selecting measured features}.
\]

This is a candidate generalization of "tone" as a response to movement through a space. The unresolved challenge is deriving \(\omega_O\) from codonic semantics, state transitions or sensor dynamics rather than choosing it by hand.

The next mathematical extension should test this over a path on S³ with a clearly specified connection or over a codonic state-transition graph with an edge-weighted discrete connection. The RNS metric, SHA-derived identity address and original quaternion address should remain distinct from response-derived quantities until their relationships are derived.

## 8. Limitations

1. The configuration space is \(\mathbb R^2\), not S³. This makes the first line-integral experiment transparent; it does not establish the right manifold for all Virtual Layer representations.
2. The connection is selected analytically. A physical or codonic derivation is still missing.
3. The observer is a simple linear projection; real sensors have nonlinearities, noise, memory and calibration error.
4. Intention weights are task definitions, not intrinsic semantic values.
5. The stability model is a designed normal form, not a learned property of a codonic algorithm.
6. The noise experiment assumes separated frequency bands. Arbitrary noise suppression is impossible without assumptions, redundancy or extra observations.
7. A path-level invariant can still be observer-specific; invariance is always relative to a specified transformation class and measurement rule.

## 9. Reproducibility

```bash
python -m unittest -v
python vl_shape_dynamics.py > build_02_report.json
```

Expected: 10 tests pass. The generated JSON report records the complete numerical findings.
