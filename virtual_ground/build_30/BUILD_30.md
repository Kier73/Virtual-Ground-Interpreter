# Build 30 — Adaptive Observers and Signal-Coded Computation

**Verification:** 24/24 new tests pass; 177/177 combined tests pass across Builds 24–30.

## Summary

Build 30 tests two connected ideas:

1. An observer can select a signal representation according to a declared task and calibration evidence.
2. Signals can carry data and instructions, and transformations on signal representations can execute a finite arithmetic operation without first decoding operands into integers.

This is a controlled numerical prototype. It does **not** demonstrate a universal signal computer, a physical analog processor, or a performance advantage over conventional digital computation.

## A. Adaptive observer selection

The selector evaluates nine candidate profiles formed from three boundary views (`harmonic`, `temporal`, `combined`) and three token views with the same names. Frame size and hop remain fixed at 256 and 64 samples to isolate observer-view selection.

It uses four labelled calibration traces per task, with task utility:

\[
U(O)=0.7F_1^{boundary}(O)+0.3A_{pairwise}^{token}(O)
\]

The chosen profile is frozen before four independent held-out traces are evaluated. The Build 29 segmenter receives raw synthetic signals, not ground-truth event boundaries. Calibration labels are used by the Build 30 profile selector to estimate whether a representation serves the declared task.

| Task family | Selected boundary view | Selected token view | Held-out boundary F1 | Held-out token pairwise accuracy |
|---|---|---|---:|---:|
| Frequency-coded | Combined | Harmonic | 0.770 | 1.000 |
| Amplitude-coded | Temporal | Temporal | 0.748 | 1.000 |
| Mixed two-channel | Combined | Temporal | 0.839 | 0.969 |

All three selections retain plausible alternatives within an absolute utility margin of 0.015. The default profile is therefore a preferred member of a near-optimal set, not a uniquely identified universal observer.

The result supports observer/task-relative representation choice. It does not show unsupervised discovery of a task objective: the task and labelled calibration set are provided in this experiment.

## B. Coding through signals

The program has two coordinated signal paths.

### Control path — FSK

The control stream uses 16-ary frequency-shift keying. Each symbol selects one orthogonal DFT bin in a 512-sample frame at 8192 Hz. A four-symbol preamble `[15, 0, 15, 0]` identifies the stream. Each instruction contributes an opcode plus its complement:

- `ADD8` → opcode 1, complement 14
- `SUB8` → opcode 2, complement 13

The complement is an error-detection check, not a full error-correcting code.

### Operand path — 8-PSK

Operands are represented as unit complex phasors:

\[
z_k=e^{2\pi i k/8},\qquad k\in\mathbb Z/8\mathbb Z
\]

Each operand signal is accompanied by a channel-specific pilot. Pilot correlation recovers its complex phasor without converting it to an integer:

\[
\widehat z_a=\frac1N\sum_{n=0}^{N-1}
\frac{x_a[n]\overline{p_a[n]}}{|p_a[n]|^2}
\]

The signal-domain arithmetic is:

\[
z_{a+b\bmod 8}=z_a z_b
\]

\[
z_{a-b\bmod 8}=z_a\overline{z_b}
\]

