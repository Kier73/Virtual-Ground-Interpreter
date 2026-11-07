# Representation Map — From Relational Geometry to Harmonic Coordinates

## 0. Governing rule

Do not choose a transform because a signal appears oscillatory. First identify the action or symmetry whose relationships should be preserved. Then select a representation adapted to that action.

A useful representation is a map

\[
T:\mathcal H_A\rightarrow\mathcal H_B
\]

whose important property is explicit: unitary/isometric, equivariant, intertwining, or otherwise structure-preserving. A coordinate change alone is not evidence of a useful invariant.

For a group action \(\rho:G\to U(\mathcal H)\), a harmonic decomposition resolves the space into invariant components / irreducible representations of \(G\). In an abelian group these components are scalar characters. For non-abelian groups they are generally matrix-valued.

## 1. The conversation's perspectives and their paths to harmonics

| Starting object / vantage | Relationships observed | Natural symmetry or operator | Candidate representation | Useful invariants | Main caution |
|---|---|---|---|---|---|
| Acoustic / vibration waveform | Translation, modulation, phase, periodicity | Translation group on \(\mathbb R\) | Fourier / Plancherel | Inner products, energy, frequency response, phase relations | Fourier magnitude alone discards phase; stationarity assumptions may obscure transients |
| Radial waveform / isotropic spatial field | Rotational symmetry and radial scale | Rotations in \(\mathbb R^n\) | Spherical harmonics plus Hankel transform | Angular degree and radial frequency | Reduces to a radial model only when rotational assumptions are justified |
| Gaussian / oscillator response | Phase-space displacement and oscillator evolution | Harmonic-oscillator / Heisenberg-Weyl action | Hermite basis and Bargmann-Fock transform | Mode number, analytic structure, oscillator spectrum | Gaussian weighting and phase conventions are part of the transform |
| Local event stream | Order, recurrence, relative intervals | Positive affine time group \(\mathbb R\rtimes\mathbb R_{>0}\) | Fourier for shifts; Mellin for scale; wavelets for joint shift-scale | Normalized interval shape, scale-space coefficients, recurrence | Nonlinear clock drift is not removed by affine normalization |
| Nonstationary event stream | Localized bursts and changing frequencies | Translation + dilation action | Wavelet / multiresolution / scattering | Scale-local energy, cross-scale relations | Continuous transforms may be redundant; admissibility / frame conditions matter |
| Gabor-like response | Local time-frequency content | Time-frequency shift group | STFT / Gabor frame | Localized phase and energy | Coefficients are redundant; image is generally a subspace, not all of coefficient space |
| Observer response vector | Distinctions induced by probes and observer | Probe transformations; observer response operator | Response Gram matrix, kernel, pullback metric; group Fourier only if a group action is specified | Pairwise inner products, distances, invariant subspaces | Different observers need not have the same feature coordinates or metric |
| Paths / geometric phase | Accumulation along a path; reversible movement | Connection / parallel transport | Holonomy representation; characters / traces | Conjugacy class, eigenvalues, trace, winding where defined | Holonomy depends on the chosen connection and path; not every phase is topological |
| S³ / quaternion orientation | Left/right multiplication, antipodality, fibre phase | \(SU(2)\cong S^3\) | Peter–Weyl; Wigner \(D^j_{mn}\); S³ hyperspherical harmonics | Representation labels, Casimir/Laplacian eigenvalues, matrix coefficients | Passing to \(SO(3)\) identifies \(q\) and \(-q\), losing half-integer-spin distinctions |
| Hopf fibre / base observer | Fibre phase versus projected direction | \(S^1\hookrightarrow S^3\to S^2\) | Fourier modes along the fibre; spherical / spin-weighted harmonics on the base | Fibre mode, base angular degree, coupled representation labels | A base-only observer cannot directly see the fibre phase |
| Event / state graph | Adjacency, local continuity, motifs, recurrence | Node-permutation action; graph Laplacian | Graph Fourier basis | Laplacian spectrum, eigenspace projectors, graph signal energy | Cospectral non-isomorphic graphs exist; eigenvectors have sign and repeated-eigenspace ambiguity |
| Boolean / binary logic space | Bit flips and XOR translations | \( (\mathbb Z/2\mathbb Z)^n \) | Walsh-Hadamard transform | Exact orthogonal characters and parity modes | Suited to cube / XOR structure, not arbitrary arithmetic |
| State evolution / virtual dynamics | How observables change under transition | Koopman composition operator | Koopman eigenfunctions / spectral measures; transfer operators | Eigenvalues, invariant subspaces, correlations | Unitary only under suitable invertible measure-preserving dynamics; general evolution can be non-normal or non-invertible |
| Codonic execution algebra | Composition, inverse, commutation, state transition | Invertible symmetry subgroup, monoid, or semigroup | Group representations where available; Koopman/operator representations otherwise | Characters, spectra, intertwining relations, algebraic identities | A codon registry or sequence is not itself a group; many operations are not invertible |
| RNS / finite address arithmetic | Modular addition, multiplication, cyclic shifts | Finite cyclic / finite abelian group | DFT / NTT over suitable finite fields or rings | Exact modular coefficients, roots-of-unity relations | Each modulus must support the transform length and required roots; RNS alone does not guarantee an NTT |
| Neural / weight parameter space | Equivalent parameterizations of the same function | Architecture-specific permutation / scaling symmetries | Quotient parameter space; equivariant representations; local Hessian/Fisher modes | Function-level equivalence, orbit distance, curvature modes | Raw weight distance can count symmetry-related parameters as different solutions |

