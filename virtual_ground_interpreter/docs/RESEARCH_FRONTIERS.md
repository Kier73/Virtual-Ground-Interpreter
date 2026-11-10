# Research Frontiers — Hypotheses, Boundaries, and Experiments

This document keeps the larger ambitions connected to the active VGI implementation without treating them as established results. Each frontier has a bounded claim, a falsification route, and an engineering sequence.

## 1. Universal invariant space

There may be a useful family of context-indexed representations for a broad class of describable systems. Each representation preserves the distinctions demanded by its declared contexts; new contexts refine the quotient; compatible maps relate representations without requiring identical coordinates.

For a context family \(A\):

\[
x\sim_A y\iff \forall c\in A,\;o_c(x)=o_c(y).
\]

This defines an exact observational quotient for deterministic observations. It does not establish a universal manifold, common topology, or physical identity.

**Experiment:** choose three structurally different finite grounds: a cyclic recurrence, a non-bijective automaton, and a small signal-state program. For each, construct two observers with different observable quotients. Search for maps preserving selected transition and output relations. Hold out contexts and action sequences when fitting candidate maps.

Report which relations commute with the maps, which distinctions each observer collapses, whether refinement is monotone, code size and reconstruction cost, counterexamples, and the first context that breaks each map. A trivial one-to-one relabelling is not a meaningful success. A useful result must preserve nontrivial structure and improve organization, prediction, or execution.



### Finite relational-atlas implementation

The active package now has an experimental observer-relative quotient module. Its observer contract explicitly selects the action probes and output channels. A recursive predictive signature creates a sequence of quotients by increasing horizon; unknown or ambiguous selected transitions stop construction rather than being guessed.

The Build 24 delayed-six fixture supplies a sharp temporal control: the full action profile is expected to split states in order across horizons, while removing PROBE_A leaves its delayed output distinction invisible. Additional tests use a cyclic recurrence (channel projection) and a many-to-one automaton (non-bijective transition). The module also checks quotient projections and adjacent-layer transition/output maps.

The paired behavioral distance is parameterized by observer, action distribution, horizon, discount, and an output metric. This is a candidate family of semantic-distance profiles, not one universal scalar. These artifacts are present in the research branch; the tests must be executed before reporting them as passed.

## Active attention and observation planning

The new finite attention planner separates local probe valuation from set-level planning. It minimizes unresolved predictive-state pairs under an additive candidate-cost budget. The delayed-six control demonstrates a useful single probe; a second control demonstrates complementary action/channel observations for which greedy marginal gain returns no choice while exhaustive lookahead finds a valid pair.

This is evidence against assuming a globally adequate greedy attention policy. The next research target is bounded lookahead or beam search with an anytime bound, followed by an observation-driven Ground update. The present score is deterministic; calibrated probabilistic information gain is a separate experiment.

## 2. Universal semantic distance

There may be reusable distance profiles, but a single scalar distance is unlikely to be task-independent. Description edit cost, behavioral discrepancy, observation discrepancy, transformation cost, time, and resource cost answer different questions.

Retain a profile:

\[
\mathbf D(x,y)=(d_{\mathrm{obs}},d_{\mathrm{beh}},d_{\mathrm{path}},
d_{\mathrm{desc}},d_{\mathrm{resource}},\ldots).
\]

A task may define a calibrated scalarization, but its weights and assumptions must be part of the task contract.

**Experiment:** build a small corpus of equivalent and non-equivalent implementations of the same finite tasks. Measure output-trace disagreement over a declared conformance horizon, shortest valid transformation path, program edit/description cost, execution and memory costs, and observer-specific measurement discrepancy.

Test whether one scalar ranking transfers across task families. A ranking reversal is a useful result: it demonstrates that the distance is task-conditional. Do not optimize weights on held-out tasks.

## 3. General task-to-program synthesis

A constrained synthesis loop is feasible when task properties, input domains, permitted operations, resource bounds, and verification conditions are explicit.

The active expression compiler proves only structural lowering for a small typed expression tree. The finite transition compiler proves a second bounded lowering route. Neither is unrestricted natural-language synthesis.

**Experiment:** extend task contracts in stages: target output and invariants; typed input/output domains; action/operation catalogue with preconditions and effects; observation and ambiguity policy; time, memory, latency, and risk budgets.

Search only within a declared DSL or bounded program grammar. Every candidate must carry a proof obligation or independently replayable certificate. Counterexamples refine the task model or grammar. Compare against hand-written reference programs and direct execution.

## 4. Physical signal computation

A signal representation can participate directly in an operation when the encoded domain has a verified algebra and the physical channel supports the required transformation with calibrated error bounds.

The current Signal8 backend operates on pilot-calibrated numerical phasors. Builds 30–31 establish finite numerical algebra; they do not establish a physical analog computer.

**Experiment:** use a controlled SDR, FPGA, or laboratory baseband path to implement one operation with an independent digital reference. Transmit known operands and pilots; perform the intended physical or hardware-native transformation before terminal symbol decoding; measure symbol/phase error, calibration drift, throughput, and power; inject channel changes, timing offsets, noise, and pilot mismatch; verify every accepted result against the reference trace.

Keep numerical simulation and hardware results in separate evidence classes. A decoded answer that agrees after conventional software has already performed the arithmetic does not count as signal computation.

## 5. Speed and energy advantage

Generative grounds and alternative substrates may reduce total cost for some workloads, particularly when setup can be amortized or when the substrate provides useful native transformations. No general advantage has been demonstrated. The current recorded Python signal-domain path was 1.49× slower than decode/compute/re-encode in its benchmark.

**Experiment:** measure the entire route:

\[
C_{\mathrm{total}}=
C_{\mathrm{observe}}+
C_{\mathrm{learn}}+
C_{\mathrm{compile}}+
C_{\mathrm{navigate}}+
C_{\mathrm{transport}}+
C_{\mathrm{execute}}+
C_{\mathrm{decode}}+
C_{\mathrm{verify}}.
\]

For energy, measure the system boundary, including transmission, idle time, retries, calibration and control electronics. Compare the same workload, correctness target, reliability, output form and hardware class. Report break-even reuse count when discovery/compilation has an upfront cost. Never infer an energy advantage from fewer arithmetic instructions or from a compact abstract description.

## 6. Shared research discipline

- Observation contracts precede interpretation.
- Missing data is not zero.
- Unknown and ambiguous are different.
- Equivalence is always relative to declared contexts.
- Candidate laws are not promoted beyond their evidence horizon.
- Algebraic compression is claimed only when generated behavior is verified.
- Distance profiles remain separate until calibration justifies a task-specific scalar.
- Failed predictions remain as counterexamples.
- Hardware and simulation evidence are labelled separately.
- A performance claim includes the complete path.

The desired outcome is not a universal vocabulary imposed on every domain. It is a small, reusable set of semantic contracts that lets different domains retain their own mathematics while still being compared and composed where structure-preserving evidence exists.
