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

The active package now has an experimental observer-relative quotient module. Its observer contract explicitly selects the action probes and output channels. A recursive predictive signature creates exact quotients by increasing horizon; unknown or ambiguous selected transitions prevent exact quotient construction rather than being guessed. A separate three-valued partial refinement now compares state pairs as equivalent, distinguishable with a known action witness, or unresolved when evidence is incomplete. Structured blockers distinguish missing edges, ambiguous edges, and known transitions that reach unresolved successor pairs. This avoids forcing a partial predictive Ground into a total partition. The runnable `examples/run_partial_predictive_relations.py` fixture emits shortest witnesses and structured blockers for both Build 24 and an incomplete two-state Ground.

The Build 24 delayed-six fixture supplies a sharp temporal control: the full action profile splits q0/q1 at horizon five with the retained witness HOLD × 4 followed by PROBE_A, while a profile that removes PROBE_A leaves the q0/q5 output distinction invisible. The partial relation is checked against the exact quotient on this complete fixture and separately on incomplete/ambiguous Grounds. Additional tests use a cyclic recurrence (channel projection) and a many-to-one automaton (non-bijective transition). The module also checks quotient projections and adjacent-layer transition/output maps.

The paired behavioral distance is parameterized by observer, action distribution, horizon, discount, and an output metric. This is a candidate family of semantic-distance profiles, not one universal scalar. These artifacts are present in the research branch; the tests must be executed before reporting them as passed.

## Active attention and observation planning

The new finite attention planner separates local probe valuation from set-level planning. It minimizes unresolved predictive-state pairs under an additive candidate-cost budget. The delayed-six control demonstrates a useful single probe; a second control demonstrates complementary action/channel observations for which greedy marginal gain returns no choice while exhaustive lookahead finds a valid pair.

This is evidence against assuming a globally adequate greedy attention policy. The next research target is bounded lookahead or beam search with an anytime bound, followed by an observation-driven Ground update. The present score is deterministic; calibrated probabilistic information gain is a separate experiment.

## Joint navigation across perception and predictive spaces

The active-attention planner now has a bounded beam-search extension. A node pairs an observer configuration (selected action probes and channels) with the predictive quotient that configuration induces. The search expands zero-marginal-gain capabilities, retains distinct observer configurations even when their current quotient scores match, and records the route and beam pruning decisions. The complementary fixture supplies a two-step route from an unresolved pair to a separating quotient.

This supports a more useful architecture than a single search over world states: the system can search over how to perceive, while measuring what each perception configuration makes distinguishable. The current candidate pool remains caller supplied. Generating probes from counterexamples is the next research direction.

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


## Counterexample-led inquiry without closing the world

A breadth-first inquiry now examines each pair collapsed by the current observer. It searches the full declared action/channel schema for a shortest distinguishing sequence, and reports whether resolution is blocked by omitted perception, insufficient horizon, or missing/ambiguous evidence.

This is intentionally narrower than a generator that invents new actions, sensors, transformations, or states. Such a generator would already require a vocabulary and semantics for its proposals, and could reproduce the observer's blind spots. The report instead preserves an explicit open boundary outside the declared Ground: it says what the model has not represented without pretending to enumerate that remainder.

This tests a methodological requirement: mathematical formalization should make a model's scope and blind spots inspectable, not silently redefine the invariant space as the model's current representation. A finite Ground can be complete relative to its own schema while remaining radically incomplete as an account of the system being studied.

**Next falsification target:** connect witness prescriptions to an actual acquisition interface only when a concrete sensor, emulator, or host action exists. Verify acquired evidence independently before constructing a new Ground version. Never convert a proposed experiment into an observation.


## Encounter memory and associative hypothesis history

The new experimental encounter layer records observations before requiring an interpretation. Immutable encounter envelopes retain payload, provenance, context, and a canonical fingerprint. Cross-encounter associations are stored as explicit hypotheses with rationale, experiment, and falsifier; append-only assessments retain support, contradiction, and inconclusive outcomes.

This design is intentionally not a semantic-similarity engine. Automatically pairing every encounter or ranking all weak connections by one curiosity score would introduce a new observer ontology and may reward noise. Instead, it supplies a durable substrate to which human or machine explorers can contribute hypotheses from directed and open-ended exploration.

