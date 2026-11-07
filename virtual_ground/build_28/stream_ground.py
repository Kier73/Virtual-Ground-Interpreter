"""Build 28: boundary-free operation discovery from continuous token streams.

Standard-library only. Learner inputs are continuous opaque-token streams plus
sparse state checkpoints. Operation boundaries and semantic action names are
not supplied. Synthetic ground-truth boundaries are used only by the evaluator.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Checkpoint:
    offset: int  # number of tokens consumed; not an operation boundary
    state: tuple[int, ...]


@dataclass(frozen=True)
class ContinuousTrace:
    trace_id: str
    tokens: tuple[str, ...]
    checkpoints: tuple[Checkpoint, ...]


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    motif_id: str
    signature: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class Motif:
    motif_id: str
    signature: tuple[str, ...]
    occurrences: int
    trace_support: int
    positions: tuple[tuple[str, int, int], ...]
    weight: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "motif_id": self.motif_id,
            "signature": list(self.signature),
            "length": len(self.signature),
            "occurrences": self.occurrences,
            "trace_support": self.trace_support,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class SegmentationAlternative:
    score: float
    segments: tuple[Segment, ...]
    skipped_tokens: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 8),
            "segments": [
                {"start": s.start, "end": s.end, "motif_id": s.motif_id,
                 "signature": list(s.signature), "score": round(s.score, 8)}
                for s in self.segments
            ],
            "skipped_token_indices": list(self.skipped_tokens),
        }


@dataclass
class SegmentationResult:
    trace_id: str
    status: str
    best: SegmentationAlternative | None
    alternatives: list[SegmentationAlternative]
    score_gap: float | None
    ambiguous_regions: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "status": self.status,
            "score_gap": None if self.score_gap is None else round(self.score_gap, 8),
            "ambiguous_regions": self.ambiguous_regions,
            "alternatives": [x.as_dict() for x in self.alternatives],
        }


class StreamGroundError(ValueError):
    pass


def _validate_trace(trace: ContinuousTrace) -> None:
    if not trace.trace_id:
        raise StreamGroundError("trace_id must be non-empty")
    if any(not isinstance(t, str) or not t for t in trace.tokens):
        raise StreamGroundError("tokens must be non-empty opaque strings")
    if len(trace.checkpoints) < 2:
        raise StreamGroundError("at least an initial and final checkpoint are required")
    offsets = [c.offset for c in trace.checkpoints]
    if offsets != sorted(offsets) or len(set(offsets)) != len(offsets):
        raise StreamGroundError("checkpoint offsets must be strictly increasing")
    if offsets[0] != 0 or offsets[-1] > len(trace.tokens):
        raise StreamGroundError("checkpoints must begin at 0 and remain within the stream")
    dims = {len(c.state) for c in trace.checkpoints}
    if len(dims) != 1 or next(iter(dims)) == 0:
        raise StreamGroundError("checkpoint states must have one consistent nonzero dimension")
    if any(not isinstance(x, int) for c in trace.checkpoints for x in c.state):
        raise StreamGroundError("this build expects integer checkpoint observations")


def _all_occurrences(tokens: Sequence[str], motif: tuple[str, ...]) -> list[tuple[int, int]]:
    n = len(motif)
    return [(i, i + n) for i in range(0, len(tokens) - n + 1)
            if tuple(tokens[i:i+n]) == motif]


def mine_motifs(
    traces: Sequence[ContinuousTrace], *, min_len: int = 2, max_len: int = 4,
    min_occurrences: int = 5, min_trace_support: int = 3,
) -> tuple[list[Motif], list[dict[str, Any]]]:
    """Mine recurrent exact n-grams; boundaries are not provided.

    Proper submotifs whose every occurrence is embedded in a longer frequent
    motif are retained in the audit as nested, but excluded from segmentation.
    """
    if min_len < 2 or max_len < min_len:
        raise StreamGroundError("invalid motif length bounds")
    occ: dict[tuple[str, ...], list[tuple[str, int, int]]] = defaultdict(list)
    for tr in traces:
        _validate_trace(tr)
        for n in range(min_len, min(max_len, len(tr.tokens)) + 1):
            for i in range(len(tr.tokens) - n + 1):
                sig = tuple(tr.tokens[i:i+n])
                occ[sig].append((tr.trace_id, i, i+n))
    eligible = {
        sig: rows for sig, rows in occ.items()
        if len(rows) >= min_occurrences and len({r[0] for r in rows}) >= min_trace_support
    }
    active: list[Motif] = []
    nested: list[dict[str, Any]] = []
    for sig, rows in eligible.items():
        covered = 0
        for trace_id, start, end in rows:
            is_nested = any(
                len(longer) > len(sig)
                and any(tid == trace_id and ls <= start and le >= end
                        for tid, ls, le in long_rows)
                for longer, long_rows in eligible.items()
            )
            covered += int(is_nested)
        if covered == len(rows):
            nested.append({"signature": list(sig), "occurrences": len(rows),
                           "trace_support": len({r[0] for r in rows}),
                           "status": "nested_submotif_excluded_from_segmentation"})
            continue
        trace_support = len({r[0] for r in rows})
        weight = (1.0 + 0.35 * len(sig) + 0.25 * math.log1p(trace_support)
                  + 0.08 * math.log1p(len(rows)))
        active.append(Motif("M000", sig, len(rows), trace_support,
                            tuple(sorted(rows)), weight))
    active.sort(key=lambda m: (-m.weight, -m.trace_support, -m.occurrences, m.signature))
    active = [Motif(f"M{i+1:03d}", m.signature, m.occurrences, m.trace_support,
                    m.positions, m.weight) for i, m in enumerate(active)]
    nested.sort(key=lambda x: (len(x["signature"]), x["signature"]))
    return active, nested


def segment_stream(
    trace: ContinuousTrace, motifs: Sequence[Motif], *, top_k: int = 4,
    ambiguity_margin: float = 0.40, skip_penalty: float = 0.02,
) -> SegmentationResult:
    """Return top non-overlapping motif segmentations plus explicit ambiguity."""
    if top_k < 1 or ambiguity_margin < 0 or skip_penalty < 0:
        raise StreamGroundError("invalid segmentation parameters")
    by_start: dict[int, list[tuple[Motif, int]]] = defaultdict(list)
    # Locate motifs in the supplied stream itself. Training positions are evidence
    # for discovery only; held-out streams are segmented with the learned motifs.
    for motif in motifs:
        for start, end in _all_occurrences(trace.tokens, motif.signature):
            by_start[start].append((motif, end))
    for start in by_start:
        by_start[start].sort(key=lambda x: (-x[0].weight, x[0].signature))

    def path_key(p: SegmentationAlternative) -> tuple:
        return tuple((s.start, s.end, s.signature) for s in p.segments), p.skipped_tokens

    @lru_cache(maxsize=None)
    def solve(i: int) -> tuple[SegmentationAlternative, ...]:
        if i >= len(trace.tokens):
            return (SegmentationAlternative(0.0, (), ()),)
        options: list[SegmentationAlternative] = []
        # Leave this token as unassigned background.
        for tail in solve(i + 1):
            options.append(SegmentationAlternative(
                tail.score - skip_penalty, tail.segments, (i,) + tail.skipped_tokens))
        # Assign a recurrent motif beginning at this offset.
        for motif, end in by_start.get(i, []):
            seg = Segment(i, end, motif.motif_id, motif.signature, motif.weight)
            for tail in solve(end):
                options.append(SegmentationAlternative(
                    tail.score + motif.weight, (seg,) + tail.segments, tail.skipped_tokens))
        unique: dict[tuple, SegmentationAlternative] = {}
        for p in options:
            k = path_key(p)
            if k not in unique or p.score > unique[k].score:
                unique[k] = p
        ranked = sorted(unique.values(), key=lambda p: (-p.score, path_key(p)))
        return tuple(ranked[:top_k])

    alts = list(solve(0))
    if not alts:
        return SegmentationResult(trace.trace_id, "no_segmentation", None, [], None, [])
    gap = (alts[0].score - alts[1].score) if len(alts) > 1 else None
    status = "resolved" if gap is None or gap > ambiguity_margin else "ambiguous"
    ambiguous_regions: list[dict[str, Any]] = []
    if status == "ambiguous":
        first = {(s.start, s.end, s.signature) for s in alts[0].segments}
        second = {(s.start, s.end, s.signature) for s in alts[1].segments}
        changed = sorted(first.symmetric_difference(second))
        if changed:
            ambiguous_regions.append({"candidate_spans": [list(x[:2]) for x in changed],
                                      "candidate_signatures": [list(x[2]) for x in changed]})
    return SegmentationResult(trace.trace_id, status, alts[0], alts, gap, ambiguous_regions)


def _solve_exact(A: Sequence[Sequence[int]], b: Sequence[int], nvars: int) -> dict[str, Any]:
    """Exact RREF solve over rationals; avoids floating-point false certainty."""
    if len(A) != len(b):
        raise StreamGroundError("linear system row mismatch")
    if not A:
        return {"status": "no_equations", "rank": 0, "solution": None}
    mat = [[Fraction(v) for v in row] + [Fraction(rhs)] for row, rhs in zip(A, b)]
    if any(len(row) != nvars + 1 for row in mat):
        raise StreamGroundError("linear system column mismatch")
    pivot_cols: list[int] = []
    r = 0
    for c in range(nvars):
        pivot = next((i for i in range(r, len(mat)) if mat[i][c] != 0), None)
        if pivot is None:
            continue
        mat[r], mat[pivot] = mat[pivot], mat[r]
        scale = mat[r][c]
        mat[r] = [x / scale for x in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][c] != 0:
                factor = mat[i][c]
                mat[i] = [x - factor*y for x, y in zip(mat[i], mat[r])]
        pivot_cols.append(c)
        r += 1
        if r == len(mat):
            break
    inconsistent = any(all(row[c] == 0 for c in range(nvars)) and row[-1] != 0 for row in mat)
    rank = len(pivot_cols)
    if inconsistent:
        return {"status": "inconsistent", "rank": rank, "solution": None}
    if rank < nvars:
        return {"status": "underdetermined", "rank": rank, "solution": None}
    sol = [Fraction(0) for _ in range(nvars)]
    for row_idx, col in enumerate(pivot_cols):
        sol[col] = mat[row_idx][-1]
    return {"status": "unique", "rank": rank,
            "solution": [int(x) if x.denominator == 1 else f"{x.numerator}/{x.denominator}" for x in sol]}


def _as_int_solution(result: Mapping[str, Any]) -> list[int] | None:
    if result.get("status") != "unique":
        return None
    out: list[int] = []
    for x in result["solution"]:
        if isinstance(x, int):
            out.append(x)
        elif isinstance(x, str) and "/" in x:
            n, d = x.split("/", 1)
            if int(d) != 1:
                return None
            out.append(int(n))
        else:
            return None
    return out


def build_effect_equations(
    traces: Sequence[ContinuousTrace], segmentations: Mapping[str, SegmentationResult],
    motifs: Sequence[Motif],
) -> dict[str, Any]:
    """Build count/effect equations from sparse checkpoints, not operation labels."""
    rows: list[list[int]] = []
    outputs: list[list[int]] = []
    provenance: list[dict[str, Any]] = []
    motif_ids = [m.motif_id for m in motifs]
    dims = len(traces[0].checkpoints[0].state) if traces else 0
    for tr in traces:
        segres = segmentations[tr.trace_id]
        if segres.status != "resolved" or segres.best is None:
            continue
        segments = segres.best.segments
        for left, right in zip(tr.checkpoints, tr.checkpoints[1:]):
            lo, hi = left.offset, right.offset
            crossing = [s for s in segments if s.start < hi and s.end > lo
                        and not (s.start >= lo and s.end <= hi)]
            if crossing:
                continue  # checkpoint bisected a candidate operation; do not misattribute it
            contained = [s for s in segments if s.start >= lo and s.end <= hi]
            counts = Counter(s.motif_id for s in contained)
            if not contained:
                continue
            rows.append([counts[mid] for mid in motif_ids])
            delta = [b-a for a, b in zip(left.state, right.state)]
            outputs.append(delta)
            provenance.append({"trace_id": tr.trace_id, "offset_interval": [lo, hi],
                               "motif_counts": {mid: counts[mid] for mid in motif_ids if counts[mid]},
                               "observed_delta": delta})
    if not rows:
        return {"status": "no_attributable_checkpoint_intervals", "motif_ids": motif_ids,
                "equations": 0, "rank_by_dimension": [], "effects": {}, "provenance": []}
    per_dim = []
    for d in range(dims):
        per_dim.append(_solve_exact(rows, [y[d] for y in outputs], len(motif_ids)))
    effects: dict[str, list[int] | None] = {mid: [] for mid in motif_ids}
    if all(x["status"] == "unique" for x in per_dim):
        solutions = [_as_int_solution(x) for x in per_dim]
        if all(x is not None for x in solutions):
            for j, mid in enumerate(motif_ids):
                effects[mid] = [solutions[d][j] for d in range(dims)]  # type: ignore[index]
        else:
            effects = {mid: None for mid in motif_ids}
    else:
        effects = {mid: None for mid in motif_ids}
    return {"status": "effects_uniquely_identified" if all(x["status"] == "unique" for x in per_dim)
            and all(v is not None for v in effects.values()) else "effects_not_fully_identified",
            "motif_ids": motif_ids, "equations": len(rows), "rank_by_dimension": per_dim,
            "effects": effects, "provenance": provenance}


def compile_partial_ground(motifs: Sequence[Motif], segmentation_results: Mapping[str, SegmentationResult],
                           effect_fit: Mapping[str, Any]) -> dict[str, Any]:
    effects = effect_fit.get("effects", {})
    operations = []
    for m in motifs:
        effect = effects.get(m.motif_id)
        status = "unknown_effect" if effect is None else (
            "recurrent_zero_effect_motif" if all(x == 0 for x in effect) else "candidate_operation")
        operations.append({"operation_id": m.motif_id, "signature": list(m.signature),
                           "support_occurrences": m.occurrences, "support_traces": m.trace_support,
                           "effect": effect, "status": status,
                           "evidence_scope": "exact recurrent token motif; finite training checkpoints"})
    structure = {"format": "virtual-ground-stream-v1", "operations": operations}
    fingerprint = sha256(json.dumps(structure, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**structure, "fingerprint": fingerprint, "status": "partial",
            "unknown_semantics": "unseen or unresolved event sequences remain unknown",
            "segmentation_scope": "exact contiguous motifs; ambiguity retained when top segmentations are close"}


def predict_checkpoint_deltas(traces: Sequence[ContinuousTrace],
                              segmentations: Mapping[str, SegmentationResult],
                              ground: Mapping[str, Any],
                              motifs: Sequence[Motif]) -> dict[str, Any]:
    effect_by_sig = {tuple(op["signature"]): op["effect"] for op in ground["operations"]}
    records = []
    correct = total = 0
    for tr in traces:
        segres = segmentations[tr.trace_id]
        if segres.status != "resolved" or segres.best is None:
            continue
        for left, right in zip(tr.checkpoints, tr.checkpoints[1:]):
            lo, hi = left.offset, right.offset
            segs = [s for s in segres.best.segments if s.start < hi and s.end > lo]
            crossing = [s for s in segs if not (s.start >= lo and s.end <= hi)]
            if crossing:
                continue
            pred = [0] * len(left.state)
            known = True
            for s in segs:
                effect = effect_by_sig.get(s.signature)
                if effect is None:
                    known = False
                    break
                for d, value in enumerate(effect):
                    pred[d] += int(value)
            if not known or not segs:
                continue
            actual = [b-a for a, b in zip(left.state, right.state)]
            ok = pred == actual
            total += 1
            correct += int(ok)
            records.append({"trace_id": tr.trace_id, "interval": [lo, hi],
                            "predicted_delta": pred, "observed_delta": actual, "correct": ok})
    return {"correct": correct, "total": total,
            "accuracy": (correct / total) if total else None, "records": records}


def compare_segments(predicted: Sequence[Segment], truth: Sequence[tuple[int, int, tuple[str, ...]]]) -> dict[str, Any]:
    p = {(s.start, s.end, s.signature) for s in predicted}
    t = set(truth)
    tp = len(p & t)
    precision = tp / len(p) if p else 1.0
    recall = tp / len(t) if t else 1.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"true_positive": tp, "predicted": len(p), "truth": len(t),
            "precision": precision, "recall": recall, "f1": f1}


def serialize_trace(tr: ContinuousTrace) -> dict[str, Any]:
    return {"trace_id": tr.trace_id, "tokens": list(tr.tokens),
            "checkpoints": [{"offset": c.offset, "state": list(c.state)} for c in tr.checkpoints]}


def deserialize_trace(obj: Mapping[str, Any]) -> ContinuousTrace:
    return ContinuousTrace(str(obj["trace_id"]), tuple(map(str, obj["tokens"])),
                           tuple(Checkpoint(int(c["offset"]), tuple(map(int, c["state"])))
                                 for c in obj["checkpoints"]))


def verify_ground_fingerprint(ground: Mapping[str, Any]) -> bool:
    structure = {"format": ground.get("format"), "operations": ground.get("operations")}
    expected = sha256(json.dumps(structure, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return expected == ground.get("fingerprint")



def permutation_filter_motifs(
    traces: Sequence[ContinuousTrace], motifs: Sequence[Motif], *,
    trials: int = 31, seed: int = 28028,
) -> tuple[list[Motif], list[dict[str, Any]]]:
    """Family-wise permutation screen preserving per-trace token inventories.

    Each null trial permutes tokens separately inside each trace. The threshold
    is the maximum count over *all candidate motifs* in *all null trials*;
    this controls the candidate-family search more conservatively than testing
    each candidate against its own null maximum. It is still a finite synthetic
    null screen, not a universal significance guarantee.
    """
    if trials < 1:
        raise StreamGroundError("at least one permutation trial is required")
    null_counts: dict[tuple[str, ...], list[int]] = {m.signature: [] for m in motifs}
    family_maxima: list[int] = []
    for trial in range(trials):
        shuffled_rows = []
        for i, tr in enumerate(traces):
            toks = list(tr.tokens)
            random_seed = seed + trial * 1009 + i * 9176
            import random
            random.Random(random_seed).shuffle(toks)
            shuffled_rows.append(toks)
        trial_counts = []
        for motif in motifs:
            count = sum(len(_all_occurrences(toks, motif.signature)) for toks in shuffled_rows)
            null_counts[motif.signature].append(count)
            trial_counts.append(count)
        family_maxima.append(max(trial_counts, default=0))
    family_threshold = max(family_maxima, default=0)
    kept: list[Motif] = []
    audit: list[dict[str, Any]] = []
    for motif in motifs:
        values = null_counts[motif.signature]
        null_max = max(values, default=0)
        null_mean = sum(values) / len(values)
        exceed = sum(v >= motif.occurrences for v in values)
        empirical_p = (1 + exceed) / (trials + 1)
        survives = motif.occurrences > family_threshold
        audit.append({"motif_id": motif.motif_id, "signature": list(motif.signature),
                      "observed_occurrences": motif.occurrences,
                      "null_max_occurrences_for_motif": null_max,
                      "null_mean_occurrences": round(null_mean, 6),
                      "familywise_null_max_across_candidates": family_threshold,
                      "empirical_tail_fraction_with_plus_one": empirical_p,
                      "survives_order_null": survives,
                      "interpretation": "within-trace token frequency preserved; local order randomized; maximum statistic controls candidate-family search"})
        if survives:
            kept.append(motif)
    kept.sort(key=lambda m: (-m.weight, -m.trace_support, -m.occurrences, m.signature))
    kept = [Motif(f"M{i+1:03d}", m.signature, m.occurrences, m.trace_support,
                  m.positions, m.weight) for i, m in enumerate(kept)]
    return kept, audit


def discover_and_compile(traces: Sequence[ContinuousTrace], **kwargs: Any) -> dict[str, Any]:
    motifs, nested = mine_motifs(traces,
        min_len=kwargs.get("min_len", 2), max_len=kwargs.get("max_len", 4),
        min_occurrences=kwargs.get("min_occurrences", 5),
        min_trace_support=kwargs.get("min_trace_support", 3))
    permutation_audit = []
    trials = int(kwargs.get("permutation_trials", 0))
    if trials:
        motifs, permutation_audit = permutation_filter_motifs(
            traces, motifs, trials=trials, seed=int(kwargs.get("permutation_seed", 28028)))
    segs = {tr.trace_id: segment_stream(tr, motifs,
        top_k=kwargs.get("top_k", 4),
        ambiguity_margin=kwargs.get("ambiguity_margin", 0.40)) for tr in traces}
    effects = build_effect_equations(traces, segs, motifs)
    ground = compile_partial_ground(motifs, segs, effects)
    return {"motifs": motifs, "nested_submotifs": nested,
            "permutation_audit": permutation_audit, "segmentations": segs,
            "effect_fit": effects, "ground": ground}


class ExecutablePartialGround:
    """Load a compiled partial ground and apply only sufficiently supported motifs."""
    def __init__(self, spec: Mapping[str, Any]):
        self.spec = dict(spec)
        if not verify_ground_fingerprint(self.spec):
            raise StreamGroundError("ground fingerprint mismatch")
        self._by_signature = {tuple(op["signature"]): op for op in self.spec.get("operations", [])}

    @classmethod
    def from_json(cls, payload: str) -> "ExecutablePartialGround":
        return cls(json.loads(payload))

    def apply(self, state: Sequence[int], event_signature: Sequence[str]) -> dict[str, Any]:
        op = self._by_signature.get(tuple(event_signature))
        if op is None:
            return {"status": "unknown_operation", "next_state": None}
        if op.get("effect") is None:
            return {"status": "unknown_effect", "next_state": None,
                    "operation_id": op["operation_id"]}
        effect = list(map(int, op["effect"]))
        if len(state) != len(effect):
            return {"status": "state_dimension_mismatch", "next_state": None,
                    "operation_id": op["operation_id"]}
        nxt = [int(x) + int(d) for x, d in zip(state, effect)]
        status = ("recurrent_zero_effect_motif" if op.get("status") == "recurrent_zero_effect_motif"
                  else "inductive_candidate")
        return {"status": status, "next_state": nxt,
                "operation_id": op["operation_id"],
                "evidence_scope": op.get("evidence_scope")}
