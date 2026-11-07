# Build 03 — Codonic Connection Geometry

## Research question

Can ordinary algebraic operations, encoded as a short codonic program, generate
an accumulated geometric transformation whose closure depends on what the
observer can measure?

This build separates four objects:

1. **Algebraic instructions** — here, addition (`ad`) and multiplication (`mx`).
2. **Edge transports** — invertible linear maps produced by those instructions.
3. **Observer projection** — the measurement that identifies some distinct
   internal states as equivalent.
4. **Holonomy-like composition** — the ordered product of edge transports around
   a closed walk in the observer's quotient representation.

The current implementation is a prototype of these relationships. It does not
claim to discover a natural connection from the full Virtual Layer seed space.

## 1. Codonic shear construction

For a state vector `v = (x,y)`, define two shear operations:

\[
S_x(k): (x,y)\mapsto(x+ky,y),\qquad
S_y(k):(x,y)\mapsto(x,y+kx).
\]

Their matrices are:

\[
S_x(k)=\begin{bmatrix}1&k\\0&1\end{bmatrix},\qquad
S_y(k)=\begin{bmatrix}1&0\\k&1\end{bmatrix}.
\]

Each shear is implemented from the two primitive codon operations:

```text
# x shear
 tmp = mx(k, y)
 x   = ad(x, tmp)

# y shear
 tmp = mx(k, x)
 y   = ad(y, tmp)
```

The spellings are aliases in an experimental registry profile. The implementation
permits substitution of different labels for the same algebraic operations.

## 2. Three shears compose to a rotation

Let:

\[
a=-\tan(\theta/2),\qquad b=\sin\theta.
\]

Then:

\[
S_x(a)S_y(b)S_x(a)
=\begin{bmatrix}1+ab&a(2+ab)\\b&1+ab\end{bmatrix}
=\begin{bmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{bmatrix}.
\]

The matrix identity is valid for `-pi < theta < pi`; the implementation rejects
values too close to the endpoints because `tan(theta/2)` becomes numerically
ill-conditioned there.

This gives an interpretable construction: elementary addition and multiplication
operations compose into a rotation. No rotation instruction is present in the
codonic program.

## 3. Observer quotient and lifted transport

The initial state is:

\[
v_0=(1,0).
\]

The final state is:

\[
v_3=R(\theta)v_0=(\cos\theta,\sin\theta).
\]

A radial observer measures:

\[
h_r(x,y)=\sqrt{x^2+y^2}.
\]

Therefore:

\[
h_r(v_3)=h_r(v_0)=1.
\]

The radial observer identifies the endpoints. A full-state observer
`h_f(x,y)=(x,y)` distinguishes them whenever `theta` is not a multiple of
`2*pi`.

The ordered transport product is:

\[
H=S_x(a)S_y(b)S_x(a)=R(\theta).
\]

Its action on the hidden orientation has accumulated phase `theta`. The radial
projection closes while the lifted state changes. This is the central result
of the toy construction.

**Important qualification:** the graph is a quotient under a chosen observer,
and the maps are edge transports in a finite-dimensional model. This is called a
*discrete holonomy analogue*, not a complete principal-bundle connection. A
stronger construction would need a defined base graph, fibres, transition maps,
compatibility conditions, and a gauge-covariant connection law.

## 4. Non-commutativity and path direction

The shear matrices generally do not commute:

\[
S_x(a)S_y(b)\ne S_y(b)S_x(a).
\]

The reverse traversal uses inverse maps in reverse order. Its transport is
`H^{-1}` and its signed phase is `-theta` (within the principal angle range).

This makes order and orientation measurable properties of the path.

## 5. Coordinate changes

Under a change of basis `B`, the edge and loop maps transform by conjugation:

\[
T_i' = BT_iB^{-1},\qquad H'=BHB^{-1}.
\]

Therefore the trace and determinant of the loop transport are preserved:

\[
\mathrm{tr}(H')=\mathrm{tr}(H),\qquad\det(H')=\det(H).
\]

For the rotation used here:

\[
\mathrm{tr}(H)=2\cos\theta,\qquad\det(H)=1.
\]

These are coordinate-independent invariants of the conjugacy class. The signed
angle requires an orientation convention; a reflection can reverse its sign.

## 6. Time parameterization versus accumulated transport

The same three shears can be traversed with different segment durations. The
endpoint transport remains the same because the ordered edge maps are unchanged.
The time-resolved radial and angular response profiles differ.

This distinguishes:

- accumulated path transport / holonomy-like quantity;
- instantaneous, time-dependent response;
- observer-specific measured signal.

The response-rate summaries in the JSON report are descriptive features of this
synthetic path, not universal definitions of tone or vibration.

## 7. Verification results

Run the test suite and `run_experiment.py` to regenerate the report and CSV traces.
The test suite checks:

- analytic three-shear rotation identity over positive and negative angles;
- determinant-one property of each shear and total transport;
- radial closure and full-state non-closure;
- signed holonomy phase;
- inverse transport under reversed path;
- registry alias substitution;
- non-commutativity;
- trace and determinant invariance under conjugation;
- same endpoint with different time-resolved response;
- rejection of invalid angles, axes and codons.

## 8. What this does and does not establish

### Established by the implementation

- A program using only configured addition and multiplication codons can
  implement elementary shears.
- Three shears compose exactly (up to floating-point error) into a rotation.
- A radial observer identifies the initial and final states, although the full
  state has changed orientation.
- Reversing the edge sequence reverses the accumulated signed phase.
- Trace and determinant of the transport are preserved under basis conjugation.
- Changing time allocation changes the measured time profile without changing
  the final ordered transport.

### Not established

- That the full Virtual Layer S3 or SHA-derived address geometry naturally
  produces this connection.
- That arbitrary codonic rewrite loops have nontrivial holonomy.
- That this toy construction yields a universal perceptual or emotional tone.
- That radial closure alone constitutes a full geometric loop in every
  mathematical model.
- That the discrete construction is already a principal-bundle connection.

## 9. Next mathematical requirement

The next version should replace the manually selected three-shear loop with a
connection derived from an explicit codonic transition graph. It should define:

1. Nodes as normalized algebraic states or observer-equivalence classes.
2. Edges as typed, invertible codonic transformations.
3. Fibres as internal degrees of freedom not retained by the observer.
4. Transport maps as compositional actions on those fibres.
5. Gauge transformations as local changes of fibre coordinates.
6. Holonomy as the ordered product around graph cycles.

Only after these definitions should we ask whether recurring holonomy classes,
response spectra or graph-topological invariants emerge from a larger codon
registry.

## References

- Kelly, S. D. (1995), “Geometric phases and robotic locomotion,” *Journal of
  Robotic Systems*, 12(6), 417–431. DOI: 10.1002/rob.4620120607.
- “Geometric phase predicts locomotion performance in undulating living systems
  across scales,” *PNAS* (2024), PMC11181092.
- Hatton, R. L. and Choset, H. (2011), “Geometric motion planning: The local
  connection, Stokes’ theorem, and the importance of coordinate choice,” DOI:
  10.1177/0278364910394392.
- Berkeley EECS, “Representing a Rotation as Three Shears,” course notes.
