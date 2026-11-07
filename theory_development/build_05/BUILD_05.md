# Build 05 — Active Observation and Intention-Conditioned Probe Selection

**Research line:** S³ / codonic algebra / observer-dependent geometry  
**Build:** 05  
**Status:** 17/17 unit tests pass; deterministic synthetic benchmark generated  
**Dependencies:** Python 3.10+, standard library only

## 1. Question

Can an observer choose which mathematical transformation or measurement to apply next, based on (a) what it can observe, (b) what it currently believes, (c) what it is trying to distinguish, and (d) the uncertainty and cost of each available probe?

This build isolates that question before integrating the selection policy with the S³/Hopf geometry from Build 04.

## 2. Model

A candidate structure is represented by a matrix hypothesis:

\[
H_h \in \mathbb R^{2\times 2}.
\]

A probe loads a normalized input direction:

\[
u_p \in \mathbb R^2, \qquad \|u_p\|_2=1.
\]

The output is computed using the local codonic scalar algebra:

\[
 y_h = H_h u_p,
\]

where each matrix-vector row is evaluated by two `mx` operations followed by `ad` accumulation. `ld` denotes loading the probe input. The codon aliases can be renamed without changing the operations.

An observer selects output channels using a projection \(P_O\), with channel gains \(G_O\):

\[
\mu(h,p,O)=P_O G_O H_h u_p.
\]

The measurement model is:

\[
Y=\mu(h,p,O)+\epsilon, \qquad
\epsilon\sim\mathcal N(0,\Sigma_O).
\]

The four synthetic structures are:

\[
H_0=\begin{bmatrix}1&0\\0&1\end{bmatrix},\quad
H_1=\begin{bmatrix}1&1.1\\0&1\end{bmatrix},
\]

\[
H_2=\begin{bmatrix}1&0\\1.1&1\end{bmatrix},\quad
H_3=\begin{bmatrix}1&0.8\\0.8&1\end{bmatrix}.
\]

Candidate probes:

| Probe | Input | Relative cost |
|---|---|---:|
| `probe_x` | `(1, 0)` | 1.0 |
| `probe_y` | `(0, 1)` | 1.0 |
| `probe_diagonal` | `(1/√2, 1/√2)` | 2.6 |

The costs are experimental relative units, not measured hardware or sensor costs. The diagonal probe has the largest raw information gain for full identification, but its higher assumed cost can make the basis probes preferable per unit cost.

## 3. Intention is a target variable

An intention does not change the underlying matrix. It defines which distinctions matter.

Three targets are tested:

- `identify_structure`: distinguish all four hypotheses.
- `locate_upper_coupling`: determine whether the upper-right coupling is present.
- `locate_lower_coupling`: determine whether the lower-left coupling is present.

Formally, each intention supplies a target map:

\[
g_I:\mathcal H\rightarrow\mathcal Z_I.
\]

The observer seeks information about \(Z_I=g_I(H)\), not necessarily the full hidden hypothesis \(H\).

This is the operational interpretation of intention in this build: a task-conditioned objective over possible observations.

## 4. Probe selection

For a candidate probe, observer, intention and current prior, the target expected information gain is:

\[
\operatorname{EIG}(p;O,I,\pi)
=I(Z_I;Y\mid p,O,\pi).
\]

Equivalently:

\[
\sum_z p(z)\int p(y\mid z,p,O)
\log_2\frac{p(y\mid z,p,O)}{p(y\mid p,O)}\,dy.
\]

The implementation approximates this integral with a 5-point tensor-product Gauss-Hermite quadrature for the one- or two-channel Gaussian mixture.

To avoid selecting a probe that is informative only under the nominal noise setting, it evaluates two noise scales and uses the worse result:

\[
\operatorname{REIG}(p)=\min_{\rho\in\{1,2\}}
\operatorname{EIG}(p;\Sigma_O\rho^2).
\]

The selection score is:

\[
\boxed{U(p)=\frac{\operatorname{REIG}(p)}{c(p)}}
\]

The probe with the highest utility is selected. After its observation, Bayesian updating produces a new posterior:

\[
p(h\mid y,p,O)\propto p(h)\,p(y\mid h,p,O).
\]

The next probe is selected using that updated posterior. This is the active loop.

**Important qualification:** this is robust only across the two specified observation-noise scales. It does not yet optimize against uncertain priors, arbitrary model misspecification, correlated noise or adversarial observations.

## 5. Observer and intention results

The selected first probe changes with observer and intention.

| Observer | Identify structure | Upper coupling | Lower coupling |
|---|---|---|---|
| Full | `probe_y` | `probe_y` | `probe_x` |
| X channel only | `probe_y` | `probe_y` | `probe_y` (weak residual information) |
| Y channel only | `probe_x` | `probe_x` (weak residual information) | `probe_x` |
| Noisy full | `probe_y` | `probe_y` | `probe_x` |

The weak residual information entries are not equivalent to full observability. In this four-hypothesis design, the bidirectional hypothesis shares one coupling with each one-directional hypothesis. A one-channel observer can therefore obtain partial information about the opposite coupling by detecting the bidirectional case, but cannot cleanly distinguish all cases.

