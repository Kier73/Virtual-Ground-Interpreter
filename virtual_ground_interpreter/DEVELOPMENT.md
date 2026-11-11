# Virtual Ground Interpreter — development loop

This package is the active development line. The numbered Builds under
`../theory_development` and `../virtual_ground` are frozen lineage; they are not
the place for new interpreter work.

## Iteration loop

Every improvement should follow the same loop:

1. **Capability hypothesis.** State the new capability or falsification target
   in one sentence.
2. **Formalize the contract.** Add the transition rule, guard semantics,
   uncertainty propagation and failure behavior to `docs/FORMAL_SPECIFICATION.md`
   before implementation.
3. **Implement the smallest trusted core change.** Prefer a backend method,
   IR instruction or machine transition over a broad refactor.
4. **Verify differentially.** Compare the optimized/fast path against an
   independent reference semantics or exhaustive finite check.
5. **Stress the boundary.** Add property, adversarial and uncertainty tests:
   invalid inputs, indeterminate guards, observer changes, calibration noise,
   checkpoint tampering and step limits.
6. **Benchmark against a baseline.** Record productivity or cost when the
   claim is comparative; do not claim a signal-domain advantage without a
   baseline.
7. **Release deliberately.** Update `CHANGELOG.md`, bump the version, run the
   quality gates and tag.

## Quality gates

A change is not done until all of these hold:

- `python -m unittest discover -s tests -v` passes.
- `python -m vgi verify` passes with zero errors.
- New behavior has a test that would fail if the central contract were broken.
- Machine execution does not decode semantic integers except through explicit
  terminal observation.
- Indeterminate guards trap atomically; no partial transition is applied.
- Uncertainty is propagated or explicitly rejected; it is never silently dropped.
- Human-readable behavior is reflected in `docs/FORMAL_SPECIFICATION.md` or
  `docs/ARCHITECTURE.md` when semantics change.
- The external contract is versioned in `specs/signal8_ground.json` and the
  Ground fingerprint is regenerated.

## Release checklist

- Update `pyproject.toml` version.
- Add a `CHANGELOG.md` entry with capability, verification totals and limits.
- Run:
  - `python -m unittest discover -s tests -v`
  - `python -m vgi verify`
  - `python -m vgi run examples/conditional_select.task.json --input input.a=3@1 --input input.b=5@3`
  - `python -m vgi compile examples/conditional_select.task.json --output program.json`
- Confirm `MANIFEST.sha256` still matches the shipped tree.
- Commit with a versioned message, e.g. `v0.2.0: typed backend protocol`.

## Near-term priorities

From `docs/DEVELOPMENT_DIRECTION.md`, in dependency order:

1. Extract a typed backend protocol so `Signal8Backend` is one implementation,
   not an implicit assumption.
2. Give each IR instruction explicit pre/postconditions and read/write sets.
3. Make the control-state transition system a first-class Ground object and
   lower it to IR for differential verification.
4. Add a second backend only after the common semantic interface is declared.
5. Reintroduce observation-driven Ground construction as a constructor with
   counterexample refinement, without forcing every domain into a group law.


## Predictive-ground compiler iteration

For transition-system or compiler work, the minimum gate is:

- Run the unit suite with Python unittest discovery over tests.
- Run the finite Ground verifier through the vgi CLI.
- Run the delayed-six integration example under examples/run_delayed_six.py.

The delayed-six runner must report matching direct and compiled state/output traces. Partial or ambiguous transition systems must remain non-executable. Regenerate MANIFEST.sha256 after every package change and verify every listed digest. Do not record passing totals until the commands have actually been run.


## Observer-relative relational atlas experiment

The package contains an experimental finite relational layer in `vgi/relational.py`. Its observer contract makes action probes and visible channels explicit. It produces exact predictive partitions by horizon, checks quotient maps and adjacent-layer transitions, and computes a task-conditioned behavioral distance profile. The small runner `examples/run_relational_atlas.py` assembles delayed-six, cyclic, and non-bijective controls.

Run the new checks with:

```bash
python -m unittest discover -s tests -p 'test_relational.py' -v
python examples/run_relational_atlas.py
```

The relational layer must preserve the existing epistemic boundary: predictive equivalence is relative to the observer and horizon, not an identity claim about physical hidden states. An omitted probe is outside the observer contract; an unknown or ambiguous selected edge is not a negative observation and must not be completed by inference.


## Active-attention planning experiment

The experimental `vgi/attention.py` module adds cost-aware candidate selection over action probes and output channels. It exposes single-candidate rankings, a greedy marginal-gain plan, and an exhaustive subset baseline bounded to a small candidate pool.

Run:

```bash
python -m unittest discover -s tests -p 'test_attention.py' -v
python examples/run_active_attention.py
python -m unittest discover -s tests -v
python -m vgi verify
```

The complementary-probe fixture is a required regression control: neither candidate should reduce ambiguity alone, but the pair should. Do not simplify the planner to greedy-only. Candidate costs are relative declared units until measured from a real observation path; deterministic pair reduction must not be described as probabilistic expected information gain.


## Joint perception-navigation experiment

The experimental `vgi/joint_attention.py` planner searches pairs of observer configurations and induced predictive quotients. It keeps zero-gain candidate steps available for later complementary observations and returns an inspectable route plus search records.

Run:

```bash
python -m unittest discover -s tests -p 'test_joint_attention.py' -v
python examples/run_joint_navigation.py
python -m unittest discover -s tests -v
python -m vgi verify
```

Compare beam widths against the exhaustive planner on small fixtures. Treat the beam as heuristic; inspect the pruned-node records before attributing a failure to the observation model.


## Counterexample-led perception inquiry

The experimental vgi/inquiry.py layer searches unresolved pairs under the current observer against every action and output channel already declared by the Ground. It returns a shortest known distinguishing action word when one exists; it reports unknown/ambiguous cells rather than imputing them.

Run:

    python -m unittest discover -s tests -p 'test_perception_inquiry.py' -v
    python examples/run_perception_inquiry.py
    python -m unittest discover -s tests -v
    python -m vgi verify

Interpret equivalence only over the evidence-supported reachable paired graph and declared alphabet. Every report retains an open, unenumerated boundary outside that finite schema. Do not generate undeclared sensors, transformations, or states as though the observer could already know them.


## Encounter and association layer

The experimental vgi/encounters.py module records JSON-compatible observation envelopes and provenance before semantic interpretation. EncounterLedger is append-only and immutable by operation. AssociationLedger stores falsifiable cross-encounter hypotheses and assessment history independently of predictive Grounds.

Run:

    python -m unittest discover -s tests -p 'test_encounters.py' -v
    python examples/run_encounter_association.py
    python -m unittest discover -s tests -v
    python -m vgi verify

Supporting or contradicting assessments must cite at least one encounter beyond the hypothesis's original basis. Keep contradictory assessments in the history. Do not automatically promote an association into a transition, invariant, or executable rule. The encounter payload envelope is JSON-compatible; large or binary source data stays in an external source store with an opaque reference and digest.
