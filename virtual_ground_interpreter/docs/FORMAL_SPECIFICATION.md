# Virtual Ground Interpreter — Formal Specification

## 1. Purpose and scope

The initial Virtual Ground Interpreter (VGI) is an executable interpreter for a bounded observable state space. Its immediate utility is to execute composable operations and conditional transitions directly over a signal-native representation, retaining semantic correctness across declared observer-coordinate changes.

A constrained typed task-expression language can be lowered into the instruction IR. The interpreter validates the resulting program against a Ground contract and executes it. This is not yet a general task-to-program synthesizer: arbitrary natural-language objectives, unknown algorithms, and automatically discovered Ground semantics are outside scope.

## 1.1 Typed task-expression language

A `TaskSpec` declares named input memory addresses and one or more named output expressions. The current expression grammar is:

\[
E ::= Input(a)\mid Add(E,E)\mid Sub(E,E)\mid Reframe(E,u)\mid If(C,E,E)
\]

with guards

\[
C ::= IsIdentity(E,\tau)\mid Equal(E,E,\tau).
\]

The compiler recursively lowers expressions into `LOAD`, `ADD`, `SUB`, `REFRAME`, `BRANCH_IDENTITY`, `BRANCH_EQ`, `MOVE`, `JUMP`, `STORE`, `EMIT` and `HALT`. For a conditional expression, the false expression is emitted as fall-through and the true expression is reached through the guard's branch edge. Nested conditionals are lowered recursively.

This compiler performs structural lowering only. It does not search for an algorithm, optimize a task across different backends, infer hidden invariants, or parse arbitrary natural language. Inputs must already exist in the initial memory mapping as signal states.

## 2. Ground contract

A Ground is a versioned executable specification, not merely a lookup table and not an ontological assertion about unobservable physical state.

For the current finite Ground:

\[
G=(D,O,\mathcal I,\mathcal A,\mathcal E)
\]

where:

- `D` is the value domain `signal.phase.cyclic.z8.v1`;
- `O={1,3,5,7}` is the supported observer-coordinate family;
- `I` is the allowed instruction set;
- `A` is the declared assumption set;
- `E` is the evidence/provenance record.

A canonical serialization of these fields is SHA-256 fingerprinted. The fingerprint binds a program checkpoint to the exact Ground contract used to interpret it.

A change in the domain, observer maps, instruction semantics, or branch policy requires a new Ground version and fingerprint.

## 3. State representation

A signal state is

\[
S=(z,u,\epsilon),
\]

with unit phasor `z`, observer coordinate `u`, and a conservative residual phase-error bound `epsilon` in radians.

The semantic encoding is

\[
\chi_u(k)=e^{2\pi iuk/8},\qquad k\in\mathbb Z/8\mathbb Z.
\]

The semantic integer is not stored in `SignalValue`. It is present only at explicit ingress (`encode_symbol`) or egress (`observe_symbol`) boundaries.

### 3.1 I/Q ingress and egress

Given payload samples `x[n]` and pilot samples `p[n]`, the calibrated phasor estimate is

\[
\hat z=\operatorname{normalize}\left(
\frac{1}{N}\sum_{n=0}^{N-1}
\frac{x[n]\overline{p[n]}}{|p[n]|^2}
\right).
\]

`ingest_iq` implements this estimator. The caller supplies `phase_error_bound`; the reference runtime does not infer a statistically calibrated confidence interval from the sample set.

`emit_iq` renders a state onto a supplied pilot sequence:

\[
x_{out}[n]=p[n]z.
\]

The runtime operates on the calibrated phasor state after ingress. It does not claim that its Python execution is a physical signal-domain circuit.

## 4. Observer coordinate changes

The units modulo 8 are `U(8)={1,3,5,7}`. For source observer `u` and target observer `v`, define

\[
m=(vu^{-1})\bmod 8.
\]

Then

\[
R_{u\to v}(z,u,\epsilon)=
\left(\operatorname{normalize}(z^m),v,\min(\pi,m\epsilon)\right).
\]

