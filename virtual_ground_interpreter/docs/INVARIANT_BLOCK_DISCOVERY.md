# GEOMETRY-FIRST-006: certified hidden coordinate-block discovery

## Research question

Can a computational observer infer algebraic locality *from the coefficients of dynamically supplied opaque operators*, rather than requiring those operands to arrive with `DiagonalMap` or block annotations? Can the inferred structure enable distant-time navigation without materializing a full composite matrix?

**Result:** yes, for a rigorously bounded class: exact **common coordinate-aligned reducing blocks** of all constituent linear operators over `Z/mZ`. The method does **not** solve generic invariant-subspace discovery under an unknown basis, algebraic simultaneous diagonalization, or arbitrary nonlinear programs. These are further research questions.

## Inputs and semantics

Input is an existing immutable `OperatorChain` from GEOMETRY-FIRST-005. Each leaf is `DenseMap` or `DiagonalMap`, with explicit source/destination `FiniteSpace` and finite-ring modulus. The entire chain must be a typed endomorphism and every intermediate factor must preserve a common coordinate dimension and ring. Coordinate indices are interpreted in the common ordered-index convention across those intermediate typed spaces. This mathematical convention does not assert that external hardware shares a coordinate system.

For each leaf matrix \(A^{(k)}\), construct an *undirected* graph on its coordinate indices: join \(i\) to \(j\) whenever \(i \neq j\) and \(A^{(k)}_{ij}\neq0\pmod m\). Take the union over **all** leaves. Connected components form a partition \(B_1,\ldots,B_r\).

For every factor \(k\), and every \(a\neq b\), the exact coefficient audit implies

\[
A^{(k)}_{B_a,B_b}=0.
\]

Each factor therefore preserves each coordinate span \(\mathrm{span}\{e_i:i\in B_a\}\). Every product of those factors preserves the same partition. This is an exact algebraic argument over `Z/mZ`; it does **not** require eigenvectors, invertibility, a field modulus, random probes, or a sampled prediction. The partition is the finest **common block-diagonal** partition of the input factors in the declared coordinate basis. A strict block structure of the *product alone* can be missed due to cancellation.

## State construction and navigation

The `CertifiedInvariantBlocks.discover(graph)` constructor:

1. Checks the typed endomorphism and common dimension/ring.
2. Inspects all supplied matrix coefficients and canonical modular zeros.
3. Computes the finest connected-coordinate partition and **refuses** if only one component exists (no proper block decomposition).
4. For every block, constructs the exact product of the corresponding *small* factor submatrices, in original right-to-left application order. **No ambient full composite** is constructed.
5. Recomputes and verifies the partition and each local composite at certificate construction time. The result carries a SHA-256 identity bound to the entire operand graph, each discovered block, all local maps, and declared proof scope.

Distant navigation then computes \(G_{B_a}^{\,t}\,x_{B_a}\) separately for every block, using VGI's existing `ModularAffineMap.power` with zero affine offset, and assembles the complete typed result. Navigation cost scales logarithmically with \(t\) for fixed block sizes; it is **not** a constant-time implementation, and the cost of reading, certifying, and multiplying the block operands belongs to preparation.

A `BlockNavigationReceipt` binds the exact admitted graph/certificate, initial value, tick, result, block sizes, and method. `verify_block_receipt` recomputes the claim against the immutable certificate. These are mathematical/integrity checks only, **not digital signatures, hypervisor admission, or trusted external execution attestations**.

## Correctness, failure and adversarial controls

`tests/test_invariant_blocks.py` adds 12 tests for:

- Discovery of three intentionally **interleaved** blocks from ordinary unannotated dense maps.
- Differential checks against direct repeated factor application over composite and prime moduli.
- Extreme tick \(10^{30}+11\), independently compared against `PreparedTemporalOperator`'s full dense-power result on the smaller eight-coordinate control.
- Dense matrices which happen to be diagonal, even when the earlier `PreparedDiagonalTemporalOperator` refuses them because of the declared operand type.
- Mixing dense and explicitly diagonal factors.
- Correctness of products of **noncommuting** factors (the order is retained).
- Exact graph fingerprint and partition changes when a dynamically rebound factor creates cross-block coupling; old receipts are rejected.
- Forged partitions, submatrices, receipt fields, mismatched intermediate dimensions, non-endomorphism graphs, and invalid timestamps.
- A deliberate **false negative**: two individually mixed factors whose product is identity are refused because their input-factor support does not reveal a proper common decomposition.

The existing five experiment suites also run, for **55/55 local tests passed** in an isolated API-compatible VGI-affine harness. This is *not* the full repository's CI; the latter requires GitHub Actions or an actual repository checkout.

## Deterministic reference benchmark

Command from the `virtual_ground_interpreter` root:

```sh
python -m unittest discover -s tests -p 'test_invariant_blocks.py' -v
python -m examples.run_invariant_blocks
python -m unittest discover -s tests -p 'test_*.py' -v
```

The synthetic benchmark builds four opaque 48×48 dense operands over `Z/97Z`, with eight shuffled six-coordinate blocks. No operator metadata discloses these blocks; inspection of all **9,216** supplied coefficients recovers the partition. The algorithm prepares eight 6×6 composites, not one 48×48 composite.

Local measured medians (Python, isolated compatibility harness; see `reports/geometry_first_006_reference.json` for exact values):

| Request | Median |
|---|---:|
| Discover and certify eight block composites | 2.62 ms |
| Full dense composite preparation via prior VGI method | 30.45 ms |
| Block navigation at logical tick 2,048 | 3.01 ms |
| Full dense navigation at the same tick 2,048 | 58.19 ms |
| Block navigation at logical tick 10³⁰ + 11 | 33.46 ms |

For fixed square-matrix powering, the cubic arithmetic **proxy** improves from \(48^3=110{,}592\) to \(8(6^3)=1{,}728\), a ratio of **64×**; this is an operation-size estimate, **not** a benchmark speedup claim. The observed timings compare explicitly different preparation strategies for the same mathematical output. Neither strategy beats direct computation for arbitrary data or arbitrary structure; this is a synthetic block-structured workload.

### Evidence and limitations

- No performance claims for GPU, distributed transport, or E-CPU hosts have been measured.
- Full dense input matrices are supplied and their coefficients inspected; this is not sublinear input observation.
- An undetected cross-block coefficient **cannot** be silently ignored because every factor coefficient is audited; the result applies only to the admitted in-memory operand snapshot.
- This technique does not recover latent invariant subspaces of simultaneously diagonalizable but fully dense matrices. To attempt that next, a new exact modular change-of-basis proof is needed. Composite moduli require additional ring-care, so a restricted finite-field experiment would be prudent.
- Faster query costs amortize certificate preparation over many navigations; a single short-time query need not benefit.

## E-CPU research interface

The discovered certificate can be a pure, typed Virtual Layer computational object. E-CPU's existing host/hypervisor admission, route selection, execution claims, checkpoints and provenance checks should remain separate authorities. A future host operation would receive an admitted **graph/certificate reference and logical target**; it should validate the exact Ground and operand snapshot before issuing a result receipt. No production E-CPU integration is asserted by this PR.

## Next question

Can a certified change of basis expose independent invariant factors when every input matrix has dense off-diagonal support? A useful next control is a family of mutually commuting finite-field matrices with a shared diagonalizing basis, plus a noncommuting near-miss. The proof would need to verify the basis transform, its inverse, and the resulting block-diagonal form for **every** factor, with a complete refusal whenever such a decomposition cannot be established.