# VLD-002B — Symbolic observer quotients

## Capability

Discover the smallest observation-preserving deterministic quotient of a **switched affine finite-field system** without enumerating its `p**n` states. Admission independently checks a portable exact witness. After admission, advance a quotient through repeated input macros using binary exponentiation.

This extends [VLD-002 certified finite-state reduction](CERTIFIED_STATE_REDUCTION.md) from explicit transition tables to algebraically specified state spaces.

## Mathematical model

A source Ground consists of a prime `p`, `n` state coordinates in `F_p`, sorted input symbols `a`, affine transition matrices `A_a` and offsets `b_a`, and an observation map `(C,h)`:

```
state        x             ∈ F_p^n
input a      f_a(x)        = A_a x + b_a
observation  O(x)          = C x + h
```

The specified observer sees the **current** state (Moore output). An input word `w = (a_1,...,a_t)` means apply `a_1` first and `a_t` last. Hence the linear coefficient of the observation after `w` is `C A_(a_t) ... A_(a_1)`; affine constants do not affect whether two initial states are distinguishable.

Construct the **smallest input-invariant row space**

```
V = span { rows(C A_(a_t) ... A_(a_1)) : t≥0, a_i∈alphabet }.
```

Let the rows of `B` be a basis of `V`, with rank `r`. The quotient map is `q(x)=B x`. Closure of `V` under right multiplication by every `A_a` gives exactly computable reduced matrices `T_a`, offsets `t_a` and observation map `D`:

```
B A_a = T_a B       B b_a = t_a        C = D B.
```

Therefore `q(f_a(x)) = T_a q(x) + t_a` and `O(x) = D q(x) + h`. The equalities commute after **every** input, so by induction they preserve observations for all finite input words, not merely tested traces.

### Minimality, not only soundness

Each basis row is accompanied by a pair `(observation_output_index, input_word)` and must independently reproduce that specific `C_i A_word`. If `B x ≠ B x'`, some basis row distinguishes the pair. Its witness word therefore produces a different observation from the two source states. No two distinct quotient states can be merged while preserving all possible future observations. Consequently there are **exactly `p**r` behavior classes among all `p**n` possible initial states**.

The quantified state domain is *every possible initial vector*. With a singled-out initial vector or a restricted reachable set, a smaller quotient may exist. Likewise, this result is not a theorem about arbitrary nonlinear, stochastic, unbounded-memory, or unknown-source machines.

## Discovery and independent admission

`vgi/symbolic_reduction.py` provides:

- `AffineGround` / `AffineAction`: bounded immutable finite-field machine description with canonical SHA-256 content identity.
- `discover_symbolic_reduction(source)`: grow the observation row orbit until closed, storing a word witness for every admitted independent row; construct `T_a`, `t_a`, `D` by exact field linear algebra.
- `admit_symbolic_reduction(source, certificate)`: independently check the content identity, canonical matrix dimensions and residues, full row rank, every distinguishing word, every commuting matrix equality, every affine offset and the output map. **Does not run the discovery or coordinate solver.**
- `AdmittedSymbolicGround.project / step / observe`: execute the admitted quotient.
- `AdmittedSymbolicGround.jump` and `.jump_word`: compose a repeated symbol or finite input sequence then exponentiate its affine map. Complexity is logarithmic in repetitions, with matrix multiplication at reduced dimension `r`.

Certificates contain the original Ground digest, basis, distinguishing words, reduced input maps, output map and content digest. Digests provide content identity, **not authentication, external source authority or a Lean kernel proof**.

### Example

From the repository root:

```bash
cd virtual_ground_interpreter
python examples/symbolic_reduction_demo.py
python -m unittest tests/test_symbolic_reduction.py -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Minimal API:

```python
source = AffineGround(5, 1, (
    AffineAction('tick', ((1,),), (2,)),
), ((1,),), (0,))

candidate = discover_symbolic_reduction(source)
quotient = admit_symbolic_reduction(source, candidate)
assert quotient.jump(quotient.project((3,)), 'tick', 10**100) == ((3 + 2*10**100) % 5,)
```

## Reproduced local experiments (2026-11-25)

| Experiment | Original states | Certified quotient | Candidate / admission time | Main finding |
| --- | ---: | ---: | ---: | --- |
| 128-coordinate binary, hidden subspace | `2**128` | `2**3 = 8` | ~9.7 / 7.9 ms | 125 hidden dimensions eliminated |
| 80-coordinate binary, hidden subspace | `2**80` | `8` | ~4.7 / 3.6 ms | ~984-byte JSON witness |
| 60-coordinate ternary, hidden subspace | `3**60` | `3**3 = 27` | ~2.5 / 2.3 ms | Works over nonbinary prime field |
| 64-coordinate rotating register | `2**64` | `2**64` | ~61 / 404 ms | Delayed observability blocks incorrect compression |

These are local Python 3.13 timings for the defined synthetic systems, not comparative production performance or network benchmarks. At reduced rank 3, `10**100` repetitions of a two-input macro took ~2–3 ms locally; at rank 64, the same type of jump took ~4.5 seconds. Time-powering computes an algebraic state, **not elapsed physical time**.

Local test suite: **19/19 passed**, including 126 randomized affine systems across fields `F_2`, `F_3`, `F_5`, independent direct trace comparisons, all-pairs small-machine witness distinction, input-macro jumps, corrupted and re-hashed certificates, and an adapter comparison against the explicit VLD-002 Mealy reducer for an all-reachable machine. No Lean check or full repository CI claim is made by these local results.

## Boundary-crossing counterexample

A 64-bit cyclic shift register observed only at position 0 can reveal all 64 bits after enough inputs. This experiment correctly returns rank 64. **An observer that sees only one coordinate per step does not imply a one-dimensional sufficient state.** The necessary state is determined by all future observations.

## Next build surfaces

1. **Guarded affine pieces:** introduce an observer-respecting partition for conditional transitions. Certify guards and cross-region quotient transitions; reject if a hidden variable can change the selected region. This is the next nonlinear frontier, not covered by the current certificate.
2. **E-CPU message-state adapter:** translate bounded sequence counters, retry windows and scheduler phases into affine input actions (`SEND`, `ACK`, `TIMEOUT`). Reuse the independently admitted quotient as a computational Ground. Correctness must include protocol side effects and not solely state-vector observations.
3. **Proof kernel translation:** port the algebraic commuting equations and witness-based distinguishability argument into Lean for third-party kernel recheck. Keep the source-Ground fingerprint and exact field assumptions explicit.
4. **Larger symbolic Grounds:** structured/sparse matrices and operator circuit representations to avoid `O(n²)` input descriptions when `n` grows. This moves beyond the present dense bounded implementation.