The semantic state is preserved because

\[
R_{u\to v}(\chi_u(k))=\chi_v(k).
\]

The maps satisfy

\[
R_{v\to w}\circ R_{u\to v}=R_{u\to w},
\qquad R_{v\to u}=R_{u\to v}^{-1}
\]

on the ideal finite signal domain.

## 5. Signal operations

Operations align the right operand to the left operand's observer coordinate, then operate on calibrated phasors.

\[
ADD(S_a,S_b)=
(z_a z_b',u_a,\min(\pi,\epsilon_a+\epsilon_b'))
\]

\[
SUB(S_a,S_b)=
(z_a\overline{z_b'},u_a,\min(\pi,\epsilon_a+\epsilon_b'))
\]

where `S_b' = R_(u_b -> u_a)(S_b)`.

The corresponding semantic laws are

\[
\chi_u(a+b)=\chi_u(a)\chi_u(b),
\]

\[
\chi_u(a-b)=\chi_u(a)\overline{\chi_u(b)}.
\]

The operations are closed over the declared domain. Their results can become operands of subsequent instructions without integer decoding.

## 6. Conditional transitions

For two observer-aligned phasors, calculate relative phase distance

\[
d=\left|\arg(z_a\overline{z_b})\right|\in[0,\pi].
\]

Let the summed phase-error bound be

\[
e=\min(\pi,\epsilon_a+\epsilon_b).
\]

The possible distance is conservatively enclosed by

\[
L=\max(0,d-e),\qquad U=\min(\pi,d+e).
\]

For configured tolerance `tau`:

- `TRUE` if `U <= tau`;
- `FALSE` if `L > tau`;
- `INDETERMINATE` otherwise.

The interpreter traps on `INDETERMINATE`, leaves the program counter and machine state unchanged, and does not silently choose a branch. The identity guard compares a value against phasor `1+0j` in its current observer coordinate.

This is a three-valued guard semantics. It is intentionally not equivalent to thresholding a noisy point estimate and always returning a Boolean.

## 7. Machine state and transition relation

A machine state is

\[
M=(pc,\rho,\mu,\Omega,H),
\]

where:

- `pc` is the program counter;
- `rho` is the register mapping;
- `mu` is persistent signal-valued memory;
- `Omega` is the output/emission sequence;
- `H` is the execution trace and undo journal.

An instruction induces a partial transition

\[
\langle P,M\rangle\rightarrow\langle P,M'\rangle.
\]

The transition is partial because missing registers/cells, invalid instructions, indeterminate branches, and step-limit conditions are explicit runtime errors rather than fabricated results.


### 7.1 Instruction transition contracts

For a program of length `n`, a normal instruction advances to `pc+1`; a taken branch or jump installs its declared target. Program construction rejects control-flow targets outside `[0,n-1]`. The instruction contracts below are the reference semantics; `rho` is the register store and `mu` is persistent memory.

| Instruction | Preconditions | State effect |
|---|---|---|
| `LOAD(dst,a)` | `a` is in `dom(mu)` | `rho[dst] := mu[a]` |
| `STORE(src,a)` | `src` is in `dom(rho)` | `mu[a] := rho[src]` |
| `MOVE(dst,src)` | `src` is in `dom(rho)` | `rho[dst] := rho[src]` |
| `REFRAME(dst,src,v)` | `src` exists; `v` is a Ground observer | `rho[dst] := R(rho[src],v)` |
| `ADD(dst,x,y)` | `x,y` exist and are valid Ground values | `rho[dst] := ADD(rho[x],rho[y])` |
| `SUB(dst,x,y)` | `x,y` exist and are valid Ground values | `rho[dst] := SUB(rho[x],rho[y])` |
| `BRANCH_EQ(x,y,t,tau)` | `x,y` exist; `tau` is valid | if guard is `TRUE`, `pc := t`; if `FALSE`, fall through; if indeterminate, trap atomically |
| `BRANCH_IDENTITY(x,t,tau)` | `x` exists; `tau` is valid | same three-valued branch rule against the group identity |
| `JUMP(t)` | `t` is a valid instruction index | `pc := t` |
| `EMIT(x,label)` | `x` exists | append `(label,rho[x])` to output sequence |
| `HALT` | none | set halted state |