## 2. Fourier-Plancherel: the reference standard

With the convention

\[
(\mathcal Ff)(\xi)=\int_{\mathbb R}f(x)e^{-2\pi i x\xi}\,dx,
\]

initially for a suitable dense domain such as \(L^1(\mathbb R)\cap L^2(\mathbb R)\), the transform extends uniquely to a unitary operator on \(L^2(\mathbb R)\). Under this convention:

\[
\langle\mathcal Ff,\mathcal Fg\rangle=\langle f,g\rangle,
\qquad
\|\mathcal Ff\|_2=\|f\|_2,
\]

\[
\mathcal F^{-1}f(x)=\int_{\mathbb R}f(\xi)e^{+2\pi i x\xi}\,d\xi,
\qquad \mathcal F^2f(x)=f(-x),\qquad \mathcal F^4=I.
\]

The Hermite functions form a complete orthonormal eigenbasis, with

\[
\mathcal Fh_n=(-i)^n h_n.
\]

Thus the four fourth-roots of unity occur as eigenvalues. The transform is a Hilbert-space isomorphism, not an isomorphism of pointwise-multiplication algebras: convolution and pointwise multiplication are interchanged (with convention-dependent normalization).

The fractional Fourier transform is most naturally selected as a one-parameter unitary/metaplectic action whose action on Hermite modes is phase rotation. Merely knowing \(\mathcal F^4=I\) does not uniquely determine every possible fractional power: the continuous one-parameter group and its generator / phase convention must be specified. In the standard time-frequency interpretation, the action corresponds to rotations in the time-frequency plane.

More specifically, the Fourier map is special because it intertwines familiar operators:

\[
\mathcal F(T_af)(\xi)=e^{-2\pi i a\xi}\widehat f(\xi),
\qquad
\mathcal F(M_bf)(\xi)=\widehat f(\xi-b),
\]

where \(T_af(x)=f(x-a)\) and \(M_bf(x)=e^{2\pi ibx}f(x)\). Under suitable domain assumptions, differentiation becomes multiplication by \(2\pi i\xi\), while convolution becomes pointwise multiplication (and pointwise multiplication becomes convolution, with convention-dependent factors).

Any two separable infinite-dimensional Hilbert spaces are abstractly unitarily isomorphic after choosing orthonormal bases. That fact alone is cheap. What makes a transform useful is that it respects or intertwines the operators, group actions, metrics and algebraic structures that matter in the problem.

The useful lesson is not "Fourier everything." It is:

