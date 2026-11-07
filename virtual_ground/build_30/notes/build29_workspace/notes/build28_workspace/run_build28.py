from __future__ import annotations

import csv
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from stream_ground import (
    Checkpoint, ContinuousTrace, Segment, compare_segments, discover_and_compile,
    mine_motifs, segment_stream, build_effect_equations, compile_partial_ground,
    predict_checkpoint_deltas, serialize_trace, verify_ground_fingerprint,
    permutation_filter_motifs,
)

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# Opaque event signatures. These labels are generated fixture symbols; their
# semantic meanings are available only to the evaluator, not to the learner.
OPS = {
    "A": (("pulse", "edge", "tail"), (1, 0)),
    "B": (("ramp", "tick"), (0, 2)),
    "C": (("pulse", "bend", "tail"), (-1, 1)),
    "D": (("hum", "click"), (0, 0)),  # recurrent decoy motif
}


def generate_trace(trace_id: str, seed: int, *, n_ops: int = 24) -> tuple[ContinuousTrace, list[tuple[int, int, tuple[str, ...]]], dict]:
    rng = random.Random(seed)
    tokens: list[str] = []
    state = [50, 50]
    checkpoints = [Checkpoint(0, tuple(state))]
    truth: list[tuple[int, int, tuple[str, ...]]] = []
    op_names: list[str] = []
    # Measurement offsets are periodic-ish but randomly dithered and are not
    # aligned to operation boundaries.
    next_sample = rng.randint(7, 10)
    noise_counter = 0
    for idx in range(n_ops):
        name = rng.choices(["A", "B", "C", "D"], weights=[0.30, 0.27, 0.28, 0.15])[0]
        sig, delta = OPS[name]
        start = len(tokens)
        for token in sig:
            tokens.append(token)
            offset = len(tokens)
            if offset == start + len(sig):
                state[0] += delta[0]
                state[1] += delta[1]
            while offset >= next_sample:
                checkpoints.append(Checkpoint(next_sample, tuple(state)))
                next_sample += rng.randint(7, 10)
        end = len(tokens)
        truth.append((start, end, sig))
        op_names.append(name)
        # Insert unique background material so that cross-operation n-grams do
        # not masquerade as operations. Background tokens carry no state effect.
        noise_counter += 1
        tokens.append(f"ambient_{trace_id}_{noise_counter}")
        if rng.random() < 0.35:
            noise_counter += 1
            tokens.append(f"drift_{trace_id}_{noise_counter}")
        offset = len(tokens)
        while offset >= next_sample:
            checkpoints.append(Checkpoint(next_sample, tuple(state)))
            next_sample += rng.randint(7, 10)
    if checkpoints[-1].offset != len(tokens):
        checkpoints.append(Checkpoint(len(tokens), tuple(state)))
    trace = ContinuousTrace(trace_id, tuple(tokens), tuple(checkpoints))
    return trace, truth, {"operation_names": op_names, "final_state": state}