The `LOAD`, `MOVE`, `REFRAME`, `ADD`, and `SUB` instructions only write registers; `STORE` writes memory; `EMIT` appends output; branch and jump instructions only alter control state; `HALT` changes the halt flag. These footprints are useful for later proof rules and safe execution scheduling.

A failed instruction is atomic: the pre-step machine state is restored before the error is surfaced. In particular, an indeterminate guard does not append a successful trace event or alter the program counter.

The memory persists for the lifetime of the machine and can be serialized in a checkpoint. A checkpoint includes program and Ground fingerprints; restore rejects mismatches. The current checkpoint format preserves execution state and visible trace but intentionally does not reconstruct pre-checkpoint undo history.

Each branch event records the predicate kind, compared signal operands, observer used for comparison, phase distance, uncertainty, lower and upper distance bounds, tolerance, result, and resulting program counter. Every successful instruction also records the signal values written to registers, memory, or output. This permits replay and audit against the same Ground.

The undo journal stores pre-step state snapshots. `undo()` reverses the most recent executed instruction, including branch PC changes, memory writes, register writes, emissions and halt state. This reference journal is intentionally simple and has O(number of live registers + memory cells) snapshot cost per instruction; it is a correctness baseline, not an optimized storage strategy.

A serialized checkpoint carries both the initial memory image and a SHA-256 state digest to detect accidental or unauthorized modification when restoring. This digest is not a digital signature and does not authenticate who created the checkpoint. Program and Ground fingerprints are checked separately. `reset()` returns the machine to its original memory image and clears the register file, outputs, trace, and undo history.

## 8. Control plane and data plane

The data plane consists of `SignalValue` states and signal-algebra operations. The control plane is the explicit typed instruction stream and program counter.

This separation lets us test whether signal values retain their computational meaning through a program without prematurely claiming that the controller itself is signal-native. The signal-control transport and learned opcode discovery remain separate extensions.

## 9. Invariance and comparison policy

The allowed observer changes are automorphisms of `Z/8Z`. Identity and equality are preserved under these changes. A linear ordering of residues is not preserved by all observer automorphisms and is not part of this Ground.

Thus the current guards are deliberately based on relations that survive observer interchange:

- equality of semantic states;
- identity relative to the group operation.

A future domain can support order, distance, topology, or other relations only when those semantics are explicitly declared and verified for that domain.

## 10. Correctness obligations

For any accepted program, the core runtime obligations are:

1. **Domain closure:** every operation returns a valid `SignalValue` in a Ground-approved observer coordinate.
2. **Semantic preservation:** operation outputs correspond to their declared `Z/8Z` transition.
3. **Observer naturality:** reframing before or after a supported operation produces equivalent semantic results.
4. **Branch soundness:** a taken or untaken branch is justified by a non-overlapping phase-distance interval; ambiguous cases trap.
5. **Transition atomicity:** a failed instruction does not partially mutate machine state.
6. **Checkpoint binding:** a checkpoint cannot be restored under a different program or Ground fingerprint.
7. **Auditability:** each successful transition produces an execution event.

The automated finite verifier checks exhaustive cases in the finite domain. This is not a machine-checked proof in Lean or another proof assistant. A future proof target is a small trusted semantics kernel with separately checked transition contracts and a derivation rule for finite execution traces.

## 11. Explicit limitations

- The domain is finite `Z/8Z`.
- The four observer coordinates are the automorphisms of that cyclic group, not arbitrary sensor/model representations.
- The signal-state runtime uses pilot-calibrated phasors, not raw waveform buffers as persistent memory.
- Phase uncertainty is a conservative user-supplied bound; no probabilistic calibration model is fitted.
- The program is supplied by the user; arbitrary task descriptions are not automatically translated into IR.
- Learning new transitions, stochastic grounds, continuous state spaces, asynchronous clocks, and resource-aware algorithm selection are outside this version.
- No physical analog hardware, speedup, energy advantage, or universal-computation result is claimed.


