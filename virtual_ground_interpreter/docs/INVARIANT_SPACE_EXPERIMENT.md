# Invariant-space experiment: independent semantics and observer-relative meaning

## Status

This experiment adds an independent finite semantic reference for captured Signal8 executions. It is a research control, not a second production runtime, not a source authenticator, and not a proof about physical signal hardware.

Run from this directory:

    python -m unittest discover -s tests -p 'test_reference.py' -v
    python -m unittest discover -s tests -p 'test_execution.py' -v
    python -m unittest discover -s tests -v
    python -m vgi verify

The tests and repository gates have been authored but have not been executed in the repository environment for this change. No passing result is claimed.

## 1. The question

The recent development sequence created three distinct views of one execution:

1. **Operational reality inside the runtime:** the actual instructions, register/memory changes, branch decisions, and signal-valued writes.
2. **Retained observation:** ChannelMessages, Encounters, receipts, and the linked pre/post-state chain.
3. **Same-runtime replay:** a second run of the same implementation over the retained Program, initial memory, and Ground.

The third view tests reproducibility, but it can repeat the same semantic defect. This experiment introduces a fourth view:

4. **Independent semantic reference:** a separately written interpreter of the declared finite instruction semantics, compared against the retained trace and final signal state.

The reference does not call Signal8Backend, SignalStateMachine, or Program to execute the semantics. It interprets the instruction descriptions directly over an abstract cyclic symbol and an explicit residual phase.

The primary question is not “does the runtime agree with itself?” It is:

> Does the captured operation preserve the mathematical meaning declared by its Ground, under the exact observer, uncertainty, instruction, and branch contract used for this execution?

## 2. A useful representation of meaning

For ideal Signal8 values, the semantic domain is

\[
K=\mathbb Z/8\mathbb Z.
\]

Observer coordinate \(u\in U(8)=\{1,3,5,7\}\) represents \(k\in K\) by

\[
\chi_u(k)=\exp(2\pi iuk/8).
\]

The runtime stores a phasor, an observer identifier, and a phase-error bound. The independent reference instead carries

\[
\widehat S=(k,u,r,\epsilon),
\]

where:

- \(k\) is the recovered abstract symbol;
- \(u\) is the observer coordinate;
- \(r\) is the signed residual angle relative to the ideal character \(\chi_u(k)\);
- \(\epsilon\) is the declared absolute residual phase bound.

This separates two things that should not be collapsed:

- the discrete meaning represented by the ideal finite group;
- the continuous error introduced by calibration, measurement, or coordinate transport.

The initial symbol is accepted only if the supplied phasor and error bound identify exactly one member of the eight-symbol alphabet. If multiple symbols remain possible, the reference result is unsupported, not a guessed interpretation.

After that ingress boundary, the reference executes the finite algebra:

\[
ADD:\quad
(k_a,u,r_a,\epsilon_a)\oplus(k_b,u,r_b,\epsilon_b)
=
(k_a+k_b\bmod 8,u,
\operatorname{wrap}(r_a+r_b),
\min(\pi,\epsilon_a+\epsilon_b)).
\]

Subtraction replaces the residual sum by a residual difference and the symbol sum by \(k_a-k_b\bmod 8\). Mixed observers are aligned using the Ground's declared coordinate transformation before applying either operation.

The reference then compares its expected event sequence and final abstract state with the captured runtime observations. Floating-point phasors and branch measurements are compared within a small declared numerical tolerance. Runtime state hashes are not treated as semantic proof.

## 3. The important qualification: observer maps are not global isometries

For an ideal character,

\[
R_{u\rightarrow v}(\chi_u(k))=\chi_v(k),
\qquad
R_{u\rightarrow v}(z)=z^m,
\qquad
m=(vu^{-1})\bmod 8.
\]

This is exact on the eight roots of unity. It preserves the finite symbol and the group operation. This is the finite algebraic invariant.

For a non-ideal phasor

\[
z=\chi_u(k)e^{ir},
\]

the same transformation yields

