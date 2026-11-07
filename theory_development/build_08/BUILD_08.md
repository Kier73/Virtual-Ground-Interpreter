# Build 08 — Generalization and Perturbation Study

**Virtual Layer research series**  
**Scope:** randomized spherical paths · observer-specific RDMs · family bootstrap · measurement degradation · H0/H1 persistence · cryptographic substrate controls · codonic equivalence

## 1. Purpose

Build 07 found apparent shared relational structure in a small, hand-designed path library. Build 08 tests whether those relationships persist when the candidate structures are sampled independently and the observers are perturbed.

The objective is not to prove a universal geometry. It is to determine which observations survive a change in candidate construction, observer sensitivity, and address substrate.

## 2. Experimental design

### 2.1 Randomized path family

The default run creates **40 independent closed spherical path families**. Each path consists of one to three concatenated random spherical petals sharing a root. Each petal contains randomly selected intermediate vertices joined by geodesic arcs. This construction permits irregular contours, self-approaches, and concatenated loops; it does not guarantee that every individual path self-intersects or is non-star-shaped.

The generated paths are closed and unit-normalized. In the default seeded run:

- 11 families contain one petal;
- 19 contain two petals;
- 10 contain three petals;
- path vertex counts range from 29 to 134.

Geometry and time sampling are stored separately. Reparameterizing a path therefore does not alter the polyline used for its geometric measurements or horizontal lift.

### 2.2 Observer signatures

Four distinct observer models are used:

| Observer | Measurement features |
|---|---|
| Shape | Path length, absolute spherical area, geodesic chord-distance distribution, centroid-relative radial distribution |
| Local transition | Geodesic turning-angle distribution and summary statistics |
| Holonomy | Hopf-fibre phase represented as `(cos(phase), sin(phase))` |
| Temporal | Complex DFT components (real and imaginary) across x/y/z and speed statistics for uniform, warped, and reversed schedules |

The observers do not share a common raw coordinate system. Each produces a feature representation, which is converted into a representational dissimilarity matrix (RDM).

### 2.3 Observer perturbations

The experiment includes:

- feature-channel projection / dropout;
- additive Gaussian feature noise in standardized coordinates;
- reduced temporal bandwidth, preserving low-frequency channels across all three axes and all schedule variants;
- local-transition measurement perturbation;
- holonomy measurement noise.

A robustness sweep varies the retained feature fraction across 1.0, 0.75, 0.5, and 0.35, and noise standard deviation across 0, 0.05, 0.10, 0.20, and 0.40 standardized units. Each point is repeated six times with deterministic independent seeds.

This is a feature-space measurement-degradation experiment. It is not a physical microphone, tactile sensor, or human-subject study.

## 3. Statistical comparisons

For each observer pair, the build reports:

- Spearman correlation between upper-triangle RDM entries;
- mean 5-nearest-neighbor Jaccard overlap;
- bootstrap confidence intervals from resampling independent path families (400 replicates);
- node-label permutation comparison (399 permutations).

The five primary cross-observer comparisons are specified before adjustment and use Holm family-wise correction. Pairwise RDM entries are not treated as independent samples; the bootstrap resamples families, not individual pairwise distances.

## 4. Main results

### 4.1 Cross-observer relationships

| Observer pair | Spearman rho | Bootstrap 95% CI | 5-NN Jaccard | Holm-adjusted p |
|---|---:|---:|---:|---:|
| Shape / Local transition | 0.272 | [0.208, 0.464] | 0.143 | 0.0125 |
| Shape / Holonomy | 0.177 | [0.102, 0.398] | 0.148 | 0.0125 |
| Shape / Temporal | 0.095 | [-0.003, 0.308] | 0.088 | 0.2650 |
| Holonomy / Temporal | 0.002 | [-0.017, 0.187] | 0.079 | 0.4150 |
| Local transition / Temporal | **0.464** | [0.304, 0.639] | 0.113 | 0.0125 |

The strongest shared relationship in this randomized library is local-transition / temporal response. Shape / local-transition remains positive but is much weaker than in Build 07. Holonomy / temporal is effectively absent in this run.

**Generalization comparison with Build 07:**

- Build 07 shape / local-transition: approximately 0.693; Build 08: 0.272.
- Build 07 holonomy / temporal: approximately 0.382; Build 08: 0.002.

This weakens the hypothesis that those two Build 07 pairings represent general observer invariants. They may have depended substantially on the original designed path families and feature choices.

The local-transition / temporal relationship is a new candidate worth testing, not yet an invariant claim.

### 4.2 Robustness to measurement degradation

At 50% retained channels, average RDM correlations (over six repeats) at selected noise levels were:

| Observer | Noise 0.0 | Noise 0.1 | Noise 0.4 |
|---|---:|---:|---:|
| Shape | 0.923 | 0.920 | 0.857 |
| Local transition | 0.886 | 0.723 | 0.666 |
| Holonomy | 0.648 | 0.640 | 0.555 |
| Temporal | 0.974 | 0.972 | 0.955 |

These values measure preservation of the observer's own original RDM under the specified feature projection/noise process. They do not measure accuracy against an external ground truth. The different sensitivities indicate that robustness depends on the representation and measurement model.

### 4.3 Cryptographic address-substrate controls

The same quantized path payloads are mapped through SHA-256, BLAKE2b-256, and BLAKE2s-256. Pairwise normalized Hamming distances are compared across address spaces and against geometric observer RDMs.

