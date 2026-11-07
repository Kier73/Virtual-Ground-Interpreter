"""Build 26: incremental induction of a partial Virtual Ground from a live stream.

Standard-library only. The learner receives a known action/channel interface and
an ordered action stream with asynchronously delivered sensor channels. It does
not receive a teacher state, hidden mode, reset operation, or candidate ground.

The inferred object is deliberately partial: unobserved transitions remain
unknown. Histories are provisionally represented by bounded predictive suffixes;
collisions trigger horizon growth, and unresolved collisions remain explicit.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
from math import log2
from typing import Any, Iterable, Mapping, Sequence
import json


class UnknownTransitionError(RuntimeError):
    """Raised when the partial ground has no evidenced transition."""


class GroundQuarantinedError(RuntimeError):
    """Raised when contradictory or unresolved evidence blocks ordinary updates."""


@dataclass(frozen=True)
class StreamEvent:
    step: int
    action: str
    output: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"step": self.step, "action": self.action, "output": list(self.output)}


@dataclass(frozen=True)
class TransitionObservation:
    output: tuple[int, ...]
    successor: str
    count: int
    evidence_steps: tuple[int, ...]


class PartialExecutableGround:
    """Executable partial Mealy-like specification. Unknown edges raise."""

    def __init__(self, specification: Mapping[str, Any]):
        if specification.get("format") != "VG-IncrementalPartialGround-1":
            raise ValueError("unsupported incremental ground format")
        self.spec = json.loads(json.dumps(specification))
        self.actions = tuple(self.spec["actions"])
        self.states = tuple(self.spec["states"])
        self.initial = self.spec.get("initial_context")
        self.transitions = self.spec["transitions"]
        self.status = self.spec.get("status", "partial")

    def step(self, state: str, action: str) -> tuple[str, tuple[int, ...]]:
        if self.status in ("quarantined", "context_budget_exceeded"):
            raise GroundQuarantinedError(f"candidate ground is not executable: {self.status}")
        if state not in self.transitions:
            raise UnknownTransitionError(f"unknown predictive context: {state}")
        if action not in self.actions:
            raise ValueError(f"unknown action: {action}")
        edge = self.transitions[state].get(action)
        if edge is None or edge.get("status") != "known":
            raise UnknownTransitionError(f"transition is unknown: ({state}, {action})")
        return str(edge["successor"]), tuple(int(v) for v in edge["output"])

    @classmethod
    def from_json(cls, text: str) -> "PartialExecutableGround":
        return cls(json.loads(text))

    def to_json(self) -> str:
        return json.dumps(self.spec, sort_keys=True, indent=2)


class StreamingGroundInducer:
    """Incrementally infer observable predictive contexts from a non-resettable stream.

    Interface contract:
      * `actions` and source channel identifiers are known from the connector.
      * `begin_action` calls are contiguous and ordered.
      * selected sensor channels may arrive before or after action registration and
        out of order across steps.
      * an event is committed only when every selected channel has arrived.
      * event outputs are interpreted according to `signature_mode`:
          - observation: output is a post-action state observation;
          - mealy: output is an action-conditioned response and action is included
            in the predictive-history signature.

    This is a bounded-history, deterministic, finite-interface learner. It does
    not infer arbitrary action alphabets, raw signal segmentation, or stochastic
    observation laws.
    """

    FORMAT = "VG-IncrementalPartialGround-1"

    def __init__(
        self,
        actions: Sequence[str],
        channel_ids: Sequence[int],
        *,
        signature_mode: str = "observation",
        initial_horizon: int = 0,
        max_horizon: int = 8,
        max_events: int = 4096,
        max_pending_steps: int = 256,
        completed_cache_limit: int = 128,
        audit_limit: int = 256,
        max_contexts: int = 1024,
    ):
        self.actions = tuple(actions)
        if not self.actions or len(set(self.actions)) != len(self.actions):
            raise ValueError("actions must be a non-empty unique sequence")
        self.channel_ids = tuple(channel_ids)
        if not self.channel_ids or len(set(self.channel_ids)) != len(self.channel_ids):
            raise ValueError("channel_ids must be non-empty and unique")
        if any(int(c) < 0 for c in self.channel_ids):
            raise ValueError("channel identifiers must be non-negative")
        if signature_mode not in ("observation", "mealy"):
            raise ValueError("signature_mode must be 'observation' or 'mealy'")
        if not 0 <= initial_horizon <= max_horizon:
            raise ValueError("invalid initial/max horizon")
        if min(max_horizon, max_events, max_pending_steps, completed_cache_limit, audit_limit, max_contexts) < 1:
            raise ValueError("all retention and model budgets must be positive")
        self.signature_mode = signature_mode
        self.horizon = initial_horizon
        self.max_horizon = max_horizon
        self.max_events = max_events
        self.max_pending_steps = max_pending_steps
        self.completed_cache_limit = completed_cache_limit
        self.audit_limit = audit_limit
        self.max_contexts = max_contexts

        self.records: list[StreamEvent] = []
        self.pending_actions: dict[int, str] = {}
        self.pending_observations: dict[int, dict[int, int]] = defaultdict(dict)
        self.pending_sources: dict[int, dict[int, str]] = defaultdict(dict)
        self.last_action_step: int | None = None
        self.next_commit_step = 0
        self.completed_cache: dict[int, tuple[str, tuple[int, ...]]] = {}
        self.completed_order: deque[int] = deque()
        self.total_event_count = 0
        self.retired_event_count = 0
        self.total_sensor_count = 0
        self.total_duplicate_count = 0
        self.total_stale_count = 0
        self.data_truncated = False
        self.status = "collecting"
        self.conflict_log: list[dict[str, Any]] = []
        self.audit: deque[dict[str, Any]] = deque(maxlen=audit_limit)
        self.version = 0
        self.version_lineage: list[dict[str, Any]] = []
        self.version_history_limit = 128
        self.conflict_history_limit = 64
        self._last_model_fingerprint: str | None = None
        self._model: dict[str, Any] = {}
        self._raw_to_quotient: dict[str, str] = {}
        self._rebuild_reason = "initialization"
        self._rebuild()

    # ---------- stream ingestion ----------

    def begin_action(self, step: int, action: str) -> dict[str, Any]:
        self._ensure_not_quarantined()
        if action not in self.actions:
            raise ValueError(f"unknown action: {action}")
        step = int(step)
        if step in self.pending_actions:
            if self.pending_actions[step] != action:
                self._quarantine("action_step_conflict", step=step, old=self.pending_actions[step], new=action)
            return self.snapshot()
        expected = 0 if self.last_action_step is None else self.last_action_step + 1
        if step != expected:
            raise ValueError(f"action step must be contiguous; expected {expected}")
        buffered = set(self.pending_actions) | set(self.pending_observations)
        if step not in buffered and len(buffered) >= self.max_pending_steps:
            raise RuntimeError("pending-step budget exceeded")
        self.pending_actions[step] = action
        self.last_action_step = step
        self._record_audit("action_registered", step=step, action=action)
        self._drain()
        return self.snapshot()

    def observe_channel(self, step: int, channel: int, value: int, *, source: str = "sensor",
                        local_sequence: int | None = None, local_timestamp: float | None = None) -> dict[str, Any]:
        self.total_sensor_count += 1
        step, channel, value = int(step), int(channel), int(value)
        if channel not in self.channel_ids:
            self._record_audit("unselected_channel_ignored", step=step, channel=channel, source=source)
            return self.snapshot()
        if step in self.completed_cache:
            old_action, old_output = self.completed_cache[step]
            idx = self.channel_ids.index(channel)
            if old_output[idx] == value:
                self.total_duplicate_count += 1
                self._record_audit("idempotent_late_duplicate", step=step, channel=channel, source=source)
                return self.snapshot()
            self._quarantine("conflicting_late_duplicate", step=step, channel=channel,
                             previous=old_output[idx], observed=value, source=source)
            return self.snapshot()
        if step < self.next_commit_step:
            self.total_stale_count += 1
            self._record_audit("stale_observation_outside_cache", step=step, channel=channel, source=source)
            return self.snapshot()
        buffered = set(self.pending_actions) | set(self.pending_observations)
        if step not in buffered and len(buffered) >= self.max_pending_steps:
            raise RuntimeError("pending-step budget exceeded")
        old = self.pending_observations[step].get(channel)
        if old is not None:
            if old == value:
                self.total_duplicate_count += 1
                self._record_audit("idempotent_pending_duplicate", step=step, channel=channel, source=source)
            else:
                self._quarantine("conflicting_duplicate_channel", step=step, channel=channel,
                                 previous=old, observed=value, source=source)
            return self.snapshot()
        self.pending_observations[step][channel] = value
        self.pending_sources[step][channel] = source
        self._record_audit("sensor_channel_received", step=step, channel=channel,
                           source=source, local_sequence=local_sequence, local_timestamp=local_timestamp)
        self._drain()
        return self.snapshot()

    def ingest_event(self, step: int, action: str, output: Sequence[int], *, source: str = "sensor") -> dict[str, Any]:
        """Convenience path for an already assembled complete observation vector."""
        if len(output) != len(self.channel_ids):
            raise ValueError("output width does not match selected channel schema")
        self.begin_action(step, action)
        for ch, value in zip(self.channel_ids, output):
            self.observe_channel(step, ch, int(value), source=source)
        return self.snapshot()

    def _drain(self) -> None:
        while self.next_commit_step in self.pending_actions:
            step = self.next_commit_step
            obs = self.pending_observations.get(step, {})
            if not all(ch in obs for ch in self.channel_ids):
                break
            action = self.pending_actions.pop(step)
            output = tuple(obs[ch] for ch in self.channel_ids)
            self.pending_observations.pop(step, None)
            self.pending_sources.pop(step, None)
            self._commit(StreamEvent(step, action, output))
            self.next_commit_step += 1

    def _commit(self, event: StreamEvent) -> None:
        # Prequential score: predict from the model before incorporating this event.
        predicted = self.predict_next(event.action)
        if predicted["status"] == "predicted":
            correct = tuple(predicted["output"]) == event.output
            self._record_audit("prequential_prediction", step=event.step,
                               predicted=list(predicted["output"]), observed=list(event.output), correct=correct)
        self.records.append(event)
        self.total_event_count += 1
        if len(self.records) > self.max_events:
            drop = len(self.records) - self.max_events
            del self.records[:drop]
            self.retired_event_count += drop
            self.data_truncated = True
        self._remember_completed(event)
        self._rebuild_reason = "new_transition_evidence"
        self._rebuild_adaptive()
        if self.status not in ("quarantined", "unresolved_context_collision", "context_budget_exceeded"):
            self.status = "tracking"
        self._record_audit("event_committed", step=event.step, action=event.action, output=list(event.output),
                           horizon=self.horizon, predictive_contexts=self.predictive_context_count)

    def _remember_completed(self, event: StreamEvent) -> None:
        self.completed_cache[event.step] = (event.action, event.output)
        self.completed_order.append(event.step)
        while len(self.completed_order) > self.completed_cache_limit:
            old = self.completed_order.popleft()
            self.completed_cache.pop(old, None)

    # ---------- context signatures and model induction ----------

    def _event_mark(self, event: StreamEvent) -> Any:
        if self.signature_mode == "observation":
            return list(event.output)
        return [event.action, list(event.output)]

    def _raw_context_key(self, position: int, horizon: int) -> str:
        left = max(0, position - horizon)
        prior = [self._event_mark(e) for e in self.records[left:position]]
        missing = horizon - len(prior)
        if missing:
            boundary = "START" if not self.data_truncated else "TRUNCATED_HISTORY"
            prior = [[boundary] for _ in range(missing)] + prior
        if horizon == 0:
            prior = []
        payload = {"mode": self.signature_mode, "horizon": horizon, "suffix": prior}
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
        return f"r{horizon}_{digest}"

    def _build_raw_model(self, horizon: int) -> dict[str, Any]:
        values: dict[tuple[str, str], dict[tuple[tuple[int, ...], str], list[int]]] = defaultdict(lambda: defaultdict(list))
        states: set[str] = set()
        visits: CounterLike = defaultdict(int)
        for i, event in enumerate(self.records):
            # After retention truncation, the left boundary no longer has a
            # trustworthy predecessor context. Do not turn that boundary into
            # a learned transition; wait until `horizon` fresh retained events
            # provide a complete suffix.
            if self.data_truncated and i < horizon:
                continue
            source = self._raw_context_key(i, horizon)
            target = self._raw_context_key(i + 1, horizon)
            states.add(source)
            states.add(target)
            visits[source] += 1
            values[(source, event.action)][(event.output, target)].append(event.step)
        collisions = []
        transitions: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in sorted(states)}
        for (source, action), outcomes in sorted(values.items()):
            if len(outcomes) == 1:
                (output, target), steps = next(iter(outcomes.items()))
                transitions[source][action] = {
                    "status": "known", "output": list(output), "successor": target,
                    "support": len(steps), "evidence_steps": list(steps[-16:]),
                }
            else:
                collision = {
                    "source": source, "action": action,
                    "alternatives": [
                        {"output": list(out), "successor": target, "count": len(steps), "steps": list(steps[-8:])}
                        for (out, target), steps in sorted(outcomes.items(), key=lambda kv: repr(kv[0]))
                    ],
                }
                collisions.append(collision)
                transitions[source][action] = {"status": "ambiguous", "alternatives": collision["alternatives"]}
        return {"states": sorted(states), "transitions": transitions, "collisions": collisions,
                "raw_context_visits": dict(visits)}

    def _partition_partial_machine(self, raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        """Merge contexts only when their observed partial behaviours are bisimilar.

        States must have identical observed-action coverage. Unknown edges are not
        treated as identity edges or silently generalized across coverage gaps.
        """
        states = list(raw["states"])
        trans = raw["transitions"]
        if not states:
            return {"states": [], "transitions": {}}, {}

        def base_signature(q: str) -> tuple:
            row = trans[q]
            return tuple((a, row[a].get("status"), tuple(row[a].get("output", [])) if row[a].get("status") == "known" else ())
                         for a in self.actions if a in row)

        signatures: dict[tuple, int] = {}
        block: dict[str, int] = {}
        for q in states:
            sig = base_signature(q)
            if sig not in signatures:
                signatures[sig] = len(signatures)
            block[q] = signatures[sig]

        for _ in range(max(1, len(states))):
            signatures = {}
            new_block: dict[str, int] = {}
            for q in states:
                row = trans[q]
                parts = []
                for a in self.actions:
                    edge = row.get(a)
                    if edge is None:
                        parts.append((a, "unknown"))
                    elif edge["status"] == "ambiguous":
                        parts.append((a, "ambiguous", tuple(sorted(repr(x) for x in edge["alternatives"]))))
                    else:
                        parts.append((a, "known", tuple(edge["output"]), block[edge["successor"]]))
                sig = tuple(parts)
                if sig not in signatures:
                    signatures[sig] = len(signatures)
                new_block[q] = signatures[sig]
            if new_block == block:
                break
            block = new_block

        members: dict[int, list[str]] = defaultdict(list)
        for q, b in block.items():
            members[b].append(q)
        quotient_id = {b: "q_" + sha256("|".join(sorted(ms)).encode()).hexdigest()[:12]
                       for b, ms in members.items()}
        mapping = {q: quotient_id[b] for q, b in block.items()}
        q_states = sorted(set(mapping.values()))
        q_trans: dict[str, dict[str, dict[str, Any]]] = {q: {} for q in q_states}
        for b, group in members.items():
            qid = quotient_id[b]
            representative = group[0]
            for a in self.actions:
                edge = trans[representative].get(a)
                if edge is None:
                    continue
                if edge["status"] == "known":
                    q_trans[qid][a] = {
                        "status": "known", "output": list(edge["output"]),
                        "successor": mapping[edge["successor"]],
                        "support": sum(int(trans[m].get(a, {}).get("support", 0)) for m in group),
                        "evidence_steps": sorted({s for m in group for s in trans[m].get(a, {}).get("evidence_steps", [])})[-16:],
                        "quotient_inference": len(group) > 1,
                    }
                else:
                    q_trans[qid][a] = {"status": "ambiguous", "alternatives": edge.get("alternatives", [])}
        return {"states": q_states, "transitions": q_trans,
                "members": {quotient_id[b]: sorted(ms) for b, ms in members.items()}}, mapping

    def _rebuild(self) -> None:
        raw = self._build_raw_model(self.horizon)
        if len(raw["states"]) > self.max_contexts:
            self.status = "context_budget_exceeded"
            self._record_audit("context_budget_exceeded", raw_contexts=len(raw["states"]),
                               max_contexts=self.max_contexts, horizon=self.horizon)
            return
        quotient, mapping = self._partition_partial_machine(raw)
        model = {
            "raw": raw,
            "quotient": quotient,
            "raw_to_quotient": mapping,
            "collisions": raw["collisions"],
        }
        # Structural fingerprint excludes support counts and evidence step IDs:
        # repeated confirmation strengthens confidence without creating a new ground.
        structural_transitions = {}
        for q, row in quotient["transitions"].items():
            structural_transitions[q] = {}
            for action, edge in row.items():
                if edge.get("status") == "known":
                    structural_transitions[q][action] = {
                        "status": "known", "output": edge["output"], "successor": edge["successor"]
                    }
                else:
                    structural_transitions[q][action] = {"status": edge.get("status"),
                                                         "alternatives": edge.get("alternatives", [])}
        structural_collisions = [
            {"source": c["source"], "action": c["action"],
             "alternatives": sorted([
                 {"output": a["output"], "successor": a["successor"]}
                 for a in c["alternatives"]
             ], key=lambda x: (x["output"], x["successor"]))}
            for c in raw["collisions"]
        ]
        fingerprint_payload = {
            "horizon": self.horizon,
            "states": quotient["states"],
            "transitions": structural_transitions,
            "collisions": structural_collisions,
        }
        fingerprint = sha256(json.dumps(fingerprint_payload, sort_keys=True).encode()).hexdigest()
        if fingerprint != self._last_model_fingerprint:
            previous = self._last_model_fingerprint
            self.version += 1
            self.version_lineage.append({
                "version": self.version, "reason": self._rebuild_reason,
                "horizon": self.horizon, "previous_fingerprint": previous,
                "fingerprint": fingerprint, "event_count_seen": self.total_event_count,
                "collision_count": len(raw["collisions"]),
            })
            if len(self.version_lineage) > self.version_history_limit:
                del self.version_lineage[:len(self.version_lineage) - self.version_history_limit]
            self._last_model_fingerprint = fingerprint
        self._model = model
        self._raw_to_quotient = mapping

    def _rebuild_adaptive(self) -> None:
        old_horizon = self.horizon
        while True:
            self._rebuild()
            if self.status == "context_budget_exceeded":
                return
            collisions = self._model["collisions"]
            if not collisions:
                break
            if self.horizon >= self.max_horizon:
                break
            self.horizon += 1
            self._rebuild_reason = "history_horizon_refinement_after_collision"
        if self._model["collisions"]:
            self.status = "unresolved_context_collision"
            self.conflict_log.extend(self._model["collisions"][-8:])
            if len(self.conflict_log) > self.conflict_history_limit:
                del self.conflict_log[:len(self.conflict_log) - self.conflict_history_limit]
            self._record_audit("context_collision_unresolved", horizon=self.horizon,
                               collision_count=len(self._model["collisions"]))
        else:
            if self.status == "unresolved_context_collision":
                self.status = "tracking"
            if self.horizon > old_horizon:
                self._record_audit("context_horizon_refined", old_horizon=old_horizon, new_horizon=self.horizon,
                                   reason="observed transition collision")

    # ---------- model query, compilation, verification ----------

    @property
    def predictive_context_count(self) -> int:
        return len(self._model.get("quotient", {}).get("states", []))

    @property
    def current_context(self) -> str | None:
        if not self.records:
            return None
        raw = self._raw_context_key(len(self.records), self.horizon)
        return self._raw_to_quotient.get(raw)

    def predict_next(self, action: str) -> dict[str, Any]:
        if action not in self.actions:
            raise ValueError(f"unknown action: {action}")
        context = self.current_context
        if context is None:
            return {"status": "unknown_initial_context", "context": None, "action": action}
        edge = self._model["quotient"]["transitions"].get(context, {}).get(action)
        if edge is None or edge.get("status") != "known":
            return {"status": "unknown_transition", "context": context, "action": action}
        return {"status": "predicted", "context": context, "action": action,
                "output": list(edge["output"]), "successor": edge["successor"]}

    def compile(self) -> dict[str, Any]:
        states = self._model["quotient"]["states"]
        transitions = self._model["quotient"]["transitions"]
        unknown = []
        ambiguous = []
        for q in states:
            for a in self.actions:
                edge = transitions.get(q, {}).get(a)
                if edge is None:
                    unknown.append([q, a])
                elif edge.get("status") != "known":
                    ambiguous.append([q, a])
        complete = bool(states) and not unknown and not ambiguous
        if self.status == "quarantined":
            status = "quarantined"
        elif self.status == "context_budget_exceeded":
            status = "context_budget_exceeded"
        elif ambiguous or self.status == "unresolved_context_collision":
            status = "unresolved"
        elif complete:
            status = "complete_over_observed_predictive_quotient"
        else:
            status = "partial"
        return {
            "format": self.FORMAT,
            "status": status,
            "version": self.version,
            "fingerprint": self._last_model_fingerprint,
            "signature_mode": self.signature_mode,
            "history_horizon": self.horizon,
            "actions": list(self.actions),
            "channels": list(self.channel_ids),
            "states": states,
            "initial_context": (self._raw_to_quotient.get(self._raw_context_key(0, self.horizon))
                                if self.records and not self.data_truncated else None),
            "startup_context_status": "unknown_due_to_retention_truncation" if self.data_truncated else
                ("observed_boundary_context" if self.records else "not_yet_observed"),
            "current_context": self.current_context,
            "transitions": transitions,
            "unknown_transitions": unknown,
            "ambiguous_transitions": ambiguous,
            "predictive_context_count": len(states),
            "observed_raw_context_count": len(self._model["raw"]["states"]),
            "known_transition_count": sum(1 for q in states for e in transitions.get(q, {}).values() if e.get("status") == "known"),
            "complete_transition_table": complete,
            "support_summary": {
                "minimum_known_edge_support": min(
                    (int(e.get("support", 0)) for row in transitions.values() for e in row.values()
                     if e.get("status") == "known"), default=0),
                "single_support_known_edges": sum(
                    1 for row in transitions.values() for e in row.values()
                    if e.get("status") == "known" and int(e.get("support", 0)) == 1),
                "high_fragmentation_warning": bool(self.records) and
                    (len(states) / max(1, len(self.records))) > 0.75 and len(self.records) >= 8,
            },
            "evidence": {
                "total_committed_events": self.total_event_count,
                "retained_events": len(self.records),
                "retired_events": self.retired_event_count,
                "data_truncated": self.data_truncated,
                "finite_history_horizon_only": True,
                "equivalence_scope": "observed action/output histories under declared channels and finite retained horizon",
                "physical_hidden_state_claim": "not inferred",
            },
            "limitations": [
                "unknown transitions remain unknown; no default edge is inserted",
                "states are finite-horizon predictive classes, not claims about physical hidden-state ontology",
                "history refinement is provisional and can over-split equivalent access histories",
                "when evidence retention is truncated, reconstruction applies only to the retained window",
                "deterministic exact integer observations are assumed; noise/stochasticity require a separate likelihood model",
                "action alphabet and channel schema are supplied by the interface",
            ],
        }

    def verify_observed_evidence(self) -> dict[str, Any]:
        spec = self.compile()
        model = PartialExecutableGround(spec)
        matched = 0
        unknown = 0
        conflicts = 0
        for i, event in enumerate(self.records):
            raw = self._raw_context_key(i, self.horizon)
            context = self._raw_to_quotient.get(raw)
            edge = spec["transitions"].get(context, {}).get(event.action) if context else None
            if edge is None or edge.get("status") != "known":
                unknown += 1
            elif tuple(edge["output"]) == event.output:
                matched += 1
            else:
                conflicts += 1
        return {
            "observed_events": len(self.records), "matched_events": matched,
            "unresolved_events": unknown, "mismatched_events": conflicts,
            "all_known_predictions_match_evidence": conflicts == 0,
            "certificate_scope": "replay of retained observations only; not proof of unseen transitions",
            "candidate_status": spec["status"],
        }

    def export_evidence(self) -> dict[str, Any]:
        return {
            "format": "VG-IncrementalEvidence-1",
            "status": self.status,
            "snapshot": self.snapshot(),
            "retained_events": [e.as_dict() for e in self.records],
            "pending_actions": dict(self.pending_actions),
            "pending_observations": {str(k): dict(v) for k, v in self.pending_observations.items()},
            "conflict_log": self.conflict_log[-64:],
            "version_lineage": self.version_lineage[-self.version_history_limit:],
            "version_lineage_retained_count": len(self.version_lineage),
            "version_count_lifetime": self.version,
            "candidate_ground": self.compile(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "version": self.version,
            "horizon": self.horizon,
            "total_event_count": self.total_event_count,
            "retained_event_count": len(self.records),
            "retired_event_count": self.retired_event_count,
            "data_truncated": self.data_truncated,
            "pending_steps": sorted(set(self.pending_actions) | set(self.pending_observations)),
            "current_context": self.current_context,
            "predictive_context_count": self.predictive_context_count,
            "collision_count": len(self._model.get("collisions", [])),
            "known_transition_count": self.compile()["known_transition_count"],
            "unknown_transition_count": len(self.compile()["unknown_transitions"]),
            "version_lineage_retained_count": len(self.version_lineage),
            "conflict_records_retained_count": len(self.conflict_log),
            "duplicate_count": self.total_duplicate_count,
            "stale_count": self.total_stale_count,
            "fingerprint": self._last_model_fingerprint,
        }

    def _quarantine(self, reason: str, **details: Any) -> None:
        self.status = "quarantined"
        conflict = {"reason": reason, **details, "step": details.get("step"),
                    "event_count": self.total_event_count, "version": self.version}
        self.conflict_log.append(conflict)
        if len(self.conflict_log) > self.conflict_history_limit:
            del self.conflict_log[:len(self.conflict_log) - self.conflict_history_limit]
        self._record_audit("quarantined", **conflict)

    def _ensure_not_quarantined(self) -> None:
        if self.status == "quarantined":
            raise GroundQuarantinedError("ground ingestion is quarantined; review/rebase required")

    def _record_audit(self, kind: str, **payload: Any) -> None:
        self.audit.append({"kind": kind, **payload})

    def _entropy(self, counts: Mapping[Any, int]) -> float:
        n = sum(counts.values())
        if n <= 0:
            return 0.0
        return -sum((c / n) * log2(c / n) for c in counts.values() if c)

    def choose_probe(self, belief: Sequence[str], profiles: Mapping[str, Mapping[str, float | str]],
                     *, max_risk: float = 0.5, risk_weight: float = 1.0) -> dict[str, Any]:
        """Score only evidenced transitions; unknown edges cannot masquerade as probes."""
        states = tuple(sorted(set(belief)))
        if not states:
            return {"status": "no_belief", "selected_action": None, "candidates": []}
        transitions = self._model["quotient"]["transitions"]
        scored = []
        for action in self.actions:
            profile = profiles.get(action)
            if not profile:
                continue
            cost = float(profile.get("cost", 1.0))
            risk = float(profile.get("risk", 1.0))
            if cost < 0 or not 0 <= risk <= 1:
                raise ValueError("invalid probe cost/risk")
            if risk > max_risk:
                continue
            outputs = []
            legal = True
            for q in states:
                edge = transitions.get(q, {}).get(action)
                if edge is None or edge.get("status") != "known":
                    legal = False
                    break
                outputs.append(tuple(edge["output"]))
            if not legal:
                continue
            parts: dict[tuple, int] = defaultdict(int)
            for out in outputs:
                parts[out] += 1
            info = self._entropy(parts)
            score = info / max(cost + risk_weight * risk, 1e-12)
            scored.append({"action": action, "information_bits": info, "cost": cost,
                           "risk": risk, "score": score, "response_classes": len(parts),
                           "side_effect": profile.get("side_effect", "unspecified")})
        scored.sort(key=lambda x: (-x["score"], x["risk"], x["cost"], x["action"]))
        if not scored or scored[0]["information_bits"] <= 0:
            return {"status": "no_safe_evidenced_informative_probe", "selected_action": None,
                    "candidates": scored}
        return {"status": "selected", "selected_action": scored[0]["action"], "candidates": scored}


    def choose_exploration_probe(self, context: str | None,
                                 profiles: Mapping[str, Mapping[str, float | str]],
                                 *, max_risk: float = 0.5, risk_weight: float = 1.0) -> dict[str, Any]:
        """Choose a low-risk unobserved edge to explore.

        Unlike `choose_probe`, this does not claim an information-gain estimate:
        the target transition is unknown by definition. The score is a transparent
        novelty-per-cost heuristic, not a prediction about the observation.
        """
        if context is None or context not in self._model.get("quotient", {}).get("transitions", {}):
            return {"status": "unknown_current_context", "selected_action": None,
                    "information_gain_estimate": None, "candidates": []}
        row = self._model["quotient"]["transitions"].get(context, {})
        candidates = []
        for action in self.actions:
            edge = row.get(action)
            if edge is not None and edge.get("status") == "known":
                continue
            profile = profiles.get(action)
            if profile is None:
                continue
            cost = float(profile.get("cost", 1.0))
            risk = float(profile.get("risk", 1.0))
            if cost < 0 or not 0 <= risk <= 1:
                raise ValueError("invalid exploration cost/risk")
            if risk > max_risk:
                continue
            score = 1.0 / max(cost + risk_weight * risk, 1e-12)
            candidates.append({"action": action, "cost": cost, "risk": risk, "score": score,
                               "side_effect": profile.get("side_effect", "unspecified"),
                               "transition_status": "ambiguous" if edge and edge.get("status") == "ambiguous" else "unknown"})
        candidates.sort(key=lambda x: (-x["score"], x["risk"], x["cost"], x["action"]))
        if not candidates:
            return {"status": "no_safe_unknown_transition_to_probe", "selected_action": None,
                    "information_gain_estimate": None, "candidates": []}
        return {"status": "exploration_probe_selected", "selected_action": candidates[0]["action"],
                "information_gain_estimate": None,
                "score_semantics": "novelty divided by declared cost plus risk penalty; no output entropy claimed",
                "candidates": candidates}

# ---------- utilities ----------

class CounterLike(defaultdict):
    def __init__(self):
        super().__init__(int)


def stream_from_teacher(learner: StreamingGroundInducer, ground: Any, actions: Sequence[str],
                        *, initial_mode: int = 0, post_state_observation: bool = True,
                        channels: Sequence[int] | None = None) -> dict[str, Any]:
    """Test-harness helper. The teacher/hidden mode never enters the learner API."""
    mode = int(initial_mode)
    observed_channels = tuple(channels) if channels is not None else learner.channel_ids
    for step, action in enumerate(actions):
        if post_state_observation:
            mode = ground.next_mode(mode, action)
            raw = ground.emit(mode, action)
        else:
            raw = ground.emit(mode, action)
            mode = ground.next_mode(mode, action)
        learner.begin_action(step, action)
        for ch in observed_channels:
            learner.observe_channel(step, ch, raw[ch], source=f"synthetic-channel-{ch}")
    return {"events_sent": len(actions), "teacher_final_mode_for_test_harness_only": mode,
            "learner_snapshot": learner.snapshot()}


def build_summary(learner: StreamingGroundInducer) -> dict[str, Any]:
    spec = learner.compile()
    return {
        "status": learner.status,
        "version": learner.version,
        "horizon": learner.horizon,
        "predictive_contexts": spec["predictive_context_count"],
        "observed_raw_contexts": spec["observed_raw_context_count"],
        "known_transitions": spec["known_transition_count"],
        "unknown_transitions": len(spec["unknown_transitions"]),
        "ambiguous_transitions": len(spec["ambiguous_transitions"]),
        "events": learner.total_event_count,
        "evidence_check": learner.verify_observed_evidence(),
        "specification": spec,
    }
