# GEOMETRY-FIRST-003 — Sparse probes, symbolic model certificates, and the unknown-edge frontier

**Status:** executable synthetic finite-field experiment, stacked on GEOMETRY-FIRST-002. The exact navigation certificate concerns a **declared mathematical Ground**, not an arbitrarily sampled real-world system.

## Research question

Can VGI reduce the number of transitions it must *observe* before discovering navigable algebra while retaining a justified distinction between observed evidence, inferred hypotheses, and exact model-level proof?

The previous experiments enumerated all `101² = 10,201` transition edges before certifying a polynomial lift. That is a valid ground-level proof, but enumeration scales with the size of the finite domain. A new approach should avoid hiding the same enumeration cost inside the proposed navigator, and it must not silently treat a fitted polynomial as an externally verified law.

## A key mathematical distinction

Let a finite-field state be `(x,y) ∈ F_p²`. Suppose an action is *known by an independent mathematical specification* to be a polynomial map of total degree at most `d`, and suppose `d < p`. There are

\[
M = \binom{d+2}{2}
\]

possible monomials. An `M × M` full-rank matrix of evaluations at queried states determines the coefficients of each output component uniquely within the declared polynomial class. The proof is a linear-algebra fact *conditional on the function belonging to that class*; the observations themselves do not prove the premise. For a degree-two map over `F_101²`, `M=6` as opposed to `10,201` points.

A finite set of samples from an **unconstrained unknown system** can always be matched by a malicious or higher-degree law that disagrees elsewhere. Thus no finite low-rank probe set alone authorizes a shortcut for that system. The module exposes this distinction in its API:

- `SparseTransitionObservations`: source/target pairs plus source/revision labels (these labels are untrusted assertions, not authentication).
- `propose_rank_probes(p,d)`: choose exactly the missing rank-independent observations for the declared monomial basis; no confidence estimates or guessed probabilities.
- `fit_sparse_hypothesis(...)`: infer output polynomials, audit all available held-out edges, retain their fingerprints, but **always refuse `state_at()`**.
- `DeclaredPolynomialGround`: an explicit, canonical symbolic action definition. This is a mathematical model declaration, not proof about an external implementation.
- `certify_declared_model(hypothesis, ground)`: require identical inferred and declared polynomials; discover monomials required for a closed feature representation; verify each lifted relation by exact coefficient arithmetic, without enumerating the entire state space.
- `ModelCertifiedSparseNavigation.state_at(...)`: use the existing `ModularAffineMap.power` to reach arbitrary logical time in the **declared formal model**. The returned result states `trust_scope="formal_declared_ground_only"` and binds exact model, observation, and certificate digests.

If the symbolic law declaration is not available, or if an observation disagrees with it, the result remains a hypothesis or is rejected. A SHA-256 fingerprint is an identity check, not a remote signature, kernel proof, or evidence of real-world truth.

## Discovering the nonlinear geometry

The unlabelled action in the synthetic fixture has declared law

\[
x' = x+y^2,\qquad y'=y+1 \pmod {101}.
\]

Six full-rank fitting observations plus two independent held-out observations recover the output polynomials. The algorithm then derives a **new feature** `z=y²` by closure of the symbolic expressions:

