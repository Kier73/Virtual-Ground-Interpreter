import hashlib
import json

from vgi.channels import ChannelContract, ChannelExchangeLedger, ChannelMessage
from vgi.encounters import EncounterProvenance
from vgi.evidence import (
    GroundReconstructionVerifier, TransitionEvidenceLedger, TransitionEvidencePolicy,
)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    contract = ChannelContract(
        "telemetry.bus", "telemetry.frame/1",
        observation_schema="vgi.transition-observation/1",
    )
    exchange = ChannelExchangeLedger()
    frames = []
    for source, seq, state, target, signal in (
        ("sensor-A", 11, "s0", "s1", 3),
        ("sensor-B", 27, "s0", "s1", 3),
        ("sensor-A", 12, "s1", "s1", 4),
        ("sensor-B", 28, "s1", "s1", 4),
    ):
        message = ChannelMessage(
            f"{source}-frame-{seq}", contract.channel_id, contract.protocol_id,
            "observation",
            {"status": "known", "source_state": state, "action": "STEP",
             "target": target, "output": [signal]},
            EncounterProvenance(
                source=source, source_ref=f"capture://{source}/{seq}",
                captured_at="2026-11-10T20:00:00-05:00",
            ),
        )
        exchange = exchange.record_observation(contract, message)
        frames.append((message, seq))
    encounters = exchange.to_encounter_ledger()

    context_digest = sha("plant-alpha/context/revision-1")
    policy = TransitionEvidencePolicy(
        "plant-alpha", context_digest, ("sensor-A", "sensor-B"),
        quorum=2, strict=True,
    )
    evidence = TransitionEvidenceLedger(policy)
    for message, seq in frames:
        evidence = evidence.ingest_channel_message(
            exchange, message.message_id, seq, encounters
        )
    before_close = {
        "s0/STEP": evidence.status("s0", "STEP").status,
        "s1/STEP": evidence.status("s1", "STEP").status,
    }
    evidence = evidence.finalize("s0", "STEP").finalize("s1", "STEP")
    ground = evidence.build_ground(
        states=("s0", "s1"), actions=("STEP",), initial_state="s0",
        channels=("signal",),
    )
    certificate = GroundReconstructionVerifier().certify(
        ground, (("STEP",), ("STEP", "STEP")),
        context_digest=context_digest,
    )
    print(json.dumps({
        "retained_encounters": len(encounters.encounters),
        "pre_finalization": before_close,
        "post_finalization": {
            "s0/STEP": evidence.decision("s0", "STEP").status,
            "s1/STEP": evidence.decision("s1", "STEP").status,
        },
        "ground_complete": ground.complete,
        "ground_fingerprint": ground.fingerprint,
        "reconstruction_certificate": certificate.to_dict(),
        "certificate_digest": certificate.digest,
        "interpretation": (
            "Two declared sources admitted these transitions under the explicit policy. "
            "The certificate covers only the supplied finite sequences and exact Ground "
            "and context; it does not prove the model exhausts the external plant."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
