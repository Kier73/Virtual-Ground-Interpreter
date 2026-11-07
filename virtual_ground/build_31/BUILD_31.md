# Build 31 — Compositional Signal Algebra and Observer Interchange

## Status

- Build 31 unit tests: **20/20 passed**.
- Exhaustive two-operation chains: **2,048/2,048 correct** across all three-operand values and all four opcode sequences.
- Binary arithmetic: **512/512 correct** across four observer coordinates, two operations, and all operand pairs.
- Observer-operation commutation: **512/512 semantic agreements**.
- Reversible transitions: **512/512 recovered the original first operand** when the second operand was retained.
- Common scalar gain/phase channel: **32/32 recovered correctly** when the same channel factor was applied to signal and pilot.
- The experiment is a finite numerical complex-baseband model over `Z/8Z`; it is not physical analog hardware or a universal computer.

## 1. Objective

Build 30 established that pilot-referenced complex phasors can represent operands and that complex multiplication/conjugation implements modular addition/subtraction before integer decoding.

Build 31 asks whether those operations compose into longer executions, whether coordinate representations can change between operations without changing semantic meaning, and how calibration/noise errors propagate through the resulting path.

## 2. Signal-state model

A state is a pair of sampled complex sequences plus an observer-coordinate label:

\[
S=(x[n],p[n],u),\qquad u\in U(8)=\{1,3,5,7\}.
\]

The pilot-referenced complex estimate is

\[
\widehat z=\operatorname{normalize}\left(
\frac{1}{N}\sum_{n=0}^{N-1}
\frac{x[n]\overline{p[n]}}{|p[n]|^2}
\right).
\]

The semantic value \(k\in\mathbb Z/8\mathbb Z\) is represented in observer coordinate \(u\) by

\[
\chi_u(k)=e^{2\pi iuk/8}.
\]

Integer decoding is a terminal observation operation. Signal execution uses calibrated complex phasors, not integer operands.

## 3. Observer-coordinate automorphisms

The odd residues are exactly the units of \(\mathbb Z/8\mathbb Z\). Each \(u\in\{1,3,5,7\}\) defines an invertible character of the cyclic group.

For source coordinate \(u\) and target coordinate \(v\), define

\[
R_{u\to v}(z)=z^{v u^{-1}\bmod 8}.
\]

This map preserves semantic state and composes:

\[
R_{v\to w}\circ R_{u\to v}=R_{u\to w}.
\]

Its inverse is \(R_{v\to u}\). No symbol/integer decode is required to reframe a state; the implementation recovers the pilot-referenced phasor and raises it to the appropriate odd power.

## 4. Operation laws and naturality

For every observer coordinate,

\[
\chi_u(a+b)=\chi_u(a)\chi_u(b),
\]

\[
\chi_u(a-b)=\chi_u(a)\overline{\chi_u(b)}.
\]

The coordinate transformation commutes with both operations:

\[
R_{u\to v}(F_u(x,y))
=F_v(R_{u\to v}(x),R_{u\to v}(y)).
\]

This is the central Build 31 result: an operation can be moved across an observer-coordinate transformation without changing its semantic result.

## 5. Composition experiment

The experiment exhaustively evaluates all four two-instruction programs:

- `ADD8 → ADD8`
- `ADD8 → SUB8`
- `SUB8 → ADD8`
- `SUB8 → SUB8`

Each program is evaluated for every triple \((a,b,c)\in\mathbb Z_8^3\):

\[
4\times 8^3=2,048\text{ executions}.
\]

The three input states may use different observer coordinates. The intermediate result and final result may each use another coordinate. The intermediate result is emitted as a signal state and consumed by the next operation. It is not converted into an integer.

**Result: 2,048 executions, zero semantic errors.** A unit test patches the terminal integer decoder to raise if any binary operation, reframing step, or two-operation chain attempts to call it.

## 6. Exhaustive checks

| Property | Cases | Errors |
|---|---:|---:|
| Symbol encode/decode across four observers | 32 | 0 |
| Coordinate-change round trips | 128 | 0 |
| `ADD8` / `SUB8` across all observers | 512 | 0 |
| Operation/observer commutation | 512 | 0 |
| Two-operation chains, all opcode patterns | 2,048 | 0 |
| Inverse translations | 512 | 0 |
| Common scalar gain/phase cancellation | 32 | 0 |

These are exhaustive finite checks for the declared `Z/8Z` model, not proofs about arbitrary signal spaces.

## 7. Calibration propagation

The scalar channel model applies a complex gain/phase to the data signal and a separately phase-shifted copy to the pilot. A residual pilot calibration error \(\delta\) therefore appears as a residual phasor rotation \(e^{i\delta}\).

For an `ADD8` stage followed by `SUB8`, the residual phase follows

\[
\boxed{\delta_{out}=\delta_a+\delta_b+\delta_{mid}-\delta_c.}
\]

The measured residual agreed with this law to floating-point precision in the controlled fixtures:

