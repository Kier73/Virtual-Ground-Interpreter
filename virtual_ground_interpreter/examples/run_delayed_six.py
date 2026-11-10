"""Run the Build 24 delayed-six Ground through direct and compiled semantics."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from vgi.transitions import GroundTransitionSystem, TransitionCompiler, differential_verify

ROOT = Path(__file__).resolve().parent
fixture = json.loads((ROOT / "delayed_six_predictive_ground.json").read_text(encoding="utf-8"))
ground = GroundTransitionSystem.from_predictive_mealy_dict(fixture)
counterexample = ("HOLD", "HOLD", "HOLD", "HOLD", "HOLD", "PROBE_A")
direct = ground.run(counterexample)
compiled = TransitionCompiler().compile(ground, len(counterexample))
realized = compiled.execute(counterexample)

short_words = tuple(itertools.product(ground.actions, repeat=2))
report = differential_verify(ground, (*short_words, counterexample))
print(json.dumps({
    "fixture": "Build 24 delayed_six",
    "ground_fingerprint": ground.fingerprint,
    "complete": ground.complete,
    "counterexample": list(counterexample),
    "direct_state_trace": list(direct.state_trace),
    "compiled_state_trace": list(realized.state_trace),
    "direct_outputs": [list(x) for x in direct.outputs],
    "compiled_outputs": [list(x) for x in realized.outputs],
    "final_state": realized.final_state,
    "program_instruction_count": len(compiled.program.instructions),
    "differential_verification": report,
}, indent=2, sort_keys=True))
if report["status"] != "PASS":
    raise SystemExit(1)
