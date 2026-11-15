# GEOMETRY-FIRST-004 — Structural law extraction from an executable program

**Status:** bounded, deterministic experimental interpreter for a closed *source-language* subset. Stack on GEOMETRY-FIRST-003. Source observation is not a remote attestation or a proof about arbitrary Python execution.

## Question

Can an algorithm reveal a navigable algebraic representation *from its operation structure*, rather than requiring a separately handwritten transition polynomial or the full finite-state transition table?

## Contract and execution model

The new `vgi.program_law` module consumes **source text**, a prime modulus `p` in the existing VGI range, and an optional partial transition-observation ledger. It parses but **never executes** the supplied code. The only accepted source shape is:

```python
def advance(x, y):
    squared = y * y
    next_x = x + squared
    next_y = y + 1
    return (next_x % 101, next_y % 101)
```

The admitted syntax is two integer input parameters (`x`, `y`), local straight-line assignment (including simultaneous tuple assignment), a final two-element return, integer constants, unary `+`/`-`, binary `+`/`-`/`*`, constant exponent `**k` with `0 <= k <= 6`, and `% p` where `p` **must** be exactly the declared modulus. Source and AST node counts, intermediate expression degrees, final output degrees and feature dimensions are bounded. Unsupported branches, loops, calls, attributes, subscripts, imports, annotations, defaults, free variables, external state, and any other AST shape are refused *prior to navigation*. Runtime input states are canonical elements of `F_p^2`.

The interpreter gives these nodes the standard commutative prime-field arithmetic meaning. Its syntactic induction maps every accepted expression to an exact coefficient dictionary in `F_p[x,y]`. Local assignments substitute previous coefficient dictionaries; simultaneous assignment evaluates right-hand sides against the same old environment. Applying `mod p` leaves the field polynomial unchanged. This is a *denotational semantics* proof for the allowed grammar, not verification of the CPython runtime or another execution substrate.

`ExtractedProgramLaw(source, p)` derives `x_next` and `y_next` entirely from the admitted AST. These are **outputs of extraction**; callers do not supply them. It also binds exact source bytes, canonical AST structure and model identities. Semantically equivalent programs may have different provenance digests.

`certify_program(source, p, ...)` uses the **existing** `sparse_polynomial._construct_lift` and `ModularAffineMap`. It discovers a finite set of monomials `phi(x,y)` closed under the structurally derived transition, then checks each feature's successor as an **exact polynomial-coefficient identity**:

`phi(F(x,y)) = M phi(x,y) + b` for every `(x,y)` in `F_p^2`.

Because identities are checked symbolically, this route does not enumerate all `p^2` source states or need a caller-supplied law. The accepted source itself is the mathematical description. One can navigate to `t` by exponentiation of a `(feature_dimension + 1)` homogeneous matrix in `O(log t)` matrix compositions; query results include the exact input source digest, model and certificate fingerprints, optional observed-evidence fingerprint, destination state, logical tick, and zero materialized intermediate states. Per-query fingerprinting does **not** scan the full chart.

## Example: nonlinear source -> linear lifted law

The source above structurally yields

`x' = x + y^2`, `y' = y + 1` (mod 101).

The closure engine introduces `z = y^2`, then independently certifies:

```text
x' = x + z
 y' = y + 1
 z' = z + 2*y + 1
```

At logical time `10^30 + 11` from `(39,47)`, the program navigator returns `(81,57)`. An independent exact integer sum-of-squares reference verifies the result, and small random-time queries agree with conventional repeated execution of a test-owned CPython fixture. A cubic source similarly discovers both `y^2` and `y^3` without those coordinates being supplied by the caller.

The source-level structural extraction fills the missing step from GEOMETRY-FIRST-003: the symbolic model is **derived from a statically checkable program** instead of separately specified by a caller. The scope is still that source-language's formal semantics.

## Evidence and trust distinctions

Three independent things must not be confused:

