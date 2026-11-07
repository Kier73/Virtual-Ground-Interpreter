# Ground Versioning and Migration

## What increments a ground version?

A new version is required when the generative logic changes, including:

- admissible state constraints or capacity;
- action definitions or action preconditions;
- transition equations;
- phase/environment evolution law;
- declared invariants or stability rules.

A state moving through a fixed transition law does not create a new version. Neither does changing which sensor is consulted or changing the cost weights used to select a route.

## Migration results

| Revision | Old encodings | Directly valid in new ground | Not directly mappable |
|---|---:|---:|---:|
| Capacity 3→4 | 64 | 64 | 0 |
| Capacity 3→2 | 64 | 36 | 28 |
| Inflow law revision | 64 | 64 | 0 |

Capacity expansion embeds old states in a larger state space. Capacity reduction invalidates states with a level above the new capacity; a separate lossy transfer/spill rule is needed to migrate them. Changing environmental forcing preserves the state encoding but changes future trajectory semantics.

A robust migration record should preserve:

1. source ground version;
2. destination ground version;
3. mapping function or partial mapping;
4. states that map directly;
5. states requiring normalization or loss;
6. invariants preserved and violated;
7. replay semantics for stored trajectories.

## Base versus effective ground

A resource shortage can make a valid operation inaccessible without changing its mathematical definition. Represent this as an operational restriction profile layered over the base ground. If the system permanently removes an actuator or changes the operation's preconditions, that is a base-ground version change.
