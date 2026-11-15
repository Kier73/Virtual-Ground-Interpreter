# GEOMETRY-FIRST-007 — discover a common navigable basis

## Question

Can a computational Ground present as *dense, fully coupled* operators in the
host's coordinate frame, yet admit exact navigation through independent smaller
transformations in another, **discovered** coordinate system?

**Yes in a sharply defined case:** a finite prime field and a common commutant
with a fully splitting, non-scalar witness. The implementation does not receive
the conjugating basis or block boundaries. It derives a finite-dimensional
linear system from the actual admitted operator coefficients, solves that
system, tests bounded candidate witnesses and certifies the resulting basis.
It refuses unsupported cases rather than making a numerical approximation.

## Mathematical route: commuting witness, not commuting operators

For a typed closed graph with admitted factor matrices `A_0,...,A_{L-1}` of
size `n` over `F_p`, discover the vector space

```
Z = { C ∈ M_n(F_p) : C A_i = A_i C for every factor i }
```

The `n²` unknown entries of `C` satisfy `L*n²` homogeneous linear equations
in the worst case. Exact modular Gaussian elimination produces a basis of `Z`.
This step is exhaustive within the declared prime-field matrix model.

Search a bounded deterministic sequence of linear combinations of the
commutant basis. A proposed witness `C` is useful when it has **at least two distinct eigenvalues** in the base field, with eigenspaces whose dimensions
sum to `n`:

```
F_p^n = ker(C - λ_1 I) ⊕ ... ⊕ ker(C - λ_k I),   k >= 2
```

If `C` commutes with every `A_i`, each eigenspace is invariant under every
`A_i`. Assemble the eigenspace basis columns into `P`. Discover `P^{-1}` by
exact Gaussian elimination and transform every factor:

```
B_i = P^{-1} A_i P
A_i = P B_i P^{-1}
```

The certificate **independently** verifies `P P^{-1} = P^{-1} P = I`,
`C A_i = A_i C`, the eigenvector relation for every column, the exact
absence of off-block entries in **every** `B_i`, and equality of each proposed
block-local composite with the original factor order. The original `A_i`
need not commute with one another.

At time `t` the fixed ordered graph composite `F = A_0 A_1 ... A_{L-1}` is
navigated through its smaller block representatives:

```
F^t x = P diag(F_1^t, ..., F_k^t) P^{-1} x
```

Powering reuses the existing `vgi.affine.ModularAffineMap.power`, not a new
approximate numerical engine. Neither an intermediate-state orbit nor the
full ambient composite is materialized during a certified block query.

## Evidence and refusal boundaries

- **All factors inspected:** The commutant constraints and certificate checks
  are exact on every matrix coefficient of every admitted factor. This is not
  statistically inferred from sample vectors.
- **Prime field only:** Composite moduli are refused. The elimination and
  eigenvalue method require field inverses.
- **Fully splitting witness only:** If the chosen `C` has nontrivial
  extension-field eigenvalues or is not diagonalizable over `F_p`, its
  eigenspaces cannot produce an admitted decomposition. A bounded search
  failure is **not** a proof that no invariant subspace exists.
- **Finite search envelope:** Dimensions `2..16`, prime moduli `2..257`,
  candidate budget `1..256` (24 by default). These are implementation
  resource bounds, not mathematical impossibility claims.
- **Graph identity:** Certificate and receipts bind exact typed frame,
  modulus, operand values, and operand graph fingerprint; replacing an operand
  requires a new discovery and a new certificate. Receipt validation
  recomputes the stated result rather than accepting its metadata.
- **Trust:** SHA-256 identifies the declared mathematical context, not the
  external process, hardware, authority, or physical transition semantics.
  E-CPU admission must remain independent of mathematical certification.
- **Not general similarity search:** This does not find extension-field or
  inseparable Jordan decompositions, arbitrary invariant flags, or structure
  that arises only after cancellation in the *whole* composite. The
  discovered eigenspaces are shared by every factor.

## Evidence: deterministic local benchmark

Run from `virtual_ground_interpreter/`:

```
python -m unittest discover -s tests -p 'test_similarity_blocks.py' -v
python -m examples.run_similarity_blocks
python -m unittest discover -s tests -p 'test_*.py' -v
```

The benchmark constructs three *independent, noncommuting within-block* 4×4
factor systems, applies an unprovided invertible mixing basis, then supplies
only their opaque 12×12 dense representatives to discovery. No hidden basis
is given to the classifier. Normal coordinate support discovers one large
12-dimensional block. The commutant method discovers **three new blocks,
4+4+4**, and certifies every original factor in the recovered basis.

Reference local numbers from `reports/geometry_first_007_reference.json`:

| Phase | Median |
| --- | ---: |
| Discover and certify common similarity basis | 695.14 ms |
| Conventional dense-composite preparation | 0.74 ms |
| Repeated-query navigation to logical tick 4096, similarity basis | 0.53 ms |
| Same-time dense navigation | 1.73 ms |
| Similarity navigation to logical tick `10^30+11` | 4.86 ms |

Both methods agree at tick 4096 and tick `10^30+11`; independent direct
transition execution was also checked at ordinary small ticks. An exact
arithmetic *cubic work proxy* falls from `12³ = 1728` to
`3 × 4³ = 192` (9×), **not** a 9× benchmark speedup. The preliminary
admission cost is vastly larger than a single dense query, so repeated use
or a host-provided valid basis/proof would be needed to amortize discovery.
The timings are pure local Python in an **API-compatible test harness**,
not E-CPU execution, an official full VGI repository CI run, or a hardware
acceleration claim.

## E-CPU integration direction

A pure VGI structural-analysis operator could produce a certificate-ground
reference, a typed graph/source digest, and admissible navigation methods.
The E-CPU hypervisor and its existing Virtual Layer operator permissions
would admit (or reject) operations; the computational-host catalogue selects
eligible substrates; reliable channels/checkpoints retain receipts and
context. Never trust a transferred `P` or `C` solely because their digest
matches: the destination must verify algebra, policy and input identity.

## Natural follow-ups

1. Use stable structured witness evidence or preadmitted structural memory to
   reduce repeated centralizer-solve cost across hosts and query epochs.
2. Explore structure that only appears in the composed map, after factor
   cancellation, and compare the extra dense preparation cost honestly.
3. Explore polynomial factorization and extension-field invariant subspaces
   where no complete base-field eigenbasis is available.
4. Measure the proof verification and query costs on a real E-CPU host under
   its native admission/recovery receipts instead of an isolated harness.