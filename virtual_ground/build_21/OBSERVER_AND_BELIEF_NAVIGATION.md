# Observer and Belief Navigation

## Why an observation quotient needs a proof

A sensor map `h:S→Y` creates observation classes:

`[s]_h = {s' : h(s')=h(s)}`

These classes do not automatically form a valid state space for a memoryless controller. For that, states merged by the observation must have compatible action availability and successor classes for every action. This is an action-labelled strong-bisimulation / transition-congruence requirement.

Build 21 performs partition refinement:

1. Start with classes of identical sensor readings.
2. Split states with different enabled actions.
3. Split states whose corresponding actions lead to different current partition classes.
4. Repeat until no further split occurs.

The resulting classes are the coarsest predictive partition refining the sensor's initial observation partition for this finite deterministic model.

## Result

| Observer | Initial classes | Predictive classes | Added splits |
|---|---:|---:|---:|
| FULL `(a,b,p)` | 64 | 64 | 0 |
| LEVELS `(a,b)` | 16 | 64 | 48 |
| TOTAL `(a+b)` | 7 | 64 | 57 |
| TOTAL_PHASE `(a+b,p)` | 28 | 64 | 36 |
| PHASE `(p)` | 4 | 64 | 60 |

In this ground, every complete state is distinguishable by some finite action/observation behavior. None of the partial static sensor maps is itself a Markov, transition-congruent quotient.

That does not make partial observation useless. It means a controller needs memory of observation history, represented here as a belief set.

## Belief update

For belief `B_t`, action `u_t`, and next observation `y_{t+1}`:

`B_{t+1} = { F(s,u_t) : s∈B_t, u_t∈U(s), h(F(s,u_t))=y_{t+1} }`

The policy solver tests only actions legal for every state in the current belief. It groups successor possibilities by the observation that would be received next and recursively requires a successful policy for every branch.

## Same-world sensor comparison

All four observer cases begin from the same actual state `(a,b,p)=(1,1,0)`. The intention is to reach `a=1,b=2`, with phase unrestricted.

| Observer | Initial belief size | Fixed-width label bits | Robust worst-case steps |
|---|---:|---:|---:|
| TOTAL | 12 | 3 | 10 |
| TOTAL_PHASE | 3 | 5 | 8 |
| LEVELS | 4 | 4 | 4 |
| FULL | 1 | 6 | 1 |

The bit counts are `ceil(log2(number of possible observation symbols))` for this finite alphabet. They are not measured communication costs.

The result illustrates task-relative sensor value: separate reservoir levels matter more to this intention than environmental phase alone. Full observation gives the shortest policy, but a partial observer can still achieve the exact target by maintaining a belief and using later observations to branch.

Belief search-node counts in `reports/build_21_results.json` are not monotonic in sensor precision. More sensor detail may reduce uncertainty while creating a different policy-branching/search structure.

## Connection to the “3D observer / 2D chart” analogy

A lower-dimensional observation may omit variables required for one-step prediction. The observer can sometimes recover useful information through a trajectory of observations. It then navigates a history-dependent belief state rather than pretending the current chart coordinate is the complete system state.

The missing dimension has not necessarily disappeared from the system. It is latent relative to the current observation, and its effect is inferred through subsequent transitions.
