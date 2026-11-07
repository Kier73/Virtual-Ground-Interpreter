# Boundary Discovery and Motif Segmentation

## Input contract

The acquisition interface supplies one continuous token sequence per trace and sparse observation checkpoints with offsets. An offset means “number of tokens consumed”; it is not an operation boundary. The learner is not given hidden segment offsets.

## Candidate generation

Enumerate exact contiguous n-grams with a bounded length. Keep motifs with minimum occurrence count and cross-trace support. Shorter motifs fully embedded in longer recurrent motifs are retained in an audit ledger but excluded from segmentation to avoid double counting.

## Segmentation objective

At each token offset, choose either:

- leave the token unassigned as background; or
- select a candidate motif beginning at that offset and advance to its end.

The dynamic program returns the top-k non-overlapping parses. Each motif receives a score based on length and training support. The score is a search heuristic, not a probability.

If the top two parses are within a declared score margin, the result is `ambiguous`. The difference region and candidate signatures are reported. Ambiguous traces are not used for operation-effect fitting.

## Known ambiguity

A target sequence `a,b,c` may represent one `ABC` operation or `AB` followed by background `C`. If both motifs are independently recurrent, the stream alone may not determine the boundary. A checkpoint inside the candidate boundary or an intervention may resolve it; otherwise the correct result is ambiguity.

## Negative control

The permutation test preserves each trace's token inventory and length but shuffles order. The maximum count over all candidate motifs and all null trials is used as a conservative family-wise threshold. This guards against frequent n-grams produced solely by frequent tokens.

This is not a formal guarantee for nonstationary natural streams. The null should eventually be adapted to local token-rate and context constraints.

## Limits

This build does not tokenize raw continuous signals. It starts after an event encoder has produced opaque token IDs. Exact n-gram mining is conservative and sensitive to edits. Future builds should investigate approximate motifs, variable duration, local rhythm, spectral/temporal features and multi-channel alignment.
