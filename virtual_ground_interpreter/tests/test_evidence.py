import hashlib
import unittest
from dataclasses import replace

from vgi.channels import ChannelContract, ChannelExchangeLedger, ChannelMessage
from vgi.encounters import EncounterLedger, EncounterProvenance
from vgi.evidence import (
    EvidenceError, GroundReconstructionCertificate, GroundReconstructionVerifier,
    TransitionEvidenceLedger, TransitionEvidencePolicy, TransportFrameReceipt,
)
from vgi.transitions import (
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def telemetry_contract():
    return ChannelContract(
        "telemetry.bus", "telemetry.frame/1",
        observation_schema="vgi.transition-observation/1",
    )


def observed_message(message_id, source, state, action, status, target=None, output=None,
                     source_sequence=1, alternatives=None):
    payload = {"status": status, "source_state": state, "action": action}
    if status == "known":
        payload.update({"target": target, "output": output})
    elif status == "ambiguous":
        payload["outcomes"] = alternatives
    return ChannelMessage(
        message_id, "telemetry.bus", "telemetry.frame/1", "observation", payload,
        EncounterProvenance(source, f"capture://{source}/{source_sequence}", collector="fixture"),
    )


def make_exchange(messages):
    exchange = ChannelExchangeLedger()
    for item in messages:
        exchange = exchange.record_observation(telemetry_contract(), item)
    return exchange, exchange.to_encounter_ledger()


def make_policy(strict=True, quorum=2, sources=("sensor-A", "sensor-B")):
    return TransitionEvidencePolicy(
        "plant-alpha", digest("plant-alpha/context/revision-1"),
        sources, quorum, strict,
    )


def frame_for(message, sequence):
    return TransportFrameReceipt.capture(
        message, transport_id="reliable-transport-A", sequence=sequence,
        received_at="2026-11-10T20:10:00-05:00",
    )


def ingest(messages, pol=None):
    pol = pol or make_policy()
    exchange, encounters = make_exchange(messages)
    ledger = TransitionEvidenceLedger(pol)
    for sequence, item in enumerate(messages, 1):
        ledger = ledger.ingest_channel_message(
            exchange, item.message_id, frame_for(item, sequence), encounters
        )
    return ledger, exchange, encounters


class TransitionEvidenceTests(unittest.TestCase):
    def test_observation_is_not_established_until_explicit_finalization(self):
        item = observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3])
        ledger, _, _ = ingest([item], make_policy(quorum=2))
        self.assertEqual(ledger.status("s0", "STEP").status, "PENDING")
        closed = ledger.finalize("s0", "STEP")
        self.assertEqual(closed.decision("s0", "STEP").status, "REFUSED")
        ground = closed.build_ground(
            states=("s0", "s1"), actions=("STEP",), initial_state="s0",
            channels=("signal",),
        )
        self.assertEqual(ground.status("s0", "STEP"), "unknown")

    def test_quorum_authorizes_transition_with_transport_and_source_lineage(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3]),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s1", [3]),
        ]
        ledger, _, _ = ingest(messages)
        decision = ledger.status("s0", "STEP")
        self.assertEqual(decision.status, "QUORUM")
        self.assertEqual(decision.agreeing_sources, ("sensor-A", "sensor-B"))
        closed = ledger.finalize("s0", "STEP")
        self.assertEqual(closed.decision("s0", "STEP").status, "AUTHORIZED")
        ground = closed.build_ground(
            states=("s0", "s1"), actions=("STEP",), initial_state="s0",
            channels=("signal",),
        )
        step = ground.step("s0", "STEP")
        self.assertEqual((step.target, step.output, step.support_count), ("s1", (3,), 2))
        self.assertEqual(len(step.evidence), 2)

    def test_strict_dissent_is_conflict(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3]),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s2", [3]),
            observed_message("c1", "sensor-C", "s0", "STEP", "known", "s1", [3]),
        ]
        pol = make_policy(True, 2, ("sensor-A", "sensor-B", "sensor-C"))
        ledger, _, _ = ingest(messages, pol)
        decision = ledger.status("s0", "STEP")
        self.assertEqual(decision.status, "CONFLICT")
        self.assertEqual(decision.dissenting_sources, ("sensor-B",))

    def test_non_strict_quorum_keeps_dissent_visible(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3]),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s2", [3]),
            observed_message("c1", "sensor-C", "s0", "STEP", "known", "s1", [3]),
        ]
        ledger, _, _ = ingest(messages, make_policy(False, 2, ("sensor-A", "sensor-B", "sensor-C")))
        decision = ledger.status("s0", "STEP")
        self.assertEqual(decision.status, "QUORUM")
        self.assertEqual(decision.dissenting_sources, ("sensor-B",))

    def test_unknown_and_ambiguous_are_indeterminate_not_negative_votes(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "unknown"),
            observed_message(
                "b1", "sensor-B", "s0", "STEP", "ambiguous",
                alternatives=[{"target": "s1", "output": [2]}, {"target": "s2", "output": [4]}],
            ),
        ]
        ledger, _, _ = ingest(messages)
        decision = ledger.status("s0", "STEP")
        self.assertEqual(decision.status, "PENDING")
        self.assertEqual(decision.indeterminate_sources, ("sensor-A", "sensor-B"))
        self.assertIsNone(decision.outcome)

    def test_same_source_changing_claim_is_conflict_and_is_retained(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3], 1),
            observed_message("a2", "sensor-A", "s0", "STEP", "known", "s2", [4], 2),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s1", [3], 1),
        ]
        ledger, _, _ = ingest(messages)
        self.assertEqual(ledger.status("s0", "STEP").conflicting_sources, ("sensor-A",))
        self.assertEqual(ledger.status("s0", "STEP").status, "CONFLICT")

    def test_transport_sequences_are_scoped_by_source_and_channel(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3], 1),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s1", [3], 1),
        ]
        ledger, _, _ = ingest(messages)
        self.assertEqual(len(ledger.evidence), 2)

    def test_finalized_event_rejects_late_evidence(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3]),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s1", [3]),
        ]
        ledger, exchange, _ = ingest(messages)
        closed = ledger.finalize("s0", "STEP")
        late = observed_message("a2", "sensor-A", "s0", "STEP", "known", "s1", [3], 8)
        next_exchange = exchange.record_observation(telemetry_contract(), late)
        with self.assertRaises(EvidenceError):
            closed.ingest_channel_message(
                next_exchange, "a2", frame_for(late, 8),
                next_exchange.to_encounter_ledger()
            )

    def test_request_intents_cannot_be_promoted_to_transition_evidence(self):
        duplex = ChannelContract(
            "duplex", "duplex/1", request_schema="request/1", response_schema="reply/1"
        )
        request = ChannelMessage(
            "req-1", "duplex", "duplex/1", "request", {"operation": "probe"},
            EncounterProvenance("client"),
        )
        exchange = ChannelExchangeLedger().propose_request(duplex, request)
        with self.assertRaises(EvidenceError):
            from vgi.evidence import TransitionEvidence
            TransitionEvidence.from_channel_message(
                exchange, "req-1", frame_for(request, 1), EncounterLedger(),
                ground_id="plant-alpha", context_digest=make_policy().context_digest,
            )

    def test_transport_receipt_must_match_exact_message_and_payload(self):
        message = observed_message("frame-check", "sensor-A", "s0", "STEP", "known", "s1", [3])
        exchange, encounters = make_exchange([message])
        frame = frame_for(message, 4)
        tampered = replace(frame, payload_digest=digest("different-payload"))
        from vgi.evidence import TransitionEvidence
        with self.assertRaises(EvidenceError):
            TransitionEvidence.from_channel_message(
                exchange, message.message_id, tampered, encounters,
                ground_id="plant-alpha", context_digest=make_policy().context_digest,
            )
        wrong_message = replace(frame, message_id="another-message")
        with self.assertRaises(EvidenceError):
            TransitionEvidence.from_channel_message(
                exchange, message.message_id, wrong_message, encounters,
                ground_id="plant-alpha", context_digest=make_policy().context_digest,
            )

    def test_frame_receipt_captures_distinct_transport_coordinates(self):
        message = observed_message("frame-roundtrip", "sensor-A", "s0", "STEP", "known", "s1", [3])
        frame = frame_for(message, 23)
        restored = TransportFrameReceipt(**frame.to_dict())
        self.assertEqual(restored, frame)
        self.assertEqual(restored.payload_digest, hashlib.sha256(
            __import__("json").dumps(message.to_dict(), sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")
        ).hexdigest())

    def test_evidence_ledger_round_trip_preserves_finalization(self):
        messages = [
            observed_message("a1", "sensor-A", "s0", "STEP", "known", "s1", [3]),
            observed_message("b1", "sensor-B", "s0", "STEP", "known", "s1", [3]),
        ]
        ledger, _, _ = ingest(messages)
        closed = ledger.finalize("s0", "STEP")
        restored = TransitionEvidenceLedger.from_json(closed.to_json())
        self.assertEqual(restored.fingerprint, closed.fingerprint)
        self.assertEqual(restored.decision("s0", "STEP").status, "AUTHORIZED")


def complete_ground():
    return GroundTransitionSystem(
        states=("s0", "s1"), actions=("STEP",), initial_state="s0",
        channels=("signal",),
        observations=(
            TransitionObservation("s0", "STEP", (TransitionOutcome("s1", (3,)),)),
            TransitionObservation("s1", "STEP", (TransitionOutcome("s1", (4,)),)),
        ),
    )


    def test_default_evidence_id_uses_the_bound_transport_frame_sequence(self):
        from vgi.evidence import TransitionEvidence

        message = observed_message(
            "sequence-bound", "sensor-A", "s0", "STEP",
            "known", "s1", [3], source_sequence=1,
        )
        exchange, encounters = make_exchange([message])
        frame = frame_for(message, 23)
        evidence = TransitionEvidence.from_channel_message(
            exchange,
            message.message_id,
            frame,
            encounters,
            ground_id="plant-alpha",
            context_digest=make_policy().context_digest,
        )
        self.assertEqual(evidence.transport_sequence, 23)
        self.assertEqual(evidence.evidence_id, "sequence-bound:23")


class GroundReconstructionTests(unittest.TestCase):
    def test_finite_compiled_replay_certificate_is_revalidatable(self):
        system = complete_ground()
        context = digest("reconstruction/context/1")
        verifier = GroundReconstructionVerifier()
        certificate = verifier.certify(
            system, (("STEP",), ("STEP", "STEP")), context_digest=context
        )
        self.assertTrue(certificate.reconstructable_for_witnesses)
        self.assertEqual(certificate.witness_count, 2)
        self.assertEqual(certificate.max_horizon, 2)
        self.assertTrue(verifier.verify(system, certificate, context_digest=context))
        restored = GroundReconstructionCertificate.from_dict(certificate.to_dict())
        self.assertEqual(restored.digest, certificate.digest)

    def test_reconstruction_refuses_partial_ground(self):
        partial = GroundTransitionSystem(
            states=("s0", "s1"), actions=("STEP", "WAIT"),
            initial_state="s0", channels=("signal",),
            observations=(
                TransitionObservation("s0", "STEP", (TransitionOutcome("s1", (3,)),)),
            ),
        )
        with self.assertRaises(EvidenceError):
            GroundReconstructionVerifier().certify(
                partial, (("STEP",),), context_digest=digest("ctx")
            )

    def test_certificate_rejects_ground_or_context_drift(self):
        system = complete_ground()
        context = digest("ctx-1")
        verifier = GroundReconstructionVerifier()
        cert = verifier.certify(system, (("STEP",),), context_digest=context)
        with self.assertRaises(EvidenceError):
            verifier.verify(system, cert, context_digest=digest("ctx-2"))
        changed = GroundTransitionSystem(
            states=("s0", "s1"), actions=("STEP",), initial_state="s0",
            channels=("signal",),
            observations=(
                TransitionObservation("s0", "STEP", (TransitionOutcome("s0", (3,)),)),
                TransitionObservation("s1", "STEP", (TransitionOutcome("s1", (4,)),)),
            ),
        )
        with self.assertRaises(EvidenceError):
            verifier.verify(changed, cert, context_digest=context)


if __name__ == "__main__":
    unittest.main()
