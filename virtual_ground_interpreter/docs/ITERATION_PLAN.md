# Iteration plan — virtual_ground_interpreter

This page turns the package's own `DEVELOPMENT_DIRECTION.md` into an
executable sequence. Each item is a separate, verifiable increment.

## Increment 0.1.0 → 0.1.1: contract hygiene

- Declare the backend protocol used by `Signal8Backend`.
- Add instruction pre/postconditions and read/write sets to the formal spec.
- No semantic change; the goal is to make the current trusted core explicit.

## Increment 0.1.1 → 0.2.0: first-class transition system

- Represent control state, signal store, guards and transitions as a Ground
  object: \(\mathcal T=(Q,V,\Gamma,\Delta,q_0)\).
- Lower that object to the current IR.
- Run the lowered program and a direct transition-system semantics in
  parallel and require identical traces.

## Increment 0.2.0 → 0.3.0: second backend proof point

- Add one small non-8-PSK backend behind the same protocol.
- Require backend-specific law proofs; do not inherit `Z/8Z` assumptions.
- Measure which interpreter facilities are genuinely reusable.

## Increment 0.3.0 → 0.4.0: observation-driven Ground constructor

- Reintroduce predictive-context learning as a constructor:
  observations → predictive distinctions → candidate transition system →
  executable Ground → counterexample refinement.
- Preserve unresolved ambiguities and emit a general finite automaton when a
  group law is not supported.

## Increment 0.4.0 → 0.5.0: adaptive interpretation

- Richer task/intent contracts, observer and operation selection, and cost
  estimation.
- Optimization remains bounded and explicit; no free-form algorithm discovery
  without an evidence boundary.

## Non-goals

- No universal or Turing-complete computation claim.
- No physical analog hardware claim.
- No silent decoding inside the data plane.
- No loss of indeterminate as a first-class outcome.
