# Certified modular-affine fast-forward

## Purpose

Cycle indexing already allows a closed deterministic orbit to answer distant logical-time queries by reducing a coordinate modulo its observed cycle period. This experiment adds an algebraically explicit route: represent each state on one verified orbit as a vector over a finite modular ring, validate one affine law against every retained edge, then use matrix exponentiation to navigate to a distant coordinate.

The scope is deliberately narrower than “the Ground is affine”. The certificate says only that a supplied map generates the particular closed OrbitIndex that was checked. It does not infer an embedding for arbitrary Ground states or replace evidence admission.

## Mathematical contract

Choose a modulus \(m\geq2\), a dimension \(d\geq1\), a matrix \(M\in(\mathbb Z/m\mathbb Z)^{d\times d}\), and an offset \(b\in(\mathbb Z/m\mathbb Z)^d\). The candidate transition is

\[
F(x)=Mx+b\pmod m.
\]

A caller supplies an encoding

\[
\eta:S_{\mathrm{orbit}}\rightarrow(\mathbb Z/m\mathbb Z)^d
\]

for the distinct states in the retained orbit. The encoding must be total and injective on that finite set. Before any fast-forward is allowed, the certificate checks every retained transition \(s\rightarrow s'\):

\[
F(\eta(s))=\eta(s').
\]

The OrbitIndex itself already guarantees that the path is closed, follows one fixed policy, traverses only known singleton Ground edges, and replays every edge against the Ground. The affine certificate additionally binds the exact OrbitIndex, Ground, policy, clock, transform, and state-encoding fingerprints.

To exponentiate, augment the state with a constant coordinate:

\[
\begin{bmatrix}x_{t+1}\\1\end{bmatrix}
=
\underbrace{\begin{bmatrix}M&b\\0&1\end{bmatrix}}_{H}
\begin{bmatrix}x_t\\1\end{bmatrix}.
\]

Then

\[
\begin{bmatrix}x_{t+N}\\1\end{bmatrix}
=
H^N
\begin{bmatrix}x_t\\1\end{bmatrix}\pmod m.
\]

Binary exponentiation computes \(H^N\) using \(O(\log N)\) matrix compositions. It does not materialize intermediate logical states. Python integer arithmetic is exact, so this implementation has no fixed-width integer overflow mode. The modulus may be composite and the matrix may be non-invertible; no modular inverse is needed for forward navigation.

## Why the certificate is sufficient

Let the certified orbit be \(s_0,s_1,\ldots,s_{\mu+p}=s_\mu\), where \(\mu\) is the transient-prefix length and \(p\) is the cycle period. The certificate checks \(F(\eta(s_i))=\eta(s_{i+1})\) for every retained edge, including the closing cycle edge.

The base case is the declared start encoding \(\eta(s_0)\). If \(F^t(\eta(s_0))=\eta(s_t)\), the checked one-step edge implies

\[
F^{t+1}(\eta(s_0))
=F(\eta(s_t))
=\eta(s_{t+1}).
\]

By induction, the affine recurrence agrees with the retained orbit at every future step. Since the orbit is closed and the encoding is injective over its states, every future vector decodes to exactly one state in that certified orbit. The matrix power is therefore a shortcut for the checked recurrence, not a guess about missing transitions.

## API

- **ModularAffineMap(modulus, matrix, offset)** defines the finite-ring map.
- **AffineOrbitCertificate.certify(orbit, transform, state_vectors)** checks closure, complete/injective encoding, and every retained edge.
- **certificate.state_at(OrbitTimeCoordinate(...))** returns an AffineFastForwardResult bound to the Ground, policy, orbit, certificate, and logical clock.

The result records the requested logical transition count, exponent bit length, method, state vector, exact state identifier, and the fact that no intermediate states were materialized. Clock mismatch and a request before the orbit origin are refused.

## Verification and limits

Run:

~~~bash
python -m unittest discover -s tests -p test_affine.py -v
python examples/run_certified_affine_fast_forward.py
~~~

The tests compare matrix powering with a separate repeated-step reference across deterministic randomized matrices, dimensions, offsets, and composite moduli. They also check a non-invertible map with both a transient prefix and a fixed point, a \(10^{12}\)-scale logical jump, incomplete encodings, collisions, edge mismatch, open orbits, and clock boundaries.

The certificate is not a proof that the candidate affine law describes every possible VGI state, every policy, or the external world. A new Ground, policy, orbit, clock, or encoding requires a new certificate. Unknown or ambiguous transitions cannot be replaced by affine extrapolation because an open orbit cannot be certified by this API. The state-to-vector map is currently supplied by the caller; discovering useful embeddings is a separate research problem.
