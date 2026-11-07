"""Command-line entry point for VGI verification and JSON programs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import Program, Signal8Backend, TaskCompiler, TaskSpec, VirtualGroundInterpreter
from .verification import verify_finite_ground


def _parse_input(spec: str, backend: Signal8Backend):
    if "=" not in spec:
        raise argparse.ArgumentTypeError("input must be ADDRESS=SYMBOL[@OBSERVER]")
    address, encoded = spec.split("=", 1)
    if not address:
        raise argparse.ArgumentTypeError("input address must be non-empty")
    if "@" in encoded:
        symbol_text, observer_text = encoded.split("@", 1)
        try:
            observer = int(observer_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("observer must be an integer") from exc
    else:
        symbol_text, observer = encoded, 1
    try:
        symbol = int(symbol_text)
        value = backend.encode_symbol(symbol, observer)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(f"invalid signal input {spec!r}: {exc}") from exc
    return address, value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vgi", description="Virtual Ground Interpreter")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("verify", help="run finite exhaustive checks for the declared Ground")
    compile_parser = sub.add_parser("compile", help="lower a declarative task JSON file to interpreter IR")
    compile_parser.add_argument("task", type=Path)
    compile_parser.add_argument("--output", type=Path, help="write the lowered program JSON to this path")

    run = sub.add_parser("run", help="execute a program JSON or declarative task JSON file")
    run.add_argument("program", type=Path)
    run.add_argument("--input", action="append", default=[], metavar="ADDRESS=SYMBOL[@OBSERVER]")
    run.add_argument("--max-steps", type=int, default=10_000)
    args = parser.parse_args(argv)

    if args.command in (None, "verify"):
        result = verify_finite_ground()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1

    backend = Signal8Backend()
    try:
        if args.command == "compile":
            task = TaskSpec.from_json(args.task.read_text(encoding="utf-8"))
            program = TaskCompiler().compile(task)
            rendered = program.to_json() + "\n"
            if args.output:
                args.output.write_text(rendered, encoding="utf-8")
                print(json.dumps({"compiled": True, "output": str(args.output),
                                  "instruction_count": len(program.instructions)}, indent=2))
            else:
                print(rendered, end="")
            return 0

        source = args.program.read_text(encoding="utf-8")
        document = json.loads(source)
        if isinstance(document, dict) and "instructions" in document:
            program = Program.from_dict(document)
        elif isinstance(document, dict) and "outputs" in document:
            program = TaskCompiler().compile(TaskSpec.from_dict(document))
        else:
            raise ValueError("input file must be a Program JSON or TaskSpec JSON document")
        memory = {}
        for raw in args.input:
            address, value = _parse_input(raw, backend)
            if address in memory:
                raise ValueError(f"duplicate input address {address!r}")
            memory[address] = value
        result = VirtualGroundInterpreter(backend=backend).execute(
            program, memory, max_steps=args.max_steps)
    except Exception as exc:
        print(f"vgi: {exc}", file=sys.stderr)
        return 2

    output = {
        "halted": result.halted,
        "observed_outputs": result.observed_outputs(backend),
        "signal_outputs": [{"label": e.label, "value": e.value.to_dict()} for e in result.outputs],
        "trace": result.trace_dicts(),
        "program_fingerprint": result.program_fingerprint,
        "ground_fingerprint": result.ground_fingerprint,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0
