"""Interpretation-neutral encounter memory and append-only association hypotheses."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any


class EncounterError(ValueError):
    """Invalid encounter, provenance, or encounter-ledger operation."""


class AssociationError(ValueError):
    """Invalid association hypothesis, assessment, or cross-reference."""


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise EncounterError("JSON object keys must be strings")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise EncounterError(
        "encounter payloads and context must be finite JSON-compatible values; "
        f"received {type(value).__name__}"
    )


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def _require_text(value: str, label: str, error_type: type[ValueError]) -> None:
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"{label} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class EncounterProvenance:
    """Origin and custody information, without assigning meaning to payload."""

    source: str
    source_ref: str | None = None
    captured_at: str | None = None
    collector: str | None = None
    content_digest: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.source, "provenance source", EncounterError)
        for value, label in (
            (self.source_ref, "source_ref"),
            (self.captured_at, "captured_at"),
            (self.collector, "collector"),
        ):
            if value is not None:
                _require_text(value, label, EncounterError)
        if self.content_digest is not None:
            digest = self.content_digest.lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise EncounterError(
                    "content_digest must be a 64-character SHA-256 hex digest"
                )
            object.__setattr__(self, "content_digest", digest)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_ref": self.source_ref,
            "captured_at": self.captured_at,
            "collector": self.collector,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class Encounter:
    """An immutable, interpretation-neutral record of one received observation.

    payload and context are JSON-compatible envelopes. Large or non-JSON source
    material should remain in its source store and be referenced by source_ref
    and content_digest rather than silently coerced into a semantic label.
    """

    encounter_id: str
    payload: Any
    provenance: EncounterProvenance
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.encounter_id, "encounter_id", EncounterError)
        if not isinstance(self.provenance, EncounterProvenance):
            raise EncounterError("provenance must be an EncounterProvenance")
        if not isinstance(self.context, Mapping):
            raise EncounterError("context must be a JSON object")
        frozen_payload = _freeze_json(self.payload)
        frozen_context = _freeze_json(self.context)
        if not isinstance(frozen_context, Mapping):
            raise EncounterError("context must be a JSON object")
        object.__setattr__(self, "payload", frozen_payload)
        object.__setattr__(self, "context", frozen_context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "payload": _thaw_json(self.payload),
            "provenance": self.provenance.to_dict(),
            "context": _thaw_json(self.context),
        }

    @property
    def fingerprint(self) -> str:
        encoded = _canonical_json(self.to_dict()).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class EncounterLedger:
    """Append-only immutable sequence of encounters."""

    encounters: tuple[Encounter, ...] = ()

    def __post_init__(self) -> None:
        records = tuple(self.encounters)
        if any(not isinstance(item, Encounter) for item in records):
            raise EncounterError("encounters must contain Encounter instances")
        ids = tuple(item.encounter_id for item in records)
        if len(ids) != len(set(ids)):
            raise EncounterError("encounter identifiers must be unique")
        object.__setattr__(self, "encounters", records)

    def append(self, encounter: Encounter) -> "EncounterLedger":
        if not isinstance(encounter, Encounter):
            raise EncounterError("append expects an Encounter")
        if self.contains(encounter.encounter_id):
            raise EncounterError(f"encounter {encounter.encounter_id!r} already exists")
        return EncounterLedger(self.encounters + (encounter,))

    def get(self, encounter_id: str) -> Encounter:
        for item in self.encounters:
            if item.encounter_id == encounter_id:
                return item
        raise EncounterError(f"unknown encounter {encounter_id!r}")

    def contains(self, encounter_id: str) -> bool:
        return any(item.encounter_id == encounter_id for item in self.encounters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-EncounterLedger-1",
            "encounters": [item.to_dict() for item in self.encounters],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            _canonical_json(self.to_dict()).encode("utf-8")
        ).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EncounterLedger":
        if not isinstance(data, Mapping) or data.get("format") != "VGI-EncounterLedger-1":
            raise EncounterError("expected VGI-EncounterLedger-1")
        records = []
        try:
            for raw in data.get("encounters", ()):
                if not isinstance(raw, Mapping):
                    raise EncounterError("each encounter record must be an object")
                records.append(Encounter(
                    encounter_id=raw["encounter_id"],
                    payload=raw["payload"],
                    provenance=EncounterProvenance(**raw["provenance"]),
                    context=raw.get("context", {}),
                ))
        except (KeyError, TypeError) as exc:
            raise EncounterError(f"invalid encounter ledger record: {exc}") from exc
        return cls(tuple(records))

    @classmethod
    def from_json(cls, source: str) -> "EncounterLedger":
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise EncounterError(f"invalid encounter ledger JSON: {exc}") from exc
        return cls.from_dict(data)


@dataclass(frozen=True, slots=True)
class AssociationHypothesis:
    """A proposed relationship, not an established fact or Ground transition."""

    hypothesis_id: str
    encounter_ids: tuple[str, ...]
    relationship: str
    rationale: str
    experiment: str
    falsifier: str
    proposed_by: str

    def __post_init__(self) -> None:
        if isinstance(self.encounter_ids, str):
            raise AssociationError("encounter_ids must be a sequence, not one string")
        for value, label in (
            (self.hypothesis_id, "hypothesis_id"),
            (self.relationship, "relationship"),
            (self.rationale, "rationale"),
            (self.experiment, "experiment"),
            (self.falsifier, "falsifier"),
            (self.proposed_by, "proposed_by"),
        ):
            _require_text(value, label, AssociationError)
        ids = tuple(self.encounter_ids)
        if len(ids) < 2 or any(not isinstance(item, str) or not item.strip() for item in ids):
            raise AssociationError(
                "an association must reference at least two encounter identifiers"
            )
        if len(set(ids)) != len(ids):
            raise AssociationError("encounter identifiers in a hypothesis must be unique")
        object.__setattr__(self, "encounter_ids", ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "encounter_ids": list(self.encounter_ids),
            "relationship": self.relationship,
            "rationale": self.rationale,
            "experiment": self.experiment,
            "falsifier": self.falsifier,
            "proposed_by": self.proposed_by,
        }


@dataclass(frozen=True, slots=True)
class AssociationAssessment:
    """An append-only assessment supported by referenced encounter evidence."""

    assessment_id: str
    hypothesis_id: str
    verdict: str
    method: str
    explanation: str
    evidence_encounter_ids: tuple[str, ...] = ()
    assessed_by: str = "unspecified"

    def __post_init__(self) -> None:
        for value, label in (
            (self.assessment_id, "assessment_id"),
            (self.hypothesis_id, "hypothesis_id"),
            (self.method, "method"),
            (self.explanation, "explanation"),
            (self.assessed_by, "assessed_by"),
        ):
            _require_text(value, label, AssociationError)
        if self.verdict not in ("supports", "contradicts", "inconclusive"):
            raise AssociationError(
                "verdict must be 'supports', 'contradicts', or 'inconclusive'"
            )
        if isinstance(self.evidence_encounter_ids, str):
            raise AssociationError(
                "evidence_encounter_ids must be a sequence, not one string"
            )
        evidence = tuple(self.evidence_encounter_ids)
        if any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise AssociationError("evidence encounter identifiers must be non-empty strings")
        if len(evidence) != len(set(evidence)):
            raise AssociationError("evidence encounter identifiers must be unique")
        if self.verdict in ("supports", "contradicts") and not evidence:
            raise AssociationError(
                "supporting or contradicting assessments require evidence encounter references"
            )
        object.__setattr__(self, "evidence_encounter_ids", evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "hypothesis_id": self.hypothesis_id,
            "verdict": self.verdict,
            "method": self.method,
            "explanation": self.explanation,
            "evidence_encounter_ids": list(self.evidence_encounter_ids),
            "assessed_by": self.assessed_by,
        }


@dataclass(frozen=True, slots=True)
class AssociationLedger:
    """Append-only hypothesis and assessment history, separate from Ground."""

    hypotheses: tuple[AssociationHypothesis, ...] = ()
    assessments: tuple[AssociationAssessment, ...] = ()

    def __post_init__(self) -> None:
        hypotheses = tuple(self.hypotheses)
        assessments = tuple(self.assessments)
        if any(not isinstance(item, AssociationHypothesis) for item in hypotheses):
            raise AssociationError(
                "hypotheses must contain AssociationHypothesis instances"
            )
        if any(not isinstance(item, AssociationAssessment) for item in assessments):
            raise AssociationError(
                "assessments must contain AssociationAssessment instances"
            )
        hypothesis_ids = [item.hypothesis_id for item in hypotheses]
        assessment_ids = [item.assessment_id for item in assessments]
        if len(hypothesis_ids) != len(set(hypothesis_ids)):
            raise AssociationError("hypothesis identifiers must be unique")
        if len(assessment_ids) != len(set(assessment_ids)):
            raise AssociationError("assessment identifiers must be unique")
        known = set(hypothesis_ids)
        if any(item.hypothesis_id not in known for item in assessments):
            raise AssociationError("every assessment must reference a stored hypothesis")
        object.__setattr__(self, "hypotheses", hypotheses)
        object.__setattr__(self, "assessments", assessments)

    def propose(
        self, hypothesis: AssociationHypothesis, encounters: EncounterLedger
    ) -> "AssociationLedger":
        if not isinstance(hypothesis, AssociationHypothesis):
            raise AssociationError("propose expects an AssociationHypothesis")
        if any(item.hypothesis_id == hypothesis.hypothesis_id for item in self.hypotheses):
            raise AssociationError(f"hypothesis {hypothesis.hypothesis_id!r} already exists")
        missing = [item for item in hypothesis.encounter_ids if not encounters.contains(item)]
        if missing:
            raise AssociationError(f"hypothesis references unknown encounters: {missing}")
        return AssociationLedger(self.hypotheses + (hypothesis,), self.assessments)

    def assess(
        self, assessment: AssociationAssessment, encounters: EncounterLedger
    ) -> "AssociationLedger":
        if not isinstance(assessment, AssociationAssessment):
            raise AssociationError("assess expects an AssociationAssessment")
        if any(item.assessment_id == assessment.assessment_id for item in self.assessments):
            raise AssociationError(f"assessment {assessment.assessment_id!r} already exists")
        hypothesis = next(
            (item for item in self.hypotheses
             if item.hypothesis_id == assessment.hypothesis_id),
            None,
        )
        if hypothesis is None:
            raise AssociationError(f"unknown hypothesis {assessment.hypothesis_id!r}")
        missing_basis = [
            item for item in hypothesis.encounter_ids if not encounters.contains(item)
        ]
        if missing_basis:
            raise AssociationError(
                f"encounter ledger is missing the hypothesis basis: {missing_basis}"
            )
        missing = [
            item for item in assessment.evidence_encounter_ids
            if not encounters.contains(item)
        ]
        if missing:
            raise AssociationError(
                f"assessment references unknown evidence encounters: {missing}"
            )
        fresh_evidence = set(assessment.evidence_encounter_ids) - set(hypothesis.encounter_ids)
        if assessment.verdict in ("supports", "contradicts") and not fresh_evidence:
            raise AssociationError(
                "supporting or contradicting assessments require at least one encounter "
                "not used to propose the hypothesis"
            )
        return AssociationLedger(self.hypotheses, self.assessments + (assessment,))

    def assessment_history(self, hypothesis_id: str) -> tuple[AssociationAssessment, ...]:
        if not any(item.hypothesis_id == hypothesis_id for item in self.hypotheses):
            raise AssociationError(f"unknown hypothesis {hypothesis_id!r}")
        return tuple(
            item for item in self.assessments if item.hypothesis_id == hypothesis_id
        )

    def current_verdict(self, hypothesis_id: str) -> str:
        history = self.assessment_history(hypothesis_id)
        return history[-1].verdict if history else "unassessed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-AssociationLedger-1",
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "assessments": [item.to_dict() for item in self.assessments],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            _canonical_json(self.to_dict()).encode("utf-8")
        ).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AssociationLedger":
        if not isinstance(data, Mapping) or data.get("format") != "VGI-AssociationLedger-1":
            raise AssociationError("expected VGI-AssociationLedger-1")
        try:
            hypotheses = tuple(
                AssociationHypothesis(**item) for item in data.get("hypotheses", ())
            )
            assessments = tuple(
                AssociationAssessment(**item) for item in data.get("assessments", ())
            )
        except (TypeError, KeyError) as exc:
            raise AssociationError(f"invalid association ledger record: {exc}") from exc
        return cls(hypotheses, assessments)

    @classmethod
    def from_json(cls, source: str) -> "AssociationLedger":
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise AssociationError(f"invalid association ledger JSON: {exc}") from exc
        return cls.from_dict(data)
