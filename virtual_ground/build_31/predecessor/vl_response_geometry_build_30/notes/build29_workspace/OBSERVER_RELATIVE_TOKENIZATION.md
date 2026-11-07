# Observer-Relative Tokenization

The token vocabulary is deliberately conditional on a view.

| View | Primary retained distinctions | Deliberately collapsed distinctions |
|---|---|---|
| Harmonic | Spectral shape, band distribution, multiscale detail | Constant positive gain changes (approximately) |
| Temporal | Relative envelope level, within-event variation, crest structure | Some spectral rearrangements with similar envelopes |
| Combined | Both spectral and temporal differences | Only distinctions omitted by both selected feature sets |

Token labels (`evt_001`, etc.) are arbitrary cluster identifiers. They are not semantic labels, operation names, or universal event identities.

Two signals can be equivalent under one observer and distinct under another. The amplitude-only fixture is an explicit example: harmonic tokenization maps all four amplitudes to one token; temporal tokenization separates them into four tokens.

For multiple aligned channels, descriptors are concatenated in channel order after channel-specific baseline centering. Each sensor's coordinate block is retained rather than averaged away. The tokenization algorithm is a deterministic greedy online centroid update. Consequently, cluster assignments depend on stream order and tolerance. It is not yet a canonical quotient construction. A future build should compare it against order-independent clustering, metric-learning and kernel-based partitions, while retaining reproducible identifiers.
