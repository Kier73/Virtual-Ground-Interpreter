"""Build 30: task-conditioned adaptive observer selection over Build 29 features.

The selector evaluates candidate segmentation/token views on a labelled calibration
set, then freezes the chosen profile before evaluating held-out streams. It does not
use held-out labels during selection. This is a controlled calibration experiment,
not an unsupervised universal observer.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import math
import sys
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD29 = ROOT / "notes" / "build29_workspace"
if str(BUILD29) not in sys.path:
    sys.path.insert(0, str(BUILD29))
from continuous_signal import SignalChannel, analyze_signals


@dataclass(frozen=True)
class ObserverProfile:
    boundary_view: str
    token_view: str
    frame_size: int = 256
    hop: int = 64
    token_tolerance: float = 0.09

    @property
    def profile_id(self) -> str:
        return f"{self.boundary_view}__{self.token_view}__f{self.frame_size}_h{self.hop}"


@dataclass(frozen=True)
class LabeledTrace:
    trace_id: str
    channels: tuple[SignalChannel, ...]
    boundary_frames: tuple[int, ...]
    event_classes: tuple[int, ...]


@dataclass
class ProfileScore:
    profile: ObserverProfile
    boundary_f1: float
    token_pairwise_accuracy: float
    utility: float
    trace_count: int
    valid_trace_count: int


def _boundary_f1(pred: Sequence[int], truth: Sequence[int], tolerance: int = 2) -> float:
    remaining = set(range(len(truth)))
    tp = 0
    for p in sorted(pred):
        candidates = [i for i in remaining if abs(int(p) - int(truth[i])) <= tolerance]
        if candidates:
            j = min(candidates, key=lambda i: abs(int(p) - int(truth[i])))
            remaining.remove(j)
            tp += 1
    fp = len(pred) - tp
    fn = len(truth) - tp
    precision = tp / (tp + fp) if tp + fp else (1.0 if not truth else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _pairwise_class_accuracy(tokens: Sequence[str], labels: Sequence[int],
                             event_indices: Sequence[int]) -> float:
    """Evaluate token equivalence only across distinct matched ground-truth events.

    Boundary labels are used only by the calibration/evaluator. Each predicted
    segment is aligned by its midpoint to a hidden evaluator interval; the
    observer itself never receives those intervals during analysis.
    """
    n = min(len(tokens), len(labels), len(event_indices))
    correct = total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if event_indices[i] == event_indices[j]:
                continue
            same_label = labels[event_indices[i]] == labels[event_indices[j]]
            same_token = tokens[i] == tokens[j]
            correct += int(same_label == same_token)
            total += 1
    return correct / total if total else 0.0


def evaluate_profile(profile: ObserverProfile, traces: Sequence[LabeledTrace],
                     boundary_weight: float = 0.5, token_weight: float = 0.5) -> ProfileScore:
    if abs(boundary_weight + token_weight - 1.0) > 1e-9 or min(boundary_weight, token_weight) < 0:
        raise ValueError("utility weights must be nonnegative and sum to one")
    b_scores: list[float] = []
    t_scores: list[float] = []
    for trace in traces:
        try:
            result = analyze_signals(
                trace.channels, frame_size=profile.frame_size, hop=profile.hop,
                observer_view=profile.boundary_view, token_view=profile.token_view,
                token_tolerance=profile.token_tolerance,
            )
            if result.selected is None:
                continue
            predicted = result.selected.boundaries
            b_scores.append(_boundary_f1(predicted, trace.boundary_frames))
            tokens = [segment.token for segment in result.selected.segments]
            indices = []
            for segment in result.selected.segments:
                midpoint = 0.5 * (segment.start_frame + segment.end_frame)
                indices.append(bisect_right(trace.boundary_frames, midpoint))
            t_scores.append(_pairwise_class_accuracy(tokens, trace.event_classes, indices))
        except (ValueError, RuntimeError):
            continue
    valid = min(len(b_scores), len(t_scores))
    if not valid:
        return ProfileScore(profile, 0.0, 0.0, -math.inf, len(traces), 0)
    b = sum(b_scores[:valid]) / valid
    t = sum(t_scores[:valid]) / valid
    utility = boundary_weight * b + token_weight * t
    return ProfileScore(profile, b, t, utility, len(traces), valid)


def candidate_profiles() -> list[ObserverProfile]:
    # Fixed time-frequency resolution is held constant in this build so the
    # experiment isolates observer-view selection from scale selection.
    return [ObserverProfile(bv, tv) for bv in ("harmonic", "temporal", "combined")
            for tv in ("harmonic", "temporal", "combined")]


def select_observer(traces: Sequence[LabeledTrace], *, boundary_weight: float = 0.5,
                    token_weight: float = 0.5, ambiguity_epsilon: float = 0.015) -> dict:
    if len(traces) < 2:
        raise ValueError("at least two calibration traces are required")
    scores = [evaluate_profile(p, traces, boundary_weight, token_weight)
              for p in candidate_profiles()]
    scores.sort(key=lambda s: (s.utility,
                               -int(s.profile.boundary_view == "combined")
                               -int(s.profile.token_view == "combined")), reverse=True)
    best = scores[0]
    plausible = [s for s in scores if best.utility - s.utility <= ambiguity_epsilon]
    return {
        "selected_profile": best.profile,
        "selected_utility": best.utility,
        "plausible_profiles": [s.profile for s in plausible],
        "ambiguous_selection": len(plausible) > 1,
        "scores": scores,
        "selection_basis": "calibration-only task utility; held-out traces excluded",
    }


def evaluate_on_heldout(profile: ObserverProfile, traces: Sequence[LabeledTrace],
                        boundary_weight: float = 0.5, token_weight: float = 0.5) -> ProfileScore:
    return evaluate_profile(profile, traces, boundary_weight, token_weight)
