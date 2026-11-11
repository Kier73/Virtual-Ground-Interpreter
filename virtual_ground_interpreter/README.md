# Virtual Ground Interpreter

**A bounded, executable interpreter core for signal-state computation.**

The Virtual Ground Interpreter (VGI) runs a small instruction language against persistent signal-valued state. Its current reference Ground is the finite cyclic domain `Z/8Z`, represented through four equivalent 8-PSK observer coordinates. Arithmetic and conditional equality tests operate on calibrated complex phasors; semantic integers are used only at input and output boundaries.

VGI is being treated as an executable runtime with a versioned contract, not as a sequence of numbered experiments.

## What it does now

- Represents values as unit complex phasors, observer coordinates, and conservative phase-error bounds.
- Ingests and emits complex I/Q sample frames using pilot-referenced calibration.
- Executes modular addition/subtraction by signal algebra, including automatic observer alignment.
- Changes observer coordinates without decoding the semantic value.
- Maintains persistent signal-valued memory and a register file.
- Compiles a constrained typed task-expression description into interpreter IR; `interpret()` is the direct compile-and-run entry point.
- Executes conditional equality and identity branches.
- Traps on indeterminate branch conditions rather than guessing.
- Records branch evidence and signal-valued writes in its instruction trace; supports pause/resume, checkpoints, reset, and journal-based undo.
- Associates execution with a versioned Ground contract and fingerprint.

## What it does not do yet

- Infer a program from an unrestricted natural-language task or an unconstrained objective.
- Discover an unknown signal alphabet or arbitrary operation algebra without supplied evidence.
- Learn or update a Ground online from live observations.
- Execute raw ADC arrays continuously inside the machine; the current runtime's native state is a pilot-calibrated phasor. I/Q ingress/egress adapters are provided.
- Implement a physical analog computer or prove a hardware performance advantage.
- Establish universal or Turing-complete computation.

The current control plane is a typed instruction stream executed by ordinary software. The data plane uses signal-domain values. The distinction is intentional and explicit.

## Installation and quick start

Python 3.10+, no third-party runtime dependencies. From this directory:

```bash
python -m pip install .
vgi verify
vgi run examples/conditional_select.task.json --input input.a=3@1 --input input.b=5@3
vgi compile examples/conditional_select.task.json --output program.json
```

For source checkout development without installation:

```bash
python -m unittest discover -s tests -v
python -m vgi verify
python -m vgi run examples/conditional_select.task.json --input input.a=3@1 --input input.b=5@3
python -m vgi compile examples/conditional_select.task.json --output program.json
```

The JSON task form is a typed expression tree, not an instruction listing. It supports input references, addition, subtraction, observer reframing, identity/equality guards, conditional expressions, and named outputs. The compiler lowers it to the validated instruction language.

Programmatic use:

```python
from vgi import (
    AddExpr, ConditionalExpr, IdentityGuard, InputExpr,
    OutputSpec, Signal8Backend, TaskCompiler, TaskSpec,
    VirtualGroundInterpreter,
)

backend = Signal8Backend()
a, b = InputExpr("input.a"), InputExpr("input.b")
task = TaskSpec("select", ("input.a", "input.b"), (
    OutputSpec("selected", ConditionalExpr(
        IdentityGuard(AddExpr(a, b), 0.02),
        when_true=b,
        when_false=a,
    )),
))
memory = {
    "input.a": backend.encode_symbol(3, observer=1),
    "input.b": backend.encode_symbol(5, observer=3),
}
interpreter = VirtualGroundInterpreter()
program = interpreter.compile_task(task)  # inspect or persist the lowered IR
result = interpreter.interpret(task, memory)  # compile + execute
print(result.observed_outputs(backend))  # {'selected': 5}
```

The two inputs use different observer coordinates. The machine adds them, checks whether the signal result is the group identity, and selects a branch. No integer decoding occurs within arithmetic, observer reframing, or branch evaluation. `observed_outputs` is an explicit terminal observation.

## Instruction language

| Instruction | Meaning |
|---|---|
| `LOAD dst,address` | Load a persistent memory cell into a register |
| `STORE src,address` | Persist a register value in memory |
| `MOVE dst,src` | Copy a signal state |
| `REFRAME dst,src,observer` | Change observer coordinate without integer decoding |
| `ADD dst,left,right` | Signal multiplication; semantic addition modulo 8 |
| `SUB dst,left,right` | Signal multiplication by conjugate; semantic subtraction modulo 8 |
| `BRANCH_EQ left,right,target,tolerance_rad` | Branch if two signal states are robustly equal |
| `BRANCH_IDENTITY src,target,tolerance_rad` | Branch if a signal state is robustly the group identity |
| `JUMP target` | Unconditional control transfer |
| `EMIT src,label?` | Append a signal-valued output |
| `HALT` | Stop execution |