A supporting or contradicting assessment must cite at least one new encounter beyond the original hypothesis basis. Assessments remain history, not proof. No association automatically mutates the predictive Ground.

**Next experiment:** connect an actual encounter source—such as a repository observation, an emulator trace, or a sensor feed—to the ledger through a source-specific adapter. Retain the original artifact and digest, then evaluate whether associations generated from independently collected encounters yield reproducible experiments. Measure useful discoveries and false leads separately; do not equate surprise with learning progress.


## Active intention, perception, and addressable channels

The next experiment separates observation from communication. A sensor can expose an incoming stream without accepting commands; an addressable source can accept a request and return a correlated response. A shared protocol identifier describes the message framing language, while the observation, request, and response schemas describe the available directions independently.

The first reference adapter queries the VGI's own finite predictive Ground using its declared state/action vocabulary. It demonstrates a limited form of model-internal dialogue: a request enters in the model's query language and a reply returns in the same protocol framing. Known, unknown, and ambiguous transition states are preserved rather than collapsed into a guessed answer. This is not a physical sensor connection.

The architecture now has a possible interaction cycle:

    active intention -> request proposal -> authorized adapter exchange
      -> correlated reply -> encounter -> association -> experiment.

The proposal is not the observation. The existence of an observation channel does not grant write authority. The received response is new evidence about the addressed source, but its interpretation and generalization remain separate tasks.

**Next falsification target:** connect a real, authorized source adapter and test whether requests framed in its native protocol produce stable, reproducible replies. Record transport success, response admission, provenance, and semantic validation separately. Do not infer duplex capability from a read-only sensor or from matching formats alone.


## E-CPU-inspired evidence separation

This VGI increment adapts several E-CPU patterns without coupling VGI to the MailCPU runtime: EvidenceLink-style transport-frame identity, policy-relative source consensus, explicit event finalization, and finite witness certificates from structural reconstruction.

The evidence layer records what arrived, binds each normalized transition claim to its Encounter and adapter-supplied transport-frame receipt, and retains source disagreement/unknown/ambiguous reports. A receipt must match the exact channel message and payload digest, but is not itself a cryptographic source authentication. Explicit policy finalization is required before a transition enters a Ground. The resulting Ground may remain partial.

A separate GroundReconstructionVerifier checks the complete Ground against VGI's compiled execution path over a finite witness corpus. Its certificate describes only those exact Ground/context fingerprints and action sequences. It does not make the Ground a complete description of the outside system.

This gives the VGI pipeline distinct evidence strata: **observed → policy-admitted → replay-verified**. Do not collapse them into one confidence score or let the reconstruction certificate authenticate source observations.

**Next empirical step:** add a real source adapter and carry its actual receive sequence, source identity, original artifact digest, and context through this pipeline. Compare retransmission, independent source agreement, disagreement, and compiled replay separately.


## Signal8 self-observation and execution-derived evidence

The Signal8 runtime already emits an auditable `ExecutionEvent` per successful
instruction. `Signal8ExecutionAdapter` captures that real runtime path into
VGI's existing observation/evidence structures. It fingerprints before/after
runtime configurations, preserves the raw event (including signal-valued
writes and branch uncertainty), and binds each observation to an Encounter
and frame receipt.

This creates an executable bridge from operation to observation without
confusing the machine's own report with independent validation. Successful
steps yield concrete, run-context-scoped transition claims; runtime faults
remain generic observations; a step limit remains an incomplete capture.
No policy is finalized and no Ground is mutated.

**Next experiment:** compare repeated runs under identical and deliberately
altered initial memory, program, and Ground contexts. Determine which
runtime-state identifiers remain invariant, which instruction transitions
recur, and which observations are sensitive to observer profile or branch
uncertainty. Then examine how independent replay or a second implementation
could corroborate (or contradict) the machine's self-reported trace. Do not
treat repetition by one source as independent evidence.


## Execution orbits and time-addressable predictive paths

