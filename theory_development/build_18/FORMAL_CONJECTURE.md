# The Relational Invariant Atlas Conjecture

## 1. Working statement

A system's observable identity is not assumed to reside in one privileged coordinate system. It is represented by a compatible family of relational invariants, each adapted to a declared transformation symmetry and observer. On overlaps between observer representations, compatibility is expressed by maps that preserve the relevant geometry and intertwine the transformation actions.

The word *atlas* is intentional: multiple charts can describe overlapping parts of a structure without requiring one globally convenient coordinate system.

This is a research conjecture about a useful computational architecture, not a new theorem claiming that every system admits a finite exact invariant representation.

A candidate harmonic "tone profile" for state `s` under observer `a` and symmetry `G` is the collection of representation coefficients:

`Theta_a(s) = { Phi_hat_a(s; pi) : pi in dual(G) }`.

A coarser invariant profile can be formed from irreducible-sector energies:

`E_a(pi; s) = d_pi || Phi_hat_a(s; pi) ||_HS^2`.

The full coefficient matrices retain phase/orientation information; the energy profile is invariant under unitary changes of representation basis but discards within-sector orientation. Thus a scalar "tone" is generally too lossy. A spectrum indexed by irreducible sectors is a better candidate, paired with phase-sensitive coefficients where path or observer distinctions matter. This is mathematical response structure, not an emotional or biological label.

## 2. Declare the objects before searching for invariants

Let:

- `S` be a state space;
- `G` be a declared transformation group acting on `S` (or, for partial/context-dependent transformations, a transformation groupoid `Γ`);
- `O = {O_a}` be a family of observers;
- `P_a` be the admissible probe family for observer `a`;
- `H_a` be a feature or Hilbert space used by observer `a`;
- `Φ_a : S -> H_a` be the observer's representation map;
- `ρ_a(g)` be the representation of transformation `g` on `H_a`.

The observed response is not just the state:

`y_a(s,p) = O_a(p,s)`, for `p in P_a`.

An observer-induced equivalence relation is:

`s ~_a s'  iff  y_a(s,p) = y_a(s',p) for every admissible p in P_a`.

The joint observer relation is the intersection:

`s ~_O s'  iff  s ~_a s' for every observer a`.

Therefore, an invariant is always relative to the declared transformations, probes and observations. A claim of observer-independent identity requires a stated joint observer family that separates the quotient classes of interest.

## 3. Invariance and equivariance are different

A scalar invariant satisfies:

`I(g.s) = I(s)`.

An equivariant representation satisfies:

`Φ_a(g.s) = ρ_a(g) Φ_a(s)`.

Equivariance is often the richer object. It preserves how a representation changes under transformation. Invariants can then be constructed from equivariant quantities using norms, traces, inner products, tensor contractions or group averaging.

If each `ρ_a(g)` is unitary, define the observer's relational kernel:

`K_a(s,s') = <Φ_a(s), Φ_a(s')>_H_a`.

Then:

`K_a(g.s, g.s') = K_a(s,s')`.

This follows directly from equivariance and unitarity. The induced distance

`d_a(s,s') = ||Φ_a(s) - Φ_a(s')||`

is a pseudometric if `Φ_a` is not injective. It becomes a metric on the quotient by the representation's indistinguishable states.

## 4. Compatibility between observer charts

For observers `a` and `b`, a map `T_ab : H_a -> H_b` is an intertwiner when:

`T_ab ρ_a(g) = ρ_b(g) T_ab`

for every transformation in the shared action domain.

If `T_ab` is unitary on the shared observable subspace and `Φ_b = T_ab Φ_a` there, then the two observers have the same Gram geometry on that subspace:

`<Φ_a(s), Φ_a(s')> = <Φ_b(s), Φ_b(s')>`.

This is the precise sense in which two different coordinate descriptions can preserve the same relationships.

A direct proof is one line:

`<TΦ_a(s), TΦ_a(s')> = <Φ_a(s), Φ_a(s')>`

because `T* T = I` on the shared subspace. The intertwining equation separately guarantees that the transformation action is represented consistently in both charts.

