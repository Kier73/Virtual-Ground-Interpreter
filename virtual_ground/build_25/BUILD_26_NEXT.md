# Proposed Build 26 — Incremental Online Ground Induction

Build 25 tracks an unknown current context using an existing predictive machine. The next step is to learn or revise the transition structure itself from a non-resettable stream.

## Proposed capabilities

1. Maintain provisional context and transition hypotheses online.
2. Separate unknown initial context from genuinely new contexts.
3. Add transition evidence without replaying the complete stream.
4. Distinguish missing observations, output noise, transition-law drift and new latent context.
5. Use safe, intention-relevant probes to distinguish competing online models.
6. Produce a versioned candidate ground with held-out or future evidence requirements.
7. Preserve observer quotient distinctions and unidentifiable variables.

## Central challenge

Without reset or a trusted equivalence oracle, a transition that has not been exercised is not known. The system must represent untested transitions as unknown rather than assume a default. Incremental ground induction should therefore use partial transition tables with confidence/evidence annotations, not a falsely complete deterministic machine.

## Proposed object

\[
\mathfrak G_t=(Q_t,A_t,\Delta_t,\Lambda_t,E_t,U_t,V_t)
\]

where:
- `Q_t`: current predictive context hypotheses;
- `A_t`: observed/proposed operation alphabet;
- `Δ_t`: partially known successor relation;
- `Λ_t`: partially known output relation;
- `E_t`: accumulated evidence;
- `U_t`: unresolved transition/context uncertainty;
- `V_t`: version lineage.

The objective is to refine this object only when evidence supports a distinction, while retaining counterexamples and unknown regions.
