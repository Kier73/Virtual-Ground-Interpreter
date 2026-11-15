# GEOMETRY-FIRST-001 — discover, bind, navigate, measure

This is an executable, finite experiment connecting the early codonic geometry proposal with the active VGI certified modular-affine navigation mechanism. It does **not** claim that arbitrary computations can be solved by geometric lookup or SHA-256 decoding.

## Question

Can a geometry reveal algebraic operations before the codonic registry tells it what those operations mean, and can the verified laws navigate context-dependent results at distant logical times without materializing intervening states?

## Method and evidence contract

- **Independent substrate:** a 100 × 100 torus, 10,000 positions, with opaque transition channels `alpha`, `beta`, `gamma`, `delta`, and `epsilon`. Coordinates and intrinsic edges are fixed; no codon or SHA label determines them.
- **Opaque naming:** three SHA-256 seed assignments produce three different labels per point. All 10,000 positions retain their same intrinsic neighbors and geometry fingerprint. Hash-space distances are deliberately not used as geometry distances. Hash addresses require the point-to-identity correspondence to be retained.
- **Black-box law inference in a declared chart:** enumerate all 10,000 source/target pairs per action. Check injectivity, idempotence, and whether displacements are uniform. Fit a 2D affine model from only the origin and two basis probes; accept it only after exact verification on *all* 10,000 points. This uses the **declared coordinate chart**; it does not discover that chart or a universal manifold from arbitrary observations.
- **Registry replacement:** two codon sets, with distinct symbolic names, independently bind typed algebraic requirements to previously observed action profiles. An ambiguous binding is rejected rather than guessed. Registry removal/replacement does not alter the geometry.
- **Structural placement:** 48 codons with 58 declared dependencies are placed with a random seed either uniformly at random or greedily near their dependencies. Measure sum of toroidal parent-edge distances, placement time, and uniqueness. The torus is homogeneous: it offers no intrinsic preferred *absolute* origin; only relative dependencies make placement informative. Locality gain is not an execution speedup.
- **Logical time:** `CertifiedGeometryNavigator` audits the finite geometry once. Its `state_at` uses direct translation, one idempotent step, or the existing VGI `ModularAffineMap.power` method, not `tick` repeated transitions. Requested ticks do not correspond to wall-clock elapsed time, external execution, or an automatic authorization to publish effects.
- **Dynamic matrix context:** `DeferredMatrixProduct` records immutable runtime-supplied operands with a SHA-256 fingerprint, and represents `AB` without materializing the product. Query one entry, apply to one vector as `A(Bv)`, or explicitly materialize the full matrix. Validate results against a separately written dense reference over modular rings. The fingerprint authenticates only the in-process content identity, not a trusted external observation or a cryptographic attestation.

The geometric actions were chosen to expose important controls:

| Action | Rule in coordinates `(x,y)` modulo `n` | Detected property | Distant-time support |
|---|---|---|---|
| alpha | `(x+1,y)` | uniform bijective translation | direct modular displacement |
| beta | `(x,y+1)` | uniform bijective translation | direct modular displacement |
| gamma | `(0,y)` | non-injective, idempotent, affine | one application |
| delta | `(x+y,y+1)` | bijective affine shear, non-uniform displacement | existing VGI affine powering |
| epsilon | `(x+y²,y+1)` | non-affine nonlinear control | **refused**, not guessed |

For `delta`, the independently checkable closed form is

\[
y_t=y_0+t\pmod n, \quad x_t=x_0+t y_0 + \tbinom{t}{2}\pmod n.
\]

This is a particularly useful observation: an algorithm that does not have a constant displacement can still have a verified algebraic law. A 2D homogeneous affine representation over the modular ring is sufficient even when the modulus is composite. A change of coordinate chart may change which laws are easy to discover; the current certificate binds to the given chart and finite transition table.

## Reproduce

From `virtual_ground_interpreter/`:

```bash
python -m unittest discover -s tests -p 'test_geometry_first.py' -v
python -m examples.run_geometry_first
```

