"""Build 27: competing explanations and unsupervised operation-signature discovery.

Standard-library only. No semantic action vocabulary is supplied. The input
interface provides observation windows and opaque low-level event tokens seen
between consecutive observations. Candidate operations are inferred from
recurrent token sequences and their observed effects.

All explanation scores are transparent ranking heuristics, not probabilities.
Finite evidence cannot prove a physical hidden-state ontology or identify a
unique ground outside the tested observation/action envelope.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence
import json


@dataclass(frozen=True)
class TransitionSample:
    step: int
    before: tuple[int, ...]
    event_tokens: tuple[str, ...]
    after: tuple[int, ...]
    sensors_before: Mapping[str, tuple[int, ...]] | None = None
    sensors_after: Mapping[str, tuple[int, ...]] | None = None

    def __post_init__(self) -> None:
        if not self.before or len(self.before) != len(self.after):
            raise ValueError("before/after state vectors must have equal non-zero dimension")
        if any(not isinstance(t, str) or not t for t in self.event_tokens):
            raise ValueError("event tokens must be non-empty strings")
        for collection in (self.sensors_before or {}, self.sensors_after or {}):
            if any(not isinstance(k, str) or not k for k in collection):
                raise ValueError("sensor names must be non-empty strings")

    @property
    def delta(self) -> tuple[int, ...]:
        return tuple(b - a for a, b in zip(self.before, self.after))

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step, "before": list(self.before),
            "event_tokens": list(self.event_tokens), "after": list(self.after),
            "sensors_before": {k: list(v) for k, v in (self.sensors_before or {}).items()},
            "sensors_after": {k: list(v) for k, v in (self.sensors_after or {}).items()},
        }


@dataclass(frozen=True)
class OperationCandidate:
    operation_id: str
    event_signature: tuple[str, ...]
    support: int
    distinct_pre_states: int
    effect_mode: str
    constant_delta: tuple[int, ...] | None
    transition_table: Mapping[str, tuple[int, ...]]
    ambiguous_pre_states: tuple[str, ...]
    status: str
    evidence_steps: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "event_signature": list(self.event_signature),
            "support": self.support,
            "distinct_pre_states": self.distinct_pre_states,
            "effect_mode": self.effect_mode,
            "constant_delta": list(self.constant_delta) if self.constant_delta is not None else None,
            "transition_table": {k: list(v) for k, v in self.transition_table.items()},
            "ambiguous_pre_states": list(self.ambiguous_pre_states),
            "status": self.status,
            "evidence_steps": list(self.evidence_steps),
        }


def _state_key(state: Sequence[int]) -> str:
    return json.dumps(list(state), separators=(",", ":"))


def _op_id(signature: Sequence[str]) -> str:
    blob = json.dumps(list(signature), separators=(",", ":"), ensure_ascii=False)
    return "op_" + sha256(blob.encode("utf-8")).hexdigest()[:12]


def discover_operation_candidates(
    samples: Sequence[TransitionSample], *, min_support: int = 2
) -> list[OperationCandidate]:
    """Discover opaque operations from recurring event-window signatures.

    There is no caller-provided action alphabet or semantic action name. The
    acquisition boundary between consecutive observations is supplied. Exact
    token-sequence recurrence is intentionally conservative: motif mining
    across unsegmented raw waveforms is not claimed here.
    """
    if min_support < 2:
        raise ValueError("min_support must be at least two")
    grouped: dict[tuple[str, ...], list[TransitionSample]] = defaultdict(list)
    for sample in samples:
        if sample.event_tokens:
            grouped[sample.event_tokens].append(sample)

    candidates: list[OperationCandidate] = []
    for signature, occurrences in sorted(grouped.items(), key=lambda kv: (kv[0], len(kv[1]))):
        if len(occurrences) < min_support:
            continue
        by_pre: dict[str, set[tuple[int, ...]]] = defaultdict(set)
        deltas = set()
        steps = []
        for sample in occurrences:
            key = _state_key(sample.before)
            by_pre[key].add(sample.delta)
            deltas.add(sample.delta)
            steps.append(sample.step)
        ambiguous = tuple(sorted(k for k, values in by_pre.items() if len(values) > 1))
        if ambiguous:
            mode, status, const_delta = "contextual_or_nonstationary", "ambiguous_effect", None
        elif len(deltas) == 1 and len(by_pre) >= 2:
            mode, status, const_delta = "constant_vector_delta", "candidate", next(iter(deltas))
        elif len(deltas) == 1:
            # One observed pre-state cannot justify a state-independent law.
            mode, status, const_delta = "single_prestate_table", "candidate", None
        else:
            mode, status, const_delta = "state_conditioned_table", "candidate", None
        table = {
            key: next(iter(values))
            for key, values in sorted(by_pre.items()) if len(values) == 1
        }
        candidates.append(OperationCandidate(
            operation_id=_op_id(signature), event_signature=signature,
            support=len(occurrences), distinct_pre_states=len(by_pre),
            effect_mode=mode, constant_delta=const_delta,
            transition_table=table, ambiguous_pre_states=ambiguous,
            status=status, evidence_steps=tuple(sorted(steps)[-64:]),
        ))
    return sorted(candidates, key=lambda x: (-x.support, -len(x.event_signature), x.operation_id))


class PartialGenerativeGround:
    """Executable partial ground compiled from discovered event signatures."""
    FORMAT = "VG-DiscoveredGround-1"

    def __init__(self, spec: Mapping[str, Any]):
        if spec.get("format") != self.FORMAT:
            raise ValueError("unsupported discovered-ground format")
        self.spec = json.loads(json.dumps(spec))
        self.operations = {x["operation_id"]: x for x in self.spec["operations"]}
        self.by_signature = {tuple(x["event_signature"]): x for x in self.spec["operations"]
                             if x["status"] == "candidate"}

    def predict(self, state: Sequence[int], event_tokens: Sequence[str]) -> dict[str, Any]:
        sig = tuple(event_tokens)
        op = self.by_signature.get(sig)
        if op is None:
            return {"status": "unknown_operation", "next_state": None, "operation_id": None}
        expected_dim = self.spec.get("state_dimension")
        if expected_dim is not None and len(state) != int(expected_dim):
            return {"status": "state_dimension_mismatch", "next_state": None, "operation_id": op["operation_id"]}
        if op["effect_mode"] == "constant_vector_delta":
            delta = op["constant_delta"]
            nxt = [int(x) + int(d) for x, d in zip(state, delta)]
            return {"status": "inductive_candidate", "next_state": nxt,
                    "operation_id": op["operation_id"], "law": "constant_vector_delta",
                    "evidence_scope": "finite observed examples; generalization remains a hypothesis"}
        key = _state_key(state)
        if key not in op["transition_table"]:
            return {"status": "unknown_precondition", "next_state": None,
                    "operation_id": op["operation_id"]}
        delta = op["transition_table"][key]
        return {"status": "observed_context_prediction",
                "next_state": [int(x) + int(d) for x, d in zip(state, delta)],
                "operation_id": op["operation_id"], "law": "observed_state_conditioned_delta"}

    def to_json(self) -> str:
        return json.dumps(self.spec, sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "PartialGenerativeGround":
        return cls(json.loads(text))


def compile_ground(samples: Sequence[TransitionSample], candidates: Sequence[OperationCandidate]) -> dict[str, Any]:
    known_states = sorted({_state_key(s.before) for s in samples} | {_state_key(s.after) for s in samples})
    operations = [c.as_dict() for c in candidates]
    dimensions = sorted({len(s.before) for s in samples} | {len(s.after) for s in samples})
    payload = {"format": PartialGenerativeGround.FORMAT, "status": "partial",
               "state_dimension": dimensions[0] if len(dimensions) == 1 else None,
               "states_observed": known_states, "operations": operations,
               "unknown_operation_semantics": "event signatures not repeated at least twice remain unknown",
               "scope": "observation windows and opaque event tokens supplied; semantic action alphabet not supplied"}
    structural_operations = []
    for op in operations:
        structural_operations.append({
            "operation_id": op["operation_id"],
            "event_signature": op["event_signature"],
            "effect_mode": op["effect_mode"],
            "constant_delta": op["constant_delta"],
            "transition_table": op["transition_table"],
            "ambiguous_pre_states": op["ambiguous_pre_states"],
            "status": op["status"],
        })
    structural = json.dumps({
        "format": payload["format"], "status": payload["status"],
        "state_dimension": payload["state_dimension"], "states_observed": payload["states_observed"],
        "operations": structural_operations,
    }, sort_keys=True, separators=(",", ":"))
    payload["fingerprint"] = sha256(structural.encode()).hexdigest()
    return payload


@dataclass(frozen=True)
class HistoryTransition:
    history: tuple[int, ...]
    event_signature: tuple[str, ...]
    output: tuple[int, ...]
    step: int = 0


def diagnose_history_collision(records: Sequence[HistoryTransition], *, max_horizon: int) -> dict[str, Any]:
    """Separate finite-history collision from unresolved predictive divergence."""
    if max_horizon < 1:
        raise ValueError("max_horizon must be positive")
    groups: dict[tuple[tuple[int, ...], tuple[str, ...]], set[tuple[int, ...]]] = defaultdict(set)
    for r in records:
        groups[(r.history[-1:] if r.history else (), r.event_signature)].add(r.output)
    collisions = [(k, v) for k, v in groups.items() if len(v) > 1]
    if not collisions:
        return {"status": "no_observed_collision", "minimum_resolving_horizon": None,
                "candidate_explanations": [], "history_collisions": 0}

    resolving = None
    resolving_factor = None
    for h in range(2, max_horizon + 1):
        refined: dict[tuple[tuple[int, ...], tuple[str, ...]], set[tuple[int, ...]]] = defaultdict(set)
        for r in records:
            refined[(r.history[-h:], r.event_signature)].add(r.output)
        if all(len(v) == 1 for v in refined.values()):
            resolving = h
            # Find the most recent single lag coordinate that is sufficient
            # within this finite dataset. This is an observed predictive factor,
            # not a claim about an unobserved physical variable.
            for lag in range(2, h + 1):
                by_factor: dict[tuple[int, tuple[str, ...]], set[tuple[int, ...]]] = defaultdict(set)
                for r in records:
                    if len(r.history) >= lag:
                        by_factor[(r.history[-lag], r.event_signature)].add(r.output)
                if all(len(v) == 1 for v in by_factor.values()):
                    resolving_factor = {"type": "observed_history_lag", "lag": lag,
                                        "distinct_values": sorted({r.history[-lag] for r in records if len(r.history) >= lag}),
                                        "scope": "predictive factor in supplied observation histories"}
                    break
            break
    if resolving is not None:
        return {"status": "insufficient_history", "minimum_resolving_horizon": resolving,
                "candidate_explanations": ["insufficient_history"],
                "history_collisions": len(collisions), "candidate_predictive_factor": resolving_factor,
                "interpretation": "A longer observed suffix resolves the collision; no new physical state is asserted."}
    return {"status": "unresolved_predictive_divergence", "minimum_resolving_horizon": None,
            "candidate_explanations": ["hidden_predictive_variable", "stochastic_or_noisy_transition"],
            "history_collisions": len(collisions),
            "interpretation": "Maximum tested history does not resolve the collision; hidden context and stochasticity remain competing explanations."}


def isolated_spikes(values: Sequence[int]) -> list[int]:
    """Indices of single-sample excursions that immediately return to baseline."""
    return [i for i in range(1, len(values) - 1)
            if values[i - 1] == values[i + 1] and values[i] != values[i - 1]]


def diagnose_sensor_shift(
    baseline: Mapping[str, Sequence[int]], observed: Mapping[str, Sequence[int]], *,
    reference_channels: Sequence[str], min_consistent: int = 3,
) -> dict[str, Any]:
    """Detect one-channel persistent offset while calibrated references remain stable."""
    offsets: dict[str, list[int]] = {}
    for channel in set(baseline) & set(observed):
        a, b = list(baseline[channel]), list(observed[channel])
        if len(a) != len(b) or not a:
            continue
        offsets[channel] = [y - x for x, y in zip(a, b)]
    shifted = {k: v[0] for k, v in offsets.items()
               if len(v) >= min_consistent and len(set(v)) == 1 and v[0] != 0}
    refs_stable = bool(reference_channels) and all(
        ch in offsets and all(x == 0 for x in offsets[ch]) for ch in reference_channels
    )
    if len(shifted) == 1 and refs_stable:
        channel, offset = next(iter(shifted.items()))
        return {"status": "sensor_calibration_shift_candidate", "channel": channel,
                "constant_offset": offset, "reference_channels_stable": True,
                "not_proven": "A physical state change affecting only this sensor remains possible without an external calibration reference."}
    if shifted and not refs_stable:
        return {"status": "sensor_remap_vs_system_change_unresolved", "shifted_channels": shifted,
                "reference_channels_stable": False}
    return {"status": "no_supported_single_channel_shift", "channel_offsets": offsets}


@dataclass(frozen=True)
class ConflictRecord:
    step: int
    context: str
    operation: str
    expected: tuple[int, ...]
    observed: tuple[int, ...]
    sensor: str


def detect_regime_change(
    baseline: Mapping[tuple[str, str], tuple[int, ...]],
    records: Sequence[ConflictRecord], *, min_context_operations: int = 2,
    min_repeats_per_key: int = 2,
) -> dict[str, Any]:
    """Propose a regime change only for persistent mismatches across keys."""
    if not records:
        return {"status": "no_conflicts", "change_point": None}
    by_key: dict[tuple[str, str], list[ConflictRecord]] = defaultdict(list)
    baseline_mismatches = []
    for r in records:
        key = (r.context, r.operation)
        if key not in baseline or tuple(r.expected) != tuple(baseline[key]):
            baseline_mismatches.append({"step": r.step, "key": list(key),
                                        "recorded_expected": list(r.expected),
                                        "baseline_expected": list(baseline.get(key, ()))})
            continue
        if tuple(r.observed) != tuple(r.expected):
            by_key[key].append(r)
    qualifying = {k: v for k, v in by_key.items() if len(v) >= min_repeats_per_key}
    if len(qualifying) < min_context_operations:
        return {"status": "insufficient_persistence_or_coverage", "change_point": None,
                "qualifying_context_operations": len(qualifying),
                "baseline_mismatch_records": baseline_mismatches,
                "competing_explanations": ["unknown_operation_effect", "sensor_error", "isolated_transition_conflict"]}
    all_steps = sorted(r.step for values in qualifying.values() for r in values)
    # Earliest step after which every qualifying key has at least the required
    # number of residuals is the conservative common change-point proposal.
    candidates = []
    for cp in all_steps:
        after = {k: [r for r in v if r.step >= cp] for k, v in qualifying.items()}
        if all(len(v) >= min_repeats_per_key for v in after.values()):
            candidates.append(cp)
    if not candidates:
        return {"status": "no_common_persistent_change_point", "change_point": None,
                "qualifying_context_operations": len(qualifying)}
    cp = min(candidates)
    sensors = {r.sensor for vals in qualifying.values() for r in vals if r.step >= cp}
    return {"status": "ground_regime_revision_candidate", "change_point": cp,
            "qualifying_context_operations": len(qualifying),
            "baseline_mismatch_records": baseline_mismatches,
            "independent_sensor_count": len(sensors),
            "sensor_corroboration": len(sensors) >= 2,
            "changed_keys": [list(k) for k in sorted(qualifying)],
            "commit_policy": "proposal only; independent validation required"}


def _entropy_probabilities(counts: Mapping[Any, float]) -> float:
    total = sum(float(v) for v in counts.values())
    if total <= 0:
        return 0.0
    from math import log2
    return -sum((float(v) / total) * log2(float(v) / total)
                for v in counts.values() if float(v) > 0)


def choose_discriminating_probe(
    hypotheses: Sequence[str],
    probes: Mapping[str, Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, float]],
    *, max_risk: float = 0.4, risk_weight: float = 1.0,
    prior_weights: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Choose a probe that separates explanations, not merely unknown actions.

    `probes[name][hypothesis]` is the predicted observation under that
    explanation. Missing predictions invalidate that probe. Information gain
    is computed from supplied prior weights (uniform by default); scores are
    conditional on the declared hypothesis set and are not world probabilities.
    """
    hs = tuple(dict.fromkeys(hypotheses))
    if len(hs) < 2:
        return {"status": "insufficient_competing_hypotheses", "selected_probe": None, "candidates": []}
    weights = {h: float((prior_weights or {}).get(h, 1.0)) for h in hs}
    if any(v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError("prior weights must be non-negative with positive total")
    prior_entropy = _entropy_probabilities(weights)
    scored = []
    for name, predictions in probes.items():
        if any(h not in predictions for h in hs):
            continue
        profile = profiles.get(name, {})
        cost = float(profile.get("cost", 1.0))
        risk = float(profile.get("risk", 1.0))
        if cost < 0 or not 0 <= risk <= 1:
            raise ValueError("invalid probe cost/risk")
        if risk > max_risk:
            continue
        partitions: dict[str, float] = defaultdict(float)
        outcomes: dict[str, list[str]] = defaultdict(list)
        for h in hs:
            key = json.dumps(predictions[h], sort_keys=True, separators=(",", ":"))
            partitions[key] += weights[h]
            outcomes[key].append(h)
        expected_remaining = 0.0
        total_weight = sum(weights.values())
        for key, mass in partitions.items():
            local_weights = {h: weights[h] for h in outcomes[key]}
            expected_remaining += (mass / total_weight) * _entropy_probabilities(local_weights)
        gain = max(0.0, prior_entropy - expected_remaining)
        score = gain / max(cost + risk_weight * risk, 1e-12)
        scored.append({"probe": name, "information_gain_bits": gain, "cost": cost,
                       "risk": risk, "score": score, "outcome_classes": len(partitions),
                       "partitions": [sorted(v) for v in outcomes.values()]})
    scored.sort(key=lambda x: (-x["score"], -x["information_gain_bits"], x["risk"], x["cost"], x["probe"]))
    if not scored or scored[0]["information_gain_bits"] <= 0:
        return {"status": "no_safe_discriminating_probe", "selected_probe": None,
                "candidates": scored, "prior_entropy_bits": prior_entropy}
    return {"status": "discriminating_probe_selected", "selected_probe": scored[0]["probe"],
            "prior_entropy_bits": prior_entropy, "candidates": scored,
            "scope": "information gain conditional on the explicit competing-hypothesis set"}


@dataclass(frozen=True)
class DiagnosticEvidence:
    isolated_spike_recovered: bool = False
    independent_channels_stable: bool = False
    persistent_single_channel_offset: bool = False
    calibrated_references_stable: bool = False
    collision_resolves_at_longer_horizon: bool = False
    max_history_still_collides: bool = False
    repeated_same_history_action_multiple_outputs: bool = False
    novel_observation_repeated: int = 0
    independent_channels_confirm_novelty: bool = False
    novel_state_has_stable_transition_profile: bool = False
    multi_context_persistent_transition_conflicts: bool = False
    multiple_sensors_corroborate_conflicts: bool = False
    recurring_unseen_event_signature: bool = False
    event_signature_effect_consistent: bool = False
    single_context_single_conflict: bool = False


def diagnose_competing_explanations(e: DiagnosticEvidence) -> dict[str, Any]:
    """Rank explanations from explicit evidence; scores are not probabilities."""
    candidates: list[dict[str, Any]] = []

    def add(code: str, score: int, evidence: list[str], next_test: str) -> None:
        candidates.append({"explanation": code, "rank_score": score,
                           "score_semantics": "ordinal evidence heuristic, not probability",
                           "supporting_evidence": evidence, "discriminating_next_test": next_test})

    if e.isolated_spike_recovered and e.independent_channels_stable:
        add("measurement_noise", 8,
            ["single-sample excursion", "returns to prior value", "independent channels remain stable"],
            "Repeat the same observation under unchanged conditions.")
    if e.persistent_single_channel_offset and e.calibrated_references_stable:
        add("sensor_calibration_shift", 8,
            ["persistent offset restricted to one channel", "calibrated reference channels stable"],
            "Apply a known reference input to the shifted channel.")
    if e.collision_resolves_at_longer_horizon:
        add("insufficient_history", 9,
            ["short history collides", "longer observed suffix separates future responses"],
            "Retain the longer predictive suffix and validate on new continuations.")
    if e.max_history_still_collides:
        add("hidden_predictive_variable_candidate", 6,
            ["maximum tested suffix still collides"],
            "Add an independent sensor or choose an intervention that separates latent contexts.")
    if e.repeated_same_history_action_multiple_outputs:
        add("stochastic_or_unmodelled_context", 7,
            ["same retained history and event signature produce multiple outputs"],
            "Repeat controlled trials and add an independent context sensor before choosing between stochasticity and hidden state.")
    if e.novel_observation_repeated >= 3 and e.independent_channels_confirm_novelty and e.novel_state_has_stable_transition_profile:
        add("new_predictive_state_candidate", 9,
            ["novel observation repeated at least three times", "independent channels corroborate", "transition profile is reproducible"],
            "Probe the candidate state with multiple known and newly discovered operations.")
    elif e.novel_observation_repeated > 0:
        add("novel_observation_unclassified", 3,
            ["novel observation seen but corroboration/profile is insufficient"],
            "Check calibration references and repeat observation under controlled conditions.")
    if e.multi_context_persistent_transition_conflicts and e.multiple_sensors_corroborate_conflicts:
        add("ground_regime_change_candidate", 10,
            ["persistent conflicts across multiple context-operation pairs", "multiple sensors corroborate"],
            "Run a held-out probe set across old and new contexts; version only after validation.")
    if e.recurring_unseen_event_signature and e.event_signature_effect_consistent:
        add("new_operation_candidate", 8,
            ["previously unlabelled event signature recurs", "observed effect is consistent"],
            "Repeat the event signature in a second pre-state and check whether its effect law generalizes.")
    if e.single_context_single_conflict:
        add("unknown_transition_or_sensor_error", 4,
            ["one context-operation conflict only"],
            "Repeat with an independent sensor and a second context; do not revise the ground yet.")

    candidates.sort(key=lambda x: (-x["rank_score"], x["explanation"]))
    explanations = {x["explanation"] for x in candidates}
    ambiguity = []
    if "new_predictive_state_candidate" in explanations and "sensor_calibration_shift" not in explanations:
        ambiguity.append("new predictive state versus uncalibrated sensor remapping remains possible")
    if "hidden_predictive_variable_candidate" in explanations and "insufficient_history" not in explanations:
        ambiguity.append("unobserved context versus longer-than-tested memory remains possible")
    if "stochastic_or_unmodelled_context" in explanations:
        ambiguity.append("stochastic transition and an unobserved deterministic variable are not distinguished")
    if not candidates:
        return {"status": "insufficient_evidence", "primary_explanation": None,
                "candidates": [], "unresolved_ambiguities": ["No diagnostic pattern met its evidence threshold."]}
    top = candidates[0]
    return {"status": "diagnostic_candidates_ranked", "primary_explanation": top["explanation"],
            "candidates": candidates, "unresolved_ambiguities": ambiguity,
            "ground_revision_authorized": False}


class SelfConstructingGroundInterpreter:
    """Bounded online wrapper around operation discovery and ground compilation.

    The connector supplies observation-window boundaries and raw event tokens,
    but no semantic action vocabulary. Candidate structures are rebuilt from
    retained evidence. A changed structural fingerprint creates a version;
    additional support for an unchanged rule does not.
    """

    def __init__(self, *, min_support: int = 2, max_samples: int = 4096):
        if min_support < 2 or max_samples < 2:
            raise ValueError("min_support and max_samples must be >= 2")
        from collections import deque
        self.min_support = min_support
        self.max_samples = max_samples
        self.samples = deque(maxlen=max_samples)
        self.total_samples = 0
        self.retired_samples = 0
        self.data_truncated = False
        self.version = 0
        self.version_events: list[dict[str, Any]] = []
        self.candidates: list[OperationCandidate] = []
        self.spec: dict[str, Any] | None = None
        self.status = "collecting"
        self._fingerprint: str | None = None

    def ingest(self, sample: TransitionSample) -> dict[str, Any]:
        if len(self.samples) == self.max_samples:
            self.retired_samples += 1
            self.data_truncated = True
        self.samples.append(sample)
        self.total_samples += 1
        self.candidates = discover_operation_candidates(list(self.samples), min_support=self.min_support)
        self.spec = compile_ground(list(self.samples), self.candidates)
        fingerprint = self.spec["fingerprint"]
        if fingerprint != self._fingerprint:
            previous = self._fingerprint
            self.version += 1
            self.version_events.append({"version": self.version, "previous_fingerprint": previous,
                                        "fingerprint": fingerprint, "reason": "new_or_revised_candidate_structure",
                                        "sample_count": self.total_samples})
            if len(self.version_events) > 128:
                self.version_events = self.version_events[-128:]
            self._fingerprint = fingerprint
        self.status = "candidate_ground_available" if self.candidates else "collecting_unclassified_events"
        return self.snapshot()

    def compile(self) -> dict[str, Any]:
        if self.spec is None:
            return {"format": PartialGenerativeGround.FORMAT, "status": "empty", "operations": [],
                    "unknown_operation_semantics": "all operations unknown"}
        out = json.loads(json.dumps(self.spec))
        out["online_status"] = self.status
        out["evidence_window"] = {"retained_samples": len(self.samples),
                                  "total_samples": self.total_samples,
                                  "retired_samples": self.retired_samples,
                                  "data_truncated": self.data_truncated}
        return out

    def snapshot(self) -> dict[str, Any]:
        return {"status": self.status, "version": self.version,
                "total_samples": self.total_samples, "retained_samples": len(self.samples),
                "retired_samples": self.retired_samples, "data_truncated": self.data_truncated,
                "candidate_operation_count": len(self.candidates),
                "candidate_ids": [x.operation_id for x in self.candidates],
                "fingerprint": self._fingerprint}

    def predict(self, state: Sequence[int], event_tokens: Sequence[str]) -> dict[str, Any]:
        if self.spec is None:
            return {"status": "ground_not_yet_induced", "next_state": None}
        return PartialGenerativeGround(self.compile()).predict(state, event_tokens)


def build_report(samples: Sequence[TransitionSample], min_support: int = 2) -> dict[str, Any]:
    candidates = discover_operation_candidates(samples, min_support=min_support)
    spec = compile_ground(samples, candidates)
    model = PartialGenerativeGround(spec)
    matched = 0
    unknown = 0
    mismatched = 0
    for s in samples:
        pred = model.predict(s.before, s.event_tokens)
        if pred["status"].startswith("unknown"):
            unknown += 1
        elif tuple(pred["next_state"]) == s.after:
            matched += 1
        else:
            mismatched += 1
    return {
        "sample_count": len(samples),
        "candidate_operations": [c.as_dict() for c in candidates],
        "compiled_ground": spec,
        "evidence_replay": {"matched": matched, "unknown": unknown, "mismatched": mismatched,
                            "scope": "retained observed windows only; not proof of unseen transitions"},
    }
