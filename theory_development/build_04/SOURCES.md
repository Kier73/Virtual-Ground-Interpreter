# Build 04 — Research Sources

These sources support the standard mathematical constructions used in the experiment. The numerical results are generated locally by the included implementation.

1. **Albert Chern, _Discrete Differential Geometry_ (UC San Diego lecture notes, last updated 2020), Chapter A: Quaternions.** Defines S³ as unit quaternions, gives the quaternion action on R³, explains the double cover S³ → SO(3), and constructs the minimal quaternion rotating one unit vector to another. Particularly relevant: sections A.3.1–A.4.2.
   - https://cseweb.ucsd.edu/~alchern/teaching/DDG.pdf

2. **Eric W. Weisstein, “Hopf Map,” Wolfram MathWorld.** Summarizes the Hopf fibration S¹ → S³ → S², identifies S³ with unit quaternions / SU(2), and describes the quotient by U(1).
   - https://mathworld.wolfram.com/HopfMap.html

3. **Peter Hornung, “Framed Curves, Ribbons, and Parallel Transport on the Sphere,” Journal of Nonlinear Science 33, article 72 (2023).** Discusses parallel transport on S² and relates holonomy to the area enclosed by a spherical loop through a Gauss–Bonnet argument.
   - https://doi.org/10.1007/s00332-023-09930-0

4. **Stefan Filipp, Yuji Hasegawa, Rudolf Loidl, and Helmut Rauch, “Spatial Non-Cyclic Geometric Phase in Neutron Interferometry,” Journal of Research of the National Institute of Standards and Technology 110, 251–257 (2005).** Gives the geometric phase for a spin-1/2 system as half the solid angle enclosed by a loop and distinguishes geometric phase from time-dependent dynamical phase.
   - https://doi.org/10.6028/jres.110.034

5. **Eliahu Cohen et al., “Geometric phase from Aharonov–Bohm to Pancharatnam–Berry and beyond,” Nature Reviews Physics 1, 437–449 (2019).** Review of geometric phases, holonomy, gauge structure, and applications across optics, condensed matter and quantum information.
   - https://www.nature.com/articles/s42254-019-0071-1

6. **“The Hopf Fibration,” Australian Mathematical Sciences Institute student research report (2026).** Supplementary accessible derivation of the quaternion form of the Hopf map and its realization as a map S³ → S². This is pedagogical support, not a primary research article.
   - https://srs.org.au/wp-content/uploads/sites/92/2026/03/crosby_nyx_srs-report.pdf

## Convention note

Different references choose different distinguished imaginary axes and may use left versus right group actions. This build fixes:

\[
\pi(q)=qkq^{-1},\qquad q\mapsto qe^{k\beta}
\]

and the increasing-azimuth orientation for the spherical-cap loop. A sign change in a reported phase can result from changing these conventions; the invariant comparison is made only after conventions are fixed.
