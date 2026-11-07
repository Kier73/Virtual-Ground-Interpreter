# Virtual Ground Conjecture — Build 20 Scorecard

| Claim | Current status | What is demonstrated | Remaining gap |
|---|---|---|---|
| A ground is a generative operational description | Formalized | State constraints + operation rules regenerate legal transitions | Apply to real software/hardware or richer physical systems |
| Ground differs from a compressed state inventory | Supported in toy | 708-byte serialized rule descriptor regenerates a 648-state, 5,832-edge graph; graph and policy are separately materialized | Byte counts are illustrative and exclude executable code/runtime; broader scaling study needed |
| Multiple grounds can describe one system | Demonstrated in finite fixture | Primitive, coordinate and graph forms agree; macro form expands to primitive operations | Formalize broader weak bisimulation and task-relative equivalence classes |
| Observer determines accessible distinctions | Demonstrated | Full, layout-only and orientation-only observers induce 648, 24 and 27 classes | Add noisy/probabilistic sensors and multiple observers |
| Intention selects an adequate representation | Demonstrated in one task | Layout-only intention can ignore orientation; exact-state intention cannot | Rich multi-constraint objectives and unknown intentions |
| Higher-level navigation can bypass conventional planning steps | Demonstrated as macro abstraction | Two macro commands expand to a legal plan for each target | Macro expansion is not always shortest; native execution advantage not measured |
| Navigation can minimize operations | Verified in finite reversible fixture | BFS yields exact shortest primitive paths; group-relative transform gives start-to-target delta | Scale to larger spaces and weighted/multiobjective costs |
| Resource scarcity changes the useful ground | Demonstrated in one cost example | Different operation costs change the preferred route | Model actual memory, processor, communication and execution budgets |
| Memory stores ground; space is procedural | Implemented in finite fixture | Ground rules regenerate graph, states and navigation catalog | Reliability under incomplete/noisy grounds; chaotic systems |
| Stable state can be treated as observer consensus | Narrow operationalization | Dwell-based stable observation | Multi-observer agreement, uncertainty and persistence under disturbances |
| Irreversible logic changes cause ground shifts | Demonstrated in two toy revisions | Changing action/support rules changes reachable states | General migration maps and versioned live systems |
| Partial and state-dependent operations fit the ground model | Demonstrated in Support-9 | 232 stable states / 774 directed edges; all stable masks are reachable | Richer constraints, environment coupling and partial observation |
| Controlled variables differ from endogenous flow | Formal extension proposed | Not yet implemented as a separate dynamic model | Test control/flow partitions under observer access and resource limits |
| Every multistate logical system has a productive ground | Open | A finite group system and finite partial system | General existence/productivity theorem; distinguish definition from useful acceleration |
| Every possible representation exists as capacity in a ground | Refined conjecture | Selected representations/graphs are compiled from one ground | Need representation compiler that preserves declared invariants over new domains |
| Navigation is constant time across the geometry | Not established | Fixed fixture permits integer addressing and precomputed policy lookup | Storage/precomputation/output costs; no general constant-time theorem |

## Central distinction

A transition system can always be redescribed as itself, so bare existence of a “ground” may be definitional. The research question is whether a ground can be sufficiently generative and task-aware to produce useful coordinates, observation quotients and macro operators that reduce total cost while preserving the distinctions the task requires.
