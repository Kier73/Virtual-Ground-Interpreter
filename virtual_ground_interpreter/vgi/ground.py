"""Executable-ground contract and its evidence boundary."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


class GroundError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class GroundSpec:
    """A versioned executable description of a bounded observable domain.

    A GroundSpec declares valid representations and transitions. It does not
    claim to describe unobservable physical state or unbounded reality.
    """

    ground_id: str
    version: str
    domain_id: str
    observer_profiles: tuple[int, ...]
    instruction_set: tuple[str, ...]
    branch_ambiguity_policy: str
    assumptions: tuple[str, ...]
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.ground_id or not self.version or not self.domain_id:
            raise GroundError("ground_id, version and domain_id must be non-empty")
        observers = tuple(self.observer_profiles)
        instructions = tuple(self.instruction_set)
        assumptions = tuple(self.assumptions)
        evidence = tuple(self.evidence)
        if (not observers or len(set(observers)) != len(observers) or
                any(isinstance(x, bool) or not isinstance(x, int) for x in observers)):
            raise GroundError("observer_profiles must contain unique integer identifiers")
        if (not instructions or len(set(instructions)) != len(instructions) or
                any(not isinstance(x, str) or not x for x in instructions)):
            raise GroundError("instruction_set must contain unique non-empty instruction names")
        if any(not isinstance(x, str) or not x for x in assumptions + evidence):
            raise GroundError("assumptions and evidence entries must be non-empty strings")
        object.__setattr__(self, "observer_profiles", observers)
        object.__setattr__(self, "instruction_set", instructions)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "evidence", evidence)
        if self.branch_ambiguity_policy != "trap":
            raise GroundError("the initial interpreter supports only branch_ambiguity_policy='trap'")

    def canonical_dict(self) -> dict[str, object]:
        return {
            "ground_id": self.ground_id,
            "version": self.version,
            "domain_id": self.domain_id,
            "observer_profiles": list(self.observer_profiles),
            "instruction_set": list(self.instruction_set),
            "branch_ambiguity_policy": self.branch_ambiguity_policy,
            "assumptions": list(self.assumptions),
            "evidence": list(self.evidence),
        }

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()


SIGNAL8_GROUND = GroundSpec(
    ground_id="virtual-ground.signal-state.z8",
    version="0.1.0",
    domain_id="signal.phase.cyclic.z8.v1",
    observer_profiles=(1, 3, 5, 7),
    instruction_set=("LOAD", "STORE", "MOVE", "REFRAME", "ADD", "SUB",
                     "BRANCH_EQ", "BRANCH_IDENTITY", "JUMP", "EMIT", "HALT"),
    branch_ambiguity_policy="trap",
    assumptions=(
        "The current value domain is the finite cyclic group Z/8Z.",
        "Signal values are pilot-referenced unit complex phasors.",
        "Observer coordinates are the four odd-unit characters of Z/8Z.",
        "Phase error bounds are conservative absolute bounds in radians.",
        "Conditional equality is evaluated geometrically in phase space.",
        "Ambiguous branch decisions stop execution rather than guessing.",
    ),
    evidence=(
        "Finite exhaustive signal-algebra checks over Z/8Z.",
        "Exhaustive composition and observer-interchange checks.",
        "Synthetic complex-baseband noise and calibration experiments.",
        "No physical analog implementation or general-computation claim.",
    ),
)
