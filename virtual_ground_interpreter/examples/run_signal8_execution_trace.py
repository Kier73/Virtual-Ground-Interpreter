"""Capture a real Signal8 execution as VGI observations and evidence."""

import json

from vgi import (
    Instruction, Program, Signal8Backend, Signal8ExecutionAdapter,
    VirtualGroundInterpreter,
)


def main():
    backend = Signal8Backend()
    interpreter = VirtualGroundInterpreter()
    program = Program("signal8-observed-add", (
        Instruction("LOAD", {"dst": "left", "address": "input.left"}),
        Instruction("LOAD", {"dst": "right", "address": "input.right"}),
        Instruction("ADD", {"dst": "sum", "left": "left", "right": "right"}),
        Instruction("STORE", {"src": "sum", "address": "result"}),
        Instruction("EMIT", {"src": "sum", "label": "sum"}),
        Instruction("HALT"),
    ))
    machine = interpreter.instantiate(program, {
        "input.left": backend.encode_symbol(3, observer=1),
        "input.right": backend.encode_symbol(5, observer=3),
    })
    capture = Signal8ExecutionAdapter().capture(
        machine, run_id="signal8-add-demo-001",
    )
    report = capture.to_dict()
    report["interpretation"] = (
        "Successful instructions are retained as concrete runtime transition "
        "observations. Raw phasors remain in the event records; capture performs "
        "no semantic integer decoding, evidence-policy finalization, or Ground mutation."
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
