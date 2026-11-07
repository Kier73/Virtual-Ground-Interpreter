# Build 07 — Cross-observer invariant discovery

**Virtual Layer research series · Build 07**  
**Status:** prototype complete; 22/22 tests pass  
**Runtime:** Python 3.10+; standard library only  
**Scope:** finite synthetic S² paths with horizontal Hopf lifts to S³. This is not the full Virtual Layer address space.

## 1. Question

Do distinct observers, using different measurements of the same codonic path library, preserve any common relational structure?

The experiment compares observer-specific representational dissimilarity matrices (RDMs), rather than forcing raw measurement coordinates into a common vector space.

## 2. Candidate library

Eight geometric families are generated:

- Three spherical caps.
- Two second-harmonic wavy boundaries with different phase offsets.
- Two third-harmonic wavy boundaries with different phase offsets.
- One fourth-harmonic wavy boundary.

Each family has four candidate records:

1. Forward traversal, uniform time parameterization.
2. Forward traversal, warped time parameterization (`gamma=1.7`).
3. Reverse traversal, uniform time parameterization.
4. Reverse traversal, warped time parameterization (`gamma=0.62`).

Total: 8 geometric families × 4 records = **32 candidates**.

A critical implementation separation was made: each candidate stores one canonical geometric polyline and a separate time-sampled trajectory. Time warping changes only the temporal sampling. It does not modify the geometric polyline used for path geometry or horizontal lifting.

## 3. Codonic and quaternion layer

Hamilton quaternion multiplication is compiled into scalar codonic instructions using the registry's addition, subtraction and multiplication operations. An alias-renamed registry (`plus`, `minus`, `times`, etc.) produces bit-for-bit identical floating-point results for the tested operations.

Each closed path on S² is horizontally lifted to S³ by composing successive minimal rotors. The final lift is checked to lie on the same Hopf fibre as the initial lift.

For the north-pole gauge used in the implementation:

\[
\pi(q)=qkq^{-1},\qquad q\in S^3
\]

The lift phase is compared with half the signed solid angle of the projected loop. This is specific to the chosen Hopf connection and gauge convention.

## 4. Observer models

Four observers are implemented. Each returns a measurement signature; its RDM is constructed independently.

| Observer | Signature | Deliberately retained / discarded |
|---|---|---|
| `base_shape` | Arc-length path length, colatitude distribution moments and quantiles | Ignores traversal direction and timing; excludes signed area |
| `holonomy` | Circular distance between final fibre phases | Retains signed accumulated phase; discards most local path detail |
| `temporal` | Low-frequency complex DFT coefficients of time-sampled x/y/z signals, step statistics and direction | Sensitive to time parameterization and traversal direction |
| `local_transition` | Distribution of geodesic turning magnitudes on the arc-length-resampled path | Retains local shape/turning structure; ignores traversal orientation |

For vector signatures, features are standardized across the candidate set before Euclidean distance is computed. Holonomy uses circular distance on the phase variable.

The RDMs are not claimed to be universal metrics. They are explicit operational definitions of four observer capabilities.

## 5. Cross-observer comparisons

### 5.1 RDM rank correlations

Spearman correlations are calculated over the upper triangle of each pair of RDMs.

| Observer pair | Spearman ρ |
|---|---:|
| base shape ↔ holonomy | 0.147 |
| base shape ↔ temporal | -0.005 |
| base shape ↔ local transition | **0.693** |
| holonomy ↔ temporal | **0.382** |
| holonomy ↔ local transition | 0.103 |
| temporal ↔ local transition | -0.032 |

The strongest relation is between global base-shape measurements and local-transition measurements. Holonomy and temporal response show a moderate relationship. Other pairs have little rank alignment in this library.

### 5.2 Nearest-neighbour overlap

Mean Jaccard overlap of the 3-nearest-neighbour sets:

| Observer pair | Mean 3-NN Jaccard |
|---|---:|
| base shape ↔ holonomy | 0.200 |
| base shape ↔ temporal | 0.000 |
| base shape ↔ local transition | **1.000** |
| holonomy ↔ temporal | 0.188 |
| holonomy ↔ local transition | 0.200 |
| temporal ↔ local transition | 0.000 |

In this designed library, the base-shape and local-transition observers identify exactly the same 3-neighbour sets. That is stronger than their rank correlation alone, but it remains a result for these chosen path families and feature definitions.

### 5.3 Block-aware permutation controls

A block-aware null shuffles entire geometric-family blocks while preserving the four within-family roles (forward/uniform, forward/warped, reverse/uniform, reverse/warped). This avoids breaking the repeated-measure structure of the candidate library.

999 permutations were performed for each of three selected observer comparisons.

