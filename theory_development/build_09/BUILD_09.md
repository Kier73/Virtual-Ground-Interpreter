# Build 09 — Cross-modal response geometry

**Virtual Layer research series**  
**Status:** Complete synthetic benchmark  
**Tests:** 24 / 24 passing  
**Runtime:** Python standard library only

## 1. Research question

Can distinct system realizations produce corresponding relational response geometry when they are interrogated with matched probes?

The build compares:

1. An acoustic-like second-order digital resonator.
2. A mechanical single-degree-of-freedom mass-spring-damper oscillator.

Each family is generated from matched natural frequency and damping ratio parameters. The two domains use different computational realizations: a digital recurrence versus a continuous-time differential equation integrated with RK4.

**Critical limitation:** both systems are deliberately parameterized to share the same second-order pole structure. Near-identical linear-response geometry is therefore an expected positive-control result. It validates the measurement pipeline's ability to recover a shared dynamical law; it does not establish a universal cross-modal invariant or prove that arbitrary acoustic and mechanical systems share geometry.

## 2. System models

### 2.1 Acoustic-like digital resonator

The recurrence is:

\[
y[n]=b_0x[n]+a_1y[n-1]+a_2y[n-2]
\]

with damped pole radius and angle derived from target frequency and damping:

\[
r=e^{-\zeta\omega_n/f_s},\qquad
\theta=\frac{\omega_n\sqrt{1-\zeta^2}}{f_s}
\]

\[
a_1=2r\cos\theta,\qquad a_2=-r^2,\qquad b_0=1-a_1-a_2
\]

A separate sensor gain is applied after the recursive state update. This separation was explicitly checked so sensor calibration does not inadvertently alter the plant poles.

An optional smooth output-compression stage is applied only in the high/low-amplitude stress probe.

### 2.2 Mechanical oscillator

The mechanical model is:

\[
m\ddot{x}+c\dot{x}+kx+\beta x^3=F(t)
\]

with:

\[
\omega_n=2\pi f_0,\quad k=m\omega_n^2,\quad c=2\zeta m\omega_n
\]

The linear run sets \(\beta=0\). The nonlinear stress run enables a positive cubic stiffness term. The equations are integrated with four RK4 substeps per sample.

The model is single-degree-of-freedom; coupled mechanical modes are deferred to the next build.

## 3. Matched probes

Both systems receive the same normalized-time probe families:

- Unit impulse / initial-velocity response.
- Step force.
- Tapered linear chirp from 2 to 24 Hz.
- Low-amplitude 10 Hz tone.
- High-amplitude 10 Hz tone.

The principal run uses 128 Hz sampling, 1,024 samples and an eight-second observation window. A sample-rate sweep additionally uses 64 Hz / 512 samples and 256 Hz / 2,048 samples while preserving the eight-second physical duration.

## 4. Observer feature representations

The build creates eight feature representations independently within each domain:

| Observer | Features |
|---|---|
| Spectral | Gain-normalized log impulse-spectrum magnitudes, 3–24 Hz |
| Phase | Unwrapped phase of the impulse spectrum |
| Temporal | Log RMS envelope over 16 time windows |
| Step | Relative final value, overshoot, undershoot, settling and rise-time fractions |
| Modulation | Local-RMS envelope mean, variation, adjacent variation and range |
| Transfer | Chirp-derived transfer magnitude and phase samples |
| Amplitude | Low/high response gain and amplitude sensitivity |
| Modal | Peak frequency, settling fraction, overshoot and decay contrast |

The local-RMS modulation features are signal descriptors only. They are not calibrated measures of auditory roughness, tactile roughness, emotional arousal, or subjective tone. This distinction is important: a research review finds that auditory roughness is commonly analyzed as a temporal feature, while tactile/visual roughness typically involves spatiotemporal surface structure; the same everyday word does not guarantee the same underlying perceptual construct.

## 5. Codonic execution

A minimal executable arithmetic subset is used inside the recurrence and ODE update functions:

| Codon | Local meaning |
|---|---|
| `ld` | Load / pass an operand |
| `ad` | Addition |
| `su` | Subtraction |
| `mx` | Multiplication |
| `dv` | Division |
| `pw` | Integer power |
| `st` | Store / return result |

The acoustic recurrence uses the operation pattern:

`ld · mx · ad · mx · ad · st`

The mechanical acceleration update uses:

`ld · mx · su · mx · su · dv · st`

The nonlinear mechanical variant additionally invokes `pw` and `mx` for the cubic stiffness term.

The registry can be renamed. An alternate registry (`load`, `plus`, `minus`, `times`, `divide`, `pow`, `write`) was executed against the same test systems. Maximum output difference was exactly zero in the tested deterministic run.

This is a local executable subset and a model of the codonic approach; it is not yet a compiler for the complete Virtual Layer registry.

## 6. Main results

### 6.1 Matched-domain relational geometry

| Feature observer | RDM Spearman \(\rho\) | Permutation p | Holm-adjusted p | Family bootstrap 95% interval | Paired profile retrieval |
|---|---:|---:|---:|---:|---:|
| Spectral | 0.9999999 | 0.002 | 0.016 | [0.999997, 1.000] | 1.000 |
| Phase | 0.9999999 | 0.002 | 0.016 | [0.999998, 1.000] | 1.000 |
| Temporal | 0.9999998 | 0.002 | 0.016 | [0.999996, 1.000] | 1.000 |
| Step | 0.9755 | 0.002 | 0.016 | [0.9640, 0.9827] | 0.675 |
| Modulation | 0.1876 | 0.004 | 0.016 | [-0.0481, 0.3672] | 0.100 |
| Transfer | 0.8940 | 0.002 | 0.016 | [0.8591, 0.9288] | 0.450 |
| Amplitude | 0.1155 | 0.116 | 0.116 | [-0.0958, 0.3179] | 0.125 |
| Modal | 0.9929 | 0.002 | 0.016 | [0.9868, 0.9962] | 0.875 |