## 12. First-class finite transition systems

The runtime now has a separate predictive transition contract:

\[
\mathcal T=(Q,A,C,q_0,\Omega),
\]

where \(Q\) is a set of predictive contexts, \(A\) a finite action alphabet, \(C\) an output-channel schema, \(q_0\) the declared initial predictive context, and \(\Omega\) the set of observed transition alternatives.

For a pair \((q,a)\), the evidence status is:
- **known:** exactly one observed successor/output pair;
- **ambiguous:** two or more distinct observed successor/output pairs;
- **unknown:** no observed pair.

The step relation is executable only for known pairs. Unknown and ambiguous pairs raise distinct errors. They are not interpreted as identity transitions, no-ops, or guessed successors.

A GroundTransitionSystem represents predictive contexts. These must not be equated with physical hidden-state identity: two physical states may share a predictive context under the declared observer and tested action family.

The importer accepts the deterministic Build 24 VG-PredictiveMealy-1 format. Missing transition or output evidence is retained as unknown. A new VGI-TransitionSystem-1 serialization can additionally retain ambiguous alternatives, support counts, and evidence references.

## 13. Transition-system compilation and differential semantics

The first compiler lowers a **complete** finite transition system into the existing Signal8 instruction IR. Predictive-state and action identifiers are embedded as finite symbol indices in \(\mathbb Z/8\mathbb Z\); output channels are also finite symbols. This is a backend-specific encoding, not a general encoding for arbitrary state spaces.

For a compiled action word of fixed length, each step performs guarded dispatch over declared state/action pairs. It writes the successor to persistent memory and emits the successor and output-channel values. An unmatched dispatch terminates early; the wrapper rejects incomplete semantic emissions.

Let \(\operatorname{run}_{\mathcal T}(a_0,\ldots,a_{n-1})\) be the direct reference semantics and \(\operatorname{run}_{IR}\) the compiled machine. The required differential condition is equality of the semantic state trace and output trace:

\[
\operatorname{states}(\operatorname{run}_{\mathcal T})
=
\operatorname{states}(\operatorname{run}_{IR}),
\qquad
\operatorname{outputs}(\operatorname{run}_{\mathcal T})
=
\operatorname{outputs}(\operatorname{run}_{IR}).
\]

This is checked for supplied action sequences. It is not a proof for untested sequences or arbitrary domains. The compiler refuses partial or ambiguous grounds instead of inventing semantics.

The current Signal8 compiler is intentionally bounded to at most eight states, eight actions, and output values in \(\mathbb Z/8\mathbb Z\). It expands guarded dispatch per compiled action slot; it is a semantic integration step, not yet a compact phase-law optimizer.

## 14. Terminal observation and uncertainty

The terminal symbol observer now respects the value's conservative phase-error bound. It determines which 8-PSK symbol decision regions intersect the phase interval. A symbol is returned only when exactly one symbol remains possible; otherwise the observer raises AmbiguousSymbolObservation.

This aligns terminal decoding with the interpreter's three-valued branch policy: uncertainty must not be silently discarded at the output boundary. A future API may expose the full candidate set as a typed result for callers that can use set-valued outputs.


## 15. Observer contexts and horizon-indexed predictive quotients

For a finite deterministic transition system \(\mathcal T=(Q,A,C,\delta,\lambda)\), define an observer context \(O=(A_O,C_O)\), where the selected action set determines available probes and the selected channel set determines the observable output projection.

The horizon signatures are:

\[
P_0(q)=\star,
\]

\[
P_{h+1}(q)=
\left(
\left(
\pi_{C_O}(\lambda(q,a)),
P_h(\delta(q,a))
\right)
\right)_{a\in A_O}.
\]

Define \(q\equiv_{O,h}r\) iff \(P_h(q)=P_h(r)\). This is equality of projected output traces for all selected action words through the declared horizon. Horizon zero places all declared states in one class. Increasing the horizon can split a class but cannot merge classes:

