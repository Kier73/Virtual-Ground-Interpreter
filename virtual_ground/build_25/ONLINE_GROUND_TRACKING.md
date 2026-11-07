# Online Ground Tracking

## Runtime model

A learned ground is an executable transition/output machine. The online observer does not assume it knows the current context. It starts from all predictive contexts compatible with the declared observer.

Each action advances each hypothesis. The model's output for that action is retained until all declared sensor channels arrive. Incoming measurements filter the possible paths, including readings that arrive after later actions have already been issued.

The online observer's state is therefore not necessarily one hidden state. It is a set of consistent path hypotheses. This is an observer-relative uncertainty representation.

## Why retain path hypotheses?

If the tracker received all outputs synchronously, a set-valued current state would be sufficient. In a distributed stream, a later sensor channel may refer to an earlier operation. By retaining the predicted output associated with each pending step, the tracker can apply a late measurement to the correct historical transition and propagate the restriction to the current context.

This is a compact finite-state form of delayed-evidence filtering.

## Contradiction semantics

An empty hypothesis set is not interpreted as an instruction to restore all states. It is a model contradiction. The tracker freezes its predictive state and exports its evidence. This prevents a ground from evading falsification by silently resetting its belief.

Recovery is a separate operation that must be specified and reviewed. Build 25 intentionally does not provide an automatic rebase or ground replacement function.

## Bounded memory

Completed action/output records are removed from the live filter after all channels arrive. A bounded recent cache supports idempotent retransmission and duplicate conflict detection. An older event beyond this cache is marked stale; it is not admitted as fresh evidence. Full logs should be persisted externally when long-term audit is required.
