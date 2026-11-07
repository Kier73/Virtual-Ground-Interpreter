# Build 06 — Active observation on S³/Hopf geometry

## Main question

Can an intention-conditioned observer choose geometric probes that distinguish paths which are equivalent in a projected base space but differ in their S³ lift or accumulated holonomy?

## Preserve from Build 04

- Unit-quaternion operations and normalization.
- Hopf projection `pi(q) = q k q^-1`.
- Fibre equivalence and horizontal lifting.
- S³ distance versus SO(3) rotational distance.
- Closed-loop holonomy and reversal tests.

## Add from Build 05

- Observer-specific projection and noise model.
- Target maps representing intention.
- Expected information gain about the target.
- Probe cost and robust score.
- Bayesian posterior update after each measurement.
- Stop when target uncertainty is sufficiently reduced.

## Candidate geometric probes

1. Base-space coordinate measurement.
2. Fibre-phase measurement.
3. Local tangent displacement along selected directions.
4. Loop-area / holonomy measurement.
5. Reverse-path comparison.
6. Antipodal comparison with explicit S³ versus SO(3) semantics.

## Core experiment

Construct path A and path B with the same Hopf-base endpoint but different holonomy. Begin with a base-only observer that treats them as equivalent. Give the active observer a choice of probes with different costs and noise. Test whether it selects a fibre-sensitive measurement when the intention is to distinguish the paths, and avoids spending on fibre measurements when the intention concerns only the base endpoint.

## Required controls

- Random and fixed-probe baselines.
- Probe cost normalization.
- Noise-scale sweep and confidence intervals.
- Reparameterization of the same path.
- Path reversal.
- Initial fibre representative changes.
- Quaternion sign changes (`q` versus `-q`).
- Registry alias changes.
- Verify probes do not mutate the underlying path, base endpoint or algebraic law.

## Falsification conditions

The proposed observer layer is not supported if:

- it cannot distinguish base-equivalent paths when given a fibre-sensitive probe;
- it reports distinction from a base-only observation that contains no distinguishing information;
- its conclusions change under a harmless codon alias change;
- it fails to preserve the Build 04 holonomy and gauge controls;
- active selection does not outperform random or repeated uninformative probing when the model actually contains discriminative information.

## Deliberately deferred

- Human emotional tone labels.
- Claims of physical resonance in the abstract seed space.
- Arbitrary-dimensional universal observer geometry.
- Integration with SHA-256 or Feistel addresses as semantic metrics.