Permutation p-values use 499 system-label permutations, so the minimum attainable value is 0.002. Holm adjustment is applied across the eight predeclared same-feature cross-domain comparisons. Values are exploratory; no confirmatory claim is made. Bootstrap resampling is over families rather than treating pairwise RDM cells as independent samples.

**Interpretation:** linear spectral, phase, temporal, and modal response profiles align strongly across the two realizations, as expected from their shared second-order dynamics. Modulation and amplitude features align much less. These less-aligned channels are candidates for studying domain-specific nonlinear response, sensor properties, or mismatched feature definitions.

### 6.2 Cross-observer comparisons

The highest cross-observer RDM correlation is acoustic modal versus mechanical transfer (0.3342), followed by acoustic spectral versus mechanical transfer (0.2712) and acoustic modal versus mechanical spectral (0.2813). These are lower than same-observer/same-feature pairings and should be treated as exploratory.

### 6.3 Sampling-rate invariance

The rank geometry of the spectral representation was retained across the tested sampling rates:

| Domain | 64 Hz vs 128 Hz | 256 Hz vs 128 Hz |
|---|---:|---:|
| Acoustic-like | 0.9962 | 0.9995 |
| Mechanical | 0.9962 | 0.9995 |

This tests rank geometry at fixed physical duration and natural frequencies, not waveform identity at different sampling rates.

### 6.4 Unit/calibration scaling

A coordinated sensor-gain rescaling (and, for the mechanical model, a matching mass/damping/stiffness unit rescaling) preserved RDM rank geometry at 1.000 for all tested normalized feature families.

This result is a controlled unit-change property of the model and feature normalization, not a general claim that all observers are scale invariant.

### 6.5 Measurement degradation

Acoustic spectral RDM retention remained high under standardized feature noise:

| Noise SD | Mean RDM retention |
|---:|---:|
| 0.00 | 1.0000 |
| 0.05 | 0.9998 |
| 0.10 | 0.9994 |
| 0.20 | 0.9977 |
| 0.40 | 0.9893 |

Feature-channel dropout also retained the rank structure in this controlled library:

| Retained feature fraction | Mean RDM retention |
|---:|---:|
| 1.00 | 1.0000 |
| 0.75 | 0.9975 |
| 0.50 | 0.9944 |
| 0.25 | 0.9854 |

These values are high partly because the generated families span a broad frequency/damping range and the features are repeated samples of the same underlying second-order system. A more heterogeneous, empirically measured set may be less robust.

### 6.6 Nonlinear amplitude response

The input high/low amplitude ratio is 6.0. Mean measured output RMS ratios were:

| Domain | High/low output RMS ratio | Deviation from linear ratio |
|---|---:|---:|
| Acoustic-like output compressor | 2.2596 | 0.6234 |
| Mechanical cubic stiffness | 5.9842 | 0.0063 |

The acoustic output stage compresses strongly in this selected range. The mechanical Duffing-like term is comparatively weak at the chosen amplitudes and parameter range. This is an intentional negative/weak result: the current mechanical nonlinear stress probe is not yet strong enough to produce a large shift. The two mechanisms are not equivalent and should not be forced into one feature interpretation.

## 7. What this build establishes

1. A codonic arithmetic subset can execute both a digital second-order recurrence and an RK4 mechanical state update.
2. Renaming the arithmetic codons leaves these tested computations unchanged.
3. Distinct computational realizations with matched pole parameters can produce strongly aligned relational response geometry.
4. Response dimensions that share the same underlying dynamics align much more strongly than amplitude/modulation dimensions that are affected by domain-specific measurement and nonlinear stages.
5. The tested normalized RDMs survive coordinated unit rescaling and moderate measurement degradation.

## 8. What it does not establish

- It does not establish a universal geometry of meaning.
- It does not demonstrate that arbitrary acoustic and material systems are isomorphic.
- It does not measure human emotional tone or affective response.
- It does not show that an acoustic resonator is physically equivalent to a material surface.
- It does not demonstrate a computational speedup over conventional processing.
- It does not yet use measured physical datasets or human observer ratings.

The strongest same-feature alignments are expected because the two systems were generated from matched second-order dynamics. Build 10 should challenge this by adding non-matched, coupled, multi-mode and empirical systems, then testing whether the common response representation still predicts relational neighborhoods.

## 9. Interpretation for the Virtual Layer

The most defensible current interpretation is:

\[
\text{System description}
\rightarrow
\text{Probe response}
\rightarrow
\text{Observer features}
\rightarrow
\text{Relational geometry}
\]

The codonic representation provides an algebraic description of how each model transforms input into state and output. The response signatures characterize the model under specified probes. RDMs compare the resulting neighborhoods without requiring the raw feature coordinates to match.

This is a viable experimental bridge between codonic algebra and response-based geometry. The next build must avoid baking shared geometry into the generator parameters and then interpreting its recovery as an independent discovery.

## 10. Selected literature

See `SOURCES.md` for the source list. Particularly relevant is Di Stefano & Spence (2022), which cautions that auditory roughness and tactile/visual roughness refer to partly different temporal and spatiotemporal phenomena. That warning reinforces why this build reports mathematical signal descriptors rather than labelling them as a universal perceptual roughness scale.
