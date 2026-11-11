import unittest

from vgi.channels import (
    ChannelContract, ChannelError, ChannelExchangeLedger, ChannelMessage,
    PredictiveGroundAdapter,
)
from vgi.encounters import EncounterProvenance
from vgi.transitions import (
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
)


def partial_ground():
    return GroundTransitionSystem(
        states=("s0", "s1"),
        actions=("STEP", "MISSING", "CHOICE"),
        initial_state="s0",
        channels=("signal",),
        observations=(
            TransitionObservation(
                "s0", "STEP", (TransitionOutcome("s1", (3,)),),
                evidence=("trace-17",),
            ),
            TransitionObservation(
                "s1", "STEP", (TransitionOutcome("s1", (4,)),),
            ),
            TransitionObservation(
                "s0", "CHOICE",
                (
                    TransitionOutcome("s0", (1,)),
                    TransitionOutcome("s1", (6,)),
                ),
                support_count=2,
                evidence=("trial-a", "trial-b"),
            ),
            TransitionObservation(
                "s1", "CHOICE", (TransitionOutcome("s1", (0,)),),
            ),
        ),
    )


def sensor_contract():
    return ChannelContract(
        channel_id="sensor.temperature",
        protocol_id="sensor.frame/1",
        observation_schema="sensor.temperature.frame/1",
    )


def make_message(
    message_id, direction, *, channel_id="sensor.temperature",
    protocol_id="sensor.frame/1", payload=None, provenance=None, correlation_id=None,
):
    return ChannelMessage(
        message_id=message_id,
        channel_id=channel_id,
        protocol_id=protocol_id,
        direction=direction,
        payload=payload if payload is not None else {"reading": 21.5},
        provenance=provenance or EncounterProvenance(source=channel_id),
        correlation_id=correlation_id,
    )


class ChannelContractTests(unittest.TestCase):
    def test_observation_capability_does_not_imply_addressability(self):
        contract = sensor_contract()
        self.assertTrue(contract.can_observe)
        self.assertFalse(contract.can_address)
        ledger = ChannelExchangeLedger().record_observation(
            contract, make_message("obs-1", "observation")
        )
        self.assertEqual(len(ledger.messages), 1)
        self.assertEqual(len(ledger.to_encounter_ledger().encounters), 1)

    def test_observation_only_channel_rejects_request_intents(self):
        contract = sensor_contract()
        request = make_message("req-1", "request")
        with self.assertRaises(ChannelError):
            ChannelExchangeLedger().propose_request(contract, request)

    def test_contract_requires_request_and_response_schemas_together(self):
        with self.assertRaises(ChannelError):
            ChannelContract("broken", "wire/1", request_schema="request/1")

    def test_schema_and_protocol_must_match_message_direction(self):
        contract = sensor_contract()
        wrong_protocol = make_message("obs-bad", "observation", protocol_id="other/1")
        with self.assertRaises(ChannelError):
            ChannelExchangeLedger().record_observation(contract, wrong_protocol)

    def test_reply_requires_a_preceding_request_and_matching_correlation(self):
        adapter = PredictiveGroundAdapter(partial_ground())
        contract = adapter.contract
        request = ChannelMessage(
            "q-1", contract.channel_id, contract.protocol_id, "request",
            {"source": "s0", "action": "STEP"},
            EncounterProvenance(source="test-client"),
        )
        wrong = ChannelMessage(
            "reply-wrong", contract.channel_id, contract.protocol_id, "reply",
            {"status": "known"}, EncounterProvenance(source=contract.channel_id),
            correlation_id="not-q-1",
        )
        prepared = ChannelExchangeLedger().propose_request(contract, request)
        with self.assertRaises(ChannelError):
            prepared.record_reply(wrong)

    def test_ground_adapter_answers_known_transition_in_shared_protocol(self):
        adapter = PredictiveGroundAdapter(partial_ground())
        contract = adapter.contract
        request = ChannelMessage(
            "query-known", contract.channel_id, contract.protocol_id, "request",
            {"source": "s0", "action": "STEP"},
            EncounterProvenance(source="test-client"),
        )
        ledger = ChannelExchangeLedger().exchange(adapter, request)
        self.assertEqual([item.direction for item in ledger.messages], ["request", "reply"])
        reply = ledger.messages[-1]
        self.assertEqual(reply.correlation_id, request.message_id)
        self.assertEqual(reply.protocol_id, request.protocol_id)
        self.assertEqual(reply.payload["status"], "known")
        self.assertEqual(reply.payload["target"], "s1")
        self.assertEqual(reply.payload["output"], (3,))
        encounters = ledger.to_encounter_ledger()
        self.assertEqual(len(encounters.encounters), 1)
        encounter = encounters.encounters[0]
        self.assertEqual(encounter.payload["status"], "known")
        self.assertEqual(encounter.context["correlation_id"], request.message_id)

    def test_ground_adapter_reports_unknown_without_inventing_a_transition(self):
        adapter = PredictiveGroundAdapter(partial_ground())
        contract = adapter.contract
        request = ChannelMessage(
            "query-unknown", contract.channel_id, contract.protocol_id, "request",
            {"source": "s0", "action": "MISSING"},
            EncounterProvenance(source="test-client"),
        )
        reply = ChannelExchangeLedger().exchange(adapter, request).messages[-1]
        self.assertEqual(reply.payload["status"], "unknown")
        self.assertNotIn("target", reply.payload)
        self.assertNotIn("output", reply.payload)

    def test_ground_adapter_returns_all_ambiguous_alternatives(self):
        adapter = PredictiveGroundAdapter(partial_ground())
        contract = adapter.contract
        request = ChannelMessage(
            "query-ambiguous", contract.channel_id, contract.protocol_id, "request",
            {"source": "s0", "action": "CHOICE"},
            EncounterProvenance(source="test-client"),
        )
        reply = ChannelExchangeLedger().exchange(adapter, request).messages[-1]
        self.assertEqual(reply.payload["status"], "ambiguous")
        self.assertEqual(len(reply.payload["outcomes"]), 2)
        self.assertEqual(reply.payload["evidence"], ("trial-a", "trial-b"))

    def test_ground_adapter_rejects_queries_outside_declared_vocabulary(self):
        adapter = PredictiveGroundAdapter(partial_ground())
        contract = adapter.contract
        request = ChannelMessage(
            "query-outside", contract.channel_id, contract.protocol_id, "request",
            {"source": "not-a-state", "action": "STEP"},
            EncounterProvenance(source="test-client"),
        )
        with self.assertRaises(ChannelError):
            adapter.exchange(request)

    def test_exchange_ledger_round_trip_and_immutability(self):
        adapter = PredictiveGroundAdapter(partial_ground())
        contract = adapter.contract
        request = ChannelMessage(
            "query-roundtrip", contract.channel_id, contract.protocol_id, "request",
            {"source": "s0", "action": "STEP"},
            EncounterProvenance(source="test-client"),
        )
        ledger = ChannelExchangeLedger().exchange(adapter, request)
        restored = ChannelExchangeLedger.from_json(ledger.to_json())
        self.assertEqual(restored.fingerprint, ledger.fingerprint)
        self.assertEqual(len(ledger.messages), 2)
        self.assertEqual(len(restored.to_encounter_ledger().encounters), 1)


if __name__ == "__main__":
    unittest.main()
