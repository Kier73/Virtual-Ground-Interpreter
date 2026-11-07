# Virtual Ground Dynamics — Banks, Control, Flow, and Environment

## 1. Operational ground

Represent a ground version as:

`G_v = (X, U, E, F, H, I, B, C)`

where:

- `X`: admissible endogenous system states;
- `U(x)`: control operations enabled in state `x`;
- `E`: exogenous/environment state space;
- `F`: state transition law;
- `H`: environmental evolution and forcing law;
- `I`: invariants and admissibility constraints;
- `B`: structural boundaries or capacities;
- `C`: resource-cost model / operational cost assumptions.

For the Build 21 fixture, `x=(a,b)` stores volume in two reservoirs and `p` is a four-phase environment state. The full state is `s=(a,b,p)`.

## 2. Banks, controls, and flow

| Role | Fixture variables | Interpretation |
|---|---|---|
| Structural banks | capacity, action preconditions, mass balance, phase law | Define what states and operations are admissible |
| Controlled | gate command `u` | The controller selects a transfer command |
| Endogenous | `a`, `b`, actual transfer, spill, unmet demand | Values produced by state/action/environment interaction |
| Exogenous | phase `p`, scheduled inflow and demand | Environmental inputs not selected by the gate controller |

A useful refinement: the *law* that maps environment phase to inflow/demand is part of the ground description; the realized current phase and forcing values are exogenous variables at runtime.

## 3. Transition law

Capacities are `0 ≤ a,b ≤ C`, with `C=3`.

Actions are `HOLD`, `A_TO_B`, and `B_TO_A`. A transfer is enabled only when its source has at least one unit and destination has room.

Let `u ∈ {-1,0,+1}` denote requested transfer from A to B (`+1`), B to A (`-1`), or hold (`0`). A valid action first changes the stored distribution:

`a_c = a - u`

`b_c = b + u`

Then the environment acts at phase `p`:

`a' = min(C, a_c + r[p])`

`spill = max(0, a_c + r[p] - C)`

`b' = max(0, b_c - d[p])`

`actual_demand = b_c - b'`

`unmet_demand = max(0, d[p] - b_c)`

`p' = phase_next[p]`

Fixture schedules:

`r = (1,0,0,1)`

`d = (0,1,0,0)`

The exact mass-balance invariant is:

`a' + b' = a + b + r[p] - actual_demand - spill`

Gate transfer cancels because it redistributes rather than creates or destroys volume.

## 4. Intention and navigation

An intention is a target predicate, not necessarily a single state:

`J: X × E → {true,false}`

Examples:

- inventory target: `a+b=3`;
- distribution target: `a=1 and b=2`;
- safety target: `a≥1 and b≥1`.

A controller is a policy over information available to the observer:

`π: belief_state → U`

For partial observations, the belief is the set of all full states compatible with the observation history. A robust policy requires the chosen action to be legal in every state in the current belief and to reach the intention for every possible branch.

## 5. Controlled versus passive stability

For a safe set `Q`, the controlled viability kernel is the greatest subset `K⊆Q` satisfying:

`∀s∈K, ∃u∈U(s): F(s,u)∈K`

The HOLD-only invariant kernel instead satisfies:

`∀s∈K_hold: F(s,HOLD)∈K_hold`

The difference identifies safety sustained by active control rather than passive system evolution.

## 6. Virtual Ground shift

A base ground shift occurs when a structural law changes: state admissibility, enabled operations, transition equations, environmental evolution law or declared invariants.

Ordinary state evolution is not a ground shift. Neither is merely choosing another sensor representation or cost preference.

However, a binding resource constraint may create an *effective ground restriction*: some operations remain logically valid but are no longer executable under the current resource budget. Keep the base logic and the operational restriction versioned separately.
