import json

from vgi.channels import ChannelExchangeLedger, ChannelMessage, PredictiveGroundAdapter
from vgi.encounters import EncounterProvenance
from vgi.transitions import (
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
)


def main():
    ground = GroundTransitionSystem(
        states=("inside-0", "inside-1"),
        actions=("ADVANCE", "WAIT"),
        initial_state="inside-0",
        channels=("response",),
        observations=(
            TransitionObservation(
                "inside-0", "ADVANCE", (TransitionOutcome("inside-1", (2,)),),
                evidence=("synthetic-fixture:advance",),
            ),
            TransitionObservation(
                "inside-1", "ADVANCE", (TransitionOutcome("inside-1", (5,)),),
                evidence=("synthetic-fixture:advance-terminal",),
            ),
            TransitionObservation(
                "inside-0", "WAIT", (TransitionOutcome("inside-0", (0,)),),
            ),
            TransitionObservation(
                "inside-1", "WAIT", (TransitionOutcome("inside-1", (0,)),),
            ),
        ),
        metadata={"fixture": "duplex-channel-internal-query"},
    )
    adapter = PredictiveGroundAdapter(ground)
    contract = adapter.contract
    request = ChannelMessage(
        message_id="query-advance-0",
        channel_id=contract.channel_id,
        protocol_id=contract.protocol_id,
        direction="request",
        payload={"source": "inside-0", "action": "ADVANCE"},
        provenance=EncounterProvenance(source="example-client"),
    )
    exchange = ChannelExchangeLedger().exchange(adapter, request)
    reply = exchange.messages[-1]
    encounters = exchange.to_encounter_ledger()

    print(json.dumps({
        "contract": contract.to_dict(),
        "can_observe": contract.can_observe,
        "can_address": contract.can_address,
        "request": request.to_dict(),
        "reply": reply.to_dict(),
        "encounter_count": len(encounters.encounters),
        "encounter_fingerprint": encounters.fingerprint,
        "exchange_fingerprint": exchange.fingerprint,
        "interpretation": (
            "This is an internal query to a finite predictive Ground. The reply "
            "is model evidence, not a physical sensor response. Unknown and "
            "ambiguous answers are represented without completion."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
