from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "legacy" / "build24"))

from incremental_ground import StreamingGroundInducer, stream_from_teacher, build_summary
from latent_ground import fixture_grounds

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
ACTIONS = ("HOLD", "PROBE_A", "PROBE_B")


def save_json(name: str, data: dict) -> None:
    (REPORTS / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def observer_quotients() -> dict:
    ground = fixture_grounds()["coupled_six"]
    configurations = {
        "parity_only": (0,),
        "residue3_only": (1,),
        "joint": (0, 1),
    }
    rows = {}
    for name, channels in configurations.items():
        learner = StreamingGroundInducer(ACTIONS, channels, signature_mode="observation", max_horizon=8)
        stream_from_teacher(learner, ground, ["HOLD"] * 36, post_state_observation=True, channels=channels)
        rows[name] = {
            "observed_channels": list(channels),
            "predictive_contexts": learner.predictive_context_count,
            "history_horizon": learner.horizon,
            "known_transitions": learner.compile()["known_transition_count"],
            "unknown_transitions": len(learner.compile()["unknown_transitions"]),
            "status": learner.status,
            "evidence_check": learner.verify_observed_evidence(),
            "specification": learner.compile(),
        }
    return rows


def unobservable_case() -> dict:
    ground = fixture_grounds()["unobservable_eight"]
    learner = StreamingGroundInducer(ACTIONS, (0,), signature_mode="observation", max_horizon=8)
    stream_from_teacher(learner, ground, ["HOLD"] * 24, post_state_observation=True, channels=(0,))
    return build_summary(learner)


def delayed_horizon() -> dict:
    ground = fixture_grounds()["delayed_six"]
    rows = []
    for count in (1, 2, 3, 4, 5, 6, 12, 18):
        learner = StreamingGroundInducer(ACTIONS, (0,), signature_mode="mealy", max_horizon=8)
        stream_from_teacher(learner, ground, ["PROBE_A"] * count,
                            post_state_observation=False, channels=(0,))
        rows.append({
            "events": count,
            "horizon": learner.horizon,
            "predictive_contexts": learner.predictive_context_count,
            "collisions": len(learner._model.get("collisions", [])),
            "status": learner.status,
            "known_transitions": learner.compile()["known_transition_count"],
            "unknown_transitions": len(learner.compile()["unknown_transitions"]),
        })
    return {"fixture": "delayed_six", "mode": "Mealy/action-conditioned observation", "rows": rows}


def partial_ground_example() -> dict:
    ground = fixture_grounds()["coupled_six"]
    learner = StreamingGroundInducer(ACTIONS, (0, 1), signature_mode="observation", max_horizon=8)
    stream_from_teacher(learner, ground, ["HOLD"] * 24, post_state_observation=True, channels=(0, 1))
    spec = learner.compile()
    save_json("partial_ground_spec_example.json", spec)
    exploration = learner.choose_exploration_probe(learner.current_context, {
        "PROBE_A": {"cost": 2.0, "risk": 0.1, "side_effect": "reversible diagnostic operation"},
        "PROBE_B": {"cost": 0.5, "risk": 0.9, "side_effect": "high-impact operation"},
    }, max_risk=0.4)
    return {
        "summary": learner.snapshot(),
        "verification": learner.verify_observed_evidence(),
        "unknown_edges_are_explicit": spec["unknown_transitions"],
        "unknown_edge_exploration": exploration,
        "version_lineage": learner.version_lineage,
        "program_round_trip_fingerprint": __import__("incremental_ground").PartialExecutableGround.from_json(
            json.dumps(spec)).spec["fingerprint"],
    }


def asynchronous_ingestion() -> dict:
    learner = StreamingGroundInducer(ACTIONS, (0, 1), signature_mode="observation")
    learner.begin_action(0, "HOLD")
    learner.begin_action(1, "PROBE_A")
    learner.observe_channel(1, 1, 2, source="sensor-B")
    learner.observe_channel(1, 0, 1, source="sensor-A")
    waiting = learner.snapshot()
    learner.observe_channel(0, 1, 1, source="sensor-B")
    learner.observe_channel(0, 0, 0, source="sensor-A")
    return {"before_gap_closed": waiting, "after_gap_closed": learner.snapshot(),
            "event_order": [e.as_dict() for e in learner.records]}


def bounded_stream() -> dict:
    learner = StreamingGroundInducer(ACTIONS, (0,), max_events=64, max_horizon=4,
                                     completed_cache_limit=16, audit_limit=24)
    for i in range(200):
        learner.ingest_event(i, "HOLD", (i % 2,))
    return learner.snapshot()


def make_transition_csv(spec: dict) -> None:
    path = REPORTS / "observed_transition_table.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["context", "action", "status", "output", "successor", "support", "evidence_steps"])
        for q in spec["states"]:
            for action in spec["actions"]:
                edge = spec["transitions"].get(q, {}).get(action)
                if edge is None:
                    writer.writerow([q, action, "unknown", "", "", 0, ""])
                else:
                    writer.writerow([q, action, edge["status"], json.dumps(edge.get("output", edge.get("alternatives", []))),
                                     edge.get("successor", ""), edge.get("support", 0),
                                     json.dumps(edge.get("evidence_steps", []))])


def main() -> None:
    observers = observer_quotients()
    unobservable = unobservable_case()
    delayed = delayed_horizon()
    partial = partial_ground_example()
    async_result = asynchronous_ingestion()
    stream = bounded_stream()
    save_json("observer_quotients.json", observers)
    save_json("delayed_horizon_learning.json", delayed)
    save_json("unobservable_context_result.json", unobservable)
    save_json("asynchronous_ingestion.json", async_result)
    save_json("bounded_stream_result.json", stream)
    spec = json.loads((REPORTS / "partial_ground_spec_example.json").read_text(encoding="utf-8"))
    make_transition_csv(spec)
    results = {
        "build": 26,
        "status": "complete",
        "evidence_class": "synthetic deterministic finite-state streaming experiments",
        "observer_quotients": {k: {key: v[key] for key in ("predictive_contexts", "history_horizon", "known_transitions", "unknown_transitions", "status")}
                               for k, v in observers.items()},
        "unobservable_eight": {k: unobservable[k] for k in ("predictive_contexts", "known_transitions", "unknown_transitions", "status", "evidence_check")},
        "delayed_horizon": delayed,
        "partial_ground": partial,
        "asynchronous_ingestion": async_result,
        "bounded_stream": stream,
        "limitations": [
            "action alphabet and selected channel schema are supplied by the connector",
            "the learner induces finite-horizon history contexts from a single non-resettable stream",
            "context quotient is provisional; finite evidence cannot prove global predictive equivalence",
            "unknown action/context pairs remain explicit and are not defaulted",
            "deterministic exact integer observations are assumed; stochastic/noisy dynamics are not learned",
            "Mealy and post-action observation signatures are distinct interface contracts",
            "no physical sensor stream or TAPS recording was processed",
        ],
    }
    save_json("build_26_results.json", results)
    print(json.dumps({"status": "complete", "report": str(REPORTS / "build_26_results.json"),
                      "observer_quotients": results["observer_quotients"],
                      "bounded_stream": stream}, indent=2))


if __name__ == "__main__":
    main()
