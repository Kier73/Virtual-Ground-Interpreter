# Iteration plan — virtual_ground_interpreter

## Completed in 0.2.0: first-class predictive transition contract

- Add GroundTransitionSystem with explicit known, unknown, and ambiguous state/action evidence.
- Import the Build 24 VG-PredictiveMealy-1 specification without hidden-state labels.
- Compile complete finite grounds to the existing Signal8 IR using guarded dispatch and persistent memory.
- Differentially compare direct and compiled semantic state/output traces.
- Preserve unknown and ambiguous edges by refusing to compile unresolved grounds.
- Make terminal symbol observation fail closed when its phase uncertainty spans multiple symbol regions.

Evidence remains finite and bounded. The delayed-six model is an integration fixture, not a general induction result newly produced by the active package.

## Next increments

### 0.2.0 → 0.3.0: typed backend and instruction contracts

- Extract an explicit backend protocol from the current Signal8Backend assumptions.
- Add instruction preconditions, postconditions, read/write sets, reversibility classification, and evidence links.
- Keep direct transition-system semantics independent from the IR implementation.

### 0.3.0 → 0.4.0: second backend proof point

- Add one small non-8-PSK backend behind the same protocol.
- Require backend-specific law tests and uncertainty semantics.
- Measure which interpreter facilities are reusable without importing Signal8 assumptions.

### 0.4.0 → 0.5.0: observation-driven Ground construction

- Connect Build 26-style incremental partial grounds to GroundTransitionSystem.
- Preserve missing and conflicting evidence explicitly.
- Refine only through new observations, longer distinguishing histories, or retained counterexamples.
- Emit a general finite transition system when no supported group or phase law is found.

### 0.5.0 → 0.6.0: task-conditioned synthesis and navigation

- Extend typed task contracts with output invariants, input domains, resource budgets, latency constraints, and ambiguity policy.
- Search only within a declared DSL/program grammar.
- Compare direct execution, recurrence, procedural regeneration, and compiled IR using whole-path cost accounting.
- Require replayable certificates or differential reference checks for accepted programs.

## Non-goals

- No universal or Turing-complete computation claim.
- No physical analog hardware claim.
- No silent decoding inside the data plane or terminal observation.
- No loss of unknown/ambiguous as first-class outcomes.
- No performance or energy advantage claim without a complete workload baseline.


## Relational-atlas research overlay

An experimental increment now adds:
- observer contexts that choose available action probes and visible output channels;
- exact horizon-indexed predictive partitions with monotone refinement and finite stabilization;
- explicit maps from finer to coarser quotients and adjacent-layer transition/output checks;
- a behavioral pseudometric profile parameterized by observer, action distribution, horizon, discount, and output metric;
- three finite probes: delayed-six prediction, cyclic recurrence, and a non-bijective automaton.

This is a research overlay, not a replacement for the typed-backend sequence. Once its test suite is executed, the next curiosity is active attention allocation: select a probe by expected ambiguity reduction per unit cost, then compare against exhaustive schedules on finite controls.


## Active-attention planning overlay

A new experimental module ranks candidate action probes and output channels by unresolved pair reduction per declared cost. It provides:
- a greedy marginal-gain planner;
- an exhaustive subset baseline for at most 16 candidates by default;
- explicit tests for a high-value single probe and a complementary-probe counterexample.

The complementary fixture demonstrates that local information gain is not generally sufficient: two candidates can each have zero marginal value yet become informative together. The next iteration should be bounded lookahead or beam search that retains such interactions, followed by active observation and Ground refinement. Probabilistic expected information gain is deferred until explicit priors and calibrated likelihoods exist.
