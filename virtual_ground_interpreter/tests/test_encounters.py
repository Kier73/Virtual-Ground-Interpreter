import unittest

from vgi.encounters import (
    AssociationAssessment, AssociationError, AssociationHypothesis,
    AssociationLedger, Encounter, EncounterError, EncounterLedger,
    EncounterProvenance,
)


def sample_encounters():
    first = Encounter(
        "encounter-spectrum",
        {"measurement": [410.2, 411.0], "unit": "nm", "note": "unclassified source reading"},
        EncounterProvenance(
            source="sensor-A", source_ref="capture://sensor-A/17",
            captured_at="2026-11-10T10:00:00-05:00", collector="operator",
        ),
        {"environment": {"location_label": "lab-west", "session": 17}},
    )
    second = Encounter(
        "encounter-rhythm",
        {"intervals": [0.49, 0.51, 0.50], "unit": "s"},
        EncounterProvenance(
            source="independent-log", source_ref="log://session-82/row-4",
            collector="importer",
        ),
        {"environment": {"session": 82, "instrument": "clock-B"}},
    )
    third = Encounter(
        "encounter-followup-support",
        {"measurement": [410.4, 411.1], "unit": "nm"},
        EncounterProvenance(source="sensor-A", source_ref="capture://sensor-A/18"),
    )
    fourth = Encounter(
        "encounter-followup-control",
        {"measurement": [420.0, 422.0], "unit": "nm"},
        EncounterProvenance(source="sensor-A", source_ref="capture://sensor-A/19"),
    )
    return first, second, third, fourth


class EncounterLedgerTests(unittest.TestCase):
    def test_encounter_payload_is_preserved_without_semantic_assignment(self):
        source_payload = {"raw": [1, {"odd-key": "uninterpreted"}], "flag": True}
        encounter = Encounter(
            "e1", source_payload, EncounterProvenance(source="unknown-origin"),
            {"session": {"id": "s1"}},
        )
        source_payload["raw"].append(2)
        self.assertEqual(
            encounter.to_dict()["payload"]["raw"],
            [1, {"odd-key": "uninterpreted"}],
        )
        with self.assertRaises(TypeError):
            encounter.context["session"]["id"] = "changed"

    def test_append_is_immutable_and_rejects_duplicate_identifiers(self):
        first, second, _, _ = sample_encounters()
        ledger = EncounterLedger().append(first)
        extended = ledger.append(second)
        self.assertEqual(len(ledger.encounters), 1)
        self.assertEqual(len(extended.encounters), 2)
        with self.assertRaises(EncounterError):
            extended.append(first)

    def test_payload_fingerprint_and_ledger_round_trip(self):
        first, second, _, _ = sample_encounters()
        ledger = EncounterLedger((first, second))
        restored = EncounterLedger.from_json(ledger.to_json())
        self.assertEqual(restored.fingerprint, ledger.fingerprint)
        self.assertEqual(
            restored.get("encounter-spectrum").fingerprint, first.fingerprint
        )

    def test_rejects_non_json_or_non_finite_payloads(self):
        with self.assertRaises(EncounterError):
            Encounter("e1", {"measurement": float("nan")},
                      EncounterProvenance(source="test"))
        with self.assertRaises(EncounterError):
            Encounter("e1", {1: "non-string key"},
                      EncounterProvenance(source="test"))

    def test_external_content_digest_is_validated(self):
        with self.assertRaises(EncounterError):
            EncounterProvenance(source="sensor", content_digest="not-a-digest")


class AssociationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.first, self.second, self.followup, self.control = sample_encounters()
        self.encounters = EncounterLedger(
            (self.first, self.second, self.followup, self.control)
        )
        self.hypothesis = AssociationHypothesis(
            hypothesis_id="hyp-spectrum-rhythm",
            encounter_ids=(self.first.encounter_id, self.second.encounter_id),
            relationship="The independent rhythm may covary with the spectral feature.",
            rationale="The two observations arose in distinct acquisition paths.",
            experiment="Collect paired readings over repeated sessions and compare alignment.",
            falsifier="The relationship fails to reproduce or vanishes under time-shuffled controls.",
            proposed_by="researcher",
        )

    def test_hypotheses_can_bridge_unrelated_sources_and_contexts(self):
        ledger = AssociationLedger().propose(self.hypothesis, self.encounters)
        self.assertEqual(len(ledger.hypotheses), 1)
        self.assertEqual(
            ledger.current_verdict(self.hypothesis.hypothesis_id), "unassessed"
        )
        self.assertEqual(len(self.encounters.encounters), 4)

    def test_proposals_must_reference_existing_encounters(self):
        missing = AssociationHypothesis(
            "hyp-missing", ("encounter-spectrum", "not-present"),
            "Possible relationship.", "A tentative cue.",
            "Repeat the observations under controlled conditions.",
            "The relation fails to reproduce.", "researcher",
        )
        with self.assertRaises(AssociationError):
            AssociationLedger().propose(missing, self.encounters)

    def test_support_and_contradiction_require_new_evidence(self):
        ledger = AssociationLedger().propose(self.hypothesis, self.encounters)
        no_evidence = AssociationAssessment(
            "assessment-empty", self.hypothesis.hypothesis_id, "supports",
            "comparison", "Looks promising.",
        )
        with self.assertRaises(AssociationError):
            ledger.assess(no_evidence, self.encounters)
        basis_only = AssociationAssessment(
            "assessment-reuse", self.hypothesis.hypothesis_id, "supports",
            "re-reading", "The original pair is reconsidered.",
            (self.first.encounter_id, self.second.encounter_id),
        )
        with self.assertRaises(AssociationError):
            ledger.assess(basis_only, self.encounters)

    def test_assessments_append_without_erasing_contradictory_history(self):
        ledger = AssociationLedger().propose(self.hypothesis, self.encounters)
        supporting = AssociationAssessment(
            "assessment-1", self.hypothesis.hypothesis_id, "supports",
            "paired-repeat", "A fresh paired observation matches the prediction.",
            (self.followup.encounter_id,), assessed_by="independent-review",
        )
        ledger = ledger.assess(supporting, self.encounters)
        contradicting = AssociationAssessment(
            "assessment-2", self.hypothesis.hypothesis_id, "contradicts",
            "control-run", "A new control observation contradicts the relationship.",
            (self.control.encounter_id,), assessed_by="independent-review",
        )
        revised = ledger.assess(contradicting, self.encounters)
        self.assertEqual(ledger.current_verdict(self.hypothesis.hypothesis_id), "supports")
        self.assertEqual(revised.current_verdict(self.hypothesis.hypothesis_id), "contradicts")
        self.assertEqual(len(revised.assessment_history(self.hypothesis.hypothesis_id)), 2)
        self.assertEqual(len(revised.hypotheses), 1)

    def test_assessments_must_reference_existing_encounters_and_basis(self):
        ledger = AssociationLedger().propose(self.hypothesis, self.encounters)
        missing = AssociationAssessment(
            "assessment-3", self.hypothesis.hypothesis_id, "inconclusive",
            "partial-observation", "The result is not yet discriminating.",
            ("not-present",),
        )
        with self.assertRaises(AssociationError):
            ledger.assess(missing, self.encounters)
        without_basis = EncounterLedger((self.followup, self.control))
        inconclusive = AssociationAssessment(
            "assessment-4", self.hypothesis.hypothesis_id, "inconclusive",
            "partial-observation", "The original basis was not supplied.",
        )
        with self.assertRaises(AssociationError):
            ledger.assess(inconclusive, without_basis)

    def test_association_ledger_round_trip_preserves_history(self):
        ledger = AssociationLedger().propose(self.hypothesis, self.encounters)
        assessment = AssociationAssessment(
            "assessment-5", self.hypothesis.hypothesis_id, "inconclusive",
            "insufficient-samples", "More paired encounters are required.",
            (self.first.encounter_id,),
        )
        ledger = ledger.assess(assessment, self.encounters)
        restored = AssociationLedger.from_json(ledger.to_json())
        self.assertEqual(restored.fingerprint, ledger.fingerprint)
        self.assertEqual(
            restored.assessment_history(self.hypothesis.hypothesis_id),
            ledger.assessment_history(self.hypothesis.hypothesis_id),
        )


if __name__ == "__main__":
    unittest.main()