| Comparison | Spearman rho |
|---|---:|
| SHA-256 / BLAKE2b-256 | -0.021 |
| SHA-256 / BLAKE2s-256 | 0.061 |
| BLAKE2b-256 / BLAKE2s-256 | 0.014 |
| SHA-256 / Shape | -0.074 |
| BLAKE2b-256 / Shape | 0.054 |

The near-zero correlations are consistent with cryptographic digests behaving as substrate-specific address coordinates rather than semantic geometry. This is a control over the generated path payloads; it is not a re-evaluation of the complete current Virtual Layer implementation.

### 4.4 Codonic decomposition controls

The Hamilton quaternion product is evaluated using configurable `ad`, `su`, and `mx` aliases. The tested alternatives include:

- left-associated addition;
- pairwise addition;
- reverse-associated addition;
- complete alias renaming (`ad/su/mx` to `plus/minus/times`);
- left and right multiplication by the quaternion identity.

Maximum absolute differences between equivalent results are approximately `2.78e-17`; identity checks are exact in this run. Raw alias strings hash differently, while a deliberately canonical semantic IR is alias-independent.

This is a narrow algebraic normalization demonstration for Hamilton multiplication. It is not a general algorithm-equivalence solver or a proof that arbitrary codonic programs can be canonicalized.

## 5. Persistent homology

The build computes Vietoris–Rips persistence over **F2 through H1** for six observer RDMs. H0 finite death times are recovered from the minimum spanning tree. For H1, the exact boundary-matrix reduction includes vertices, edges and triangles, with a maximum edge threshold at the 72nd percentile of the observer's pairwise distances.

Positive-persistence H1 intervals in the default run:

| Observer | Positive H1 intervals | Zero-lifetime bars | Censored H1 intervals |
|---|---:|---:|---:|
| Shape | 12 | 510 | 0 |
| Local transition | 4 | 518 | 0 |
| Holonomy | 1 | 521 | 0 |
| Temporal | 9 | 515 | 0 |
| Shape, noisy/dropout | 10 | 512 | 0 |
| Temporal, low-band | 25 | 497 | 0 |

Many edge cycles are filled immediately by triangles at the same filtration value, producing zero-lifetime bars. They are reported separately and are not counted as positive-persistence features. H2 is not computed in this build.

Normalized H1 Betti curves are compared descriptively. Their observer-to-observer correlations are not treated as formal evidence of topology equivalence. For example, shape versus its noisy/dropout observer has a normalized Betti-curve correlation of approximately 0.683, while temporal versus low-band temporal is approximately 0.073. A full persistence-diagram bottleneck-distance analysis and stronger sampling-based stability study remain future work.

Persistent homology is an established way to summarize multiscale connectivity and loops. Stability results bound persistence-diagram changes under controlled perturbations, but this build does not yet calculate bottleneck distances between all observer diagrams.

## 6. Interpretation

The main result is not that all observers converge on one geometry. They do not.

Instead:

1. Some cross-observer relational structure survives randomized path generation, but it is selective and weaker than in Build 07.
2. Temporal representation preserves its own RDM well under the tested channel projection and noise, but this does not make it equivalent to geometric or holonomy observers.
3. Cryptographic address-space distances are empirically uncorrelated with the geometric descriptors in this control, reinforcing the need to keep address identity and response geometry separate.
4. Different observer RDMs yield different H1 persistence summaries. The topology of an observed representation is itself observer-dependent.
5. Codonic algebraic identity can be preserved across nomenclature and some expression-tree changes when a semantic operation definition is held fixed.

The original proposition remains open: meaning may be investigated through relationships preserved under transformations, but these experiments do not establish a universal invariant meaning space.

## 7. Limitations

- All paths and observers are synthetic.
- The random path generator is broad but not a uniform sampler of all possible loops on S2.
- Feature selection encodes modelling choices; different features can change RDM relationships.
- Bootstrap intervals and permutation results apply to this generated family population and observer definitions only.
- The RDM permutation test is a Mantel-style node-label permutation; it does not make pairwise distances independent.
- The persistence computation is exact over F2 through H1 for the finite truncated complexes used here; H2 is omitted.
- Zero-lifetime bars are numerous due to same-filtration edge/triangle events and should not be interpreted as robust loops.
- Cryptographic hash controls do not establish a general theorem about all address substrates.
- The codonic canonicalization example is specific to one operation family.
- No actual voice recordings, material-touch data, emotional ratings, or biological sensor data are included.

## 8. Reproduction

Python 3.10+; standard library only.

```bash
python -m unittest discover -s tests -v
python cross_observer_generalization.py --out .
```

Default deterministic configuration: seed `81008`, 40 path families, 400 family-bootstrap replicates, 399 label permutations, and six robustness repeats per setting.

See `reports/build_08_report.json`, `data/`, `test_run.txt`, and `MANIFEST.sha256` for results and integrity checks.

## 9. Research sources

- Kriegeskorte et al., *Representational Similarity Analysis — Connecting the Branches of Systems Neuroscience*. https://doi.org/10.1093/scan/nsz099
- Diedrichsen et al., *Statistical inference on representational geometries*. https://pmc.ncbi.nlm.nih.gov/articles/PMC10446828/
- Chazal et al., *The Structure and Stability of Persistence Modules*. https://www.stat.cmu.edu/~arinaldo/papers/BandforRips.pdf
- Hensel et al., *A Survey of Topological Machine Learning Methods*. https://pmc.ncbi.nlm.nih.gov/articles/PMC8187791/
- Edelsbrunner & Harer, *Persistent Homology*. https://vis.lbl.gov/PDFs/PH-handbook.pdf