| Residual inputs (radians) | Predicted final error | Measured final error | Decoded output |
|---|---:|---:|---:|
| 0, 0, 0, 0 | 0.000 | 0.000 | 7, correct |
| 0.05, 0.10, 0.04, 0.02 | 0.170 | 0.170 | 7, correct |
| 0.12, 0.09, 0.08, 0.03 | 0.260 | 0.260 | 7, correct |
| 0.25, 0.20, 0.15, 0.02 | 0.580 | 0.580 | 0, incorrect |
| 0.45, 0, 0, 0 | 0.450 | 0.450 | 0, incorrect |

For 8-PSK the nearest-symbol decision boundary lies \(\pi/8\) radians (22.5 degrees) from a symbol center. The last two examples cross that boundary. This makes calibration state an execution dependency, not merely a one-time input-cleaning step.

A common complex gain/phase applied equally to the signal and its pilot cancels in the pilot-referenced estimate. Differential signal/pilot phase does not.

## 8. Noise sweep

Each noise level evaluates all four opcode sequences for all 512 input triples (2,048 chains). Independent additive Gaussian I/Q noise is applied to input payload samples and both emitted stages; the pilot is the reference path. Each state uses 64 samples.

| Complex noise sigma per I/Q component | Errors | Accuracy |
|---:|---:|---:|
| 0.00 | 0 / 2,048 | 100.00% |
| 0.02 | 0 / 2,048 | 100.00% |
| 0.10 | 0 / 2,048 | 100.00% |
| 0.25 | 0 / 2,048 | 100.00% |
| 0.50 | 18 / 2,048 | 99.12% |
| 1.00 | 362 / 2,048 | 82.32% |
| 1.50 | 783 / 2,048 | 61.77% |
| 2.00 | 1,074 / 2,048 | 47.56% |

The values are tied to this sample count, unit-amplitude signal, pilot estimator and Gaussian noise model. They are not a general channel-capacity result.

## 9. Software timing diagnostic

A local Python timing diagnostic compares:

- signal path: pilot correlation, two phasor operations, and signal re-emission of the intermediate and final results;
- conventional baseline: decode the three input signals, execute the two modular integer operations, and re-encode the final result as a signal state.

Measured medians in this run:

| Path | Median per chain |
|---|---:|
| Signal-domain chain | 0.333 ms |
| Decode / integer compute / re-encode | 0.223 ms |
| Ratio | 1.49× slower for signal-domain path |

This recorded run measured 0.333 ms versus 0.223 ms (1.49× slower); repeated runs varied modestly with interpreter and machine load. This is a Python implementation timing result, sensitive to sample count and machine load. It is not a hardware comparison and gives no evidence of lower energy, latency or cost in a physical signal processor. The present implementation pays pilot-correlation and intermediate re-emission overhead.

## 10. Reusable correctness contracts

The finite operation contracts are:

\[
F_+(\chi_u(a),\chi_u(b))=\chi_u(a+b),
\]

\[
F_-(\chi_u(a),\chi_u(b))=\chi_u(a-b).
\]

The observer-change contract is:

\[
R_{u\to v}(\chi_u(k))=\chi_v(k).
\]

Since each primitive preserves its corresponding `Z/8Z` transition, correctness of any finite composed path follows by induction on the number of transitions, provided every intermediate observer conversion satisfies the reframe contract. The implementation checks representative finite domains exhaustively; the report does not claim a machine-checked theorem in Lean or another proof assistant.

## 11. Interpretation

Build 30 demonstrated that a signal representation's algebra can implement finite arithmetic before integer decoding. Build 31 demonstrates that this finite algebra can be composed, that its semantic result survives changes among four equivalent observer coordinates, and that calibration residuals propagate predictably through a composed path.

A stronger formulation of the research direction is now experimentally supported within this model:

**The invariant is not a fixed signal coordinate. It is the semantic relation preserved by operations and by transformations between compatible coordinates.**

## 12. Limitations

1. Numerical complex-baseband simulation only; no physical analog hardware was constructed or measured.
2. The finite state group is `Z/8Z`; universal or Turing-complete computation is not established.
3. The observer family comprises the four automorphisms of this cyclic group, not arbitrary sensor or model representations.
4. The channel model is scalar and does not include multipath, carrier-frequency offset, nonlinear distortion, or clock drift.
5. Noise results apply only to this sample count, pilot design and generated Gaussian distribution.
6. The signal-domain path is slower than the decode/compute/re-encode software baseline in this benchmark.
7. Reversibility applies to group translations when the second operand is retained. Arbitrary branching, destructive updates, and memory lifecycle have not been implemented.
8. The operation recovers pilot-referenced complex phasors before applying group operations; it does not multiply raw waveform samples pointwise as a complete physical circuit would.

## 13. Next build

Build 32 should investigate a **signal-state machine**: persistent signal memory, control selection, conditional transitions and explicit preservation of branch information where reversibility is required. The next goal should be a small executable state machine with a testable instruction trace, not a premature claim of general-purpose computation.
