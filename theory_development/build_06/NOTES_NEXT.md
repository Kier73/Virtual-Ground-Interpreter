# Build 07 — Cross-observer invariant discovery

## Motivation

Build 06 produced explicit observer-dependent equivalence classes. Different measurement families partitioned the same candidate set differently:

- Endpoint-only observation collapsed all four path candidates.
- A base-trajectory observer distinguished them using oriented area.
- An SO(3)-rotation observer distinguished the selected four loop classes.
- An S³ phase observer additionally distinguished the antipodal representatives `q` and `-q`.

The next question is whether distinct observers preserve any common relational structure after their individual measurement geometries are constructed.

## Proposed investigation

1. Generate a larger but controlled library of codonic paths: cap loops, wavy loops, concatenated loops, reversed loops, and paths with equivalent endpoints.
2. For each observer, construct an observation signature and an observer-specific dissimilarity matrix (RDM).
3. Compare RDMs with rank correlation and distance-based tests. Do not align raw coordinates when the observers measure different quantities.
4. Compute observable quotient partitions from the admissible probe family. Refine each partition as probes are added; verify that adding probes can split classes but cannot merge previously distinguishable classes under fixed noise laws.
5. Test robustness under codon alias renaming, path reparameterization, quaternion gauge shifts, sampling resolution, and measurement noise.
6. Investigate graph Laplacians and persistent homology only after neighborhood construction is stable. Compare topology over several distance thresholds rather than selecting one convenient threshold.

## Candidate invariants

- Endpoint equivalence under a fixed Hopf projection.
- Signed or unsigned holonomy, depending on observer capability.
- Reversal symmetry: orientation-sensitive quantities should change sign; orientation-insensitive quantities should remain unchanged.
- Antipodal quotient under SO(3) versus pointwise distinction in S³.
- Neighborhood rank ordering shared by different observers.
- Cycle/path relations preserved by codon alias changes.

## Controls and falsification

- Randomize candidate labels and probe aliases.
- Compare against shuffled RDMs and randomly permuted path associations.
- Include observers with deliberately insufficient probe families; they must retain unresolved quotient classes.
- Change one measurement channel at a time to identify which distinction splits a class.
- Repeat at increasing discretization and report convergence, not just a single resolution.
- Preserve the distinction between a base-path area inference (which assumes path history and a known connection) and a direct fibre-phase measurement.

## Exit criteria

Build 07 is useful if at least one relational pattern is recovered independently by multiple observer families, survives harmless codon renaming and numerical refinement, and is absent or weakened in shuffled controls. No universal invariant should be claimed from a small synthetic fixture.
