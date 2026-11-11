"""Demonstrate evidence-bound execution-orbit construction and logical-time navigation.

From this package directory:
    python examples/run_execution_orbit_navigation.py

The example advances a virtual logical coordinate. It does not sleep, alter a
host clock, or mutate an external process.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vgi import (  # noqa: E402
    Instruction,
    Program,
    Signal8Backend,
    Signal8ExecutionAdapter,
    VirtualGroundInterpreter,
    verify_execution_reference,
)
from vgi.orbit import (  # noqa: E402
    ExecutionOrbitAdapter,
    OrbitNavigator,
)


def build_report() -> dict:
    backend = Signal8Backend()
    runtime = Signal8ExecutionAdapter(VirtualGroundInterpreter(backend=backend))
    program = Program("logical-orbit-demo", (
        Instruction("LOAD", {"dst": "x", "address": "x"}),
        Instruction("JUMP", {"target": 0}),
        Instruction("HALT"),
    ))
    trace = runtime.capture(
        program,
        {"x": backend.encode_symbol(5, observer=1)},
        trace_id="logical-orbit-demo-trace",
        max_steps=12,
    )

    reference = verify_execution_reference(trace)
    if reference.status != "match":
        raise RuntimeError(
            "independent semantic reference did not match: "
            + "; ".join(reference.mismatches)
        )

    ingestion = ExecutionOrbitAdapter().ingest(
        (trace,),
        (reference,),
        clock_id="logical-orbit-demo-clock",
        base_tick=40,
    )

    # Evidence is not automatically admitted. Finalize each distinct observed
    # state/action event under the explicit policy before constructing Ground.
    observed_events = sorted({
        (item.source_state, item.action)
        for item in ingestion.evidence_ledger.evidence
    })
    for source_state, action in observed_events:
        ingestion = ingestion.finalize(source_state, action)

    ground = ingestion.build_ground()
    policy = ingestion.derive_policy()
    orbit = OrbitNavigator.compile(
        ground,
        policy,
        start_state=ground.initial_state,
        start_time=ingestion.initial_time,
    )

    distant_time = ingestion.initial_time.advance(10**12)
    located = orbit.state_at(distant_time)
    target_state = orbit.states[2]
    target = orbit.locate_state(target_state, from_time=distant_time)

    return {
        "format": "VGI-ExecutionOrbitDemo-1",
        "reference": reference.to_dict(),
        "ingestion": {
            "fingerprint": ingestion.fingerprint,
            "traces": [item.to_dict() for item in ingestion.trace_summaries],
            "observed_events": len(ingestion.evidence_ledger.evidence),
            "finalized_events": len(ingestion.evidence_ledger.finalizations),
            "ground_fingerprint": ground.fingerprint,
            "ground_complete": ground.complete,
            "unknown_pairs": len(ground.unknown_pairs),
            "duplicate_deliveries": ingestion.duplicate_count,
            "missing_deliveries": ingestion.missing_count,
        },
        "orbit": {
            "fingerprint": orbit.fingerprint,
            "closed": orbit.closed,
            "start_state": orbit.start_state,
            "states": list(orbit.states),
            "actions": [item.action for item in orbit.steps],
            "cycle_start_index": orbit.cycle_start_index,
            "cycle_period": orbit.cycle_period,
        },
        "future_navigation": {
            "requested_time": distant_time.to_dict(),
            "status": located.status,
            "state": located.state,
            "method": located.method,
            "skipped_cycles": located.skipped_cycles,
            "skipped_steps": located.skipped_steps,
            "path_fingerprint": located.path_fingerprint,
        },
        "future_target": {
            "target_state": target_state,
            "from_time": distant_time.to_dict(),
            "status": target.status,
            "resolved_time": None if target.resolved_time is None else target.resolved_time.to_dict(),
            "method": target.method,
            "skipped_cycles": target.skipped_cycles,
        },
        "scope": [
            "the captured trace is observation; the independent reference checks its bounded Signal8 semantics",
            "the partial Ground contains only explicitly finalized, authorized evidence",
            "the policy is fixed and deterministic for this finite orbit",
            "future skipping is valid only because the finite state/action path closes and replays",
            "the logical tick is not wall-clock time and no external process is changed",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