\[
\left[\begin{matrix}x'\\y'\\z'\end{matrix}\right]
=\left[\begin{matrix}1&0&1\\0&1&0\\0&2&1\end{matrix}\right]
\left[\begin{matrix}x\\y\\z\end{matrix}\right]
+\left[\begin{matrix}0\\1\\1\end{matrix}\right]\pmod{101}.
\]

Since these are **identical polynomials** in the declared Ground, they agree at every finite-field state. The lifted map maintains the invariant `z=y²` and can be powered by repeated squaring. This proves a distant-time shortcut within this specified model, without the prior full `10,201`-edge audit.

The same general procedure discovers both `y²` and `y³` for `x'=x+y³, y'=y+1`, and refuses a degree-two representation that cannot contain them. It also refuses unclosed nonlinear feature growth when the declared degree budget is exceeded. The feature basis and the algebraic law are not supplied as the final lifted transformation.

## Adversarial negative result — important

We change **one transition at a previously unobserved state**, while leaving every fitting and held-out observation unchanged. The hypothesis and its digest are unchanged. As soon as that state is queried, the candidate is contradicted and rejected.

This is a constructive counterexample to interpreting sparse interpolation as an unconditional law of an unknown system. The symbolic certificate only concerns its own declared mathematical Ground; it does *not* retroactively validate that external counterexample world.

For a physical/external substrate, a future path needs either (a) trusted executable specification and independently checked correspondence to observation, or (b) sufficiently strong external evidence and a clearly declared probabilistic risk bound — never an invented universal guarantee from sparse samples.

## Measured reference results

`python -m examples.run_sparse_polynomial` from the VGI directory using the isolated local harness that substitutes an API-compatible `ModularAffineMap`. It is **not the complete GitHub repository runtime**. The results are reproducible JSON in `reports/geometry_first_003_reference.json`; timings are exploratory local medians.

| Measure | Result |
|---|---:|
| Finite domain | 10,201 states |
| Required fitting probes | 6 |
| Independent held-out observations | 2 |
| Total observed edges | 8 |
| Observation-count reduction against exhaustive | 1,275.125× |
| Sparse hypothesis fitting | 0.164 ms |
| Model symbolic closure + certificate | 0.078 ms |
| Navigated query, `t=10³⁰+11` | 0.887 ms |
| Previous complete-edge discovery + certificate | 133.94 ms |
| Distant-time state from `(39,47)` | `(81,57)` |

**Cost accounting:** sparse discovery requires obtaining 8 samples, plus a separate valid model declaration and mathematical verification of that declaration, neither of which is free. This is **not** an overall 1,275× speedup; it is an observation-count reduction in a synthetic problem when a symbolic Ground definition is available. Model construction, external correspondence, runtime admission, and deployment costs are not included in timing figures. The large-t result was independently checked with the integer sum-of-squares formula and against the earlier exhaustive certificate. Dense matrix powers retain their dimension-dependent arithmetic cost; logical time is not physical elapsed time.

## Verification and refusals

The `test_sparse_polynomial.py` suite checks:

1. Minimal rank-complete probe selection, sample-only refusal to navigate, independent holdouts, and provenance identity.
2. Exact symbolic nonlinear lift and very distant time with independent closed-form control.
3. A single unobserved counterexample that sparse observations cannot detect, and that contradicts the model upon observation.
4. Incomplete rank, duplicate sources, invalid field/degree/coefficients, conflicting declared law, and over-budget feature growth.
5. Cubic discovery and refusal at an insufficient feature degree.
6. Differential agreement with the old full-edge certificate, plus 40 randomized finite-field affine models and independent step-by-step reference.

Tests passed in the isolated local API-compatible harness: **10 new tests, 22 combined GEOMETRY-FIRST-001/002/003 tests**. GitHub Actions must run the integrated package before asserting full repository compatibility.

## E-CPU correspondence

This result naturally divides responsibilities, without inventing another computation authority:

1. **VGI:** select informative probes, preserve partial observation records, infer candidate laws, and issue formal model-scoped certificates only when a separate symbolic mathematical law has been checked.
2. **E-CPU navigation-admission/hypervisor:** decide whether the declared model, source identity/revision, observation provenance, authority rights and requested logical-time jump are admissible for a specific operator and host. An opaque digest cannot establish external authority.
3. **E-CPU computational host / Transit / checkpoint:** perform pure matrix powering, route and rehome replay-safe results if needed, and publish a typed result receipt binding the model digest, observation digest, certificate digest, input state, logical timestamp, output state and implementation fingerprint.

The current experiment adds **no new E-CPU operator** and does not claim end-to-end distributed execution. It supplies proof and cost concepts for a future operator while preserving E-CPU's established authorization, recovery, and quorum authorities.

## Next falsification frontier

Test automatic **degree-bound discovery from authenticated operation structure**, without manually granting a model oracle. A promising path is to instrument an independently checkable finite-state transition DSL so VGI receives structural obligations from the program and observation commitments from its runtime. If these disagree, do not extrapolate. A second track can test probabilistic laws with honest uncertainty, but that must not be promoted to exact certification.

## Reproduction

From `virtual_ground_interpreter`:

```sh
python -m unittest discover -s tests -p 'test_sparse_polynomial.py' -v
python -m examples.run_sparse_polynomial
python -m unittest discover -s tests -p 'test_*.py' -v
```

This experiment uses only the Python standard library and already-existing VGI `ModularAffineMap` and GEOMETRY-FIRST-002 source. It is stacked on PR #25, itself stacked on PR #24.