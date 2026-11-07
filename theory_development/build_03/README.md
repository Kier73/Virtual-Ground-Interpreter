# Virtual Layer — Build 03: Codonic Connection Geometry

A dependency-free Python research prototype exploring whether short codonic
programs can define edge transports whose ordered composition produces a
nontrivial observer-relative loop transformation.

## Run

```bash
python -m unittest discover -s tests -v
python run_experiment.py
```

Python 3.10+. No third-party packages.

## Experimental codon profile

This build uses the project-conversation spellings `ad` = addition and `mx` =
multiplication. The `Registry` object permits different spellings without
changing the operation semantics. This is an experimental profile, not a
claim that these identifiers are fixed in the current Virtual Layer registry.

## Core construction

A shear is encoded using two instructions:

```text
tmp = mx(k, y)
x   = ad(x, tmp)
```

or, for a y-shear:

```text
tmp = mx(k, x)
y   = ad(y, tmp)
```

Three shears compose to a rotation:

\[
R(\theta)=S_x(-\tan(\theta/2))S_y(\sin\theta)S_x(-\tan(\theta/2)).
\]

The radial observer identifies states with equal norm. The full observer sees
both coordinates. The composed transport returns the radial observation to
its starting value while changing the hidden orientation by `theta`.

## Terminology caveat

The experiment calls the ordered product of edge maps a **discrete holonomy
analogue**. It is a finite-dimensional construction illustrating observer
quotients and lifted transport. It is not presented as a full principal-bundle
connection, nor as evidence of universal or biological resonance.