\[
z^m=\chi_v(k)e^{imr}.
\]

The symbol coordinate is transported as intended, but the residual angle is multiplied by the integer representative \(m\). Its uncertainty bound correspondingly expands to \(\min(\pi,m\epsilon)\).

There is a subtle but consequential result. The inverse observer exponent is an inverse modulo eight, not an inverse on the entire unit circle. For example, the \(1\to3\) map and \(3\to1\) map both use exponent 3. Their composition is exponent 9:

\[
R_{3\rightarrow1}(R_{1\rightarrow3}(z))=z^9.
\]

For an ideal eighth root, \(z^9=z\). For an off-grid residual, the residual is multiplied by nine. Thus the round trip preserves the ideal symbol but is not an identity on arbitrary noisy phasors. The error bound expands by the same factor.

This is why an observer change should not be described as a global isometry of the continuous phasor circle. It is an exact finite-group coordinate map with an explicitly propagated local residual.

### Branch predicates are also observer-relative

The current equality branch compares angular distance against a tolerance. The angular metric on the continuous circle is not preserved by every odd-power map.

A sharp finite counterexample is the pair \(0,1\in\mathbb Z/8\mathbb Z\) at tolerance \(\pi/4\):

- observer 1 sees separation \(\pi/4\), so the inclusive tolerance test returns true;
- observer 3 sees separation \(3\pi/4\), so the test returns false.

For ideal, distinct symbols, a tolerance strictly below \(\pi/4\) does separate every pair under all four observers. At the boundary and above, observer changes can change the result. With nonzero uncertainty, a branch can become indeterminate even when the ideal symbol relation is unchanged.

Therefore the invariant contract must include the predicate, observer, tolerance, and uncertainty margin. “Same symbol” and “within angular tolerance” are different claims.

## 4. What the independent verifier checks

The new vgi/reference.py module supports the finite instruction set:

- memory and register operations: LOAD, STORE, MOVE;
- coordinate/algebra operations: REFRAME, ADD, SUB;
- robust control: BRANCH_EQ, BRANCH_IDENTITY, JUMP;
- observable output and termination: EMIT, HALT.

For each attempted instruction it independently predicts:

- the program counter transition;
- the opcode and branch decision;
- branch distance, uncertainty interval, tolerance, and observer;
- every register, memory, and output write;
- the expected failure category for a trapped instruction.

It then checks the retained raw event, frame identity/order, and final snapshot. A runtime operation deliberately replaced by a wrong result should produce a semantic mismatch even though the trace is internally well-formed.

Each report is bound to the exact trace fingerprint, Program fingerprint, and Ground fingerprint, and records the numerical comparison tolerance used. Its own canonical fingerprint makes the comparison result referable without treating the result as a signature or source-authentication proof.

Three outcomes are deliberately distinct:

- match: the independent finite semantics agree within the declared numerical tolerance;
- mismatch: a captured operation, branch, write, failure, or final state disagrees with the reference;
- unsupported: the initial evidence does not justify a unique Signal8 meaning, or the retained contract is outside the reference's scope.

The reference checks finite semantics. It does not authenticate a source, independently validate the physical origin of a phasor, establish external completeness, or prove a universal law.

## 5. The new invariant stack

The project is becoming clearer when its invariants are organized as a stack of contracts rather than collapsed into one score.

| Layer | Invariant question | Evidence that can answer it |
|---|---|---|
| Representation | Does this observation identify a value under its observer and uncertainty? | Calibrated measurement, declared alphabet, unique decoding region |
| Algebra | Does an operation preserve the declared relation? | Exhaustive finite laws, metamorphic tests, independent reference |
| Control | Does the branch predicate preserve the intended decision? | Observer, tolerance, uncertainty margin, branch trace |
| Prediction | Do two contexts remain indistinguishable under selected probes and horizon? | Observer-relative quotient and distinguishing witnesses |
| Behavior | Do two implementations produce corresponding observable traces for the task? | Held-out input sequences, independent semantic comparison |
| Evidence | Is the claim bound to the exact observation, source, context, and admission policy? | Encounter, provenance, frame receipt, policy finalization |
| Resource | Is the preserved behavior worth its end-to-end time, energy, memory, and risk? | Whole-path measurement under matched conditions |

