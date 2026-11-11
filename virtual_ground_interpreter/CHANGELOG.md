## Unreleased — independent Signal8 semantic reference and invariant-space experiment

- Add a reference interpreter that does not execute through Signal8Backend, SignalStateMachine, or Program; compare all supported instruction events, writes, branch evidence, failure categories, and final state against retained traces.
- Separate ideal Z/8Z symbols from continuous residual phase and propagated error bounds; return unsupported when input uncertainty does not justify one symbol.
- Exhaust all 64 C8 operand pairs for both ADD and SUB under all 16 mixed-observer pairings (2,048 arithmetic operations), checking the decoded outputs against modular arithmetic.
- Add controls for exact same-observer REFRAME identity, ambiguous branch traps, strict separation below pi/4, the observer-dependent equality boundary at pi/4, noisy observer round trips, and a deliberately corrupted runtime arithmetic result.
- Document the distinction between representation, algebra, control, prediction, behavior, evidence, and resource invariants.
- Re-examine Builds 25–31 and define a provenance-preserving route to renew online Ground induction, competing explanations, raw event/motif discovery, adaptive observer selection, and signal algebra.
- The focused tests and repository-wide gates have not been executed in this environment; no passing status is claimed.

## Unreleased — Signal8 execution observations

- Add a step-boundary adapter that captures actual SignalStateMachine execution as observation-only channel messages.
- Bind each successful instruction event to before/after runtime-configuration identifiers, exact program/Ground fingerprints, a retained Encounter, and a payload-bound frame receipt.
- Preserve raw SignalValue writes and branch measurements without semantic integer decoding.
- Retain runtime faults as generic observations, not successful transition claims; label bounded captures as incomplete when HALT is not reached.
- Keep policy finalization and Ground mutation outside the adapter. A machine's self-observation is not independent source corroboration.
- Add focused adapter tests, an example runner, and execution-trace provenance documentation. Full repository gates must still be run in the repository environment.

## Unreleased — evidence admission and finite reconstruction

- Add transition evidence linked to retained inbound channel messages, Encounters, and adapter-supplied transport-frame receipts bound to exact payload digests.
- Add explicit source/quorum decisions and immutable event finalization before transition admission.
- Build partial Grounds from authorized transitions only; keep unknown, ambiguous, pending, refused, and conflicting events unresolved.
- Add finite compiled-replay certificates bound to exact Ground/context fingerprints and witness action sequences.
- Add 15 focused tests, an example runner, and architecture/formal documentation. The committed evidence tests and full repository quality gates have not been run in this environment.

## Unreleased — duplex channel contracts

- Add explicit observation, request, and reply schemas under a shared protocol identifier.
- Keep observation-only sensors distinct from addressable request/reply channels.
- Add a correlated append-only channel ledger and conversion of inbound messages into encounters.
- Add a predictive-Ground query adapter that reports known, unknown, and ambiguous transitions without completing missing evidence.
- Add ten focused tests and a model-internal request/reply example. The committed channel test suite and full repository gates have not been executed in this environment.

## Unreleased — encounter memory and associative hypotheses

- Add immutable, interpretation-neutral encounter records with provenance, context, canonical fingerprints, and append-only ledger snapshots.
- Add cross-encounter hypotheses requiring a rationale, experiment, and falsifier.
- Add append-only supporting, contradicting, and inconclusive assessments; support/contradiction requires evidence beyond the original hypothesis basis.
- Keep encounter memory and associations separate from predictive Ground construction; no automatic semantic promotion or curiosity scalar is introduced.
- Add focused tests, an example runner, and the encounter/association architecture note. Core ledger behavior was exercised in a small isolated local harness; the committed test file and full repository gates have not been run.

## Unreleased — counterexample-led inquiry and open perception boundary

- Add shortest, evidence-backed distinguishing-experiment search for pairs collapsed by the current observer.
- Report omitted declared actions/channels, temporal witnesses, unknown or ambiguous transition blockers, and search bounds.
- Preserve an explicit open-world boundary beyond the declared finite Ground; do not synthesize undeclared capabilities.
- Add tests and an example runner. Tests have not been executed in this environment; no passing totals are claimed.