1. identify a symmetry (translations);
2. represent its action on a Hilbert space;
3. find a basis that decomposes / diagonalizes that action;
4. verify the exact norm and operator relations being preserved.

## 3. The time idea: affine symmetry is a natural unifier

A local clock transformation has the form

\[
t\mapsto a+ct,\qquad a\in\mathbb R,\quad c>0.
\]

The transformations form the orientation-preserving affine group

\[
\mathrm{Aff}^+(\mathbb R)\cong\mathbb R\rtimes\mathbb R_{>0}.
\]

The translation subgroup changes origin. The dilation subgroup changes clock rate. They do not commute, which is why the combined structure is a semidirect product.

- Fourier analysis is naturally adapted to translations.
- Mellin analysis is naturally adapted to positive scaling / dilation. Under logarithmic coordinates, multiplicative scale becomes additive translation.
- Wavelet analysis combines translation and dilation in one representation and is therefore a particularly natural candidate for locally timed, nonstationary structures.

For a positive variable, one unitary Mellin convention on \(L^2(\mathbb R_+,dx)\) is obtained by first setting

\[
g(u)=e^{u/2}f(e^u),\qquad u=\log x,
\]

then taking the ordinary Fourier transform of \(g\). The resulting transform is proportional to

\[
(\mathcal Mf)(\xi)=\frac{1}{\sqrt{2\pi}}\int_0^\infty f(x)x^{-1/2-i\xi}\,dx.
\]

The weight / measure is essential. Mellin is not just an ordinary Fourier transform with a different name; it is Fourier analysis after the correct logarithmic coordinate and unitary weighting.

For Build 15's event graphs, normalized intervals already quotient out the affine offset and positive uniform scale. The next question is whether a scale-space or affine-group representation captures nonlinear drift and localized tempo change better than a single global normalization.


## 3A. Additional useful transforms

- **Hankel:** when the object is radial in Euclidean space, angular variables can be separated and the radial Fourier transform becomes a Hankel transform with a Bessel kernel. It is a symmetry-adapted route for radial wave propagation / vibration, not a generic substitute for the Fourier transform.
- **Bargmann:** the Bargmann transform maps \(L^2(\mathbb R)\) unitarily to a Gaussian-weighted Fock space of entire functions. Hermite modes become monomials; oscillator mode number becomes a natural grading. It may be useful when a Gaussian / phase-space representation is computationally simpler than a time-domain one.
- **Hilbert transform:** within the Fourier representation it is a multiplier by \(-i\,\mathrm{sgn}(\xi)\), with \(H^2=-I\) on the zero-mean / appropriate \(L^2\) setting (more generally, the constant-frequency convention is handled separately). It is useful for quadrature / analytic-signal phase, but is not an independent complete representation.
- **Walsh-Hadamard:** the character transform of \((\mathbb Z/2\mathbb Z)^n\). This is a strong candidate for Boolean codon layers, XOR symmetry and binary state spaces. It should be chosen when the underlying action really is bitwise XOR / hypercube translation.
- **DCT:** when a finite sequence is not naturally periodic, a cosine transform can encode an even-reflection boundary condition and avoid the artificial wraparound implicit in a DFT. The boundary condition must be selected rather than hidden.

## 4. Non-abelian harmonics and the quaternion branch

For a compact group \(G\), Peter–Weyl decomposes \(L^2(G)\) into matrix-coefficient spaces of its irreducible unitary representations. In a common normalization,

\[
\|f\|_{L^2(G)}^2=\sum_{\pi\in\widehat G}d_\pi\|\widehat f(\pi)\|_{HS}^2,
\qquad
\widehat f(\pi)=\int_G f(g)\pi(g)^*\,dg.
\]

The coefficients are matrices, not just scalar frequencies. This is important for rotations and noncommuting transformations.

The unit quaternions form \(SU(2)\), which is diffeomorphic to \(S^3\). Its irreducible representations are indexed by spin \(j=0,\frac12,1,\frac32,\ldots\), with dimension \(2j+1\). Their matrix coefficients are Wigner \(D^j_{mn}\) functions. Equivalently, the degree-\(\ell\) scalar harmonics on \(S^3\) have Laplacian eigenvalue

