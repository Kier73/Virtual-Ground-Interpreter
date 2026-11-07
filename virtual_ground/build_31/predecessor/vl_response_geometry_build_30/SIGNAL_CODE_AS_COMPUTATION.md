# Signal Code as Computation

## Three different meanings

"Coding via signals" can mean at least three things, which must not be collapsed:

1. **Signal as data representation:** information is encoded in waveform properties.
2. **Signal as instruction transport:** a signal selects operations to perform.
3. **Signal as computational substrate:** the operation itself is a transformation on signal representations.

Build 30 demonstrates all three in a small finite system.

## Signal control language

The control stream uses a 16-symbol FSK alphabet. A four-symbol preamble supports frame location. An instruction is carried by an opcode and its complement. The declared instruction set contains `ADD8` and `SUB8`.

## Signal operand language

Values in \(\mathbb Z/8\mathbb Z\) are represented by 8-PSK roots of unity:

\[
\chi(k)=e^{2\pi i k/8}
\]

This is a group homomorphism:

\[
\chi(a+b)=\chi(a)\chi(b)
\]

and

\[
\chi(a-b)=\chi(a)\overline{\chi(b)}
\]

The complex phasors carry the operands. A per-channel pilot provides gain and phase reference. Correlation with the conjugated pilot recovers a complex representation, not an integer operand.

## Computation

After the control path selects the operation, the data path applies multiplication or conjugate multiplication to the recovered phasors. The result is emitted as another pilot-referenced carrier.

The operand symbols are converted to integers only for final evaluation. A test patches the integer decoder to fail if it is called during the arithmetic operation; the signal-domain operation still succeeds.

## Interpretation

This is a concrete signal-domain arithmetic primitive. It shows that a signal need not merely carry a description of an operation; the algebra of its representation can implement the operation.

However, the prototype is a numerical complex-baseband simulation. It uses digital sample arrays and a software control decoder. It does not demonstrate a physical analog circuit, universal computation, or a speed/energy advantage.

To establish a more general signal computer, further work would need to introduce persistent memory, conditional branching, signal fan-out, composition of longer programs, synchronization, error correction and physical channel measurements.

## Connection to raw event discovery

The FSK control waveform is also analyzed by the preserved Build 29 event observer. The temporal view recovers 14 of 15 internal FSK symbol boundaries (F1 0.966) without being given those boundary labels. The FSK decoder then uses the known 512-sample symbol duration and sync preamble to finish exact decoding.

This shows a partial raw-signal-to-instruction path. It is not yet fully protocol-blind: generic event discovery provides most boundaries, while a declared symbol duration and preamble resolve the framing.
