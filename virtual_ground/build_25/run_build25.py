from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
B24 = ROOT / "legacy" / "build24"
sys.path.insert(0, str(B24))
sys.path.insert(0, str(ROOT))

from latent_ground import LearnedMealyGround
from online_ground import (
    ClockFit, Conflict, GroundVersionMonitor, LocalClockRegistry,
    OnlineBeliefTracker, ProbeProfile, SafeProbeScheduler,
)

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load(name: str) -> LearnedMealyGround:
    path = B24 / "reports" / f"ground_spec_{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return LearnedMealyGround.from_dict(data["specification"])


def write(name: str, data) -> None:
    (REPORTS / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    machine = load("coupled_six__joint")
    # The synthetic oracle starts at q2, but the online learner is intentionally
    # not told this and has no reset/teacher object.
    tracker = OnlineBeliefTracker(machine, history_limit=32, completed_cache_limit=16)
    clocks = LocalClockRegistry()
    clocks.add_anchor("sensor-A", 10.0, 0.0)
    clocks.add_anchor("sensor-A", 20.0, 10.0)
    clocks.add_anchor("sensor-B", 100.0, 0.0)
    clocks.add_anchor("sensor-B", 120.0, 10.0)
    snapshots = [{"event": "stream_open", **tracker.snapshot()}]

    # Action 0: HOLD. Sensor B reports first; sensor A is delayed. Both local
    # clocks map the step's paired event to reference time 5, but the join uses
    # the explicit action-step identity rather than timestamp equality.
    tracker.begin_action(0, "HOLD")
    snapshots.append({"event": "action_0_issued", **tracker.snapshot()})
    event_b = clocks.add_event(source="sensor-B", source_sequence=1, local_timestamp=110.0,
                              channel=1, value=2, step_id=0)
    clocks.deliver(tracker, event_b)
    snapshots.append({"event": "step_0_sensor_B", **tracker.snapshot()})
    event_a = clocks.add_event(source="sensor-A", source_sequence=1, local_timestamp=15.0,
                              channel=0, value=0, step_id=0)
    clocks.deliver(tracker, event_a)
    snapshots.append({"event": "step_0_sensor_A", **tracker.snapshot()})

    # Action 1 follows; sensor B for step 1 is delivered before sensor A.
    tracker.begin_action(1, "PROBE_A")
    event_b1 = clocks.add_event(source="sensor-B", source_sequence=2, local_timestamp=112.0,
                                channel=1, value=0, step_id=1)
    clocks.deliver(tracker, event_b1)
    snapshots.append({"event": "step_1_sensor_B", **tracker.snapshot()})
    event_a1 = clocks.add_event(source="sensor-A", source_sequence=2, local_timestamp=16.0,
                                channel=0, value=1, step_id=1)
    clocks.deliver(tracker, event_a1)
    snapshots.append({"event": "step_1_sensor_A", **tracker.snapshot()})
    write("unknown_start_online_trace.json", {
        "test_oracle_initial_context_not_available_to_learner": "q2",
        "action_sequence": ["HOLD", "PROBE_A"],
        "snapshots": snapshots,
        "final_evidence": tracker.export_evidence(),
    })

    # An unkeyed event is deliberately not fused with either stream.
    unmatched = clocks.add_event(source="sensor-C", source_sequence=1, local_timestamp=115.0,
                                 channel=2, value=1, step_id=None)
    write("local_clock_alignment.json", {
        "clock_registry": clocks.summary(),
        "sensor_A_mapped_time": clocks.map_time("sensor-A", 15.0),
        "sensor_B_mapped_time": clocks.map_time("sensor-B", 110.0),
        "same_step_join_A": event_a["join_status"],
        "same_step_join_B": event_b["join_status"],
        "unkeyed_sensor_C": unmatched["join_status"],
        "interpretation": "Per-source order is retained; explicit step identity joins observations; raw timestamps alone do not establish cross-source correspondence.",
    })

    profiles = {
        "HOLD": ProbeProfile(cost=1.0, risk=0.01, side_effect="passive observation"),
        "PROBE_A": ProbeProfile(cost=2.0, risk=0.10, side_effect="small reversible transition"),
        "PROBE_B": ProbeProfile(cost=0.5, risk=0.90, side_effect="high-impact transition"),
    }
    scheduler = SafeProbeScheduler(machine, max_risk=0.35, risk_weight=2.0)
    write("safe_probe_selection.json", scheduler.choose(machine.states, profiles))

    # A single sensor corruption quarantines the ground but does not cause a
    # revision proposal. Independent contradictions across actions do.
    transient = OnlineBeliefTracker(machine)
    transient.begin_action(0, "HOLD")
    transient.observe_channel(0, 0, 99, source="sensor-A")
    write("single_conflict_quarantine.json", transient.export_evidence())

    version_monitor = GroundVersionMonitor("fixture-ground-v1", proposal_threshold=2)
    version_monitor.record(Conflict(4, "HOLD", ((0, 99),), (), "sensor-A", "outside_predicted_output_support"))
    version_monitor.record(Conflict(7, "PROBE_A", ((1, 99),), (), "sensor-B", "outside_predicted_output_support"))
    write("persistent_change_proposal.json", version_monitor.summary())

    # Delayed distinguishing evidence, with no reset or hidden initial mode.
    delayed = load("delayed_six__available")
    delayed_tracker = OnlineBeliefTracker(delayed)
    delayed_trace = []
    for i in range(5):
        delayed_tracker.begin_action(i, "HOLD")
        delayed_tracker.observe_channel(i, 0, 0, source="rare-event-sensor")
        delayed_trace.append({"step": i, "action": "HOLD", "belief": list(delayed_tracker.belief)})
    before_probe = delayed_tracker.snapshot()
    delayed_tracker.begin_action(5, "PROBE_A")
    delayed_tracker.observe_channel(5, 0, 1, source="rare-event-sensor")
    after_probe = delayed_tracker.snapshot()
    write("delayed_context_online.json", {
        "trace": delayed_trace,
        "belief_before_distinguishing_probe": before_probe,
        "belief_after_distinguishing_probe": after_probe,
        "note": "The physical starting mode is not exposed to the tracker; the observable context is only narrowed after the distinguishing event.",
    })

    # Long stream memory compaction run.
    long_stream = OnlineBeliefTracker(machine, history_limit=64, completed_cache_limit=32)
    for i in range(250):
        q = long_stream.belief[0]
        out = machine.outputs[q]["HOLD"]
        long_stream.begin_action(i, "HOLD")
        long_stream.observe_channel(i, 0, out[0], source="A")
        long_stream.observe_channel(i, 1, out[1], source="B")
    write("bounded_memory_stream.json", long_stream.snapshot())

    results = {
        "build": 25,
        "status": "complete",
        "evidence_class": "synthetic finite-state online tracking experiments",
        "tests_in_primary_suite": 34,
        "inherited_build24_tests": 17,
        "unknown_start": {
            "initial_belief_size": 6,
            "belief_after_first_partial_channel": snapshots[2]["belief"],
            "belief_after_both_channels": snapshots[3]["belief"],
            "belief_after_second_action": tracker.snapshot()["belief"],
            "final_status": tracker.status,
        },
        "async_local_clocks": clocks.summary(),
        "probe_scheduler": scheduler.choose(machine.states, profiles),
        "single_conflict_status": transient.status,
        "persistent_conflict_status": version_monitor.status,
        "long_stream_memory": long_stream.snapshot(),
        "limitations": [
            "Build 24 still supplies the learned finite predictive machine; Build 25 does not yet learn a new transition law online.",
            "Actions and channel schemas are known; raw action/sensor discovery is not implemented.",
            "The online model is deterministic; stochastic observation likelihoods are not implemented.",
            "Cross-source events are joined only by explicit step identity or separately calibrated clocks; raw timestamps are never treated as shared time.",
            "Ground revision is proposed after independent conflicts but is never automatically committed.",
            "Probe selection uses one-step output information gain with cost/risk penalties; it is not a globally optimal risk-sensitive control policy.",
        ],
    }
    write("build_25_results.json", results)


if __name__ == "__main__":
    main()
