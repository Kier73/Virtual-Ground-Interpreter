# GEOMETRY-FIRST-008 — portable similarity-basis structural memory

## Research question

Can an expensive mathematical understanding of a computational Ground be
**reused by an independent observer** without either trusting a bare claim or
repeating the original basis-discovery search?

**Yes, for the exact finite-field similarity-block representations admitted by
GEOMETRY-FIRST-007.** A self-contained memory record supplies the typed
operator snapshot, a proposed common commuting witness, a change of basis,
its inverse, block boundaries, and ordered block-local products. The receiving
observer checks the *entire proof against every input factor*. It does not
solve the original commutant linear system or search for a new basis.

This is structural memory of a *mathematical model*; it is **not** proof that
an external processor or communication path faithfully implements the model,
and it grants no E-CPU execution authority.

## Authority and observation are separate

There are three distinct assertions:

1. **Self-contained mathematical validity**. A record describes a typed,
   finite-prime-field operator graph and a basis witness. Its validity is
   checked independently by the receiver over every input coefficient.
2. **Context identity**. Canonical UTF-8 JSON and SHA-256 digests bind the
   exact graph snapshot, witness, and local products. The receiver may also
   require an *out-of-band expected graph digest and memory digest*. Without
   those anchors, an adversary could supply a different, fully self-consistent
   mathematical record.
3. **Execution authority**. The E-CPU HeadlessOS/Hypervisor and computational
   host must separately establish operator eligibility, permissions, host
   identity, receipt ownership, and durable transport/recovery state. None of
   those authorities can be inferred from SHA-256 or algebra alone.

No signature, universal correctness of unseen states, remote attestation, or
cross-host network execution is claimed here.

## Mathematically exact replay

For each factor `A_i` in an ordered operator chain, the structural memory
provides a finite-field witness `C`, invertible matrix `P`, inverse `Q`, and
coordinate blocks `I_1...I_k` with distinct eigenvalues `lambda_j`.

The receiver verifies, using exact arithmetic in `F_p`:

```
Q*P = P*Q = I
C*A_i = A_i*C                   for EVERY admitted factor
C*P[:,j] = lambda_block(j)*P[:,j]
B_i = Q*A_i*P                   for EVERY admitted factor
B_i[a,b] = 0                   for every cross-block coefficient
F_j = product of the B_i block j in the exact original factor order
```

From this, `A_0 ... A_{L-1} = P diag(F_1,...,F_k) Q`. Its `t`-fold
application to a typed vector is calculated as

```
F^t * x = P * diag(F_1^t,...,F_k^t) * Q * x
```

The block powers reuse VGI's existing `ModularAffineMap.power`. The
**verifier never performs the O(L*n^6) commutant search**. Its proof work
still depends on every factor, basis size, and block coefficient; it is not
constant-time admission, free data transport, or reduced input storage.

A downloaded record does not make external effects true. Its validity is
restricted to the declared operator coefficients and algebraic semantics.

## Actual implementation

- `vgi/structural_memory.py`: bounded, strictly decoded, content-addressed
  JSON record export/import, independent proof verification, typed navigation
  receipts, and conservatively checked dynamic rebinds. The 1 MiB record
  budget and 4,096-bit logical-time ceiling are *implementation bounds*.
- `tests/test_structural_memory.py`: 13 adversarial tests, including a true
  independent Python process with separate observer state, dense/stepwise
  controls, forged/mismatched proof/graph/receipt refusals, external digest
  anchoring, noncanonical JSON, changed operands, and intact rebinds.
- `examples/verify_basis_memory.py`: minimal independent-process verifier,
  reading **only JSON** and independently supplied expected SHA-256 digests.
  It cannot execute code carried in the record. Its output is a proof-scoped
  mathematical result, not an E-CPU execution receipt.
- `examples/run_structural_memory.py`: reproducible producer/receiver
  benchmark and second-process validation.