For the full observer, the first-probe robust EIG for full identification is approximately:

| Probe | Nominal EIG (bits) | Worst tested EIG (bits) | Cost-adjusted utility |
|---|---:|---:|---:|
| `probe_y` | 1.3164 | 0.9973 | 0.9973 |
| `probe_x` | 1.3164 | 0.9973 | 0.9973 |
| `probe_diagonal` | 1.9718 | 1.4330 | 0.5511 |

The diagonal probe carries more raw information, while the basis probes deliver more robust information per assumed unit cost.

## 6. Sequential demonstration

The active example starts with a uniform prior and a true `H1_upper_coupling` structure. The policy chooses `probe_y`. Its observed response is sufficiently discriminative that the posterior passes the configured 0.995 confidence threshold after one probe. It therefore stops without performing an unnecessary second measurement.

In other episodes, the first probe leaves a pair of hypotheses observationally equivalent. The updated posterior then drives the selection of a complementary probe.

This demonstrates intention-conditioned active measurement in a finite model, not a universal strategy for arbitrary state spaces.

## 7. Policy evaluation

Four policies were compared under the same two-probe budget:

1. `active`: select each probe from current observer, intention and posterior.
2. `fixed_probe_x_repeat`: repeatedly use the x-basis probe.
3. `fixed_complementary_xy`: precommit to x then y.
4. `random`: choose a probe uniformly at random.

At the nominal noise level, 160 deterministic Monte Carlo trials were run (40 for each true hypothesis).

| Policy | Full-hypothesis accuracy | Mean probe cost |
|---|---:|---:|
| Active | 100.0% | 1.913 |
| Fixed x repeated | 72.5% | 1.925 |
| Fixed complementary x-y | 100.0% | 1.894 |
| Random | 95.6% | 2.548 |

95% Wilson intervals are included in the JSON report. With 160 trials, a displayed 100% accuracy has a lower Wilson bound below 100%; it is not a proof of perfect generalization.

**Interpretation:** active selection outperforms repeatedly applying one fixed probe and is more cost-efficient than the random policy in this fixture. It matches a preplanned complementary pair. It does not beat an already-known optimal fixed design in this small, stationary problem. The value of active selection is its ability to condition decisions on observer and task, update after each result, and stop when the target is sufficiently resolved.

## 8. Noise sensitivity

The full observer's base channel noise standard deviation is 0.12. The report evaluates factors 0.5, 1, 2, 4 and 6. Each factor uses 240 trials (60 per true hypothesis) per policy.

Approximate full-hypothesis accuracy:

| Noise multiplier | Active | Fixed x-y | Fixed x repeated | Random |
|---:|---:|---:|---:|---:|
| 0.5× | 100.0% | 100.0% | 75.0% | 94.2% |
| 1× | 100.0% | 100.0% | 73.3% | 94.2% |
| 2× | 95.4% | 97.1% | 70.0% | 86.3% |
| 4× | 72.5% | 72.1% | 49.6% | 63.7% |
| 6× | 51.7% | 59.6% | 45.0% | 48.3% |

The confidence intervals overlap for some policy comparisons; the small synthetic study does not establish a broad superiority claim. All methods lose discriminative performance as noise becomes large relative to the response differences.

This is a central negative result for the project: sensor tuning and optimal probe choice can improve signal extraction under a model, but cannot recover information that is absent or overwhelmed without additional assumptions or independent measurements. No general-purpose filter removes arbitrary degrees of noise while preserving all signal.

## 9. What remains invariant, what changes

The model separates three layers:

1. **Underlying structure:** the hypothesis matrix; immutable during observation.
2. **Observer projection:** which output channels are available and their gains/noise.
3. **Intention:** which property of the hidden structure is the current target.

The same matrix can yield different observed responses under different observers. The same observer can select different probes for different intentions. Neither operation mutates the underlying matrix.

This is consistent with the larger research direction: observer-relative measurement geometry can change while the described object remains fixed. However, this experiment does not yet establish a shared invariant across S³ paths or sensory modalities.

## 10. Implementation scope and limitations

- Four hand-constructed 2×2 linear hypotheses; not an open-ended algorithm registry.
- Three normalized probes; their relative costs are assumed.
- Independent Gaussian noise with known covariance; no correlated or heavy-tailed noise.
- Uniform prior for standard report evaluations; prior misspecification is not yet stress-tested.
- EIG is a deterministic quadrature approximation, not a closed-form exact value.
- Codonic `mx` and `ad` operations execute the matrix-vector response. `ld` denotes the loaded probe input. This is a minimal local interpreter, not the full VL codon VM.
- The active observer is not yet operating directly over S³, Hopf fibres, RNS/CRT, Feistel or SHA-256 addresses.

## 11. Next build

Build 06 will attach this active-probe policy to the S³/Hopf transport model. Candidate probes will include local tangent perturbations, closed-loop path variants, fibre-sensitive measurements and base-space projections. The test will ask whether active selection can distinguish two paths that the base observer regards as equivalent but the lifted S³ observer does not.
