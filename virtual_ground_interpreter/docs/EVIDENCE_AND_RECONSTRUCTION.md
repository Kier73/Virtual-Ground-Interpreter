# Evidence admission and Ground reconstruction

## Current implementation: observation → policy → admitted Ground → replay certificate

\`vgi.evidence\` implements four distinct transitions: retain an exact inbound message and its transport/encounter bindings; aggregate source-relative claims; explicitly finalize an event; construct authorized Ground transitions and verify a finite compiled replay corpus.

**Code**: [\`vgi/evidence.py\`](../vgi/evidence.py) (\`TransitionEvidenceLedger\`, \`TransitionEvidencePolicy\`, \`GroundReconstructionVerifier\`). **Tests**: [\`tests/test_evidence.py\`](../tests/test_evidence.py). The policy, claim and certificate each retain separate exact provenance identities.

### Formal admission relation

For one event \(e=(s,a)\), let \(S\) be the policy's allowed source IDs, \(q\) the quorum and \(R_e\) the retained evidence records. Group claims by source; a source with more than one distinct claim signature contributes to \(C_e\), the conflict set. A source with one \`known\` claim votes once for its exact \((target,output)\); a source with one \`unknown\` or \`ambiguous\` claim belongs to the indeterminate set \(I_e\).

For each outcome \(o\), define the agreeing source set \(A_o\), and let \(A_*\) be the unique largest group when one exists. Define \(M_e=S\setminus\operatorname{ObservedSources}(R_e)\) and \(D_e\) as known dissenters outside \(A_*\).

\[
\operatorname{Conflict}(e)=
(C_e\ne\varnothing)\;\lor\;\operatorname{TiedMax}(e)\;\lor\;
(\operatorname{strict}\land D_e\ne\varnothing).
\]

After conflict precedence is applied, the implementation returns \`QUORUM\` exactly when a unique winner exists, \(|A_*|\ge q\), and either \`strict=False\` or both \(M_e\) and \(I_e\) are empty. Other cases remain \`PENDING\`. In particular, strict dissent gives \`CONFLICT\`, whereas non-strict dissent may coexist with \`QUORUM\` and remains recorded.

The **commit boundary** is the separate call \`finalize(s,a)\`:

\[
\texttt{QUORUM}\mapsto\texttt{AUTHORIZED},\qquad
\texttt{CONFLICT}\mapsto\texttt{CONFLICT},\qquad
\texttt{PENDING}\mapsto\texttt{REFUSED}.
\]

\`build_ground\` includes a transition for \(e\) **iff** it has an \`AUTHORIZED\` finalization. The finalized event binds the ordered evidence IDs and the raw decision digest; further evidence for that event requires a new Ground/context revision.

### Current Python call path

\`\`\`python
from vgi.evidence import (
    TransitionEvidencePolicy, TransitionEvidenceLedger,
    GroundReconstructionVerifier,
)

# context_digest is the already computed, exact SHA-256 context identity.
policy = TransitionEvidencePolicy(
    "plant-alpha", context_digest, ("sensor-A", "sensor-B"), 2, True
)
ledger = TransitionEvidenceLedger(policy)
# Each inbound observation already has a ChannelExchangeLedger entry,
# a matching TransportFrameReceipt, and an EncounterLedger entry.
ledger = ledger.ingest_channel_message(exchange, message_id, frame, encounters)
decision_before_close = ledger.status("s0", "STEP")
ledger = ledger.finalize("s0", "STEP")
decision_after_close = ledger.decision("s0", "STEP")
ground = ledger.build_ground(
    states=("s0", "s1"), actions=("STEP",),
    initial_state="s0", channels=("signal",),
)
# When a complete, single-valued Ground exists:
certificate = GroundReconstructionVerifier().certify(
    ground, (("STEP",), ("STEP", "STEP")), context_digest=context_digest
)
\`\`\`

The final \`certify\` call requires a **complete** Ground; the snippet shows the API and is executable only when the supplied received evidence has authorized transitions for every declared state/action. For a self-contained two-state reconstruction fixture, see \`complete_ground()\` and \`GroundReconstructionTests.test_finite_compiled_replay_certificate_is_revalidatable\` in the tests.

### Replay obligation

For a complete Ground \(G\) and caller-declared finite action corpus \(W\), \`GroundReconstructionVerifier.certify\` requires

\[
\forall w\in W:\;
\operatorname{Run}_{G}(w)=\operatorname{Run}_{\operatorname{Compile}(G)}(w),
\]

including the checked trace semantics returned by \`differential_verify\`. The certificate binds the exact Ground fingerprint, context, compiler identity/version, action words and digest of direct-run traces. The current corpus has \(1\le |W|\le4096\), unique words, and maximum word length \(128\).

**Translation insight:** provenance and agreement, finalization authority, and replay equivalence are three different types of evidence. This makes a useful candidate for a typed cross-repository evidence interface: an observer-relative processor may consume a source law only after a declared evidence/admission transition, and its output equality can then be certified separately.


## Observed evidence

TransitionEvidence.from_channel_message accepts only an inbound observation or reply already present in ChannelExchangeLedger, a matching TransportFrameReceipt, and a derived Encounter in EncounterLedger. It verifies the exact payload, provenance, channel/protocol, direction, message identity, and correlation context.

A TransportFrameReceipt binds transport identity, frame ID, source, channel, message ID, sequence, and a digest of the exact ChannelMessage. The receipt is supplied by the adapter at its receive boundary. This provides integrity binding within the record, but does not cryptographically authenticate the adapter or source. Frame identity is scoped by transport, source, channel, and sequence. Repeated matching messages from one source count as one source vote; a source that changes its claim creates a conflict.

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

## Evidence scope and next construction

| Contract | Currently bound evidence | Next construction |
|---|---|---|
| Source identity | Transport frame/Encounter-linked provenance; integrity-bound source identifiers | Independently authenticated sensor/source identities |
| Admission | Source-deduplicated strict/non-strict quorum and explicit finalization | Connect receiver-owned policy authority across host domains |
| Ground | Only authorized state/action transitions; absent events remain partial | Qualified acquisition for unknown/ambiguous transitions |
| Reconstruction | Finite Signal8-compatible, complete Ground; caller-declared replay corpus | Extend compiler and independent witness domains |

The ledger's source identifiers and SHA-256 hashes are data-integrity records; actual authentication is supplied by the receiver's transport and trust system. The reconstruction certificate measures equivalence on the stated witness corpus. Neither the numerical quorum nor a finite replay corpus implies an unqualified external-world claim.

## Signal8 execution source

The Signal8 runtime can now serve as a first in-repository observation source.
`Signal8ExecutionAdapter` captures each successful instruction step as an
observation-only ChannelMessage, Encounter, TransportFrameReceipt, and
concrete-step TransitionEvidence claim. Runtime state identifiers are based on
a declared projection of machine configuration, while the original
`ExecutionEvent` retains raw signal values and branch measurements.

These records are scoped to one run and one concrete machine execution. They
are not independent source votes, are not automatically finalized, and do not
mutate a Ground. See [Signal8 execution trace capture](SIGNAL8_EXECUTION_TRACE.md).