Thus, after the FSK control opcode is decoded, the arithmetic stage multiplies the recovered operand phasors (or multiplies one by the other's conjugate). The operands are not decoded to integers before that operation. The output is re-encoded onto an output pilot.

This is a finite group computation using the one-dimensional complex representation of the cyclic group \(\mathbb Z/8\mathbb Z\). The homomorphism is exact in the noiseless model.

### End-to-end program

Six instructions are transmitted:

| Instruction | Expected result |
|---|---:|
| `ADD8(3,6)` | 1 |
| `SUB8(1,4)` | 5 |
| `ADD8(7,7)` | 6 |
| `SUB8(0,3)` | 5 |
| `ADD8(5,5)` | 2 |
| `SUB8(7,2)` | 5 |

The control decoder recovers a 37-sample leading offset and all six opcodes. The signal-domain arithmetic and output encoding reproduce all six expected results.

## C. Verification results

- All 64 `ADD8` operand pairs and all 64 `SUB8` operand pairs are correct in the noiseless exhaustive sweep.
- The full six-instruction transmitted program executes correctly.
- FSK control is decoded with a 37-sample leading offset, additive noise, positive gain scaling and DC offset.
- Phase arithmetic tolerates independent per-channel gain and phase offsets when channel-specific pilots are correctly supplied.
- A one-symbol pilot phase miscalibration changes the decoded result, demonstrating that calibration is necessary.
- No operand integer decoding occurs before the phasor operation (tested by replacing the integer decoder with a failure during execution).

Noise sweep over 128 modular operations:

| Complex noise sigma | Errors | Accuracy |
|---:|---:|---:|
| 0.00 | 0 | 100.00% |
| 0.02 | 0 | 100.00% |
| 0.10 | 0 | 100.00% |
| 0.50 | 0 | 100.00% |
| 1.00 | 1 | 99.22% |
| 1.50 | 3 | 97.66% |
| 2.00 | 12 | 90.63% |

The noise sigma is in the same amplitude units as the complex signal samples. These figures apply to the fixed 256-sample pilot-correlated fixture, not a general communication channel.

## D. What this establishes about coding by signals

The experiment establishes three bounded claims:

1. **Signals can encode data.** FSK control symbols and 8-PSK operands carry program information.
2. **Signals can encode instructions.** The FSK control path carries the operation choice, with a complement check.
3. **Signal representations can participate directly in computation.** Complex phasor multiplication and conjugation implement modular addition and subtraction before operands are decoded into integers.

What it does not establish:

- universal or Turing-complete signal computation;
- that the entire interpreter can execute without a digital controller;
- that a physical mixer or analog circuit has been built or benchmarked;
- lower energy, latency or cost than digital arithmetic;
- robustness to arbitrary multipath, carrier-frequency offset, nonlinear distortion or timing drift;
- a universal, observer-independent signal vocabulary.

The signal as a broad descriptive medium is promising, but the invariant is not the raw waveform. It is the relational structure that survives a declared family of transformations and remains distinguishable under a specified observer.

## E. Relation to the Virtual Ground conjecture

The Ground need not be committed to one signal coordinate system. It can retain a set of observer profiles and choose among them according to intention, calibration and resources.

The coded arithmetic fixture adds a more concrete possibility: an operation can be represented as a transformation on signal states. The instruction is not merely a label attached to a digital operation; a restricted operation is implemented in the algebra of the signal representation.

A future interpreter could therefore discover both:

- which signal representation makes a system most navigable;
- which operations can be carried out directly in that representation.

This is an early finite proof-of-concept, not a general Virtual Layer-native computer.

## D. Raw-signal event bridge into the coded program

The generated FSK control waveform was also passed through the generic Build 29 continuous-signal event observer, before the protocol-specific FSK decoder was used. With a 256-sample analysis frame and 64-sample hop, the temporal observer recovered 14 of the 15 internal symbol boundaries (recall 0.933, precision 1.000, F1 0.966). The combined view recovered 11/15 (F1 0.846); the harmonic view recovered 8/15 (F1 0.696).

This is a useful connection between the signal-to-event work and signal-coded instructions. However, the FSK decoder still knows the symbol frame size and uses a preamble to recover the 37-sample offset. The generic event detector does not yet recover every exact symbol boundary by itself. The final framing result is therefore a hybrid of discovered event evidence and a declared protocol.

## E. Updated interpretation

The experiment now supports a stronger but still bounded statement: the same signal system can expose event boundaries, carry an instruction stream, encode operands, and undergo an algebraic transformation that performs a finite computation. It is not merely a symbolic message transported by sound-like data; the representation's group law performs the arithmetic.
