# Build 06 — Active Observation on S³ / Hopf Geometry

**Research implementation:** configurable codonic arithmetic, Hopf-fibre transport, observer-dependent equivalence, intention-conditioned probe selection.

**Verification:** 31/31 unit tests passed. Python 3.10+, standard library only.

---

## 1. Question

Can an observer actively choose a geometric measurement that distinguishes candidate paths which have the same Hopf-base endpoint but different lifted states or holonomy? When is a distinction genuinely unavailable to an observer, rather than merely not yet measured?

Build 06 connects the active sensing policy from Build 05 to the quaternion/Hopf geometry from Build 04.

## 2. Geometry

A unit quaternion is

\[
q=w+xi+yj+zk,\qquad |q|=1.
\]

The Hopf projection used here is

\[
\pi:S^3\rightarrow S^2,\qquad \pi(q)=qkq^{-1}.
\]

The right fibre action is

\[
q\mapsto qe^{k\beta},
\]

which preserves the Hopf projection. Each base point corresponds to a circle of total-space representatives.

The horizontal lift uses successive minimal rotors. Given neighboring unit base vectors \(n_j,n_{j+1}\), a shortest rotor is constructed from their dot and cross products; then

\[
q_{j+1}=r(n_j,n_{j+1})q_j.
\]

Quaternion Hamilton products are compiled into a scalar codon program using `mx`, `ad`, and `su`. The resulting program contains 28 scalar instructions. Renaming these codons (`plus`, `minus`, `times`, etc.) leaves its numerical result unchanged.

For a closed base path, the relative endpoint is in the fibre:

\[
q_0^{-1}q_T\approx e^{k\varphi}.
\]

The measured phase is

\[
\varphi=\operatorname{atan2}\big((q_0^{-1}q_T)_k,
                                  (q_0^{-1}q_T)_w\big).
\]

For the north-gauge convention and cap loops used here, the expected phase is half the signed solid angle:

\[
\varphi\approx\frac{1}{2}\Omega,
\qquad
\Omega=\oint(1-\cos\theta)\,d\phi.
\]

The numerical path-area integral and discrete horizontal lift are independently calculated and compared.

## 3. Candidate paths

Four candidates are constructed:

| Candidate | Colatitude | Direction |
|---|---:|---|
| `small_forward` | 0.62 rad | + |
| `small_reverse` | 0.62 rad | − |
| `large_forward` | 0.98 rad | + |
| `large_reverse` | 0.98 rad | − |

All four start and end at the north pole in the Hopf base. Their trajectories differ in cap size and orientation.

A separate antipodal control takes one lifted endpoint `q` and compares it with `-q`, keeping the same base path. This is a representation control: the pair is not claimed to be two horizontal lifts of the same fixed connection and initial representative. It tests the difference between retaining the S³ representative and quotienting to SO(3).

## 4. Probe library

| Probe | Measurement | Cost | Noise σ |
|---|---|---:|---:|
| `base_endpoint` | final Hopf-base z coordinate | 0.10 | 0.010 |
| `base_apex` | maximum colatitude of the base trajectory | 0.55 | 0.030 |
| `base_area` | signed solid angle of the full base trajectory | 0.80 | 0.080 |
| `so3_angle` | signed SO(3) rotation about known k axis | 0.70 | 0.050 |
| `s3_phase` | phase relative to fixed S³ reference representative | 0.90 | 0.040 |

Costs and noise levels are synthetic relative units. The `so3_angle` probe is not a generic arbitrary-axis SO(3) sensor: it measures a signed rotation about the known fibre axis k for this controlled candidate family.

## 5. Observer families

- **Endpoint-only:** sees the final Hopf-base endpoint.
- **Base-path:** sees endpoint, maximum colatitude, and full oriented base-path area.
- **SO(3):** sees endpoint and signed k-axis rotation, which identifies `q` and `-q`.
- **S³ lift:** sees endpoint, apex, SO(3) angle, and a phase-sensitive S³ measurement.
- **Hybrid:** has all listed probe families.

The base-path observer can infer the holonomy from a complete base trajectory because the selected connection convention relates holonomy to oriented area. Therefore fibre phase is hidden from an endpoint-only observer, not from every possible base-path observer.

## 6. Observer-specific equivalence (finite observable quotient)

For observer \(O\), define

\[
h_1\sim_O h_2
\iff
p(y\mid h_1,p,O)=p(y\mid h_2,p,O)
\quad\text{for every admissible probe }p\in\mathcal P_O.
\]

All probes use the same Gaussian noise law per observer, so equality of measurement means is sufficient for equal observation distributions in this finite model. The implementation clusters candidate measurement signatures within numerical tolerance.

### Four regular path hypotheses

| Observer | Observable equivalence classes |
|---|---|
| Endpoint-only | all four candidates in one class |
| Base-path | four singleton classes |
| SO(3) | four singleton classes for this selected family |
| S³ lift | four singleton classes |

The endpoint-only observer cannot distinguish the four loops from their final base point. A base-path observer can distinguish them because it retains trajectory geometry.

### Antipodal control: `q` versus `-q`

| Observer | Result |
|---|---|
| Endpoint-only | one equivalence class |
| Base-path | one equivalence class |
| SO(3) | one equivalence class |
| S³ lift | two equivalence classes |

Mathematically,

\[
d_{S^3}(q,-q)=\pi,
\qquad
 d_{SO(3)}(q,-q)=0.
\]

