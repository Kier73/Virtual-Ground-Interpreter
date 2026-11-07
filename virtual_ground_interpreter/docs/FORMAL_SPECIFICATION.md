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