These layers interact, but they are not interchangeable. A perfect hash chain cannot prove an instruction semantically correct. An independent semantic match cannot authenticate who supplied the original signal. A predictive quotient cannot prove physical hidden-state identity. A low behavioral distance cannot establish lower energy.

The invariant space is thus better modeled as a family of task- and context-indexed preservation relations, with explicit maps between representations. The target is not one coordinate system in which every meaning must live. It is a navigable structure of compatible descriptions, each preserving specified distinctions.

## 6. Re-examining Builds 25–31 with the newer architecture

### Builds 25–26: online tracking and partial Ground induction

These builds already established valuable disciplines: non-resettable tracking, asynchronous channel arrival, contradiction quarantine, bounded history, horizon refinement, and explicit known/unknown/ambiguous transitions.

The new Encounter and evidence layers allow a stronger version:
- preserve each raw source event and its local sequence/time metadata;
- retain unmatched and late observations rather than normalizing them into a guessed global clock;
- associate events by explicit action-step/event identity where available;
- keep sensor-clock alignment as a separate, versioned calibration hypothesis;
- derive a partial predictive Ground only from admitted claims;
- replay held-out and retained witnesses against every proposed Ground version.

The next experiment should be a trace-ingestion adapter that converts an existing VGI execution trace into a streaming input source for a partial predictive Ground, then intentionally reorders, duplicates, delays, and contradicts selected observations. It should test the distinction among transport disorder, observer ambiguity, insufficient history, and true model conflict.

### Build 27: competing explanations and discriminating probes

The earlier diagnostic engine kept noise, calibration shift, sensor remapping, insufficient history, hidden predictive factors, stochastic context, new state, and Ground change as competing explanations. That is directly compatible with the modern Encounter/Association architecture.

The upgrade is to bind each explanation to:
- the exact encounters on which it rests;
- an experiment that separates it from its closest competitor;
- a predicted observation for each outcome;
- a declared cost and risk;
- a falsifier and append-only assessment.

The current inquiry module can produce shortest distinguishing sequences inside an already-declared Ground. The next step is to let a retained discrepancy propose candidate probes, but not let the proposal itself become an observation or a new action in the Ground. Newly proposed capabilities need an authorized adapter and a newly declared semantic contract.

### Builds 28–29: motifs and raw event boundaries

These builds offer one of the strongest opportunities for renewed work. Build 28 discovered recurrent ordered motifs from opaque event tokens, retained ambiguous segmentations, used shuffled negative controls, and inferred effects from sparse checkpoints. Build 29 moved down to continuous measurements and proposed observer-relative event boundaries using multiple feature views and thresholds.

Now the full process can be reconstructed with stronger epistemic separation:

1. Retain raw samples and the exact acquisition metadata as source-bound Encounters.
2. Produce multiple independent event-boundary hypotheses (feature view, frame/hop, threshold, and channel fusion).
3. Keep alternative segmentations and ambiguous intervals as hypotheses; do not choose one parse merely because its score is highest.
4. Mine recurrent motifs separately within each segmentation hypothesis.
5. Use trace/action/checkpoint alignment, ablation, and held-out streams to test whether a motif predicts a state effect.
6. Apply order-preserving shuffled controls and controls that preserve local token rates, event lengths, and cross-channel dependencies.
7. Keep a motif as an event regularity until an intervention or independently observed effect supports an operation claim.
8. Only then produce transition-evidence candidates for explicit policy admission.

The key improvement is that the raw waveform, feature description, event boundary, token identity, motif, effect hypothesis, and admitted transition become linked but distinct records. This allows a later discovery to revise segmentation or interpretation without overwriting what was actually measured.

### Build 30: adaptive observer choice

Build 30 chose observer profiles using labelled calibration data and retained near-optimal alternatives. The current quotient and active-attention planners provide a more structural objective than profile-level classification scores alone.