| Pair | Observed ρ | Null mean | Null 95th percentile | Empirical p | Holm-adjusted p |
|---|---:|---:|---:|---:|---:|
| base shape ↔ holonomy | 0.147 | -0.004 | 0.126 | 0.027 | 0.027 |
| base shape ↔ local transition | 0.693 | 0.261 | 0.587 | 0.011 | 0.022 |
| holonomy ↔ temporal | 0.382 | 0.272 | 0.339 | 0.001 | 0.003 |

These are exploratory permutation results, not confirmatory population-level statistical claims. The three comparisons were selected during model development, the library is synthetic, and only eight independent geometric families are represented. Permutation p-values do not remove those design limitations.

Unrestricted candidate-label permutation controls are also included in the machine-readable report for comparison.

## 6. Observer-specific equivalence classes

Approximate equivalence is evaluated using observer-specific thresholds, documented in the JSON report. These are connected components of a thresholded distance graph (single-linkage closure), not a claim that every pair within each component is below the threshold.

| Observer | Threshold | Resulting partition |
|---|---:|---|
| base shape | 0.02 standardized distance | 8 classes of 4 records |
| holonomy | 5e-5 rad | 12 classes; phase-degenerate shapes can merge |
| temporal | 0.1 standardized distance | 32 singleton classes |
| local transition | 0.05 standardized distance | 8 classes of 4 records |

Interpretation:

- Base-shape and local-transition observers treat reverse and time-warped records of the same geometric family as equivalent.
- Holonomy preserves orientation but cannot distinguish every shape whose enclosed solid angle is equal or nearly equal.
- The temporal observer distinguishes every record under its deliberately time-sensitive signature.

Thresholds are operational tolerances for this synthetic data set, not universal perceptual thresholds.

## 7. Reparameterization control

For each geometric family and direction, uniform and warped time samplings were compared.

Observed results:

- Maximum base-shape signature difference: **0** (same stored geometry path).
- Maximum holonomy phase difference: **0** (same lifted geometric path).
- Maximum S³ endpoint difference: **0**.
- Minimum temporal signature L2 change: **0.3598**.

This is the intended structural/dynamic separation: geometry and holonomy remain fixed while the time-sampled signal changes.

## 8. Resolution convergence

A wavy path was reconstructed at increasing boundary sampling resolutions. The difference between measured lift phase and half the signed solid angle decreased:

| Boundary samples | Absolute phase/half-area error |
|---:|---:|
| 180 | 1.1306e-4 rad |
| 360 | 2.8265e-5 rad |
| 720 | 7.0663e-6 rad |

The error decreases by approximately a factor of four when the resolution doubles, consistent with second-order convergence for this discretization regime.

## 9. Graph and topology diagnostics

The build includes:

- 3-nearest-neighbour graph overlap.
- Betti-0 component counts across distance thresholds.
- A normalized weighted graph-Laplacian spectrum.
- Zero-dimensional persistence death times, represented by minimum-spanning-tree edge weights.

**Important limitation:** the reported high correlations between sorted H0 death-time lists compare only distributions of MST merge scales. Sorting discards the identity of the merged candidate clusters. Those correlations are not sufficient evidence that the observers recover the same topology. No H1 or higher-dimensional persistent homology is computed in this build.

The first nonzero normalized graph-Laplacian eigenvalue (spectral gap) is:

| Observer | First nonzero eigenvalue |
|---|---:|
| base shape | 0.4923 |
| holonomy | 0.5302 |
| temporal | 0.8304 |
| local transition | 0.7552 |

These spectra provide global summaries; their interpretation depends on the selected distance and kernel construction.

## 10. Main conclusion

Build 07 identifies a limited but measurable shared relational pattern:

1. Base-shape and local-transition observers preserve strongly aligned neighborhoods in this path library.
2. Holonomy and temporal observers preserve a weaker shared ordering.
3. Time parameterization is ignored by the geometric and holonomy observers but detected by the temporal observer.
4. Observer equivalence classes differ substantially; no single observer's geometry subsumes all others.

This supports a narrow proposition: different measurement systems can recover some common relational structure while retaining distinct observer-specific distinctions.

It does **not** establish a universal invariant space, a universal definition of tone, or an emotional interpretation of the measured signatures.

## 11. Limitations and next tests

- Only eight geometric families are included; the 32 records are repeated variants, not 32 independent path families.
- Observer feature functions are hand-designed.
- The Hopf holonomy is mathematically coupled to the base path's oriented area; the two are not independent physical measurements.
- The temporal DFT signature is a synthetic trajectory signal, not a measured voice, material or biological response.
- The codonic interpreter covers the scalar algebra needed for quaternion multiplication, not the complete Virtual Layer registry or execution runtime.
- The S²/S³ geometry is a controlled test bed, not proof that the full Virtual Layer address substrate is intrinsically S³.
- H0 summaries require richer matched-cluster or diagram comparisons; higher-dimensional topology remains open.

Next: expand path families, vary the observer definitions without tuning to the result, add controlled noise, use independent random geometric families, and test H1 persistence with a stable implementation. Only then should a stronger invariant-discovery claim be considered.
