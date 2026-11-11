# Encounter and association layer

## Why this layer exists

A task-directed observer is useful for resolving a known question, but it should not determine which encounters can enter memory or which cross-domain connections may be proposed. The encounter layer therefore sits before semantic interpretation.

It has two separate stores:

1. EncounterLedger: immutable, append-only records of observations, payloads, provenance, and context.
2. AssociationLedger: explicit hypotheses connecting one or more encounters, their rationale, a proposed experiment, a falsifier, and an append-only history of assessments.

The layers do not require encounters to share a vocabulary, source, context key, or domain before they can be associated.

## Encounter envelope

An Encounter consists of a caller-assigned unique identifier; a JSON-compatible payload without a mandatory semantic label; provenance (source, optional source reference, capture-time string, collector, and external content digest); and a JSON-compatible context object.

Nested payload/context structures are frozen on construction. Appending returns a new ledger, duplicate IDs are rejected, and canonical JSON fingerprints make changes detectable. Large or non-JSON source material should remain in its original source system and be referenced by source_ref plus a SHA-256 digest. The digest is recorded, not independently authenticated or checked against a remote object by this package.

The envelope is not an acquisition driver. It preserves what a caller supplies; it does not claim to have sensed or independently verified the source.

## Association hypotheses

An AssociationHypothesis references at least two existing encounter IDs and contains a proposed relationship, the rationale for considering it, a concrete experiment, an explicit falsifier, and the proposer.

The relation is deliberately free-form. The core does not infer a relationship merely because two encounters share a tag, context key, modality, or source. Upstream agents and people can use different reasoning methods to propose connections without forcing those methods into this store's ontology.

Hypotheses are tentative by construction. Proposals must resolve to existing encounters. They cannot modify the referenced records.

## Append-only assessments

An AssociationAssessment records one of three outcomes: supports, contradicts, or inconclusive.

Supporting and contradicting assessments require references to evidence encounters already present in the encounter ledger. At least one cited encounter must not have been part of the original hypothesis basis; this prevents simply relabeling the observations that inspired the hypothesis as independent confirmation. The original basis may still be cited alongside new evidence.

Inconclusive assessments may record partial evidence or no new evidence. Assessment history is append-only: a later contradiction does not erase an earlier supporting assessment, and vice versa.

The current verdict is only the last recorded assessment, not a universal truth value. Conflicting history remains accessible and must be interpreted in its experimental context. The core does not automatically promote any association into a predictive Ground, an executable transition, or a general law.

## Suggested workflow

1. Append an Encounter before assigning it a relationship to the current objective.
2. Allow directed or open-ended exploration to inspect the ledger and propose a cross-encounter hypothesis.
3. Require a rationale, experiment, and falsifier before storing the hypothesis.
4. Append new observations from the experiment as new encounters.
5. Assess the hypothesis by referencing those new encounter IDs.
6. Only a separate Ground-construction and verification process may derive a formal transition or invariant from the evidence.

This architecture preserves the possibility that an incidental observation becomes relevant later without pretending that every encounter must immediately become a candidate state or action.

## Limits

- Payload and context envelopes are JSON-compatible; arbitrary binary data should remain in an external store with a reference and digest.
- There is no automatic semantic embedding, similarity score, or pairwise association enumeration.
- The core does not rank hypotheses by an uncalibrated novelty or curiosity scalar.
- It does not prove the independence or truth of evidence references; provenance is recorded, not authenticated.
- It does not acquire live sensor data or mutate a Ground.
