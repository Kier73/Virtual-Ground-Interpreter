"""Build 25: non-resettable online Virtual Ground tracking.

Standard-library implementation. The observer starts with an unknown predictive
context, processes actions and asynchronously arriving partial sensor outputs,
and never silently resets when the current ground is contradicted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from math import log2
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json


@dataclass(frozen=True, order=True)
class Hypothesis:
    state: str
    # Expected output vectors for action steps whose observations are incomplete.
    pending: tuple[tuple[int, tuple[int, ...]], ...] = ()

    def pending_map(self) -> dict[int, tuple[int, ...]]:
        return dict(self.pending)


@dataclass(frozen=True)
class Conflict:
    step: int
    action: str
    observed: tuple[tuple[int, int], ...]
    possible_outputs: tuple[tuple[int, ...], ...]
    source: str
    classification: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "action": self.action,
            "observed": {str(k): v for k, v in self.observed},
            "possible_outputs": [list(x) for x in self.possible_outputs],
            "source": self.source,
            "classification": self.classification,
        }


class GroundVersionMonitor:
    """Collect contradictions and propose—but never commit—ground revisions."""

    def __init__(self, ground_fingerprint: str, proposal_threshold: int = 2):
        self.ground_fingerprint = ground_fingerprint
        if proposal_threshold < 2:
            raise ValueError("proposal threshold must be at least two independent conflicts")
        self.proposal_threshold = proposal_threshold
        self.conflicts: list[Conflict] = []
        self.status = "current_ground_consistent"

    def record(self, conflict: Conflict) -> dict[str, Any]:
        self.conflicts.append(conflict)
        distinct_steps = {c.step for c in self.conflicts}
        distinct_actions = {c.action for c in self.conflicts}
        if len(distinct_steps) >= self.proposal_threshold and len(distinct_actions) >= 2:
            self.status = "ground_revision_proposal"
        else:
            self.status = "single_or_unconfirmed_conflict"
        return self.summary()

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_ground_fingerprint": self.ground_fingerprint,
            "conflict_count": len(self.conflicts),
            "distinct_steps": len({c.step for c in self.conflicts}),
            "distinct_actions": sorted({c.action for c in self.conflicts}),
            "auto_committed": False,
            "conflicts": [c.as_dict() for c in self.conflicts],
        }


class OnlineBeliefTracker:
    """Tracks possible current predictive states without a reset assumption.

    Action steps must be submitted in increasing contiguous step order. Sensor
    channel observations may arrive before or after the corresponding action,
    and may arrive out of order across steps. Hypotheses retain expected outputs
    for incomplete steps so late observations can still refine the current state.
    """

    def __init__(self, machine: Any, *, initial_states: Iterable[str] | None = None,
                 max_pending_steps: int = 256, history_limit: int = 256,
                 completed_cache_limit: int = 128):
        if max_pending_steps < 1 or history_limit < 1 or completed_cache_limit < 1:
            raise ValueError("online retention limits must be positive")
        self.machine = machine
        self.states = tuple(machine.states)
        if not self.states:
            raise ValueError("machine has no states")
        self.actions = tuple(next(iter(machine.transitions.values())).keys())
        output_widths = {len(machine.outputs[q][a]) for q in self.states for a in self.actions}
        if len(output_widths) != 1:
            raise ValueError("online tracker requires a fixed output-channel schema")
        self.channel_count = next(iter(output_widths))
        self.initial_states = tuple(initial_states) if initial_states is not None else self.states
        if not set(self.initial_states).issubset(self.states) or not self.initial_states:
            raise ValueError("invalid initial candidate states")
        self.hypotheses: set[Hypothesis] = {Hypothesis(q) for q in self.initial_states}
        self.observations: dict[int, dict[int, int]] = defaultdict(dict)
        self.actions_by_step: dict[int, str] = {}
        self.source_by_step: dict[int, set[str]] = defaultdict(set)
        self.last_action_step: int | None = None
        self.max_pending_steps = max_pending_steps
        self.history_limit = history_limit
        self.completed_cache_limit = completed_cache_limit
        self.completed_cache: OrderedDict[int, tuple[str | None, dict[int, int]]] = OrderedDict()
        self.completed_step_count = 0
        self.retired_step_count = 0
        self.history_total_count = 0
        self.status = "tracking"
        self.conflict: Conflict | None = None
        self.history: list[dict[str, Any]] = []
        self.version_monitor = GroundVersionMonitor(self.fingerprint())

    def fingerprint(self) -> str:
        data = {
            "states": list(self.machine.states),
            "transitions": self.machine.transitions,
            "outputs": self.machine.outputs,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=list).encode()).hexdigest()

    @property
    def belief(self) -> tuple[str, ...]:
        return tuple(sorted({h.state for h in self.hypotheses}))

    @property
    def hypothesis_count(self) -> int:
        return len(self.hypotheses)

    @property
    def unresolved_steps(self) -> tuple[int, ...]:
        steps: set[int] = set()
        for h in self.hypotheses:
            steps.update(s for s, _ in h.pending)
        return tuple(sorted(steps))

    def begin_action(self, step: int, action: str) -> dict[str, Any]:
        if self.status == "contradicted":
            raise RuntimeError("ground is contradicted; explicit review/rebase required")
        if action not in self.actions:
            raise ValueError(f"unknown action: {action}")
        if step in self.actions_by_step:
            if self.actions_by_step[step] != action:
                raise ValueError("step already registered with a different action")
            return self.snapshot()
        expected_next = 0 if self.last_action_step is None else self.last_action_step + 1
        if step != expected_next:
            raise ValueError(f"action step must be contiguous; expected {expected_next}")
        buffered_steps = set(self.unresolved_steps) | set(self.observations)
        if len(buffered_steps) >= self.max_pending_steps:
            raise RuntimeError("pending observation horizon exceeded")
        self.actions_by_step[step] = action
        self.last_action_step = step
        expanded: set[Hypothesis] = set()
        for h in self.hypotheses:
            out = tuple(self.machine.outputs[h.state][action])
            nxt = self.machine.transitions[h.state][action]
            pending = h.pending_map()
            pending[step] = out
            if self._matches(out, self.observations.get(step, {})):
                expanded.add(Hypothesis(nxt, tuple(sorted(pending.items()))))
        if not expanded:
            self._enter_conflict(step, action, self.observations.get(step, {}), "no_hypothesis_matches_pre_arrived_observation", "action-interface")
            return self.snapshot()
        self.hypotheses = self._prune_complete(expanded)
        self._record("action", step=step, action=action)
        return self.snapshot()

    def observe_channel(self, step: int, channel: int, value: int, *, source: str = "sensor",
                        local_sequence: int | None = None, local_timestamp: float | None = None) -> dict[str, Any]:
        if self.status == "contradicted":
            raise RuntimeError("ground is contradicted; observation retained only by the external event log")
        if not 0 <= channel < self.channel_count:
            raise ValueError("channel index outside model schema")
        if step in self.completed_cache:
            old_action, old_row = self.completed_cache[step]
            if old_row.get(channel) == value:
                return self.snapshot()
            conflicting_row = dict(old_row)
            conflicting_row[channel] = int(value)
            self._enter_conflict(step, old_action or "<completed-step>", conflicting_row,
                                 "conflicting_late_duplicate_sensor_value", source)
            return self.snapshot()
        if self.last_action_step is not None and step <= self.last_action_step and step not in self.actions_by_step:
            self._record("stale_observation_outside_retention", step=step, channel=channel, source=source)
            return self.snapshot()
        buffered_steps = set(self.unresolved_steps) | set(self.observations)
        if step not in buffered_steps and len(buffered_steps) >= self.max_pending_steps:
            raise RuntimeError("pending observation horizon exceeded")
        prior = self.observations[step].get(channel)
        if prior is not None and prior != value:
            conflicting_row = dict(self.observations[step])
            conflicting_row[channel] = int(value)
            self._enter_conflict(step, self.actions_by_step.get(step, "<pending-action>"),
                                 conflicting_row, "conflicting_duplicate_sensor_value", source)
            return self.snapshot()
        if prior is not None and prior == value:
            # Idempotent retransmission: do not re-filter a hypothesis whose
            # completed-step prediction may already have been compacted away.
            self.source_by_step[step].add(source)
            return self.snapshot()
        self.observations[step][channel] = int(value)
        self.source_by_step[step].add(source)
        if step not in self.actions_by_step:
            self._record("sensor_arrived_before_action", step=step, channel=channel, source=source)
            return self.snapshot()
        filtered: set[Hypothesis] = set()
        for h in self.hypotheses:
            expected = h.pending_map().get(step)
            if expected is not None and self._matches(expected, self.observations[step]):
                filtered.add(h)
        if not filtered:
            possible = tuple(sorted({
                h.pending_map()[step] for h in self.hypotheses if step in h.pending_map()
            }))
            self._enter_conflict(step, self.actions_by_step[step], self.observations[step],
                                 "observation_not_predicted_by_any_live_hypothesis", source,
                                 possible_outputs=possible)
            return self.snapshot()
        self.hypotheses = self._prune_complete(filtered)
        self._record("sensor_observation", step=step, channel=channel, value=value, source=source,
                     local_sequence=local_sequence, local_timestamp=local_timestamp)
        return self.snapshot()

    def _matches(self, expected: Sequence[int], observed: Mapping[int, int]) -> bool:
        return all(expected[i] == v for i, v in observed.items())

    def _prune_complete(self, hypotheses: set[Hypothesis]) -> set[Hypothesis]:
        complete = sorted(
            step for step, obs in self.observations.items()
            if len(obs) == self.channel_count
        )
        out: set[Hypothesis] = set()
        for h in hypotheses:
            pending = tuple((s, y) for s, y in h.pending if s not in complete)
            out.add(Hypothesis(h.state, pending))
        # Completed observations are compacted out of the live tracker. Keep a
        # bounded duplicate cache and bounded audit ring; older retransmissions
        # are treated as stale rather than being misinterpreted as new evidence.
        for step in complete:
            row = dict(self.observations.pop(step))
            action = self.actions_by_step.pop(step, None)
            self.source_by_step.pop(step, None)
            self.completed_cache[step] = (action, row)
            self.completed_step_count += 1
            while len(self.completed_cache) > self.completed_cache_limit:
                self.completed_cache.popitem(last=False)
                self.retired_step_count += 1
        return out

    def _enter_conflict(self, step: int, action: str, observed: Mapping[int, int], classification: str,
                        source: str, possible_outputs: tuple[tuple[int, ...], ...] = ()) -> None:
        self.conflict = Conflict(step, action, tuple(sorted(observed.items())), possible_outputs,
                                 source, classification)
        self.status = "contradicted"
        self.version_monitor.record(self.conflict)
        self._record("ground_contradiction", **self.conflict.as_dict())

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "belief": list(self.belief),
            "hypothesis_count": self.hypothesis_count,
            "unresolved_steps": list(self.unresolved_steps),
            "last_action_step": self.last_action_step,
            "buffered_observation_steps": sorted(set(self.observations) | set(self.unresolved_steps)),
            "completed_step_count": self.completed_step_count,
            "retired_step_count": self.retired_step_count,
            "retained_history_records": len(self.history),
            "history_total_count": self.history_total_count,
            "conflict": self.conflict.as_dict() if self.conflict else None,
            "version_monitor": self.version_monitor.summary(),
        }

    def _record(self, kind: str, **data: Any) -> None:
        self.history.append({"kind": kind, **data})
        self.history_total_count += 1
        if len(self.history) > self.history_limit:
            del self.history[:len(self.history) - self.history_limit]

    def export_evidence(self) -> dict[str, Any]:
        return {
            "format": "VG-OnlineEvidence-1",
            "ground_fingerprint": self.fingerprint(),
            "unknown_initial_context": True,
            "initial_candidate_states": list(self.initial_states),
            "actions": {str(k): v for k, v in self.actions_by_step.items()},
            "observations": {str(k): {str(c): v for c, v in row.items()} for k, row in self.observations.items()},
            "status": self.status,
            "completed_step_count": self.completed_step_count,
            "retired_step_count": self.retired_step_count,
            "retained_completed_cache": [
                {"step": s, "action": a, "observations": {str(c): v for c, v in row.items()}}
                for s, (a, row) in self.completed_cache.items()
            ],
            "snapshot": self.snapshot(),
            "history_total_count": self.history_total_count,
            "history": self.history,
        }


@dataclass(frozen=True)
class ProbeProfile:
    cost: float
    risk: float
    side_effect: str = "none"


class SafeProbeScheduler:
    """One-step expected information gain, penalized for cost and risk."""
    def __init__(self, machine: Any, *, risk_weight: float = 2.0, max_risk: float = 0.35):
        if risk_weight < 0 or not 0 <= max_risk <= 1:
            raise ValueError("risk weight must be nonnegative and max_risk must lie in [0,1]")
        self.machine = machine
        self.risk_weight = risk_weight
        self.max_risk = max_risk

    @staticmethod
    def _entropy(counts: Mapping[tuple[int, ...], int]) -> float:
        n = sum(counts.values())
        if n <= 0:
            return 0.0
        return -sum((v / n) * log2(v / n) for v in counts.values() if v)

    def choose(self, belief: Iterable[str], profiles: Mapping[str, ProbeProfile]) -> dict[str, Any]:
        states = tuple(sorted(set(belief)))
        if not states:
            return {"status": "no_belief", "selected_action": None, "candidates": []}
        candidates = []
        for action in self.machine.transitions[states[0]]:
            profile = profiles.get(action, ProbeProfile(float("inf"), 1.0, "unavailable"))
            if profile.cost < 0 or not 0 <= profile.risk <= 1:
                raise ValueError(f"invalid cost/risk profile for {action}")
            if profile.risk > self.max_risk:
                continue
            partitions: dict[tuple[int, ...], int] = defaultdict(int)
            for q in states:
                partitions[tuple(self.machine.outputs[q][action])] += 1
            info = self._entropy(partitions)
            denom = profile.cost + self.risk_weight * profile.risk
            score = info / max(denom, 1e-12)
            candidates.append({
                "action": action, "information_bits": info,
                "cost": profile.cost, "risk": profile.risk,
                "side_effect": profile.side_effect,
                "response_classes": len(partitions), "score": score,
            })
        candidates.sort(key=lambda x: (-x["score"], x["risk"], x["cost"], x["action"]))
        if not candidates or candidates[0]["information_bits"] <= 0:
            return {"status": "no_safe_informative_probe", "selected_action": None, "candidates": candidates}
        return {"status": "selected", "selected_action": candidates[0]["action"], "candidates": candidates}


@dataclass
class ClockFit:
    source: str
    anchors: list[tuple[float, float]] = field(default_factory=list)
    intercept: float | None = None
    slope: float | None = None
    max_anchors: int = 64
    total_anchor_count: int = 0

    def add_anchor(self, local_time: float, reference_time: float) -> None:
        self.anchors.append((float(local_time), float(reference_time)))
        self.total_anchor_count += 1
        if len(self.anchors) > self.max_anchors:
            del self.anchors[:len(self.anchors) - self.max_anchors]
        self._refit()

    def _refit(self) -> None:
        if len(self.anchors) == 1:
            x, y = self.anchors[0]
            self.intercept, self.slope = y - x, None
            return
        if len(self.anchors) < 2:
            self.intercept = self.slope = None
            return
        xs = [x for x, _ in self.anchors]
        ys = [y for _, y in self.anchors]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        denom = sum((x - mx) ** 2 for x in xs)
        if denom <= 1e-15:
            self.intercept = self.slope = None
            return
        self.slope = sum((x - mx) * (y - my) for x, y in self.anchors) / denom
        self.intercept = my - self.slope * mx

    @property
    def status(self) -> str:
        if not self.anchors:
            return "unsynchronized_local_clock"
        if len(self.anchors) == 1:
            return "offset_only_drift_unresolved"
        if self.slope is None:
            return "insufficient_clock_geometry"
        return "affine_clock_calibrated"

    def to_reference(self, local_time: float) -> float:
        if len(self.anchors) < 2 or self.intercept is None or self.slope is None:
            raise RuntimeError("clock mapping unavailable: at least two distinct paired anchors are required")
        return self.intercept + self.slope * float(local_time)

    def as_dict(self) -> dict[str, Any]:
        return {"source": self.source, "status": self.status, "retained_anchor_count": len(self.anchors),
                "total_anchor_count": self.total_anchor_count,
                "intercept": self.intercept, "slope": self.slope}


class LocalClockRegistry:
    """Keeps source clocks separate; joins only by explicit event/step identity."""
    def __init__(self, *, event_history_limit: int = 512, unmatched_history_limit: int = 256):
        self.clocks: dict[str, ClockFit] = {}
        self.last_sequence: dict[str, int] = {}
        self.events: list[dict[str, Any]] = []
        self.unmatched: list[dict[str, Any]] = []
        self.event_history_limit = event_history_limit
        self.unmatched_history_limit = unmatched_history_limit
        self.total_event_count = 0
        self.total_unmatched_count = 0

    def add_anchor(self, source: str, local_time: float, reference_time: float) -> None:
        self.clocks.setdefault(source, ClockFit(source)).add_anchor(local_time, reference_time)

    def add_event(self, *, source: str, source_sequence: int, local_timestamp: float,
                  channel: int, value: int, step_id: int | None = None) -> dict[str, Any]:
        prev = self.last_sequence.get(source)
        if prev is not None and source_sequence <= prev:
            raise ValueError("source sequence must increase monotonically")
        self.last_sequence[source] = source_sequence
        ev = {"source": source, "source_sequence": source_sequence,
              "local_timestamp": float(local_timestamp), "channel": int(channel),
              "value": int(value), "step_id": step_id}
        self.events.append(ev)
        self.total_event_count += 1
        if len(self.events) > self.event_history_limit:
            del self.events[:len(self.events) - self.event_history_limit]
        if step_id is None:
            self.unmatched.append(ev.copy())
            self.total_unmatched_count += 1
            if len(self.unmatched) > self.unmatched_history_limit:
                del self.unmatched[:len(self.unmatched) - self.unmatched_history_limit]
            join_status = "unmatched_no_shared_event_identity"
        else:
            join_status = "joined_by_explicit_step_id"
        return {"event": ev, "join_status": join_status,
                "clock": self.clocks.setdefault(source, ClockFit(source)).as_dict()}

    def deliver(self, tracker: OnlineBeliefTracker, receipt: Mapping[str, Any]) -> dict[str, Any]:
        """Deliver a keyed sensor receipt to the online tracker; leave unkeyed events unmatched."""
        if receipt.get("join_status") != "joined_by_explicit_step_id":
            return {"status": "unmatched", "reason": receipt.get("join_status")}
        event = receipt["event"]
        return tracker.observe_channel(
            int(event["step_id"]), int(event["channel"]), int(event["value"]),
            source=str(event["source"]), local_sequence=int(event["source_sequence"]),
            local_timestamp=float(event["local_timestamp"]),
        )

    def map_time(self, source: str, local_timestamp: float) -> float:
        if source not in self.clocks:
            raise RuntimeError("unknown source clock")
        return self.clocks[source].to_reference(local_timestamp)

    def summary(self) -> dict[str, Any]:
        return {"clock_models": {s: c.as_dict() for s, c in sorted(self.clocks.items())},
                "retained_event_count": len(self.events), "total_event_count": self.total_event_count,
                "retained_unmatched_event_count": len(self.unmatched),
                "total_unmatched_event_count": self.total_unmatched_count,
                "timestamp_join_policy": "never join different source clocks by raw timestamp alone"}


def load_machine_from_spec(path: str):
    """Load a Build 24 VG-PredictiveMealy-1 specification without a teacher/reset."""
    from latent_ground import LearnedMealyGround
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "specification" in data:
        data = data["specification"]
    return LearnedMealyGround.from_dict(data)
