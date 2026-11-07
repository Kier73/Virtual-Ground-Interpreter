# Unknown Transitions and Evidence Certificates

An incremental ground must distinguish three different facts:

1. A transition has been observed consistently.
2. A transition has been observed inconsistently.
3. A transition has not been observed.

Build 26 represents these as `known`, `ambiguous`, and `unknown` respectively.

It does not default an unobserved edge to a self-loop, identity, no-op, or inferred neighbour. Any such default would turn absence of evidence into a generative rule.

The replay certificate proves only that every retained event is compatible with the known transition table, or explicitly unresolved where no unique edge exists. It is not a conformance proof for arbitrary future action words. A future build needs independent held-out future observations, risk-aware active probing, and a bounded equivalence statement over a declared test language.

Context horizon increases are candidate model refinements. They are not automatically ground revisions: an apparent collision may have resulted from insufficient history, a late sensor, corrupted measurement, a new latent variable, or true structural change. Build 26 preserves this ambiguity instead of automatically committing a new ground.
