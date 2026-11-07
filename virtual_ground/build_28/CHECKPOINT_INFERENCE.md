# Sparse Checkpoint Effect Inference

The stream is observed at sparse token offsets. Checkpoint intervals are not aligned to hidden operation boundaries.

For interval `k`:

- `y_k` is the observed vector difference between adjacent checkpoints;
- `n_kj` counts inferred motif `j` wholly contained in the interval;
- any interval containing a motif that crosses either checkpoint is excluded.

The learner constructs:

\[
Y=X\Beta
\]

The solver performs exact rational row reduction. It reports one of:

- `unique`: full column rank and a consistent solution;
- `underdetermined`: more than one coefficient vector fits the evidence;
- `inconsistent`: no exact coefficient vector fits;
- `no_equations`: no checkpoint interval can be attributed safely.

Only unique integer-valued effects are compiled as candidate operation effects. Zero vectors are recorded as recurrent motifs with no measured state effect. This does not prove that such a motif has no effect on unobserved variables.
