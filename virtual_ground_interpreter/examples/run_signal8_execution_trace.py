"""Capture and replay the actual Signal8 instruction stream without decoding outputs."""
import json

from vgi import (
    Instruction,
    Program,
    Signal8Backend,
    Signal8ExecutionAdapter,
    project_execution_transitions,
    verify_execution_replay,
)


def main():
    backend = Signal8Backend()
    interpreter_adapter = Signal8ExecutionAdapter()
    program = Program("signal8-add-trace", (
        Instruction("LOAD", {"dst": "a", "address": "input.a"}),
        Instruction("LOAD", {"dst": "b", "address": "input.b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("EMIT", {"src": "sum", "label": "sum"}),
        Instruction("HALT"),
    ))
    initial_memory = {
        "input.a": backend.encode_symbol(3, observer=1),
        "input.b": backend.encode_symbol(5, observer=3),
    }

    observed = interpreter_adapter.capture(
        program, initial_memory, trace_id="signal8-add-observed",
    )
    replay = interpreter_adapter.replay(
        observed, trace_id="signal8-add-replay",
    )
    replay_report = verify_execution_replay(observed, replay)
    projection = project_execution_transitions((observed, replay))

    print(json.dumps({
        "capture_status": observed.status,
        "program_fingerprint": observed.program_fingerprint,
        "ground_fingerprint": observed.ground_fingerprint,
        "captured_instruction_events": len(observed.entries),
        "retained_encounters": len(observed.encounters.encounters),
        "transport_frames": len(observed.entries),
        "replay": replay_report.to_dict(),
        "observed_transition_projection": projection.to_dict(),
        "interpretation": (
            "The projection groups only source/action/successor combinations witnessed "
            "by the two traces. Signal values remain phasors; no terminal integer decode "
            "is performed. This is evidence about this interpreter execution, not an "
            "authorization or complete description of an external system."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
