# Build 19 representation comparison

| Representation | Input | Preserves / exposes | Deliberately loses | Main limitation |
|---|---|---|---|---|
| SU(2) endpoint harmonics | Final quaternion | Endpoint and rotational representation content | Path history | Finite band may omit sectors |
| SO(3) endpoint harmonics | Final rotation | Rotation independent of lift sign | Antipodal lift distinction | Cannot distinguish same-endpoint paths |
| Hopf endpoint harmonics | Hopf base endpoint | Base orientation | Right-fibre phase | Cannot recover fibre coordinate |
| S3 path signature | Quaternion trajectory in R4 | Ordered path geometry, iterated integrals | Tree-like excursions; elapsed-time reparameterization | Truncation and sampling error |
| SO3 path signature | Rotation-matrix trajectory in R9 | Rotation-path history | Quaternion lift sign | Ambient embedding and truncation |
| Hopf path signature | Hopf-base trajectory in R3 | Base-path history | Entire right-U(1) fibre at each time | Finite projected sampling |
| Observer kernel | Any selected feature map | Pairwise similarity and induced pseudometric | No extra observation beyond features | Kernel inherits feature-map blind spots |
| Joint endpoint/path kernel | Endpoint + path feature maps | Combined endpoint and trajectory geometry | Declared observer quotients and signature equivalences | May duplicate endpoint information |

## Selected pair outcomes

| Pair | S3 observer | SO(3) observer | Hopf observer | Explanation |
|---|---|---|---|---|
| Same endpoint, different route | Distinguishes | Distinguishes | Distinguishes | Higher path-signature levels detect the route difference |
| Fibre-shifted lift, same Hopf path | Distinguishes | Distinguishes | Identifies | Hopf quotient removes fibre phase |
| Antipodal path | Distinguishes | Identifies | Identifies | SO(3) and Hopf views factor through the antipodal quotient |
| Same geometry, different time labels | Identifies in geometry-only view | Identifies in geometry-only view | Identifies in geometry-only view | Time-augmented signature distinguishes the timing allocation |
| Exact forward/reverse excursion | Identifies | Identifies | Identifies | Tree-like equivalence of path signatures |

All examples are deterministic synthetic fixtures. “Identifies” means zero or numerical-zero feature distance in the tested finite implementation, not a universal theorem about every possible representation.
