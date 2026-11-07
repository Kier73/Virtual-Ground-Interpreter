# Representation atlas: what each perspective preserves

| Perspective / system | Transformation symmetry | Adapted representation | Preserved structure | Important loss or condition |
|---|---|---|---|---|
| Translation on `R` or `T` | additive shifts | Fourier characters | translation action becomes phase multiplication; Plancherel geometry | phase is lost by magnitude-only spectra |
| Dilation on positive time | multiplicative scaling | Mellin transform / log-time Fourier | dilation becomes translation | absolute scale requires a separate channel |
| Localized signal events | time-frequency shifts | STFT / Gabor | local timing and frequency content | frame, window, redundancy and uncertainty trade-offs |
| Multiscale transients | scale/translation | wavelets | localized scale structure | invariance depends on pooling and chosen wavelet family |
| Binary XOR group | `(Z/2)^n` translation | Walsh-Hadamard characters | exact group-character decomposition | does not encode arbitrary arithmetic multiplication |
| Finite cyclic arithmetic | cyclic shifts | DFT / NTT | exact cyclic convolution algebra | NTT requires suitable roots of unity and invertible normalization in the coefficient ring |
| Compact non-abelian group | left/right group action | Peter-Weyl matrix coefficients | irreducible representation blocks and Plancherel energy | coefficients are matrices, not scalar frequencies |
| Unit quaternions / S3 | `SU(2)` left/right multiplication | Wigner-D / SU(2) harmonics | rotational composition, spin sectors | low-order truncation loses fine structure |
| Hopf base observer | right `U(1)` fibre action | S2 spherical harmonics | fibre-invariant structure | fibre phase is deliberately discarded; only zero right-weight modes remain |
| Event graph | node permutation / graph isomorphism | graph Laplacian spectrum | spectrum invariant under relabeling | cospectral non-isomorphic graphs exist; spectrum is not a complete identifier |
| Ordered path | increasing reparameterization | path signature | iterated ordered interactions | translation and tree-like excursions are quotiented; truncation loses higher-order terms |
| State evolution | time evolution `Φ^t` | Koopman operators | linear action on observables | unitary only with suitable measure-preserving invertible dynamics; continuous spectrum and hidden-state memory matter |
| Observer response | observer-specific probes | pullback metrics, Gram kernels | distinctions and distances visible to that observer | null directions create pseudometrics; depends on probe coverage |
| Codonic transformation chain | composition of operations | group/monoid representation | operation order and composition laws | only if codon semantics and algebraic action are actually defined |
| Weight / meaning spaces | task- and observer-preserving transformations | quotient geometry, kernels, equivariant maps | equivalence classes and stable relational geometry | parameter-space symmetries can be non-identifiable and task-dependent |

## Unifying workflow

1. Declare the state object and the allowed transformations.
2. Declare the observer, probes, and what it cannot see.
3. Choose a representation adapted to the action (characters, irreducibles, path signature, graph modes, Koopman observables).
4. Separate equivariant coordinates from invariant contractions.
5. Compare representations using intertwiners on shared subspaces or compare their invariant kernels.
6. Test separation, stability, composition and computational cost.

The desired outcome is not one transform that replaces all others. It is a minimal compatible atlas for the workload.

## Arithmetic and RNS note

For a prime modulus `p`, an `N`-point number-theoretic transform over `F_p` needs a primitive `N`th root of unity; a sufficient common condition is `N | (p-1)`. The inverse also requires that `N` be invertible modulo `p`, which follows when `N | (p-1)`. For an RNS system, every CRT modulus must support the required root and inverse normalization. The resulting transform is an exact invertible linear map over a finite ring/field; it is not automatically a unitary map for a positive Hilbert norm.

## Why arbitrary Hilbert-space isomorphisms are not enough

Any two separable infinite-dimensional Hilbert spaces are abstractly unitarily isomorphic. That existence statement carries little system-specific information. The useful structure comes from mapping the *actions* as well: a compatibility map must intertwine the operators/representations selected by the declared symmetry.
