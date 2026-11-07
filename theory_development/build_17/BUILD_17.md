# Build 17 — Temporal representations under clock symmetries

## Status

- Build 14 signal-processing pipeline, Build 15 local-clock event graph and Build 16 harmonic/falsification tooling retained.
- Added a common synthetic unlabelled pulse signal with identical event pulse shapes and amplitudes. No event-specific amplitude rank is available to drive correspondence.
- Added finite Fourier magnitude, circular Hann STFT, undecimated Haar-like detail-energy descriptor, finite log-time Mellin magnitude, normalized event intervals, and graph-Laplacian spectral signatures.
- Added controlled circular translation, linear time dilation, monotone quadratic clock drift and log-time dilation.
- Added graph motif-threshold sensitivity and eigenspace-energy comparison under node relabeling.
- Tests: **83 passing**, including inherited Build 14–16 regression coverage.
- All new experiments use generated fixtures. No empirical sensor data or participant data was processed.

## 1. Question

Build 16 established that a finite DFT and a graph Fourier transform are unitary decompositions under their respective inner products, but that fact alone does not tell us whether either basis is appropriate for a temporal process. Build 17 asks:

> Which symmetry action does each representation simplify, and which relationships survive that action?

The goal is not to find one universal transform. It is to identify a small family of representations that each expose a different invariant, covariance or deformation.

## 2. Common controlled signal

A 512-sample signal is generated from ten identical Gaussian event pulses at sample positions:

`[42, 66, 96, 128, 176, 213, 271, 319, 391, 447]`.

Every pulse has the same amplitude and width. This removes event-specific marks and global mark-rank as a source of alignment information. The experiment does not claim the event positions were recovered from a noisy sensor; they are known fixture construction inputs.

Transformations:

- Circular translation: 32 samples.
- Time dilation: factor 1.15 about the signal midpoint.
- Nonlinear local-clock deformation: `phi(t) = t + 0.35*T*(t/T)^2`, where `T` is the final sample coordinate. Its derivative is positive over the tested domain.
- Log-time dilation: an eight-sample circular shift on a 256-sample log-time grid of period 6.

## 3. Results

### 3.1 Fourier magnitude

The unitary finite DFT magnitude has circular-shift relative error:

`4.90e-14`.

This is numerical roundoff: for a circular shift, the DFT coefficients acquire a linear phase factor while their magnitudes remain unchanged. Under the 1.15 time dilation, same-bin magnitude relative difference is `0.589`; the spectral centroid moves from `0.03386` to `0.02823` cycles/sample (ratio `0.834`). The ideal inverse scale is approximately `0.870`; finite support, interpolation and boundary behavior account for the deviation.

**Interpretation:** Fourier magnitude is a translation-invariant summary for the finite cyclic signal. Dilation is a frequency-coordinate covariance, not an invariance at fixed frequency bins. Discarding phase also makes magnitude a lossy summary; it is not a complete signal identifier.

### 3.2 STFT

For a 64-sample circular Hann window and 16-sample hop, a 32-sample circular shift exactly permutes STFT frame columns. The shift-covariance error is `0.0`. The flattened, unaligned STFT field differs by `0.702` after nonlinear clock drift.

**Interpretation:** the STFT is locally informative and covariant to aligned frame shifts. It is not invariant as an indexed time-frequency field. A downstream matcher must account for frame translation and local deformation rather than compare columns as though fixed in time.

### 3.3 Undecimated Haar-like detail energies

The pooled detail-energy descriptor has shift error `0.0`. Under time dilation, its scale moment moves from `4.651` to `4.768` and its energy distribution changes.

**Important scope:** this implementation computes circular, undecimated Haar-like contrasts at dyadic window widths, then pools their squared values. It is a redundant multiscale descriptor, **not** an orthonormal discrete wavelet transform and not a full continuous wavelet transform.

**Interpretation:** pooling over all circular positions makes this descriptor shift invariant. Scale information remains visible in the distribution across levels.

### 3.4 Mellin magnitude

The implemented Mellin case uses the measure `dt/t`, with `u = log(t)`. Under this measure, the Mellin transform is a Fourier transform in log time. A positive-time dilation becomes a translation in `u`.

The 256-sample finite log-grid fixture uses a period of 6; an eight-sample shift corresponds to dilation factor `1.20623`. The Mellin magnitude relative error is `3.24e-14`.

**Important scope:** this is a finite periodic log-grid test on `L²(R₊, dt/t)`. The more common unitary Mellin formulation on `L²(R₊, dt)` includes the corresponding half-power weight (the critical line `Re(s)=1/2`). The test does not claim boundary-free exactness for arbitrary finite nonperiodic data.

### 3.5 Graph Fourier / event-graph spectrum

The event graph has ten nodes. It connects consecutive event nodes and adds recurrence edges when pairs of normalized log-intervals fall within a configured motif tolerance. The node signal is the local mean of adjacent normalized log intervals.

