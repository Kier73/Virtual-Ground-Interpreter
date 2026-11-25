# VLD-002C — Guarded Process Grounds

A computational Ground should execute in motion, not merely classify or store
an equivalence class. VLD-002C extends the affine observer-quotient compiler to
**state-dependent conditional transitions**, adds independent admission for
nonlinear branching, process receipts, selective live migration, and certified
logarithmic jumps on invariant branches.

## 1. Executable source semantics

For each input symbol `a`, define a state in `F_p^n`, an affine predicate,
and two distinct affine successor maps:

```
condition: (g_a x == c_a) over F_p
if true:  x_next = A_a^+ x + b_a^+
if false: x_next = A_a^- x + b_a^-
y = C x + d
```

The equality predicate is nonlinear as a global state transition: it switches
between affine maps. The declared observation is of the **current** state.
The supported prime fields have `2 <= p <= 251`, dimension `1..128`, at most
12 inputs and 64 observation rows. The proof covers **all initial states** in
`F_p^n`, not just one accessible trajectory.

## 2. Sufficient observer coordinates

Find a full-row-rank matrix `B` and interpret the smaller state as `z = Bx`.
A certificate carries `T_a^+`, `T_a^-`, `t_a^+`, `t_a^-`, a projected guard
`gamma_a` when required, and an output map `D`:

```
C = D B
B A_a^+ = T_a^+ B       B b_a^+ = t_a^+
B A_a^- = T_a^- B       B b_a^- = t_a^-
```

For each `a`, independent admission requires one of:

1. **Guard visible**: `gamma_a B = g_a`, so the condition can be evaluated
   from `z` exactly; or
2. **Guard elided**: `T_a^+ == T_a^-` and `t_a^+ == t_a^-`, so the condition
   cannot alter the next observer state, regardless of hidden source state.

These identities commute for one transition, then inductively for every
finite input word. In particular an observer can execute the reduced machine
without consulting source state once admission succeeds.

The compiler begins with the span of `C`, closes the row space under **both**
branches of every input, adds a predicate row if the two projected updates
still differ, and repeats until stable. Adding a row may uncover new
transition dependencies: closure always runs again. Every strict refinement
raises rank, so the procedure terminates after at most `n` additions.

The strategy is deliberately conservative: it closes both branches over all
source states, even ones a guarded transition might never take. **No nonlinear
minimality theorem is claimed.** Redundant constraints are eligible for later
SMT/finite-field reachability refinement and exact proof.

## 3. A surprising useful fact: irrelevant conditions are removable

A branching predicate can depend on a hundred hidden variables and remain
unnecessary if both branches have identical **projected** effects. Keeping
such a predicate would classify irrelevant information rather than support
the intended computation. VLD-002C stores `guard: null` in that case;
admission rejects any attempted elision with unequal projected branches.

Conversely, a predicate that changes only a hidden register may become
necessary if a *later* input makes that register visible. The closure search
captures that delayed dependency by repeatedly applying all branch matrices.

## 4. Running and checking the process

```python
cert = discover_guarded_reduction(source)
q = admit_guarded_reduction(source, cert)
z0 = q.project(source_snapshot)
receipt = run_guarded(q, z0, ('tick',) * 16)
assert verify_guarded_receipt(q, receipt)['status'] == 'VERIFIED'
```

Each transition records input, prior and next quotient coordinates, chosen
branch or `elided`, observed output, and a chained SHA-256 value. Replay
checks the entire state transition sequence against independently admitted
algebra, not just a digest. SHA-256 is a **content identity**, not host
signature or authority. For authenticated external operations, bind receipts
to E-CPU source, epoch, host and authority qualifications separately.

## 5. On-demand observation during live Ground upgrades

Suppose the process is running under `B_old` and new outputs require `B_new`.
Both reductions must certify the **same source transition dynamics**.
Construct a complement `P` of `rowspan(B_old)` in `rowspan([B_old;B_new])`.
Then a migration plan contains exact coefficients `L`:

```
B_new = L [ B_old ; P ]
z_new = L [ z_old ; P x ]
```

A process can migrate without materializing the entire source state if it
obtains just the missing measurements `P x`. The number required is

```
rank([B_old; B_new]) - rank(B_old)
```

and is minimal among **independent linear measurements**, for arbitrary
source states and exact linear reconstruction. Migration verifies the lift
algebra and refuses to mix different transition systems. The external host
must authenticate the probe values and ensure they refer to the **same
logical state/epoch** as `z_old`; the algebra alone cannot authenticate them.

A central invariant follows: **a reduced Ground cannot reconstruct a newly
needed hidden coordinate from nothing**. When the observer changes, either
a sufficient structural relationship exists or additional observation is
required. The protocol expresses the exact observation budget.

## 6. Time navigation through invariant branches

A guarded process normally requires executing its branch decisions. A repeated
input can be exponentiated if the selected branch is provably invariant.
Let the quotient guard be `g z == c`, and the selected affine branch be
`z' = Tz+t`. If there is `lambda` with

```
g T = lambda g
(g t) + lambda*c = c
```

then the equality hyperplane is preserved. Its complement is preserved
provided `lambda != 0`. Constant guards are trivially invariant. After the
check, `jump_invariant(z, symbol, N)` reuses VLD-002B's binary affine
composition, costing `O(log N)` matrix compositions instead of `N` steps.
A failing invariant refuses the jump; the general switched process is not
claimed to admit logarithmic fast-forward.

## 7. Reproduction

```bash
cd virtual_ground_interpreter
python -m unittest tests.test_guarded_reduction -v
python -m examples.guarded_reduction_demo
python -m unittest discover -s tests -p 'test_*.py' -v
```

Demo: `2^128` possible states reduce to a four-state guarded quotient;
16 certified transition receipts; an upgraded observer asks for **one**
new linear source measurement; and an invariant branch jumps across `10^100`
repetitions.

### Test plan and evidence

- Exact observed-output and state commutation for exhaustive small-field
  states and three-input words, plus randomized guarded machines.
- Delayed branch influence, hidden guard elimination, zero observations.
- Rehashed malicious transition and guard edits; illegal branch elision.
- Receipt tamper detection under a separately recomputed content hash.
- Same-dynamics state migration with zero and one new probes, and rejection
  of dynamics changes.
- Huge invariant jumps and rejection of unsafe accelerated branches.

**Open work:** bounded proof-driven reachability for tighter quotients;
nonlinear polynomial predicates; low-dimensional algebraic invariant
synthesis; provenance-bound live probes; self-modifying observer policies;
formal Lean recheck of the guarded commuting-square theorem; E-CPU execution
sessions that permit quotient upgrade at an epoch boundary.