The Hopf projection and SO(3) rotation representation identify the antipodal representatives; the S³ point representation retains their distinction.

## 7. Intention-conditioned selection

An intention defines which target labels matter, without changing the candidate geometry:

\[
g_I:\mathcal H\rightarrow\mathcal Z_I.
\]

The selector estimates

\[
\operatorname{EIG}(p)=I(g_I(H);Y_p\mid O,\pi_0)
\]

and chooses the probe maximizing robust information gain per cost:

\[
p^*=\arg\max_{p\in\mathcal P_O}
\frac{\min_{\lambda\in\{1,1.5\}}
\operatorname{EIG}(p;\lambda\sigma_O)}{c(p)}.
\]

EIG is approximated using 5-point Gauss-Hermite quadrature for the finite one-dimensional Gaussian mixtures. After a measurement, a Bayesian posterior update is performed. The observer stops when the target posterior reaches 0.995, when the probe budget ends, or when no admissible probe carries positive information about the requested target.

### Selected probes

| Observer | Intention | Selected probe | Robust EIG |
|---|---|---|---:|
| Base-path | cap size | `base_apex` | ~1 bit |
| Base-path | loop orientation | `base_area` | ~1 bit |
| Base-path | full path | `base_area` | ~2 bits |
| SO(3) | full path | `so3_angle` | ~2 bits |
| S³ lift | antipodal representative | `s3_phase` | ~1 bit |
| Endpoint-only | full path | none; unresolved | 0 bits |

A constant target such as “are these endpoints the same?” requires no probe because all candidates share that target label in the fixture. This is reported as `already_resolved`, not as sensor discrimination.

## 8. Numerical results

For the default 48 meridian and 480 latitude samples:

| Candidate | Signed area Ω | Expected Ω/2 | Measured phase | Absolute phase error |
|---|---:|---:|---:|---:|
| small forward | 1.169436 | 0.584718 | 0.584706 | 1.23e−5 |
| small reverse | −1.169436 | −0.584718 | −0.584706 | 1.23e−5 |
| large forward | 2.783309 | 1.391655 | 1.391637 | 1.72e−5 |
| large reverse | −2.783309 | −1.391655 | −1.391637 | 1.72e−5 |

Base endpoint discrepancies are on the order of 10⁻¹⁵, and off-fibre residuals are also on the order of 10⁻¹⁵. The remaining phase error is consistent with finite-step discretization in the sampled horizontal lift.

### Policy evaluation

240 trials were run for each policy on the four-path base-observer task; 200 trials were run for the antipodal task.

| Task | Policy | Resolution rate | Accuracy among resolved | Mean cost |
|---|---|---:|---:|---:|
| Base-path full path | Active | 100% | 100% | 0.80 |
| Base-path full path | Fixed initial best probe | 100% | 100% | 0.80 |
| Base-path full path | Random | 65% | 100% | 0.86 |
| S³ antipodal pair | Active | 100% | 100% | 0.90 |
| S³ antipodal pair | Fixed initial best probe | 100% | 100% | 0.90 |
| S³ antipodal pair | Random | 44.5% | 100% | 1.01 |

Accuracy is conditional on the observer declaring the target resolved. Wilson 95% intervals are included in the JSON report. The active policy matches a fixed best probe in these deliberately simple tasks because one suitable measurement is sufficient. It should not be claimed to outperform a known optimal preplanned probe. Its demonstrated value is choosing different measurement families for different intentions and observer capabilities, and refusing unsupported distinctions.

## 9. Reproducibility and tests

`./run_build.sh` runs the unit suite and regenerates all artifacts. The suite contains 31 tests covering:

- codonic Hamilton multiplication, identity and non-commutativity;
- alias-renaming invariance;
- Hopf projection and fibre invariance;
- horizontal lift and area/phase agreement;
- path reversal and base closure;
- S³/SO(3) antipodal metric distinctions;
- observer-specific observable quotient partitions;
- intention-conditioned probe choice;
- correct unresolved behaviour when no allowed probe distinguishes a target.

## 10. Limitations

- This is a finite synthetic mathematical model, not a live Virtual Layer or full SHA-256/Feistel/RNS/CRT implementation.
- Only two cap sizes and two orientations are used.
- The base-area probe assumes the observer retains the full projected trajectory and knows the connection convention.
- The S³ phase probe uses a fixed reference representative; absolute phase is gauge-dependent. Relative phase/holonomy must specify the reference and transport convention.
- The SO(3) scalar probe is specialized to rotations about known axis k.
- Noise is independent Gaussian with known variance; model mismatch and correlated noise are not explored.
- Probe costs are assumed, not measured hardware costs.
- No emotion labels, biological signals, or physical vibration are inferred.

## 11. Interpretation

Build 06 demonstrates a finite observer-specific quotient: the same candidate set produces different equivalence classes as the admissible probe family changes. Intention changes which distinctions are worth resolving. It does not alter the underlying quaternion paths.

The most important negative result is equally useful: an endpoint-only observer has no information about which of these closed loops occurred. It correctly remains uncertain. Giving that observer a different name or a more elaborate classifier would not create the missing observation.

The antipodal control shows a separate structural distinction: a representation that quotients S³ to SO(3) deliberately discards the `q` versus `-q` distinction. Retaining the S³ representative preserves it.

These are concrete mathematical results within the specified model. They are not yet evidence for a universal invariant meaning space or for physical/emotional resonance in codonic address space.
