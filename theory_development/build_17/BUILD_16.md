# Build 16 — Falsifying Event Correspondence and Introducing Harmonic Representations

## Status

- Build 15's independent-local-clock event matcher retained.
- Added mark-only, interval-only, equal-weight and prior combined-feature ablations.
- Added independent B-mark shuffle and B event-order shuffle negative controls.
- Added nonlinear quadratic clock-drift sweep.
- Added unitary finite DFT / inverse / inner-product / Parseval / fourth-power diagnostics.
- Added graph Laplacian eigensystem and graph Fourier transform for event subgraphs.
- Added node-relabeling spectrum-invariance check.
- Tests: 68 passing (Build 16 tests plus inherited Build 14 / Build 15 regression coverage).
- Benchmark: 40 deterministic synthetic trials per condition.
- No empirical sensor audio or participant data processed.

## 1. Why this build

Build 15 showed that an event graph could recover synthetic correspondence without comparing absolute timestamps. Build 16 asks a stricter question: which features actually carry the correspondence, and do they add information beyond each other?

The answer matters. A strong aggregate F1 can conceal reliance on one synthetic feature that real observers do not share. We therefore compare ablations and negative controls before adding richer representations.

## 2. Falsification design

Each trial contains 50 latent events, with observer B experiencing 10% dropout and five inserted false events. Clocks have independent offsets and rates. True event marks undergo a monotone affine transform and small independent noise. A quadratic term adds non-affine clock drift. The test harness retains latent event IDs only to score matches; the matcher does not receive those IDs.

Ablations:

| Matcher | Mark weight | Interval-shape weight |
|---|---:|---:|
| Mark-only | 1.00 | 0.00 |
| Interval-only | 0.00 | 1.00 |
| Existing combined | 0.78 | 0.22 |
| Equal-weight | 0.50 | 0.50 |

Negative controls independently shuffle B marks or randomize the latent event identities assigned to B's chronological event slots. The latter destroys monotone event correspondence while retaining an ordered local time sequence.

## 3. Results

<badge color="success">40 trials per condition</badge>

| Condition | Precision | Recall | F1 |
|---|---:|---:|---:|
| Mark-only | 0.915 | 0.950 | 0.932 |
| Interval-only | 0.788 | 0.815 | 0.801 |
| Combined 0.78 / 0.22 | 0.908 | 0.945 | 0.926 |
| Equal weights | 0.880 | 0.919 | 0.899 |
| B marks independently shuffled | 0.303 | 0.304 | 0.303 |
| B event order shuffled | 0.043 | 0.043 | 0.043 |

### Interpretation

The existing combined matcher does **not** improve on mark-only matching in this synthetic setup. Mark-only has F1 0.932 versus 0.926 for the combined method. Interval-only still carries useful information (F1 0.801), and the shuffled-mark control falls to 0.303, indicating the temporal interval cue can help when the mark cue is disrupted. Shuffling the event order drops F1 to 0.043, confirming that monotone order is a strong assumption of the dynamic-programming aligner.

The result is a correction to Build 15's interpretation: the benchmark is not evidence that multiple independent relational cues jointly recover identity. The mark ranks are highly informative because both synthetic observers carry monotone transforms of a shared latent event mark. Real acoustic / throat-vibration marks may not have this property.

## 4. Nonlinear clock-drift sweep

Quadratic drift severity is increased while preserving monotonicity of the local clock map. Mark-only F1 remains 0.932 by construction because it does not use event times. Interval-only moves from 0.801 at zero drift to 0.776 at the highest tested drift 0.60. The combined matcher moves from 0.926 to 0.932. This limited sweep does not establish general nonlinear-drift invariance; it shows that the mark cue dominates this benchmark and masks moderate interval degradation.

All trial-level values and scenario parameters are in `reports/falsification_controls.json`.

## 5. Harmonic representation prototypes

### 5.1 Finite DFT

The implementation uses the unitary finite transform

\[
X_k=\frac{1}{\sqrt N}\sum_{n=0}^{N-1}x_n e^{-2\pi i kn/N},
\qquad
x_n=\frac{1}{\sqrt N}\sum_{k=0}^{N-1}X_k e^{+2\pi i kn/N}.
\]

A 32-sample deterministic complex fixture gives:

- Parseval energy error: approximately \(1.1\times10^{-14}\).
- Maximum inverse reconstruction error: approximately \(1.1\times10^{-14}\).
- Maximum \(F^4=I\) error: approximately \(2.5\times10^{-14}\).
- Circular-shift Fourier-magnitude difference: numerical roundoff only.

The finite DFT is a cyclic-group transform. Applying it to a nonperiodic event trace implicitly uses a periodic boundary convention. For an open event chain, a path-graph Laplacian, DCT-like boundary model or wavelet representation may be more suitable.

### 5.2 Graph Fourier

For the observer-local event graph, the implementation forms a weighted undirected adjacency matrix from successor and recurrence edges, then

\[
L=D-A=U\Lambda U^T,\qquad \widehat x_G=U^Tx.
\]

The 14-node demo preserves signal energy to approximately \(3.6\times10^{-15}\) and reconstructs to numerical precision. Reversing node labels changes the Laplacian by permutation similarity; the sorted eigenvalue spectrum differs by approximately \(8.9\times10^{-16}\).

This is an exact check of the implementation's linear-algebraic properties, not a finding about real sensor data. The spectrum is invariant to node relabeling but not a complete graph identifier: non-isomorphic cospectral graphs exist. Individual eigenvectors are also not canonical within repeated eigenspaces; compare eigenspace projectors / multiplicities rather than raw basis columns.

## 6. Why the harmonic map is broader than Fourier

The attached `REPRESENTATION_MAP.md` connects each major project perspective to its natural action and representation. The main routes are:

- translation -> Fourier characters;
- positive scale -> Mellin characters;
- translation + dilation -> wavelet / affine-group representation;
- graph topology -> graph-Laplacian modes;
- compact non-abelian symmetry -> matrix-valued irreducible representations;
- quaternion / S³ geometry -> SU(2) Peter–Weyl / Wigner-D harmonics;
- nonlinear dynamics -> Koopman action on observables;
- codonic execution -> group representations only on invertible symmetry actions, otherwise semigroup / operator methods;
- weight space -> quotient parameter geometry under architecture-specific symmetries.

The transform must match the symmetry. A harmonic decomposition is not automatically meaningful just because a basis has oscillatory modes.

## 7. Limitations

1. Synthetic marks are shared latent-event descriptors. A real observer may not provide cross-modal marks with stable ranks.
2. The dynamic-programming aligner only supports monotone correspondences. It cannot solve arbitrary reordering.
3. The nonlinear drift family tested here is quadratic with positive derivative; arbitrary local clock wander is not covered.
4. Finite DFT is a transparent O(N²) prototype, not an FFT implementation.
5. Graph Fourier uses a small dense Jacobi eigensolver and a chosen event-graph weighting rule; it is not an optimized sparse graph pipeline.
6. No empirical TAPS audio was processed in this build.

## 8. Reproduction

```bash
python -m unittest discover -s tests -v
python build_16.py --output reports
```

Only the Python standard library is required.

## 9. Next action

Build 17 should compare Fourier, wavelet, Mellin and graph representations on the same temporal signal under controlled translation, dilation and nonlinear clock drift. The first priority is to remove dependence on globally ranked marks and test whether local / multiscale relationships provide robust correspondence by themselves.
