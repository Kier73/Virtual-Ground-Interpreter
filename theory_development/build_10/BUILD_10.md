# Build 10 — Heterogeneous systems and active probing

**Virtual Layer research series**  
**Status:** Complete synthetic benchmark  
**Tests:** 25 / 25 passing  
**Runtime:** Python standard library only  
**Primary seed:** `20261105`

## 1. Research question

Build 09 compared a digital second-order resonator with a mechanical oscillator after deliberately matching their natural frequency and damping ratio. Their linear response geometries aligned almost perfectly, as expected from their shared second-order pole structure.

Build 10 removes that matched-model assumption. It asks:

> Does cross-domain relational response geometry remain when the underlying systems have independently drawn parameters, different structural orders, coupling, damping, anti-resonance-like readouts, and nonlinearities?

A second question integrates Build 05's active observer:

> Can selecting probes adaptively improve identification of an unknown structural class compared with a fixed or random probe schedule?

All Build 10 plants and signals are synthetic. No synthetic trace is described as human emotional tone or as a measurement of biological perception.

## 2. Heterogeneous system models

### 2.1 Acoustic-like modal network

Each system is a bank of two or three discrete-time second-order resonant modes. For mode `i`:

\[
y_i[n] = b_{0,i}u_i[n] + a_{1,i}y_i[n-1] + a_{2,i}y_i[n-2]
\]

with poles parameterized by a modal frequency and damping ratio. The modal drive includes weak directed cross-feed from prior modal outputs. The observed output is a weighted sum of modal states.

Additional variations include:

- two or three modes;
- random signed modal residues;
- optional second-order notch filter (anti-resonance-like spectral trough);
- low and stronger smooth output compression;
- system-specific gain and sample delay.

The notch-depth feature is a spectral-trough proxy. It is not a calibrated physical anti-resonance estimator.

### 2.2 Coupled mechanical two-degree-of-freedom system

The mechanical system is:

\[
M\ddot q + C\dot q + Kq + f_{nl}(q) = Bu(t)
\]

where `M`, `C`, and `K` are independently generated symmetric 2×2 mass, damping, and stiffness matrices. State evolution is integrated with RK4.

Four structural variations are sampled:

1. Proportional damping: \(C=\alpha M+\beta K\).
2. Non-proportional damping: an independently generated positive-definite damping matrix.
3. An output/sensor mixture with cancellation-prone readout.
4. Cubic local and coupled stiffness nonlinearities.

A relative damping non-proportionality index is calculated as the normalized Frobenius residual after the best fit \(C\approx\alpha M+\beta K\). It is a diagnostic for this generated matrix family, not a universal damping metric.

The cubic mechanical terms are parameterized dimensionlessly relative to a reference displacement. This makes the nonlinear stress cases measurable at the selected excitation amplitudes.

### 2.3 Independence of the two domains

Acoustic and mechanical parameter draws use independent random streams. No acoustic resonant frequency is paired to a mechanical eigenfrequency. Each domain contains 32 independently generated systems, sampled across four structural classes.

The two domains do share broad observation conditions (duration and probe families), because response comparisons require a common experimental protocol. That does not mean their internal parameters or equations are matched.

## 3. Probe library

Every system is tested with five probes:

- impulse;
- step;
- tapered chirp;
- multisine;
- amplitude staircase.

The observer receives only the response-derived feature vector for the selected probe. It does not receive the generating parameters.

## 4. Response features

Each probe produces 33 scalar features:

- input/output log gain;
- crest factor and zero-crossing rate;
- spectral centroid, bandwidth, flatness, and peak frequency;
- four broad-band energy proportions;
- log-envelope decay and late/early energy ratio;
- sixteen normalized log spectral-band energies;
- four-block gain span and gain-vs-input-level slope;
- spectral peak count and a trough-depth proxy.

See `feature_schema.csv` for the complete index map.

These are engineering signal descriptors. The feature names do not imply that they are direct measures of subjective roughness, valence, arousal, or perceived vocal tone.

## 5. Cross-domain geometry comparison

### 5.1 Why there is no paired RDM correlation

The two domains are independently sampled. There is no justified one-to-one mapping between acoustic system 7 and mechanical system 7. Therefore, Build 10 deliberately does **not** report a cross-domain paired RDM correlation.

Instead, it compares unpaired summaries of within-domain relational geometry:

1. each system's five probe signatures are averaged into a compact 17-dimensional summary;
2. within-domain RDMs are constructed separately;
3. normalized distance quantiles and normalized minimum-spanning-tree edge distributions are compared;
4. trace-normalized covariance eigenvalue spectra are compared;
5. a column-shuffled null independently permutes each feature across systems within each domain, preserving feature marginals while disrupting cross-feature and row-wise relationships.

This is a distributional geometry comparison, not proof that individual systems in different domains correspond.

### 5.2 Results

| Statistic | Observed | Column-shuffled null | Interpretation |
|---|---:|---:|---|
| Covariance-spectrum cosine similarity | 0.9777 | mean 0.9950; 95th percentile 0.9984 | Observed similarity is not unusually high |
| Normalized distance-quantile gap | 0.0713 | mean 0.0255; 5th percentile 0.0100 | Observed distributions are not unusually close |
| Normalized MST-edge Wasserstein gap | 0.0719 | mean 0.0533; 5th percentile 0.0303 | No evidence of unusually similar MST profiles |

Empirical one-sided null probabilities:

- covariance similarity upper-tail: `p = 0.995`;
- distance-profile gap lower-tail: `p = 1.000`;
- MST-profile gap lower-tail: `p = 0.860`.

