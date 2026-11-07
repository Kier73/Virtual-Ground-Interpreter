# Adaptive Observer Selection

## Purpose

Select an observer representation by measured usefulness for a declared task, rather than treating one signal feature family as universally best.

## Candidate family

Nine profiles are evaluated:

\[
O=(v_b,v_t),\quad v_b,v_t\in\{H,T,C\}
\]

where H is harmonic, T is temporal, C is combined; the first view controls boundary scoring and the second controls token descriptors.

Resolution is held at 256-sample frames and 64-sample hops. This isolates view selection; frame-scale adaptation is not yet included.

## Calibration objective

\[
U(O)=0.7 F_1^{boundary}(O)+0.3 A_{pairwise}^{token}(O)
\]

Pairwise token accuracy is computed only across distinct evaluator event intervals, mapping each predicted segment midpoint to an event interval. The labels and boundaries are used only for calibration/evaluation, never by the underlying Build 29 signal segmenter.

The winning profile is frozen before evaluating held-out traces. Profiles within 0.015 utility of the winner are retained as plausible alternatives.

## Observed task-conditioned profiles

| Task | Profile | Held-out boundary F1 | Held-out token agreement |
|---|---|---:|---:|
| Frequency-coded | combined / harmonic | 0.770 | 1.000 |
| Amplitude-coded | temporal / temporal | 0.748 | 1.000 |
| Mixed channels | combined / temporal | 0.839 | 0.969 |

All tasks retain near-optimal alternatives. This is a set-valued selection, not proof that the chosen profile is uniquely optimal.

## Limitations

- The calibration task labels are supplied.
- This is supervised task calibration, not unsupervised discovery of intention.
- Synthetic fixtures only.
- Tokenization inherits Build 29's greedy, order-dependent descriptor clustering.
- No adaptive frame size, hop, transfer-function inverse or learned continuous feature weights are included yet.

## Signal-coded control framing audit

The FSK control waveform from the finite signal program was fed through the Build 29 raw signal observer. The temporal view recovered 14/15 symbol boundaries (precision 1.000, recall 0.933, F1 0.966). The harmonic view recovered 8/15, and the combined view 11/15. This provides a bridge from adaptive event observation to instruction decoding. The protocol decoder still uses the declared 512-sample symbol frame and a sync preamble.
