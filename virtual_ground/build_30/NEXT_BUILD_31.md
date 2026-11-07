# Next Investigation — Build 31

## From a finite signal program to a compositional signal machine

Build 30 demonstrates a finite signal-coded instruction set and signal-domain modular arithmetic. The next step is to test whether signal-coded operations can compose into longer stateful programs while preserving their relational meaning.

Candidate investigations:

1. Add persistent signal state and memory cells represented by stable harmonic/phase patterns.
2. Add conditional branching selected by signal comparisons or matched-filter outputs.
3. Compose operation blocks and verify the homomorphism between program composition and signal transformations.
4. Compare FSK, PSK, orthogonal code and wavelet packet instruction representations.
5. Introduce explicit timing recovery, frame synchronization, error correction and channel estimation.
6. Benchmark sample count, latency, energy proxies and robustness against an ordinary digital implementation of the same task.
7. Investigate whether the interpreter can select a signal code and operation algebra jointly from a task and observer budget.

The key question:

**Can a Virtual Ground compile a task into a signal representation whose native transformations execute the intended logic, while preserving verifiable invariants across composition?**

A finite-state or modular arithmetic machine should be the next bounded target. Universal computation should remain a separate claim requiring an explicit memory/control construction and proof or empirical demonstration.
