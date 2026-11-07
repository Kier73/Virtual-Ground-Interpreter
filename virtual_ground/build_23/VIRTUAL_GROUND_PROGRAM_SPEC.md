# Executable Virtual Ground Program Specification

A serialized program contains:

```json
{
  "capacity": 4,
  "capacity_status": "exact_from_observed_saturation",
  "period": 4,
  "inflow": {"mode": "lookup", "values": [1, 0, 0, 1], "params": []},
  "demand": {"mode": "lookup", "values": [0, 1, 0, 0], "params": []},
  "phase_next": {"mode": "permutation_stride", "values": [1, 2, 3, 0], "params": [1]},
  "transfer": {"modulus": 1, "values": [[1], [1], [1], [1]]}
}
```

The example is illustrative. The exact generated specification is available in `reports/ground_program_spec_example.json`.

## Evaluation contract

Input:

- a valid state `(a,b,phase)`;
- one operation from `HOLD`, `A_TO_B`, `B_TO_A`.

Output:

- the deterministic next state `(a',b',phase')`.

The evaluator applies the inferred phase schedules, operation law, finite source/destination availability and capacity clipping. `compile_program_spec(spec)` reconstructs the executable in-memory program from JSON-compatible data.

A specification is not an execution certificate for an arbitrary physical system. It is a learned finite model whose scope is delimited by its state schema, operation grammar, evidence and held-out validation.
