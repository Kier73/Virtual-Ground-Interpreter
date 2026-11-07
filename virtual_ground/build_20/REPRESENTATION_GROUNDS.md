# Representation Grounds and Resource Trade-offs

Build 20 compares five ways to hold and navigate the same finite toy system.

| Ground | Stored object | Strength | Cost / limitation | Equivalence type |
|---|---|---|---|---|
| Primitive generator ground | Base state, nine operation rules, orientation invariant | Procedurally generates legal transformations | Search may be needed for an optimal path | Reference semantics |
| Coordinate ground | Bijective mixed-radix state address | Direct state indexing; transitions commute with encoding | Address is not itself a shortest route | Strong transition-system isomorphism |
| Materialized graph | All 648 states and 5,832 labelled directed edges | Supports direct graph queries and precomputed policies | Stores the expanded state geometry | Same graph as generator ground |
| Macro ground | `SET_LAYOUT`, `SET_ORIENTATION`, each with primitive expansion | Two high-level stages navigate any state pair in this fixture | Expansion may be longer than a shortest primitive path | Expansion / weak operational equivalence |
| Observer quotient | Layout-only (24 classes) or orientation-only (27 classes) | Drops irrelevant variables for an aligned task | Cannot recover hidden state distinctions | Task-specific quotient equivalence |

## Exact finite fixture

A state is

\[
s=(p,o),\qquad p\in S_4,\quad o\in\mathbb Z_3^4,\quad\sum_i o_i=0\pmod 3.
\]

There are

\[
|\mathcal S|=4!\cdot 3^3=648
\]

valid states. The nine primitive moves are three adjacent swaps and three independent orientation-pair twists, each with its inverse. They generate the full state space. The resulting transformation group is the semidirect product

\[
\left\{o\in\mathbb Z_3^4:\sum_i o_i=0\right\}\rtimes S_4,
\]

with order \(27\cdot24=648\).

The fixture is intentionally not a full Rubik's Cube model. It isolates the core algebra of piece permutation, modular orientation, composition and observability.

## Exact measurements

- 648 valid states; all 648 reachable from the solved state.
- 5,832 directed state/action edges.
- Base-ground graph diameter: 8 primitive operations.
- Exact shortest-path mean from solved to all 648 states: 4.6451 primitive operations.
- Factorized macro expansion mean: 5.0000 primitive operations.
- The factorized route differs from the exact shortest distance for 230 of 648 targets.
- The factorized navigation uses an average of 1.9213 nonempty high-level commands (maximum two), but those commands expand to an average of five primitive operations.
- Layout-only observer: 24 equivalence classes.
- Orientation-only observer: 27 equivalence classes.
- Full observer: 648 equivalence classes.

## Why the macro example matters

For any start/target pair, the factorized ground first rearranges the piece layout, then corrects orientation. The two high-level commands are:

1. `SET_LAYOUT(target.permutation)`
2. `SET_ORIENTATION(target.orientation)`

Each command expands into a legal primitive sequence and is verified by replay. This shows how a higher-level description can bypass a long sequence of *planning decisions* without pretending that the underlying primitive actions disappeared.

A genuinely faster physical execution requires a target interface that can perform the macro as a native operation. A purely virtual macro reduces representation/command depth, not necessarily mechanical action count.

## Intention changes the required space

For a layout goal, all 27 orientation configurations over the same piece arrangement are equivalent. The 648-state ground reduces to 24 classes. A layout-only observer can therefore satisfy a layout intention without reconstructing hidden orientations.

For an exact-state intention, that same quotient is inadequate. It has removed distinctions required by the task. The correct ground is not simply the smallest one; it is the least costly one that preserves the intended distinctions.

## Resource-weighted navigation

For state code 5, uniform primitive costs select:

`TWIST1+ ; TWIST2-` (2 actions, cost 2).

When twists cost 4 and swaps cost 1, the preferred route changes to:

`SWAP23 ; TWIST1+ ; SWAP23` (3 actions, weighted cost 6).

The two routes reach the same target. This concretely demonstrates that navigation depends on the observer/resource cost profile, not merely on geometric distance in an unweighted graph.

## Ground revision

The orientation-locked version removes all six twist operations and increments the ground version. Only the 24 zero-orientation permutation states remain reachable from the solved state. This is a change to the generative logic, not a coordinate relabeling.


## Partial, irreversible ground

The accompanying `Support-9` fixture represents a Jenga-like support system as a partial directed transition graph. Unlike the rotor puzzle, it is not a group: actions remove blocks, are state-dependent and are irreversible. It has 232 reachable stable states and 774 directed edges. Revising one support rule creates a new ground version with 200 reachable states and 646 edges. A level-count observer is not transition-congruent because equal layer counts can hide different support identities and legal actions.


## Serialized footprint and precomputed navigation

The 708-byte ground descriptor is configuration data and depends on the shared transition interpreter. The materialized graph contains 5,832 edges and occupies 182,701 serialized JSON bytes; the exact shortest-policy table has 648 entries and occupies 51,376 serialized JSON bytes. The coordinate and macro schemas are smaller still, but they describe rules and rely on the same interpreter. These payload counts illustrate the difference between a procedural ground and materialized derived spaces; they are not a full implementation-size or runtime-memory comparison.

A `GroundNavigator` precomputes the 648 shortest relative transformations from the identity. Given start and target states, it computes the relative transform and uses that finite policy table. Querying avoids replaying the path that originally produced the start state. The path still has to be emitted and, unless available natively, executed as primitive actions.