There is deliberately no integer `<` operator on `Z/8Z`: the cyclic group has no observer-invariant linear order. The available guards test identity and equivalence, which are preserved by the declared observer automorphisms. A future ordered domain must declare its order as part of its own Ground contract.

## Project map

- `vgi/values.py` — signal value type, 8-PSK backend, I/Q ingress/egress, observer maps and robust predicates.
- `vgi/ground.py` — versioned executable Ground contract and evidence boundary.
- `vgi/ir.py` — validated instruction and program representation.
- `vgi/compiler.py` — typed task-expression DSL and lowering to control-flow IR.
- `vgi/machine.py` — interpreter, persistent memory, register state, branch logic, trace, checkpoints and undo.
- `vgi/execution.py` — canonical Signal8 execution-trace capture, serialization, same-runtime replay comparison, and observed-only transition projection.
- `vgi/signal8_trace.py` — compatibility adapter for observing an already-instantiated machine; exported as `LegacySignal8ExecutionAdapter`.

- `vgi/verification.py` — finite exhaustive verification of the declared Ground.
- `vgi/cli.py` — compile, execute, and verify commands.
- `examples/` — runnable conditional signal-state program.
- `tests/` — deterministic unit tests.
- `docs/` — formal semantics, architecture and next research priorities.
- `reports/` — executed verification output and package manifest.

## Core mathematical contract

A runtime value is

\[
S=(z,u,\epsilon),\qquad |z|=1,\quad u\in\{1,3,5,7\},\quad 0\leq\epsilon\leq\pi.
\]

The observer character is

\[
\chi_u(k)=e^{2\pi iuk/8}.
\]

For source observer `u` and target observer `v`, let

\[
m=v u^{-1}\pmod 8.
\]

The coordinate change is `z -> z^m`; it preserves the represented semantic state and propagates the phase bound conservatively as `min(pi, m*epsilon)`.

After aligning observers, arithmetic is

\[
ADD(S_a,S_b): (z_a z_b,u,\min(\pi,\epsilon_a+\epsilon_b)),
\]

\[
SUB(S_a,S_b): (z_a\overline{z_b},u,\min(\pi,\epsilon_a+\epsilon_b)).
\]

Conditional equality uses a phase-distance interval, not an early integer decode. If the interval overlaps the configured tolerance boundary, the branch is indeterminate and execution traps.

See [`docs/FORMAL_SPECIFICATION.md`](docs/FORMAL_SPECIFICATION.md) for the full transition semantics and assumptions.


## Predictive transition grounds

The runtime also exposes a bounded bridge from learned predictive machines to executable VGI programs:

    import json
    from pathlib import Path
    from vgi import GroundTransitionSystem, TransitionCompiler

    legacy = json.loads(Path("examples/delayed_six_predictive_ground.json").read_text())
    ground = GroundTransitionSystem.from_predictive_mealy_dict(legacy)
    actions = ("HOLD", "HOLD", "HOLD", "HOLD", "HOLD", "PROBE_A")

    direct = ground.run(actions)
    compiled = TransitionCompiler().compile(ground, len(actions))
    result = compiled.execute(actions)

    assert result.state_trace == direct.state_trace
    assert result.outputs == direct.outputs

GroundTransitionSystem distinguishes known, unknown, and ambiguous transitions. The initial compiler accepts only complete deterministic grounds and lowers them to the current Signal8 instruction language. It is bounded to eight states, eight actions, and output values in Z/8Z. Unknown and ambiguous transitions are never silently guessed. See the formal specification and the development-throughline review in the docs directory.

Terminal symbol observation also respects phase uncertainty: it returns a symbol only when one decision region is consistent with the declared error bound.


## Observer-relative relational atlas (experimental)

The experimental relational layer treats an observer as an explicit choice of available action probes and visible output channels. It constructs exact predictive equivalence classes over increasing horizons, verifies maps between finer and coarser quotients, and calculates a behavioral distance profile tied to the observer and action distribution.

```python
from vgi import ObserverContext, refinement_series, behavioral_distance

observer = ObserverContext.full(ground, "available")
quotients = refinement_series(ground, observer, max_horizon=8)
distance = behavioral_distance(ground, observer, "q0", "q1", horizon=5)
```