\[
-\ell(\ell+2),\qquad \text{multiplicity }(\ell+1)^2,
\]

with \(\ell=2j\). This is a direct route from the existing quaternion / Hopf / antipodal work into harmonic coordinates.

The distinction between \(SU(2)\) and \(SO(3)\) matters here. \(SU(2)\to SO(3)\) is a double cover. A representation that descends to \(SO(3)\) cannot distinguish the two lifts \(q\) and \(-q\); the half-integer-spin representations retain information that is lost under that quotient. For the Hopf fibration, the natural decomposition is by fibre Fourier mode together with base-sphere angular structure; a base-only observer may discard the fibre mode.

## 5. Graph harmonics are structure-dependent

For an undirected weighted graph with adjacency \(A\), degree matrix \(D\), and combinatorial Laplacian

\[
L=D-A,
\]

let \(L=U\Lambda U^T\) with orthonormal eigenvectors. For node signal \(x\),

\[
\widehat x_G=U^Tx,\qquad x=U\widehat x_G,
\qquad \|x\|_2^2=\|\widehat x_G\|_2^2.
\]

This gives a graph Fourier transform tied to the graph's topology / edge weights, not to an assumed regular time axis. On a cycle graph it recovers the familiar Fourier modes; on a general graph it gives graph-specific modes.

Under node relabeling, the Laplacian changes by permutation similarity and its eigenvalue multiset is invariant. However, two non-isomorphic graphs can be cospectral. Repeated eigenvalues also mean individual eigenvectors inside an eigenspace are not canonical; compare eigenspace projectors or invariant subspaces rather than raw eigenvector columns.

Build 16 implements a small, transparent Jacobi eigensolver and graph Fourier analysis for controlled event graphs. It is deliberately not an optimized large-graph solver.

## 6. Dynamics and algorithms: Koopman before assuming Fourier

For a state transition \(T:X\to X\), the Koopman operator acts on observables:

\[
(U_Tf)(x)=f(Tx).
\]

It is linear even when \(T\) is nonlinear. If the dynamics are invertible and preserve the chosen measure, this operator is unitary on the corresponding \(L^2\) space. For general non-invertible or measure-changing transitions it need not be unitary. Spectral decompositions can involve point, continuous or residual components and may require operator-specific methods.

This gives a sensible representation path for Virtual Layer state evolution: first define state transitions and observables; then define the induced operator; then investigate eigenfunctions, invariant subspaces, correlations and spectral measures. Do not assume that every codonic operation generates a group. Invertible operations may form a symmetry subgroup; the full execution algebra may instead be a monoid or semigroup.

## 7. Observer geometry: use kernels and intertwiners

For states \(s_a\), probes \(P\), and observer \(O\), let \(r_O(s_a)\) be the measured response vector. Define a weighted Gram matrix

\[
K_O(a,b)=\langle r_O(s_a),r_O(s_b)\rangle_W.
\]

A shared unitary change of feature basis leaves \(K_O\) unchanged. The induced squared distance is

\[
d_O(a,b)^2=K_O(a,a)+K_O(b,b)-2\operatorname{Re}K_O(a,b).
\]

This is a natural stable object when observers use different coordinates. A cross-observer comparison can compare distance / kernel geometry rather than demanding identical raw features. If a symmetry group acts on states and responses, an intertwiner \(T\) should satisfy

\[
T\rho_A(g)=\rho_B(g)T.
\]

That is a stronger and more useful target than simply finding a high correlation between two representations: it says the mapping respects the action of the symmetry.

## 8. Weight-space meaning

Raw parameter distance is not necessarily function distance. Neural architectures can have parameter symmetries (for example, hidden-unit permutations; some architectures also admit scaling symmetries). The natural first step is to identify the group action on parameters and the equivalence relation

