from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from ground_diagnosis import (
    TransitionSample, HistoryTransition, ConflictRecord, DiagnosticEvidence,
    SelfConstructingGroundInterpreter, discover_operation_candidates,
    compile_ground, PartialGenerativeGround, diagnose_history_collision,
    isolated_spikes, diagnose_sensor_shift, detect_regime_change,
    diagnose_competing_explanations, choose_discriminating_probe, build_report,
)

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def write_json(name: str, data) -> None:
    (REPORTS / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def operation_discovery() -> dict:
    # The learner receives no semantic action names, only event-token windows.
    samples = []
    step = 0
    for x in range(10):
        samples.append(TransitionSample(step, (x,), ("edge_04", "pulse_12"), (x + 1,))); step += 1
        samples.append(TransitionSample(step, (x,), ("ring_09",), (x + 3,))); step += 1
    train = samples[:14]  # x=0..6 for both operators; x=7..9 held out
    test = samples[14:]
    learner = SelfConstructingGroundInterpreter(min_support=2)
    snapshots = []
    for s in train:
        snapshots.append(learner.ingest(s))
    spec = learner.compile()
    model = PartialGenerativeGround(spec)
    predictions = []
    for s in test:
        p = model.predict(s.before, s.event_tokens)
        predictions.append({"step": s.step, "before": list(s.before),
                            "event_tokens": list(s.event_tokens), "expected": list(s.after),
                            "prediction": p, "correct": p.get("next_state") == list(s.after)})
    (REPORTS / "inferred_ground_spec.json").write_text(model.to_json() + "\n", encoding="utf-8")
    with (REPORTS / "observed_transition_windows.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["step", "before", "event_tokens", "after"])
        for s in samples:
            w.writerow([s.step, json.dumps(s.before), json.dumps(s.event_tokens), json.dumps(s.after)])
    return {"training_windows": len(train), "held_out_windows": len(test),
            "training_states": sorted({s.before[0] for s in train}),
            "held_out_states": sorted({s.before[0] for s in test}),
            "learner_snapshot": learner.snapshot(),
            "operations": spec["operations"],
            "held_out_predictions": predictions,
            "held_out_correct": sum(x["correct"] for x in predictions),
            "held_out_total": len(predictions),
            "boundary": "Constant-delta extrapolation is supported by multiple observed pre-states but remains a finite-evidence hypothesis."}


def diagnostics() -> dict:
    noisy = {"trace": [1, 2, 99, 2, 3, 4], "spike_indices": isolated_spikes([1,2,99,2,3,4]),
             "diagnosis": diagnose_competing_explanations(DiagnosticEvidence(
                 isolated_spike_recovered=True, independent_channels_stable=True))}
    history_short = [HistoryTransition((0, 0), ("evt_a",), (1,)),
                     HistoryTransition((1, 0), ("evt_a",), (2,))]
    insufficient = diagnose_history_collision(history_short, max_horizon=2)
    hidden_or_stochastic = diagnose_history_collision([
        HistoryTransition((0, 0), ("evt_a",), (1,)),
        HistoryTransition((0, 0), ("evt_a",), (2,)),
    ], max_horizon=4)
    sensor_shift = diagnose_sensor_shift(
        {"sensor_A": [10,11,12,13], "reference": [5,5,5,5]},
        {"sensor_A": [13,14,15,16], "reference": [5,5,5,5]},
        reference_channels=["reference"])
    remap_unresolved = diagnose_sensor_shift(
        {"sensor_A": [10,11,12,13]}, {"sensor_A": [13,14,15,16]}, reference_channels=[])
    baseline = {("q0", "opA"): (0,), ("q1", "opB"): (1,), ("q2", "opA"): (0,)}
    conflicts = []
    for step in (20,21,22):
        conflicts.extend([
            ConflictRecord(step, "q0", "opA", (0,), (2,), "sensor_A"),
            ConflictRecord(step, "q1", "opB", (1,), (3,), "sensor_B"),
            ConflictRecord(step, "q2", "opA", (0,), (2,), "sensor_A"),
        ])
    regime = detect_regime_change(baseline, conflicts, min_context_operations=2, min_repeats_per_key=2)
    e = DiagnosticEvidence(multi_context_persistent_transition_conflicts=True,
                           multiple_sensors_corroborate_conflicts=True)
    regime_diagnosis = diagnose_competing_explanations(e)
    new_state = diagnose_competing_explanations(DiagnosticEvidence(
        novel_observation_repeated=4, independent_channels_confirm_novelty=True,
        novel_state_has_stable_transition_profile=True))
    unknown_operation = diagnose_competing_explanations(DiagnosticEvidence(
        recurring_unseen_event_signature=True, event_signature_effect_consistent=True))
    return {"measurement_noise": noisy, "insufficient_history": insufficient,
            "hidden_vs_stochastic": hidden_or_stochastic,
            "sensor_calibration_shift": sensor_shift,
            "sensor_shift_without_reference": remap_unresolved,
            "persistent_regime_change": regime,
            "regime_explanation_ranking": regime_diagnosis,
            "new_state_candidate": new_state, "new_operation_candidate": unknown_operation}


def probe_selection() -> dict:
    hypotheses = ["sensor_remap", "new_predictive_state", "ground_regime_change"]
    probes = {
        "known_reference_input": {"sensor_remap": "offset_persists", "new_predictive_state": "reference_matches",
                                  "ground_regime_change": "reference_matches"},
        "repeat_same_transition": {"sensor_remap": "same_offset", "new_predictive_state": "new_profile",
                                   "ground_regime_change": "new_profile"},
        "cross_context_probe": {"sensor_remap": "channel_only", "new_predictive_state": "local_context",
                                 "ground_regime_change": "multiple_contexts"},
    }
    profiles = {"known_reference_input": {"cost": 1.0, "risk": 0.02},
                "repeat_same_transition": {"cost": 1.5, "risk": 0.03},
                "cross_context_probe": {"cost": 2.0, "risk": 0.05}}
    selected = choose_discriminating_probe(hypotheses, probes, profiles, max_risk=0.2)
    unsafe = choose_discriminating_probe(hypotheses, probes,
        {k: {"cost": v["cost"], "risk": 0.9} for k,v in profiles.items()}, max_risk=0.2)
    return {"hypotheses": hypotheses, "selected_probe": selected,
            "declines_unsafe_alternatives": unsafe}


def open_world_counterexample() -> dict:
    # The inferred +1 operator fits x=0..5 but fails at a held-out boundary
    # where a different law is used. This must be a validation failure, not
    # silently accepted as a new global operation law.
    train = [TransitionSample(i, (i,), ("drift_token",), (i+1,)) for i in range(6)]
    held = TransitionSample(99, (6,), ("drift_token",), (9,))
    candidates = discover_operation_candidates(train)
    spec = compile_ground(train, candidates)
    pred = PartialGenerativeGround(spec).predict(held.before, held.event_tokens)
    correct = pred.get("next_state") == list(held.after)
    return {"training_effect": "+1", "held_out_before": list(held.before),
            "held_out_observed_after": list(held.after), "prediction": pred,
            "held_out_correct": correct,
            "action": "reject global law for this validation scope; retain a counterexample and consider a context-conditioned rule or ground revision"}


def main() -> None:
    operation = operation_discovery()
    diag = diagnostics()
    probes = probe_selection()
    ood = open_world_counterexample()
    write_json("operation_discovery.json", operation)
    write_json("competing_explanations.json", diag)
    write_json("discriminating_probe_selection.json", probes)
    write_json("open_world_counterexample.json", ood)
    results = {
        "build": 27,
        "status": "complete",
        "evidence_class": "synthetic integer-vector transition windows and rule-based diagnostic cases",
        "operation_discovery": {"candidate_count": operation["learner_snapshot"]["candidate_operation_count"],
                                "held_out_correct": operation["held_out_correct"],
                                "held_out_total": operation["held_out_total"]},
        "diagnostic_statuses": {
            "noise": diag["measurement_noise"]["diagnosis"]["primary_explanation"],
            "history": diag["insufficient_history"]["status"],
            "hidden_vs_stochastic": diag["hidden_vs_stochastic"]["status"],
            "sensor_shift": diag["sensor_calibration_shift"]["status"],
            "sensor_shift_no_reference": diag["sensor_shift_without_reference"]["status"],
            "regime": diag["persistent_regime_change"]["status"],
        },
        "probe_choice": probes["selected_probe"]["selected_probe"],
        "open_world_validation_correct": ood["held_out_correct"],
        "limitations": [
            "event windows are supplied by the observation interface; raw waveform boundary discovery is not implemented",
            "event token strings are opaque symbols; semantic action names are not supplied or inferred",
            "operation discovery uses recurrent exact event-window signatures, not arbitrary subsequence grammar induction",
            "state values are discrete integer observation vectors; continuous latent variable discovery is not implemented",
            "diagnostic rank scores are ordinal heuristics, not calibrated probabilities",
            "hidden predictive variable and stochastic transition can remain observationally equivalent",
            "sensor remap and physical state change remain ambiguous without independent calibration references",
            "ground revision is proposed only; this build never automatically commits a new ground",
            "constant-delta operation extrapolation is a hypothesis supported by finite examples, not proof outside tested domain",
            "no physical sensor data was processed",
        ],
    }
    write_json("build_27_results.json", results)
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
