# Virtual Layer — Build 09

## Cross-modal response geometry

A reproducible, standard-library-only Python experiment comparing synthetic acoustic-like digital resonators and mechanical mass-spring-damper systems under matched probes.

### Run

```bash
python -m unittest discover -s tests -v
python cross_modal_response.py
```

The main run generates 40 matched parameter families per domain, 8 observer feature representations, representational dissimilarity matrices (RDMs), permutation tests, family bootstrap intervals, noise/dropout sweeps, sample-rate checks, coordinated unit-rescaling checks, and codon-alias equivalence checks.

### Scope and limitations

- These are synthetic systems, not recordings of voices, musical instruments, touched materials, or biological sensors.
- The acoustic-like model is a second-order digital resonator. The mechanical model is a single-degree-of-freedom damped oscillator integrated with RK4.
- The two systems deliberately share matched natural-frequency and damping parameters. Therefore strong linear-response RDM alignment is a positive-control result expected from the construction, not evidence of an unknown universal cross-modal law.
- The acoustic output compression and mechanical cubic-stiffness perturbation are different nonlinear mechanisms. They are stress probes, not perceptual roughness measures.
- No human participants, emotion labels, or affective ratings are included.

### Contents

- `cross_modal_response.py` — models, probes, codonic arithmetic interpreter, RDM analysis, perturbation tests, and report generation.
- `tests/test_build_09.py` — 24 unit and report-integrity tests.
- `codon_schema.json` — executable local arithmetic codon subset and model-expression descriptions.
- `reports/` — full and condensed numerical reports.
- `data/` — RDMs, parameters, robustness results, and representative signal traces.
- `BUILD_09.md` — mathematical reference and interpretation.
- `NOTES_NEXT.md` — Build 10 direction.
- `SOURCES.md` — selected external research references.
- `MANIFEST.sha256` — SHA-256 file integrity manifest.

No third-party package is required.
