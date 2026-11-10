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