\[
\theta\sim\theta'\quad\Longleftrightarrow\quad f_\theta=f_{\theta'}
\]

on the relevant input domain. Only after quotienting or aligning symmetry-related parameters should spectral geometry on weight space be interpreted. Local Hessian / Fisher modes are objective- and data-dependent, not universal coordinates of meaning.

The long-term possibility is an invariant geometry on equivalence classes of functions or computations, with a learned / discovered symmetry action. It is not justified to assume that raw LLM weight vectors already live in one globally harmonic basis.

## 9. Invariants: a hierarchy, not one universal scalar

1. **Hilbert invariants:** norms, inner products, orthogonality, Parseval energy.
2. **Equivariance / intertwining:** an action commutes with the representation map.
3. **Orbit invariants:** pairwise distances, kernel geometry, characters, conjugacy classes.
4. **Spectral invariants:** eigenvalue multisets, multiplicities, trace moments, Casimir values.
5. **Path invariants:** holonomy conjugacy class, winding / homotopy information under the appropriate assumptions.
6. **Graph invariants:** Laplacian spectrum, degree / motif distributions, graph kernels; spectra alone are incomplete.
7. **Empirical invariants:** cross-observer RDM / kernel agreement under calibrated, held-out probes. These are statistical findings, not exact theorems.

An invariant is always relative to a specified action, measure, metric, observer and information-retention level. Every projection can preserve some structure while discarding other structure.

## 10. Build roadmap

- **Build 16 (this package):** ablate Build 15's event matcher, add shuffled-mark and shuffled-order controls, vary nonlinear clock drift, verify unitary finite DFT and graph Fourier prototypes.
- **Build 17:** compare Fourier, wavelet, Mellin and event-graph representations on the same temporal signals; establish which event descriptors survive affine and locally varying time changes.
- **Build 18:** implement a minimal SU(2)/S³ harmonic decomposition with Wigner-matrix or quaternion-polynomial modes; explicitly test the antipodal quotient and Hopf-fibre observability.
- **Build 19:** derive a finite group action from codonic transformations; test group Fourier / NTT only where roots-of-unity and inverse conditions hold; separately analyze non-invertible operations with Koopman / transfer operators.
- **Build 20:** compare observer response Gram matrices and test intertwiners between observer-specific representations.

## 11. Build 16 implementation boundary

Implemented here:

- unitary finite DFT with inverse, Plancherel / inner-product and fourth-power checks;
- circular-shift magnitude invariant;
- real symmetric graph Laplacian, Jacobi eigensystem and graph Fourier transform;
- node relabeling spectral check;
- event matcher ablations, independent mark shuffle, event-order shuffle and quadratic clock-drift sweep.

Not implemented here:

- continuous Fourier / Mellin / wavelet transforms;
- fractional Fourier or metaplectic transform;
- SU(2) Wigner matrices;
- NTT over RNS channels;
- Koopman eigenspectrum of a measured Virtual Layer dynamical system;
- empirical TAPS analysis.

This boundary is intentional: a mathematically correct prototype should precede a larger abstraction.

---

## Build 17 — concrete temporal symmetry comparisons

Build 17 added finite, executable probes for the following action/representation pairs:

| Action | Representation | Tested result |
|---|---|---|
| Circular time translation | Finite Fourier magnitude | Invariant to numerical precision |
| Frame-aligned time translation | STFT field | Covariant by frame-column permutation |
| Circular time translation | Pooled undecimated Haar-like detail energies | Invariant after pooling over positions |
| Positive multiplicative scale | Mellin transform in log-time coordinates | Invariant on the periodic finite log grid |
| Positive affine clock map | Normalized event intervals and recurrence graph | Invariant for the selected graph construction |
| Nonlinear monotone clock drift | Local intervals and recurrence graph | Changes under the tested deformation |
| Node relabeling | Graph Laplacian spectrum/eigenspace energy | Invariant; not a complete graph identifier |

See `BUILD_17.md` for boundary conditions and numerical results, and `PERSPECTIVE_PATHS.md` for the route from each conversation perspective to a candidate representation family.
