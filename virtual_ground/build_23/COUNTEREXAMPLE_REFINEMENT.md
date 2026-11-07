# Counterexample-Driven Ground Refinement

## Demonstration

The last synthetic ground uses a transfer quantum depending on source level modulo 4:

\[
Q(p,a)=1+(a\bmod4)\quad\text{with residue }3\mapsto1
\]

The initial grammar searches source residue moduli through 3. It cannot reconcile the observed uncensored transfers and correctly rejects the training set with an explicit `richer rule or more probes` error.

After the grammar is expanded to modulus 4, the learner induces:

\[
Q(p,a)= (1,2,3,1)_{a\bmod4}
\]

for each environmental phase. The reloaded program exactly predicts held-out transitions and every state/action pair in the finite domain.

## Refinement loop

\[
\text{candidate program}
\rightarrow\text{counterexample}
\rightarrow\text{residual classification}
\rightarrow\text{grammar extension}
\rightarrow\text{re-synthesis}
\rightarrow\text{held-out verification}
\]

Potential counterexample classes:

- constant law rejected, phase-dependent law fits;
- phase-only law rejected, source-level residue law fits;
- residue law rejected, a larger modulus fits;
- schedule lookup fits samples but fails new phase probes;
- one-off sensor anomaly is inconsistent with all laws and should not trigger ground revision;
- repeated independent residuals support a new ground version.

This build implements the first three classes for discrete finite schedules and operation quanta. It does not yet implement a generic residual classifier or automatic search over arbitrary expression trees.
