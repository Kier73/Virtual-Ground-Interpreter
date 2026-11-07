# Virtual Ground Induction

## Formal target

A Virtual Ground is treated as a generative operational specification:

\[
\mathfrak G=(X,U,E,F,\mathcal I,\mathcal O,\mathcal J,\mathcal C,\nu)
\]

where:

- `X`: state variables and their domains;
- `U`: controlled inputs / operations;
- `E`: exogenous context and forcing variables;
- `F`: state-transition law;
- `I`: invariants and legal-state constraints;
- `O`: observer mapping and available measurements;
- `J`: intention/task predicate;
- `C`: resource/cost model;
- `ν`: ground version / schema identity.

The distinction from a state graph is generative: a graph is a materialized collection of transitions; the ground is the rule system from which those transitions can be produced.

## Inference from observations

For records `r_i=(x_i,u_i,y_i)` with `y_i=F(x_i,u_i,e_i)`, the induction pipeline is:

1. Validate the observed transition schema and action coverage.
2. Use HOLD/no-control transitions to isolate environmental schedule effects.
3. Infer phase progression from repeated context transitions.
4. Recover inflow and demand schedules from boundary/interior observations that avoid clipping ambiguity.
5. Use controlled transfer interventions to infer operation response.
6. Search the current rule grammar for an exact operation law.
7. Construct a generative transition program.
8. Check training, held-out and exhaustive finite-domain transitions.
9. Audit conservation and observer quotient compatibility.
10. Serialize the inferred ground with a stable fingerprint.

## Identifiability conditions

A parameter is only identified when the observations distinguish it from alternatives.

Examples:

- No gate intervention means transfer quantum is not identified.
- No observation at a saturated boundary means capacity is only a lower bound.
- Missing phase coverage prevents a complete periodic schedule from being inferred.
- A total-only observer can identify inventory while failing to identify exact reservoir distribution and may not be transition-congruent.
- Multiple laws may agree on the sampled traces but diverge on held-out interventions.

The induction engine fails closed when required evidence is absent or inconsistent. It does not silently choose a convenient law.

## The role of intention

A task may need only an observer quotient or derived invariant, while a generative ground needs a transition-congruent representation or a belief state that retains missing distinctions.

Therefore:

\[
\text{task sufficient} \not\Rightarrow \text{transition sufficient}
\]

A representation may answer a specific goal while being inadequate as a complete computational ground.

## Ground revision

A revised ground is proposed when an independently validated observation cannot be explained by the current transition law and a richer law explains it. Distinguish:

- state-coordinate extension;
- parameter revision;
- environmental law revision;
- operation law revision;
- new state variable / new latent context;
- observer change;
- cost-model change.

A parameter or transition-law change can preserve state encoding while changing future dynamics. A new state variable may require schema migration.