- `reports/geometry_first_008_reference.json`: deterministic run outputs and
  separately measured discovery, export, admission, rebind, and query times.

### Updating operands without repeating discovery

`AdmittedSimilarityMemory.rebind(updated_graph)` reuses `P`, `Q`, blocks and
`C` **only if** it can independently recheck every required proof property
for the new immutable operand graph. It recomputes the ordered local products,
reconstructs a new certificate, and assigns a **new content digest**. The old
navigation receipts do not verify for the new model.

A cross-block coefficient that destroys this witness is refused, even if the
new graph happens to have another useful decomposition. A fresh basis search
would then be a separate, explicitly authorized procedure.

## Reproduction

From the `virtual_ground_interpreter/` directory:

```shell
python -m unittest discover -s tests -p 'test_structural_memory.py' -v
python -m examples.run_structural_memory
python -m unittest discover -s tests -p 'test_*.py' -v
```

To exercise a different interpreter process directly, export a memory JSON
file and run:

```shell
python -m examples.verify_basis_memory \
  --memory my_basis.json \
  --graph-sha256 <expected-graph-digest> \
  --memory-sha256 <expected-record-digest> \
  --tick 123456789 \
  --vector 1,2,3,4,5,6,7,8
```

These hashes must come from a trusted upstream admission process, not from
whatever the untrusted sender places in the file.

## Reference benchmark and amortization

The deterministic case is a 12-dimensional finite-field graph (`F_101`)
containing three operators with a hidden 4+4+4 basis, generated as in the
preceding experiment. The original coordinate detector sees one 12-wide
block; discovery identifies three 4-dimensional blocks. A separate process
validates the same distant-time result at logical time `10^30+11`.

The measured reference costs are recorded in
`reports/geometry_first_008_reference.json`. They are pure Python timings
from an isolated compatibility harness, **not official GitHub CI, an E-CPU
host, or a platform acceleration claim**. The expensive producer discovery
is compared to a fully revalidated receiver admission, not to a relaxed hash
lookup. The entire record includes all original factors, which must be
transferred and authenticated by a higher authority if used between hosts.

Total cost of `N` independently navigating observers under this model:

```
search-per-observer  ≈ N * discovery + N * query
portable proof       ≈ discovery + export + N * admission + N * query
```

This estimate omits communications, reliable delivery, and authorization and
is only useful if the same Ground is reused enough times to recover the
up-front discovery cost.

## Interface relationship with E-CPU

A future integration can adopt the following conservative workflow:

1. A locally trusted analyzer certifies the VGI mathematical Ground and
   publishes the canonical memory digest and required operator manifest.
2. E-CPU's existing computational host and hypervisor admit a *pure* operator
   request. The host supplies an independently trusted expected graph digest
   or content-addressed Ground reference, not arbitrary Python to execute.
3. The receiver obtains the record over an authenticated, reliable channel
   and calls `admit_similarity_memory` with the expected digests. This
   repeats all mathematical checks but **not discovery**.
4. Subsequent logical-time demands refer to the admitted, immutable memory
   and typed initial vector; result receipts bind the Ground and query.
5. E-CPU's existing execution claim/replay mechanisms fence reassignment,
   persist verified outputs and ensure only an authorized receiver commits
   the result. These steps are **not yet implemented in this PR**.

This preserves the principle that the host can be any suitable observer, as
long as it can validate the representation, the navigation result, and its
separately authorized operating context.

## Next experimental questions

- Store and retrieve mathematical memory through E-CPU's actual structural
  memory and transit authorities, then test receiver restart and reassignment.
- Split reusable structural *basis* evidence from operand-specific certificates
  so updated pure operators can verify against a common chart without
  transferring every preceding factor snapshot.
- Investigate when dense preparation or independent component navigation is
  actually cheaper after including verification, transport, and amortization.
- Expand to nonsplitting commutants and extension-field or nonsemisimple
  invariant structures, keeping proof and claimed scope exact.