Not every pair of observers admits a unitary intertwiner. A projection may discard degrees of freedom. In that case, compare the shared subrepresentation or shared kernels; do not force a false coordinate alignment.

## 5. The executable SU(2) example

Identify the unit 3-sphere with `SU(2)`. Its normalized Haar measure is the standard S^3 volume form divided by `2π²`.

Irreducible representations are indexed by `n = 0,1,2,...`, with spin `j=n/2` and dimension `n+1`. The matrix coefficients form the Peter-Weyl harmonic basis. With the standard convention:

`L²(SU(2)) = closure( direct_sum_n M_n )`

and

`||f||²_2 = sum_n (n+1) ||f_hat(n)||²_HS`.

The spherical Laplacian eigenvalue for the degree-`n` sector is `n(n+2)` (up to the sign convention for `Δ`), with multiplicity `(n+1)²`.

### 5.1 Antipodal quotient

The central element `-I` acts in the spin-`n/2` representation as `(-1)^n I`.

Therefore:

- odd `n` (half-integer spin) changes sign under `q -> -q`;
- even `n` (integer spin) is unchanged.

Functions that descend from `S³` to `SO(3) = SU(2)/{±I}` must be antipodally even. Thus the `SO(3)` quotient removes the half-integer sectors.

### 5.2 Hopf quotient

Use the Hopf map:

`π(q) = q i q^{-1}`.

Its fibres are right multiplication by the subgroup:

`h(β) = exp(i β)`.

A function on the base `S²` pulled back to `S³` is invariant along the entire right `U(1)` fibre. Averaging a spin-`j` representation over that subgroup projects onto its zero-weight subspace.

For `j=n/2`:

- half-integer `j` has no zero weight, so the full fibre average vanishes;
- integer `j` has one zero-weight direction, so exactly one right-weight column survives.

This is more information loss than the antipodal quotient. `SO(3)` removes only the odd-`n` sectors; `S²` removes all nonzero right-fibre weights as well.

This is an observer quotient, not a claim that the discarded fibre coordinate is physically unreal. The base observer simply cannot distinguish it.

There are therefore two distinct quotient steps:

1. `S³ -> SO(3)`: identify only `q` and `-q`; odd-`n` / half-integer-spin sectors disappear.
2. `S³ -> S²` through the Hopf map: identify the entire right `U(1)` fibre; all nonzero right weights disappear, including additional directions within integer-spin sectors.

The second quotient is strictly coarser than the first.

## 6. Paths and time are a complementary branch

For a bounded-variation path `X`, its signature is the sequence of iterated integrals:

`S(X) = (1, ∫dX, ∫dX⊗dX, ... )`.

The full signature is invariant under increasing time reparameterization and characterizes bounded-variation paths up to tree-like equivalence under the standard hypotheses. It therefore preserves ordered path geometry while intentionally discarding traversal speed, initial translation and tree-like excursions.

This suggests maintaining two distinct temporal views:

- `S_geom`: signature of the state/signal path, useful when traversal speed is irrelevant;
- `S_time`: signature of a path augmented by explicit elapsed-time or event-time coordinates, useful when duration and tempo are meaningful.

Clock-free geometry and temporal emission should not be collapsed into one feature vector without recording which invariance has been imposed.

For local event streams, increments remove clock offset; dividing by a robust scale such as the median interval removes uniform clock-rate scale. Keep the removed offset and scale as separate calibration metadata if actual timing matters. Nonlinear drift requires a richer clock model; it is not removed by affine normalization.

The practical representation should therefore retain parallel channels:

- a clock-free path signature for geometry/order when tempo is irrelevant;
- normalized interval and event-order features for local-clock relational structure;
- absolute duration/rate metadata when temporal scale is meaningful.

This prevents an invariance operation from silently erasing the very information a later observer needs.

## 7. Evolving states: Koopman branch

A dynamics map `Φ^t` induces a linear operator on observables:

`U^t f = f o Φ^t`.

