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