See [the relational-atlas experiment](docs/RELATIONAL_ATLAS.md) and run `python examples/run_relational_atlas.py`. This is a finite research tool, not a universal state-space model or a claim about physical hidden-state identity. The exact quotient still requires known singleton edges.

For incomplete grounds, `partial_refinement_series` retains three pairwise results: equivalent, distinguishable with a shortest known action word, or unresolved because an edge or continuation is missing/ambiguous:

```python
from vgi import ObserverContext, partial_refinement_series

observer = ObserverContext("available", ("HOLD", "PROBE_A"), ("channel_0",))
series = partial_refinement_series(partial_ground, observer, max_horizon=8)
comparison = series[-1]
print(comparison.status("context-a", "context-b"))
print(comparison.witness("context-a", "context-b"))
print(comparison.blocked("context-a", "context-b"))
print(comparison.blockers("context-a", "context-b"))  # structured missing/ambiguous/successor reasons
```

See [partial predictive relations](docs/PARTIAL_PREDICTIVE_RELATIONS.md) and run `python examples/run_partial_predictive_relations.py`. An unresolved pair is neither merged nor declared distinct.


## Active attention planning (experimental)

Candidate action probes and output channels can be ranked by their reduction in unresolved predictive-state pairs per declared cost. For small candidate sets, compare local greedy selection with exact subset search:

```python
from vgi import (
    AttentionCandidate, greedy_attention_plan, exhaustive_attention_plan,
)

candidates = (
    AttentionCandidate("action", "PROBE_A", cost=1.0),
)
greedy = greedy_attention_plan(ground, observer, candidates, horizon=5, budget=1.0)
exact = exhaustive_attention_plan(ground, observer, candidates, horizon=5, budget=1.0)
```

See [the active-attention experiment](docs/ACTIVE_ATTENTION.md) and run `python examples/run_active_attention.py`. Greedy selection is not assumed sufficient: complementary observations can have zero individual gain and positive joint value.


## Joint perception-navigation search (experimental)

The joint planner searches observer configurations and tracks the predictive quotient induced by each one. It retains zero-immediate-gain configurations so complementary action/channel capabilities can be combined.

```python
from vgi import beam_attention_plan

plan = beam_attention_plan(
    ground, observer, candidates, horizon=5, budget=2.0,
    beam_width=8, max_depth=4,
)
for step in plan.route:
    print(step.candidate, step.actions, step.channels,
          step.unresolved_before, step.unresolved_after)
```

See [the joint navigation experiment](docs/JOINT_NAVIGATION.md) and run `python examples/run_joint_navigation.py`. The search is bounded; its records show which observer configurations were expanded and pruned.


## Encounter memory and associative hypotheses

The experimental encounter layer records observations and provenance before requiring a semantic interpretation. Immutable EncounterLedger snapshots preserve payload/context envelopes and content fingerprints. A separate AssociationLedger stores cross-encounter hypotheses with a rationale, experiment, falsifier, and append-only assessments. Supporting or contradicting assessments require at least one new evidence encounter beyond the hypothesis's original basis.

This layer does not automatically classify encounters, calculate a universal curiosity score, or promote hypotheses into Ground transitions. See docs/ENCOUNTER_ASSOCIATION.md for the contract and example runner.


## Duplex channel contracts

The experimental `vgi/channels.py` module distinguishes observation-only channels from addressable request/reply channels. A shared protocol identifier describes the message framing language, while observation, request, and response schemas declare the supported directions separately. Correlated exchanges can be materialized as encounters without turning outbound requests into observations.

`PredictiveGroundAdapter` is a model-internal reference implementation. It answers queries about the finite Ground while preserving known, unknown, and ambiguous transitions. It is not a physical sensor/actuator adapter. See `docs/DUPLEX_CHANNELS.md` and `examples/run_duplex_channel.py`.


## Evidence admission and Ground reconstruction

The experimental `vgi/evidence.py` layer separates retained channel observations from policy-admitted transition claims and finite compiled-replay certificates. Transition claims are bound to an Encounter, channel/protocol, source, and a transport-frame receipt. A declared quorum policy must be explicitly finalized before a transition is included in a Ground; unknown, ambiguous, pending, and conflicting events remain absent.

`GroundReconstructionVerifier` separately checks that compiled VGI matches direct Ground semantics over a caller-declared finite action-sequence corpus. Its certificate binds the exact Ground and context and does not claim completeness about an external system. See `docs/EVIDENCE_AND_RECONSTRUCTION.md`.


## Signal8 execution trace capture

