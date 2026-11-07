from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vgi import Signal8Backend, TaskSpec, VirtualGroundInterpreter

backend = Signal8Backend()
task = TaskSpec.from_json((ROOT / "examples" / "conditional_select.task.json").read_text())

# Inputs may arrive in different observer coordinates. No integer conversion
# occurs inside the machine; observation happens only after HALT.
memory = {
    "input.a": backend.encode_symbol(3, observer=1),
    "input.b": backend.encode_symbol(5, observer=3),
}

interpreter = VirtualGroundInterpreter()
program = interpreter.compile_task(task)
result = interpreter.interpret(task, memory)
print(json.dumps({
    "ground": interpreter.ground.ground_id,
    "halted": result.halted,
    "observed_outputs": result.observed_outputs(backend),
    "trace": result.trace_dicts(),
}, indent=2))