Under an affine clock map (offset plus positive scale), the normalized log intervals, recurrence graph, sorted Laplacian eigenvalues and eigenspace signal energies are unchanged to numerical precision. Under the tested nonlinear clock deformation, the eigenvalue relative difference is `0.180` and the eigenspace signature distance is `0.224` at motif tolerance `0.60`.

Node relabeling yields eigenvalue maximum error `8.17e-17` and eigenspace-energy maximum error `5.55e-17`.

#### Motif-threshold sensitivity

| Motif tolerance | Base recurrence edges | Nonlinear recurrence edges | Laplacian spectrum difference |
|---:|---:|---:|---:|
| 0.30 | 0 | 0 | 0.000 |
| 0.45 | 0 | 0 | 0.000 |
| 0.60 | 3 | 0 | 0.180 |
| 0.80 | 9 | 1 | 0.351 |
| 1.00 | 12 | 7 | 0.233 |

This sensitivity is important. With no recurrence edges, the graph is simply a path, so its Laplacian eigenvalues cannot express changes in interval motifs; the node signal's spectral energy can still change. Adding recurrence edges makes the graph spectrum sensitive to the motif threshold and to nonlinear drift. The threshold must therefore be calibrated or treated as a model parameter, never presented as a natural constant.

Graph Laplacian spectra are invariant under node relabeling, but are not complete graph identifiers. Non-isomorphic cospectral graphs exist. Individual eigenvectors are not canonical inside repeated eigenspaces; compare eigenvalue multiplicities and eigenspace projectors/energies rather than raw eigenvector columns.

## 4. Representation-selection matrix

| Representation | Natural action | Tested behavior | Main use | Main limitation |
|---|---|---|---|---|
| Fourier magnitude | Circular translation | Invariant | Global periodic content | Loses phase; fixed-bin dilation mismatch |
| STFT | Time translation | Covariant by frame permutation | Local time-frequency structure | Boundary/window/hop dependence |
| Undecimated Haar-like energies | Circular translation | Pooled energy invariant | Multiscale transients | Redundant, lossy descriptor; not an orthogonal DWT |
| Mellin magnitude | Positive multiplicative scale | Invariant on the periodic log grid | Scale relationships | Measure and boundary conditions matter |
| Event graph Laplacian | Node relabeling; affine clock through normalized gaps | Invariant under tested affine map | Irregular event topology and recurrence | Graph construction and motif threshold matter |
| Normalized log intervals | Positive affine clock maps | Invariant | Local rhythm shape | Not invariant to nonlinear clock drift |

## 5. What this says about harmonic representations

“Harmonic” should be read as **symmetry-adapted decomposition**, not necessarily sinusoidal oscillation in ordinary time.

- Translation symmetry suggests Fourier characters.
- Positive-scale symmetry suggests Mellin characters in log coordinates.
- Localized transients and changing scale suggest wavelet or affine-group representations.
- Irregular event relationships suggest graph-Laplacian modes.
- Compact non-abelian symmetry, particularly SU(2) for the unit-quaternion/S³ branch, suggests matrix-valued irreducible representations and Wigner-D / hyperspherical harmonics.
- General nonlinear dynamics suggest Koopman operators on observables. Their spectral structure depends on the dynamics and need not be a finite orthogonal Fourier basis.

No single one of these is the universal invariant space. The operator action should be specified before choosing the representation.

## 6. Important next concepts

A monotone nonlinear time warp changes normalized interval patterns. If the intended equivalence is “same path, different speed,” then interval-ratio invariants are not enough. Two promising routes are:

1. **Path signatures / iterated integrals:** designed to summarize ordered multichannel paths in a way that is invariant under suitable increasing reparameterizations, subject to the usual tree-like equivalence and truncation loss.
2. **Diffeomorphic registration / dynamic time warping:** estimate a time correspondence, then compare residual structure. This is a fitted correspondence, not an intrinsic invariant; its regularization and cost are part of the model.

Build 18 should take the SU(2)/S³ route as the next planned harmonic branch. A later temporal build should compare path-signature invariants to fitted time-warp registration.

## 7. Limitations

1. Everything in Build 17 is synthetic and deterministic. No throat vibration, acoustic, room response or mechanical dataset was processed.
2. The event centers are known fixture inputs. There is no noisy physical event detector in this build.
3. DFT and STFT use finite circular boundary conditions.
4. The Mellin experiment is a periodic finite log-grid construction.
5. The Haar-like multiscale descriptor is not a standard orthonormal wavelet basis.
6. Graph Fourier properties depend on the chosen graph-construction rule and recurrence threshold.
7. Spectral invariants can be incomplete; distinct objects can share the same summary.

## 8. Reproduction

```bash
python -m unittest discover -s tests -v
python build_17.py --output reports
```

Only the Python standard library is required.