The experimental orbit layer connects captured machine execution to a transition Ground without treating capture as automatic admission. It adapts the E-CPU observed-orbit, observer-relative navigation, and typed temporal-coordinate patterns, but keeps VGI's runtime independent. Independently reference-matched frames are retained with source Encounter and receipt identity. A semantic-effect projection removes per-occurrence step index from categorical event outputs while leaving the exact raw event and digest in the trace. This lets repeated operations become comparable without rewriting evidence.

Evidence finalization remains policy-gated. The resulting Ground may be partial. A fixed state-to-action policy then induces a path. Only known single-valued edges are traversed. If a state repeats, the finite prefix and closed cycle are replay-checked, and later logical-time coordinates can be reduced modulo the cycle period.

This is a specific finite result, not a general theorem that every system has a cyclic orbit. It does not claim physical quantum superposition, retroactive execution of the past, or physical-time travel. Unknown and ambiguous transitions remain unresolved; logical ticks are not elapsed seconds.

**Next experiment:** extend orbit navigation to observer-relative target predicates and behavioral-equivalence classes. A target may describe a meaning or observable condition rather than a raw state digest, while the result preserves multiple matches, observer scope, and unresolved predicate outcomes. Any inverse lookup must remain bounded to a certified orbit unless a separate preimage proof is provided.

## Certified modular-affine fast-forward

The first algebraic fast-forward path is now implemented as a certificate over
one replay-checked, closed, fixed-policy orbit. A caller supplies a
modular-affine map and an injective state-vector encoding. The implementation
checks every retained edge before powering the homogeneous matrix in
logarithmic time. The transform, encoding, orbit, Ground, policy, and logical
clock are fingerprint-bound.

This is an orbit-restricted generator result, not a claim that the full Ground
or external system is affine. Composite moduli and non-invertible matrices
are supported for forward navigation; unknown or ambiguous edges remain a
hard stop.

**Next experiment:** state-target navigation over observer-relative predicates
and behavioral-equivalence classes, connecting the partial predictive
relations to the orbit layer. A target may describe an observable condition
rather than a raw state digest, while preserving multiple matches, observer
scope, and unresolved outcomes. Inverse lookup must remain bounded to a
certified orbit unless a separate preimage proof is provided.

## Proof-search dogfooding and formal-methods interface

The finite proof-shaped experiments now live in
[PROOF_SEARCH_DOGFOOD.md](PROOF_SEARCH_DOGFOOD.md), with a runnable package
example. They show that VGI can compare future observable behavior of
Boolean-cube vertices, partial CNF assignments, and partial clique
constructions, while preserving explicit blockers for missing edges.

The architectural gap is now clearer: proof states often create multiple
jointly required subgoals, which need AND/OR hyper-transitions rather than
the current one-target deterministic edge or ambiguous alternative outcomes.
In addition, active attention still relies on complete contextual quotients
and cannot yet rank missing state/action cells directly. The strongest next
build is a proof-state adapter plus partial-aware active attention, with a
trusted Lean/kernel result retained as separate evidence.

## Sparse attention and ProofGround navigation

A new architectural increment adds a sparse partial-refinement interface,
cell-specific counterfactual attention, exact rational/polynomial observables,
and an AND/OR ProofGround adapter.

The sparse interface eagerly builds only proven-equivalence classes and
computes distinguishability witnesses or uncertainty blockers lazily for
requested pairs. Its construction is expected \(O(HSA)\); requesting every
pair still costs quadratic work. The attention scorer changes one hypothetical
cell at a time, and reports exact expected value only when the caller supplies
an exact scenario distribution. Otherwise it reports scenario bounds.

ProofGround represents tactic applications as hyperedges: all child
obligations on one edge are jointly required, while different edges are
alternative routes. Scope-sensitive identity includes the local context,
assumptions, metavariables and environment fingerprints. Raw kernel claims
are retained as untrusted data; an external kernel receipt is required for
accepted/rejected status, and the upstream checker remains a separate trust
boundary.

Exact rational and polynomial observables are stored outside the Signal8
categorical channel, preserving exact mathematical quantities without
pretending Signal8 can carry them losslessly.

**Next work:** connect a real Lean trace exporter and authenticated kernel
receipt verifier, then add a proof-obligation scheduler whose probe selection
uses sparse relations and partial-aware attention.
