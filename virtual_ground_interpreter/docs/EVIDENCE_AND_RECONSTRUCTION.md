# Evidence admission and Ground reconstruction

## Why this layer exists

A received frame is not necessarily an established fact. An admitted transition is not proof that the Ground exhausts an external system. A compiled Ground that matches its reference semantics on selected examples is not proof of untested behavior.

This module keeps three objects distinct:

1. **Observed evidence** — a ChannelMessage and its Encounter, bound to source, channel, protocol, transport sequence, payload digest, Ground identity, and context.
2. **Established transition** — a claim admitted only after explicit finalization under a declared source/quorum policy.
3. **Reconstructable Ground** — a complete Ground whose direct semantics and compiled VGI execution agree over a retained finite witness corpus.

The implementation is VGI-native. It is inspired by E-CPU's typed substrate observations, EvidenceLink frame binding, ObservationConsensus/GatedObservationCoordinator, and StructuralMemoryVerifier's finite witness certificates; it does not import E-CPU runtime code.

## Observed evidence

TransitionEvidence.from_channel_message accepts only an inbound observation or reply already present in ChannelExchangeLedger and whose derived Encounter exists in EncounterLedger. It verifies the exact payload, provenance, channel/protocol, direction, message identity, and correlation context.

The transport sequence is supplied separately because application message identity and transport-frame identity are different coordinates. Frame identity is scoped by source, channel, and sequence. Repeated matching messages from one source count as one source vote; a source that changes its claim creates a conflict.

The normalized transition claim has three statuses:

- known: source_state (or source), action, target, output;
- unknown: source_state (or source), action, with no proposed result;
- ambiguous: source_state (or source), action, and every represented alternative.

Unknown and ambiguous are indeterminate observations. They are not votes for a negative transition and cannot be used to complete a Ground.

## Policy-relative establishment

TransitionEvidencePolicy binds a Ground identity, context digest, allowed source set, quorum, and strictness.

For each (source_state, action), the ledger:
- groups known claims by exact (target, output);
- counts each source at most once;
- preserves unknown/ambiguous sources as indeterminate;
- reports dissent, missing sources, ties, and same-source changes separately.

A strict policy requires quorum with no dissent, no missing sources, and no indeterminate sources. A non-strict policy may admit a quorum despite dissent or missing sources, but those sources remain visible in the decision. Ties and same-source contradictions remain conflicts in either mode.

QUORUM is not yet an admitted transition. finalize() closes the event and records AUTHORIZED, CONFLICT, or REFUSED with the decision digest and exact ordered evidence IDs. New evidence for a finalized event must be collected under a new Ground/context revision.

build_ground() constructs a possibly partial Ground using only AUTHORIZED finalizations. Unseen, pending, unknown, ambiguous, refused, and conflicting events remain absent and therefore unknown in the resulting Ground. The Ground metadata retains the evidence policy and ledger digests.

## Reconstruction certificate

GroundReconstructionVerifier uses VGI's existing TransitionCompiler and differential_verify path. It requires a complete, single-valued Ground supported by the current Signal8 compiler, then executes a caller-declared corpus of finite action sequences through both direct Ground semantics and compiled VGI.

GroundReconstructionCertificate binds the exact Ground fingerprint, context digest, witness digest, explicit action sequences, witness count, maximum tested horizon, and compiler identity/version.

verify() reruns the witness corpus and checks the binding. The certificate means only that the compiled representation reproduced those finite action-sequence witnesses for that exact Ground and context. It is not a proof about untested sequences, undiscovered states/actions, or the external system. The certificate digest is an integrity identity, not an authenticated signature.

## Suggested loop

1. Retain inbound channel messages as Encounters.
2. Extract typed transition claims with transport-frame identity.
3. Accumulate evidence from policy-authorized sources.
4. Inspect each decision; do not infer from PENDING, unknown, or ambiguous.
5. Explicitly finalize each event.
6. Construct a partial Ground from admitted transitions.
7. Complete the finite Ground only as further evidence warrants.
8. Run the reconstruction verifier and retain its finite witness certificate.

Observed evidence, policy-admitted structure, and replay certificates remain separately addressable. None overwrites the previous layer.

## Limits

- Source authentication, transport encryption, and signatures are not provided; provenance is recorded, not authenticated.
- A quorum is a declared policy, not a universal truth criterion.
- Protocol-specific messages must be normalized into the declared transition-claim shape by an adapter.
- Only complete finite Grounds supported by the current Signal8 compiler receive reconstruction certificates.
- Replay certificates cover only their finite witness corpora and exact Ground/context digests.
- No automatic Ground mutation, missing-edge inference, or physical hidden-state identity claim is made.