This linearizes the action on functions, even when the underlying state dynamics are nonlinear. It is unitary on the usual `L²` space when the dynamics are invertible and preserve the measure; without those conditions, do not assume unitarity or a complete orthogonal eigenbasis.

For partially observed systems, the projection onto observed functions can produce memory terms. A finite instantaneous spectral model may therefore miss hidden-state effects; delay coordinates or memory-aware models may be necessary.

This makes Koopman representations a natural bridge between observer-response geometry and state evolution: the object being decomposed is the evolution of observables, not necessarily the raw state vector. The choice of observable subspace determines which distinctions are visible.

## 8. What is conjectural

The following is the actual open research target:

> For a useful class of systems, can a finite, stable, observer-adapted atlas of harmonic and path representations recover the shared relational state up to the equivalence induced by declared transformations and probes, with a measurable error bound under truncation, noise and observer projection?

A positive result would need to show all of the following:

1. **Separation:** the joint representation distinguishes the quotient states relevant to the task.
2. **Compatibility:** overlapping observers have verifiable intertwiners or comparable invariant kernels.
3. **Stability:** small measurement perturbations do not produce uncontrolled changes in the relational signature.
4. **Compositionality:** concatenated paths/transforms map to composable algebraic objects.
5. **Budget:** the finite representation is cheaper or more effective for the target workload than the direct representation.
6. **Composition:** representation-level composition agrees with composition of the described operations, including order-sensitive/noncommuting transformations.

A universal finite exact signature is not assumed. Completeness, robustness and computational efficiency are separate proof obligations.

## 9. Computational corollary to test

For feature maps with norm bounded by `M`, if observed features have errors at most `ε`, then the corresponding Gram entries obey:

`|<x+δx, y+δy> - <x,y>| <= 2M ε + ε²`.

This elementary bound gives a first stability baseline. More useful system-level bounds must also include conditioning of the observation map, spectral truncation tail, graph-threshold sensitivity and clock-estimation error.

For the SU(2) Peter-Weyl expansion, spectral truncation has an exact `L²` tail identity:

`||f - P_{<=N} f||²_2 = sum_{n>N} (n+1) ||f_hat(n)||²_HS`.

This gives a principled compute/accuracy dial: retain sectors carrying most response energy, while measuring exactly how much `L²` energy was omitted. It does not guarantee that low-energy sectors contain the task-relevant distinctions; that must be tested separately.

## 10. Practical rule

For every new representation, record:

- transformation group/action;
- observer and probe family;
- function/feature space and measure;
- invariant or equivariant quantity;
- exact quotient/lost degrees of freedom;
- reconstruction or completeness conditions;
- truncation and perturbation error;
- composition law;
- computational cost.

A transform without this ledger is a visualization, not yet a verified invariant representation.

## 11. Transformation groups, monoids and groupoids

The harmonic path applies most directly when the allowed transformations form a group with suitable unitary representations. Codonic execution may be more general:

- reversible operations can generate groups;
- partially reversible/contextual transformations may be represented by groupoids;
- irreversible operations naturally form monoids or semigroups.

This distinction matters. A sequence of codons is not automatically a group element. The registry must define operation types, domains, codomains, composition, identity and available inverses. Where inverses do not exist, a Koopman/semigroup action on observables may be the right representation object rather than a unitary group representation.

An arbitrary unitary isomorphism between two Hilbert spaces is not enough to establish shared structure. The map must intertwine the declared actions. This is why the compatibility equation is a central proof obligation rather than a cosmetic coordinate alignment.

## 12. A candidate computational meaning of tone

For a fixed state and probe family, collect the observer's response over the symmetry orbit. Expand the response in irreducible sectors. The resulting sector-energy profile is a candidate *harmonic tone*:

`E_a(pi; s) = d_pi || R_hat_a(s; pi) ||^2_HS`.

It is a relational response profile indexed by symmetries/modes, not a universal scalar attribute. Its interpretation changes when the observer, probes, representation measure or quotient changes. Preserve phase-sensitive coefficients when orientation and path distinctions matter; sector energies alone can identify distinct responses as equal.
