# Build 23 Experiment Protocol

1. Generate each hidden ground from a parameterized constructor unavailable to the learner.
2. Enumerate valid states and the three controlled operations.
3. Place all HOLD transitions in training to expose environmental laws, and deterministically withhold a subset of active-operation transitions.
4. Infer a program using only transition records and the bounded grammar.
5. Evaluate training and held-out transitions.
6. Exhaustively compare the inferred program with every state/action transition in the finite fixture (evaluation only; the learner does not receive these labels).
7. Compute mass-balance residuals from the inferred program.
8. Audit observer projections for transition congruence.
9. Remove saturation evidence and verify that capacity becomes a lower bound.
10. Remove a necessary operation intervention and verify that inference fails closed.
11. Test grammar expansion from source residue modulus 3 to 4.
12. Serialize, reload and re-evaluate the induced ground program.
13. Compare fingerprints across an environmental law revision.

All generated data are synthetic and deterministic. The full-domain comparison uses the hidden fixture only as a test oracle.
