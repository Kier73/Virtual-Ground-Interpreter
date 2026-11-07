# Build 02 — Shape, Movement, Observer, and Geometric Phase

**Project:** Virtual Layer / Codonic algebra / S³ response geometry  
**Status:** exploratory synthetic model  
**Runtime:** Python 3.10+; standard library only

## Purpose

This build tests a distinction suggested by the research discussion:

- **Shape / path:** the oriented curve traced in configuration space.
- **Movement / timing:** the parameterization of that curve over time.
- **Observer:** the measurement map and connection through which the path is read.
- **Intention:** the task-dependent choice of which measured response features matter.
- **Tone:** a candidate name for time-resolved response characteristics, kept distinct from path-level invariants.

The model uses an illustrative connection

`A(x,y) = (-alpha*y/2, beta*x/2)`

and computes `integral A_x dx + A_y dy`. With `alpha=beta=1`, the integral around a closed planar loop equals its signed area. This is a toy geometric model, not a biological locomotion law.

## Experiments

1. Traverse the same ellipse at uniform and nonuniform speeds.
2. Compare path-level geometric phase with temporal phase-rate descriptors.
3. Reverse path orientation.
4. Compare observers with invertible, area-preserving and rank-deficient coordinate projections.
5. Estimate transverse convergence toward a stable limiting cycle.
6. Illustrate why filtering separated high-frequency noise is possible, but does not imply arbitrary noise can be removed without assumptions or signal loss.

## Run

```bash
python -m unittest -v
python vl_shape_dynamics.py > build_02_report.json
```

## Interpretation limits

- The connection is selected for an interpretable first experiment; it is not derived from the Virtual Layer's codon registry or from a physical system.
- Observer projections are controlled mathematical examples, not calibrated biological sensors.
- Intention weights define a task-specific comparison. They do not establish intrinsic meaning.
- A path integral is invariant to monotone reparameterization only when the same oriented geometric path and connection are retained.
- This model does not claim that all meaningful structures share a geometric phase, or that S³ is the unique appropriate state space.