A renewed experiment should select a set of observations by:
- task-relevant predictive distinctions;
- horizon and held-out contexts;
- interaction between actions and channels;
- cost, side-effect risk, latency, and calibration burden;
- robustness of the resulting quotient to held-out contexts and noise.

A profile that wins on labelled calibration may fail when the task changes. The new planner should preserve a set of near-optimal observer configurations and measure how sensitive the choice is to task-contract changes. The complementary-probe counterexample remains a mandatory regression: two capabilities may have zero individual gain and positive joint value.

### Build 31: compositional signal algebra

Build 31's ideal finite group laws have now been connected to a stateful instruction runtime and are being checked by a separate semantic implementation. The next refinement is to separate exact algebraic invariants from approximate channel behavior.

For each operation path, retain a profile such as

\[
\mathcal P=
(\text{symbol relation},
\text{observer path},
\text{residual phase},
\text{error bound},
\text{branch margin},
\text{resource cost}).
\]

Do not compress this into one correctness score. Compare the exact ideal result, the measured phasor, the conservative uncertainty envelope, and the final predicate result separately.

A later physical experiment can replace the simulated ingress/egress with a controlled SDR/FPGA path while preserving the same reference contracts. Simulation and hardware evidence must remain separate.

## 7. A path through the invariant space

The combined architecture suggests a reusable cycle:

\[
\text{Acquire}
\rightarrow
\text{Retain}
\rightarrow
\text{Describe}
\rightarrow
\text{Compare}
\rightarrow
\text{Discriminate}
\rightarrow
\text{Admit}
\rightarrow
\text{Compile}
\rightarrow
\text{Execute}
\rightarrow
\text{Independently check}.
\]

A second loop operates over representations:

\[
\text{Observer}
\rightarrow
\text{Predictive quotient}
\rightarrow
\text{Unresolved distinctions}
\rightarrow
\text{Candidate probe}
\rightarrow
\text{New observation}
\rightarrow
\text{Quotient refinement}.
\]

The loops join only through retained evidence and explicit contracts. A proposed probe is not an observation. An observation is not an admitted transition. An admitted transition is not a universally valid law. A replay match is not independent semantic correctness. A semantic match is not source authentication.

This organization yields a practical meaning for “navigating invariant space”: find transformations between descriptions that preserve the particular relations required by a task, identify the first boundary where preservation fails, and use that counterexample to select the next observation or refinement.

## 8. Next experimental sequence

The present change deliberately implements only the independent Signal8 reference and its observer/uncertainty controls. The most useful follow-on experiments, in order, are:

1. **Trace-to-partial-Ground ingestion:** stream retained execution encounters into the existing partial-ground machinery, injecting reorder, duplication, missing frames and conflicts.
2. **Counterexample-generated probe proposals:** connect replay/reference discrepancies and inquiry witnesses to candidate attention actions; require an authorized source before acquisition.
3. **Multi-hypothesis raw segmentation:** revisit Builds 28–29 using retained raw data, alternative segmentations, order-preserving null controls, and independent checkpoint/ablation evidence.
4. **Observer-set robustness:** revisit Build 30 by comparing near-optimal sets across held-out task contracts, rather than selecting a single profile from one labelled calibration split.
5. **Cross-substrate commuting tests:** use the same task contract and semantic reference to compare the Signal8 runtime with a second implementation or eventual hardware adapter.

The order matters. It builds on the now-established trace/evidence foundations before attempting automatic semantic discovery.

## 9. Decision rule

An invariant candidate is worth retaining when it:
- states exactly which representations, contexts, actions, and observations it covers;
- survives an independent implementation or held-out test;
- retains its counterexamples and uncertainty limits;
- improves a measurable task property or makes an important distinction navigable;
- does not require silently filling unknown regions of the model.

A candidate should be narrowed, split, or rejected when a counterexample shows that its claimed preservation relation is too broad. This is progress: the boundary of an invariant is part of the knowledge gained.
