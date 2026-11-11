# Legacy Signal8 execution-observation adapter

> **Compatibility note:** this document describes the earlier
> `vgi.signal8_trace.LegacySignal8ExecutionAdapter` API, which captures an
> already-instantiated `SignalStateMachine`. The canonical serialized
> capture/replay API is now `vgi.execution.Signal8ExecutionAdapter`, documented
> in [SIGNAL8_EXECUTION_TRACES.md](SIGNAL8_EXECUTION_TRACES.md).

The legacy adapter remains available for callers that need to observe a
machine already in progress. Its entry point is
`LegacySignal8ExecutionAdapter.capture(machine, run_id=..., max_steps=...)`.
It retains before/after runtime configurations, raw events, Encounters,
frame receipts, and concrete step-level transition evidence. It does not
finalize a policy or mutate a Ground.

The canonical execution-trace API starts from a declared Program and initial
SignalValue memory, serializes a complete trace envelope, and supports
same-runtime replay verification. New code should use that API.
