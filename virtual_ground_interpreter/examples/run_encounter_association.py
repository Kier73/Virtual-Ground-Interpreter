import json

from vgi.encounters import (
    AssociationHypothesis, AssociationLedger, Encounter, EncounterLedger,
    EncounterProvenance,
)


def main():
    # These are deliberately unrelated source records. The bridge below is a
    # proposal with a test and falsifier, not an assertion that the sources match.
    spectrum = Encounter(
        "encounter-spectrum",
        {"measurement": [410.2, 411.0], "unit": "nm"},
        EncounterProvenance(
            source="sensor-A", source_ref="capture://sensor-A/17",
            captured_at="2026-11-10T10:00:00-05:00",
        ),
        {"session": 17, "environment": "lab-west"},
    )
    rhythm = Encounter(
        "encounter-rhythm",
        {"intervals": [0.49, 0.51, 0.50], "unit": "s"},
        EncounterProvenance(
            source="independent-log", source_ref="log://session-82/row-4"
        ),
        {"session": 82, "instrument": "clock-B"},
    )

    encounters = EncounterLedger((spectrum, rhythm))
    hypothesis = AssociationHypothesis(
        hypothesis_id="hyp-spectrum-rhythm",
        encounter_ids=(spectrum.encounter_id, rhythm.encounter_id),
        relationship="A periodic process may covary with the spectral feature.",
        rationale="An unexpected cross-source association is worth testing.",
        experiment="Acquire paired spectral and interval observations across repeated sessions.",
        falsifier="The association fails to reproduce or disappears under time-shuffled controls.",
        proposed_by="example-runner",
    )
    associations = AssociationLedger().propose(hypothesis, encounters)

    print(json.dumps({
        "encounter_count": len(encounters.encounters),
        "encounter_fingerprint": encounters.fingerprint,
        "association_count": len(associations.hypotheses),
        "association_fingerprint": associations.fingerprint,
        "hypothesis": hypothesis.to_dict(),
        "hypothesis_status": associations.current_verdict(hypothesis.hypothesis_id),
        "interpretation": (
            "The relationship remains an unassessed hypothesis. Original encounters "
            "are retained separately; no Ground transition or fact is created."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