No extra dependencies. The benchmark emits JSON and records the geometry/certificate and dynamic-operand fingerprints, sample data, graph distance, time query, correctness assertions, and median runtime. The tests independently repeat short trajectories, check a very distant `10^30`-scale logical coordinate, compare random modular matrices against a dense reference, require SHA relabeling invariance, and require refusal when the algebraic shortcut is not established.

## Findings from one local reference run (2026-11-14)

**The complete local six-test focused suite passed.** The local harness used a small API-compatible substitute for VGI's `ModularAffineMap` while coding offline; repository CI must still validate against the *actual* VGI implementation. These figures are exploratory Python wall-clock measurements, not hardware-neutral performance or speedups against optimized BLAS.

| Measurement | Observation |
|---|---:|
| Substrate points | 10,000 |
| Intrinsic action edges checked | 50,000 |
| Seed relabelings | 3 distinct 10,000-address sets |
| Complete certificate preprocessing | ~560 ms |
| Codons / dependency edges | 48 / 58 |
| Random placement total edge distance | 2,860 |
| Guided placement total edge distance | 76 |
| Random placement time | ~12.7 ms |
| Guided placement time | ~2.2 ms |
| Large-time coordinate | `10^30+11` |
| Affine shear query after certification | ~0.49 ms |
| Nonlinear control | refused |
| Dynamic matrix size and ring | 48 × 48 modulo 97 |
| Context-bound deferred matrix admission | ~1.06 ms |
| One matrix entry query | ~0.0033 ms |
| One matrix-vector query | ~0.20 ms |
| Dense full-product reference | ~5.80 ms |
| Deferred full-product materialization | ~7.46 ms |

The placement ratio is `2860/76 ≈ 37.6` in the *chosen locality cost*, not a speed ratio. Guided placement requires looking at neighbor candidates but avoids an expensive scan of all free positions at each step. This comparison does not isolate the effects of candidate-search strategy from the placement objective. In a homogeneous torus, there is no meaningful absolute position preference.

The matrix result is a demand-driven computation: computing one entry is `O(n)` arithmetic, applying a product to one vector is `O(n²)`, and explicitly computing every entry uses `O(n³)` under the naive dense reference. Operand admission already costs `O(n²)` to preserve immutable, fingerprinted inputs. The timings do not imply a universal matrix-multiplication breakthrough: optimized BLAS, reuse across vectors, and full-product requests can reverse the preferred execution method.

## Distinctions preserved

1. Geometry and symbolic identities are separate. SHA avalanche does not predict geometric proximity.
2. Geometry law identification is empirical/exhaustive over this finite Ground; it is not a proof about an unrelated external process.
3. Logical-time navigation becomes practical when an algebraic representation has been **observed and verified**. It does not create an answer to an arbitrary unstructured function.
4. An unknown runtime matrix product can be kept as a compositional result. A query for individual entries still performs arithmetic; it is not a static answer lookup.
5. `epsilon` is intentionally unresolved although a more expressive polynomial-in-time representation may exist. This makes it a next problem, not an incorrect inference.
6. Structural proximity for dependency placement does not itself establish causal correctness, latency improvement, or an optimal host assignment.

## Next research target

**GEOMETRY-FIRST-002:** discover higher-degree polynomial or lifted-state operators from observations and certify them independently of the chosen coordinate chart. Begin with `epsilon`, attempt to find a finite-dimensional lift in which the nonlinear transition becomes affine, then compare certification cost, algebraic jump cost, required state size, and refusal behavior on genuinely non-closed or ambiguous Grounds. Connect discovered laws to the existing VGI observer-relative atlas and evidence admission instead of treating the synthetic ground as externally grounded.

Related existing VGI foundations: `docs/AFFINE_FAST_FORWARD.md`, `docs/ORBIT_NAVIGATION.md`, `docs/RELATIONAL_ATLAS.md`, and `Theory Docs/VirtualLayer_early_codonic_reference.md` at the repository root.