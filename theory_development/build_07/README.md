# Virtual Layer — Build 07

Cross-observer invariant discovery across codonic paths on S² and horizontal Hopf lifts to S³.

## Requirements

- Python 3.10 or newer
- Standard library only

## Run

From this directory:

```bash
python -m unittest discover -s tests -v
python cross_observer_invariants.py
```

The second command writes:

- `reports/build_07_report.json`
- `data/candidate_metadata.csv`
- `data/rdm_base_shape.csv`
- `data/rdm_holonomy.csv`
- `data/rdm_temporal.csv`
- `data/rdm_local_transition.csv`
- `data/rdm_correlations.csv` and `data/neighbor_overlap.csv`
- `data/block_permutation_controls.csv`
- `data/h0_persistence_deaths.csv` and `data/graph_laplacian_spectrum.csv`
- `data/betti0_curves.csv` and `data/reparameterization_checks.csv`
- `reports/key_results.json`

## Main files

- `cross_observer_invariants.py` — codon interpreter, quaternion operations, path library, observer signatures, RDMs, graph and permutation analysis.
- `tests/test_build_07.py` — 22 reproducibility and invariant checks.
- `BUILD_07.md` — mathematical definitions, findings, limitations and next steps.
- `SOURCES.md` — research foundations for RDM comparison and persistent topology.
- `NOTES_NEXT.md` — proposed Build 08 experiments.

## Scope

This is a finite synthetic experiment. It is not the full Virtual Layer, does not measure biological or emotional tone, and does not establish a universal invariant geometry.
