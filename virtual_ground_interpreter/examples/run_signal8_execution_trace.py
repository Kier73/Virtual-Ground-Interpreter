"""Capture a Signal8 run, retain its provenance, and verify deterministic replay."""

import json

from vgi import (
    Instruction,
    Program,
    Signal8Backend,
    Signal8ExecutionAdapter,
    VirtualGroundInterpreter,
    verify_execution_replay,
)


def main():
    backend = Signal8Backend()
    interpreter = VirtualGroundInterpreter(backend=backend)
    adapter = Signal8ExecutionAdapter(interpreter)
    program = Program("signal8-observed-add", (
        Instruction("LOAD", {"dst": "left", "address": "input.left"}),
        Instruction("LOAD", {"dst": "right", "address": "input.right"}),
        Instruction("ADD", {"dst": "sum", "left": "left", "right": "right"}),
        Instruction("STORE", {"src": "sum", "address": "result"}),
        Instruction("EMIT", {"src": "sum", "label": "sum"}),
        Instruction("HALT"),
    ))
    initial_memory = {
        "input.left": backend.encode_symbol(3, observer=1),
        "input.right": backend.encode_symbol(5, observer=3),
    }

    observed = adapter.capture(
        program, initial_memory, trace_id="signal8-add-observed-001",
    )
    replayed = adapter.replay(
        observed, trace_id="signal8-add-replay-001",
    )
    verification = verify_execution_replay(observed, replayed)

    print(json.dumps({
        "observed_trace": observed.to_dict(),
        "replayed_trace": replayed.to_dict(),
        "replay_verification": verification.to_dict(),
        "interpretation": (
            "The replay checks the exact program, initial signal memory, Ground, "
            "and retained instruction path in the same VGI implementation. "
            "It establishes bounded reproducibility, not an independent semantic "
            "oracle or completeness about an external system."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
