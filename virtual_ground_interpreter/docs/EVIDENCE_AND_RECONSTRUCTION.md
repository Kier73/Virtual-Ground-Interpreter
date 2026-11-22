# Evidence admission and Ground reconstruction

## Current implementation: observation → policy → admitted Ground → replay certificate

`vgi.evidence` implements four distinct transitions: retain an exact inbound message and its transport/encounter bindings; aggregate source-relative claims; explicitly finalize an event; construct authorized Ground transitions and verify a finite compiled replay corpus.

**Code**: [`vgi/evidence.py`](../vgi/evidence.py) (`TransitionEvidenceLedger`, `TransitionEvidencePolicy`, `GroundReconstructionVerifier`). **Tests**: [`tests/test_evidence.py`](../tests/test_evidence.py). The policy, claim and certificate each retain separate exact provenance identities.

### Formal admission relation

For one event \(e=(s,a)\), let \(S\) be the policy's allowed source IDs, \(q\) the quorum and \(R_e\) the retained evidence records. Group claims by source; a source with more than one distinct claim signature contributes to \(C_e\), the conflict set. A source with one `known` claim votes once for its exact \((target,output)\); a source with one `unknown` or `ambiguous` claim belongs to the indeterminate set \(I_e\).

For each outcome \(o\), define the agreeing source set \(A_o\), and let \(A_*\) be the unique largest group when one exists. Define \(M_e=S\setminus\operatorname{ObservedSources}(R_e)\) and \(D_e\) as known dissenters outside \(A_*\).

\[
\operatorname{Conflict}(e)=
(C_e\ne\varnothing)\;\lor\;\operatorname{TiedMax}(e)\;\lor\;
(\operatorname{strict}\land D_e\ne\varnothing).
\]

After conflict precedence is applied, the implementation returns `QUORUM` exactly when a unique winner exists, \(|A_*|\ge q\), and either `strict=False` or both \(M_e\) and \(I_e\) are empty. Other cases remain `PENDING`. In particular, strict dissent gives `CONFLICT`, whereas non-strict dissent may coexist with `QUORUM` and remains recorded.

The **commit boundary** is the separate call `finalize(s,a)`:

\[
\texttt{QUORUM}\mapsto\texttt{AUTHORIZED},\qquad
\texttt{CONFLICT}\mapsto\texttt{CONFLICT},\qquad
\texttt{PENDING}\mapsto\texttt{REFUSED}.
\]

`build_ground` includes a transition for \(e\) **iff** it has an `AUTHORIZED` finalization. The finalized event binds the ordered evidence IDs and the raw decision digest; further evidence for that event requires a new Ground/context revision.

### Current Python call path

```python
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
```

The final `certify` call requires a **complete** Ground; the snippet shows the API and is executable only when the supplied received evidence has authorized transitions for every declared state/action. For a self-contained two-state reconstruction fixture, see `complete_ground()` and `GroundReconstructionTests.test_finite_compiled_replay_certificate_is_revalidatable` in the tests.

### Replay obligation

For a complete Ground \(G\) and caller-declared finite action corpus \(W\), `GroundReconstructionVerifier.certify` requires

\[
\forall w\in W:\;
\operatorname{Run}_{G}(w)=\operatorname{Run}_{\operatorname{Compile}(G)}(w),
\]

including the checked trace semantics returned by `differential_verify`. The certificate binds the exact Ground fingerprint, context, compiler identity/version, action words and digest of direct-run traces. The current corpus has \(1\le |W|\le4096\), unique words, and maximum word length \(128\).

**Translation insight:** provenance and agreement, finalization authority, and replay equivalence are three different types of evidence. This makes a useful candidate for a typed cross-repository evidence interface: an observer-relative processor may consume a source law only after a declared evidence/admission transition, and its output equality can then be certified separately.


## Operational evidence and reconstruction details

| Stage | Actual input and invariant |
|---|---|
| Receive | `TransitionEvidence.from_channel_message` validates an inbound `ChannelMessage` against `ChannelExchangeLedger`, the matching `TransportFrameReceipt`, and `EncounterLedger`; exact frame identity includes transport, source, channel and sequence |
| Normalize | `known` has a single target/output; `unknown` has no outcome; `ambiguous` retains declared alternatives; indeterminate observations never vote for a negative transition |
| Decide | Distinct source claims are counted once per exact outcome; a changed signature by the same source is retained as a conflict; missing, dissenting and indeterminate sets remain visible |
| Finalize | The `AUTHORIZED`, `CONFLICT`, or `REFUSED` decision is digest-bound to exact event evidence and cannot be retroactively edited within that revision |
| Compile and certify | `GroundReconstructionVerifier` compares direct Ground execution with the existing `TransitionCompiler` for each declared finite action word, retaining source Ground/context identity and exact witness traces |

Receiver authentication is distinct from the transport receipt's recorded identity. The certificate checks the declared corpus and compiler version. The underlying exact evidentiary objects are retained rather than overwritten at each stage.

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