## Unreleased — joint perception-navigation

- Add bounded beam search over observer configurations and their induced predictive quotients.
- Retain zero-immediate-gain observer configurations to discover complementary attention routes.
- Record the perception-to-prediction route and every visited configuration's beam-retention decision.
- Add comparative report runner and tests for complementary-probe and delayed-six controls.
- New tests have not been executed in this environment; no passing totals are claimed.

## Unreleased — cost-aware active attention

- Add candidates for action probes and output channels with explicit relative costs.
- Add unresolved-pair reduction and per-cost probe ranking.
- Add greedy marginal-gain and bounded exhaustive subset planners.
- Add a complementary-observation control demonstrating why greedy attention can miss jointly informative capabilities.
- Add tests and a report runner for delayed-six and complementary-probe cases.
- The new test suite has not been executed in this environment; no passing totals are claimed.

## Unreleased — observer-relative relational atlas research

- Add explicit observer contexts over action probes and visible output channels.
- Add exact horizon-indexed predictive quotient refinement, finer-to-coarser maps, and adjacent-layer transition/output checks.
- Add observer- and action-distribution-relative behavioral pseudometric profiles.
- Add finite controls for delayed prediction, cyclic recurrence, and a non-bijective automaton.
- This is an experimental research increment. The new tests have not been executed in this environment; no passing status is claimed.

# Changelog

## 0.2.0 — predictive transition-system integration

- Added first-class predictive transition grounds with known, unknown, and ambiguous edge states, support counts, and evidence references.
- Added an importer for the archived Build 24 VG-PredictiveMealy-1 format.
- Added a bounded compiler from complete finite grounds to the existing Signal8 IR, with runtime action slots and persistent state updates.
- Added direct-versus-compiled semantic trace verification and a delayed-six regression fixture.
- Unknown or ambiguous grounds are rejected by the compiler rather than completed with guessed transitions.
- Terminal symbol observation now refuses ambiguous decoding when phase uncertainty overlaps multiple 8-PSK decision regions.
- Added development continuity and research frontier documents. No universal-space, general synthesis, physical hardware, or speed/energy claim is made.

Verification note: the new test suite and example are included in this increment. They must be run in the repository environment before treating this release as validated.


## 0.1.0 — initial interpreter baseline

- Bounded signal-state interpreter over finite `Z/8Z` in four 8-PSK observer coordinates.
- Typed task-expression compiler lowering a constrained DSL to validated control-flow IR.
- Persistent signal-valued memory, registers, instruction trace, checkpoints, reset and journal-based undo.
- Three-valued equality/identity guards with atomic trap behavior on indeterminate conditions.
- Exhaustive finite verification over the declared Ground.

Verification baseline:

- 42 unit tests pass.
- `vgi verify` reports 4,772 finite cases with zero errors.
- Ground: `virtual-ground.signal-state.z8`
- Fingerprint: `4ba599c21ec7e446572dad61b2a66ecb9c0844fd3dee406e4d947e04db56c43b`


## Unreleased — Signal8 capture replay material and context identity

- Retain complete before/after runtime configurations with each successful instruction observation.
- Include program/Ground definitions and initial/final configurations for independent inspection and replay.
- Keep run IDs in provenance but exclude them from structural context digests, allowing identical initial contexts to be compared.
- Scope in-process transport identity by run to prevent frame-sequence collisions across captures.
- Expose runtime-configuration ID recomputation for retained snapshots.
- Updated focused tests and full repository gates have not been executed here.


## Unreleased — harden Signal8 trace replay and consolidate the adapter API

- Enforce contiguous frame and step indices, a continuous pre/post state-digest chain, and closure at the retained final-state digest.
- Require one channel message and one Encounter per execution frame; require one transport session per trace and keep failed attempts final.
- Compare frame sequence as part of replay verification while continuing to ignore transport IDs and capture timestamps.
- Make `vgi.execution.Signal8ExecutionAdapter` the canonical package-level API; expose the previous in-progress-machine adapter under the explicit `LegacySignal8ExecutionAdapter` name.
- Update the runnable example, legacy tests, and documentation so the two APIs cannot be confused.
- The focused test suite and repository-wide gates have not been executed in this environment.
