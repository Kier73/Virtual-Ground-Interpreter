# Build 30 Limitations and Evidence Boundaries

1. All adaptive-observer and signal-computation experiments are synthetic controlled fixtures.
2. The adaptive observer uses four labelled calibration traces per task and four separate held-out traces. It is not unsupervised task discovery.
3. The candidate observer family is limited to harmonic, temporal and combined views. Frame size and hop remain fixed.
4. Build 29's segmentation and greedy token clustering are inherited; the latter is order-dependent.
5. The signal-coded program uses 16-ary FSK for opcodes and 8-PSK I/Q phasors for operands. It demonstrates two modular operations over Z/8Z only.
6. Phase-domain arithmetic uses complex sample arrays and per-channel pilots. This is a numerical signal-processing implementation, not a physical mixer or analog computer.
7. Pilot miscalibration causes errors. Phase synchronization and calibration remain explicit system requirements.
8. The noise sweep uses fixed sample length and deterministic noise seeds. It is not a general bit-error-rate study.
9. The FSK complement is a simple detection check, not a full error-correcting code.
10. No TAPS audio or other empirical sensor recordings were processed.
11. No claim is made that signal computation is faster, cheaper or more energy-efficient than digital arithmetic.
12. Universal/Turing-complete signal-native computation is not demonstrated.