def write_json(name: str, obj) -> None:
    (REPORTS / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    train_pairs = [generate_trace(f"train_{i:02d}", 8000+i) for i in range(12)]
    test_pairs = [generate_trace(f"test_{i:02d}", 9000+i) for i in range(5)]
    train = [x[0] for x in train_pairs]
    test = [x[0] for x in test_pairs]
    truth = {x[0].trace_id: x[1] for x in train_pairs + test_pairs}

    learned = discover_and_compile(train, min_len=2, max_len=4,
                                    min_occurrences=5, min_trace_support=3,
                                    top_k=5, ambiguity_margin=0.40,
                                    permutation_trials=31, permutation_seed=28028)
    motifs = learned["motifs"]
    train_segs = learned["segmentations"]
    # The held-out segmentation uses only the learned training motifs.
    test_segs = {tr.trace_id: segment_stream(tr, motifs, top_k=5, ambiguity_margin=0.40) for tr in test}

    segmentation_metrics = []
    all_predicted = 0
    all_truth = 0
    all_tp = 0
    for tr in train + test:
        seg = (train_segs if tr.trace_id.startswith("train_") else test_segs)[tr.trace_id]
        if seg.best:
            m = compare_segments(seg.best.segments, truth[tr.trace_id])
            segmentation_metrics.append({"trace_id": tr.trace_id, "status": seg.status, **m})
            all_predicted += m["predicted"]
            all_truth += m["truth"]
            all_tp += m["true_positive"]

    # Recompute effects using training traces only. Test checkpoints remain hidden.
    fit = build_effect_equations(train, train_segs, motifs)
    ground = compile_partial_ground(motifs, train_segs, fit)
    model_predictions = predict_checkpoint_deltas(test, test_segs, ground, motifs)
    # Executable JSON round-trip: the loaded ground must preserve its fingerprint.
    from stream_ground import ExecutablePartialGround
    executable = ExecutablePartialGround.from_json(json.dumps(ground, sort_keys=True))
    execution_examples = []
    for op in ground["operations"]:
        if op["status"] in ("candidate_operation", "recurrent_zero_effect_motif"):
            execution_examples.append({"signature": op["signature"],
                "result": executable.apply([50, 50], op["signature"])})
    write_json("executable_ground_roundtrip.json", {
        "fingerprint_valid": executable.spec["fingerprint"] == ground["fingerprint"],
        "examples": execution_examples,
        "unknown_operation": executable.apply([50,50], ["not", "seen"])})

    # Training segmentation metrics and held-out state-delta prediction.
    train_status = {k: v.status for k, v in train_segs.items()}
    test_status = {k: v.status for k, v in test_segs.items()}
    write_json("learned_motifs.json", [m.as_dict() for m in motifs])
    write_json("nested_submotifs.json", learned["nested_submotifs"])
    write_json("permutation_motif_audit.json", learned["permutation_audit"])
    write_json("training_segmentations.json", {k: v.as_dict() for k, v in train_segs.items()})
    write_json("heldout_segmentations.json", {k: v.as_dict() for k, v in test_segs.items()})
    write_json("partial_virtual_ground.json", ground)
    write_json("checkpoint_effect_fit.json", fit)
    write_json("heldout_checkpoint_predictions.json", model_predictions)
    write_json("synthetic_evaluation_truth_only.json", {
        "warning": "Evaluation-only hidden generator labels. Never passed to learner.",
        "operations": {k: {"signature": list(v[0]), "delta": list(v[1])} for k, v in OPS.items()},
        "traces": {k: {"segments": [[a,b,list(sig)] for a,b,sig in v],
                       "operation_names": next(meta["operation_names"] for tr,_,meta in train_pairs+test_pairs if tr.trace_id == k)}
                    for k,v in truth.items()},
    })
    with (REPORTS / "continuous_stream_inputs.jsonl").open("w", encoding="utf-8") as f:
        for tr in train + test:
            f.write(json.dumps({"split": "train" if tr.trace_id.startswith("train_") else "heldout",
                                **serialize_trace(tr)}, sort_keys=True) + "\n")

    # Shuffled negative control: destroys local ordered motifs while preserving token frequencies.
    shuffled = []
    for i, tr in enumerate(train):
        toks = list(tr.tokens)
        random.Random(3000+i).shuffle(toks)
        shuffled.append(ContinuousTrace(f"shuffle_{i:02d}", tuple(toks), tr.checkpoints))
    shuffled_motifs, _ = mine_motifs(shuffled, min_len=2, max_len=4,
                                     min_occurrences=5, min_trace_support=3)
    shuffled_kept, shuffled_audit = permutation_filter_motifs(
        shuffled, shuffled_motifs, trials=31, seed=38028)
    write_json("shuffled_control_permutation_audit.json", shuffled_audit)

    # Ambiguous segmentation fixture: AB may be an operation, while ABC may be
    # another operation or AB followed by background C. Preserve both parses.
    amb_traces = []
    for i in range(5):
        amb_traces.append(ContinuousTrace(f"amb_ab_{i}", ("a", "b", f"n{i}"),
                          (Checkpoint(0,(0,)), Checkpoint(3,(1,)))))
    for i in range(5):
        amb_traces.append(ContinuousTrace(f"amb_abc_{i}", ("a", "b", "c", f"m{i}"),
                          (Checkpoint(0,(0,)), Checkpoint(4,(2,)))))
    amb_motifs, amb_nested = mine_motifs(amb_traces, min_len=2, max_len=3,
                                         min_occurrences=4, min_trace_support=3)
    amb_target = ContinuousTrace("amb_target", ("a", "b", "c"),
                                 (Checkpoint(0,(0,)), Checkpoint(3,(2,))))
    amb_seg = segment_stream(amb_target, amb_motifs, top_k=5, ambiguity_margin=0.50)
    write_json("ambiguity_fixture.json", {"motifs": [m.as_dict() for m in amb_motifs],
                                            "nested": amb_nested, "segmentation": amb_seg.as_dict()})

    # Ablation/decoy control: recurrent decoy motif should be segmented but have zero learned effect.
    operation_rows = []
    for m in motifs:
        op = next(x for x in ground["operations"] if x["operation_id"] == m.motif_id)
        operation_rows.append({**m.as_dict(), "effect": op["effect"], "status": op["status"]})
    with (REPORTS / "operation_catalog.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["motif_id", "signature", "length", "occurrences", "trace_support", "weight", "effect", "status"])
        w.writeheader()
        for row in operation_rows:
            row["signature"] = json.dumps(row["signature"])
            row["effect"] = json.dumps(row["effect"])
            w.writerow(row)
    with (REPORTS / "segmentation_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trace_id", "status", "true_positive", "predicted", "truth", "precision", "recall", "f1"])
        w.writeheader(); w.writerows(segmentation_metrics)
    with (REPORTS / "stream_event_map.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trace_id", "token_index", "token", "inferred_motif_id", "segment_start", "segment_end", "segmentation_status"])
        w.writeheader()
        for tr in train + test:
            segres = (train_segs if tr.trace_id.startswith("train_") else test_segs)[tr.trace_id]
            token_owner = {}
            if segres.best:
                for seg in segres.best.segments:
                    for idx in range(seg.start, seg.end):
                        token_owner[idx] = seg
            for idx, token in enumerate(tr.tokens):
                seg = token_owner.get(idx)
                w.writerow({"trace_id": tr.trace_id, "token_index": idx, "token": token,
                    "inferred_motif_id": seg.motif_id if seg else "",
                    "segment_start": seg.start if seg else "",
                    "segment_end": seg.end if seg else "",
                    "segmentation_status": segres.status})
    with (REPORTS / "checkpoint_residuals.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trace_id", "offset_start", "offset_end", "predicted_delta", "observed_delta", "correct"])
        w.writeheader()
        for row in model_predictions["records"]:
            w.writerow({"trace_id": row["trace_id"], "offset_start": row["interval"][0],
                        "offset_end": row["interval"][1], "predicted_delta": json.dumps(row["predicted_delta"]),
                        "observed_delta": json.dumps(row["observed_delta"]), "correct": row["correct"]})

    precision = all_tp / all_predicted if all_predicted else 1.0
    recall = all_tp / all_truth if all_truth else 1.0
    cp_total = cp_aligned = 0
    for tr in train + test:
        boundary_offsets = {end for _, end, _ in truth[tr.trace_id]}
        for cp in tr.checkpoints:
            if cp.offset in (0, len(tr.tokens)):
                continue
            cp_total += 1
            cp_aligned += int(cp.offset in boundary_offsets)
    summary = {
        "build": 28,
        "status": "complete" if fit["status"] == "effects_uniquely_identified" and model_predictions["total"] else "partial",
        "evidence_class": "synthetic continuous opaque-token streams with sparse asynchronous state checkpoints",
        "training_streams": len(train), "heldout_streams": len(test),
        "training_tokens": sum(len(t.tokens) for t in train),
        "heldout_tokens": sum(len(t.tokens) for t in test),
        "operation_boundaries_supplied_to_learner": False,
        "semantic_operation_names_supplied_to_learner": False,
        "internal_checkpoint_count": cp_total,
        "internal_checkpoints_coinciding_with_hidden_operation_boundaries": cp_aligned,
        "checkpoint_boundary_alignment_rate": (cp_aligned / cp_total) if cp_total else None,
        "sparse_checkpoint_offsets_are_operation_aligned": False,
        "mined_motif_count": len(motifs),
        "candidate_operation_count": sum(x["status"] == "candidate_operation" for x in ground["operations"]),
        "recurrent_zero_effect_motif_count": sum(x["status"] == "recurrent_zero_effect_motif" for x in ground["operations"]),
        "nested_submotif_count": len(learned["nested_submotifs"]),
        "segmentation_precision": precision,
        "segmentation_recall": recall,
        "segmentation_f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0,
        "ambiguous_training_streams": sum(x != "resolved" for x in train_status.values()),
        "ambiguous_heldout_streams": sum(x != "resolved" for x in test_status.values()),
        "checkpoint_effect_fit_status": fit["status"],
        "checkpoint_effect_equations": fit["equations"],
        "heldout_checkpoint_predictions_correct": model_predictions["correct"],
        "heldout_checkpoint_predictions_total": model_predictions["total"],
        "heldout_checkpoint_accuracy": model_predictions["accuracy"],
        "shuffled_control_raw_motif_count": len(shuffled_motifs),
        "shuffled_control_after_familywise_filter_count": len(shuffled_kept),
        "familywise_null_max_threshold": (shuffled_audit[0]["familywise_null_max_across_candidates"] if shuffled_audit else 0),
        "permutation_filter_trials": 31,
        "permutation_filter_survivors": sum(1 for x in learned["permutation_audit"] if x["survives_order_null"]),
        "permutation_filter_rejected": sum(1 for x in learned["permutation_audit"] if not x["survives_order_null"]),
        "ambiguity_fixture_status": amb_seg.status,
        "ground_fingerprint_valid": verify_ground_fingerprint(ground),
        "limits": [
            "event tokenization and trace start/end are supplied; raw waveform event detection is not implemented",
            "motif mining is exact contiguous n-gram discovery, not approximate edit-distance or neural segmentation",
            "synthetic evaluator knows boundaries, but learner receives only tokens and sparse checkpoints",
            "checkpoint windows crossing a proposed segment are excluded from effect equations rather than misattributed",
            "operation effects are inferred from aggregate checkpoint equations and may be underdetermined",
            "recurrent motifs with zero effect are retained as event motifs, not promoted as operations",
            "causal attribution requires interventions or ablations; recurrence alone is not causality",
            "ambiguity is retained when alternative segmentations have sufficiently similar scores",
            "no physical sensor or TAPS data was processed",
        ],
    }
    write_json("build_28_results.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
