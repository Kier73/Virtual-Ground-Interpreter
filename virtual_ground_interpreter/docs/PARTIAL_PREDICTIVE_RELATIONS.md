# Partial predictive relations

## Purpose

The exact observer-relative quotient in VGI is useful when every action selected by the observer has one known transition from every state. A learned Ground is often not in that condition: some state/action pairs have never been observed, and others have conflicting outcomes.

The partial relational method preserves that epistemic distinction. It compares pairs of predictive contexts without pretending an unknown or ambiguous edge is a known edge.

API:

    from vgi import (
        ObserverContext,
        partial_contextual_comparison,
        partial_refinement_series,
    )

    observer = ObserverContext("available-probes", ("HOLD", "PROBE_A"), ("channel_0",))
    series = partial_refinement_series(partial_ground, observer, max_horizon=8)
    comparison = series[-1]
    print(comparison.status("context-a", "context-b"))
    print(comparison.witness("context-a", "context-b"))
    print(comparison.blocked("context-a", "context-b"))
print(comparison.blockers("context-a", "context-b"))

The existing exact functions remain unchanged:

- `refinement_series` and `contextual_quotient` still require every selected edge to be known and singleton.
- `partial_refinement_series` and `partial_contextual_comparison` operate on incomplete or ambiguous Grounds and return pairwise three-valued results.

This is intentionally not represented as an ordinary quotient partition. When some pairs are unresolved, a partition would risk making "not proven equal" look like "proven different".

## Three-valued relation

Let (S) be the declared state set, (A_O) the action probes selected by observer (O), and (pi_O) the selected output-channel projection.

At horizon zero, no actions have yet been observed, so every state pair is equivalent:

[
E_0(x,y)=mathrm{true}.
]

For a state/action pair, an edge is usable only when the Ground has exactly one known outcome. Unknown and ambiguous edges are both non-usable, but remain distinguishable in the Ground itself.

At horizon (h+1), a pair is **distinguishable** if a known action gives different projected outputs, or gives equal outputs and reaches a pair already distinguishable at horizon (h):

[
D_{h+1}(x,y)
=
D_h(x,y)
lor
exists ain A_O:
egin{cases}
pi_O(o_x)
epi_O(o_y), & 	ext{both edges known},\
pi_O(o_x)=pi_O(o_y)land D_h(x',y'), & 	ext{both edges known}.
end{cases}
]

A pair is **equivalent** only when every selected action is known on both sides, emits the same projected output, and reaches a pair equivalent at the previous horizon:

[
E_{h+1}(x,y)
=
orall ain A_O:
operatorname{Known}(x,a)land
operatorname{Known}(y,a)land
pi_O(o_x)=pi_O(o_y)land
E_h(x',y').
]

All remaining pairs are **unresolved**. This includes a pair for which no difference has been observed but at least one required edge is unknown or ambiguous, or a known action reaches an unresolved successor pair.

The three statuses are not interchangeable:

- **equivalent**: bounded agreement has been established for this observer and horizon;
- **distinguishable**: a concrete known action word witnesses a difference;
- **unresolved**: neither claim is supported by the available transitions.

An unresolved pair is not counted as equivalent or distinguishable.

## Monotonicity and witnesses

For a fixed Ground and observer, horizon extension obeys:

[
mathrm{equivalent}ightarrow
{mathrm{equivalent},mathrm{unresolved},mathrm{distinguishable}},
]

[
mathrm{unresolved}ightarrow
{mathrm{unresolved},mathrm{distinguishable}},
qquad
mathrm{distinguishable}ightarrow
mathrm{distinguishable}.
]

A pair cannot become equivalent at a longer horizon after it was unresolved, because the same missing/ambiguous prefix or unresolved successor remains. New evidence may change the Ground and therefore resolve the pair on a new version; the prior comparison object remains immutable and still describes the prior evidence.

Every distinguishable pair retains a shortest observed action word. Ties use the observer's declared action order. Each unresolved pair carries structured blocker provenance:

- `missing_edge`: one or both current state/action edges are unknown;
- `ambiguous_edge`: one or both current edges have conflicting possible outcomes;
- `unresolved_successor`: both current edges are known and outputs match, but their successor pair is unresolved at the previous horizon.

The blocker retains the left and right edge statuses as well as the action. This distinction is useful for attention planning: acquire missing evidence, discriminate competing outcomes, or extend/refine the downstream context.

A known difference on one action is sufficient to distinguish a pair even if another selected action remains unknown. Conversely, an ambiguous edge is not treated as a distinguishing witness just because one of its possible outcomes differs: without a unique retained outcome, this implementation remains conservative and returns unresolved.

## Build 24: delayed-six regression

Build 24 provides a precise positive control. Under all actions and the output channel, (q_0) and (q_1) remain equivalent through horizon four, then become distinguishable at horizon five. The shortest witness is:

[
(mathrm{HOLD},mathrm{HOLD},mathrm{HOLD},mathrm{HOLD},mathrm{PROBE_A}).
]

The same Ground demonstrates observer relativity. An observer that sees only HOLD and PROBE_B cannot see the q0/q5 output distinction; an observer that selects PROBE_A can distinguish that pair immediately.

These results are bounded behavioral statements. They do not imply that q0 and q1 (or q0 and q5) are physically identical states. They say only that the selected observer has, or has not, established a difference within the stated horizon.

## Partial-Ground controls

The test suite includes:

- a two-state cycle with A observed but B missing: the pair remains unresolved for an observer selecting both actions, while an A-only observer can establish bounded equivalence;
- an ambiguous edge with multiple possible outcomes: unresolved, not a guessed distinction;
- a known immediate output difference despite a different action remaining unknown: distinguishable with a one-action witness;
- a two-step witness composed from the prior horizon;
- a new evidence version that resolves an old unresolved pair, while the old comparison remains unchanged;
- equivalence/observer-channel checks against the existing exact quotient on a complete Ground;
- monotone horizon refinement on both partial and complete fixtures.

## What this enables next

This relation closes the conceptual gap between partial Ground induction and observer-relative quotient navigation. It gives the active-attention layer a direct way to identify why a pair cannot yet be merged:

1. an edge has not been observed;
2. an edge has conflicting outcomes;
3. known behavior agrees so far but reaches a pair whose future remains unresolved.

A later probe planner can use these blocked actions and distinguishing witnesses as candidate experiments, then account for action cost, source authorization, side effects, latency, and evidence policy. This method does not itself authorize a probe, create an Encounter, or admit a transition into Ground.

## Limits

- Equivalence is always relative to the selected action set, channel projection, Ground version, and horizon.
- Only unique known transitions support a positive distinguishing witness.
- Ambiguous transitions are conservatively unresolved; disjoint set-valued outcome reasoning is not implemented here.
- The comparison does not infer physical hidden-state identity.
- Tests are authored but have not yet been executed for this change.
