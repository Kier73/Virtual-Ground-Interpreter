# Open perception frontier

## The observer is a projection, not an ontology

The relational atlas derives distinctions from a finite transition Ground. An observer selects actions and channels; the resulting quotient says which declared predictive contexts that observer can distinguish over a finite horizon. It does not say that distinctions excluded by the observer do not exist.

A generator that proposes only actions, channels, transformations, or states already named by its observer risks reproducing that observer's blind spots. An unknown capability cannot be reliably listed by a mechanism that has no representation for it.

## Counterexample inquiry

The experimental module vgi/inquiry.py takes each pair still equivalent under the current observer and searches by breadth-first traversal over every action and channel already declared by the Ground. It returns the shortest shared action word whose terminal outputs differ, if such a word is supported by known, single-valued transitions.

The witness identifies both traces, differing channels, required horizon, and any already-declared actions or channels omitted by the current observer. This distinguishes perception omissions from temporal omissions.

Unknown and ambiguous transition cells block a verified experiment. They are reported with separate statuses and are never filled by inference.

## The open boundary

Every report carries an OpenWorldBoundary. It records the finite states, actions, channels, transition completeness, unknown cells, and ambiguous cells in the supplied Ground. Everything outside that declaration remains open and unenumerated.

Thus even equivalence over a complete declared Ground is scoped to the represented transition system and its alphabet. It is not physical hidden-state identity, universal observability, or proof that no other sensor, transformation, state, or distinction exists.

The boundary is not a list of hidden possibilities. Such a list would already impose a vocabulary on what it claims is unknown. The boundary instead records that the model has not closed the world.

This API cannot generate an undeclared transformation or an entirely unrepresented state. Those require a new semantic contract and fresh evidence, not a synthetic prediction.

## Conclusions

- witness_found: a shortest distinguishing word was found using known transitions.
- equivalent_over_declared_ground: the reachable paired graph was exhausted without a difference or blocked edge.
- no_witness_within_horizon: the explicit search bound was reached without a witness.
- inconclusive_missing_evidence: a reachable unknown or ambiguous transition blocked part of the inquiry.

Run from the package directory:

    python -m unittest discover -s tests -p 'test_perception_inquiry.py' -v
    python examples/run_perception_inquiry.py

This research tool prescribes inquiries. It does not acquire live sensor data or mutate the Ground automatically.
