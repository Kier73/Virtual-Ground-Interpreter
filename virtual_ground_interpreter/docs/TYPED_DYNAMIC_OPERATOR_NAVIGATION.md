# GEOMETRY-FIRST-005 — Typed dynamic operator composition and demand navigation

## Question

Can VGI preserve a dynamically supplied matrix operation as a *composable, addressable computational object* and navigate to a selected result without first materializing all intermediate matrix values? Can this representation also express the affine laws discovered from bounded executable programs, while preserving mathematical truth and E-CPU's existing admission responsibility?

## Relationship to previous experiments

- GEOMETRY-FIRST-001 separates opaque/hash names, intrinsic geometry, algebraic laws, and codonic placement. Its `DeferredMatrixProduct` represents one square product `AB` with fixed operands and provides single-entry, vector, and complete-product demands.
- GEOMETRY-FIRST-002 discovers closed affine lifts for nonlinear finite-field transformations; GEOMETRY-FIRST-003 distinguishes sparse hypotheses from verified symbolic laws.
- GEOMETRY-FIRST-004 derives a formally valid polynomial law from an accepted bounded program's AST, before lifting the law algebraically.
- **This build generalizes deferred binary `AB` to an arbitrary typed compositional chain**, permits rectangular maps and sparse diagonal operators, binds dynamic operand snapshots, emits independently replayable mathematical demand receipts, and connects VGI's existing `ModularAffineMap` to a typed homogeneous representation. It does **not** create a second execution authority or treat a mathematical digest as an external attestation.

## Mathematical contract

Let `Space(frame,d,m)` denote an explicitly identified coordinate frame of dimension `d` over the ring `Z/mZ`, where `m >= 2`. Two frames are not interchangeable merely because they share a dimension and modulus.

Each immutable leaf is a linear map `A: Space(in, n, m) → Space(out, p, m)`; it is a dense `p×n` matrix or a diagonal map whose domain/codomain dimensions match. A graph stores a sequence `A_0, A_1, ..., A_{k-1}` with the composition contract:

```
A_i.domain == A_(i+1).codomain
T = A_0 ◦ A_1 ◦ ... ◦ A_(k-1)
```

The rightmost factor acts first. The graph's SHA-256 identity binds the canonical type declarations and every immutable leaf's coefficients and identity. It is an **identity fingerprint**, not an authorization signature.

### Demand-driven semantics

A graph is already an addressable result. Its downstream consumers can request:

1. **One matrix entry** `T[i,j]`, computed by sending the `j`th basis vector through the factor chain and observing output `i`.
2. **One action on a vector** `T·v`, computed by successively applying the original leaves right-to-left; no intermediate `A_i A_j` product is formed.
3. **The entire dense matrix** `T`, which is necessarily fully materialized in this implementation (by applying the chain to the complete input basis).

For a chain of `k` square dense `n×n` matrices, an entry or vector demand takes `O(k n²)` ring operations, while generating the whole dense matrix via basis probes takes `O(k n³)`. All leaves still have their original storage costs; avoiding a *new* dense product is not equivalent to eliminating arithmetic, storage, or verification work. A dense triple-loop reference independently checks the results, including rectangular compositions over both prime and composite moduli.

The demand receipt records the graph, exact request, output fingerprint, result, number of leaf applications, estimated scalar products, and whether a dense composite was formed. A verifier recomputes the requested result from the current immutable chain. If one dynamic operand is re-bound, the graph fingerprint changes and the old receipt no longer verifies. This remains a **declared-model replay check**, not a signed external receipt.

### Distant logical time is a different demand

A logical-time query `T^t·v` is supported only for a closed endomorphism, where `T.domain == T.codomain`. A prepared temporal object explicitly **builds the full composite matrix first** using finite-ring matrix composition. It then independently verifies the prepared matrix against each typed basis-vector traversal of the original graph, and uses VGI's existing `ModularAffineMap.power` (zero offset) for binary powering.

Preparing the dense operator is a real cost: `O(k n³)` in the general square dense case. The subsequent query uses `O(n³ log t)` ring operations, and no intermediate **logical states** are materialized. This is meaningful for repeated queries at distant logical times against an unchanged graph, *not* a claim of constant-time calculation or acceleration of arbitrary unknown models. A new dynamic operand invalidates the prepared temporal identity and requires preparation against the new graph.

### Structure-selected logical time without dense preparation

For a closed chain whose admitted leaves are *all explicitly typed diagonal maps*, the system can discover a stronger coordinatewise law:

```
T = Diag(d1) ◦ Diag(d2) ◦ ... ◦ Diag(dk)
T^t · v = ((d1_i*d2_i*...*dk_i)^t * v_i mod m)_i
```

