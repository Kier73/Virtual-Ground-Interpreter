# VLD-002 — Certified finite-state reduction

**Capability.** Construct the smallest reachable deterministic finite-state Ground that preserves a chosen set of observable transition outputs for **every finite input sequence**. Discovery emits a quotient machine and portable mapping witness; independent admission checks transitions, reachability, and minimality without calling the discovery algorithm.

## Use

```python
from vgi.certified_reduction import (
    FiniteGround, discover_reduction, verify_reduction,
)

source = FiniteGround.from_dict(machine_json)
reduced, witness = discover_reduction(source, ("observable_channel",))
receipt = verify_reduction(source, reduced, witness)
assert receipt["status"] == "VERIFIED"
# Persist reduced.to_dict(), witness.to_dict(), and pinned source.to_dict().
```

`FiniteGround` is a **total deterministic Mealy machine**: a finite state set `S`, input alphabet `A`, transition `δ : S × A → S`, and typed string-valued output channels `λ : S × A → Channel → String`. A Ground specifies its initial state. Artifacts use sorted, unique state/input identifiers, canonical edge order, and SHA-256 content identities. The initial pilot is bounded to 128 states and 32 input symbols.

The observation contract is a fixed subset `O` of output channels. The projection `π_O` discards every channel not in `O`.

## Mathematical obligation

Discovery computes the reachable states `Reach(s₀)` and an observation-relative equivalence `~_O`. Two states are equivalent when **every future input word** produces the same projected output sequence. The algorithm starts with one state block and repeatedly refines by the signatures

```
signature(s) = ((π_O(λ(s,a)), class(δ(s,a)))) for each a ∈ A
```

until the partition stabilizes. The quotient state represents a block; one representative supplies its outgoing transitions.

The witness is a map `h : Reach(s₀) → Q` and source/target hashes. **Admission**, run independently of discovery, checks for each reachable source state and every input:

```
h(s₀) = q₀
λ_Q(h(s), a) = π_O(λ_S(s, a))
h(δ_S(s, a)) = δ_Q(h(s), a)
```

These equations imply output-trace equivalence for **all finite input words** by induction on word length, without executing all words. The checker also ensures the witness covers exactly reachable source states, all target states are reachable and represented, and the input alphabet/observer contract is unchanged. Minimality is validated separately by an independent least fixed point of distinguishable unordered target-state pairs: a pair is distinguished if some input yields different output or leads to an already distinguished pair. Every distinct target-state pair must be distinguishable.

This is a finite exact algorithmic check of a specific Ground model, **not** a Lean theorem, a certificate for an arbitrary Turing machine, a general multi-step simulation, or a speedup guarantee. It deliberately targets the observation-relative aspect of certified state reduction, complementing the stronger and more heterogeneous constructions in [DeepMind's Cryptids](https://github.com/google-deepmind/cryptids).

## Reproducible experiment

The test model contains two independently incremented cyclic counters, modulo 4 and modulo 3. Inputs `A` and `B` increment the corresponding counter; every action reports both counter phases. All 12 states are reachable.

| Required observations | Original states | Admitted minimal states | Reduction |
|---|---:|---:|---:|
| None | 12 | 1 | 91.7% |
| Counter A | 12 | 4 | 66.7% |
| Counter B | 12 | 3 | 75.0% |
| Both counters | 12 | 12 | 0% |

Every certificate checks all **24 source transitions**. In addition to the proof-carrying transition check, tests enumerate every input word of length 0–5 (63 words per observation contract), search 336 randomized machine/scope combinations, check delayed distinguishability, eliminate unreachable states and reject corrupted outputs, successors, maps, digests, observation scopes, and behaviorally correct but nonminimal quotients. Counts describe the *tests included*, not an extrapolated performance result.

From the repository root:

```bash
cd virtual_ground_interpreter
python -m unittest discover -s tests -p 'test_certified_reduction.py' -v
```

## Next experiment — crossing the state-space boundary

1. **Concrete E-CPU adapter.** Export a bounded `E-CPU` interpreter transition subgraph as a finite Mealy Ground. Explicitly encode queue state and `SEND`/`WAIT` effects in the observable contract; never assume a pure register snapshot suffices.
2. **Symbolic state relation.** Replace the finite enumerated map `h` with an independently checkable relation on parameterized state families (counters, queues, stacks, memory windows), with an inductive invariant and a multi-step simulation clause.
3. **Observation-cost frontier.** Given an intention as required channels, compare retained states, transition cost, receipt size and verification complexity. Search for **new** observation bases that preserve the intention while shrinking the quotient.
4. **Independent Lean recheck.** Mirror the finite-state commuting-square theorem in Lean 4 and emit a separate kernel verification receipt tied to the exact machine/certificate identities.

The research question is now operational: *which distinctions in a computational state are necessary for the observer's future, rather than merely present in the original representation?*
