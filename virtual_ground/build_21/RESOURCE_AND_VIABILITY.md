# Resource-Aware Navigation and Viability

## 1. Pareto navigation

A route has a vector cost rather than one universal scalar:

`c(path) = (time, energy, communication)`

A route dominates another only if it is no worse in every cost and strictly better in at least one. Build 21 preserves nondominated route labels and lets an execution profile choose among them.

For the fixed task:

- start: `(0,1,0)`;
- target: `(1,2,3)`;
- environmental forcing remains active throughout the route.

Two nondominated solutions:

| Route | Time | Energy | Communication |
|---|---:|---:|---:|
| Faster | 7 | 10 | 4 |
| Lower-energy | 11 | 9 | 3 |

The lower-energy route uses eight HOLD steps before transferring three units A→B. It waits for the exogenous inflow schedule to build A's inventory. The faster route uses a B→A move and then three A→B moves.

The resource profile chooses the route, not the ground's legal transformation rules. If a hard resource budget makes every route infeasible, the task is not executable under that profile even though the logical target remains reachable without that restriction.

## 2. Controlled viability

Safety predicate:

`Q = { (a,b,p) : a≥1 and b≥1 }`

Computed kernels:

| Kernel | States |
|---|---:|
| Controlled viability kernel | 35 |
| HOLD-only autonomous kernel | 0 |

The controlled kernel includes exactly those safe states from which at least one legal action can keep the system in the safe set indefinitely. A witness policy is exported in `reports/viability_policy.csv`.

This turns “banks versus flow” into a formal control question: which regions of the state space remain viable under active control, and which remain viable under the environment alone?

## 3. Operational ground restriction

Separate:

- **base ground** — all logically legal operations and transition laws;
- **resource profile** — time, energy, communication, memory and computation limits;
- **effective operational ground** — base-ground actions and routes still executable under the profile.

A changed preference weight selects another Pareto route. A binding budget can remove route feasibility. Neither alone rewrites the underlying state-transition law, but both change the operational possibilities accessible to an observer/controller.