`PreparedDiagonalTemporalOperator` derives and binds the per-coordinate product from the immutable dynamic operands. Its proof checks **every input basis action** against the original typed graph before permitting distant-time requests. No dense composite is formed, including during certificate preparation; the proof cost is `O(k n²)` reference ring operations for basis checks, and time navigation uses `n` scalar modular exponentiations, `O(n log t)` ring multiplications. It works on composite moduli and singular maps because no inverse is required. Rebinding any operand requires a new certificate. Non-diagonal dense operands are **refused** by this route, even when they might happen to be numerically diagonal; recognizing equivalent structure in opaque representations remains research.

The benchmark additionally compares 48-coordinate, three-diagonal-factor structured preparation and a conventional dense preparation of the *same* graph. Median local measurements were **1.20 ms** for structure-aware certification, **0.14 ms** for the `10^30+11` query, and **13.13 ms** for dense preparation. These are reference Python measurements for this deliberately structured case, not hardware or arbitrary-matrix speedup claims.

### Program-derived affine adapter

A verified `ModularAffineMap` of dimension `d` and offset `b` can be embedded as the homogeneous `(d+1)×(d+1)` linear map:

```
H = [ M  b ]
    [ 0  1 ]
```

`homogeneous_affine_map` builds this as a typed dense leaf. A regression fixture invokes GEOMETRY-FIRST-004's `certify_program` on source that computes `x' = x + y², y' = y + 1 (mod 101)`, receives the discovered 3-coordinate law, embeds it in 4 dimensions, composes two copies, and compares finite and `10^30+11` logical-time results with the independently certified original program transition. A decoder refuses a vector whose final homogeneous coordinate differs from `1`.

**Important:** preservation of the homogeneous constant alone is **not** sufficient to prove every nonlinear feature invariant (for example `z=y²`). Any arbitrary typed map may act on the lifted vector algebraically but must not be interpreted as a valid base program state unless the feature-closure relation is separately justified and checked. The test checks both invariants for the chosen composition.

## Verification and negative controls

From the repository's `virtual_ground_interpreter/` directory:

```sh
python -m unittest discover -s tests -p 'test_typed_operator_navigation.py' -v
python examples/run_typed_operator_navigation.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

The new regression tests cover:

- Dynamic rectangular products with an independent triple-loop dense reference, over both `Z/8Z` and `Z/97Z`.
- Typed diagonal+dense composition, one entry, one vector, and explicitly requested full materialization.
- Distinct observer/coordinate frames, Boolean/nonintegral coefficients, mismatched shapes/rings and invalid demands.
- Immutable dynamic operand versions, stale receipt refusal, and tampered result/cost refusal.
- Randomly generated closed dense operator chains compared with repeated reference execution for many small logical times, including noninvertible maps.
- A `10^30+11`-scale temporal query checked against an independent shear formula.
- A structurally selected 48-coordinate diagonal temporal route, over prime and composite rings, which does **not** prepare a dense map; refuses non-diagonal factors and tampered coefficients.
- A program-derived polynomial lift bridged to the homogeneous typed operator graph, with negative homogeneous-chart invariant control.

The local reference suite currently ran **43/43** tests across GEOMETRY-FIRST-001 through 005 in a minimal API-compatible Python harness, including **10/10** newly added tests. The real repository uses its own existing `vgi.affine` implementation and existing tests; GitHub CI (currently queued) is required before reporting full-repository verification. The benchmark report records exact machine-dependent local timings separately from operation-count proxies.

## Connection to E-CPU (proposed; not implemented)

Existing E-CPU interfaces establish the relevant responsibilities:

- `mailcpu/virtual_layer.py`: workloads carry *intent and coordinates*, not executable Python or authority. OperatorSpec and runtime must define a typed effect and eligible substrate.
- `mailcpu/navigation_admission.py`: the hypervisor independently admits/rejects navigation operations and binds authorization to process/context/resource identity.
- `mailcpu/vgi_host.py`, `mailcpu/transit_vgi.py`: existing receiver-local VGI hosting provides an approved Transit adapter model.
- Existing E-CPU structural memory and navigable DAG checkpoints can retain admitted graph/leaf fingerprints and evidence, but this experiment has **not** integrated those protocols or proven recovery/physical-host performance.

Proposed pure operator identifier: `vgi.typed-linear.navigate/v1` (design placeholder, **not registered**). Its unprivileged workload would name a previously admitted graph identity, typed input coordinate, requested observable (`entry`, `vector`, `dense`, or prepared `time`), and logical time when applicable. The receiving host would independently resolve/canonicalize operand snapshots, verify graph/type identities and mathematical certificates, then return a result receipt through the existing hypervisor-governed result channel. No arbitrary executable source belongs in the transit workload.

## Research frontier

The next harder question is **representation-driven optimization**. Before materializing a dense matrix for distant time, can the system discover a smaller closed invariant subspace, a block decomposition, a commutative operator algebra, or a rational form from the typed graph and admitted observation evidence? Success would make the *choice of a navigable representation* part of the computation, rather than always using full `n×n` dense powering. Discoverability, certificate cost, and explicit failure examples must be measured; arbitrary matrix inputs cannot have universal shortcuts for free.