**Main result:** this benchmark does not detect a shared cross-domain relational geometry beyond the selected feature-shuffled control. The near-perfect Build 09 alignment was strongly dependent on its matched second-order dynamics. This is a useful negative result: it prevents the earlier positive control from being promoted into a general invariant claim.

The null is a specific control, not an exhaustive model of all possible chance geometries. The finite generated bank and selected 17-D summary also limit generalization.

## 6. Active observer experiment

The observer is trained on 12 examples per structural class and evaluated on 32 independently generated held-out cases per domain (8 per class). All three policies see the same held-out systems and the same probe-specific feature-noise draws.

Policies:

- **Active:** approximate expected information gain per probe cost, recalculated after each observation.
- **Fixed:** a static three-probe order ranked once from the training set under a uniform prior.
- **Random:** a seeded random choice without replacement.

The expected-information calculation uses a transparent three-point approximation along the single most discriminative feature coordinate. It is not an exact multivariate mutual-information integral.

### Results

| Domain | Policy | Accuracy | Wilson 95% interval | Brier score |
|---|---|---:|---:|---:|
| Acoustic-like | Active | 31.3% | 18.0–48.6% | 1.349 |
| Acoustic-like | Fixed | 37.5% | 22.9–54.7% | 1.206 |
| Acoustic-like | Random | 31.3% | 18.0–48.6% | 1.281 |
| Mechanical | Active | 50.0% | 33.6–66.4% | 0.939 |
| Mechanical | Fixed | 46.9% | 30.9–63.6% | 1.006 |
| Mechanical | Random | 53.1% | 36.4–69.1% | 0.842 |

Four-class chance accuracy is 25%. Confidence intervals are broad and overlap. Active selection is not a consistent winner: fixed probing is best in the acoustic-like case, while random is best in the mechanical case. Active probing has a slight accuracy advantage over fixed in the mechanical case, but not over random.

**Interpretation:** the current approximate myopic EIG policy is not yet a reliable advantage. It may be limited by the Gaussian class model, training-set size, the feature representation, probe costs, or the structural classes themselves. Build 11 should improve calibration and compare richer design criteria rather than assume active observation is superior.

## 7. Nuisance transformations

### 7.1 Sampling rate

The same 12 systems per domain are evaluated at 128, 256, and 512 Hz while holding physical duration at two seconds and setting built-in sample delays to zero for this specific sweep.

| Domain | 128 vs 256 Hz RDM rank retention | 512 vs 256 Hz |
|---|---:|---:|
| Acoustic-like | 0.935 | 0.980 |
| Mechanical | 0.961 | 0.978 |

The tested relational ordering is mostly retained, but it is not perfectly sampling-rate invariant.

### 7.2 Sensor transfer function

The same plants are passed through an additional first-order low-pass sensor, gain 1.7, and physical delay 8 ms.

| Domain | Sensor cutoff | RDM rank retention |
|---|---:|---:|
| Acoustic-like | 24 Hz | 0.965 |
| Acoustic-like | 48 Hz | 0.983 |
| Acoustic-like | 72 Hz | 0.982 |
| Mechanical | 24 Hz | 0.898 |
| Mechanical | 48 Hz | 0.914 |
| Mechanical | 72 Hz | 0.912 |

Sensor transfer characteristics alter the measured relational geometry, especially in the mechanical sample. This reinforces the need to separate plant dynamics from sensor response.

### 7.3 Feature-space noise

Feature-space perturbations are tested under Gaussian, Laplace, and uniform distributions. At noise scale 0.5 standardized units, RDM rank retention remains approximately 0.987–0.990 for both domains in this generated bank. This is robustness of the chosen feature-space ranks, not a general denoising guarantee and not a raw-sensor SNR result.

## 8. Codonic algebra

The local executable codon subset is:

| Codon | Operation |
|---|---|
| `ld` | Load / pass operand |
| `ad` | Addition |
| `su` | Subtraction |
| `mx` | Multiplication |
| `dv` | Division |
| `pw` | Integer power |
| `st` | Store / return |

The same mechanical trace is executed with alternate names (`load`, `plus`, `minus`, `times`, `divide`, `pow`, `write`). Maximum output discrepancy is exactly zero in the deterministic check.

This is an executable local subset, not a compiler for the full Virtual Layer registry.

## 9. What this build establishes

1. Heterogeneous modal networks and coupled mechanical systems can be simulated and interrogated under common probes without parameter matching.
2. The Build 09 cross-domain near-identity result does not generalize to this independently parameterized benchmark under the selected unpaired geometry summaries and shuffled null.
3. Measurement rate and sensor transfer function can alter observer-specific response geometry.
4. The current active-probe policy does not outperform fixed/random policies consistently.
5. Codon aliases can change while local algebraic execution remains identical.

It does **not** establish that no cross-domain invariants exist. A negative result under one model bank, feature family, and null control is narrower: these particular invariants were not detected here.

## 10. Build 11 direction

Move from synthetic-only tests to an empirical bridge with explicit calibration metadata:

- one measured structural-dynamics dataset with impact and random excitation, multiple sensor layouts, and baseline/damaged states;
- one openly licensed acoustic room impulse-response collection;
- a manifest that records sample rate, sensor position, channel, units, excitation, preprocessing, licence, and provenance;
- a plant/sensor decomposition, so sensor filtering is not mistaken for a physical-system property;
- probe selection constrained to measurements that the actual dataset supports;
- a held-out structure/site split to prevent leakage.

Candidate datasets and licensing notes are listed in `NOTES_NEXT.md`. No real-world measurements are bundled with Build 10.