The experimental `vgi/signal8_trace.py` adapter captures actual instruction
steps from an existing `SignalStateMachine`. Each successful event becomes an
observation-only ChannelMessage, retained Encounter, frame receipt, and
run-scoped `TransitionEvidence` claim. Before/after state identifiers are
computed from a declared runtime-configuration projection; the raw
`ExecutionEvent` preserves branch measurements and signal-valued writes
without decoding them to semantic integers.

The adapter does not apply an evidence policy, finalize transitions, or mutate
a Ground. A runtime fault is retained as a generic observation, while a
step-limited trace remains explicitly incomplete. A VGI machine observing its
own execution is not independent external corroboration. See
[`docs/SIGNAL8_EXECUTION_TRACE.md`](docs/SIGNAL8_EXECUTION_TRACE.md) and run
`python examples/run_signal8_execution_trace.py`.


### Capture completeness and cross-run comparability

Signal8 capture artifacts retain full before/after runtime configurations,
program/Ground definitions, and initial/final state snapshots. State IDs can
be recomputed from retained configurations. Run IDs remain provenance, while
structurally identical initial contexts share a context digest. Transport
sessions are scoped per capture to avoid frame-sequence collisions. This is
replay material, not a replay certificate.


## Independent Signal8 semantic reference

The canonical execution trace can now be checked by a separate finite semantic implementation. The reference interprets the retained instruction stream over the abstract cyclic group Z/8Z while separately propagating residual phase and error bounds. It does not call the runtime machine or Signal8 arithmetic backend.

    from vgi import verify_execution_reference

    report = verify_execution_reference(trace)
    print(report.to_dict())

The result is match, mismatch, or unsupported. Unsupported is important: a retained input whose uncertainty does not identify a unique Signal8 symbol is not forced into a semantic interpretation. A match checks the finite instruction semantics against the captured events and final state; it does not authenticate the source or establish physical hardware behavior.

See docs/INVARIANT_SPACE_EXPERIMENT.md for the observer-coordinate boundary result, the invariant stack, and the renewed Build 25–31 research path.


## Execution orbits and logical-time navigation

The experimental vgi/orbit.py module connects independently checked Signal8 execution traces to evidence-gated partial Grounds and fixed-policy orbit navigation.

~~~python
from vgi import (
    ExecutionOrbitAdapter, OrbitNavigator, verify_execution_reference,
)

report = verify_execution_reference(trace)
ingestion = ExecutionOrbitAdapter().ingest((trace,), (report,))
for source_state, action in sorted({
    (item.source_state, item.action)
    for item in ingestion.evidence_ledger.evidence
}):
    ingestion = ingestion.finalize(source_state, action)
ground = ingestion.build_ground()
policy = ingestion.derive_policy()
orbit = OrbitNavigator.compile(
    ground, policy, start_state=ground.initial_state,
    start_time=ingestion.initial_time,
)
future = orbit.state_at(ingestion.initial_time.advance(10**12))
~~~

Observation does not automatically admit a transition. The adapter retains original frames, Encounters, transport receipts, delivery reorder/duplicates/omissions, and failed attempts. Only explicitly finalized AUTHORIZED evidence enters the constructed Ground. A closed cycle is recognized only along known single-valued edges under one fixed state-to-action policy; only then can a distant logical tick be reduced modulo its period.

OrbitTimeCoordinate is an instruction-attempt coordinate, not wall time or elapsed duration. The navigator changes a virtual lookup coordinate; it does not change a host clock or execute an external process. See docs/ORBIT_NAVIGATION.md and run python examples/run_execution_orbit_navigation.py.

## Certified modular-affine fast-forward

For a selected closed orbit, VGI can validate a finite-ring affine generator against every retained edge and use homogeneous matrix exponentiation to reach a distant logical coordinate:

~~~python
from vgi.affine import AffineOrbitCertificate, ModularAffineMap

transform = ModularAffineMap(modulus=8, matrix=((2,),), offset=(0,))
certificate = AffineOrbitCertificate.certify(
    orbit, transform,
    {"s0": (1,), "s1": (2,), "s2": (4,), "s3": (0,)},
)
future = certificate.state_at(ingestion.initial_time.advance(10**12))
~~~

This does not make the entire Ground affine. The state encoding must be complete and injective over the closed orbit, and the candidate map must reproduce every retained transition. The certificate is bound to that exact orbit, Ground, fixed policy, and clock. [AFFINE_FAST_FORWARD.md](docs/AFFINE_FAST_FORWARD.md) explains the certificate boundary; run the example with `python examples/run_certified_affine_fast_forward.py`.