\[
q\equiv_{O,h+1}r\Rightarrow q\equiv_{O,h}r.
\]

For a finite \(n\)-state Ground, at most \(n-1\) strict refinements are possible. If the partition is unchanged between two adjacent horizons, deterministic refinement is stable thereafter. A discrete partition (one class per declared state) is also immediately stable because no further split is possible. The implementation refuses to derive a quotient when any selected state/action edge is unknown or ambiguous.

## 16. Quotient projections and layered transition maps

For \(H\ge h\), every class in \(Q_{O,H}\) lies inside one class in \(Q_{O,h}\), defining a projection \(\pi_{H\to h}\). The implementation checks this property rather than assuming it.

For adjacent layers, a transition/output map is well-defined:

\[
([q]_{h+1},a)
\mapsto
(\pi_{C_O}(\lambda(q,a)),[\delta(q,a)]_h).
\]

The implementation verifies that all representatives of a source class yield the same projected output and target class. This is a finite homomorphism-like compatibility condition between adjacent predictive quotients. It does not assert that arbitrary observer quotients are isomorphic or share a common geometry.

## 17. Observer-relative behavioral pseudometric

For a fixed observer \(O\), action distribution \(\mu\), horizon \(H\), discount \(\gamma\in[0,1]\), and metric \(d_C\) on projected outputs, define

\[
D_{H,O,\mu,\gamma}(q,r)=
\frac{1}{Z_H}
\mathbb E_{w\sim\mu^H}
\left[
\sum_{t=0}^{H-1}\gamma^t
d_C(y_t(q,w),y_t(r,w))
\right],
\qquad
Z_H=\sum_{t=0}^{H-1}\gamma^t.
\]

The same action sequence is applied to both initial contexts. For deterministic systems this is a pseudometric because each fixed action word induces a sum of pullbacks of the output metric, and expectation preserves non-negativity, symmetry, and the triangle inequality. Distinct contexts may still have distance zero. If \(\mu\) has full support on \(A_O\), zero distance is equivalent to equality of selected output traces over all action words of length \(H\), which also determines every shorter prefix.

The current implementation uses the normalized cyclic metric on selected \(\mathbb Z/8\mathbb Z\) output symbols. The resulting distance is not universal or observer-independent; it is a profile whose context, action weights, horizon, discount, and output metric must travel with the value.


## 18. Cost-aware active attention over finite observers

A candidate attention capability \(p\) adds either an action probe or an output channel to the current observer contract. For a quotient \(Q_{O,H}\), define the unresolved-pair objective:

\[
U(O,H)=\sum_{B\in Q_{O,H}}\binom{|B|}{2}.
\]

The deterministic marginal reduction and efficiency are:

\[
\Delta(p\mid O,H)=U(O,H)-U(O\oplus p,H),
\qquad
\eta(p\mid O,H)=\frac{\Delta(p\mid O,H)}{c(p)}.
\]

The initial planner implements a myopic greedy policy that repeatedly selects the affordable candidate with maximum marginal efficiency. It stops when no candidate has positive marginal gain.

For small candidate pools, exhaustive planning solves:

\[
\min_{S\subseteq P}U(O\oplus S,H)
\quad\text{such that}\quad
\sum_{p\in S}c(p)\le B.
\]

The exact solver enumerates candidate subsets and defaults to a maximum of sixteen candidates.

The objective is not generally submodular. A two-context fixture demonstrates complementary observations: adding action \(B\) while channel \(x\) is visible produces no split; adding channel \(y\) while only action \(A\) is available also produces no split; adding both exposes a distinguishing \((B,y)\) output. Thus one candidate can have zero marginal value before another capability is acquired and positive marginal value afterward. Greedy attention can stop despite a feasible informative combination.

The score is deterministic pair reduction, not expected information gain. Probabilistic attention requires explicit priors and calibrated observation likelihoods. Candidate costs are relative declared units and do not imply measured latency or energy.