1. **AST/model identity**: SHA-256 digests bind exact source, structural expression, and derived mathematical law. A digest is not an attestation of a live process.
2. **Symbolic algebraic proof**: identities are exact for the accepted AST's *declared interpretation* over `F_p`. This justifies fast-forward only in that model.
3. **External correspondence**: if observations from a particular host/process are supplied, the certificate checks them but does not infer all remaining physical transitions from those samples. A single contradictory observation refuses certification. The source can be changed without changing some sampled outputs, so environmental admission requires independent trust in the actual code/provenance and host runtime.

The `ProgramNavigationCertificate.to_dict()` explicitly returns `external_implementation_verified: false`. The `ProgramNavigationResult` carries `trust_scope: formal_bounded_program_semantics_only`. No API here promotes sample-only fitting to an unrestricted law. No calls to `exec()`/`eval()` occur on source in the production module (test-owned fixture strings are executed **only in the independent differential tests**).

### Negative controls

- External calls, imported modules, loops, conditional branches, hidden globals, noninteger or wrong-modulus reduction, unbound variables: **refused**.
- `x'=x*x, y'=y+1`: feature closure grows beyond supported finite basis: **refused**, not approximated.
- `x'=x+y^4`: source law degree exceeds the bounded interpreter: **refused**.
- Cubic requires degree-three feature closure; asking for degree two: **refused**.
- Forged feature matrix, incomplete feature set or contradicting observation: **refused**.
- Simultaneous assignments have distinct semantics from sequential ones; the differential control verifies the distinction.

## Measurements and cost

The reference fixture uses 10,201 *mathematically representable* states in `F_101^2`, but the compiler does not enumerate them. It binds one accepted source law, and optional six rank-independent transition observations can check host correspondence at those six points.

The accompanying JSON report contains medians measured with an **isolated API-compatible local VGI affine harness**. It compares 25,000 repeated reference transitions with a logarithmic navigation query on the same single recurrence, and includes compile+certificate costs separately. This is evidence for a change in computational representation and repeated-query cost, not an unrestricted faster-than-CPU, Numpy, or hardware accelerator claim.

The bounded source **is a stronger assumption than sparse observation**: access to a verified, trusted program representation is precisely what permits exact symbolic proof without exhaustively observing each state. No runtime/host attestation, network transfer, or physical calibration cost is included.

## Reproduction

From `virtual_ground_interpreter`:

```bash
python -m unittest discover -s tests -p 'test_program_law.py' -v
python -m examples.run_program_law
python -m unittest discover -s tests -p 'test_*.py' -v
```

The isolated harness passed 11 new tests and 33 total geometry-first tests. Integration with the actual repository should be confirmed by its GitHub Actions run before merging.

## E-CPU architecture correspondence and next build

The current E-CPU sources already distinguish mathematically named workloads from execution authority:

- `mailcpu/virtual_layer.py`: a `VirtualLayerWorkload` carries **intent and coordinate**, not executable code or authority.
- `mailcpu/navigation_admission.py`: the hypervisor owns process-bound grants and replays evidence against a trusted provider.
- `mailcpu/vgi_host.py` and `mailcpu/transit_vgi.py`: the existing VGI host boundary transports typed tasks, not source code; it is governed by the receiver's HeadlessOS and Virtual Layer operator registry.
- `mailcpu/navigable_computation_checkpoint.py` and `mailcpu/transferable_execution_claim.py`: existing checkpoint/rehome and pure-operation result-fencing components can retain certificate and result identity across reassignment.

**Do not ship arbitrary Python source in a `VirtualLayerWorkload`.** A proposed integration would first admit/validate a bounded source object on the trusted host, store its structural certificate and source digest in structural memory, register an authorized pure operator for a **reference** to that verified certificate, and require the hypervisor to bind the request's starting state, logical timestamp, expected operator/model fingerprint and resource envelope. The independent host verifier re-evaluates the polynomial identity or certificate provenance before accepting a result. This is only a design sketch here; the experiment does not implement an E-CPU operator, grant, or host receipt.

## Next falsification target

Broaden from 2-variable, degree<=3 prime-field straight-line recurrences to a typed computational IR with sparse matrices or parameterized operator families. Distinguish a successful *lift* from mere delayed materialization, and count upfront structural-analysis cost, intermediate result materialization, transport, and saved operations across repeated contexts. Never claim arbitrary dynamic matrix multiplication becomes free by changing its address.